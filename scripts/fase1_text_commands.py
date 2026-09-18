"""
Fase 1 - Parser de comandos por texto (sin voz, sin red)

Objetivo: validar el mapeo "intencion -> teclas" con un loop simple de texto en
consola, usando el mismo juego "Star Trek: Starfleet Command Gold Edition" ya
validado en la Fase 0 (via DxWnd, en modo ventana).

Como usar:
1. Igual que en la Fase 0: abrir el juego DESDE DxWnd, entrar a una mision/
   tutorial donde la nave pueda moverse.
2. Instalar la dependencia nueva de este script (ademas de pydirectinput):
       pip install pygetwindow
3. Ajustar WINDOW_TITLE_KEYWORDS mas abajo si hace falta, para que coincida con
   el titulo real de la ventana del juego (ver seccion "Como encontrar el
   titulo" mas abajo).
4. Correr este script DESDE UNA CONSOLA COMO ADMINISTRADOR (imprescindible,
   ver ROADMAP.md Fase 0 - sin privilegios elevados el input no llega al juego):
       python fase1_text_commands.py
5. Escribir comandos en espanol en la consola, por ejemplo:
       alerta roja
       disparar
       media maquina
       cuarto de maquina
       alto total
       escudos al maximo
       seguir a esa nave / seguir a la amenaza
       ataquen con todo          (combo: max ECM + alpha strike)
       alejense a maxima velocidad  (combo: acelerar al 100%)
       ayuda                     (lista todos los comandos disponibles)
6. Escribir "salir" o "exit" para terminar el loop.

NOTA sobre COMBOS: una sola frase puede disparar varias teclas en secuencia
(ver diccionario COMBOS mas abajo). Es facil agregar mas combos nuevos:
agregar una entrada a COMBOS con "palabras" (lista de frases que lo activan),
"pasos" (lista de teclas o tuplas (tecla, cantidad) a ejecutar en orden), y
"descripcion" (para que aparezca en el listado de "ayuda").

IMPORTANTE - Manejo de foco de ventana (ida y vuelta automatica):
Como el comando se escribe en la consola (que tiene el foco mientras escribis),
el script NO depende de que vos hagas click manual en el juego antes de cada
accion. El flujo de foco es:
  1. Escribis el comando en la consola (foco en la consola, normal).
  2. Al confirmar con Enter, ANTES de mandar cualquier tecla, el script busca
     la ventana del juego por su titulo y la trae al frente automaticamente
     (funcion enfocar_ventana_juego).
  3. Se manda la tecla/combo/secuencia de velocidad al juego, ya enfocado.
  4. Al terminar de mandar la(s) tecla(s), el script vuelve a traer al frente
     la ventana de la consola automaticamente (funcion enfocar_consola), asi
     queda todo listo para escribir el siguiente comando comodamente sin tener
     que hacer Alt+Tab ni click manual en ningun momento.

Como encontrar el titulo exacto de la ventana del juego (si el matching
automatico no encuentra la ventana):
1. Con el juego abierto via DxWnd, abrir el Administrador de Tareas.
2. Pestaña "Detalles" (o "Procesos"), buscar el proceso del juego/DxWnd.
3. O simplemente correr en una consola de Python:
       import pygetwindow as gw
       print(gw.getAllTitles())
   y buscar en la lista impresa el titulo real de la ventana del juego, para
   copiarlo (o parte de el) en WINDOW_TITLE_KEYWORDS abajo.

Nota importante sobre velocidad: en esta fase, "cuarto/media/tres cuartos/toda
maquina" se traducen a una CANTIDAD FIJA Y APROXIMADA de pulsaciones de S/A
(ver STEPS_VELOCIDAD abajo). Esto es una aproximacion para validar el flujo
completo; la precision real (basada en la velocidad maxima real de la nave)
se aborda en la Fase 3 del roadmap (OCR del HUD o calibracion manual por nave).
"""

import re
import unicodedata
import time
import ctypes

import pydirectinput
import pygetwindow as gw

# Acuse de recibo hablado (opcional, ver oficiales.py). Si no esta el modulo,
# todo sigue funcionando exactamente igual, sin voz.
try:
    import oficiales
except ImportError:
    oficiales = None

# pydirectinput pausa 0.1s despues de CADA llamada elemental (~0.3s por press):
# medido el 17/09, era todo el costo de ejecucion que quedaba. Ver ROADMAP.
PAUSA_INTERNA_PYDIRECTINPUT = 0.0
pydirectinput.PAUSE = PAUSA_INTERNA_PYDIRECTINPUT

# Titulo EXACTO de la ventana del juego, confirmado en pruebas reales (ver
# scripts/probar_activar.py) corriendo pygetwindow.getAllWindows() con el
# juego abierto via DxWnd. Se usa como primer intento de busqueda (mas
# preciso, evita falsos positivos con otras ventanas que puedan contener
# palabras parecidas en el titulo, ej. un navegador con una pestana sobre el
# juego).
WINDOW_TITLE_EXACTO = "Starfleet Command"

# Palabras clave de respaldo (si por algun motivo el titulo exacto cambiara,
# ej. al abrir otra mision o actualizar el juego). Se usan solo si la
# busqueda por titulo exacto no encuentra nada.
WINDOW_TITLE_KEYWORDS = ["starfleet", "star trek", "dxwnd"]

# Si es True, tira una excepcion cuando no encuentra la ventana del juego (en
# vez de solo avisar por consola y seguir sin mandar la tecla).
FALLAR_SI_NO_ENCUENTRA_VENTANA = False

# Si es True, imprime informacion de debug sobre que ventana se encontro y
# cual quedo activa. Apagado por defecto porque esas consultas a la API de
# Windows + los prints se pagan en CADA comando. Prender solo para
# diagnosticar problemas de foco (ej. "la tecla no llega al juego").
DEBUG_VENTANA = False

# Pausa despues de enfocar la ventana del juego, antes de mandar la primera
# tecla. IMPORTANTE: se confirmo en pruebas (scripts/probar_tecla_con_foco.py)
# que con una pausa corta (0.15s) la tecla no llegaba al juego pese a que
# Windows ya marcaba la ventana como "activa" - haciendo falta una pausa mas
# larga para que el juego "asiente" el cambio de foco internamente.
#
# Measured with calibrar_latencia.py on the real machine (17/09): 0.2s still
# worked, so 0.3s keeps one step of margin. Re-run the calibrator if the
# machine or the DxWnd setup changes.
PAUSA_POST_ENFOQUE = 0.3

