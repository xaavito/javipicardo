"""
Fase 2 - Comandos por VOZ (push-to-talk + STT local u OpenAI)

Objetivo: reemplazar el input() de texto de la Fase 1 por microfono + STT,
reusando el MISMO parser y ejecutor ya validados en `fase1_text_commands.py`
(parsear_comando, ejecutar_accion, foco de ventana).

STT_BACKEND (mas abajo) elige entre:
- "openai": API de Whisper de OpenAI (scripts/stt_openai.py). Requiere
  internet + OPENAI_API_KEY, pero suele ser mas rapido/preciso que local.
  ES EL BACKEND POR DEFECTO ACTUAL.
- "local": faster-whisper corriendo en CPU, sin internet ni costo.

Modo de activacion: PUSH-TO-TALK (mantener apretada una tecla mientras se
habla, soltarla al terminar). Se eligio este modo en vez de deteccion de
silencio (VAD) porque es mas simple de implementar y da menor latencia (ver
README seccion de latencia estimada).

------------------------------------------------------------------------
COMO INSTALAR (en la maquina Windows, junto a lo que ya se instalo en
Fase 0 / Fase 1: python, pydirectinput, pygetwindow):

    pip install sounddevice numpy keyboard

Si STT_BACKEND == "openai" (el default actual), ademas:

    pip install openai soundfile

Y configurar la variable de entorno OPENAI_API_KEY (ver stt_openai.py para
el detalle de como setearla en Windows).

Si STT_BACKEND == "local", en cambio, instalar:

    pip install faster-whisper

Notas sobre las dependencias:
- faster-whisper (solo si STT_BACKEND=="local"): motor de transcripcion de
  voz optimizado para CPU. La primera vez que se corre, descarga el modelo
  elegido (unos cientos de MB, ver MODEL_SIZE mas abajo) - hace falta
  internet la primera vez nada mas, despues queda cacheado localmente.
- openai + soundfile (solo si STT_BACKEND=="openai"): cliente de la API y
  libreria para armar el WAV en memoria antes de mandarlo.
- sounddevice: captura de audio del microfono.
- numpy: manejo del buffer de audio como array.
- keyboard: detectar cuando se mantiene apretada la tecla de push-to-talk.
  ESTA LIBRERIA REQUIERE PERMISOS DE ADMINISTRADOR EN WINDOWS para escuchar
  el teclado globalmente - correr la consola como Administrador (que ya es
  un requisito desde la Fase 0 de todos modos).

------------------------------------------------------------------------
COMO USAR:
1. Igual que en Fases 0/1: abrir el juego DESDE DxWnd, entrar a una mision
   donde la nave pueda moverse.
2. Correr este script DESDE UNA CONSOLA COMO ADMINISTRADOR:
       python fase2_voice_commands.py
3. La PRIMERA VEZ que se corre, va a tardar un poco mas en arrancar mientras
   descarga el modelo de Whisper (ver progreso en consola).
4. Mantener apretada la tecla configurada en PUSH_TO_TALK_KEY (por defecto
   F12 - elegida por NO estar mapeada a ninguna accion del juego, ver nota
   en la definicion de la constante mas abajo) MIENTRAS se habla el comando,
   y soltarla al terminar de hablar.
   Ejemplos de comandos a decir (en español, hablando normal):
       "alerta roja"
       "disparar"
       "media maquina"
       "cuarto de maquina"
       "escudos al maximo"
       "seguir a esa nave" / "seguir a la amenaza"
       "siguiente objetivo"
       "objetivo mas cercano"
5. El script transcribe lo dicho, lo muestra en consola, lo interpreta con
   el mismo parser de la Fase 1, y ejecuta la accion (con el mismo manejo de
   foco automatico juego <-> consola).
6. Presionar ESC para salir del programa.

NOTA DE LATENCIA: el tiempo entre soltar la tecla y que se ejecute la accion
en el juego depende del tamaño del modelo elegido (MODEL_SIZE) y de la
duracion de lo hablado. Con el modelo "small" en CPU deberia rondar entre
0.5 y 1.5 segundos, mas la pausa de enfoque de ventana ya conocida de la
Fase 1 (PAUSA_POST_ENFOQUE, definida en fase1_text_commands.py).
"""

