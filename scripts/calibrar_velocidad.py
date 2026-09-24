"""
Mide cuantas pulsaciones de "s" hay desde velocidad 0 hasta la maxima de la
nave, que es el dato que le falta a los comandos de velocidad.

POR QUE
-------
"media maquina" y "velocidad al 70 por ciento" mandan N pulsaciones de "s" a
ciegas. Cuantas hacen falta depende de la nave, y nunca se midio: el valor 8
se eligio a ojo en la Fase 1. Por eso el 24/09 "velocidad al 70 por ciento" no
llegaba a 3/4.

Esto no reemplaza a la Fase 3 (leer el HUD por OCR): es el enfoque simplificado
que el README ya proponia, pero con el numero medido en vez de inventado.

COMO USAR
---------
1. Juego abierto DESDE DxWnd, nave libre de moverse, fuera de combate, con el
   indicador de velocidad a la vista.
2. Consola COMO ADMINISTRADOR:
       python calibrar_velocidad.py
3. Mira el HUD y segui las instrucciones.

OJO: la velocidad maxima cambia segun la nave. Si jugas varias clases muy
distintas, conviene medir con la que mas uses.
"""

import sys
import time

import fase1_text_commands as fase1


def main():
    print(__doc__)
    input("Enter cuando el juego este abierto y la nave libre de moverse...")

    print("\n[1/3] Frenando a cero (15x 'a')...")
    fase1.enfocar_ventana_juego()
    for _ in range(15):
        fase1.pydirectinput.press("a")
        time.sleep(fase1.PAUSA_ENTRE_TECLAS)
    fase1.enfocar_consola()

    r = input("  ¿La nave quedo DETENIDA del todo? (s/n): ").strip().lower()
    if not r.startswith("s"):
        print("  Si no llego a cero, algo mas esta pasando. Abortando.")
        return 1

    print("\n[2/3] Ahora voy a acelerar de a UNA pulsacion.")
    print("  Mira el indicador de velocidad y deci 'n' cuando deje de subir")
    print("  (o sea, cuando ya este en la maxima).\n")

    pasos = 0
    for intento in range(1, 41):
        fase1.enfocar_ventana_juego()
        fase1.pydirectinput.press("s")
        fase1.enfocar_consola()
        r = input(f"  pulsacion {intento}: ¿SUBIO la velocidad? (s/n): ")
        if not r.strip().lower().startswith("s"):
            pasos = intento - 1
            break
        pasos = intento
    else:
        print("  40 pulsaciones y seguia subiendo, algo raro. Abortando.")
        return 1

    print(f"\n[3/3] RESULTADO: {pasos} pulsaciones de 0 a maxima.\n")
    print("Pone esto en fase1_text_commands.py:\n")
    print(f"    PASOS_HASTA_MAXIMA = {pasos}\n")
    print("Con ese valor, los niveles quedan asi:")
    tope = pasos
    for nivel, nombre in [(1, "cuarto"), (2, "media"), (3, "tres cuartos"),
                          (4, "toda maquina")]:
        pct = [0, 25, 50, 75, 100][nivel]
        print(f"    {nombre:14} ({pct:3}%) -> {max(1, round(tope * pct / 100))}x 's'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
