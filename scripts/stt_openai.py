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
import re
import unicodedata

import soundfile as sf
from openai import OpenAI

import config

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
    "alerta roja, media maquina, cuarto de maquina, "
    "tres cuartos de maquina, toda maquina avante, alto total, "
    "fuego a discrecion, disparar, alpha strike, escudos al maximo, "
    "camuflaje, deep scan, ECM, ECCM, seguir a esa nave, "
    "siguiente objetivo, objetivo mas cercano, ataquen con todo."
)


# Cliente OpenAI cacheado a nivel de modulo.
#
# IMPORTANTE (fix de latencia): antes se creaba un cliente NUEVO en cada
# transcripcion. Crear el cliente es caro la primera vez (inicializa el SDK,
# el pool de conexiones HTTP, y sobre todo hace el handshake TLS + resolucion
# DNS contra la API de OpenAI la primera vez que se usa). Eso hacia que el
# PRIMER comando tuviera un delay notablemente mayor que los siguientes.
# Ahora se crea una sola vez y se reusa, y ademas se puede "precalentar" al
# arrancar el programa con precalentar() (ver mas abajo).
_cliente_cacheado = None


def _cliente():
    global _cliente_cacheado
    if _cliente_cacheado is None:
        _cliente_cacheado = OpenAI(api_key=config.api_key())
    return _cliente_cacheado


def _normalizar_para_comparar(texto):
    """Lowercase, no accents, no punctuation, single spaces."""
    texto = texto.lower().strip()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def es_eco_del_prompt(texto):
    """True when the model echoed PROMPT_VOCABULARIO back instead of
    transcribing speech.

    Seen live on 17/09: after a push-to-talk tap with no speech in it, the API
    answered with the vocabulary prompt word for word. That text ENDS with
    "ataquen con todo", so the rules parser matched it and fired the Alpha
    Strike combo on its own. Any transcription that is mostly prompt text has
    to be dropped before it reaches the parser.
    """
    t = _normalizar_para_comparar(texto)
    if not t:
        return False

    p = _normalizar_para_comparar(PROMPT_VOCABULARIO)

    # A long verbatim chunk of the prompt came back.
    if len(t) >= 40 and t in p:
        return True

    # Or almost every word of the answer belongs to the prompt. The threshold
    # is high on purpose: a real order is never this long.
    palabras = t.split()
    if len(palabras) >= 12:
        del_prompt = sum(1 for w in palabras if w in set(p.split()))
        if del_prompt / len(palabras) >= 0.85:
            return True

    return False


def obtener_cliente():
    """Public accessor to the cached client, so other modules (llm_fallback)
    reuse this same connection instead of opening a second one against the
    same API."""
    return _cliente()


def precalentar():
    """Inicializa el cliente y abre la conexion HTTPS con la API ANTES de que
    el usuario diga el primer comando, para que ese primer comando no pague
    el costo de inicializacion (handshake TLS, DNS, arranque del SDK).

    Se llama una sola vez al arrancar el script. Manda un audio minimo de
    silencio: es la forma de forzar que la conexion quede realmente
    establecida (crear el cliente solo no abre la conexion, el SDK es lazy).
    El costo de este audio es despreciable (~0.1 seg de silencio).

    Devuelve True si el precalentado funciono, False si fallo (no es
    critico: si falla, el programa sigue andando igual, solo que el primer
    comando volvera a ser mas lento).
    """
    try:
        import numpy as np
        silencio = np.zeros(int(16000 * 0.1), dtype=np.float32)
        # usar_prompt=False: silence + prompt makes the model echo the prompt
        # back, which printed a bogus warning on every startup.
        transcribir_openai(silencio, 16000, language="es", usar_prompt=False)
        return True
    except Exception as e:
        print(f"  [!] No se pudo precalentar la conexion con OpenAI: {e}")
        return False


def transcribir_openai(audio, sample_rate, language="es", usar_prompt=True):
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
            prompt=PROMPT_VOCABULARIO if usar_prompt else "",
            # temperature=0 -> transcripcion lo mas determinista posible, sin
            # que el modelo "improvise" palabras cuando el audio es ambiguo.
            temperature=0,
        )
        texto = respuesta.text.strip()
        if usar_prompt and es_eco_del_prompt(texto):
            print("  [!] La API devolvio el prompt de vocabulario en vez de "
                  "una transcripcion (audio sin voz). Se descarta.")
            return ""
        return texto
    except Exception as e:
        print(f"  [!] Error transcribiendo con OpenAI: {e}")
        return ""
