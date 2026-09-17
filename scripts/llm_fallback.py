"""
Fase 4 (opcional) - Fallback con LLM para comandos que el parser de reglas de
la Fase 1 no reconoce. Soporta DOS backends intercambiables:
  - "ollama": LLM local (Llama 3.2, etc.), gratis, sin internet.
  - "openai": LLM en la nube (gpt-4o-mini, etc.), requiere API key y
    conexion a internet, pero suele ser mas rapido/preciso.
Se elige con la constante LLM_BACKEND mas abajo.

IMPORTANTE: esto es un FALLBACK, no un reemplazo del parser de reglas. El
flujo real es:
  1. Se intenta primero con fase1.parsear_comando(texto) (rapido, gratis,
     sin latencia de red/inferencia).
  2. Si el resultado es {"action": "unknown", ...}, RECIEN AHI se llama a
     `interpretar_con_llm(texto)` de este modulo, como ultimo recurso.

El LLM NUNCA "inventa" acciones libremente: se le pasa el catalogo EXACTO de
acciones que el sistema puede ejecutar (generado dinamicamente desde
catalogo_comandos.py, para que nunca quede desincronizado de lo que el
parser de reglas realmente soporta) y se le pide que devuelva SOLO un JSON
con una de esas acciones (o {"accion": null} si ninguna aplica).

------------------------------------------------------------------------
COMO INSTALAR - backend "ollama" (LLM local):
1. Instalar Ollama en la maquina Windows: https://ollama.com/download
2. Descargar un modelo chico:
       ollama pull llama3.2:3b
3. Instalar el cliente de Python:
       pip install ollama

COMO INSTALAR - backend "openai" (LLM en la nube, API key):
1. Instalar el cliente de Python:
       pip install openai
2. Configurar la variable de entorno OPENAI_API_KEY (ver stt_openai.py para
   el detalle de como setearla en Windows - misma API key sirve para STT y
   para el LLM, son el mismo servicio).

Ver README seccion 2.4 para la tabla completa de tamaños de modelo local y
cuanta RAM necesita cada uno.
------------------------------------------------------------------------
"""

import json
import os
import re

import catalogo_comandos as cc

# Backend a usar: "ollama" (local) o "openai" (API, requiere OPENAI_API_KEY).
LLM_BACKEND = "openai"

# Modelo de Ollama a usar (si LLM_BACKEND == "ollama").
MODELO_LLM_OLLAMA = "llama3.2:3b"

# Modelo de OpenAI a usar (si LLM_BACKEND == "openai"). gpt-4o-mini es rapido
# y barato, mas que suficiente para esta tarea de clasificacion simple.
MODELO_LLM_OPENAI = "gpt-4o-mini"

# Import diferido/condicional de cada SDK, para no requerir instalar AMBOS
# si solo se va a usar uno de los dos backends.
if LLM_BACKEND == "ollama":
    import ollama
elif LLM_BACKEND == "openai":
    from openai import OpenAI


# Cached OpenAI client, the same fix already applied in stt_openai.py:
# creating one per call pays DNS + TLS handshake on the first fallback of
# every run. When the STT also runs on the OpenAI backend its client is
# reused, so the connection that precalentar_todo() warms up at startup
# serves the LLM too.
_cliente_cacheado = None


def _cliente():
    global _cliente_cacheado
    if _cliente_cacheado is None:
        try:
            import stt_openai
            _cliente_cacheado = stt_openai.obtener_cliente()
        except Exception:
            # STT on the local backend, or soundfile not installed: this
            # module opens its own client.
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "No se encontro la variable de entorno OPENAI_API_KEY. "
                    "Ver docstring de este archivo / stt_openai.py para como "
                    "configurarla."
                )
            _cliente_cacheado = OpenAI(api_key=api_key)
    return _cliente_cacheado