import collections
import sys
import time
import queue

import numpy as np
import sounddevice as sd
import keyboard

# Backend de STT (Speech-to-Text): "local" (faster-whisper, gratis, sin
# internet) u "openai" (API de Whisper de OpenAI, requiere API key e
# internet, generalmente mas rapida/precisa). Ver README para el detalle de
# como configurar OPENAI_API_KEY.
STT_BACKEND = "openai"

if STT_BACKEND == "local":
    from faster_whisper import WhisperModel
elif STT_BACKEND == "openai":
    # Se importa el modulo entero (ademas de la funcion) para poder llamar a
    # stt_openai_mod.precalentar() al arrancar - ver precalentar_todo().
    import stt_openai as stt_openai_mod
    from stt_openai import transcribir_openai

# Reusa TODA la logica ya validada de la Fase 1: normalizacion, diccionarios,
# parser, ejecutor con manejo de foco de ventana.
import fase1_text_commands as fase1

# Fallback opcional con LLM local (Fase 4, ver llm_fallback.py). Es opcional
# a proposito: si Ollama no esta instalado, el script sigue funcionando
# igual con el parser de reglas solo (USAR_LLM_FALLBACK queda en False).
USAR_LLM_FALLBACK = True
try:
    import llm_fallback
except ImportError:
    USAR_LLM_FALLBACK = False


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

# Tamaño del modelo Whisper. Ver README seccion 2.4 para tabla de tamaños:
# tiny (~75MB, rapido/impreciso) -> base (~145MB) -> small (~480MB,
# recomendado por precision) -> medium (~1.5GB, mas preciso pero mas lento).
# Si la latencia con "small" se siente alta, probar "base" primero (buen
# equilibrio velocidad/precision para comandos cortos de vocabulario acotado
# como los de este proyecto) antes de bajar directo a "tiny".
MODEL_SIZE = "base"

# Idioma esperado (acelera un poco la transcripcion al no tener que
# autodetectar el idioma cada vez).
LANGUAGE = "es"

# Tecla de push-to-talk: mantener apretada mientras se habla.
# IMPORTANTE: se eligio F12 en vez de F9/F10/F11 porque esas SI estan
# mapeadas en el juego (HUD Minimal/Normal/Maximum Information, ver
# docs/hotkeys_sfc2.md) y usarlas colisionaria: como el foco termina estando
# en la ventana del juego mientras se mantiene apretada la tecla, el juego
# podria recibir tambien el evento y cambiar de HUD sin querer.
# F12 no aparece en la lista completa de hotkeys de la Gold Edition
# (docs/hotkeys_sfc2.md) - deberia estar libre, pero CONFIRMAR en el juego
# (Options -> Hotkeys, o probando en una mision) antes de confiar del todo.
# Alternativas libres si hiciera falta cambiarla: "insert", "num enter".
PUSH_TO_TALK_KEY = "f12"

# Tecla para salir del programa.
EXIT_KEY = "esc"

# ---------------------------------------------------------------------------
# Modo de escucha
#
#   "push_to_talk" -> mantener F12 mientras se habla (el de siempre)
#   "boton"        -> mantener apretado el boton del panel web con el MOUSE.
#                     Igual que el push-to-talk pero sin tocar el teclado, que
#                     es comodo si ya estas jugando con el mouse. El audio lo
#                     graba Python igual; la pagina solo avisa cuando empezar
#                     y cuando terminar.
#   "activa"       -> microfono SIEMPRE abierto. No hay boton: se llama al
#                     oficial por su nombre ("computadora, alerta roja") y eso
#                     es lo que activa la orden.
#   "web"          -> igual que "activa", pero el microfono lo maneja la
#                     PAGINA: graba, corta las frases por volumen y le manda el
#                     audio a Python. La ventaja real no es de comodidad:
#                     pidiendo echoCancellation, el browser cancela su propia
#                     salida de la entrada, y como la voz de los oficiales sale
#                     por esa misma pagina, el eco se resuelve de raiz en vez
#                     de silenciar el microfono mientras hablan.
#
# En modo activo, el nombre del oficial NO es decoracion: es el filtro que
# separa una orden de una charla. Todo lo que no empiece llamando a alguien se
# descarta sin ejecutar nada.
# ---------------------------------------------------------------------------
MODO_ESCUCHA = "boton"

