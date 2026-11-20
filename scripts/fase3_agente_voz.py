"""
Fase 3 - La tripulacion por voz con el Agents SDK de OpenAI (pedido de Pato,
Sesion #3). Reemplaza al spike: ya no es una tool, son todas, con un agente
por oficial (ver agentes.py).

------------------------------------------------------------------------
EL CIRCUITO:

  microfono --> COMPUERTA LOCAL --(solo si suena a orden)--> sesion Realtime
   (24 kHz)    (gratis, en la PC)                            (gpt-realtime)
                                                                   |
      panel LCARS + voz del oficial <-- fase1.ejecutar_accion <-- tool call

  - La sesion Realtime corre en Python por WebSocket (openai-agents). Una
    sesion conectada pero sin audio NO consume tokens: se paga lo que se le
    manda y lo que contesta.
  - Por eso la COMPUERTA: el microfono esta siempre abierto, pero el audio
    solo sale hacia OpenAI cuando la PC detecta, sola y sin red, algo que se
    parece a una orden. Recien ahi se manda (con PRE_ROLL_SEG de audio
    previo, para no perder el nombre del oficial). Ver COMPUERTA abajo.
  - La tecla la sigue apretando fase1.ejecutar_accion, con la consola como
    Administrador. Las "dos trampas" de Pato (call_id + response.create) las
    resuelve el SDK.

------------------------------------------------------------------------
COMO INSTALAR (Windows, consola como Administrador, ademas de lo de fase 1/2):

    pip install openai-agents sounddevice numpy vosk

  y el modelo chico de español de Vosk (~40 MB), descomprimido en
  models/ en la raiz del proyecto (esta en el .gitignore):

    https://alphacephei.com/vosk/models  ->  vosk-model-small-es-0.42

COMO CORRERLO:

    python scripts/fase3_agente_voz.py            (o MODO_ESCUCHA = "agente"
                                                   en fase2_voice_commands.py)
    python scripts/fase3_agente_voz.py --self-test (sin red, micro ni juego)
    python scripts/fase3_agente_voz.py --solo-compuerta (calibrar, sin gastar)
"""

import argparse
import asyncio
import collections
import json
import os
import sys
import time

import audio_enviado
import config

# --- Modelo y voz -----------------------------------------------------------

MODELO = "gpt-realtime-2.1"     # "gpt-realtime-2.1-mini" cuesta ~1/3
MODELO_STT = "gpt-4o-mini-transcribe"

# Quien pone la voz:
#   "oficiales" -> el agente contesta en TEXTO (barato) y suenan los wav
#                  pre-generados de cada oficial, con su retrato en el panel.
#                  Es el HUD que ya gusta.
#   "realtime"  -> el agente habla con voz propia (VOZ). Mas natural, y el
#                  audio de salida es lo mas caro de la sesion.
VOZ_AGENTE = "oficiales"
VOZ = "ash"

# Con VOZ_AGENTE = "realtime": True si se usan auriculares. Con parlantes, el
# microfono se tapa mientras habla el agente, para que no se escuche a si mismo.
AURICULARES = False

# ¿Hace falta nombrar a un oficial para que la orden cuente? Mismo criterio que
# fase2. Ademas de las instrucciones del agente, decide que palabras abren la
# compuerta "vosk".
EXIGIR_NOMBRE_DE_OFICIAL = True

# --- Compuerta: que audio sale hacia OpenAI --------------------------------
#
#   "vosk"    -> reconocimiento LOCAL de palabras clave (Vosk, offline, CPU).
#                Solo abre cuando escucha el nombre de un oficial (o, con
#                EXIGIR_NOMBRE_DE_OFICIAL = False, una palabra de comando).
#                La charla del puente no cuesta nada.
#   "energia" -> abre con cualquier voz por encima de UMBRAL_VOZ. Sin
#                dependencias, pero toda charla se paga.
#   "abierta" -> manda todo, siempre. Solo para medir.
#
# Vosk no transcribe la orden (eso lo sigue haciendo OpenAI, que es mejor):
# solo decide si vale la pena gastar en escucharla.
COMPUERTA = "vosk"
RUTA_MODELO_VOSK = os.path.join(config.RAIZ, "models", "vosk-model-small-es-0.42")

