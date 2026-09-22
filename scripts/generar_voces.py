"""
Genera UNA VEZ los wav de las respuestas de los oficiales, con la API de TTS
de OpenAI, y los deja en audio/oficiales/.

Se corre una sola vez (y de nuevo solo si se agregan frases nuevas a
oficiales.py). Como el set de frases es fijo y chico, conviene generarlas con
una voz buena y guardarlas, en vez de sintetizar en vivo: sale mas barato,
suena mejor, y reproducir un archivo tarda ~0ms.

COMO USAR:
    pip install openai
    (con OPENAI_API_KEY configurada, ver stt_openai.py)
    python generar_voces.py

Vuelve a generar solo lo que falta. Para rehacer todo:
    python generar_voces.py --rehacer
"""

import os
import sys

from openai import OpenAI

import oficiales

MODELO_TTS = "gpt-4o-mini-tts"

# Una voz por oficial. La idea es que se distingan entre si; ajustar a gusto
# despues de escucharlas. Ver la lista de voces disponibles en la doc de OpenAI.
# Sin haberlas escuchado no hay forma de acertarle: ajustar despues de oirlas
# y volver a correr con --rehacer.
VOZ_POR_OFICIAL = {
    "timon": "shimmer",         # T'Lara, vulcana, femenina: plana y monotona
    "armas": "onyx",            # Korak, klingon, masculino: grave
    "defensa": "coral",         # Zheva, andoriana, femenina
    "ciencias": "echo",         # Delon, trill, masculino
    "ingenieria": "alloy",      # Grax, boliano, masculino: calido
    "seguridad": "sage",        # Pell, tellarita, femenina: aspera
    "comunicaciones": "nova",   # Nima, betazoide, femenina: calida
    "computadora": "ballad",    # la voz del sistema, sin cuerpo
}

# Instruccion de tono por oficial (el modelo de TTS nuevo la acepta).
TONO_POR_OFICIAL = {
    "timon": "Habla de forma neutra y sin emocion, como una vulcana.",
    "armas": "Habla con energia marcial, breve y seguro.",
    "defensa": "Habla con calma profesional y alerta.",
    "ciencias": "Habla con precision, tono academico.",
    "ingenieria": "Habla en tono calido y campechano.",
    "seguridad": "Habla con voz aspera y directa, sin adornos.",
    "comunicaciones": "Habla en tono calido y atento.",
    "computadora": "Habla como la computadora de una nave: neutra y clara.",
}


def main():
    rehacer = "--rehacer" in sys.argv

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[!] Falta la variable de entorno OPENAI_API_KEY. "
              "Ver stt_openai.py para como configurarla.")
        return 1

    cliente = OpenAI(api_key=api_key)
    os.makedirs(oficiales.DIR_AUDIO, exist_ok=True)

    generados = saltados = fallados = 0

    for desenlace, por_oficial in oficiales.RESPUESTAS.items():
        for clave, frases in por_oficial.items():
            for frase in frases:
                nombre = oficiales._nombre_archivo(clave, frase)
                ruta = os.path.join(oficiales.DIR_AUDIO, nombre)

                if os.path.isfile(ruta) and not rehacer:
                    saltados += 1
                    continue

                try:
                    # wav y no mp3: winsound (que es lo que usa oficiales.py
                    # para reproducir) solo lee wav.
                    respuesta = cliente.audio.speech.create(
                        model=MODELO_TTS,
                        voice=VOZ_POR_OFICIAL.get(clave, "nova"),
                        input=frase,
                        instructions=TONO_POR_OFICIAL.get(clave, ""),
                        response_format="wav",
                    )
                    respuesta.write_to_file(ruta)
                    generados += 1
                    print(f"  OK  {nombre}  ({clave}: \"{frase}\")")
                except Exception as e:
                    fallados += 1
                    print(f"  [!] Fallo {nombre}: {type(e).__name__}: {e}")

    print(f"\nGenerados: {generados} · ya estaban: {saltados} · "
          f"fallados: {fallados}")
    print(f"Carpeta: {os.path.abspath(oficiales.DIR_AUDIO)}")
    if generados or saltados:
        print("\nProbalos con: python fase1_text_commands.py  (escribi "
              "'alerta roja' y deberia contestar Sunek)")
    return 0 if not fallados else 1


if __name__ == "__main__":
    sys.exit(main())
