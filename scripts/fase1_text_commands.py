"""
Fase 1 - Parser de comandos por texto (sin voz, sin red)

Objetivo: validar el mapeo "intencion -> teclas" con un loop simple de texto en
consola, usando el mismo juego "Star Trek: Starfleet Command Gold Edition" ya
validado en la Fase 0 (via DxWnd, en modo ventana).

Como usar:
1. Igual que en la Fase 0: abrir el juego DESDE DxWnd, entrar a una mision/
   tutorial donde la nave pueda moverse.
2. Instalar la dependencia nueva de este script (ademas de pydirectinput):
       pip install pygetwindow
3. Ajustar WINDOW_TITLE_KEYWORDS mas abajo si hace falta, para que coincida con
   el titulo real de la ventana del juego (ver seccion "Como encontrar el
   titulo" mas abajo).
4. Correr este script DESDE UNA CONSOLA COMO ADMINISTRADOR (imprescindible,
   ver ROADMAP.md Fase 0 - sin privilegios elevados el input no llega al juego):
       python fase1_text_commands.py
5. Escribir comandos en espanol en la consola, por ejemplo:
       alerta roja
       disparar
       media maquina
       cuarto de maquina
       alto total
       escudos al maximo
       seguir a esa nave / seguir a la amenaza
       ataquen con todo          (combo: max ECM + alpha strike)
       alejense a maxima velocidad  (combo: acelerar al 100%)
       ayuda                     (lista todos los comandos disponibles)
6. Escribir "salir" o "exit" para terminar el loop.

NOTA sobre COMBOS: una sola frase puede disparar varias teclas en secuencia
(ver diccionario COMBOS mas abajo). Es facil agregar mas combos nuevos:
agregar una entrada a COMBOS con "palabras" (lista de frases que lo activan),
"pasos" (lista de teclas o tuplas (tecla, cantidad) a ejecutar en orden), y
"descripcion" (para que aparezca en el listado de "ayuda").

IMPORTANTE - Manejo de foco de ventana (ida y vuelta automatica):
Como el comando se escribe en la consola (que tiene el foco mientras escribis),
el script NO depende de que vos hagas click manual en el juego antes de cada
accion. El flujo de foco es:
  1. Escribis el comando en la consola (foco en la consola, normal).
  2. Al confirmar con Enter, ANTES de mandar cualquier tecla, el script busca
     la ventana del juego por su titulo y la trae al frente automaticamente
     (funcion enfocar_ventana_juego).
  3. Se manda la tecla/combo/secuencia de velocidad al juego, ya enfocado.
  4. Al terminar de mandar la(s) tecla(s), el script vuelve a traer al frente
     la ventana de la consola automaticamente (funcion enfocar_consola), asi
     queda todo listo para escribir el siguiente comando comodamente sin tener
     que hacer Alt+Tab ni click manual en ningun momento.

Como encontrar el titulo exacto de la ventana del juego (si el matching
automatico no encuentra la ventana):
1. Con el juego abierto via DxWnd, abrir el Administrador de Tareas.
2. Pestaña "Detalles" (o "Procesos"), buscar el proceso del juego/DxWnd.
3. O simplemente correr en una consola de Python:
       import pygetwindow as gw
       print(gw.getAllTitles())
   y buscar en la lista impresa el titulo real de la ventana del juego, para
   copiarlo (o parte de el) en WINDOW_TITLE_KEYWORDS abajo.

Nota importante sobre velocidad: en esta fase, "cuarto/media/tres cuartos/toda
maquina" se traducen a una CANTIDAD FIJA Y APROXIMADA de pulsaciones de S/A
(ver STEPS_VELOCIDAD abajo). Esto es una aproximacion para validar el flujo
completo; la precision real (basada en la velocidad maxima real de la nave)
se aborda en la Fase 3 del roadmap (OCR del HUD o calibracion manual por nave).
"""

import re
import unicodedata
import time
import ctypes

import pydirectinput
import pygetwindow as gw

