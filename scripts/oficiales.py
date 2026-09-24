"""
Tripulacion virtual: quien contesta cada orden, y con que frase.

Las respuestas son ACUSES DE RECIBO, no conversacion: "si capitan", "no se
como, capitan". No hay LLM de por medio ni texto dinamico - por eso el set de
frases es fijo y chico, y por eso el audio se puede generar UNA sola vez y
guardarlo en disco (ver generar_voces.py). Reproducir un wav tarda ~0ms, asi
que la voz no agrega latencia al comando.

COMO SE USA (ya enganchado en fase1_text_commands.ejecutar_accion):
    import oficiales
    oficiales.responder(accion)

El orden importa: PRIMERO se aprieta la tecla, DESPUES habla el oficial. Asi
el juego ya reacciono mientras suena la voz, en vez de sentirse lento.

AUDIO: si no hay wav generado, se imprime la frase igual y no pasa nada mas.
Es opcional a proposito - el sistema funciona sin voz.
Generar los wav:  python generar_voces.py   (una vez, necesita OPENAI_API_KEY)
"""

import os
import random
import unicodedata

# Carpeta con los wav generados por generar_voces.py. Si no existe, el sistema
# imprime la frase y sigue.
DIR_AUDIO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "audio", "oficiales")

# Poner en False para dejar solo el texto, sin reproducir audio.
VOZ_ACTIVADA = True

# Panel web con el retrato del oficial que contesta (ver panel_web.py).
PANEL_WEB = True

try:
    import panel_web
except ImportError:
    panel_web = None

# winsound es de la libreria estandar de Windows y reproduce wav sin instalar
# nada. En la Mac no existe: se degrada a solo texto.
try:
    import winsound
except ImportError:
    winsound = None


# ---------------------------------------------------------------------------
# El plantel. Los roles y su reparto de comandos salen del Officer MFD del
# propio juego (pag. 102 del manual), no de un invento nuestro.
#
# "teclas" es que comandos le tocan a cada uno. Se mapea por TECLA porque es
# el atomo que devuelve el parser, y no cambia aunque se agreguen sinonimos.
# ---------------------------------------------------------------------------

OFICIALES = {
    "timon": {
        "nombre": "T'Lara",
        "raza": "vulcana",
        "sexo": "femenino",
        "rango": "alferez",
        "alias": ["timonel", "piloto", "alferez", "lara"],
        "uniforme": "rojo",
        "teclas": {"a", "s", "multiply", "subtract", "divide"},
    },
    "armas": {
        "nombre": "Korak",
        "raza": "klingon",
        "sexo": "masculino",
        "rango": "teniente",
        "alias": ["artillero", "armas", "korak"],
        "uniforme": "dorado",
        "teclas": {"z", "y", "t", "`", "\\", "5", "6", "7", "8"},
    },
    "defensa": {
        "nombre": "Zheva",
        "raza": "andoriana",
        "sexo": "femenino",
        "rango": "teniente",
        "alias": ["defensa", "tactico", "zheva"],
        "uniforme": "dorado",
        "teclas": {"r", "k", "x", "f"},
    },
    "ciencias": {
        "nombre": "Delon",
        "raza": "trill",
        "sexo": "masculino",
        "rango": "teniente",
        "alias": ["ciencias", "cientifico", "delon"],
        "uniforme": "azul",
        "teclas": {"i"},
    },
    "ingenieria": {
        "nombre": "Grax",
        "raza": "boliano",
        "sexo": "masculino",
        "rango": "comandante",
        "alias": ["ingeniero", "ingenieria", "grax"],
        "uniforme": "dorado",
        # Sin comandos todavia: el juego tiene reparaciones y energia, nosotros no.
        "teclas": set(),
    },
    "seguridad": {
        "nombre": "Pell",
        "raza": "tellarita",
        "sexo": "femenino",
        "rango": "teniente",
        "alias": ["seguridad", "marines", "pell"],
        "uniforme": "dorado",
        # Hit and run raids y abordajes existen en el juego, sin comandos nuestros.
        "teclas": set(),
    },
    "comunicaciones": {
        "nombre": "Nima",
        "raza": "betazoide",
        "sexo": "femenino",
        "rango": "alferez",
        "alias": ["comunicaciones", "comunicacion", "nima"],
        "uniforme": "dorado",
        "teclas": set(),
    },
    # Comodin: contesta lo que no es de nadie en particular, y todos los
    # errores. Es la voz que ya existe hoy, antes de que haya oficiales.
    "computadora": {
        "nombre": "Computadora",
        "raza": None,
        "sexo": None,
        "rango": None,
        "alias": ["computadora"],
        "uniforme": None,
        "teclas": set(),
    },
}

# Combos: los pasos son de varios oficiales, asi que se asigna a mano quien da
# el acuse. Criterio: el que ejecuta el paso que define la intencion.
OFICIAL_POR_COMBO = {
    "ataque_total": "armas",
    "retirada_maxima": "timon",
    "ir_al_mas_cercano": "timon",
    "ir_a_cualquiera": "timon",
}


# ---------------------------------------------------------------------------
# Las frases. Cuatro desenlaces posibles, varias variantes de cada uno para
# que no suene siempre igual. Cortas a proposito: mientras habla un oficial no
# se puede dar otra orden (ver WISHLIST 3.2.2).
# ---------------------------------------------------------------------------

