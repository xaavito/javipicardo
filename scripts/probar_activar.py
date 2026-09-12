"""
Script de diagnostico - Fase 1
Prueba si pygetwindow.activate() realmente deja el foco de teclado en la
ventana del juego "Starfleet Command", y compara contra SetForegroundWindow
directo via ctypes como alternativa mas confiable.

Correr con: python probar_activar.py
(consola como Administrador, juego abierto via DxWnd)
"""

import time
import ctypes

import pygetwindow as gw

TITULO = "Starfleet Command"


def main():
    ventanas = gw.getWindowsWithTitle(TITULO)
    if not ventanas:
        print(f"No se encontro ninguna ventana con titulo exacto '{TITULO}'")
        return

    v = ventanas[0]
    print(f"Ventana encontrada: {v.title!r} (hwnd={v._hWnd})")

    print("\n--- Prueba 1: pygetwindow activate() ---")
    try:
        v.activate()
    except Exception as e:
        print(f"Error en activate(): {e}")
    time.sleep(1)
    activa = gw.getActiveWindow()
    print(f"Ventana activa segun pygetwindow: {activa.title if activa else None}")

    print("\n--- Prueba 2: ctypes SetForegroundWindow directo ---")
    hwnd = v._hWnd
    resultado = ctypes.windll.user32.SetForegroundWindow(hwnd)
    print(f"SetForegroundWindow devolvio: {resultado} (0 = fallo, distinto de 0 = ok)")
    time.sleep(1)
    activa2 = gw.getActiveWindow()
    print(f"Ventana activa segun pygetwindow: {activa2.title if activa2 else None}")

    print("\n--- Prueba 3: BringWindowToTop + SetForegroundWindow combinados ---")
    ctypes.windll.user32.BringWindowToTop(hwnd)
    resultado2 = ctypes.windll.user32.SetForegroundWindow(hwnd)
    print(f"SetForegroundWindow devolvio: {resultado2}")
    time.sleep(1)
    activa3 = gw.getActiveWindow()
    print(f"Ventana activa segun pygetwindow: {activa3.title if activa3 else None}")


if __name__ == "__main__":
    main()