# Titulo EXACTO de la ventana del juego, confirmado en pruebas reales (ver
# scripts/probar_activar.py) corriendo pygetwindow.getAllWindows() con el
# juego abierto via DxWnd. Se usa como primer intento de busqueda (mas
# preciso, evita falsos positivos con otras ventanas que puedan contener
# palabras parecidas en el titulo, ej. un navegador con una pestana sobre el
# juego).
WINDOW_TITLE_EXACTO = "Starfleet Command"

# Palabras clave de respaldo (si por algun motivo el titulo exacto cambiara,
# ej. al abrir otra mision o actualizar el juego). Se usan solo si la
# busqueda por titulo exacto no encuentra nada.
WINDOW_TITLE_KEYWORDS = ["starfleet", "star trek", "dxwnd"]

# Si es True, tira una excepcion cuando no encuentra la ventana del juego (en
# vez de solo avisar por consola y seguir sin mandar la tecla).
FALLAR_SI_NO_ENCUENTRA_VENTANA = False

# Pausa despues de enfocar la ventana del juego, antes de mandar la primera
# tecla. IMPORTANTE: se confirmo en pruebas (scripts/probar_tecla_con_foco.py)
# que con una pausa corta (0.15s) la tecla no llegaba al juego pese a que
# Windows ya marcaba la ventana como "activa" - haciendo falta una pausa mas
# larga para que el juego "asiente" el cambio de foco internamente.
PAUSA_POST_ENFOQUE = 1.0


# ---------------------------------------------------------------------------
# 1) Normalizacion de texto
# ---------------------------------------------------------------------------

def normalizar(texto):
    """Pasa a minusculas, saca tildes/acentos y espacios extra."""
    texto = texto.lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def contiene_frase(texto_normalizado, frase):
    """Busca 'frase' dentro de 'texto_normalizado' respetando limites de
    palabra, para evitar falsos positivos como 'parar' matcheando dentro de
    'disparar'."""
    patron = r'\b' + re.escape(frase) + r'\b'
    return re.search(patron, texto_normalizado) is not None


# ---------------------------------------------------------------------------
# Manejo de foco de ventana: buscar y activar la ventana del juego antes de
# mandar cualquier tecla, para no depender de que el usuario haga click
# manualmente en el juego (la consola tiene el foco mientras se escribe).
# ---------------------------------------------------------------------------

def encontrar_ventana_juego():
    """Busca la ventana del juego. Primero intenta por titulo EXACTO
    (case-insensitive y con strip de espacios, mas tolerante que
    getWindowsWithTitle "a pelo"). Si no encuentra nada asi, cae a la busqueda
    laxa por palabras clave (WINDOW_TITLE_KEYWORDS). Devuelve el objeto
    ventana de pygetwindow, o None si no encuentra ninguna con ningun metodo.

    NOTA: se volvio a este metodo (recorrer getAllWindows() a mano en vez de
    depender de gw.getWindowsWithTitle()) porque en una version anterior de
    este script, getWindowsWithTitle() con el titulo exacto dejo de encontrar
    la ventana en la practica (posible sensibilidad a mayusculas/espacios en
    esa funcion especifica de pygetwindow), rompiendo el enfoque que antes
    funcionaba con la busqueda laxa por substring."""
    todas = gw.getAllWindows()

    # Intento 1: titulo exacto (case-insensitive, con strip)
    objetivo = WINDOW_TITLE_EXACTO.strip().lower()
    for ventana in todas:
        titulo = (ventana.title or "").strip().lower()
        if titulo == objetivo:
            return ventana

    # Intento 2 (respaldo): palabras clave, busqueda laxa por substring
    for ventana in todas:
        titulo = (ventana.title or "").lower()
        if not titulo:
            continue
        if any(kw in titulo for kw in WINDOW_TITLE_KEYWORDS):
            return ventana
    return None