# --- Parametros del modo activo (VAD por energia, sin dependencias nuevas) ---

# Nivel RMS por encima del cual se considera que alguien esta hablando. Si
# agarra ruido de fondo, subirlo; si se come el principio de las frases,
# bajarlo. Medir el ruido de la sala con probar_microfono.py ayuda.
UMBRAL_VOZ = 0.015

# Silencio que cierra una frase. Mas corto responde antes pero corta al que
# habla pausado.
SILENCIO_PARA_CORTAR = 0.7

# Corte de seguridad: ninguna orden dura mas que esto.
MAX_DURACION_FRASE = 8.0

# ¿Hace falta nombrar a un oficial para que la orden cuente?
#
#   True  -> solo se ejecuta lo que empieza llamando a alguien
#            ("computadora, alerta roja"). Todo lo demas se ignora.
#   False -> tambien se aceptan ordenes sueltas ("alerta roja"), pero con el
#            parser ESTRICTO: la frase tiene que SER un comando, no contenerlo.
#            Asi "dale fuego a la parrilla" no dispara las armas.
#
# Lo unico que aporta el nombre es ese filtro: quien contesta ya se deduce del
# comando. En False se gana comodidad y se pierde margen: una frase que
# CASUALMENTE sea exactamente un comando se ejecuta. Y las ordenes en lenguaje
# libre (las que van al LLM) siguen necesitando el nombre, porque ahi no hay
# forma de distinguir una orden de una charla.
EXIGIR_NOMBRE_DE_OFICIAL = True

# Audio que se guarda ANTES de detectar voz. Sin esto se pierde siempre la
# primera silaba, que justamente es donde esta el nombre del oficial.
PRE_ROLL = 0.4

# Margen extra despues de que termina de hablar un oficial, antes de volver a
# escuchar. Evita que el sistema se escuche a si mismo.
MARGEN_ANTI_ECO = 0.4

SAMPLE_RATE = 16000  # Hz, el que espera Whisper
CHANNELS = 1

# Dispositivo de entrada. None = el default de Windows. Si hay varios
# microfonos (tipico al enchufar un auricular Bluetooth, que aparece como dos
# dispositivos distintos), poner aca el NUMERO que muestra:
#     python probar_microfono.py
DISPOSITIVO_ENTRADA = 1

# Below this many seconds the recording is a push-to-talk tap, not an order.
# It is not sent to the API: an audio with no speech makes the model answer
# with the vocabulary prompt itself (see es_eco_del_prompt in stt_openai.py).
MIN_DURACION_AUDIO_SEG = 0.3

# A spoken order is short. Anything longer than this is a hallucination or an
# echo, and it must not reach the parser: the parser matches a command ANYWHERE
# in the text, so a long spurious transcription can fire a real key.
MAX_CARACTERES_COMANDO = 150


# ---------------------------------------------------------------------------
# Captura de audio mientras se mantiene apretada la tecla de push-to-talk
# ---------------------------------------------------------------------------

def grabar_mientras(sigue_apretado, etiqueta):
    """Graba audio del microfono mientras `sigue_apretado()` devuelva True.
    Sirve igual para la tecla fisica que para el boton del panel: lo unico que
    cambia es como se pregunta si todavia esta apretado."""
    bloques = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  [!] Aviso de audio: {status}")
        bloques.put(indata.copy())

    print(f"[grabando... {etiqueta}]")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                         dtype='float32', device=DISPOSITIVO_ENTRADA,
                         callback=callback):
        while sigue_apretado():
            time.sleep(0.01)

    print("[grabacion terminada, transcribiendo...]")

    trozos = []
    while not bloques.empty():
        trozos.append(bloques.get())

    if not trozos:
        return np.array([], dtype=np.float32)

    audio = np.concatenate(trozos, axis=0).flatten()
    return audio


# ---------------------------------------------------------------------------
# Escucha activa: microfono siempre abierto, sin boton
# ---------------------------------------------------------------------------

