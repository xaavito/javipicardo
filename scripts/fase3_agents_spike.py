"""
Fase 3 - Spike del Agents SDK (Opcion 1: Python server-side).

QUE ES ESTO: un spike, no la implementacion. Lo minimo para contestar las
preguntas de PRUEBAS.md #29, aunque despues se tire el codigo. Si al terminar
sabemos las respuestas, salio bien.

QUE HACE, Y NADA MAS: decir "alerta roja" por voz y que la tecla 'r' llegue al
juego, pasando por el agente. UNA sola tool. Sin oficiales, sin panel, sin
encadenado.

------------------------------------------------------------------------
LA ARQUITECTURA (Opcion 1, decidida con Javi el 26/10):

  microfono --(sounddevice)--> RealtimeAgent en Python --(tool)--> ejecutar_accion
      ^                         (gpt-realtime-2.1, WebSocket)            |
      |                                                                  v
  parlante <----- audio del oficial (eventos 'audio') <------- la tecla al juego

  - El SDK de Python (openai-agents) corre la sesion Realtime por WebSocket del
    lado del server. NO tiene transporte WebRTC de browser (eso es solo el SDK
    de TS). Por eso el audio lo capturamos nosotros con sounddevice y se lo
    pasamos con session.send_audio(); el browser queda fuera del camino de audio.
  - El transporte de audio propio que habiamos escrito (POST de PCM a /voz) no
    hace falta: lo reemplaza send_audio() del SDK, no WebRTC.
  - La inyeccion de teclas sigue en Python como Administrador (ejecutar_accion),
    igual que siempre.

  La Opcion 2 (browser + WebRTC con el SDK de TS + un servicio Python de teclas)
  NO se descarta: queda anotada en WISHLIST.md como alternativa si alguna vez
  queremos el audio en el browser. Este spike explora la 1.

LAS "DOS TRAMPAS" DE PATO (mismo call_id + response.create): las resuelve el
SDK solo. Cuando el modelo pide una tool, el RealtimeRunner la ejecuta, devuelve
el resultado con el call_id correcto y dispara la respuesta. Por eso usamos el
SDK y no la Realtime API cruda: esa plomeria es exactamente lo que nos ahorra.

------------------------------------------------------------------------
COMO INSTALAR (en la maquina Windows, consola como Administrador):

    pip install "openai-agents" sounddevice numpy

  - openai-agents: el SDK. Trae RealtimeAgent / RealtimeRunner.
  - sounddevice + numpy: captura de microfono y reproduccion del parlante
    (el quickstart del SDK NO incluye esto a proposito; es lo que ponemos aca).
  - pydirectinput: ya instalado de las fases anteriores (para apretar la tecla).

  La OPENAI_API_KEY sale de config.py (variable de entorno o .env), igual que
  el resto de los scripts.

------------------------------------------------------------------------
COMO CORRERLO:

  En la Mac (sin pydirectinput ni micro configurado), para validar que el modulo
  arma bien y que la tool dispara el mock de la tecla:

      python scripts/fase3_agents_spike.py --self-test

  En la Windows, el spike de verdad (habla y escucha):

      python scripts/fase3_agents_spike.py

------------------------------------------------------------------------
A VERIFICAR AL INSTALAR (no lo pude confirmar desde la Mac, la doc no lo fija):
  - El import exacto del decorador de tools: aca uso `from agents import
    function_tool`, que es el estandar del SDK. Si pip trajo otra forma
    (`from agents.decorators import tool`), ajustar las 2 lineas marcadas con
    [VERIFICAR-IMPORT].
  - Los campos del evento 'audio': uso event.audio para los bytes de salida.
    Si el payload los expone con otro nombre, ajustar _reproducir() (marcado
    con [VERIFICAR-AUDIO]).
"""

import argparse
import asyncio
import sys

import config

# --- Parametros de audio de la Realtime API --------------------------------
# La Realtime API trabaja en PCM16, mono, 24 kHz. No cambiar sin motivo.
SAMPLE_RATE = 24000
CANALES = 1
DTYPE = "int16"
# Tamanio del bloque que mandamos por vez. 20 ms a 24 kHz = 480 muestras.
BLOQUE = 480

MODELO = "gpt-realtime-2.1"
VOZ = "ash"
MODELO_STT = "gpt-4o-mini-transcribe"  # transcripcion dentro de la sesion

# Mismo vocabulary biasing que stt_openai.PROMPT_VOCABULARIO, acotado a lo del
# spike (el turno es una sola orden). Si crece, importarlo de alla.
PROMPT_VOCABULARIO = "alerta roja, escudos, fasers, torpedos, media maquina, ECCM"

INSTRUCCIONES = (
    "Sos el oficial tactico de una nave estelar. Cuando el capitan de una "
    "orden, ejecutala con la herramienta que corresponda y confirma en una "
    "frase corta, en espaniol. No inventes ordenes que no existan."
)


# ---------------------------------------------------------------------------
# 1) La capa de teclas: real en Windows, mock en la Mac
# ---------------------------------------------------------------------------
# fase1_text_commands importa pydirectinput a nivel de modulo, que no existe en
# la Mac. Si el import falla, caemos a un mock que solo imprime: asi el spike
# se puede validar aca sin tocar el juego.

try:
    from fase1_text_commands import ejecutar_accion
    MOCK_TECLAS = False
