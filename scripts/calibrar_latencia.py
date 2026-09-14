"""
Calibrador de latencia - encuentra los valores MINIMOS SEGUROS de
PAUSA_POST_ENFOQUE y PAUSA_ENTRE_TECLAS para esta maquina/juego.

POR QUE EXISTE ESTE SCRIPT
--------------------------
Los valores actuales (1.0s post-enfoque, 0.15s entre teclas) se eligieron de
forma CONSERVADORA en la Fase 0, no medida: se sabia que con 0.15s la tecla
no llegaba al juego, se probo 1.0s, funciono, y quedo asi. Pero el minimo
real puede ser bastante menor.

Esto importa porque PAUSA_POST_ENFOQUE se paga en CADA comando, y
PAUSA_ENTRE_TECLAS se paga hasta 8 veces en comandos de velocidad y combos.
Bajar la primera de 1.0 a 0.4 ahorra 0.6s en cada orden que des.

COMO USARLO
-----------
1. Abrir el juego DESDE DxWnd, en una mision donde la nave se pueda mover.
2. Correr DESDE UNA CONSOLA COMO ADMINISTRADOR:
       python calibrar_latencia.py
3. Va a probar pausas cada vez mas cortas, mandando teclas de velocidad
   (S/A) y preguntandote si la nave reacciono.
4. Al final te dice que valores poner en fase1_text_commands.py.

IMPORTANTE: mira la NAVE mientras corre, no la consola.
"""

import time

import fase1_text_commands as fase1

# Valores a probar, de mas seguro a mas agresivo.
PAUSAS_ENFOQUE = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
PAUSAS_TECLAS = [0.15, 0.10, 0.07, 0.05, 0.03]

# Repeticiones por prueba, para no fiarse de un solo intento.
REPETICIONES = 3


def _acelerar(nivel, pausa_teclas):
    fase1.ejecutar_accion(
        {"action": "set_speed", "level": nivel, "raw": "calibracion"},
        pausa_entre_teclas=pausa_teclas,
    )


def probar_pausa_enfoque(pausa):
    """Manda 4x 'S' con la pausa de enfoque dada. True si la nave reacciono
    en las REPETICIONES pruebas."""
    original = fase1.PAUSA_POST_ENFOQUE
    fase1.PAUSA_POST_ENFOQUE = pausa
    try:
        for i in range(REPETICIONES):
            print(f"\n  Intento {i + 1}/{REPETICIONES} con pausa={pausa}s")
            print("  Mando 4x 'S' (acelerar) en 2 seg... MIRA LA NAVE")
            time.sleep(2)
            _acelerar(2, 0.15)

            r = input("  ¿Acelero la nave? (s/n): ").strip().lower()
            if not r.startswith("s"):
                print("  -> Fallo: esta pausa es demasiado corta.")
                return False

            print("  Frenando para volver al estado inicial...")
            _acelerar(0, 0.15)
            time.sleep(1)
        return True
    finally:
        fase1.PAUSA_POST_ENFOQUE = original


def probar_pausa_teclas(pausa_teclas, pausa_enfoque_segura):
    """Manda 8x 'S' seguidas. Si el juego no procesa todas, la nave no llega
    a maxima - por eso se pregunta eso puntualmente."""
    original = fase1.PAUSA_POST_ENFOQUE
    fase1.PAUSA_POST_ENFOQUE = pausa_enfoque_segura
    try:
        print(f"\n  Probando pausa entre teclas = {pausa_teclas}s")
        print("  Primero frenamos del todo...")
        _acelerar(0, 0.15)
        time.sleep(1)

        print("  Mando 8x 'S' (a maxima) en 2 seg... MIRA LA NAVE")
        time.sleep(2)
        _acelerar(4, pausa_teclas)

        r = input("  ¿Llego a MAXIMA velocidad (8 pasos)? (s/n): ")
        return r.strip().lower().startswith("s")
    finally:
        fase1.PAUSA_POST_ENFOQUE = original


def main():
    print("=" * 68)
    print("CALIBRADOR DE LATENCIA - SFC Voice Commander")
    print("=" * 68)
    print(__doc__)

    if fase1.encontrar_ventana_juego() is None:
        print("\n[!] No se encontro la ventana del juego.")
        print("    Abri el juego DESDE DxWnd antes de correr esto.")
        return

    input("\nEnter para empezar (juego abierto, nave movible)... ")

    # --- Parte 1: PAUSA_POST_ENFOQUE ---
    print("\n" + "=" * 68)
    print("PARTE 1: pausa despues de enfocar la ventana")
    print("Se paga en CADA comando - es la que mas impacta.")
    print("=" * 68)

    mejor_enfoque = None
    for pausa in PAUSAS_ENFOQUE:
        print(f"\n--- Probando PAUSA_POST_ENFOQUE = {pausa}s ---")
        if probar_pausa_enfoque(pausa):
            mejor_enfoque = pausa
            print(f"  OK: {pausa}s funciona de forma consistente.")
        else:
            print(f"  {pausa}s NO es confiable. Corto la busqueda aca.")
            break

    if mejor_enfoque is None:
        print("\n[!] Ni 1.0s funciono - hay otro problema (¿consola como "
              "Administrador? ¿juego abierto desde DxWnd?)")
        return

    # --- Parte 2: PAUSA_ENTRE_TECLAS ---
    print("\n" + "=" * 68)
    print("PARTE 2: pausa entre teclas consecutivas")
    print("Se paga hasta 8 veces en comandos de velocidad y combos.")
    print("=" * 68)

    mejor_teclas = None
    for pausa in PAUSAS_TECLAS:
        if probar_pausa_teclas(pausa, mejor_enfoque):
            mejor_teclas = pausa
            print(f"  OK: {pausa}s entre teclas funciona.")
        else:
            print(f"  {pausa}s pierde teclas. Corto la busqueda aca.")
            break

    # --- Resultado ---
    print("\n" + "=" * 68)
    print("RESULTADO")
    print("=" * 68)
    print("\nPone estos valores en fase1_text_commands.py:\n")
    print(f"    PAUSA_POST_ENFOQUE = {mejor_enfoque}")
    if mejor_teclas:
        print(f"    PAUSA_ENTRE_TECLAS = {mejor_teclas}")

    ahorro = 1.0 - mejor_enfoque
    print(f"\nAhorro por comando (solo enfoque): {ahorro:.2f}s")
    if mejor_teclas:
        ahorro_8 = ahorro + (0.15 - mejor_teclas) * 8
        print(f"Ahorro en comandos de 8 teclas: {ahorro_8:.2f}s")

    print("\nSUGERENCIA: dejate margen. Si 0.3s funciono, poner 0.4s es mas")
    print("prudente que ir al limite exacto.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalibracion interrumpida.")