def _rms(bloque):
    return float(np.sqrt(np.mean(bloque ** 2))) if bloque.size else 0.0


def _remuestrear(audio, hz_origen, hz_destino=SAMPLE_RATE):
    """Interpolacion lineal, que para voz y para un STT alcanza de sobra. El
    browser graba a la frecuencia de la placa (normalmente 48 kHz) y Whisper
    espera 16 kHz."""
    if hz_origen == hz_destino or audio.size == 0:
        return audio
    n = int(round(audio.size * hz_destino / float(hz_origen)))
    if n <= 1:
        return np.array([], dtype=np.float32)
    viejo = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
    nuevo = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(nuevo, viejo, audio).astype(np.float32)


def escuchar_desde_la_web(modelo):
    """El microfono lo maneja la pagina: aca solo se esperan las frases que
    manda, ya cortadas por su detector de voz."""
    ofi = getattr(fase1, "oficiales", None)
    if ofi is None or ofi.panel_web is None:
        print("[!] El modo 'web' necesita el panel (panel_web.py) y oficiales.py.")
        return

    panel = ofi.panel_web
    panel.pedir_microfono(True)
    print("Abrí el panel en el browser y dale permiso al micrófono.")
    print("Después hablá normal, llamando a un oficial:")
    print('   "computadora, alerta roja"   ·   "artillero, fuego"\n')

    while True:
        if keyboard.is_pressed(EXIT_KEY):
            print("Saliendo...")
            panel.pedir_microfono(False)
            return

        frase = panel.proxima_frase(timeout=0.4)
        if frase is None:
            continue

        crudo, hz = frase
        audio = np.frombuffer(crudo, dtype=np.float32)
        audio = _remuestrear(audio, hz)
        if audio.size / SAMPLE_RATE < MIN_DURACION_AUDIO_SEG:
            continue
        _procesar_frase(modelo, audio, ofi)


def escuchar_activo(modelo):
    """Loop de escucha continua. Corta las frases por silencio y solo ejecuta
    las que empiezan llamando a un oficial."""
    ofi = getattr(fase1, "oficiales", None)
    if ofi is None:
        print("[!] El modo activo necesita oficiales.py (es quien sabe los "
              "nombres por los que se llama a cada uno).")
        return

    seg_por_bloque = 0.1
    bloque_n = int(SAMPLE_RATE * seg_por_bloque)
    cola = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            pass  # los overflows ocasionales no valen un print por bloque
        cola.put(indata.copy())

    pre = collections.deque(maxlen=max(1, int(PRE_ROLL / seg_por_bloque)))
    grabando = False
    frase = []
    silencio = 0.0
    mudo_hasta = 0.0

    print("Escuchando. Llamá a un oficial por su nombre, por ejemplo:")
    print('   "computadora, alerta roja"   ·   "artillero, fuego"')
    print('   "timonel, media máquina"     ·   "Korak" (para que conteste)\n')

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype='float32', device=DISPOSITIVO_ENTRADA,
                        blocksize=bloque_n, callback=callback):
        while True:
            if keyboard.is_pressed(EXIT_KEY):
                print("Saliendo...")
                return

            try:
                bloque = cola.get(timeout=0.5)
            except queue.Empty:
                continue

            # Mientras habla un oficial, no escuchamos: si no, el sistema se
            # transcribe a si mismo y puede ejecutar lo que acaba de decir.
            if time.time() < mudo_hasta:
                grabando, frase, silencio = False, [], 0.0
                pre.clear()
                continue

            nivel = _rms(bloque.flatten())

            if not grabando:
                pre.append(bloque)
                if nivel >= UMBRAL_VOZ:
                    grabando = True
                    frase = list(pre)
                    silencio = 0.0
                continue

            frase.append(bloque)
            silencio = 0.0 if nivel >= UMBRAL_VOZ else silencio + seg_por_bloque
            largo = len(frase) * seg_por_bloque

            if silencio < SILENCIO_PARA_CORTAR and largo < MAX_DURACION_FRASE:
                continue

            audio = np.concatenate(frase, axis=0).flatten()
            grabando, frase, silencio = False, [], 0.0
            pre.clear()

            if audio.size / SAMPLE_RATE < MIN_DURACION_AUDIO_SEG:
                continue

            mudo_hasta = _procesar_frase(modelo, audio, ofi)

            # Lo que entro mientras pensabamos no sirve: puede tener la voz del
            # oficial, o la mitad de otra frase.
            while not cola.empty():
                cola.get()