def enfocar_ventana_juego():
    """Intenta traer al frente la ventana del juego. Devuelve True si lo
    logro, False si no encontro la ventana (y no hizo nada)."""
    ventana = encontrar_ventana_juego()
    if ventana is None:
        msg = (f"No se encontro la ventana '{WINDOW_TITLE_EXACTO}' (titulo "
               f"exacto) ni ninguna con titulo que contenga "
               f"{WINDOW_TITLE_KEYWORDS} (respaldo). Ejecutar "
               "pygetwindow.getAllTitles() para ver los titulos disponibles "
               "y ajustar WINDOW_TITLE_EXACTO/WINDOW_TITLE_KEYWORDS.")
        if FALLAR_SI_NO_ENCUENTRA_VENTANA:
            raise RuntimeError(msg)
        print(f"  [!] {msg}")
        return False

    # Log de debug: siempre visible, para poder confirmar en la consola
    # exactamente que ventana se encontro (titulo y hwnd) antes de intentar
    # enfocarla y mandar la tecla.
    print(f"  [debug] Ventana encontrada: titulo={ventana.title!r} "
          f"hwnd={ventana._hWnd}")

    try:
        if ventana.isMinimized:
            ventana.restore()
        # Se usa BringWindowToTop + SetForegroundWindow via ctypes en vez de
        # pygetwindow.activate(): en las pruebas (scripts/probar_activar.py y
        # probar_tecla_con_foco.py) se confirmo que este metodo, combinado con
        # una pausa mas larga despues (PAUSA_POST_ENFOQUE), es el que
        # efectivamente logra que la tecla llegue al juego. Con activate() +
        # una pausa corta, Windows marcaba la ventana como "activa" pero el
        # juego no llegaba a procesar la tecla igual.
        hwnd = ventana._hWnd
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        # Pausa mas larga para dar tiempo a que el juego "asiente" el cambio
        # de foco internamente antes de mandar la tecla.
        time.sleep(PAUSA_POST_ENFOQUE)

        # Debug: confirmar cual ventana quedo realmente activa segun Windows,
        # para comparar contra la que se intento enfocar.
        activa = gw.getActiveWindow()
        print(f"  [debug] Ventana activa despues de enfocar: "
              f"{activa.title if activa else None!r}")

        return True
    except Exception as e:
        print(f"  [!] No se pudo activar la ventana del juego: {e}")
        return False


def enfocar_consola():
    """Vuelve a traer al frente la ventana de ESTA consola (donde corre el
    script), despues de haber enfocado el juego para mandar una tecla. Usa
    ctypes/Win32 directo (GetConsoleWindow + SetForegroundWindow) en vez de
    buscar por titulo, porque el titulo de la consola puede variar segun como
    se la haya abierto."""
    try:
        import ctypes
        hwnd_consola = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd_consola:
            ctypes.windll.user32.SetForegroundWindow(hwnd_consola)
            time.sleep(0.1)
    except Exception as e:
        print(f"  [!] No se pudo volver el foco a la consola: {e}")


# ---------------------------------------------------------------------------
# 2) Diccionarios de sinonimos / vocabulario del dominio
#    (fuente: docs/hotkeys_sfc2.md - Gold Edition)
# ---------------------------------------------------------------------------

# Velocidad: frase reconocida -> nivel logico (0 a 4). El nivel se traduce a
# pasos de teclado en STEPS_VELOCIDAD, mas abajo.
SPEED_WORDS = {
    # Detener / velocidad 0
    "alto total": 0, "parar": 0, "detener": 0, "pare maquinas": 0,
    "parada de emergencia": 0, "frenar": 0,
    # 1/4
    "cuarto de maquina": 1, "un cuarto de maquina": 1, "un cuarto": 1,
    # 1/2
    "media maquina": 2, "mitad de maquina": 2, "mitad": 2,
    # 3/4
    "tres cuartos de maquina": 3, "tres cuartos": 3,
    # Full
    "toda maquina": 4, "maxima velocidad": 4, "maxima": 4,
    "avante toda": 4, "velocidad maxima": 4,
}

# Cantidad aproximada de pulsaciones de S (o A si negativo) para llegar a cada
# nivel desde una posicion neutra/desconocida. Es una heuristica para validar
# el flujo end-to-end; no es precisa (ver nota de Fase 3 en el docstring).
STEPS_VELOCIDAD = {
    0: ("a", 8),   # frenar fuerte: varios A para asegurar que baje a 0
    1: ("s", 2),
    2: ("s", 4),
    3: ("s", 6),
    4: ("s", 8),
}