# True restringe Vosk a las palabras clave. NO: medido el 12/11 con frases
# sintetizadas, fuerza cualquier charla a una palabra clave y abre siempre.
# En modo libre abrio con las 4 ordenes con rol y con ninguna charla.
GRAMATICA_VOSK = False

UMBRAL_VOZ = 0.015          # RMS (0-1), mismo valor que fase2
PRE_ROLL_SEG = 1.5          # audio previo que se manda al abrir
COLA_SILENCIO_SEG = 1.2     # sigue abierta tras dejar de hablar: el VAD del
                            # server necesita ese silencio para cerrar el turno
MAX_ABIERTA_SEG = 12.0      # nadie da una orden mas larga
MARGEN_ANTI_ECO = 0.4

# --- Guardas ----------------------------------------------------------------

# Tope de teclas por rafaga, como MAX_ACCIONES_EN_CADENA del parser.
MAX_ACCIONES_POR_RAFAGA = 5
RAFAGA_SEG = 4.0

# La sesion se corta sola al pasar este gasto estimado (USD).
MAX_USD_POR_SESION = 2.00

# USD por millon de tokens. CONFIRMAR contra https://openai.com/api/pricing
# antes de llevarle numeros a Pato: salen de la doc del 26/10.
PRECIOS = {
    "gpt-realtime-2.1": {"audio_in": 32.0, "audio_cache": 0.40,
                         "texto_in": 4.0, "texto_cache": 0.40,
                         "audio_out": 64.0, "texto_out": 16.0},
    "gpt-realtime-2.1-mini": {"audio_in": 10.0, "audio_cache": 0.30,
                              "texto_in": 0.60, "texto_cache": 0.06,
                              "audio_out": 20.0, "texto_out": 2.40},
}

# --- Audio ------------------------------------------------------------------

SAMPLE_RATE = 24000         # PCM16 mono 24 kHz: lo que pide la Realtime API
BLOQUE = 480                # 20 ms
DISPOSITIVO_ENTRADA = None  # None = default de Windows; fase2 pasa el suyo

try:
    from stt_openai import PROMPT_VOCABULARIO
except ImportError:
    PROMPT_VOCABULARIO = "alerta roja, media maquina, escudos, fasers, ECM"


# ---------------------------------------------------------------------------
# Compuerta
# ---------------------------------------------------------------------------

def _normalizar(texto):
    import unicodedata
    texto = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                    if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() else " " for c in texto).split()


def palabras_clave(exigir_nombre):
    """Palabras que abren la compuerta "vosk": los alias de los oficiales y,
    si no se exige nombre, las palabras con peso de los comandos."""
    import oficiales
    palabras = set()
    for datos in oficiales.OFICIALES.values():
        for alias in datos["alias"]:
            palabras.update(_normalizar(alias))
    if not exigir_nombre:
        import catalogo_comandos as cc
        for item in cc.generar_catalogo():
            for frase in item["ejemplos"]:
                palabras.update(_normalizar(frase))
    # "t" de "t lara" o "a" abririan con cualquier cosa
    return {p for p in palabras if len(p) >= 4}


class DetectorVosk:
    """Spotting local de palabras clave. `escuchar(pcm16)` devuelve la
    palabra que disparo, o None."""

    def __init__(self, ruta_modelo, palabras, gramatica=True):
        import vosk
        vosk.SetLogLevel(-1)
        if not os.path.isdir(ruta_modelo):
            raise FileNotFoundError(
                f"No esta el modelo de Vosk en {ruta_modelo}. Bajarlo de "
                "https://alphacephei.com/vosk/models (ver cabecera).")
        modelo = vosk.Model(ruta_modelo)
        self.palabras = set(palabras)
        if gramatica:
            lista = sorted(self.palabras) + ["[unk]"]
            self._rec = vosk.KaldiRecognizer(modelo, SAMPLE_RATE,
                                             json.dumps(lista))
        else:
            self._rec = vosk.KaldiRecognizer(modelo, SAMPLE_RATE)

    def escuchar(self, pcm16):
        if self._rec.AcceptWaveform(pcm16):
            texto = json.loads(self._rec.Result()).get("text", "")
        else:
            texto = json.loads(self._rec.PartialResult()).get("partial", "")
        for palabra in texto.split():
            if palabra in self.palabras:
                return palabra
        return None

    def reiniciar(self):
        self._rec.Reset()


