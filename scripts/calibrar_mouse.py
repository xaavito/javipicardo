"""
Calibrador del mouse - para fijar los numeros de fase1_text_commands.py que
NO se pueden medir desde la Mac: la posicion de la nave en pantalla, el radio
del rumbo, y la posicion de los botones del MFD. Corre en la Windows, con el
juego abierto via DxWnd (ver PRUEBAS #30).

QUE HACE: te muestra la geometria de la ventana del juego y, cada vez que
apretas Enter, lee donde esta el cursor y lo imprime en coordenadas RELATIVAS
a la esquina superior-izquierda de la ventana (que es como las espera fase1).

COMO USARLO:
  1. Abri el juego (ventana), ponelo como lo vas a jugar.
  2. python scripts/calibrar_mouse.py   (consola como Administrador)
  3. Segui lo que pide en pantalla: llevas el mouse al punto, apretas Enter.

Al final te imprime las lineas listas para pegar en fase1_text_commands.py:
  NAVE_CENTRO_REL, RUMBO_RADIO y BOTONES_MFD.
"""

import ctypes
import ctypes.wintypes
import math

import pygetwindow as gw

WINDOW_TITLE_EXACTO = "Starfleet Command"
WINDOW_TITLE_KEYWORDS = ["starfleet", "star trek", "dxwnd"]


def encontrar_ventana():
    objetivo = WINDOW_TITLE_EXACTO.strip().lower()
    for v in gw.getAllWindows():
        if (v.title or "").strip().lower() == objetivo:
            return v
    for v in gw.getAllWindows():
        t = (v.title or "").lower()
        if t and any(kw in t for kw in WINDOW_TITLE_KEYWORDS):
            return v
    return None


def pos_cursor():
    """(x, y) absolutos del cursor, via Win32 GetCursorPos."""
    punto = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(punto))
    return punto.x, punto.y


def pedir_punto(ventana, texto):
    input(f"\n{texto}\n  -> llevá el mouse ahí y apretá Enter...")
    ax, ay = pos_cursor()
    rel = (ax - ventana.left, ay - ventana.top)
    print(f"     abs=({ax},{ay})  rel a la ventana={rel}")
    return rel


def main():
    ventana = encontrar_ventana()
    if ventana is None:
        print("No se encontro la ventana del juego. Abri el juego primero.")
        return

    print(f"Ventana: left={ventana.left} top={ventana.top} "
          f"width={ventana.width} height={ventana.height}")
    centro_ventana = (ventana.width // 2, ventana.height // 2)
    print(f"Centro de la ventana (rel): {centro_ventana}")

    nave = pedir_punto(ventana, "1) La NAVE propia en el mapa tactico.")
    proa = pedir_punto(ventana, "2) Un punto 'a las 12' (derecho hacia la proa, "
                                "lo mas lejos que clickearias un rumbo).")

    radio = int(round(math.hypot(proa[0] - nave[0], proa[1] - nave[1])))

    intercept = pedir_punto(ventana, "3) El boton INTERCEPT del Helm MFD "
                                     "(abri el Helm con ' primero).")
    yellow = pedir_punto(ventana, "4) El boton YELLOW ALERT del HUD.")

    # Si la nave esta ~en el centro, conviene dejar NAVE_CENTRO_REL = None.
    cerca_centro = (abs(nave[0] - centro_ventana[0]) < 10
                    and abs(nave[1] - centro_ventana[1]) < 10)

    print("\n" + "=" * 60)
    print("Pegá esto en fase1_text_commands.py:\n")
    if cerca_centro:
        print("NAVE_CENTRO_REL = None  # la nave coincide con el centro")
    else:
        print(f"NAVE_CENTRO_REL = {nave}")
    print(f"RUMBO_RADIO = {radio}")
    print("BOTONES_MFD = {")
    print(f'    "intercept": {intercept},')
    print(f'    "yellow_alert": {yellow},')
    print("}")
    print("=" * 60)


if __name__ == "__main__":
    main()