except ImportError:
    MOCK_TECLAS = True

    def ejecutar_accion(accion, **kwargs):
        print(f"  [MOCK tecla] ejecutar_accion({accion})")


def _alerta_roja_impl():
    """La accion real detras de la tool: mandar la tecla 'r' al juego."""
    # responder=False: en el spike contesta el modelo de voz, no los oficiales.
    ejecutar_accion({"action": "key", "key": "r"}, responder=False)
    return "Alerta roja activada."


# ---------------------------------------------------------------------------
# 2) La tool, tal como la ve el agente
# ---------------------------------------------------------------------------

def _definir_tool():
    # [VERIFICAR-IMPORT]: estandar del SDK. Ver cabecera si pip trajo otra forma.
    from agents import function_tool

    @function_tool
    def alerta_roja() -> str:
        """Pone la nave en alerta roja (sube escudos y arma las fasers)."""
        return _alerta_roja_impl()

    return alerta_roja


# ---------------------------------------------------------------------------
# 3) Self-test: sin audio, para validar en la Mac con mocks (clinerules)
# ---------------------------------------------------------------------------

def self_test():
    print("=== Self-test del spike (sin audio) ===")
    print(f"  Capa de teclas: {'MOCK (sin pydirectinput)' if MOCK_TECLAS else 'REAL'}")

    # El SDK (openai-agents) no esta en la Mac, igual que openai/pydirectinput:
    # intentar definir la tool es informativo, no debe hacer fallar el self-test.
    try:
        tool = _definir_tool()
        print(f"  Tool definida: {getattr(tool, 'name', tool)!r}")
    except ModuleNotFoundError:
        print("  Tool: SDK 'openai-agents' no instalado (se valida en la Windows).")

    print("  Disparo manual de la accion (lo que el agente correria):")
    resultado = _alerta_roja_impl()
    print(f"  -> resultado: {resultado!r}")
    print("OK: el modulo arma y la tecla dispara por la capa de teclas.")


# ---------------------------------------------------------------------------
# 4) El spike de verdad: voz en Windows
# ---------------------------------------------------------------------------

async def correr_spike():
    import numpy as np
    import sounddevice as sd
    from agents import RealtimeAgent, RealtimeRunner

    clave = config.api_key()  # tira RuntimeError con instrucciones si falta

    agente = RealtimeAgent(
        name="Tactico",
        instructions=INSTRUCCIONES,
        tools=[_definir_tool()],
    )

    runner = RealtimeRunner(
        starting_agent=agente,
        config={
            "model_settings": {
                "model_name": MODELO,
                "api_key": clave,
                "audio": {
                    "input": {
                        "format": "pcm16",
                        "transcription": {
                            "model": MODELO_STT,
                            "prompt": PROMPT_VOCABULARIO,
                        },
                        # semantic_vad + interrupt_response = barge-in de fabrica:
                        # podes hablarle encima y se calla (fila 'Interrupcion' #29).
                        "turn_detection": {
                            "type": "semantic_vad",
                            "interrupt_response": True,
                        },
                    },
                    "output": {"format": "pcm16", "voice": VOZ},
                },
            }
        },
    )

    session = await runner.run()

    # Cola de audio de salida: los eventos 'audio' empujan bytes, el stream de
    # salida los consume. Se vacia en 'audio_interrupted' (barge-in).
    cola_salida = asyncio.Queue()

    # --- Captura de microfono: manda cada bloque con send_audio() ---
    async def capturar_micro():
        loop = asyncio.get_running_loop()
        q = asyncio.Queue()

        def cb(indata, frames, t, status):
            if status:
                print(f"  [audio-in] {status}", file=sys.stderr)
            loop.call_soon_threadsafe(q.put_nowait, bytes(indata))

        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOQUE,
                               channels=CANALES, dtype=DTYPE, callback=cb):
            print("  Micro abierto. Deci 'alerta roja'. Ctrl+C para cortar.")
            while True:
                chunk = await q.get()
                await session.send_audio(chunk)

    # --- Reproduccion del parlante: consume la cola de salida ---
    async def reproducir():
        with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=CANALES,
                                dtype=DTYPE) as stream:
            while True:
                chunk = await cola_salida.get()
                if chunk is None:
                    continue
                await asyncio.to_thread(stream.write, chunk)

    # --- Loop de eventos de la sesion ---
    async def consumir_eventos():
        async for event in session:
            tipo = event.type
            if tipo == "audio":
                # [VERIFICAR-AUDIO]: bytes de salida del oficial.
                await cola_salida.put(event.audio)
            elif tipo == "audio_interrupted":
                # Barge-in: tirar lo que quede en cola para que se calle ya.
                while not cola_salida.empty():
                    cola_salida.get_nowait()
            elif tipo == "tool_start":
                print(f"  [tool] empieza: {getattr(event, 'tool', '?')}")
            elif tipo == "tool_end":
                print(f"  [tool] termina: {getattr(event, 'output', '')}")
            elif tipo == "error":
                print(f"  [error] {event}", file=sys.stderr)

    async with session:
        await asyncio.gather(capturar_micro(), reproducir(), consumir_eventos())


def main():
    ap = argparse.ArgumentParser(description="Spike del Agents SDK (opcion 1).")
    ap.add_argument("--self-test", action="store_true",
                    help="Valida el modulo y la tool sin audio (para la Mac).")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    try:
        asyncio.run(correr_spike())
    except KeyboardInterrupt:
        print("\nSpike cortado.")


if __name__ == "__main__":
    main()