class Compuerta:
    """Decide que bloques de microfono salen hacia la sesion. Cerrada no se
    manda nada; al abrir se manda el pre-roll guardado y despues todo hasta
    COLA_SILENCIO_SEG sin voz (o MAX_ABIERTA_SEG)."""

    def __init__(self, modo, detector=None, reloj=time.monotonic):
        self.modo = modo
        self.detector = detector
        self.reloj = reloj
        seg_bloque = BLOQUE / SAMPLE_RATE
        self._pre = collections.deque(maxlen=int(PRE_ROLL_SEG / seg_bloque))
        self._abierta_desde = None
        self._ultima_voz = 0.0
        self.mudo_hasta = 0.0
        self.segundos_enviados = 0.0
        self.aperturas = 0

    @property
    def abierta(self):
        return self._abierta_desde is not None

    def _abrir(self, motivo):
        self._abierta_desde = self._ultima_voz = self.reloj()
        self.aperturas += 1
        print(f"  [compuerta] abre ({motivo})")

    def _cerrar(self):
        self._abierta_desde = None
        self._pre.clear()
        if self.detector is not None:
            self.detector.reiniciar()

    def procesar(self, pcm16, rms):
        """Devuelve la lista de bloques a mandar (vacia si esta cerrada)."""
        ahora = self.reloj()
        if ahora < self.mudo_hasta:
            if self.abierta:
                self._cerrar()
            return []

        if self.modo == "abierta":
            self.segundos_enviados += BLOQUE / SAMPLE_RATE
            return [pcm16]

        if not self.abierta:
            self._pre.append(pcm16)
            if self.modo == "energia":
                disparo = "voz" if rms >= UMBRAL_VOZ else None
            else:
                disparo = self.detector.escuchar(pcm16)
            if disparo is None:
                return []
            self._abrir(disparo)
            salida = list(self._pre)
            self._pre.clear()
            self.segundos_enviados += len(salida) * BLOQUE / SAMPLE_RATE
            return salida

        if rms >= UMBRAL_VOZ:
            self._ultima_voz = ahora
        if (ahora - self._ultima_voz > COLA_SILENCIO_SEG
                or ahora - self._abierta_desde > MAX_ABIERTA_SEG):
            self._cerrar()
            return []
        self.segundos_enviados += BLOQUE / SAMPLE_RATE
        return [pcm16]


# ---------------------------------------------------------------------------
# Guardas
# ---------------------------------------------------------------------------

class Gasto:
    """Suma el costo estimado con los eventos `usage` de la sesion."""

    def __init__(self, modelo):
        self.precios = PRECIOS.get(modelo, PRECIOS["gpt-realtime-2.1"])
        self.usd = 0.0

    def sumar(self, evento):
        p = self.precios
        ent = evento.input_tokens_details
        sal = evento.output_tokens_details
        cache = getattr(ent, "cached_tokens_details", None) if ent else None
        audio_cache = (getattr(cache, "audio_tokens", 0) or 0) if cache else 0
        texto_cache = (getattr(cache, "text_tokens", 0) or 0) if cache else 0
        audio_in = ((ent.audio_tokens or 0) if ent else 0) - audio_cache
        texto_in = ((ent.text_tokens or 0) if ent else 0) - texto_cache
        if ent is None:
            texto_in = evento.usage.input_tokens
        audio_out = (sal.audio_tokens or 0) if sal else 0
        texto_out = ((sal.text_tokens or 0) if sal
                     else evento.usage.output_tokens)
        self.usd += (audio_in * p["audio_in"] + audio_cache * p["audio_cache"]
                     + texto_in * p["texto_in"] + texto_cache * p["texto_cache"]
                     + audio_out * p["audio_out"]
                     + texto_out * p["texto_out"]) / 1_000_000
        return self.usd


class Rafaga:
    """Como mucho MAX_ACCIONES_POR_RAFAGA teclas cada RAFAGA_SEG."""

    def __init__(self, reloj=time.monotonic):
        self.reloj = reloj
        self._marcas = collections.deque()

    def permitir(self):
        ahora = self.reloj()
        while self._marcas and ahora - self._marcas[0] > RAFAGA_SEG:
            self._marcas.popleft()
        if len(self._marcas) >= MAX_ACCIONES_POR_RAFAGA:
            return False
        self._marcas.append(ahora)
        return True


# ---------------------------------------------------------------------------
# La sesion
# ---------------------------------------------------------------------------

