"""
Guarda en disco el audio tal cual sale hacia OpenAI, para escucharlo despues.

Sirve para diagnosticar ordenes que no se toman: si el WAV guardado empieza o
termina cortado, el problema es el corte (VAD del browser o compuerta), no la
transcripcion. Cada envio queda en `grabaciones/` con fecha y modo en el
nombre, y `grabaciones/registro.txt` junta duracion y lo que se transcribio.

No hace falta ffmpeg: lo que se manda ya es WAV (modo web) o PCM16 crudo
(modo agente), y se escribe con soundfile / wave.
"""

import datetime
import os
import wave

import config

GUARDAR_AUDIO_ENVIADO = True
CARPETA = os.path.join(config.RAIZ, "grabaciones")


def _ruta(modo):
    os.makedirs(CARPETA, exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    return os.path.join(CARPETA, f"{marca}_{modo}.wav")


def _registrar(ruta, segundos, texto):
    linea = f"{os.path.basename(ruta)}\t{segundos:.2f}s\t{texto}\n"
    with open(os.path.join(CARPETA, "registro.txt"), "a", encoding="utf-8") as f:
        f.write(linea)


def guardar_wav(contenido, segundos, modo, texto=""):
    """Guarda los bytes de un WAV ya armado (lo mismo que se subio)."""
    if not GUARDAR_AUDIO_ENVIADO:
        return
    try:
        ruta = _ruta(modo)
        with open(ruta, "wb") as f:
            f.write(contenido)
        _registrar(ruta, segundos, texto)
    except Exception as e:
        # Que guardar nunca rompa la escucha
        print(f"  [!] No se pudo guardar el audio enviado: {e}")


def guardar_pcm16(pcm16, sample_rate, modo, texto=""):
    """Guarda PCM16 mono crudo (lo que la compuerta manda a la Realtime API)."""
    if not GUARDAR_AUDIO_ENVIADO:
        return
    try:
        ruta = _ruta(modo)
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm16)
        _registrar(ruta, len(pcm16) / 2 / sample_rate, texto)
    except Exception as e:
        print(f"  [!] No se pudo guardar el audio enviado: {e}")