# Alertas
# IMPORTANTE: pydirectinput/pyautogui esperan los nombres de teclas de letras
# en MINUSCULA para su mapeo interno (KEYBOARD_MAPPING). Mandar 'R' en vez de
# 'r' puede fallar silenciosamente o no ser reconocido - este fue el bug real
# que causaba que "alerta roja" no funcionara pese a que el foco de ventana
# estaba correcto.
ALERT_WORDS = {
    "alerta roja": "r",
    "roja": "r",
    "red alert": "r",
}
# Nota: el manual de esta edicion no documenta una tecla dedicada de Yellow
# Alert (ver docs/hotkeys_sfc2.md) - a confirmar en el juego real.

# Disparo / armas
# Nota: "ataquen" a secas se saco de FIRE_WORDS porque colisionaba con el
# combo ALL_OUT_ATTACK_WORDS ("ataquen con todo") - ahora FIRE_WORDS requiere
# frases un poco mas especificas para disparo simple.
FIRE_WORDS = ["disparar", "fuego", "abran fuego", "dispare", "disparen"]
ALPHA_STRIKE_WORDS = ["alpha strike", "fuego total", "disparen todo",
                      "todas las armas", "fuego a discrecion"]

# Combo: "ataquen con todo" - maximiza ECM (para reducir el daño recibido
# mientras se hace el ataque) y despues dispara Alpha Strike (todas las
# armas de todos los hardpoints de una vez). Ver ALL_OUT_ATTACK_STEPS mas
# abajo, junto a los demas combos.
ALL_OUT_ATTACK_WORDS = ["ataquen con todo", "ataque total", "todo el poder de fuego",
                        "usen todas las armas", "fuego con todo"]

# Combo: "alejarse a maxima velocidad" - el juego no permite controlar el
# RUMBO por teclado (se hace con el mouse/waypoints, fuera del alcance de
# este proyecto por ahora), asi que se interpreta como acelerar a maxima
# velocidad nada mas (ignorando el "alejarse", que implicaria girar 180°).
RETREAT_WORDS = ["alejense a maxima velocidad", "alejarse a maxima velocidad",
                 "retirada a maxima velocidad", "huyan a maxima velocidad"]

# Escudos
SHIELD_MAX_WORDS = ["escudos al maximo", "reforzar escudos", "maximo escudo"]

# Camuflaje
CLOAK_WORDS = ["camuflaje", "cloaking", "activar camuflaje", "modo sigilo"]

# Deep Scan
DEEPSCAN_WORDS = ["escaneo profundo", "deep scan", "escanear"]

# Follow Target (Numpad *): seguir automaticamente al target seleccionado.
# El manual no distingue entre "nave" y "amenaza" - Follow Target sigue a lo
# que este seleccionado como target en ese momento (ver T/SHIFT+T/Y/SHIFT+Y
# para cambiar de target antes de seguir, si hiciera falta mas adelante).
FOLLOW_WORDS = [
    "seguir a esa nave", "seguir la nave", "seguir nave",
    "seguir a la amenaza", "seguir amenaza", "seguir al objetivo",
    "seguir objetivo", "seguir target", "sigan a esa nave",
    "sigan la nave", "persigan a esa nave", "perseguir nave",
]

# Cycle target (T): ciclar al proximo target disponible. Util decir esto
# antes de "seguir a esa nave" si el target actual no es el deseado.
NEXT_TARGET_WORDS = ["siguiente objetivo", "cambiar de blanco",
                     "cambiar objetivo", "proximo objetivo"]

# Target al enemigo mas cercano (backtick `)
NEAREST_ENEMY_WORDS = ["objetivo mas cercano", "enemigo mas cercano",
                       "apunten al mas cercano", "target mas cercano"]

# Pedir ayuda / listar comandos disponibles (no manda ninguna tecla al juego)
HELP_WORDS = ["que comandos hay", "ayuda", "que puedo decir",
             "lista de comandos", "mostrar comandos", "help"]