def _config_sesion(modelo, exigir_nombre):
    entrada = {
        "format": "pcm16",
        "transcription": {"model": MODELO_STT, "language": "es",
                          "prompt": PROMPT_VOCABULARIO},
        # eagerness alto: las ordenes son cortas, no hace falta esperar a ver
        # si el capitan sigue hablando.
        "turn_detection": {"type": "semantic_vad", "eagerness": "high",
                           "interrupt_response": True},
    }
    ajustes = {"model_name": modelo, "audio": {"input": entrada}}
    if VOZ_AGENTE == "realtime":
        ajustes["output_modalities"] = ["audio"]
        ajustes["audio"]["output"] = {"format": "pcm16", "voice": VOZ}
    else:
        ajustes["output_modalities"] = ["text"]
    return {
        "model_settings": ajustes,
        # En orden: "alerta roja y media maquina" tiene que apretar r y
        # despues la velocidad, no las dos a la vez.
        "async_tool_calls": False,
        "tracing_disabled": True,
    }


class Puente:
    """Une la compuerta, la sesion y el ejecutor de teclas."""

    def __init__(self, compuerta, ejecutar_accion, responder,
                 ultimo_audio_seg=lambda: 0.0, modelo=MODELO):
        self.compuerta = compuerta
        self._ejecutar_accion = ejecutar_accion
        self._responder = responder
        self._ultimo_audio_seg = ultimo_audio_seg
        self.gasto = Gasto(modelo)
        self.rafaga = Rafaga()
        self.ejecutadas = []
        # Lo lee agentes.crear_tool: el panel muestra lo que dijo el capitan
        self.contexto = {"texto": None}
        self._texto = collections.defaultdict(str)
        self.cola_parlante = asyncio.Queue()

    async def ejecutar(self, accion, _contexto):
        """El ejecutor de las tools (ver agentes.crear_tool)."""
        if not self.rafaga.permitir():
            print(f"  [guarda] tope de {MAX_ACCIONES_POR_RAFAGA} ordenes en "
                  f"{RAFAGA_SEG:.0f}s: no se ejecuta {accion.get('raw')!r}")
            return "Rechazado: demasiadas ordenes seguidas."
        await asyncio.to_thread(self._ejecutar_accion, accion)
        self.ejecutadas.append(accion)
        sonar = VOZ_AGENTE == "oficiales"
        await asyncio.to_thread(self._responder, accion, sonar)
        if sonar:
            self.compuerta.mudo_hasta = (time.monotonic()
                                         + self._ultimo_audio_seg()
                                         + MARGEN_ANTI_ECO)
        return f"Hecho: {accion.get('raw')}."

    def manejar_evento(self, evento):
        """Devuelve False si hay que cortar la sesion."""
        tipo = evento.type
        if tipo == "audio":
            self.cola_parlante.put_nowait(evento.audio.data)
        elif tipo == "audio_interrupted":
            while not self.cola_parlante.empty():
                self.cola_parlante.get_nowait()
        elif tipo == "handoff":
            print(f"  [handoff] {evento.from_agent.name} -> "
                  f"{evento.to_agent.name}")
        elif tipo == "error":
            print(f"  [error] {evento.error}", file=sys.stderr)
        elif tipo == "raw_model_event":
            return self._manejar_crudo(evento.data)
        return True

    def _manejar_crudo(self, dato):
        tipo = dato.type
        if tipo == "input_audio_transcription_completed":
            print(f"\n<- \"{dato.transcript}\"")
            self.contexto["texto"] = dato.transcript
        elif tipo in ("output_text_delta", "transcript_delta"):
            self._texto[dato.item_id] += dato.delta
        elif tipo == "turn_ended":
            for texto in self._texto.values():
                if texto.strip():
                    print(f"  [agente] {texto.strip()}")
            self._texto.clear()
        elif tipo == "usage":
            usd = self.gasto.sumar(dato)
            print(f"  [gasto] ${usd:.4f} en la sesion "
                  f"({self.compuerta.segundos_enviados:.0f}s de audio enviado, "
                  f"{self.compuerta.aperturas} aperturas)")
            if usd >= MAX_USD_POR_SESION:
                print(f"  [guarda] se paso el tope de ${MAX_USD_POR_SESION:.2f}"
                      f" por sesion. Se corta.")
                return False
        return True


