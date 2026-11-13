"""
Genera docs/manual_comandos.md, el manual para jugar: todos los comandos, a
que oficial le tocan, que tecla aprietan y todas las frases que los activan.

Las frases salen de los diccionarios del parser (via catalogo_comandos), asi
que el manual nunca queda desactualizado: despues de agregar un sinonimo o un
comando, volver a correr

    python generar_manual.py

No necesita el juego ni pydirectinput: corre en cualquier lado.
"""

import os
import sys
import types

# catalogo_comandos importa fase1, que importa pydirectinput/pygetwindow
for _modulo in ("pydirectinput", "pygetwindow"):
    if _modulo not in sys.modules:
        try:
            __import__(_modulo)
        except ImportError:
            sys.modules[_modulo] = types.ModuleType(_modulo)

import catalogo_comandos as cc
import fase1_text_commands as fase1
import oficiales

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs",
                      "manual_comandos.md")

NOMBRE_TECLA = {
    "multiply": "`*` del teclado numérico",
    "subtract": "`-` del teclado numérico",
    "divide": "`/` del teclado numérico",
    "`": "`` ` `` (a la izquierda del 1)",
    "\\": "`\\`",
    "shift": "`Shift`",
    "ctrl": "`Ctrl`",
    "insert": "`Insert`",
}

ORDEN_OFICIALES = ["timon", "armas", "defensa", "ciencias", "computadora"]

PUESTO = {
    "timon": "Timón: velocidad y maniobras",
    "armas": "Armas: disparo y objetivos",
    "defensa": "Defensa: alertas, escudos y camuflaje",
    "ciencias": "Ciencias: sensores",
    "computadora": "Computadora: lo que no es de nadie",
}


def _tecla(t):
    return NOMBRE_TECLA.get(t, f"`{t.upper() if len(t) == 1 else t}`")


def _teclas_de(item):
    p = item["parametros"]
    if item["accion"] == "set_speed":
        tecla, veces = fase1.STEPS_VELOCIDAD[p["level"]]
        if p["level"] == 0:
            return f"{_tecla(tecla)} × {veces} (frena hasta 0)"
        return f"{_tecla(tecla)} × {veces} desde parado"
    if item["accion"] == "key":
        return _tecla(p["key"])
    if item["accion"] == "key_combo":
        return " + ".join(_tecla(t) for t in p["keys"])
    if item["accion"] == "combo":
        pasos = []
        for paso in fase1.COMBOS[p["combo"]]["pasos"]:
            if isinstance(paso, tuple):
                teclas = " + ".join(_tecla(t) for t in paso[0].split("+"))
                pasos.append(teclas if paso[1] == 1 else f"{teclas} × {paso[1]}")
            else:
                pasos.append(_tecla(paso))
        return ", después ".join(pasos)
    return ""


def _frases(lista):
    return " · ".join(f"«{f}»" for f in lista)


def _por_oficial():
    grupos = {}
    for item in cc.generar_catalogo():
        accion = cc.item_a_accion(item, "")
        grupos.setdefault(oficiales.oficial_para(accion), []).append(item)
    return grupos


def _llamado(clave):
    datos = oficiales.OFICIALES[clave]
    return ", ".join(f"*{a}*" for a in datos["alias"])


def _asignables():
    """Comandos que existen pero esperan que se les asigne tecla en el juego."""
    filas = [("Yellow Alert", "TECLA_YELLOW_ALERT", fase1.TECLA_YELLOW_ALERT,
              fase1.YELLOW_WORDS, "Sube escudos sin armar las armas."),
             ("Overload", "TECLA_OVERLOAD", fase1.TECLA_OVERLOAD,
              fase1.OVERLOAD_WORDS,
              "Armas pesadas en sobrecarga: más daño, alcance máximo 8, más "
              "energía."),
             ("Carga normal", "TECLA_ARMAS_NORMAL", fase1.TECLA_ARMAS_NORMAL,
              fase1.ARMAS_NORMAL_WORDS, "Saca el overload.")]
    return [f for f in filas if f[2] is None]


