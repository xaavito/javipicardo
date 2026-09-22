"""
Diagnostico de microfono: que dispositivos hay, cual se esta usando, y si de
verdad esta entrando audio.

POR QUE EXISTE
--------------
Cuando el STT no entiende nada, hay tres causas posibles y desde la consola de
fase2 no se distinguen: (1) el microfono no captura, (2) captura pero de otro
dispositivo, (3) captura bien y el problema es el STT. Esto separa las tres.

El caso tipico es un auricular Bluetooth. Windows expone CADA auricular BT como
DOS dispositivos distintos:
  - "Auriculares (Stereo)"    -> perfil A2DP: buen sonido, SIN microfono
  - "Auriculares (Hands-Free)" -> perfil HFP:  hay microfono, pero el sonido de
                                  salida baja a calidad telefono
Si Windows quedo en el perfil A2DP, el microfono simplemente no existe para las
aplicaciones, y grabas silencio sin ningun error.

COMO USAR
---------
    python probar_microfono.py            lista los dispositivos y graba del default
    python probar_microfono.py 3          graba del dispositivo numero 3
    python probar_microfono.py --lista    solo lista, no graba

Mientras graba, HABLA. La barra de nivel tiene que moverse.
"""

import sys

import numpy as np
import sounddevice as sd

SEGUNDOS = 4
SAMPLE_RATE = 16000  # el mismo que usa fase2_voice_commands.py
CANALES = 1

# Debajo de esto, lo grabado es silencio o ruido de fondo, no voz.
UMBRAL_VOZ_DBFS = -45.0


def listar():
    print("\n=== Dispositivos de entrada disponibles ===\n")
    try:
        default_in = sd.default.device[0]
    except Exception:
        default_in = None

    hay = False
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] < 1:
            continue
        hay = True
        marca = " <-- DEFAULT" if i == default_in else ""
        print(f"  [{i}] {d['name']}")
        print(f"       canales={d['max_input_channels']} "
              f"rate nativo={int(d['default_samplerate'])} Hz{marca}")

        # Un BT en perfil A2DP aparece sin canales de entrada, o directamente
        # no aparece: por eso conviene ver la lista entera.
        try:
            sd.check_input_settings(device=i, samplerate=SAMPLE_RATE,
                                    channels=CANALES, dtype="float32")
            print(f"       16000 Hz mono: OK")
        except Exception as e:
            print(f"       16000 Hz mono: NO ({type(e).__name__}) "
                  f"<-- fase2 no va a poder usar este")
    if not hay:
        print("  (ninguno)")
        print("\n  [!] No hay NINGUN dispositivo de entrada. Si tenes un "
              "auricular Bluetooth,\n      casi seguro esta en perfil A2DP: "
              "ver el encabezado de este archivo.")


def barra(dbfs):
    if dbfs < -60:
        n = 0
    else:
        n = int((dbfs + 60) / 60 * 30)
    return "#" * n + "." * (30 - n)


def grabar(dispositivo):
    nombre = "default"
    if dispositivo is not None:
        try:
            nombre = sd.query_devices(dispositivo)["name"]
        except Exception:
            pass

    print(f"\n=== Grabando {SEGUNDOS}s de '{nombre}' — HABLA AHORA ===\n")

    bloques = []

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  [!] aviso: {status}")
        bloques.append(indata.copy())
        pico = float(np.max(np.abs(indata))) if indata.size else 0.0
        db = 20 * np.log10(pico) if pico > 0 else -99.0
        print(f"\r  nivel [{barra(db)}] {db:6.1f} dBFS", end="", flush=True)

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CANALES,
                            dtype="float32", device=dispositivo,
                            callback=callback, blocksize=int(SAMPLE_RATE / 10)):
            sd.sleep(int(SEGUNDOS * 1000))
    except Exception as e:
        print(f"\n\n  [!] No se pudo abrir el dispositivo: "
              f"{type(e).__name__}: {e}")
        return 1

    print("\n")
    if not bloques:
        print("  [!] No llego NINGUN bloque de audio.")
        return 1

    audio = np.concatenate(bloques, axis=0).flatten()
    rms = float(np.sqrt(np.mean(audio ** 2)))
    pico = float(np.max(np.abs(audio)))
    db_rms = 20 * np.log10(rms) if rms > 0 else -99.0
    db_pico = 20 * np.log10(pico) if pico > 0 else -99.0

    print(f"  muestras: {audio.size} ({audio.size / SAMPLE_RATE:.1f}s)")
    print(f"  RMS:  {db_rms:6.1f} dBFS")
    print(f"  pico: {db_pico:6.1f} dBFS\n")

    if db_pico <= -90:
        print("  RESULTADO: SILENCIO ABSOLUTO. El dispositivo abrio pero no")
        print("  entra nada. Si es Bluetooth, es el perfil A2DP (ver arriba).")
        print("  Si no, revisa Configuracion > Privacidad > Microfono.")
        return 1
    if db_rms < UMBRAL_VOZ_DBFS:
        print("  RESULTADO: entra algo, pero muy bajo — parece ruido de fondo")
        print("  y no voz. Subi el volumen del microfono en Windows, o")
        print("  acercate mas, y volve a probar.")
        return 1

    print("  RESULTADO: OK, el microfono captura voz.")
    print("  Si fase2 igual no entiende, el problema no es el microfono.")
    if dispositivo is not None:
        print(f"\n  Para que fase2 use este: poner en fase2_voice_commands.py")
        print(f"      DISPOSITIVO_ENTRADA = {dispositivo}")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    listar()

    if "--lista" in sys.argv:
        return 0

    dispositivo = int(args[0]) if args else None
    return grabar(dispositivo)


if __name__ == "__main__":
    sys.exit(main())