async def correr(puente, exigir_nombre, modelo=MODELO, modelo_realtime=None,
                 bloques=None):
    """Corre la sesion. `bloques` es un async iterator de (pcm16, rms); si es
    None se abre el microfono. `modelo_realtime` permite inyectar un modelo
    de prueba (self-test)."""
    import agentes
    from agents.realtime import RealtimeRunner

    runner = RealtimeRunner(
        starting_agent=agentes.armar_tripulacion(puente.ejecutar,
                                                 exigir_nombre),
        model=modelo_realtime,
        config=_config_sesion(modelo, exigir_nombre),
    )
    model_config = {} if modelo_realtime else {"api_key": config.api_key()}
    session = await runner.run(context=puente.contexto,
                               model_config=model_config)

    async def mandar_audio():
        fuente = bloques if bloques is not None else _microfono()
        enviado = []
        async for pcm16, rms in fuente:
            if (VOZ_AGENTE == "realtime" and not AURICULARES
                    and not puente.cola_parlante.empty()):
                continue
            for salida in puente.compuerta.procesar(pcm16, rms):
                await session.send_audio(salida)
                enviado.append(salida)
            # Al cerrar la compuerta, lo que salio en esa apertura va a disco
            if enviado and not puente.compuerta.abierta:
                if bloques is None:
                    audio_enviado.guardar_pcm16(b"".join(enviado),
                                                SAMPLE_RATE, "agente")
                enviado = []

    async def consumir_eventos():
        async for evento in session:
            if not puente.manejar_evento(evento):
                return

    async with session:
        tareas = [asyncio.create_task(consumir_eventos()),
                  asyncio.create_task(mandar_audio())]
        if VOZ_AGENTE == "realtime" and bloques is None:
            tareas.append(asyncio.create_task(_parlante(puente.cola_parlante)))
        # Termina cuando la sesion se corta (o se acaba la fuente de audio).
        _, pendientes = await asyncio.wait(
            tareas, return_when=asyncio.FIRST_COMPLETED)
        for t in pendientes:
            t.cancel()


async def _microfono():
    import numpy as np
    import sounddevice as sd

    loop = asyncio.get_running_loop()
    cola = asyncio.Queue()

    def cb(indata, frames, t, status):
        loop.call_soon_threadsafe(cola.put_nowait, bytes(indata))

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOQUE,
                           channels=1, dtype="int16",
                           device=DISPOSITIVO_ENTRADA, callback=cb):
        while True:
            pcm16 = await cola.get()
            muestras = np.frombuffer(pcm16, dtype=np.int16) / 32768.0
            rms = float(np.sqrt(np.mean(muestras ** 2))) if muestras.size else 0.0
            yield pcm16, rms


async def _parlante(cola):
    import sounddevice as sd
    with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16") as stream:
        while True:
            await asyncio.to_thread(stream.write, await cola.get())


def armar_compuerta(exigir_nombre):
    if COMPUERTA != "vosk":
        return Compuerta(COMPUERTA)
    try:
        detector = DetectorVosk(RUTA_MODELO_VOSK, palabras_clave(exigir_nombre),
                                GRAMATICA_VOSK)
    except (ImportError, FileNotFoundError) as e:
        print(f"  [!] Compuerta 'vosk' no disponible ({e}).")
        print("      Se usa 'energia': funciona, pero toda charla se paga.")
        return Compuerta("energia")
    return Compuerta("vosk", detector)


async def _probar_compuerta(compuerta):
    async for pcm16, rms in _microfono():
        compuerta.procesar(pcm16, rms)


def solo_compuerta(dispositivo=None, exigir_nombre=None):
    """Microfono + compuerta, sin sesion: para calibrar sin gastar. Imprime
    cada apertura y cuanto audio se hubiera mandado."""
    global DISPOSITIVO_ENTRADA
    if dispositivo is not None:
        DISPOSITIVO_ENTRADA = dispositivo
    if exigir_nombre is None:
        exigir_nombre = EXIGIR_NOMBRE_DE_OFICIAL
    compuerta = armar_compuerta(exigir_nombre)
    print(f"Compuerta '{compuerta.modo}' sin sesion (no se gasta nada). "
          "Habla normal y llama a oficiales. Ctrl+C para terminar.")
    inicio = time.monotonic()
    try:
        asyncio.run(_probar_compuerta(compuerta))
    except KeyboardInterrupt:
        pass
    total = time.monotonic() - inicio
    print(f"\n{compuerta.aperturas} aperturas · se hubieran mandado "
          f"{compuerta.segundos_enviados:.0f}s de {total:.0f}s de microfono")


