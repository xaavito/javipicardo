"""
Catalogo de comandos - generado dinamicamente a partir de los diccionarios de
`fase1_text_commands.py`, para que el LLM (Fase 4, fallback) y el parser de
reglas (Fase 1) NUNCA queden desincronizados. Si se agrega un comando nuevo a
cualquiera de los diccionarios de fase1_text_commands.py, este catalogo lo
refleja automaticamente sin tener que tocar nada aca.

Se usa desde llm_fallback.py para armar el system prompt del LLM: en vez de
dejarlo "inventar" acciones libremente, se le pasa la lista EXACTA de acciones
validas que el sistema puede ejecutar, y se le pide que elija una de esas (o
ninguna, si no aplica ningun comando).
"""

import fase1_text_commands as fase1

# Target memory slots: the game keys 5-8 select, CTRL+5-8 store (manual p.157).
RANURA_POR_TECLA = {"5": 1, "6": 2, "7": 3, "8": 4}

# Cached (tools, mapa) pair -- see generar_tools_openai().
_tools_cacheadas = None


def _agrupar_por_tecla(diccionario):
    """{frase: tecla} -> {tecla: [frases]}, keeping the original order."""
    agrupado = {}
    for frase, tecla in diccionario.items():
        agrupado.setdefault(tecla, []).append(frase)
    return agrupado