# ---------------------------------------------------------------------------
# Combos: una sola frase dispara VARIAS sub-acciones en secuencia. Cada combo
# es una lista de "pasos", donde cada paso es una tecla simple (str) o una
# tupla (tecla, cantidad_de_veces) para repetir una tecla N veces (ej. subir
# varios niveles de velocidad). El enfoque de ventana se hace UNA sola vez
# para todo el combo, no una vez por cada paso, para no repetir la pausa de
# 1 segundo (PAUSA_POST_ENFOQUE) mas de lo necesario.
# ---------------------------------------------------------------------------

COMBOS = {
    # "ataquen con todo": maximizar ECM (reduce el daño que recibimos
    # mientras atacamos) + Alpha Strike (disparar todas las armas de todos
    # los hardpoints a la vez).
    "ataque_total": {
        "palabras": ALL_OUT_ATTACK_WORDS,
        "pasos": ["f", ("shift+z", 1)],  # f = Max ECM, shift+z = Alpha Strike
        "descripcion": "Maximiza ECM y dispara Alpha Strike (todas las armas)",
    },
    # "alejense a maxima velocidad": acelerar al maximo (ver nota en
    # RETREAT_WORDS sobre por que no incluye giro de 180°).
    "retirada_maxima": {
        "palabras": RETREAT_WORDS,
        "pasos": [("s", 8)],  # 8x 's' = nivel de velocidad 4 (toda maquina)
        "descripcion": "Acelera a máxima velocidad (no gira la nave)",
    },
}


def listar_comandos():
    """Imprime en consola la lista de comandos disponibles, organizada por
    categoria, junto con un ejemplo de frase para cada uno. Se puede invocar
    diciendo/escribiendo cualquiera de las HELP_WORDS (ej. "ayuda")."""
    print("\n=== Comandos disponibles ===")
    print("(Decí o escribí una frase parecida a estos ejemplos)\n")

    print("VELOCIDAD:")
    print("  'alto total' / 'parar' / 'detener'          -> velocidad 0")
    print("  'cuarto de maquina'                          -> velocidad 25%")
    print("  'media maquina' / 'mitad'                    -> velocidad 50%")
    print("  'tres cuartos de maquina'                    -> velocidad 75%")
    print("  'toda maquina' / 'maxima velocidad'          -> velocidad 100%")

    print("\nARMAS:")
    print("  'disparar' / 'fuego' / 'abran fuego'         -> disparo simple")
    print("  'alpha strike' / 'fuego a discrecion'        -> disparar todo")
    print("  'objetivo mas cercano'                       -> target al enemigo mas cercano")
    print("  'siguiente objetivo' / 'cambiar de blanco'   -> ciclar target")
    print("  'seguir a esa nave' / 'seguir a la amenaza'  -> Follow Target")

    print("\nDEFENSA:")
    print("  'alerta roja'                                -> Red Alert")
    print("  'escudos al maximo'                          -> panel de escudos")
    print("  'camuflaje' / 'modo sigilo'                  -> toggle cloak")
    print("  'escaneo profundo' / 'deep scan'             -> toggle deep scan")

    print("\nCOMBOS (varias acciones en una sola orden):")
    for datos in COMBOS.values():
        ejemplo = datos["palabras"][0]
        print(f"  '{ejemplo}'  -> {datos['descripcion']}")

    print("\nOTROS:")
    print("  'ayuda' / 'que comandos hay'                 -> mostrar esta lista")
    print("  'salir' / 'exit'                              -> terminar el programa")
    print()


# ---------------------------------------------------------------------------
# 3) Parser: texto -> accion estructurada (dict)
# ---------------------------------------------------------------------------