def main(dispositivo=None, exigir_nombre=None):
    """Punto de entrada. fase2 lo llama con MODO_ESCUCHA = "agente"."""
    global DISPOSITIVO_ENTRADA
    import fase1_text_commands as fase1
    import oficiales

    if dispositivo is not None:
        DISPOSITIVO_ENTRADA = dispositivo
    if exigir_nombre is None:
        exigir_nombre = EXIGIR_NOMBRE_DE_OFICIAL

    # Por voz no se escribe en la consola: el foco se queda en el juego.
    fase1.DEVOLVER_FOCO_CONSOLA = False
    if oficiales.PANEL_WEB and oficiales.panel_web is not None:
        url = oficiales.panel_web.iniciar()
        if url:
            print(f"Panel de la tripulacion: {url}  (abrilo al lado del juego)")

    print("=== SFC Voice Commander - Fase 3: la tripulacion con Agents SDK ===")
    print(f"Modelo: {MODELO} · voz: {VOZ_AGENTE} · tope ${MAX_USD_POR_SESION:.2f}")
    compuerta = armar_compuerta(exigir_nombre)
    print(f"Compuerta: {compuerta.modo}")
    print('Llamá a un oficial: "computadora, alerta roja" · '
          '"artillero, fuego". Ctrl+C para salir.\n')

    fase1.encontrar_ventana_juego()
    puente = Puente(
        compuerta,
        ejecutar_accion=lambda a: fase1.ejecutar_accion(a, responder=False),
        responder=oficiales.responder,
        ultimo_audio_seg=lambda: oficiales.ULTIMO_AUDIO_SEG,
    )
    try:
        asyncio.run(correr(puente, exigir_nombre))
    except KeyboardInterrupt:
        pass
    print(f"\nSesion cerrada. Gasto estimado: ${puente.gasto.usd:.4f}")


# ---------------------------------------------------------------------------
# Self-test: sin red, sin micro y sin pydirectinput (para la Mac)
# ---------------------------------------------------------------------------

def _simular_windows():
    """Reemplaza pydirectinput/pygetwindow por grabadores, asi corre el
    ejecutor de verdad (fase1.ejecutar_accion) y se ve que tecla apreto."""
    import types
    teclas = []
    pdi = types.ModuleType("pydirectinput")
    pdi.PAUSE = 0
    pdi.press = lambda t: teclas.append(t)
    pdi.keyDown = lambda t: teclas.append(f"{t}+")
    pdi.keyUp = lambda t: None
    gw = types.ModuleType("pygetwindow")
    gw.getAllWindows = lambda: []
    gw.getAllTitles = lambda: []
    # Pisar siempre: en la Windows los de verdad estan instalados
    sys.modules["pydirectinput"] = pdi
    sys.modules["pygetwindow"] = gw
    return teclas