RESPUESTAS = {
    # La orden se ejecuto.
    "ok": {
        "timon": ["Sí, capitán.", "Enseguida, capitán.", "A la orden."],
        "armas": ["Sí, capitán.", "Con gusto, capitán.", "Armas listas."],
        "defensa": ["Sí, capitán.", "Afirmativo.", "Hecho, capitán."],
        "ciencias": ["Sí, capitán.", "Afirmativo, capitán."],
        "ingenieria": ["Sí, capitán.", "En camino, capitán."],
        "seguridad": ["Sí, capitán.", "Entendido, capitán."],
        "comunicaciones": ["Sí, capitán.", "En ello, capitán."],
        "computadora": ["Afirmativo.", "Orden ejecutada."],
    },
    # El parser y el LLM no entendieron la orden.
    "no_entendido": {
        "computadora": ["No sé cómo hacer eso, capitán.",
                        "No comprendo la orden, capitán."],
    },
    # Una palabra suelta que encaja con varios comandos (FRASES_AMBIGUAS).
    "ambiguo": {
        "computadora": ["¿Podría precisar, capitán?",
                        "Necesito más precisión, capitán."],
    },
    # El juego no soporta ese comando (NO_SOPORTADO).
    "no_soportado": {
        "computadora": ["Eso no está a mi alcance, capitán.",
                        "No es posible, capitán."],
    },
}


def oficial_para(accion):
    """Devuelve a que oficial le toca la accion. Cae en 'computadora' si no es
    de nadie: los errores no tienen dueno."""
    tipo = accion.get("action")

    if tipo == "combo":
        return OFICIAL_POR_COMBO.get(accion.get("combo"), "computadora")

    if tipo in ("set_speed", "set_speed_pct"):
        return "timon"

    if tipo == "key":
        tecla = accion.get("key")
        for nombre, datos in OFICIALES.items():
            if tecla in datos["teclas"]:
                return nombre

    if tipo == "key_combo":
        # De ["shift", "z"] o ["ctrl", "5"], el modificador no identifica nada:
        # decide la segunda tecla.
        teclas = accion.get("keys") or []
        if len(teclas) >= 2:
            for nombre, datos in OFICIALES.items():
                if teclas[1] in datos["teclas"]:
                    return nombre

    return "computadora"


def _desenlace(accion):
    tipo = accion.get("action")
    if tipo in ("key", "key_combo", "set_speed", "set_speed_pct", "combo"):
        return "ok"
    if tipo == "ambiguo":
        return "ambiguo"
    if tipo == "no_soportado":
        return "no_soportado"
    if tipo == "unknown":
        return "no_entendido"
    return None  # help y cualquier otra cosa no llevan acuse


def elegir_frase(accion):
    """Devuelve (clave_oficial, frase) o (None, None) si esta accion no lleva
    acuse de recibo."""
    desenlace = _desenlace(accion)
    if desenlace is None:
        return None, None

    por_oficial = RESPUESTAS[desenlace]
    clave = oficial_para(accion) if desenlace == "ok" else "computadora"
    frases = por_oficial.get(clave) or por_oficial["computadora"]
    return clave, random.choice(frases)


def _nombre_archivo(clave_oficial, frase):
    """Nombre estable del wav de una frase, para que generar_voces.py y esto
    coincidan sin mantener un indice aparte. Sin tildes ni eñes: un nombre de
    archivo ASCII evita sorpresas al reproducirlo desde Windows."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", frase.lower())
        if unicodedata.category(c) != "Mn"
    )
    limpio = "".join(c if c.isalnum() and c.isascii() else "_"
                     for c in sin_tildes)
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return f"{clave_oficial}__{limpio.strip('_')}.wav"


# Para avisar una sola vez por corrida, en vez de en cada comando.
_ya_avise_sin_audio = False


def reproducir(clave_oficial, frase):
    """Reproduce el wav de esa frase si existe. Asincrono: no bloquea el loop
    de comandos. Devuelve True si sono algo."""
    global _ya_avise_sin_audio

    if not VOZ_ACTIVADA or winsound is None:
        return False

    ruta = os.path.join(DIR_AUDIO, _nombre_archivo(clave_oficial, frase))
    if not os.path.isfile(ruta):
        # Que la falta de sonido nunca sea silenciosa: si no se avisa, parece
        # que la voz fallo cuando en realidad nunca se genero el archivo.
        if not _ya_avise_sin_audio:
            _ya_avise_sin_audio = True
            print(f"  [!] No hay audio generado ({os.path.abspath(ruta)}). "
                  f"Corre `python generar_voces.py` para tener voz.")
        return False

    try:
        winsound.PlaySound(ruta, winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
    except Exception as e:
        print(f"  [!] No se pudo reproducir la voz: {e}")
        return False


def responder(accion):
    """Imprime el acuse del oficial que corresponde y, si hay wav generado, lo
    reproduce. Se llama DESPUES de mandar las teclas, nunca antes."""
    clave, frase = elegir_frase(accion)
    if frase is None:
        return

    datos = OFICIALES[clave]
    quien = datos["nombre"]
    print(f"  [{quien}] {frase}")
    reproducir(clave, frase)

    if PANEL_WEB and panel_web is not None:
        panel_web.publicar(clave, quien, frase, accion.get("raw"))


if __name__ == "__main__":
    # python oficiales.py -> muestra el plantel y todas las frases a generar.
    print("=== Plantel ===")
    for clave, d in OFICIALES.items():
        teclas = ", ".join(sorted(d["teclas"])) or "(sin comandos propios)"
        raza = d["raza"] or "-"
        print(f"  {d['nombre']:12} {clave:16} {raza:12} teclas: {teclas}")

    print("\n=== Frases a generar en audio ===")
    total = 0
    for desenlace, por_oficial in RESPUESTAS.items():
        for clave, frases in por_oficial.items():
            for frase in frases:
                total += 1
                print(f"  {_nombre_archivo(clave, frase)}")
    print(f"\n{total} archivos de audio en total.")