def _procesar_frase(modelo, audio, ofi):
    """Transcribe, mira si llaman a un oficial, y ejecuta. Devuelve hasta
    cuando hay que dejar de escuchar (mientras contesta el oficial)."""
    t0 = time.time()
    texto = transcribir(modelo, audio)
    t1 = time.time()

    if not texto or len(texto) > MAX_CARACTERES_COMANDO:
        return 0.0

    clave, resto = ofi.detectar_oficial(texto)

    if clave is None:
        if EXIGIR_NOMBRE_DE_OFICIAL:
            print(f"[ignorado, no llama a nadie] \"{texto}\"")
            return 0.0

        # Sin nombre, el filtro es el parser estricto: la frase entera tiene
        # que ser un comando. Y no se consulta al LLM: interpretar lenguaje
        # libre de algo que quiza ni sea una orden es justo lo peligroso.
        accion = fase1.parsear_estricto(texto)
        if accion["action"] == "unknown":
            print(f"[ignorado, no es un comando] \"{texto}\"")
            return 0.0

        print(f"\n<- \"{texto}\"  (STT: {t1 - t0:.2f}s)")
        fase1.ejecutar_accion(accion)
        return time.time() + ofi.ULTIMO_AUDIO_SEG + MARGEN_ANTI_ECO

    nombre = ofi.OFICIALES[clave]["nombre"]
    print(f"\n{nombre} <- \"{texto}\"  (STT: {t1 - t0:.2f}s)")

    if not resto:
        # Lo llamaron y nada mas: que conteste y quede a la espera.
        accion = {"action": "a_la_orden", "oficial": clave, "raw": texto}
        ofi.responder(accion)
        return time.time() + ofi.ULTIMO_AUDIO_SEG + MARGEN_ANTI_ECO

    accion = fase1.parsear_comando(resto)

    if accion["action"] == "unknown" and USAR_LLM_FALLBACK:
        print(f"  [el parser no reconocio '{resto}', consultando al LLM...]")
        accion = llm_fallback.interpretar_con_llm(resto)

    fase1.ejecutar_accion(accion)
    print(f"  [tiempos] STT: {t1 - t0:.2f}s | TOTAL: {time.time() - t0:.2f}s")
    return time.time() + ofi.ULTIMO_AUDIO_SEG + MARGEN_ANTI_ECO


# ---------------------------------------------------------------------------
# Transcripcion: soporta backend "local" (faster-whisper) u "openai" (API)
# ---------------------------------------------------------------------------

def cargar_modelo():
    """Solo aplica al backend 'local'. Con backend 'openai' no hay nada que
    cargar (la transcripcion se hace via API en cada llamada), se devuelve
    None."""
    if STT_BACKEND != "local":
        print(f"Backend STT: '{STT_BACKEND}' (no requiere cargar modelo local).")
        return None

    print(f"Cargando modelo Whisper '{MODEL_SIZE}' (la primera vez puede "
          f"tardar mientras se descarga)...")
    # compute_type="int8" acelera bastante la inferencia en CPU, con una
    # perdida de precision generalmente aceptable para este caso de uso.
    modelo = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("Modelo cargado.")
    return modelo


def transcribir(modelo, audio):
    if audio.size == 0:
        return ""

    if STT_BACKEND == "openai":
        return transcribir_openai(audio, SAMPLE_RATE, language=LANGUAGE)

    # backend "local"
    segmentos, _info = modelo.transcribe(audio, language=LANGUAGE)
    texto = " ".join(seg.text.strip() for seg in segmentos)
    return texto.strip()


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def precalentar_microfono():
    """Abre y cierra el stream de audio una vez al arrancar.

    Fix de latencia: la PRIMERA vez que se abre el microfono, Windows tarda
    bastante mas (inicializa el driver de audio, negocia el formato, reserva
    el dispositivo). Si eso pasa recien cuando el usuario aprieta F12 por
    primera vez, ese delay se lo come el primer comando - y peor aun, se
    pierden los primeros milisegundos de lo que dijo. Abriendolo aca, el
    driver ya queda listo.
    """
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype='float32', device=DISPOSITIVO_ENTRADA):
            pass
        return True
    except Exception as e:
        print(f"  [!] No se pudo precalentar el microfono: {e}")
        return False