# Pausa entre teclas consecutivas dentro de un mismo comando. Importa mucho
# en los comandos de velocidad y combos, que mandan hasta 8 teclas.
# Measured on 17/09: 0.03s still worked, 0.05s keeps one step of margin.
PAUSA_ENTRE_TECLAS = 0.05


# ---------------------------------------------------------------------------
# 1) Normalizacion de texto
# ---------------------------------------------------------------------------

def normalizar(texto):
    """Pasa a minusculas, saca tildes/acentos y espacios extra."""
    texto = texto.lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def contiene_frase(texto_normalizado, frase):
    """Busca 'frase' dentro de 'texto_normalizado' respetando limites de
    palabra, para evitar falsos positivos como 'parar' matcheando dentro de
    'disparar'."""
    patron = r'\b' + re.escape(frase) + r'\b'
    return re.search(patron, texto_normalizado) is not None


# ---------------------------------------------------------------------------
# Manejo de foco de ventana: buscar y activar la ventana del juego antes de
# mandar cualquier tecla, para no depender de que el usuario haga click
# manualmente en el juego (la consola tiene el foco mientras se escribe).
# ---------------------------------------------------------------------------

# Cache de la ventana del juego (fix de latencia).
#
# gw.getAllWindows() enumera TODAS las ventanas abiertas de Windows y arma un
# objeto por cada una. Es la parte mas lenta del envio de un comando, y se
# estaba haciendo de cero en CADA comando. Como la ventana del juego no
# cambia mientras el juego sigue abierto, se cachea el objeto encontrado y se
# reusa; si el handle dejo de ser valido (se cerro o se reabrio el juego), se
# vuelve a buscar automaticamente.
_ventana_cacheada = None


def _ventana_sigue_viva(ventana):
    """True si la ventana cacheada todavia existe segun Windows."""
    if ventana is None:
        return False
    try:
        return bool(ctypes.windll.user32.IsWindow(ventana._hWnd))
    except Exception:
        return False


def encontrar_ventana_juego(usar_cache=True):
    """Busca la ventana del juego. Primero intenta por titulo EXACTO
    (case-insensitive y con strip de espacios, mas tolerante que
    getWindowsWithTitle "a pelo"). Si no encuentra nada asi, cae a la busqueda
    laxa por palabras clave (WINDOW_TITLE_KEYWORDS). Devuelve el objeto
    ventana de pygetwindow, o None si no encuentra ninguna con ningun metodo.

    NOTA: se volvio a este metodo (recorrer getAllWindows() a mano en vez de
    depender de gw.getWindowsWithTitle()) porque en una version anterior de
    este script, getWindowsWithTitle() con el titulo exacto dejo de encontrar
    la ventana en la practica (posible sensibilidad a mayusculas/espacios en
    esa funcion especifica de pygetwindow), rompiendo el enfoque que antes
    funcionaba con la busqueda laxa por substring.

    Si usar_cache=True (default) y ya se encontro la ventana antes, se
    devuelve la cacheada sin volver a enumerar todas las ventanas de Windows
    (ver comentario de _ventana_cacheada)."""
    global _ventana_cacheada

    if usar_cache and _ventana_sigue_viva(_ventana_cacheada):
        return _ventana_cacheada

    todas = gw.getAllWindows()

    # Intento 1: titulo exacto (case-insensitive, con strip)
    objetivo = WINDOW_TITLE_EXACTO.strip().lower()
    for ventana in todas:
        titulo = (ventana.title or "").strip().lower()
        if titulo == objetivo:
            _ventana_cacheada = ventana
            return ventana

    # Intento 2 (respaldo): palabras clave, busqueda laxa por substring
    for ventana in todas:
        titulo = (ventana.title or "").lower()
        if not titulo:
            continue
        if any(kw in titulo for kw in WINDOW_TITLE_KEYWORDS):
            _ventana_cacheada = ventana
            return ventana

    _ventana_cacheada = None
    return None


def enfocar_ventana_juego():
    """Intenta traer al frente la ventana del juego. Devuelve True si lo
    logro, False si no encontro la ventana (y no hizo nada)."""
    ventana = encontrar_ventana_juego()
    if ventana is None:
        msg = (f"No se encontro la ventana '{WINDOW_TITLE_EXACTO}' (titulo "
               f"exacto) ni ninguna con titulo que contenga "
               f"{WINDOW_TITLE_KEYWORDS} (respaldo). Ejecutar "
               "pygetwindow.getAllTitles() para ver los titulos disponibles "
               "y ajustar WINDOW_TITLE_EXACTO/WINDOW_TITLE_KEYWORDS.")
        if FALLAR_SI_NO_ENCUENTRA_VENTANA:
            raise RuntimeError(msg)
        print(f"  [!] {msg}")
        return False

    # Log de debug. Se apaga por defecto (DEBUG_VENTANA) porque acceder a
    # ventana.title hace una llamada extra a la API de Windows y el print a
    # consola tambien cuesta - chico, pero se paga en CADA comando. Ponerlo
    # en True si hay que diagnosticar problemas de foco de ventana.
    if DEBUG_VENTANA:
        print(f"  [debug] Ventana encontrada: titulo={ventana.title!r} "
              f"hwnd={ventana._hWnd}")

    try:
        if ventana.isMinimized:
            ventana.restore()
        # Se usa BringWindowToTop + SetForegroundWindow via ctypes en vez de
        # pygetwindow.activate(): en las pruebas (scripts/probar_activar.py y
        # probar_tecla_con_foco.py) se confirmo que este metodo, combinado con
        # una pausa mas larga despues (PAUSA_POST_ENFOQUE), es el que
        # efectivamente logra que la tecla llegue al juego. Con activate() +
        # una pausa corta, Windows marcaba la ventana como "activa" pero el
        # juego no llegaba a procesar la tecla igual.
        hwnd = ventana._hWnd
        ctypes.windll.user32.BringWindowToTop(hwnd)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        # Pausa mas larga para dar tiempo a que el juego "asiente" el cambio
        # de foco internamente antes de mandar la tecla.
        time.sleep(PAUSA_POST_ENFOQUE)

        # Debug: confirmar cual ventana quedo realmente activa segun Windows.
        # Tambien apagado por defecto: getActiveWindow() es otra llamada a la
        # API de Windows que se pagaba en cada comando.
        if DEBUG_VENTANA:
            activa = gw.getActiveWindow()
            print(f"  [debug] Ventana activa despues de enfocar: "
                  f"{activa.title if activa else None!r}")

        return True
    except Exception as e:
        print(f"  [!] No se pudo activar la ventana del juego: {e}")
        return False