def generar_catalogo():
    """Devuelve una lista de dicts, cada uno describiendo una accion posible
    que el sistema puede ejecutar, con su nombre, una breve descripcion, y
    ejemplos de frases que la activan. Pensado para servir de contexto a un
    LLM (Fase 4) o para mostrar como ayuda (Fase 1)."""
    catalogo = []

    # --- Velocidad por nivel ---
    niveles_nombre = {0: "detener", 1: "cuarto_maquina", 2: "media_maquina",
                      3: "tres_cuartos_maquina", 4: "toda_maquina"}
    # Frases de ejemplo por nivel (tomamos 1-2 de SPEED_WORDS para cada nivel)
    ejemplos_por_nivel = {}
    for frase, nivel in fase1.SPEED_WORDS.items():
        ejemplos_por_nivel.setdefault(nivel, []).append(frase)

    for nivel, nombre in niveles_nombre.items():
        catalogo.append({
            "accion": "set_speed",
            "parametros": {"level": nivel},
            "nombre_legible": nombre,
            "descripcion": f"Ajustar velocidad a nivel {nivel} de 4 "
                           f"({nombre.replace('_', ' ')})",
            "ejemplos": ejemplos_por_nivel.get(nivel, [])[:3],
        })

    # --- Comandos de una sola tecla (alertas, disparo, escudos, etc.) ---
    grupos_de_una_tecla = [
        ("red_alert", fase1.ALERT_WORDS.keys(), "r", "Activar alerta roja"),
        ("disparar", fase1.FIRE_WORDS, "z", "Disparar armas (una descarga)"),
        ("escudos_maximo", fase1.SHIELD_MAX_WORDS, "k",
         "Abrir panel de escudos / reforzar escudos"),
        ("camuflaje", fase1.CLOAK_WORDS, "x", "Activar/desactivar camuflaje"),
        ("deep_scan", fase1.DEEPSCAN_WORDS, "i", "Activar/desactivar deep scan"),
        ("seguir_target", fase1.FOLLOW_WORDS, "multiply",
         "Seguir automaticamente a la nave/objetivo seleccionado"),
        ("siguiente_objetivo", fase1.NEXT_TARGET_WORDS, "t",
         "Ciclar al siguiente objetivo disponible"),
        ("objetivo_mas_cercano", fase1.NEAREST_ENEMY_WORDS, "`",
         "Seleccionar como objetivo al enemigo mas cercano"),
        ("siguiente_enemigo", fase1.NEXT_ENEMY_WORDS, "y",
         "Ciclar al siguiente enemigo, salteando unidades no hostiles"),
        ("deseleccionar_objetivo", fase1.DESELECT_WORDS, "\\",
         "Soltar el objetivo seleccionado, sin elegir otro"),
        ("orbitar_objetivo", fase1.ORBIT_WORDS, fase1.TECLA_ORBITAR,
         "Poner la nave en orbita alrededor del objetivo"),
        ("maniobras_evasivas", fase1.ERRATIC_WORDS, "divide",
         "Maniobras erraticas: +4 de ECM natural, a costa de nuestra "
         "punteria y de no poder lanzar shuttles/minas/torpedos"),
    ]
    for nombre, frases, tecla, descripcion in grupos_de_una_tecla:
        catalogo.append({
            "accion": "key",
            "parametros": {"key": tecla},
            "nombre_legible": nombre,
            "descripcion": descripcion,
            "ejemplos": list(frases)[:3],
        })

    # --- Comandos de dos teclas (modificador + tecla) ---
    grupos_de_dos_teclas = [
        ("alpha_strike", fase1.ALPHA_STRIKE_WORDS, ["shift", "z"],
         "Disparar todas las armas de todos los hardpoints a la vez"),
        ("enemigo_anterior", fase1.PREV_ENEMY_WORDS, ["shift", "y"],
         "Ciclar hacia atras entre enemigos, volver al anterior"),
        ("objetivo_anterior", fase1.PREV_TARGET_WORDS, ["shift", "t"],
         "Ciclar hacia atras entre objetivos, volver al anterior"),
    ]
    for nombre, frases, teclas, descripcion in grupos_de_dos_teclas:
        catalogo.append({
            "accion": "key_combo",
            "parametros": {"keys": teclas},
            "nombre_legible": nombre,
            "descripcion": descripcion,
            "ejemplos": list(frases)[:3],
        })

    # --- Memoria de targets: seleccionar (5-8) y guardar (CTRL+5-8) ---
    # Built from the phrase->key dicts, so a new phrase for an existing slot
    # shows up here on its own.
    for tecla, frases in _agrupar_por_tecla(fase1.TARGET_MEMORIA_WORDS).items():
        ranura = RANURA_POR_TECLA.get(tecla, tecla)
        catalogo.append({
            "accion": "key",
            "parametros": {"key": tecla},
            "nombre_legible": f"seleccionar_objetivo_memorizado_{ranura}",
            "descripcion": (f"Volver a seleccionar la nave guardada en la "
                            f"ranura de memoria {ranura}"),
            "ejemplos": frases[:3],
        })

    for tecla, frases in _agrupar_por_tecla(fase1.GUARDAR_TARGET_WORDS).items():
        ranura = RANURA_POR_TECLA.get(tecla, tecla)
        catalogo.append({
            "accion": "key_combo",
            "parametros": {"keys": ["ctrl", tecla]},
            "nombre_legible": f"guardar_objetivo_en_memoria_{ranura}",
            "descripcion": (f"Guardar el objetivo actual en la ranura de "
                            f"memoria {ranura}, para volver a el mas tarde"),
            "ejemplos": frases[:3],
        })

    # --- Combos (definidos en fase1.COMBOS) ---
    for nombre_combo, datos in fase1.COMBOS.items():
        catalogo.append({
            "accion": "combo",
            "parametros": {"combo": nombre_combo},
            "nombre_legible": nombre_combo,
            "descripcion": datos["descripcion"],
            "ejemplos": datos["palabras"][:3],
        })

    return catalogo