def generar():
    l = []
    w = l.append

    w("# Manual de comandos — SFC Voice Commander")
    w("")
    w("> Generado por `scripts/generar_manual.py` a partir de los diccionarios "
      "del parser. No editar a mano: agregar el sinónimo en "
      "`fase1_text_commands.py` y volver a generar.")
    w("")
    w("## Cómo se habla")
    w("")
    w("- **Primero el nombre, después la orden.** Toda orden empieza llamando a "
      "alguien: *«computadora, alerta roja»*, *«artillero, fuego»*, "
      "*«timonel, media máquina»*. Sin nombre no se ejecuta nada: así la "
      "charla del puente no dispara teclas.")
    w("- **La computadora atiende todo.** Si no sabés a quién le toca, "
      "llamala a ella. Igual contesta, con su voz y su retrato, el oficial "
      "del puesto de la orden.")
    w("- **Se llama por el puesto, no por el nombre propio.** El detector "
      "local (Vosk) no conoce *Korak*, *Zheva* ni *T'Lara*: decí *artillero*, "
      "*defensa* o *timonel*. Los nombres propios sólo sirven en los modos "
      "de fase 2.")
    w("- **Varias órdenes en una frase:** *«computadora, alerta roja y media "
      "máquina»*. Se ejecutan en orden; como mucho 5 por frase.")
    w("- **Lenguaje libre:** con el agente (`fase3_agente_voz.py`) no hace "
      "falta la frase exacta: *«poné la alarma y tirale con todo»* también "
      "anda. Las frases de abajo son las que el parser reconoce al instante y "
      "sin costo.")
    w("- **Si dudás, pregunta:** una palabra suelta como *«máquina»* o "
      "*«velocidad»* no se adivina; te pregunta cuál.")
    w("")
    w("## La tripulación")
    w("")
    w("| Puesto | Oficial | Se lo llama |")
    w("|---|---|---|")
    for clave in ORDEN_OFICIALES:
        datos = oficiales.OFICIALES[clave]
        w(f"| {PUESTO[clave].split(':')[0]} | {datos['nombre']} | "
          f"{_llamado(clave)} |")
    w("")
    w("Ingeniería, seguridad y comunicaciones todavía no tienen comandos.")
    w("")

    grupos = _por_oficial()
    for clave in ORDEN_OFICIALES:
        items = grupos.get(clave)
        if not items:
            continue
        datos = oficiales.OFICIALES[clave]
        w(f"## {PUESTO[clave]} ({datos['nombre']})")
        w("")
        for item in items:
            titulo = item["nombre_legible"].replace("_", " ").capitalize()
            w(f"### {titulo}")
            w("")
            w(f"{item['descripcion']}. Tecla: {_teclas_de(item)}.")
            w("")
            w(_frases(item["frases"]))
            w("")
        if clave == "timon":
            w("### Velocidad en porcentaje")
            w("")
            w("*«velocidad al 70 por ciento»*, *«velocidad 40%»*: se redondea "
              "al cuarto más cercano (0, 25, 50, 75 o 100%).")
            w("")
            w("> Las órdenes de velocidad mandan una cantidad fija de "
              "pulsaciones, calculada desde parado "
              f"({fase1.PASOS_HASTA_MAXIMA} hasta la máxima, "
              "`PASOS_HASTA_MAXIMA`, depende de la nave). Si la nave ya se "
              "movía, se suman: para un nivel exacto, primero *«alto total»*.")
            w("")

    asignables = _asignables()
    if asignables:
        w("## Comandos que esperan una tecla")
        w("")
        w("El juego no les asigna tecla por defecto. Asignales una en "
          "**Options → hotkeys** del juego y ponela en la constante de "
          "`fase1_text_commands.py`; hasta entonces, decirlos avisa y no hace "
          "nada.")
        w("")
        for nombre, constante, _, palabras, que in asignables:
            w(f"### {nombre}")
            w("")
            w(f"{que} Constante: `{constante}`.")
            w("")
            w(_frases(palabras))
            w("")

    w("## Otros")
    w("")
    w("- **Ayuda:** " + _frases(fase1.HELP_WORDS) + " — lista los comandos "
      "en la consola.")
    w("- **Llamar sin orden:** decir sólo el nombre (*«computadora»*) hace que "
      "conteste *«¿Sí, capitán?»* y espere.")
    w("- **Salir:** `Esc` en los modos de fase 2; `Ctrl+C` en el agente.")
    w("")
    w("## Jugadas útiles")
    w("")
    w("- **Perseguir a una nave concreta:** *«artillero, siguiente enemigo»* "
      "hasta que sea la que querés → *«artillero, guardar objetivo uno»* → "
      "en cualquier momento *«artillero, objetivo uno»* y *«timonel, seguir "
      "a esa nave»*.")
    w("- **Entrar al combate:** *«computadora, alerta roja y vamos al "
      "enemigo más cercano»*.")
    w("- **Golpe fuerte de cerca:** *«computadora, ataquen con todo»* (máximo "
      "ECM y Alpha Strike).")
    w("- **Salir del fuego:** *«timonel, maniobras evasivas»* (+4 de ECM, a "
      "costa de nuestra puntería) o *«timonel, aléjense a máxima "
      "velocidad»*.")
    w("")
    return "\n".join(l)


if __name__ == "__main__":
    texto = generar()
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"Manual generado: {os.path.abspath(SALIDA)}")