def parsear_comando(texto):
    t = normalizar(texto)

    # Ayuda / listar comandos (se chequea primero, no manda tecla al juego)
    if any(contiene_frase(t, w) for w in HELP_WORDS):
        return {"action": "help", "raw": texto}

    # Combos (se chequean ANTES que los comandos individuales, porque son mas
    # especificos - ej. "ataquen con todo" no debe interpretarse como el
    # "disparar" simple de FIRE_WORDS)
    for nombre_combo, datos in COMBOS.items():
        if any(contiene_frase(t, w) for w in datos["palabras"]):
            return {"action": "combo", "combo": nombre_combo,
                    "pasos": datos["pasos"], "raw": texto}

    # Alpha strike (mas especifico, chequear antes que disparo simple)
    if any(contiene_frase(t, w) for w in ALPHA_STRIKE_WORDS):
        return {"action": "key_combo", "keys": ["shift", "z"], "raw": texto}

    # Disparo simple
    if any(contiene_frase(t, w) for w in FIRE_WORDS):
        return {"action": "key", "key": "z", "raw": texto}

    # Alertas
    for frase, tecla in ALERT_WORDS.items():
        if contiene_frase(t, frase):
            return {"action": "key", "key": tecla, "raw": texto}

    # Escudos al maximo
    if any(contiene_frase(t, w) for w in SHIELD_MAX_WORDS):
        return {"action": "key", "key": "k", "raw": texto}

    # Camuflaje
    if any(contiene_frase(t, w) for w in CLOAK_WORDS):
        return {"action": "key", "key": "x", "raw": texto}

    # Deep scan
    if any(contiene_frase(t, w) for w in DEEPSCAN_WORDS):
        return {"action": "key", "key": "i", "raw": texto}

    # Follow Target (Numpad *) - "multiply" es el nombre de tecla que espera
    # pydirectinput para el asterisco del teclado numerico.
    if any(contiene_frase(t, w) for w in FOLLOW_WORDS):
        return {"action": "key", "key": "multiply", "raw": texto}

    # Cycle target (T)
    if any(contiene_frase(t, w) for w in NEXT_TARGET_WORDS):
        return {"action": "key", "key": "t", "raw": texto}

    # Target al enemigo mas cercano (backtick)
    if any(contiene_frase(t, w) for w in NEAREST_ENEMY_WORDS):
        return {"action": "key", "key": "`", "raw": texto}

    # Velocidad con numero explicito: "velocidad al 70 por ciento" / "70%"
    m = re.search(r'(\d+)\s*(por ciento|%)', t)
    if m and contiene_frase(t, 'velocidad'):
        pct = int(m.group(1))
        return {"action": "set_speed_pct", "pct": pct, "raw": texto}

    # Velocidad por nivel con nombre (cuarto, media, etc.) - se chequea al
    # final porque frases cortas como "parar"/"frenar" podrian aparecer
    # dentro de oraciones mas largas de otros comandos.
    # Se ordena por longitud de frase descendente para priorizar matches
    # mas especificos (ej. "tres cuartos de maquina" antes que "tres cuartos").
    for frase, nivel in sorted(SPEED_WORDS.items(), key=lambda kv: -len(kv[0])):
        if contiene_frase(t, frase):
            return {"action": "set_speed", "level": nivel, "raw": texto}

    return {"action": "unknown", "raw": texto}


# ---------------------------------------------------------------------------
# 4) Ejecutor: accion estructurada -> pulsaciones reales de teclado
# ---------------------------------------------------------------------------

def _presionar_paso(paso, pausa_entre_teclas):
    """Ejecuta un paso individual de un combo. Un paso puede ser:
    - un string simple, ej. "f" -> press('f')
    - un string con "+", ej. "shift+z" -> keyDown/press/keyUp combinados
    - una tupla (tecla, cantidad) -> repetir esa tecla N veces
    """
    if isinstance(paso, tuple):
        tecla, cantidad = paso
        if "+" in tecla:
            modificador, tecla_final = tecla.split("+")
            for _ in range(cantidad):
                pydirectinput.keyDown(modificador)
                time.sleep(0.05)
                pydirectinput.press(tecla_final)
                time.sleep(0.05)
                pydirectinput.keyUp(modificador)
                time.sleep(pausa_entre_teclas)
        else:
            for _ in range(cantidad):
                pydirectinput.press(tecla)
                time.sleep(pausa_entre_teclas)
    else:
        if "+" in paso:
            modificador, tecla_final = paso.split("+")
            pydirectinput.keyDown(modificador)
            time.sleep(0.05)
            pydirectinput.press(tecla_final)
            time.sleep(0.05)
            pydirectinput.keyUp(modificador)
        else:
            pydirectinput.press(paso)
        time.sleep(pausa_entre_teclas)


