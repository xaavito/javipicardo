"""
Fase 0 - Script de prueba de inyeccion de teclado (SendInput via pydirectinput)

Objetivo: confirmar que se puede simular una tecla contra el juego
"Star Trek: Starfleet Command Gold Edition" corriendo en Windows (via DxWnd,
en modo ventana), y que el juego la recibe como si fuera un teclado fisico.

Como usar:
1. Instalar Python en la maquina Windows (si no esta instalado).
2. Instalar la dependencia:
       pip install pydirectinput
3. Abrir el juego DESDE DxWnd (doble click en el perfil configurado), esperar a
   que cargue, y entrar a una mision/tutorial donde la nave pueda moverse
   (ideal: Academy > primer tutorial, o cualquier mision simple).
4. Dejar la ventana del juego con el foco activo (click una vez sobre ella).
5. Correr este script:
       python fase0_test_key.py
6. Observar si la velocidad deseada de la nave (indicador "Desired Speed" del
   HUD) cambia al recibir las teclas S y A.

Resultado esperado si funciona: la velocidad deseada sube un paso con cada
pulsacion de S, y baja un paso con cada pulsacion de A.

Si NO funciona (no hay reaccion visible en el juego), ver ROADMAP.md seccion
Fase 0 para las alternativas: SendInput directo via ctypes, o AutoHotkey.
"""

import time
import pydirectinput

# Cuanto esperar antes de empezar a mandar teclas, para dar tiempo a
# hacer click en la ventana del juego y dejarla en foco.
SEGUNDOS_DE_ESPERA = 5

# Pausa entre pulsaciones sucesivas (pydirectinput ya tiene un delay por
# defecto, pero lo dejamos explicito para poder ajustarlo facil).
PAUSA_ENTRE_TECLAS = 0.5


def contar_regresivo(segundos):
    print(f"Tenes {segundos} segundos para hacer click en la ventana del juego "
          f"y dejarla en foco...")
    for i in range(segundos, 0, -1):
        print(f"  {i}...")
        time.sleep(1)


def main():
    contar_regresivo(SEGUNDOS_DE_ESPERA)

    print("Mandando tecla 'S' (Speed Up / acelerar) x3...")
    for _ in range(3):
        pydirectinput.press('s')
        time.sleep(PAUSA_ENTRE_TECLAS)

    print("Esperando 2 segundos...")
    time.sleep(2)

    print("Mandando tecla 'A' (Slow Down / desacelerar) x3...")
    for _ in range(3):
        pydirectinput.press('a')
        time.sleep(PAUSA_ENTRE_TECLAS)

    print("Listo. Revisa en el juego si la velocidad deseada (Desired Speed) "
          "subio y despues bajo durante la prueba.")


if __name__ == "__main__":
    main()