def enfocar_consola():
    """Vuelve a traer al frente la ventana de ESTA consola (donde corre el
    script), despues de haber enfocado el juego para mandar una tecla. Usa
    ctypes/Win32 directo (GetConsoleWindow + SetForegroundWindow) en vez de
    buscar por titulo, porque el titulo de la consola puede variar segun como
    se la haya abierto."""
    try:
        import ctypes
        hwnd_consola = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd_consola:
            ctypes.windll.user32.SetForegroundWindow(hwnd_consola)
            time.sleep(0.1)
    except Exception as e:
        print(f"  [!] No se pudo volver el foco a la consola: {e}")


# ---------------------------------------------------------------------------
# 2) Diccionarios de sinonimos / vocabulario del dominio
#    (fuente: docs/hotkeys_sfc2.md - Gold Edition)
# ---------------------------------------------------------------------------

# Velocidad: frase reconocida -> nivel logico (0 a 4). El nivel se traduce a
# pasos de teclado en STEPS_VELOCIDAD, mas abajo.
SPEED_WORDS = {
    # Detener / velocidad 0
    "alto total": 0, "parar": 0, "detener": 0, "pare maquinas": 0,
    "parada de emergencia": 0, "frenar": 0,
    # 1/4
    "cuarto de maquina": 1, "un cuarto de maquina": 1, "un cuarto": 1,
    # 1/2
    "media maquina": 2, "mitad de maquina": 2, "mitad": 2,
    # 3/4
    "tres cuartos de maquina": 3, "tres cuartos": 3,
    # Full
    "toda maquina": 4, "maxima velocidad": 4, "maxima": 4,
    "avante toda": 4, "velocidad maxima": 4,
}

# Cantidad aproximada de pulsaciones de S (o A si negativo) para llegar a cada
# nivel desde una posicion neutra/desconocida. Es una heuristica para validar
# el flujo end-to-end; no es precisa (ver nota de Fase 3 en el docstring).
STEPS_VELOCIDAD = {
    0: ("a", 8),   # frenar fuerte: varios A para asegurar que baje a 0
    1: ("s", 2),
    2: ("s", 4),
    3: ("s", 6),
    4: ("s", 8),
}

def pct_a_nivel(pct):
    """Rounds an explicit percentage to the closest of the 5 speed levels.

    An exact percentage needs the real top speed of the current ship, which
    is Fase 3; rounding to the nearest quarter is the simplified approach the
    README describes, and beats ignoring the order.
    """
    pct = max(0, min(100, pct))
    return int(round(pct / 25.0))


# Alertas
# IMPORTANTE: pydirectinput/pyautogui esperan los nombres de teclas de letras
# en MINUSCULA para su mapeo interno (KEYBOARD_MAPPING). Mandar 'R' en vez de
# 'r' puede fallar silenciosamente o no ser reconocido - este fue el bug real
# que causaba que "alerta roja" no funcionara pese a que el foco de ventana
# estaba correcto.
ALERT_WORDS = {
    "alerta roja": "r",
    "roja": "r",
    "red alert": "r",
}

# ---------------------------------------------------------------------------
# Comandos que el capitan puede pedir de forma razonable pero que EL JUEGO NO
# SOPORTA por teclado. Se listan aparte para poder dar un mensaje claro que
# explique POR QUE no se puede hacer, en vez de un generico "comando no
# reconocido" (que hace pensar que es un problema de transcripcion o que
# falta un sinonimo, cuando en realidad la accion no existe en el juego).
#
# Ademas, marcarlos aca evita gastar una llamada al LLM de fallback: no tiene
# sentido preguntarle a un LLM por algo que sabemos de antemano que no se
# puede ejecutar.
# ---------------------------------------------------------------------------

NO_SOPORTADO = {
    "alerta_amarilla": {
        "palabras": ["alerta amarilla", "yellow alert", "amarilla"],
        "motivo": (
            "Yellow Alert EXISTE en el juego (boton en el HUD, pag. 101 del "
            "manual: sube escudos sin armar las armas), pero NO tiene tecla "
            "asignada - solo Red Alert ('r') la tiene. Por ahora hay que "
            "clickearlo. Probá con 'alerta roja' (sube escudos Y arma las "
            "armas)."
        ),
    },
    "interceptar": {
        "palabras": ["interceptar", "intercepten", "interceptalo",
                     "vamos hacia esa nave", "acercarse al objetivo"],
        "motivo": (
            "Intercept Target existe como orden del oficial de timon "
            "(pag. 103 del manual) pero NO tiene hotkey - se da desde el "
            "Helm Officer MFD con el mouse. Alternativas por voz: "
            "'seguir a esa nave' (Follow Target) u 'orbitar'."
        ),
    },
}

# Una sola palabra puede ser compatible con varios comandos distintos, y ahi
# NO hay que adivinar: el 18/09 el STT corto "media maquina" a "Maquina." y el
# LLM eligio cuarto de maquina, o sea que acelero la nave por una palabra a
# medias. Se matchea contra el texto COMPLETO (no con contiene_frase), asi que
# "media maquina" sigue resolviendo normal; solo cae aca la palabra suelta.
FRASES_AMBIGUAS = {
    "maquina": ("¿Qué velocidad? 'cuarto de máquina', 'media máquina', "
                "'tres cuartos de máquina' o 'toda máquina'."),
    "velocidad": ("¿Qué velocidad? 'media máquina', 'toda máquina', "
                  "'alto total', o 'velocidad al 70 por ciento'."),
    "alerta": "¿'alerta roja'? Es la única que tiene tecla en el juego.",
    "escudos": "¿'escudos al máximo'?",
    "objetivo": ("¿'objetivo más cercano', 'siguiente objetivo' o "
                 "'deseleccionar objetivo'?"),
    "enemigo": ("¿'siguiente enemigo', 'enemigo más cercano' o 'vamos al "
                "enemigo más cercano'?"),
    "escudo": "¿'escudos al máximo'?",
}