def _armar_system_prompt():
    catalogo_texto = cc.catalogo_como_texto()
    return f"""Sos el sistema de control por voz de una nave de Star Trek: \
Starfleet Command. Tu trabajo es interpretar la orden del capitan (en \
español, puede tener errores de transcripcion de voz) y devolver SOLO un \
JSON (sin texto adicional, sin markdown, sin explicaciones) con el formato:

{{"accion": "<nombre_de_accion>", "parametros": {{...}}}}

Estas son las UNICAS acciones validas que existen en el sistema. Elegi la \
que mejor coincida con la intencion del capitan, usando EXACTAMENTE el \
mismo valor de "accion" y "parametros" que se muestra en cada ejemplo (no \
inventes acciones ni parametros nuevos):

{catalogo_texto}

Si la orden del capitan no coincide razonablemente con NINGUNA de estas \
acciones, devolve exactamente: {{"accion": null}}

Respondé SOLO con el JSON, nada mas."""


def _extraer_json(texto_respuesta):
    """El LLM a veces envuelve la respuesta en markdown (```json ... ```) o
    agrega texto extra pese a la instruccion. Esta funcion intenta extraer
    el primer bloque JSON valido de la respuesta."""
    texto = texto_respuesta.strip()

    # Sacar posibles bloques markdown de codigo
    texto = re.sub(r'^```(json)?\s*', '', texto)
    texto = re.sub(r'\s*```$', '', texto)

    # Si aun asi no es JSON puro, buscar el primer {...} de la respuesta
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        texto = match.group(0)

    return json.loads(texto)


def _llamar_ollama(system_prompt, texto_usuario):
    respuesta = ollama.chat(
        model=MODELO_LLM_OLLAMA,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto_usuario},
        ],
        options={"temperature": 0},  # determinístico, sin creatividad
    )
    return respuesta["message"]["content"]


def _item_catalogo_a_accion(item, texto_usuario):
    """Traduce un item del catalogo (formato accion/parametros, generico y
    legible) al formato interno que ya usa fase1.ejecutar_accion()
    (action/keys/level/etc, segun el tipo). Compartido por ambos backends."""
    accion_nombre = item["accion"]
    parametros = item["parametros"]

    if accion_nombre == "set_speed":
        return {"action": "set_speed", "level": parametros.get("level", 0),
                "raw": texto_usuario}
    elif accion_nombre == "key":
        return {"action": "key", "key": parametros.get("key"),
                "raw": texto_usuario}
    elif accion_nombre == "key_combo":
        return {"action": "key_combo", "keys": parametros.get("keys", []),
                "raw": texto_usuario}
    elif accion_nombre == "combo":
        nombre_combo = parametros.get("combo")
        if nombre_combo in cc.fase1.COMBOS:
            return {"action": "combo", "combo": nombre_combo,
                    "pasos": cc.fase1.COMBOS[nombre_combo]["pasos"],
                    "raw": texto_usuario}

    return {"action": "unknown", "raw": texto_usuario}


def _interpretar_con_openai_function_calling(texto_usuario):
    """Usa 'function calling' (tools) de la API de OpenAI: en vez de pedirle
    al modelo que GENERE un JSON libre describiendo la accion, se le pasa un
    esquema de funciones (una por cada comando real del juego, generado
    dinamicamente por catalogo_comandos.generar_tools_openai()) y se le pide
    que ELIJA cual invocar. Esto es mas rapido (el modelo esta entrenado
    especificamente para esta tarea) y mas confiable (la API valida que el
    nombre de funcion elegido exista en el esquema, no puede "inventar" un
    comando que no este en la lista)."""
    tools, mapa_nombre_a_item = cc.generar_tools_openai()

    cliente = _cliente()
    respuesta = cliente.chat.completions.create(
        model=MODELO_LLM_OPENAI,
        messages=[
            {"role": "system", "content": (
                "Sos el sistema de control por voz de una nave de Star "
                "Trek: Starfleet Command. El capitan va a dar una orden en "
                "español (puede tener errores de transcripcion de voz). "
                "Elegi la funcion (herramienta) que mejor represente esa "
                "orden. Si ninguna aplica razonablemente, no llames a "
                "ninguna funcion."
            )},
            {"role": "user", "content": texto_usuario},
        ],
        tools=tools,
        tool_choice="auto",
        temperature=0,
    )

    mensaje = respuesta.choices[0].message
    tool_calls = mensaje.tool_calls

    if not tool_calls:
        # El modelo decidio que ninguna funcion aplica.
        return {"action": "unknown", "raw": texto_usuario}

    nombre_elegido = tool_calls[0].function.name
    item = mapa_nombre_a_item.get(nombre_elegido)
    if item is None:
        # No deberia pasar nunca (la API solo puede elegir nombres del
        # esquema que le pasamos), pero por las dudas.
        return {"action": "unknown", "raw": texto_usuario}

    return _item_catalogo_a_accion(item, texto_usuario)


