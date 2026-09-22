"""
Genera UNA VEZ los retratos de los oficiales con la API de imagenes de OpenAI,
y los deja en images/oficiales/.

Se corre una sola vez. Generar una imagen tarda segundos y cuesta, asi que
NUNCA se genera en vivo: el plantel es fijo, se genera y se guarda.

Los prompts NO se escriben a mano: se arman desde la tabla OFICIALES de
oficiales.py (raza, sexo, rol, color de uniforme), asi que agregar un oficial
nuevo alcanza para que aparezca aca.

COMO USAR:
    pip install openai
    (con OPENAI_API_KEY configurada, ver stt_openai.py)
    python generar_retratos.py

Vuelve a generar solo lo que falta. Para rehacer todo:
    python generar_retratos.py --rehacer
Para ver los prompts sin gastar nada:
    python generar_retratos.py --solo-prompts
"""

import base64
import os
import sys

import config
import oficiales

# El SDK se importa dentro de main(), no aca: asi --solo-prompts sirve para
# revisar los prompts en cualquier maquina, sin tener openai instalado.

MODELO_IMAGEN = "gpt-image-1"

# Tamaño cuadrado: los retratos se muestran chicos al lado del juego.
TAMANIO = "1024x1024"

# Estilo del plantel. Los dos salen de las referencias de images/image.png.
# IMPORTANTE: elegir UNO y que todo el plantel sea coherente - mezclar
# ilustracion con fotorrealismo se nota feo cuando se ven juntos.
#   "ilustrado"      -> perdona mejor las caras generadas y se lee bien en chico
#   "fotorrealista"  -> mas impactante de a uno, mas dificil de mantener parejo
ESTILO = "ilustrado"

ESTILOS = {
    "ilustrado": (
        "digital comic-book illustration, bold clean linework, cel shading, "
        "rich saturated color"
    ),
    "fotorrealista": (
        "photorealistic portrait photography, shallow depth of field, "
        "cinematic lighting"
    ),
}

# Como se ve cada uniforme, en la epoca de las imagenes de referencia.
UNIFORMES = {
    "rojo": "a burgundy red and black command-division uniform",
    "dorado": "a mustard gold and black operations-division uniform",
    "azul": "a teal blue and black sciences-division uniform",
}

# Rasgos por raza. Sin nombrar franquicias ni personajes: se describe el
# aspecto, que es lo que el modelo necesita y evita que rechace el pedido.
RAZAS = {
    "vulcana": "pointed ears, severe straight black bowl-cut hair, upswept "
               "eyebrows, completely neutral serene expression",
    "klingon": "prominent ridged forehead, long dark braided hair, heavy "
               "brow, fierce proud expression, dark warrior complexion",
    "andoriana": "pale blue skin, white hair, two slender antennae rising "
                 "from the forehead, sharp alert expression",
    "trill": "a line of dark brown spots running down each side of the face "
             "from forehead to neck, warm human-like features",
    "boliano": "light blue skin, completely bald, a vertical cartilage ridge "
               "running down the middle of the face, friendly expression",
    "tellarita": "stocky build, porcine snout-like nose, small deep-set eyes, "
                 "coarse facial hair, gruff stubborn expression",
    "betazoide": "entirely solid black eyes with no visible iris, dark wavy "
                 "hair, warm empathic expression",
}

SEXOS = {"femenino": "female", "masculino": "male"}

# Roles en ingles, para el prompt.
ROLES = {
    "timon": "flight controller at the helm",
    "armas": "weapons officer",
    "defensa": "tactical and defense officer",
    "ciencias": "science officer",
    "ingenieria": "chief engineer",
    "seguridad": "chief of security",
    "comunicaciones": "communications officer",
}


def armar_prompt(clave, datos):
    """Arma el prompt de un oficial desde la tabla de oficiales.py."""
    rasgos = RAZAS.get(datos["raza"], "")
    sexo = SEXOS.get(datos.get("sexo"), "")
    uniforme = UNIFORMES.get(datos["uniforme"], "")
    rol = ROLES.get(clave, "bridge officer")

    return (
        f"Character portrait of a {sexo} science-fiction starship {rol}, "
        f"an alien with {rasgos}. Wearing {uniforme} with a metallic "
        f"insignia badge on the chest. Seated on the bridge of a starship, "
        f"softly blurred consoles and screens behind. Head and shoulders, "
        f"facing the viewer, centered. {ESTILOS[ESTILO]}. No text, no "
        f"lettering, no watermark."
    )


def main():
    rehacer = "--rehacer" in sys.argv
    solo_prompts = "--solo-prompts" in sys.argv

    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "images", "oficiales")

    # La computadora no tiene cara: es voz sin cuerpo.
    a_generar = {c: d for c, d in oficiales.OFICIALES.items()
                 if d.get("raza")}

    if solo_prompts:
        for clave, datos in a_generar.items():
            print(f"\n=== {datos['nombre']} ({clave}) ===")
            print(armar_prompt(clave, datos))
        print(f"\n{len(a_generar)} retratos, estilo '{ESTILO}'. "
              f"Sin --solo-prompts se generan de verdad.")
        return 0

    try:
        api_key = config.api_key()
    except RuntimeError as e:
        print(f"[!] {e}")
        return 1
    print(f"API key: {config.de_donde_salio()}")

    from openai import OpenAI
    cliente = OpenAI(api_key=api_key)
    os.makedirs(destino, exist_ok=True)

    generados = saltados = fallados = 0

    for clave, datos in a_generar.items():
        ruta = os.path.join(destino, f"{clave}.png")

        if os.path.isfile(ruta) and not rehacer:
            saltados += 1
            continue

        print(f"  generando {datos['nombre']} ({datos['raza']}, "
              f"{datos.get('sexo')})...")
        try:
            respuesta = cliente.images.generate(
                model=MODELO_IMAGEN,
                prompt=armar_prompt(clave, datos),
                size=TAMANIO,
                n=1,
            )
            with open(ruta, "wb") as f:
                f.write(base64.b64decode(respuesta.data[0].b64_json))
            generados += 1
            print(f"  OK  {clave}.png")
        except Exception as e:
            fallados += 1
            print(f"  [!] Fallo {clave}: {type(e).__name__}: {e}")

    print(f"\nGenerados: {generados} · ya estaban: {saltados} · "
          f"fallados: {fallados}")
    print(f"Carpeta: {os.path.abspath(destino)}")
    if generados:
        print("\nSi alguno no te convence: borra ese png y volve a correr, o "
              "ajusta su entrada en RAZAS y usa --rehacer.")
    return 0 if not fallados else 1


if __name__ == "__main__":
    sys.exit(main())