# Disparo / armas
# Nota: "ataquen" a secas se saco de FIRE_WORDS porque colisionaba con el
# combo ALL_OUT_ATTACK_WORDS ("ataquen con todo") - ahora FIRE_WORDS requiere
# frases un poco mas especificas para disparo simple.
FIRE_WORDS = ["disparar", "fuego", "abran fuego", "dispare", "disparen"]
ALPHA_STRIKE_WORDS = ["alpha strike", "fuego total", "disparen todo",
                      "todas las armas", "fuego a discrecion"]

# Combo: "ataquen con todo" - maximiza ECM (para reducir el daño recibido
# mientras se hace el ataque) y despues dispara Alpha Strike (todas las
# armas de todos los hardpoints de una vez). Ver ALL_OUT_ATTACK_STEPS mas
# abajo, junto a los demas combos.
ALL_OUT_ATTACK_WORDS = ["ataquen con todo", "ataque total", "todo el poder de fuego",
                        "usen todas las armas", "fuego con todo"]

# Combo: "alejarse a maxima velocidad" - se interpreta como acelerar a maxima
# velocidad nada mas, ignorando el "alejarse" (que implicaria girar 180°).
#
# Nota (13/09): se confirmo que Follow Target SI vira la nave, pero solo
# HACIA un objetivo - no sirve para huir (rumbo opuesto). Para eso haria
# falta el HET 180° (Numpad 5 = Start HET, ver manual pag. 103) o el control
# de rumbo absoluto de la Fase 6. Pendiente de evaluar si conviene sumar el
# HET 180° a este combo: es una maniobra brusca que estresa la nave y puede
# fallar, asi que meterla sin querer en una retirada podria ser contraproducente.
RETREAT_WORDS = ["alejense a maxima velocidad", "alejarse a maxima velocidad",
                 "retirada a maxima velocidad", "huyan a maxima velocidad"]

# Combo: "vamos al enemigo mas cercano" - selecciona el enemigo MAS CERCANO
# (backtick `), le pone rumbo con Follow Target (Numpad *) y acelera.
# Ver INTERCEPTAR_CERCANO_STEPS mas abajo para el detalle de los pasos.
IR_AL_CERCANO_WORDS = [
    "vamos al enemigo mas cercano", "al enemigo mas cercano",
    "vamos por el mas cercano", "atacar al mas cercano",
    "ir al enemigo mas cercano", "vayan al mas cercano",
    "acercarse al enemigo mas cercano",
]

# Combo: "busca un enemigo cualquiera" - cicla al proximo enemigo (Y), le pone
# rumbo y acelera. "Al azar" en la practica = el proximo del ciclo, que es lo
# mas parecido que permite el juego (no hay un comando de target aleatorio).
IR_A_CUALQUIERA_WORDS = [
    "busca un enemigo", "busquen un enemigo", "buscar enemigo",
    "vamos por cualquiera", "atacar a cualquiera",
    "vamos por otro enemigo", "busca otro enemigo",
    "elegi un enemigo", "buscar un objetivo",
    # 17/09: "Ir a enemigo" was not recognised and the LLM answered 404.
    "ir a enemigo", "ir al enemigo", "vamos por un enemigo",
]

# Escudos
# "escudos a maximo" (without the "l") reached the LLM fallback in the 17/09
# live test: the STT transcribes what was said, so the variants have to be here.
SHIELD_MAX_WORDS = ["escudos al maximo", "escudos a maximo", "reforzar escudos",
                    "refuercen escudos", "maximo escudo", "subir escudos",
                    "levantar escudos", "escudos arriba"]

# Camuflaje
CLOAK_WORDS = ["camuflaje", "cloaking", "activar camuflaje", "modo sigilo"]

# Deep Scan
DEEPSCAN_WORDS = ["escaneo profundo", "deep scan", "escanear"]

# Follow Target (Numpad *): seguir al target seleccionado.
#
# CONFIRMADO EN EL JUEGO (prueba del 13/09): Follow Target efectivamente
# **VIRA LA NAVE hacia el objetivo y lo persigue** - NO es solo seguimiento
# de camara. Esto es importante porque el manual nunca lo describe (lista la
# tecla en pag. 159 pero no la explica, a diferencia de Orbit/Intercept/
# Erratic), asi que hubo que verificarlo empiricamente.
#
# Consecuencia: es el comando de movimiento por voz mas util que tenemos, y
# el unico que apunta la nave a un objetivo sin depender del mouse. Los
# combos de aproximacion (ir_al_mas_cercano / ir_a_cualquiera) se apoyan en
# esto.
#
# El manual no distingue entre "nave" y "amenaza" - Follow Target actua sobre
# lo que este seleccionado como target en ese momento (ver T/SHIFT+T/Y/SHIFT+Y
# para cambiar de target antes de seguir).
FOLLOW_WORDS = [
    "seguir a esa nave", "seguir la nave", "seguir nave",
    "seguir a la amenaza", "seguir amenaza", "seguir al objetivo",
    "seguir objetivo", "seguir target", "sigan a esa nave",
    "sigan la nave", "persigan a esa nave", "perseguir nave",
    # 17/09: "Seguir enemigo" fell to the LLM, which picked cycling instead.
    "seguir enemigo", "seguir al enemigo", "seguir a ese enemigo",
    "perseguir al enemigo", "persigan al enemigo",
]

# Cycle target (T): ciclar al proximo target disponible (CUALQUIER unidad,
# incluye naves propias/neutrales). Util decir esto antes de "seguir a esa
# nave" si el target actual no es el deseado.
NEXT_TARGET_WORDS = ["siguiente objetivo", "cambiar de blanco",
                     "cambiar objetivo", "proximo objetivo"]

