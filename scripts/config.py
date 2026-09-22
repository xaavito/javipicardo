"""
De donde sale la OPENAI_API_KEY. Un solo lugar para todos los scripts.

Orden de busqueda:
1. La variable de entorno OPENAI_API_KEY (lo de siempre, y lo que ya esta
   configurado en la maquina Windows).
2. Un archivo `.env` en la raiz del proyecto, con la linea:
       OPENAI_API_KEY=sk-...

El `.env` ya esta en el .gitignore desde el primer commit, asi que no se sube.
Sirve para correr los scripts en una maquina donde no queres dejar la variable
seteada de forma permanente.

NUNCA pasar la key por parametro de linea de comandos: queda en el historial de
la consola, en el buffer de la ventana y en la lista de procesos.
"""

import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_ENV = os.path.join(RAIZ, ".env")

_MENSAJE_FALTA = (
    "No se encontro la OPENAI_API_KEY. Dos formas de configurarla:\n"
    "  1) Variable de entorno:  set OPENAI_API_KEY=sk-...   (ver stt_openai.py)\n"
    f"  2) Archivo {ARCHIVO_ENV} con la linea:  OPENAI_API_KEY=sk-...\n"
    "     (ese archivo esta en el .gitignore, no se sube al repo)"
)


def _leer_env(nombre):
    """Busca una variable en el archivo .env. Devuelve None si no esta."""
    if not os.path.isfile(ARCHIVO_ENV):
        return None
    try:
        with open(ARCHIVO_ENV, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                if clave.strip() == nombre:
                    return valor.strip().strip("'\"") or None
    except Exception as e:
        print(f"  [!] No se pudo leer {ARCHIVO_ENV}: {e}")
    return None


def api_key(obligatoria=True):
    """Devuelve la OPENAI_API_KEY. Si obligatoria y no esta, tira RuntimeError
    con las instrucciones."""
    clave = os.environ.get("OPENAI_API_KEY") or _leer_env("OPENAI_API_KEY")
    if not clave and obligatoria:
        raise RuntimeError(_MENSAJE_FALTA)
    return clave


def de_donde_salio():
    """Para diagnosticar sin imprimir nunca la key."""
    if os.environ.get("OPENAI_API_KEY"):
        return "variable de entorno"
    if _leer_env("OPENAI_API_KEY"):
        return f"archivo {ARCHIVO_ENV}"
    return "no se encontro"


if __name__ == "__main__":
    print(f"OPENAI_API_KEY: {de_donde_salio()}")