def self_test():
    teclas = _simular_windows()
    import fase1_text_commands as fase1
    import oficiales
    import agentes
    from agents import set_tracing_disabled
    from agents.realtime import RealtimeModelToolCallEvent
    from agents.realtime.testing import ScriptedRealtimeModel
    from agents.testing.model import ModelStep, ScriptedModel, function_call

    set_tracing_disabled(True)
    fase1.FALLAR_SI_NO_ENCUENTRA_VENTANA = False
    fase1.enfocar_ventana_juego = lambda: True
    fase1.enfocar_consola = lambda: None
    oficiales.VOZ_ACTIVADA = False
    oficiales.PANEL_WEB = False
    fallas = []

    def chequear(condicion, que):
        print(f"  {'OK ' if condicion else 'MAL'} {que}")
        if not condicion:
            fallas.append(que)

    print("=== Self-test de la Fase 3 ===")
    print("\nTripulacion:\n  " + agentes.resumen().replace("\n", "\n  "))

    # 1) Compuerta: sin palabra clave no sale nada; con palabra clave sale el
    #    pre-roll; tras el silencio vuelve a cerrar.
    class DetectorFalso:
        def __init__(self):
            self.proxima = None

        def escuchar(self, _):
            return self.proxima

        def reiniciar(self):
            self.proxima = None

    reloj = [0.0]
    det = DetectorFalso()
    comp = Compuerta("vosk", det, reloj=lambda: reloj[0])
    enviados = []
    for _ in range(100):                       # 2 s de charla sin nombre
        reloj[0] += 0.02
        enviados += comp.procesar(b"x", 0.05)
    chequear(not enviados, "charla sin nombre: no se manda nada")
    det.proxima = "computadora"
    reloj[0] += 0.02
    enviados = comp.procesar(b"x", 0.05)
    chequear(len(enviados) == int(PRE_ROLL_SEG / 0.02),
             f"palabra clave: abre y manda {PRE_ROLL_SEG}s de pre-roll")
    for _ in range(int(COLA_SILENCIO_SEG / 0.02) + 5):
        reloj[0] += 0.02
        comp.procesar(b"x", 0.0)
    chequear(not comp.abierta, "tras el silencio vuelve a cerrar")
    comp.mudo_hasta = reloj[0] + 1
    det.proxima = "computadora"
    chequear(not comp.procesar(b"x", 0.05), "muda mientras habla el oficial")

    # 2) Sesion Realtime: alerta roja directa, y handoff al artillero + fuego.
    async def sesion_de_prueba():
        modelo = ScriptedRealtimeModel(strict=False, connect_events=[
            RealtimeModelToolCallEvent(name="red_alert", call_id="c1",
                                       arguments="{}"),
            RealtimeModelToolCallEvent(name="llamar_armas", call_id="c2",
                                       arguments="{}"),
            RealtimeModelToolCallEvent(name="disparar", call_id="c3",
                                       arguments="{}"),
        ])
        puente = Puente(Compuerta("abierta"),
                        ejecutar_accion=lambda a: fase1.ejecutar_accion(
                            a, responder=False),
                        responder=lambda a, sonar: None)

        async def sin_audio():
            await asyncio.sleep(1.0)
            return
            yield

        await correr(puente, True, modelo_realtime=modelo, bloques=sin_audio())
        return puente

    puente = asyncio.run(sesion_de_prueba())
    chequear(teclas[:2] == ["r", "z"],
             f"realtime: alerta roja, handoff al artillero y fuego (teclas {teclas})")

    # 3) Guarda de rafaga.
    reloj = [0.0]
    r = Rafaga(reloj=lambda: reloj[0])
    permitidas = sum(r.permitir() for _ in range(MAX_ACCIONES_POR_RAFAGA + 3))
    chequear(permitidas == MAX_ACCIONES_POR_RAFAGA,
             f"rafaga: {permitidas} de {MAX_ACCIONES_POR_RAFAGA + 3} pasan")

    # 4) Agente de texto (fallback del parser): junta sin apretar nada.
    del teclas[:]
    modelo_texto = ScriptedModel([ModelStep(output=[
        function_call("red_alert", "{}", call_id="t1"),
        function_call("media_maquina", "{}", call_id="t2"),
    ])])
    acciones = agentes.interpretar_texto("alerta roja y a media", 5,
                                         modelo=modelo_texto)
    chequear([a.get("key") or a.get("level") for a in acciones] == ["r", 2]
             and not teclas,
             "texto: junta alerta roja + media maquina, sin apretar teclas")

    # 5) Gasto con un evento usage de mentira.
    from types import SimpleNamespace as N
    g = Gasto("gpt-realtime-2.1")
    g.sumar(N(usage=N(input_tokens=0, output_tokens=0),
              input_tokens_details=N(audio_tokens=1_000_000, text_tokens=0,
                                     cached_tokens_details=None),
              output_tokens_details=N(audio_tokens=0, text_tokens=0)))
    chequear(abs(g.usd - 32.0) < 1e-6, "gasto: 1M tokens de audio = $32")

    print(f"\n{'TODO OK' if not fallas else f'{len(fallas)} FALLAS'}")
    return not fallas


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--self-test", action="store_true",
                    help="Valida todo sin red, micro ni juego (para la Mac).")
    ap.add_argument("--solo-compuerta", action="store_true",
                    help="Micro + compuerta sin sesion, para calibrar gratis.")
    ap.add_argument("--dispositivo", type=int, default=None,
                    help="Numero de microfono (ver probar_microfono.py).")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(0 if self_test() else 1)
    if args.solo_compuerta:
        _simular_windows()
        solo_compuerta(dispositivo=args.dispositivo)
    else:
        main(dispositivo=args.dispositivo)
