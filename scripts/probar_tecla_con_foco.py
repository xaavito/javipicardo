"""
Script de diagnostico - Fase 1 (parte 2)
Ya confirmamos que activate() SI trae la ventana "Starfleet Command" al frente
(foco real de Windows). Este script prueba mandar una tecla despues de eso,
con una pausa mas larga, y probando ademas con pyautogui como alternativa a
pydirectinput, para descartar diferencias entre ambas librerias.

Correr con: python probar_tecla_con_foco.py
(consola como Administrador, juego abierto via DxWnd, en una mision/tutorial
donde se pueda ver si la nave acelera)
"""

import time
import ctypes

import pygetwindow as gw
import pydirectinput

TITULO = "Starfleet Command"


def enfocar(v):
    hwnd = v._hWnd
    ctypes.windll.user32.BringWindowToTop(hwnd)
    ctypes.windll.user32.SetForegroundWindow(hwnd)


def main():
    ventanas = gw.getWindowsWithTitle(TITULO)
    if not ventanas:
        print(f"No se encontro ventana con titulo '{TITULO}'")
        return
    v = ventanas[0]

    print("Enfocando ventana...")
    enfocar(v)
    print("Esperando 2 segundos (pausa larga antes de mandar la tecla)...")
    time.sleep(2)

    print("Ventana activa ahora:", gw.getActiveWindow().title)

    print("\n--- Prueba A: pydirectinput.press('s') x5, con pausa larga ---")
    for i in range(5):
        pydirectinput.press('s')
        print(f"  tecla S enviada #{i+1}")
        time.sleep(0.5)

    print("\nRevisa el juego: la velocidad deseada debio subir 5 pasos.")
    print("Esperando 3 segundos antes de la siguiente prueba...")
    time.sleep(3)

    print("\n--- Prueba B: pydirectinput con keyDown/keyUp manual (en vez de press) ---")
    for i in range(5):
        pydirectinput.keyDown('s')
        time.sleep(0.05)
        pydirectinput.keyUp('s')
        print(f"  tecla S (keyDown/keyUp) enviada #{i+1}")
        time.sleep(0.5)

    print("\nRevisa el juego de nuevo: la velocidad debio subir 5 pasos mas.")


if __name__ == "__main__":
    main()