def ejecutar_accion(accion, pausa_entre_teclas=0.15):
    tipo = accion.get("action")

    # Acciones que efectivamente mandan alguna tecla: enfocar el juego primero.
    # (help, set_speed_pct y unknown no mandan nada, no hace falta cambiar el foco)
    if tipo in ("key", "key_combo", "set_speed", "combo"):
        enfocado = enfocar_ventana_juego()
        if not enfocado:
            print("  [!] Se intenta mandar la tecla igual, pero puede que no "
                  "llegue al juego si el foco no quedo en la ventana correcta.")

    if tipo == "help":
        listar_comandos()

    elif tipo == "combo":
        nombre = accion["combo"]
        pasos = accion["pasos"]
        descripcion = COMBOS[nombre]["descripcion"]
        print(f"  -> Combo '{nombre}': {descripcion}")
        for paso in pasos:
            _presionar_paso(paso, pausa_entre_teclas)

    elif tipo == "key":
        tecla = accion["key"]
        print(f"  -> Tecla: {tecla}")
        pydirectinput.press(tecla)

    elif tipo == "key_combo":
        teclas = accion["keys"]
        print(f"  -> Combo: {'+'.join(teclas)}")
        pydirectinput.keyDown(teclas[0])
        time.sleep(0.05)
        pydirectinput.press(teclas[1])
        time.sleep(0.05)
        pydirectinput.keyUp(teclas[0])

    elif tipo == "set_speed":
        nivel = accion["level"]
        tecla, cantidad = STEPS_VELOCIDAD[nivel]
        print(f"  -> Velocidad nivel {nivel}: {cantidad}x tecla '{tecla}' "
              f"(aproximado, ver Fase 3 para precision real)")
        for _ in range(cantidad):
            pydirectinput.press(tecla)
            time.sleep(pausa_entre_teclas)

    elif tipo == "set_speed_pct":
        pct = accion["pct"]
        print(f"  -> Velocidad {pct}% solicitada, pero el conteo preciso de "
              f"pasos aun no esta implementado (pendiente Fase 3). "
              f"No se envia ninguna tecla por ahora.")

    elif tipo == "unknown":
        print(f"  -> Comando no reconocido: '{accion['raw']}'")

    else:
        print(f"  -> Tipo de accion desconocido: {tipo}")

    # Si se enfoco el juego para esta accion, volver el foco a la consola
    # para poder seguir escribiendo el proximo comando comodamente.
    if tipo in ("key", "key_combo", "set_speed", "combo"):
        enfocar_consola()


# ---------------------------------------------------------------------------
# 5) Loop principal
# ---------------------------------------------------------------------------

def main():
    # Import diferido (no a nivel de modulo) para evitar import circular:
    # llm_fallback importa catalogo_comandos, que a su vez importa este mismo
    # modulo (fase1_text_commands) para leer los diccionarios de comandos.
    usar_llm_fallback = True
    try:
        import llm_fallback
    except ImportError:
        usar_llm_fallback = False

    print("=== SFC Voice Commander - Fase 1: comandos por texto ===")
    print("Escribi un comando (ej: 'alerta roja', 'disparar', 'media maquina')")
    print("Escribi 'ayuda' para ver todos los comandos, 'salir' o 'exit' para terminar.\n")
    if usar_llm_fallback:
        print("(LLM fallback disponible: si el parser de reglas no reconoce "
              "una frase, se consulta a Ollama antes de darla por perdida)\n")

    while True:
        try:
            texto = input("Capitan, orden: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if not texto:
            continue
        if normalizar(texto) in ("salir", "exit", "quit"):
            print("Saliendo...")
            break

        accion = parsear_comando(texto)

        if accion["action"] == "unknown" and usar_llm_fallback:
            backend = llm_fallback.LLM_BACKEND
            print(f"  [parser de reglas no reconocio la frase, consultando "
                  f"al LLM (backend: {backend})...]")
            accion = llm_fallback.interpretar_con_llm(texto)

        ejecutar_accion(accion)


if __name__ == "__main__":
    main()
