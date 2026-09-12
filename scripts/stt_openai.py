"""
STT (Speech-to-Text) usando la API de Whisper de OpenAI, como alternativa al
Whisper local (faster-whisper) usado por defecto en fase2_voice_commands.py.

Ventaja principal: corre en los servidores de OpenAI (GPU), generalmente mas
rapido que un modelo local en CPU, ademas de mas preciso. Desventaja: requiere
internet y tiene un costo por uso (bajo - cobra centavos de dolar por minuto
de audio transcripto).

Alineado con la guia oficial de Speech-to-Text de OpenAI
(https://developers.openai.com/api/docs/guides/speech-to-text):
- usa el modelo `gpt-4o-mini-transcribe` (mas nuevo/preciso/barato que
  `whisper-1`), ver MODELO_STT.
- usa el parametro `prompt` para sesgar la transcripcion hacia el vocabulario
  especifico del juego, ver PROMPT_VOCABULARIO.

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

# Modelo de transcripcion de OpenAI.
# - "gpt-4o-mini-transcribe" (ACTUAL): mas nuevo, mas preciso y mas barato que
#   whisper-1, y es el que recomienda la guia oficial de Speech-to-Text de
#   OpenAI. Para comandos cortos como los de este proyecto es la mejor
#   relacion precision/latencia/costo.
# - "gpt-4o-transcribe": misma familia, mas preciso todavia pero mas caro y
#   algo mas lento. Probar solo si el mini se queda corto.
# - "whisper-1": el clasico (era el que usaba este script antes). Se deja
#   documentado como fallback por si hiciera falta volver atras.
MODELO_STT = "gpt-4o-mini-transcribe"

# Vocabulario del dominio para sesgar la transcripcion (parametro `prompt` de
# la API, documentado en la guia oficial de Speech-to-Text como "prompting" /
# vocabulary biasing). Sirve para que el STT no destroce terminos propios del
# juego y la jerga naval/Star Trek que usamos como comandos: sin esto, es
# comun que "media maquina" salga como "media manzana", o que "ECM" salga
# como "eceeme".
#
# Limite: la ventana de prompt del STT es de ~224 tokens - no meter la lista
# completa de comandos, solo los terminos que MAS se confunden al transcribir.
PROMPT_VOCABULARIO = (
    "Comandos de nave de Star Trek: Starfleet Command. "
    "alerta roja, alerta amarilla, media maquina, cuarto de maquina, "
    "tres cuartos de maquina, toda maquina avante, alto total, "
    "fuego a discrecion, disparar, alpha strike, escudos al maximo, "
    "camuflaje, deep scan, ECM, ECCM, seguir a esa nave, "
    "siguiente objetivo, objetivo mas cercano, ataquen con todo."
)


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
            # Sesga la transcripcion hacia el vocabulario del juego (ver
            # PROMPT_VOCABULARIO). Mejora notablemente el reconocimiento de
            # terminos como "media maquina" o "ECCM" sin costo extra de
            # latencia.
            prompt=PROMPT_VOCABULARIO,
            # temperature=0 -> transcripcion lo mas determinista posible, sin
            # que el modelo "improvise" palabras cuando el audio es ambiguo.
            temperature=0,
        )
        return respuesta.text.strip()
    except Exception as e:
        print(f"  [!] Error transcribiendo con OpenAI: {e}")
        return ""
