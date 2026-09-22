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
ESTILO = "fotorrealista"

ESTILOS = {
    "ilustrado": (
        "digital comic-book illustration, bold clean linework, cel shading, "
        "rich saturated color"
    ),
    # Los rasgos se piden como PROTESIS Y MAQUILLAJE sobre un actor real, que
    # es lo que de verdad se ve en la serie - sin eso el modelo tiende a
    # dibujar un monstruo. El resto de la descripcion (lente, luz, encuadre)
    # esta para que las siete fotos parezcan de la misma sesion.
    "fotorrealista": (
        "photorealistic cinematic film still from a live-action television "
        "series. The alien features are practical prosthetic makeup and "
        "appliances applied to a real human actor, with visible natural skin "
        "texture and pores. Shot on an 85mm lens at eye level, soft key light "
        "from the left, gentle fill, shallow depth of field, neutral color "
        "grading, no stylisation"
    ),
}

# Como se ve cada uniforme, en la epoca de las imagenes de referencia.
# El panel de color va en el PECHO y los hombros en negro. Sin aclararlo sale
# a veces la variante invertida (hombros de color, pecho negro), que existe de
# verdad pero desentona con el resto del plantel.
UNIFORMES = {
    "rojo": "a uniform whose chest panel is burgundy red, with black "
            "shoulders and black sleeves",
    "dorado": "a uniform whose chest panel is mustard gold, with black "
              "shoulders and black sleeves",
    "azul": "a uniform whose chest panel is teal blue, with black shoulders "
            "and black sleeves",
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
    "trill": "two neat symmetrical lines of dark brown spots, one down each "
             "side of the face only, from the hairline past the temple and "
             "down the neck, leaving the centre of the face clear. Warm "
             "human-like features",
    # 22/09: la primera version salio como un humano calvo pintado de azul.
    # La cresta es EL rasgo boliano, asi que hay que insistir mucho con ella.
    "boliano": "light blue skin, completely bald, and a thick raised vertical "
               "cartilage ridge that bisects the whole face, starting at the "
               "top of the bald scalp and running down the forehead, between "
               "the eyes, along the nose and to the upper lip, clearly raised "
               "and casting its own shadow. Friendly open expression",
    # 22/09: pedida femenina, salio inequivocamente masculina (barba tupida).
    # Se sacan los rasgos que empujaban a eso y se agregan senales femeninas.
    "tellarita": "stocky build, porcine snout-like upturned nose, small "
                 "deep-set eyes, no beard at all, a clean-shaven face with "
                 "softer rounded cheeks, and long hair pulled back into a "
                 "braid. Gruff stubborn expression",
    # 22/09: salio con ojos normales y orejas puntiagudas, o sea leida como
    # vulcana. Los ojos negros son EL rasgo, y hay que negar las orejas.
    "betazoide": "completely black eyes - the entire eyeball solid black with "
                 "no visible white and no visible iris, like pools of ink - "
                 "and plain rounded human ears, definitely not pointed ears. "
                 "Dark wavy hair, warm empathic expression",
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