def precalentar_todo():
    """Hace todas las inicializaciones costosas ANTES de que el usuario diga
    el primer comando, para que ese primero no sea mas lento que el resto.
    Ver comentarios en cada funcion de precalentado para el detalle."""
    print("Precalentando (para que el primer comando no tenga delay extra)...")

    if MODO_ESCUCHA == "web":
        # En este modo Python no toca el microfono: lo abre la pagina.
        print("  - Microfono: lo maneja el browser, no Python")
    else:
        t0 = time.time()
        ok_mic = precalentar_microfono()
        try:
            info = sd.query_devices(DISPOSITIVO_ENTRADA, "input")
            cual = info["name"]
        except Exception:
            cual = "desconocido"
        print(f"  - Microfono: {'OK' if ok_mic else 'FALLO'} -> {cual} "
              f"({time.time() - t0:.2f}s)")

    if STT_BACKEND == "openai":
        t0 = time.time()
        ok_api = stt_openai_mod.precalentar()
        print(f"  - Conexion con la API de OpenAI: "
              f"{'OK' if ok_api else 'FALLO'} ({time.time() - t0:.2f}s)")

    # El parser y el catalogo de comandos tambien se "tocan" una vez aca,
    # para que Python termine de importar/compilar todo lo que haga falta.
    t0 = time.time()
    fase1.parsear_comando("precalentar")
    if USAR_LLM_FALLBACK:
        try:
            import catalogo_comandos
            catalogo_comandos.generar_tools_openai()
        except Exception:
            pass
    print(f"  - Parser y catalogo de comandos: OK ({time.time() - t0:.2f}s)")

    # Busqueda de la ventana del juego: enumerar todas las ventanas de
    # Windows es lento la primera vez. Se hace aca para que quede cacheada
    # (ver _ventana_cacheada en fase1_text_commands.py) y el primer comando
    # no tenga que pagarlo.
    t0 = time.time()
    ventana = fase1.encontrar_ventana_juego()
    if ventana is not None:
        print(f"  - Ventana del juego: OK, encontrada y cacheada "
              f"({time.time() - t0:.2f}s)")
    else:
        print(f"  - Ventana del juego: NO ENCONTRADA ({time.time() - t0:.2f}s)")
        print("    OJO: abri el juego DESDE DxWnd antes de dar comandos, o el")
        print("    primer comando va a tardar mas mientras la busca de nuevo.")