# Cycle target ENEMIGO (Y): igual que T pero ciclando SOLO entre enemigos.
# Documentado en el manual como "Target Enemy (cycles)" (pag. 157). Es el
# comando practico para ir "pasando" entre naves enemigas hasta encontrar la
# que se quiere seguir/atacar, sin que se cuelen unidades no hostiles.
NEXT_ENEMY_WORDS = ["siguiente enemigo", "proximo enemigo", "otro enemigo",
                    "cambiar de enemigo", "siguiente nave enemiga"]

# Ciclado en orden INVERSO (SHIFT+T / SHIFT+Y): para volver atras si nos
# pasamos de la nave que queriamos seleccionar.
PREV_TARGET_WORDS = ["objetivo anterior", "volver al objetivo anterior",
                     "blanco anterior"]
PREV_ENEMY_WORDS = ["enemigo anterior", "volver al enemigo anterior"]

# Target al enemigo mas cercano (backtick `)
NEAREST_ENEMY_WORDS = ["objetivo mas cercano", "enemigo mas cercano",
                       "apunten al mas cercano", "target mas cercano"]

# Deseleccionar target (\): soltar la nave que se tenia seleccionada.
DESELECT_WORDS = ["deseleccionar objetivo", "deseleccionar a objetivo",
                  "deseleccionar el objetivo", "deseleccionar target",
                  "soltar objetivo", "soltar el objetivo",
                  "cancelar objetivo", "olvidar objetivo"]

# ---------------------------------------------------------------------------
# Memoria de targets (teclas 5-8 y CTRL+5-8, pag. 157 del manual).
# Esto es lo mas cercano que el juego ofrece a "seguir a UNA NAVE DETERMINADA":
# no se puede nombrar una nave por voz, pero SI se puede guardar el target
# actual en una de 4 ranuras de memoria y volver a seleccionarlo despues.
#
# Flujo tipico por voz:
#   "siguiente enemigo"        -> cicla hasta la nave que se quiere
#   "guardar objetivo uno"     -> CTRL+5, queda memorizada en la ranura 1
#   ...(combate, se cambia de target varias veces)...
#   "objetivo uno"             -> 5, vuelve a seleccionar ESA misma nave
#   "seguir a esa nave"        -> Numpad *, la persigue
# ---------------------------------------------------------------------------

# Seleccionar target guardado (teclas 5, 6, 7, 8 -> ranuras 1 a 4)
TARGET_MEMORIA_WORDS = {
    "objetivo uno": "5", "objetivo 1": "5", "primer objetivo": "5",
    "objetivo dos": "6", "objetivo 2": "6", "segundo objetivo": "6",
    "objetivo tres": "7", "objetivo 3": "7", "tercer objetivo": "7",
    "objetivo cuatro": "8", "objetivo 4": "8", "cuarto objetivo": "8",
}

# Guardar el target actual en memoria (CTRL + 5..8)
GUARDAR_TARGET_WORDS = {
    "guardar objetivo uno": "5", "memorizar objetivo uno": "5",
    "guardar objetivo dos": "6", "memorizar objetivo dos": "6",
    "guardar objetivo tres": "7", "memorizar objetivo tres": "7",
    "guardar objetivo cuatro": "8", "memorizar objetivo cuatro": "8",
}

# ---------------------------------------------------------------------------
# Maniobras del Helm officer documentadas en la pag. 103 del manual. Son
# ordenes que delegan el pilotaje en el oficial de timon - o sea que NO
# requieren controlar el rumbo con el mouse, que es justo la limitacion que
# tenemos hoy (ver Fase 6 del ROADMAP).
# ---------------------------------------------------------------------------

# OJO - Intercept Target NO tiene hotkey: el manual lo documenta como una
# orden del Helm Officer MFD (pag. 103), pero NO aparece en la lista de
# teclas (pag. 157-159), a diferencia de Orbit/Follow/Erratic que si tienen.
# Se maneja como comando no soportado (ver NO_SOPORTADO) hasta confirmar en
# el juego si se le puede asignar una tecla desde Options -> Hotkeys.

# CONFIRMADO en el juego (18/09): Numpad "–" orbita. SFCquick pag. 24 dice
# Numpad "." y esta equivocado; vale SFCfullMan pag. 159.
TECLA_ORBITAR = "subtract"

# Orbit Target: pone la nave en orbita alrededor del target.
ORBIT_WORDS = ["orbitar", "orbitar objetivo", "ponerse en orbita",
               "orbiten la nave", "orbitar la nave"]

# Erratic Maneuvers (Numpad /): maniobras evasivas, genera 4 puntos de ECM
# natural. Nota del manual: dificulta tambien NUESTRA punteria y bloquea
# lanzar shuttles/minas/torpedos mientras este activo.
ERRATIC_WORDS = ["maniobras evasivas", "maniobra evasiva", "evasivas",
                 "zigzag", "maniobras erraticas"]

# Pedir ayuda / listar comandos disponibles (no manda ninguna tecla al juego)
HELP_WORDS = ["que comandos hay", "ayuda", "que puedo decir",
             "lista de comandos", "mostrar comandos", "help"]


# ---------------------------------------------------------------------------
# Combos: una sola frase dispara VARIAS sub-acciones en secuencia. Cada combo
# es una lista de "pasos", donde cada paso es una tecla simple (str) o una
# tupla (tecla, cantidad_de_veces) para repetir una tecla N veces (ej. subir
# varios niveles de velocidad). El enfoque de ventana se hace UNA sola vez
# para todo el combo, no una vez por cada paso, para no repetir la pausa de
# 1 segundo (PAUSA_POST_ENFOQUE) mas de lo necesario.
# ---------------------------------------------------------------------------

