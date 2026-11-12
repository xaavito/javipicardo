"""
La tripulacion como agentes del Agents SDK de OpenAI (pedido de Pato, Sesion #3).

Un solo lugar arma las tools y los agentes, y lo usan las dos entradas:

  - VOZ (fase3_agente_voz.py): una sesion Realtime con la Computadora como
    agente de entrada y un agente por oficial. Llamar a un oficial por su
    nombre es un HANDOFF: el SDK le pasa la conversacion al agente de ese rol,
    que solo tiene sus propias tools (el enrutado de WISHLIST 3.0).
  - TEXTO (llm_fallback.py): cuando el parser de reglas no reconoce una frase,
    un Agent de texto elige la(s) tool(s). Reemplaza al function calling a mano.

Lo que NO cambia: el schema sale de catalogo_comandos (que sale de los
diccionarios del parser), y la tecla la aprieta fase1.ejecutar_accion. El
agente elige; el ejecutor validado ejecuta.

Cada tool recibe un `ejecutor(accion, contexto)` asincronico. En voz ejecuta
la tecla en el momento; en texto solo junta las acciones, para que el que
llama mantenga el "todo o nada" de las cadenas.

COMO INSTALAR (Windows, consola como Administrador):
    pip install openai-agents
"""

import asyncio

import catalogo_comandos as cc
import config
import oficiales

# Modelo del agente de texto (fallback del parser). El mismo que usaba el
# function calling a mano: elegir una tool no necesita un modelo mas grande.
MODELO_TEXTO = "gpt-4o-mini"

_SCHEMA_SIN_ARGUMENTOS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}

REGLAS_COMUNES = (
    "Ejecuta las ordenes SOLO con las herramientas; no inventes ordenes que no "
    "existan. Si el capitan pide varias cosas en una frase, llama una "
    "herramienta por cada una, en el orden en que las pidio. Si la orden es "
    "ambigua o parece cortada (por ejemplo 'maquina' a secas), NO adivines: "
    "preguntale que quiso decir. Ejecutar la orden equivocada es peor que no "
    "ejecutar nada."
)


def _alias(clave):
    return ", ".join(oficiales.OFICIALES[clave]["alias"])


def items_por_oficial():
    """{clave_oficial: [items del catalogo]}. El dueño de cada comando lo
    decide oficiales.oficial_para, el mismo criterio que elige quien contesta."""
    _, mapa = cc.generar_tools_openai()
    grupos = {}
    for item in mapa.values():
        accion = cc.item_a_accion(item, item["nombre_legible"])
        grupos.setdefault(oficiales.oficial_para(accion), []).append(item)
    return grupos


def crear_tool(item, ejecutor):
    """Un FunctionTool sin argumentos por comando del catalogo: el nombre ya
    identifica la accion, el modelo solo elige cual."""
    from agents import FunctionTool

    ejemplos = ", ".join(f'"{e}"' for e in item["ejemplos"])

    async def invocar(ctx, _argumentos_json):
        contexto = ctx.context if isinstance(ctx.context, dict) else {}
        accion = cc.item_a_accion(item, contexto.get("texto")
                                  or item["nombre_legible"])
        return await ejecutor(accion, contexto)

    return FunctionTool(
        name=item["nombre_legible"],
        description=f"{item['descripcion']}. Frases tipicas: {ejemplos}.",
        params_json_schema=_SCHEMA_SIN_ARGUMENTOS,
        on_invoke_tool=invocar,
    )


# ---------------------------------------------------------------------------
# Voz: la tripulacion Realtime
# ---------------------------------------------------------------------------

def _instrucciones_computadora(exigir_nombre):
    filtro = ""
    if exigir_nombre:
        filtro = (
            " El microfono esta siempre abierto: una orden solo cuenta si "
            "empieza llamando a la computadora o a un oficial. Cualquier otra "
            "cosa es charla del puente: ignorala, sin herramientas y sin "
            "contestar."
        )
    return (
        "Sos la computadora de a bordo de una nave estelar en combate. El "
        "capitan da ordenes en español rioplatense, cortas, y la transcripcion "
        "puede tener errores. Ejecutalas al instante con la herramienta que "
        "corresponda y confirma en tres o cuatro palabras. "
        f"Te llaman como: {_alias('computadora')}. "
        "Si el capitan llama a un oficial por su nombre, transferile la "
        "conversacion con la herramienta llamar_<rol> correspondiente. "
        + REGLAS_COMUNES + filtro
    )


def _instrucciones_oficial(clave):
    datos = oficiales.OFICIALES[clave]
    return (
        f"Sos {datos['nombre']}, {datos['rango'] or 'oficial'} a cargo de "
        f"{clave} en el puente de una nave estelar en combate. Te llaman como: "
        f"{_alias(clave)}. Ejecuta al instante las ordenes del capitan que son "
        "de tu puesto y confirma en tres o cuatro palabras, en personaje. Si "
        "la orden es de otro puesto, devolvele la conversacion a la "
        "computadora con llamar_computadora para que la despache. "
        + REGLAS_COMUNES
    )