def main():
    # Via fase1: este script no importa oficiales por su cuenta, reusa todo lo
    # de la Fase 1 (parser, ejecutor, acuses de los oficiales).
    # Por voz no se escribe en la consola: el hook de F12 es global y el panel
    # muestra lo que pasa. Que el foco se quede en el juego.
    fase1.DEVOLVER_FOCO_CONSOLA = False

    ofi = getattr(fase1, "oficiales", None)
    if ofi is not None and ofi.PANEL_WEB and ofi.panel_web is not None:
        url = ofi.panel_web.iniciar()
        if url:
            print(f"Panel de la tripulacion: {url}  (abrilo al lado del juego)")

    print("=== SFC Voice Commander - Fase 2: comandos por VOZ ===")
    if MODO_ESCUCHA == "web":
        print("Modo: MICRÓFONO EN EL BROWSER (con cancelación de eco)")
        if STT_BACKEND == "openai":
            print("  [!] Igual que el modo activo: se transcribe todo lo que")
            print("      se escucha, y con backend 'openai' eso se paga por")
            print("      frase. Conviene STT_BACKEND = 'local'.")
    elif MODO_ESCUCHA == "boton":
        print("Modo: BOTÓN DEL PANEL (sin teclas físicas)")
    elif MODO_ESCUCHA == "activa":
        print("Modo: ESCUCHA ACTIVA (sin botón)")
        if STT_BACKEND == "openai":
            print("  [!] OJO: con escucha activa se transcribe TODO lo que se")
            print("      escucha, y con el backend 'openai' eso se paga por")
            print("      cada frase. Para este modo conviene STT_BACKEND =")
            print("      'local' (ver prueba #13).")
    else:
        print(f"Push-to-talk: mantené apretada '{PUSH_TO_TALK_KEY}' mientras hablás.")
    print(f"Presioná '{EXIT_KEY}' para salir.\n")

    modelo = cargar_modelo()

    precalentar_todo()

    print("\nListo.\n")

    if MODO_ESCUCHA == "web":
        escuchar_desde_la_web(modelo)
        return

    if MODO_ESCUCHA == "activa":
        escuchar_activo(modelo)
        return

    # Que pregunta hay que hacer para saber si el capitan esta hablando, y que
    # decirle por consola. Lo unico que cambia entre los dos modos.
    if MODO_ESCUCHA == "boton":
        panel = ofi.panel_web if ofi is not None else None
        if panel is None:
            print("[!] El modo boton necesita el panel web. Volviendo a F12.")
            apretado = lambda: keyboard.is_pressed(PUSH_TO_TALK_KEY)
            etiqueta = f"mantene '{PUSH_TO_TALK_KEY}' y hablá"
        else:
            panel.mostrar_boton(True)
            apretado = panel.boton_apretado
            etiqueta = "soltá el botón al terminar"
            print("Apretá el botón 🎙 del panel con el mouse y hablá.\n")
    else:
        apretado = lambda: keyboard.is_pressed(PUSH_TO_TALK_KEY)
        etiqueta = f"mantene '{PUSH_TO_TALK_KEY}' y hablá, soltá al terminar"
        print("Esperando comandos por voz...\n")

    while True:
        if keyboard.is_pressed(EXIT_KEY):
            print("Saliendo...")
            break

        if apretado():
            t0 = time.time()
            audio = grabar_mientras(apretado, etiqueta)

            if audio.size:
                pico = float(np.max(np.abs(audio)))
                if pico < 0.001:
                    print(f"[el microfono grabo SILENCIO ({pico:.5f} de pico). "
                          f"Corre probar_microfono.py para ver por que]\n")
                    continue

            duracion = audio.size / SAMPLE_RATE
            if duracion < MIN_DURACION_AUDIO_SEG:
                print(f"[grabacion de {duracion:.2f}s, demasiado corta para "
                      f"ser una orden - no se manda al STT]\n")
                continue

            texto = transcribir(modelo, audio)
            t1 = time.time()

            if not texto:
                print("[no se entendio nada, probá de nuevo]\n")
                continue

            if len(texto) > MAX_CARACTERES_COMANDO:
                print(f"Transcripcion descartada por ser demasiado larga "
                      f"({len(texto)} caracteres) - no parece una orden:")
                print(f"  \"{texto[:120]}...\"\n")
                continue

            print(f"Transcripcion: \"{texto}\"  (STT: {t1 - t0:.2f}s)")

            accion = fase1.parsear_comando(texto)

            if accion["action"] == "unknown" and USAR_LLM_FALLBACK:
                backend = llm_fallback.LLM_BACKEND
                print(f"  [parser de reglas no reconocio la frase, "
                      f"consultando al LLM (backend: {backend})...]")
                t_llm0 = time.time()
                accion = llm_fallback.interpretar_con_llm(texto)
                t_llm1 = time.time()
                print(f"  [LLM: {t_llm1 - t_llm0:.2f}s]")

            t_exec0 = time.time()
            fase1.ejecutar_accion(accion)
            t_exec1 = time.time()

            # Desglose de tiempos: sirve para ver DONDE se va la latencia
            # (transcripcion vs. enfoque de ventana + envio de teclas).
            print(f"  [tiempos] STT: {t1 - t0:.2f}s | "
                  f"ejecucion: {t_exec1 - t_exec0:.2f}s | "
                  f"TOTAL: {t_exec1 - t0:.2f}s")
            print()  # linea en blanco para separar cada comando en consola

        time.sleep(0.02)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario. Saliendo...")
        sys.exit(0)