COMBOS = {
    # "ataquen con todo": maximizar ECM (reduce el daño que recibimos
    # mientras atacamos) + Alpha Strike (disparar todas las armas de todos
    # los hardpoints a la vez).
    "ataque_total": {
        "palabras": ALL_OUT_ATTACK_WORDS,
        "pasos": ["f", ("shift+z", 1)],  # f = Max ECM, shift+z = Alpha Strike
        "descripcion": "Maximiza ECM y dispara Alpha Strike (todas las armas)",
    },
    # "alejense a maxima velocidad": acelerar al maximo (ver nota en
    # RETREAT_WORDS sobre por que no incluye giro de 180°).
    "retirada_maxima": {
        "palabras": RETREAT_WORDS,
        "pasos": [("s", 8)],  # 8x 's' = nivel de velocidad 4 (toda maquina)
        "descripcion": "Acelera a máxima velocidad (no gira la nave)",
    },

    # -----------------------------------------------------------------------
    # "Buscar un objetivo e ir hacia el": selecciona + pone rumbo + acelera,
    # todo en una sola orden. Son los dos combos mas "completos" que se pueden
    # armar hoy solo con teclado.
    #
    # El paso de RUMBO usa Follow Target ("multiply"), CONFIRMADO en el juego
    # (prueba del 13/09): vira la nave hacia el objetivo y lo persigue. Ver la
    # nota arriba de FOLLOW_WORDS.
    # -----------------------------------------------------------------------

    # "vamos al enemigo mas cercano"
    "ir_al_mas_cercano": {
        "palabras": IR_AL_CERCANO_WORDS,
        "pasos": [
            "`",          # Target Nearest Enemy: selecciona el mas cercano
            "multiply",   # Follow Target: vira la nave hacia el objetivo
            ("s", 6),     # acelerar a ~3/4 de maquina para acercarse
        ],
        "descripcion": ("Selecciona el enemigo MAS CERCANO, pone rumbo hacia "
                        "él y acelera a 3/4 de máquina"),
    },

    # "busca un enemigo" (el proximo del ciclo - el juego no tiene target
    # aleatorio real, ver IR_A_CUALQUIERA_WORDS)
    "ir_a_cualquiera": {
        "palabras": IR_A_CUALQUIERA_WORDS,
        "pasos": [
            "y",          # Target Enemy (cycles): proximo enemigo del ciclo
            "multiply",   # Follow Target: vira la nave hacia el objetivo
            ("s", 6),     # acelerar a ~3/4 de maquina para acercarse
        ],
        "descripcion": ("Busca un enemigo (el siguiente del ciclo), pone "
                        "rumbo hacia él y acelera a 3/4 de máquina"),
    },
}


def listar_comandos():
    """Imprime en consola la lista de comandos disponibles, organizada por
    categoria, junto con un ejemplo de frase para cada uno. Se puede invocar
    diciendo/escribiendo cualquiera de las HELP_WORDS (ej. "ayuda")."""
    print("\n=== Comandos disponibles ===")
    print("(Decí o escribí una frase parecida a estos ejemplos)\n")

    print("VELOCIDAD:")
    print("  'alto total' / 'parar' / 'detener'          -> velocidad 0")
    print("  'cuarto de maquina'                          -> velocidad 25%")
    print("  'media maquina' / 'mitad'                    -> velocidad 50%")
    print("  'tres cuartos de maquina'                    -> velocidad 75%")
    print("  'toda maquina' / 'maxima velocidad'          -> velocidad 100%")
    print("  'velocidad al 70 por ciento'                 -> % explicito,")
    print("                                                  redondeado al cuarto mas cercano")

    print("\nARMAS:")
    print("  'disparar' / 'fuego' / 'abran fuego'         -> disparo simple")
    print("  'alpha strike' / 'fuego a discrecion'        -> disparar todo")
    print("  'objetivo mas cercano'                       -> target al enemigo mas cercano")
    print("  'siguiente objetivo' / 'cambiar de blanco'   -> ciclar target (todos)")
    print("  'siguiente enemigo' / 'otro enemigo'         -> ciclar SOLO enemigos")
    print("  'objetivo anterior' / 'enemigo anterior'     -> ciclar hacia atras")
    print("  'deseleccionar objetivo'                     -> soltar el target")

    print("\nSEGUIR A UNA NAVE DETERMINADA:")
    print("  (el juego no permite nombrar naves, pero se pueden memorizar)")
    print("  'siguiente enemigo'        -> cicla hasta encontrar la nave que querés")
    print("  'guardar objetivo uno'     -> la memoriza en la ranura 1 (hasta 4)")
    print("  'objetivo uno'             -> vuelve a seleccionar ESA nave")
    print("  'seguir a esa nave'        -> Follow Target, la persigue")

    print("\nMANIOBRAS (las pilotea el oficial de timon, sin mouse):")
    print("  'seguir a esa nave' / 'seguir a la amenaza'  -> vira hacia el")
    print("                                                  objetivo y lo persigue")
    print("  'orbitar' / 'ponerse en orbita'              -> Orbit Target")
    print("  'maniobras evasivas' / 'zigzag'              -> Erratic Maneuvers (+4 ECM)")

    print("\nDEFENSA:")
    print("  'alerta roja'                                -> Red Alert")
    print("  'escudos al maximo'                          -> panel de escudos")
    print("  'camuflaje' / 'modo sigilo'                  -> toggle cloak")
    print("  'escaneo profundo' / 'deep scan'             -> toggle deep scan")

    print("\nCOMBOS (varias acciones en una sola orden):")
    for datos in COMBOS.values():
        ejemplo = datos["palabras"][0]
        print(f"  '{ejemplo}'  -> {datos['descripcion']}")


    print("\nOTROS:")
    print("  'ayuda' / 'que comandos hay'                 -> mostrar esta lista")
    print("  'salir' / 'exit'                              -> terminar el programa")

    if NO_SOPORTADO:
        print("\nNO DISPONIBLES (el juego no los soporta):")
        for datos in NO_SOPORTADO.values():
            print(f"  '{datos['palabras'][0]}'  -> {datos['motivo']}")
    print()


# ---------------------------------------------------------------------------
# 3) Parser: texto -> accion estructurada (dict)
# ---------------------------------------------------------------------------