def armar_tripulacion(ejecutor, exigir_nombre=True):
    """Devuelve el agente de entrada (la Computadora) de una sesion Realtime.

    La Computadora tiene TODAS las tools: una orden sin nombre se ejecuta en
    un solo viaje, sin pagar un handoff. Los oficiales tienen solo las suyas y
    se llega a ellos por handoff cuando el capitan los nombra. El nombre de
    cada agente es la clave del oficial, para que los eventos se puedan
    traducir de vuelta al retrato y la voz.
    """
    from agents.realtime import RealtimeAgent, realtime_handoff

    grupos = items_por_oficial()
    tools = {clave: [crear_tool(i, ejecutor) for i in items]
             for clave, items in grupos.items()}
    todas = [t for lista in tools.values() for t in lista]

    computadora = RealtimeAgent(
        name="computadora",
        instructions=_instrucciones_computadora(exigir_nombre),
        tools=todas,
    )

    tripulantes = []
    for clave, lista in tools.items():
        if clave == "computadora":
            continue
        datos = oficiales.OFICIALES[clave]
        tripulantes.append(RealtimeAgent(
            name=clave,
            handoff_description=(f"{datos['nombre']}, a cargo de {clave}. "
                                 f"Se lo llama como: {_alias(clave)}."),
            instructions=_instrucciones_oficial(clave),
            tools=lista,
        ))

    volver = realtime_handoff(
        computadora, tool_name_override="llamar_computadora",
        tool_description_override="Devolver la conversacion a la computadora")
    for agente in tripulantes:
        agente.handoffs = [volver]
    computadora.handoffs = [
        realtime_handoff(a, tool_name_override=f"llamar_{a.name}")
        for a in tripulantes
    ]
    return computadora


# ---------------------------------------------------------------------------
# Texto: el fallback del parser de reglas
# ---------------------------------------------------------------------------

_agente_texto = None
_clave_configurada = False


async def _juntar(accion, contexto):
    contexto["acciones"].append(accion)
    return "Orden registrada."


def armar_agente_texto(modelo=MODELO_TEXTO):
    """Agent de texto con todas las tools en modo "juntar": no aprieta nada,
    devuelve lo que eligio. stop_on_first_tool corta despues de la primera
    tanda de tool calls, asi no se paga una segunda vuelta para que el modelo
    escriba una confirmacion que nadie lee."""
    from agents import Agent, ModelSettings

    todas = [crear_tool(i, _juntar)
             for items in items_por_oficial().values() for i in items]
    return Agent(
        name="computadora",
        instructions=(
            "Sos el sistema de control por voz de una nave de Star Trek: "
            "Starfleet Command. El capitan da una orden en español (puede "
            "tener errores de transcripcion). " + REGLAS_COMUNES +
            " Si ninguna herramienta aplica, no llames a ninguna."
        ),
        tools=todas,
        model=modelo,
        model_settings=ModelSettings(temperature=0, parallel_tool_calls=True),
        tool_use_behavior="stop_on_first_tool",
    )


def interpretar_texto(texto, max_acciones, modelo=None):
    """Lista de acciones (formato fase1) que el agente eligio para `texto`.
    Vacia si ninguna aplica. Solo junta: ejecutar es cosa del que llama."""
    global _agente_texto, _clave_configurada
    from agents import Runner, set_default_openai_key, set_tracing_disabled

    if modelo is not None:
        agente = armar_agente_texto(modelo)
    else:
        if not _clave_configurada:
            set_default_openai_key(config.api_key())
            # Las trazas van a la plataforma de OpenAI con cada orden: ruido
            # y latencia que no usamos.
            set_tracing_disabled(True)
            _clave_configurada = True
        if _agente_texto is None:
            _agente_texto = armar_agente_texto()
        agente = _agente_texto

    contexto = {"texto": texto, "acciones": []}
    Runner.run_sync(agente, texto, context=contexto, max_turns=2)
    return contexto["acciones"][:max_acciones]


def precalentar():
    """Arma el agente de texto (import del SDK + schema) antes del primer
    fallback. Devuelve False si el SDK no esta instalado."""
    global _agente_texto
    try:
        if _agente_texto is None:
            _agente_texto = armar_agente_texto()
        return True
    except ImportError:
        return False


def resumen():
    """Texto del plantel de agentes y sus tools, para `python agentes.py`."""
    lineas = []
    for clave, items in items_por_oficial().items():
        nombre = oficiales.OFICIALES[clave]["nombre"]
        lineas.append(f"{nombre} ({clave}): "
                      + ", ".join(i["nombre_legible"] for i in items))
    return "\n".join(lineas)


if __name__ == "__main__":
    print(resumen())