def generar_tools_openai():
    """Genera el catalogo en el formato "tools" (function calling) que espera
    la API de OpenAI (chat.completions con parametro `tools=`). Cada comando
    del catalogo se expone como una funcion SIN parametros libres (el nombre
    de la funcion ya identifica la accion exacta a ejecutar - no hace falta
    que el modelo "complete" argumentos, solo elegir cual invocar). Esto es
    mas rapido y confiable que pedirle al modelo que genere JSON libre: la
    API valida que el nombre de funcion elegido exista en este esquema, y el
    modelo esta especificamente entrenado para esta tarea de eleccion.

    Devuelve: (lista_de_tools, mapa_nombre_a_item)
    - lista_de_tools: lista en formato OpenAI tools, lista para pasar tal
      cual al parametro `tools=` de chat.completions.create().
    - mapa_nombre_a_item: dict {nombre_legible: item_del_catalogo}, para
      traducir de vuelta el nombre de funcion elegido a la accion interna
      real que hay que ejecutar.
    """
    # Cached: the catalog comes from static dicts, so the schema never
    # changes while the program runs. Without the cache the warm-up call in
    # precalentar_todo() achieved nothing and every LLM fallback rebuilt the
    # whole schema before being able to ask anything.
    global _tools_cacheadas
    if _tools_cacheadas is not None:
        return _tools_cacheadas

    catalogo = generar_catalogo()
    tools = []
    mapa = {}

    for item in catalogo:
        nombre = item["nombre_legible"]
        ejemplos = ", ".join(f'"{e}"' for e in item["ejemplos"])
        descripcion = f"{item['descripcion']}. Frases tipicas: {ejemplos}."

        tools.append({
            "type": "function",
            "function": {
                "name": nombre,
                "description": descripcion,
                "parameters": {
                    "type": "object",
                    "properties": {},  # sin argumentos libres, ver docstring
                    "required": [],
                },
            },
        })
        mapa[nombre] = item

    _tools_cacheadas = (tools, mapa)
    return _tools_cacheadas


# Command dictionaries of fase1 that on purpose stay out of the catalog:
# "ayuda" prints the command list instead of pressing a key, so there is
# nothing for the LLM to invoke.
FUERA_DEL_CATALOGO = {"HELP_WORDS"}


def verificar_cobertura():
    """Lists the fase1 command dictionaries that no catalog entry covers.

    The catalog is the only thing the LLM fallback can choose from, so a
    command the rules parser understands but that is missing here is
    unreachable by voice through the LLM. That is what happened with the
    targeting and helm commands added on 12/09. Compares the first phrase of
    every `*_WORDS` collection of fase1 against the catalog examples.

    Returns a list of (dictionary name, phrase that is not represented).
    """
    ejemplos = set()
    for item in generar_catalogo():
        ejemplos.update(item["ejemplos"])

    faltantes = []
    for nombre, valor in vars(fase1).items():
        if not nombre.endswith("_WORDS") or nombre in FUERA_DEL_CATALOGO:
            continue
        if not isinstance(valor, (list, dict)) or not valor:
            continue
        primera = list(valor)[0]
        if primera not in ejemplos:
            faltantes.append((nombre, primera))
    return faltantes


def catalogo_como_texto():
    """Version en texto plano del catalogo, lista para insertar en un prompt
    de LLM o para imprimir como ayuda."""
    lineas = []
    for item in generar_catalogo():
        ejemplos = " | ".join(f'"{e}"' for e in item["ejemplos"])
        lineas.append(
            f"- accion=\"{item['accion']}\" parametros={item['parametros']} "
            f"({item['descripcion']}). Ejemplos de frases: {ejemplos}"
        )
    return "\n".join(lineas)


if __name__ == "__main__":
    # Permite correr este archivo solo para ver el catalogo generado:
    #   python catalogo_comandos.py
    print(catalogo_como_texto())

    faltantes = verificar_cobertura()
    print(f"\n{len(generar_catalogo())} comandos en el catalogo.")
    if faltantes:
        print("\n[!] Comandos que el parser entiende pero el LLM NO puede "
              "elegir (agregarlos en generar_catalogo):")
        for nombre, frase in faltantes:
            print(f"  - {nombre}  (ej. \"{frase}\")")
    else:
        print("Cobertura OK: el catalogo cubre todos los comandos del parser.")