def parsear_comando(texto):
    t = normalizar(texto)

    # Ayuda / listar comandos (se chequea primero, no manda tecla al juego)
    if any(contiene_frase(t, w) for w in HELP_WORDS):
        return {"action": "help", "raw": texto}

    # Palabra suelta ambigua: se compara el texto COMPLETO sin puntuacion, asi
    # que no puede robarle un match a una frase mas larga.
    solo_palabras = re.sub(r'[^a-z0-9 ]+', '', t).strip()
    if solo_palabras in FRASES_AMBIGUAS:
        return {"action": "ambiguo", "motivo": FRASES_AMBIGUAS[solo_palabras],
                "raw": texto}

    # Comandos que el juego NO soporta (ver NO_SOPORTADO). Se chequea MUY
    # temprano, y en particular ANTES que ALERT_WORDS: "alerta amarilla"
    # contiene la palabra "alerta", asi que si se chequeara despues correria
    # riesgo de matchear un comando de alerta equivocado. Devuelve una accion
    # propia para poder explicar el motivo real al usuario.
    for nombre, datos in NO_SOPORTADO.items():
        if any(contiene_frase(t, w) for w in datos["palabras"]):
            return {"action": "no_soportado", "nombre": nombre,
                    "motivo": datos["motivo"], "raw": texto}

    # Combos (se chequean ANTES que los comandos individuales, porque son mas
    # especificos - ej. "ataquen con todo" no debe interpretarse como el
    # "disparar" simple de FIRE_WORDS)
    for nombre_combo, datos in COMBOS.items():
        if any(contiene_frase(t, w) for w in datos["palabras"]):
            return {"action": "combo", "combo": nombre_combo,
                    "pasos": datos["pasos"], "raw": texto}

    # Alpha strike (mas especifico, chequear antes que disparo simple)
    if any(contiene_frase(t, w) for w in ALPHA_STRIKE_WORDS):
        return {"action": "key_combo", "keys": ["shift", "z"], "raw": texto}

    # Disparo simple
    if any(contiene_frase(t, w) for w in FIRE_WORDS):
        return {"action": "key", "key": "z", "raw": texto}

    # Alertas
    for frase, tecla in ALERT_WORDS.items():
        if contiene_frase(t, frase):
            return {"action": "key", "key": tecla, "raw": texto}

    # Escudos al maximo
    if any(contiene_frase(t, w) for w in SHIELD_MAX_WORDS):
        return {"action": "key", "key": "k", "raw": texto}

    # Camuflaje
    if any(contiene_frase(t, w) for w in CLOAK_WORDS):
        return {"action": "key", "key": "x", "raw": texto}

    # Deep scan
    if any(contiene_frase(t, w) for w in DEEPSCAN_WORDS):
        return {"action": "key", "key": "i", "raw": texto}

    # Follow Target (Numpad *) - "multiply" es el nombre de tecla que espera
    # pydirectinput para el asterisco del teclado numerico.
    if any(contiene_frase(t, w) for w in FOLLOW_WORDS):
        return {"action": "key", "key": "multiply", "raw": texto}

    # --- Memoria de targets (lo mas cercano a "seguir a UNA nave concreta") ---
    # GUARDAR se chequea ANTES que SELECCIONAR: "guardar objetivo uno"
    # contiene "objetivo uno", asi que el orden inverso lo matchearia mal.
    for frase, tecla in GUARDAR_TARGET_WORDS.items():
        if contiene_frase(t, frase):
            return {"action": "key_combo", "keys": ["ctrl", tecla],
                    "raw": texto}

    for frase, tecla in TARGET_MEMORIA_WORDS.items():
        if contiene_frase(t, frase):
            return {"action": "key", "key": tecla, "raw": texto}

    # --- Ciclado de targets ---
    # Las variantes "anterior" (SHIFT+) van ANTES que las normales, porque
    # "objetivo anterior" tambien contendria palabras de las listas normales.
    if any(contiene_frase(t, w) for w in PREV_ENEMY_WORDS):
        return {"action": "key_combo", "keys": ["shift", "y"], "raw": texto}

    if any(contiene_frase(t, w) for w in PREV_TARGET_WORDS):
        return {"action": "key_combo", "keys": ["shift", "t"], "raw": texto}

    # Cycle target ENEMIGO (Y) - mas especifico que el ciclado general
    if any(contiene_frase(t, w) for w in NEXT_ENEMY_WORDS):
        return {"action": "key", "key": "y", "raw": texto}

    # Deseleccionar target (\)
    if any(contiene_frase(t, w) for w in DESELECT_WORDS):
        return {"action": "key", "key": "\\", "raw": texto}

    # --- Maniobras del Helm officer ---
    if any(contiene_frase(t, w) for w in ORBIT_WORDS):
        return {"action": "key", "key": TECLA_ORBITAR, "raw": texto}

    if any(contiene_frase(t, w) for w in ERRATIC_WORDS):
        return {"action": "key", "key": "divide", "raw": texto}

    # Cycle target (T)
    if any(contiene_frase(t, w) for w in NEXT_TARGET_WORDS):
        return {"action": "key", "key": "t", "raw": texto}

    # Target al enemigo mas cercano (backtick)
    if any(contiene_frase(t, w) for w in NEAREST_ENEMY_WORDS):
        return {"action": "key", "key": "`", "raw": texto}

    # Velocidad con numero explicito: "velocidad al 70 por ciento" / "70%"
    m = re.search(r'(\d+)\s*(por ciento|%)', t)
    if m and contiene_frase(t, 'velocidad'):
        pct = int(m.group(1))
        return {"action": "set_speed_pct", "pct": pct, "raw": texto}

    # Velocidad por nivel con nombre (cuarto, media, etc.) - se chequea al
    # final porque frases cortas como "parar"/"frenar" podrian aparecer
    # dentro de oraciones mas largas de otros comandos.
    # Se ordena por longitud de frase descendente para priorizar matches
    # mas especificos (ej. "tres cuartos de maquina" antes que "tres cuartos").
    for frase, nivel in sorted(SPEED_WORDS.items(), key=lambda kv: -len(kv[0])):
        if contiene_frase(t, frase):
            return {"action": "set_speed", "level": nivel, "raw": texto}

    return {"action": "unknown", "raw": texto}


# ---------------------------------------------------------------------------
# 4) Ejecutor: accion estructurada -> pulsaciones reales de teclado
# ---------------------------------------------------------------------------

