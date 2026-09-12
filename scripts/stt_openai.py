"""
STT (Speech-to-Text) usando la API de Whisper de OpenAI, como alternativa al
Whisper local (faster-whisper) usado por defecto en fase2_voice_commands.py.

Ventaja principal: corre en los servidores de OpenAI (GPU), generalmente mas
rapido que un modelo local en CPU, ademas de mas preciso. Desventaja: requiere
internet y tiene un costo por uso (bajo - la API de Whisper cobra centavos de
dolar por minuto de audio transcripto).

------------------------------------------------------------------------
COMO CONFIGURAR LA API KEY (nunca hardcodear la key en el codigo):

En Windows, seteala como variable de entorno antes de correr el script:

    (PowerShell)
    $env:OPENAI_API_KEY = "sk-..."
    python fase2_voice_commands.py

    (CMD)
    set OPENAI_API_KEY=sk-...
    python fase2_voice_commands.py

O de forma permanente (para no tener que setearla en cada sesion de consola):
Panel de Control -> Sistema -> Configuracion avanzada del sistema ->
Variables de entorno -> Nueva variable de usuario: OPENAI_API_KEY = sk-...
(reiniciar la consola despues para que tome el cambio)

------------------------------------------------------------------------
COMO INSTALAR:
    pip install openai soundfile
"""

import io
import os

import soundfile as sf
from openai import OpenAI

# Modelo de transcripcion de OpenAI. "whisper-1" es el clasico; tambien
# existe "gpt-4o-transcribe" y "gpt-4o-mini-transcribe" (mas nuevos, revisar
# precios/disponibilidad en la documentacion de OpenAI si se quiere probar).
MODELO_STT = "whisper-1"


def _cliente():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No se encontro la variable de entorno OPENAI_API_KEY. Ver "
            "docstring de este archivo para como configurarla."
        )
    return OpenAI(api_key=api_key)


def transcribir_openai(audio, sample_rate, language="es"):
    """Recibe un array numpy float32 (mono) con el audio grabado y devuelve
    el texto transcripto usando la API de Whisper de OpenAI. Si audio esta
    vacio, devuelve "" sin llamar a la API."""
    if audio.size == 0:
        return ""

    cliente = _cliente()

    # La API espera un archivo de audio (wav, mp3, etc.), no un array crudo -
    # se arma un WAV en memoria con soundfile, sin necesidad de guardar nada
    # a disco.
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV")
    buffer.seek(0)
    buffer.name = "audio.wav"  # la libreria de OpenAI usa esto para el mimetype

    try:
        respuesta = cliente.audio.transcriptions.create(
            model=MODELO_STT,
            file=buffer,
            language=language,
        )
        return respuesta.text.strip()
    except Exception as e:
        print(f"  [!] Error transcribiendo con OpenAI: {e}")
        return ""