def _interpretar_con_ollama_json_libre(texto_usuario):
    """Backend Ollama: pide JSON libre en el texto de la respuesta (no todos
    los modelos chicos de Ollama soportan function calling de forma
    confiable), y lo parsea con _extraer_json()."""
    system_prompt = _armar_system_prompt()
    try:
        contenido = _llamar_ollama(system_prompt, texto_usuario)
        data = _extraer_json(contenido)
    except Exception as e:
        print(f"  [!] Error consultando a Ollama: {e}")
        return {"action": "unknown", "raw": texto_usuario}

    accion_nombre = data.get("accion")
    if not accion_nombre:
        return {"action": "unknown", "raw": texto_usuario}

    return _item_catalogo_a_accion(
        {"accion": accion_nombre, "parametros": data.get("parametros", {}) or {}},
        texto_usuario,
    )


def interpretar_con_llm(texto_usuario, timeout_seg=10):
    """Manda el texto del usuario al LLM (backend segun LLM_BACKEND) y
    devuelve una accion estructurada en el MISMO formato que
    fase1.parsear_comando() (compatible con fase1.ejecutar_accion()), o
    {"action": "unknown", "raw": texto_usuario} si el LLM no pudo interpretar
    nada util o hubo algun error.

    - Backend "openai": usa function calling (mas rapido y confiable, ver
      _interpretar_con_openai_function_calling).
    - Backend "ollama": usa JSON libre en el texto de la respuesta (ver
      _interpretar_con_ollama_json_libre), porque no todos los modelos
      chicos que corren bien en CPU soportan function calling de forma
      confiable.
    """
    try:
        if LLM_BACKEND == "openai":
            return _interpretar_con_openai_function_calling(texto_usuario)
        elif LLM_BACKEND == "ollama":
            return _interpretar_con_ollama_json_libre(texto_usuario)
        else:
            raise ValueError(f"LLM_BACKEND desconocido: {LLM_BACKEND!r}")
    except Exception as e:
        modelo = (MODELO_LLM_OPENAI if LLM_BACKEND == "openai"
                  else MODELO_LLM_OLLAMA)
        detalle = getattr(e, "body", None) or getattr(e, "message", None)
        print(f"  [!] Error consultando al LLM ({LLM_BACKEND}, modelo "
              f"{modelo}): {type(e).__name__}: {e}")
        if detalle:
            print(f"      detalle: {detalle}")
        return {"action": "unknown", "raw": texto_usuario}


if __name__ == "__main__":
    # Prueba manual rapida: python llm_fallback.py "aumenta bastante la velocidad"
    import sys
    texto = " ".join(sys.argv[1:]) or "aumentá bastante la velocidad, como a la mitad"
    print(f"Texto de prueba: {texto!r}\n")
    print("System prompt generado:\n")
    print(_armar_system_prompt())
    print("\n--- Consultando al LLM ---")
    resultado = interpretar_con_llm(texto)
    print("Resultado:", resultado)