def _presionar_paso(paso, pausa_entre_teclas):
    """Ejecuta un paso individual de un combo. Un paso puede ser:
    - un string simple, ej. "f" -> press('f')
    - un string con "+", ej. "shift+z" -> keyDown/press/keyUp combinados
    - una tupla (tecla, cantidad) -> repetir esa tecla N veces
    """
    if isinstance(paso, tuple):
        tecla, cantidad = paso
        if "+" in tecla:
            modificador, tecla_final = tecla.split("+")
            for _ in range(cantidad):
                pydirectinput.keyDown(modificador)
                time.sleep(0.05)
                pydirectinput.press(tecla_final)
                time.sleep(0.05)
                pydirectinput.keyUp(modificador)
                time.sleep(pausa_entre_teclas)
        else:
            for _ in range(cantidad):
                pydirectinput.press(tecla)
                time.sleep(pausa_entre_teclas)
    else:
        if "+" in paso:
            modificador, tecla_final = paso.split("+")
            pydirectinput.keyDown(modificador)
            time.sleep(0.05)
            pydirectinput.press(tecla_final)
            time.sleep(0.05)
            pydirectinput.keyUp(modificador)
        else:
            pydirectinput.press(paso)
        time.sleep(pausa_entre_teclas)


def _enviar_nivel_velocidad(nivel, pausa_entre_teclas):
    """Presses the S/A sequence of a speed level (see STEPS_VELOCIDAD)."""
    tecla, cantidad = STEPS_VELOCIDAD[nivel]
    for _ in range(cantidad):
        pydirectinput.press(tecla)
        time.sleep(pausa_entre_teclas)


def ejecutar_accion(accion, pausa_entre_teclas=None):
    if pausa_entre_teclas is None:
        pausa_entre_teclas = PAUSA_ENTRE_TECLAS
    tipo = accion.get("action")

    # Acciones que efectivamente mandan alguna tecla: enfocar el juego primero.
    # (help, no_soportado y unknown no mandan nada, no hace falta cambiar el foco)
    if tipo in ("key", "key_combo", "set_speed", "set_speed_pct", "combo"):
        enfocado = enfocar_ventana_juego()
        if not enfocado:
            print("  [!] Se intenta mandar la tecla igual, pero puede que no "
                  "llegue al juego si el foco no quedo en la ventana correcta.")

    if tipo == "help":
        listar_comandos()

    elif tipo == "combo":
        nombre = accion["combo"]
        pasos = accion["pasos"]
        descripcion = COMBOS[nombre]["descripcion"]
        print(f"  -> Combo '{nombre}': {descripcion}")
        for paso in pasos:
            _presionar_paso(paso, pausa_entre_teclas)

    elif tipo == "key":
        tecla = accion["key"]
        print(f"  -> Tecla: {tecla}")
        pydirectinput.press(tecla)

    elif tipo == "key_combo":
        teclas = accion["keys"]
        print(f"  -> Combo: {'+'.join(teclas)}")
        pydirectinput.keyDown(teclas[0])
        time.sleep(0.05)
        pydirectinput.press(teclas[1])
        time.sleep(0.05)
        pydirectinput.keyUp(teclas[0])

    elif tipo == "set_speed":
        nivel = accion["level"]
        tecla, cantidad = STEPS_VELOCIDAD[nivel]
        print(f"  -> Velocidad nivel {nivel}: {cantidad}x tecla '{tecla}' "
              f"(aproximado, ver Fase 3 para precision real)")
        _enviar_nivel_velocidad(nivel, pausa_entre_teclas)

    elif tipo == "set_speed_pct":
        pct = accion["pct"]
        nivel = pct_a_nivel(pct)
        tecla, cantidad = STEPS_VELOCIDAD[nivel]
        print(f"  -> Velocidad {pct}% -> nivel {nivel} de 4 (~{nivel * 25}%, "
              f"el mas cercano): {cantidad}x tecla '{tecla}' "
              f"(aproximado, ver Fase 3 para precision real)")
        _enviar_nivel_velocidad(nivel, pausa_entre_teclas)

    elif tipo == "ambiguo":
        print(f"  -> '{accion['raw']}' es ambiguo, no se ejecuta nada. "
              f"{accion['motivo']}")

    elif tipo == "no_soportado":
        print(f"  -> No se puede ejecutar '{accion['raw']}': {accion['motivo']}")

    elif tipo == "unknown":
        print(f"  -> Comando no reconocido: '{accion['raw']}'")

    else:
        print(f"  -> Tipo de accion desconocido: {tipo}")

    # Si se enfoco el juego para esta accion, volver el foco a la consola
    # para poder seguir escribiendo el proximo comando comodamente.
    if tipo in ("key", "key_combo", "set_speed", "set_speed_pct", "combo"):
        enfocar_consola()

    # El oficial contesta AL FINAL, con la tecla ya mandada: asi el juego ya
    # reacciono mientras suena la voz, en vez de sentirse lento.
    if oficiales is not None:
        oficiales.responder(accion)


# ---------------------------------------------------------------------------
# 5) Loop principal
# ---------------------------------------------------------------------------

def main():
    # Import diferido (no a nivel de modulo) para evitar import circular:
    # llm_fallback importa catalogo_comandos, que a su vez importa este mismo
    # modulo (fase1_text_commands) para leer los diccionarios de comandos.
    usar_llm_fallback = True
    try:
        import llm_fallback
    except ImportError:
        usar_llm_fallback = False

    print("=== SFC Voice Commander - Fase 1: comandos por texto ===")
    print("Escribi un comando (ej: 'alerta roja', 'disparar', 'media maquina')")
    print("Escribi 'ayuda' para ver todos los comandos, 'salir' o 'exit' para terminar.\n")
    if usar_llm_fallback:
        print("(LLM fallback disponible: si el parser de reglas no reconoce "
              "una frase, se consulta a Ollama antes de darla por perdida)\n")

    while True:
        try:
            texto = input("Capitan, orden: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if not texto:
            continue
        if normalizar(texto) in ("salir", "exit", "quit"):
            print("Saliendo...")
            break

        accion = parsear_comando(texto)

        if accion["action"] == "unknown" and usar_llm_fallback:
            backend = llm_fallback.LLM_BACKEND
            print(f"  [parser de reglas no reconocio la frase, consultando "
                  f"al LLM (backend: {backend})...]")
            accion = llm_fallback.interpretar_con_llm(texto)

        ejecutar_accion(accion)


if __name__ == "__main__":
    main()
