# Registro de sesiones de feedback (Pato)

Resumen ejecutivo de las charlas de feedback con **Pato**, que lidera/controla el
proyecto. Se estima una cadencia **semanal, los viernes**.

**Cómo funciona el ciclo:** lo que sale de la charla del viernes son puntos a
avanzar **antes del viernes siguiente**. Si alguno no se avanza, la idea es
llegar a la próxima charla con **el motivo explicado**, no con el punto en
blanco. Por eso cada tabla tiene una columna de compromiso/estado.

Formato de cada entrada: qué se sugirió, cómo estábamos al momento de la charla,
y qué se hizo (o por qué se decidió no hacerlo). La idea es que la tabla se pueda
copiar y mandar por Slack tal cual, sin tener que releer el `ROADMAP.md` entero.

- Detalle técnico largo de cada decisión: ver `../ROADMAP.md` (Fase 7).
- Estado general del proyecto: ver `../README.md`.

Convención de estado:
- ✅ **Hecho** — implementado después de la charla.
- ✅ **Ya estaba** — el proyecto ya lo tenía resuelto antes de la sugerencia.
- ❌ **No adoptado** — decisión consciente de no hacerlo, *con motivo a explicar
  en la próxima charla*.
- ⏳ **Pendiente** — comprometido para antes del próximo viernes.

---

## Sesión #1 — jueves 11/09/2026 — Arquitectura de IA (STT + LLM)

**Tema:** enfoque de Speech-to-Text y uso de LLM / function calling.
**Estado general: avanzado.** Todo lo accionable de esta charla ya se implementó
al día siguiente; queda 1 punto pendiente de validar en vivo y 2 decisiones
conscientes de no adoptar (con motivo, ver abajo).

| # | Lo que sugirió Pato | Cómo estábamos | Qué se hizo | Estado |
|---|---|---|---|---|
| 1 | Usar la guía oficial de Speech-to-Text de OpenAI | Ya usábamos la API de STT de OpenAI, pero no habíamos revisado la guía a fondo | Se leyó la guía y salieron 2 mejoras concretas (filas 1a y 1b), ambas aplicadas | ✅ Hecho |
| 1a | (de la guía) Modelo de transcripción | Usábamos `whisper-1`, que era el modelo vigente cuando se escribió el script | **Migrado a `gpt-4o-mini-transcribe`**: más preciso, más barato y más rápido | ✅ Hecho |
| 1b | (de la guía) Parámetro `prompt` para sesgar vocabulario | No lo conocíamos | **Agregado.** Le pasamos la jerga del juego ("media máquina", "ECCM", "alpha strike"...) para que no transcriba cualquier cosa. Ataca justo el riesgo #1 que teníamos anotado en el roadmap. También sumamos `temperature=0` para que no improvise | ✅ Hecho |
| 2 | Mandar audio directo al LLM (sin STT separado) | — | **No adoptado.** Tenemos un parser de reglas local y gratis que resuelve la mayoría de comandos en microsegundos, y para consultarlo necesitamos el texto primero. Mandando audio directo pagaríamos API en *todos* los comandos, incluso en "alerta roja" | ❌ No adoptado *(a explicar)* |
| 3 | Pasarle la lista de comandos como `tools` y que devuelva `tool_calls` | Ya implementado antes de la charla | `llm_fallback.py` ya usa `tools=[...]` + `tool_choice="auto"` nativo. Las 16 tools se generan solas desde el catálogo | ✅ Ya estaba |
| 4 | "Diccionario de desambiguación" | Ya implementado antes de la charla | `catalogo_comandos.py` lo genera **dinámicamente desde los mismos diccionarios del parser**, así que nunca queda desincronizado con lo que el sistema sabe ejecutar | ✅ Ya estaba |
| 5 | Usar `@openai/agents` (Agents SDK) en vez de parsear el JSON a mano | — | **🔄 REVISADO el 25/09: se adopta, ver Sesión #3.** El argumento de abajo era válido para el sistema de septiembre y dejó de valer cuando aparecieron el encadenado de comandos y el enrutado por oficial. Texto original: **No adoptado por ahora.** `@openai/agents` es de JS/TS y el proyecto es 100% Python (obligado por `pydirectinput` para controlar Windows); el equivalente sería `openai-agents`. El caso de uso actual es clasificación de **un solo paso** ("frase → tool"), sin árbol de decisiones. **Sí lo reevaluaríamos** si hiciéramos comandos encadenados tipo "atacá con todo, y si no hay objetivo, seleccioná el más cercano primero" | ❌ No adoptado *(a explicar)* |

### Compromisos para la próxima charla (viernes)

- ⏳ **Probar en vivo en la Windows** el STT nuevo: medir si baja la latencia real
  y si el `prompt` de vocabulario reduce los errores de transcripción de la jerga
  del juego. Ajustar `PROMPT_VOCABULARIO` con los términos que sigan fallando.
- 🗣️ **Explicarle a Pato los dos puntos que no adoptamos** (filas 2 y 5) con el
  razonamiento de arriba, para validar si comparte el criterio o prefiere que
  vayamos igual por ese camino.

---

## Sesión #2 — viernes 18/09/2026

**Tema:** review of everything built since Session #1, and a **new agenda** of
requests.
**Estado general: everything built was reviewed and approved.** No corrections
came out of it and both Session #1 commitments are closed, so the meeting moved
on to the new agenda in section 6 — which points the project at a **UI layer**
for the first time.

Sections 1 to 5 were written on 17/09, before the meeting, as the progress
report. Section 6 is what came out of it.

### 1. Session #1 commitments — done

| Commitment | Result |
|---|---|
| ⏳ → ✅ Test the new STT live (`gpt-4o-mini-transcribe` + vocabulary biasing) | **Done.** Accuracy: 4 of the 5 phrases came out perfect. Latency: **1.5-3.1s**, ~2s on average |
| ⏳ → ✅ Tune `PROMPT_VOCABULARIO` with whatever keeps failing | The only failure was not the STT's: it transcribed "escudos **a** máximo" correctly and it was the parser that lacked that synonym |
| 🗣️ Explain the two points we did not adopt | See section 3: one of the two **changed state** with the measurement |

### 2. The vocabulary biasing works, and has a dangerous failure mode

Worth telling because it comes out of his suggestion 1b from the last meeting,
and **the technique stays** — it does improve the game jargon.

Given audio with **no speech** in it (a push-to-talk released before speaking),
the API returns the vocabulary `prompt` **as if it were the transcription**.
Our prompt ends with "ataquen con todo", so the parser matched it and **fired
an Alpha Strike with nobody giving an order**.

The underlying cause is ours: the parser matches a command anywhere in the
text, so any long spurious transcription can press a real key. Three
independent guards: drop the answer when it is the prompt, never send audio
shorter than 0.3s to the API, and never let anything longer than 150
characters reach the parser.

A second version of the same problem turned up, this time from the LLM: the
STT clipped "media máquina" down to **"Máquina."** and the fallback **guessed**
"cuarto de máquina", so half a word accelerated the ship. A single ambiguous
word now answers with the alternatives and executes nothing, and the LLM system
prompt says explicitly that a truncated phrase must call no function.

> Takeaway for the meeting: when you are flying a ship, **an unclear input must
> never produce a confident action**. Both bugs of the week are the same problem
> wearing two faces.

### 3. The two rejected points, revisited with data

| Point | Session #1 | With this week's measurements |
|---|---|---|
| **Audio straight to the LLM (no separate STT)** | ❌ Not adopted: it would break the free parser path | **The measurement runs in his favour.** The STT is now **80%** of a command (1.5-3.1s out of ~2.5-3.5s), not the minor cost we assumed. Even so, before going that way we are testing `faster-whisper` locally (`tiny`): if it lands at the expected 0.2-0.4s it wins on latency **and** on cost **and** keeps the local parser. If the local model is not accurate enough, his proposal becomes the best option left |
| **Agents SDK (`openai-agents`)** | ❌ Not adopted: single-step classification | **Unchanged.** The concrete case that would justify it is still ad-hoc command chaining ("atacá con todo, y si no hay objetivo seleccioná el más cercano"), which is in the wishlist and has not been started |

### 4. The week's progress, in numbers

| What | Before | Now |
|---|---|---|
| Execution of one command (1 key) | 1.75s estimated / 1.45s real | **0.43s** |
| "media máquina" (4 keys) | 1.88s | **0.65s** |
| Whole command, end to end | 3.5-5.8s | **2.3-3.5s** |

Two findings behind that: the focus and inter-key pauses **had never been
measured** (the 1.0s picked by eye was 5 times the real minimum), and
`pydirectinput` was adding **0.1s per elementary call — 0.3s per key —** on its
own, which was in no previous analysis.

Also: the **LLM fallback ran live for the first time** (it picked correctly, and
declined correctly when no command applied), and the **catalog the LLM sees
turned out to be out of sync** with the parser — 16 of the 32 commands were
missing from it, so the LLM could not choose them. Fixed, with a coverage check
so it cannot happen again.

### 5. Open, worth mentioning

- **Intermittent 404** from the chat API: two calls died in 0.19s while others
  in the same session worked in 0.9-1.4s, so it is not the model name.
  Diagnostics were added to chase it.
- **Single next step**: local STT. It is the last big latency lever.

### 6. La agenda nueva que puso Pato

Textual, en el orden en que la dio:

| # | Lo que pidió Pato | Cómo estamos | Estado |
|---|---|---|---|
| 1 | **Probar push to talk** | **Resuelto el mismo día, con propuesta propia:** no dejar push-to-talk. Se llama al oficial por su nombre ("computadora", "alférez", "timonel") y eso hace tres cosas a la vez — activa la escucha, muestra a ese personaje, y **enruta la orden a su rol**. Diseño completo en `WISHLIST.md` §3.0 | ✅ Definido |
| 2 | **Generar imágenes de pilotos, oficiales** | Analizado hace rato en `WISHLIST.md` §3.3: retratos por IA **pre-generados una vez** y guardados en disco (generarlos en vivo es inviable por tiempo y costo), plantel fijo de 4-6 oficiales, opcionalmente 2-3 expresiones cada uno | ⏳ Comprometido |
| 3 | **Contestar con voz de computadora** | Analizado en `WISHLIST.md` §3.2: TTS con una voz por oficial, cacheando las frases fijas. Clave de latencia: **ejecutar la tecla primero** y que la voz suene mientras el juego ya reaccionó | ⏳ Comprometido |
| 4 | **¿Videítos del juego?** | Nuevo, y lo dijo con signo de pregunta. Sin analizar: no está claro si es grabar clips del juego o mostrar video en la interfaz | ⏳ **A aclarar con él** |
| 5 | **Cliente browser + server Python en background** | Nuevo como arquitectura. Analizado en `WISHLIST.md` §5. **Pasó además un ejemplo andando** (`patopitaluga/ejemplo-agente-realtime`, cuyo `package.json` se llama "voicecommander"): Node + Express que firma una sesión de la **Realtime API** y un browser que abre WebSocket directo contra OpenAI. Analizado en §5.6-§5.8 | ⏳ Comprometido |

### 6b. Estado de la agenda al jueves 24/09, para la charla del viernes

| # | Pedido | Estado | Qué se puede mostrar |
|---|---|---|---|
| 2 | Imágenes de pilotos y oficiales | ✅ **Hecho** | **7 retratos fotorrealistas**, uno por puesto, siete razas distintas y balanceado en sexo. Se generan desde la tabla del plantel, no a mano. Faltan regenerar 2 con el prompt corregido |
| 3 | Contestar con voz de computadora | ✅ **Hecho** | 25 frases generadas, **el oficial que corresponde al comando contesta** y habla. Confirmado en texto el 24/09; el audio tuvo un bug de cabecera ya corregido |
| 1 | Probar push to talk | ✅ **Hecho, y de cuatro formas** | `MODO_ESCUCHA` tiene 4 valores: la tecla de siempre, un **botón en el panel** (para no soltar el mouse), **escucha activa** (micrófono abierto, se llama al oficial por su nombre) y **micrófono en el browser** con cancelación de eco. Y `EXIGIR_NOMBRE_DE_OFICIAL` permite además dar órdenes sin nombrar a nadie |
| 5 | Cliente browser + server Python | ✅ **Andando en su versión mínima** | `panel_web.py`: server de librería estándar (cero dependencias) + página que muestra **el retrato del oficial que contesta, su frase, y reproduce su voz**. Es donde se junta todo: sus puntos 2, 3 y 5 en una sola pantalla |
| 4 | ¿Videítos del juego? | ⏳ **A aclarar** | Admite dos lecturas muy distintas: grabar clips, o mostrar video en la interfaz |

**Sobre su ejemplo de hark:** sólo **detecta** cuándo hablás (`speaking` /
`stopped_speaking`), no graba ni manda nada. Igual sirvió: llevó a mover el
micrófono al browser, y ahí apareció el beneficio que no era obvio —
`echoCancellation` hace que el browser **cancele su propia salida de la
entrada**, y como la voz de los oficiales sale por esa misma página, el eco se
resuelve de raíz y **se le puede hablar encima a un oficial**.

**Dos cosas para plantearle:**

1. **Su ejemplo de Realtime nos da vuelta el argumento del audio directo**, y
   conviene decirlo nosotros. Con `server_vad` resuelve además el fin de turno,
   que era el costo que le veíamos a sacar el push-to-talk.
2. **Lo que se pierde es el parser local**, que era el camino gratis y de
   microsegundos. La propuesta es Realtime + nuestro ejecutor detrás de
   `/tool_calls`, y un wake word local que decida cuándo se manda audio si el
   costo por minuto molesta.

**Lo que no se avanzó, con el motivo:** la prueba #13 (STT local), que era la
última palanca grande de latencia. Primero se la comió esta agenda, y ahora
además **quedó en espera de un micrófono decente**: el Bluetooth graba a
calidad teléfono y con ese audio la comparación no mide el modelo, mide el
micrófono.

**Lo que ordena esta agenda:** los puntos 2, 3 y 4 son cosas que hay que
**mostrar o reproducir en algún lado**, y hoy no existe ese lugar — la consola
es todo lo que tenemos. El punto 5 es ese lugar. Así que **el 5 habilita al 2,
3 y 4**, y el 1 puede ser un requisito del 5: un tab de browser no puede
capturar una tecla global mientras el foco lo tiene el juego, así que la
captura de voz define qué arquitectura es posible. Ver `WISHLIST.md` §5.

**Restricción dura que no cambia:** la inyección de teclas tiene que seguir
viviendo en el proceso Python corriendo **como Administrador** — un browser no
puede mandar teclas al juego. Cualquier cliente web es interfaz, no control.

### 7. El ejemplo de Pato da vuelta una discusión vieja, y hay que decirlo

Su ejemplo usa la **Realtime API**: el browser manda audio por WebSocket
directo a OpenAI y recibe **tool calls** y **audio de vuelta**. Eso es,
literalmente, el **"audio directo al LLM" que propuso en la Sesión #1 y que
rechazamos dos veces** — ahora con código funcionando. En la Sesión #2 ya
habíamos reconocido que la medición corría a su favor (el STT resultó ser el
80% del tiempo de un comando); con esto el argumento se termina de dar vuelta.

Resuelve además tres cosas que teníamos abiertas: `turn_detection: server_vad`
detecta el fin de turno (el costo que §3.0.3 le atribuía a sacar el
push-to-talk), el audio de salida cubre su punto 3 sin trabajo extra, y su
`POST /tool_calls` es exactamente donde entra nuestro `ejecutar_accion()`.

**Lo que se pierde y hay que decidir:** el parser de reglas deja de
interpretar. Era el camino local, gratis y de microsegundos. Tres opciones en
`WISHLIST.md` §5.8; la recomendación es **Realtime + nuestro ejecutor detrás de
`/tool_calls`**, y agregarle un **wake word local** que decida cuándo se manda
audio si el costo por minuto molesta.

**Sobre Node:** no conviene mover el input. El juego es de 2000 y sólo responde
a `SendInput` con **scancodes** (`pydirectinput`); `pyautogui`, que usa
virtual-keys, no hizo nada — y las librerías de Node (`robotjs`, `nut.js`)
arrancan justo con el enfoque que ya sabemos que falla. Sus dos endpoints, en
cambio, son ~20 líneas portables a FastAPI, y el `index.html` se reusa tal cual
porque el browser habla con OpenAI, no con el server.

### Compromisos para la próxima charla (viernes)

- ⏳ **Arrancar por el punto 5** (server Python + cliente browser), que es lo
  que habilita el resto, y llevar algo andando aunque sea mínimo: una página
  que muestre lo que hoy se ve en consola.
- ⏳ **Punto 3 en su versión barata primero**: respuestas de texto por oficial,
  que ya se pueden hacer sin ningún modelo, antes de meter TTS.
- ⏳ **Punto 2**: generar el plantel de oficiales una vez y dejarlo en disco.
- 🗣️ **Preguntarle qué quiso decir con "probar push to talk"** y con "videítos
  del juego" — las dos admiten varias lecturas y cambian bastante el trabajo.
- 🗣️ Contar que el STT local (prueba #13) quedó sin correr: se lo comió la
  agenda nueva. Es la última palanca grande de latencia.

---

## Sesión #3 — viernes 25/09/2026 — Agents SDK

**Tema:** repaso de los puntos de la agenda anterior, y un pedido nuevo.
**Estado general: todos los puntos que había que ver quedaron OK.** No salieron
correcciones. De la charla sale **un pedido nuevo y concreto**: usar el
**Agents SDK de OpenAI**. Pato mostró el proyecto andando con nuestro
diccionario de comandos y convenció.

| # | Lo que pidió Pato | Cómo estábamos | Estado |
|---|---|---|---|
| 1 | **Usar el Agents SDK de OpenAI** | ❌ **Lo habíamos rechazado dos veces** (Sesión #1, fila 5), con el argumento de que nuestro caso era clasificación de un solo paso y el SDK era complejidad innecesaria | 🔄 **Se reconsidera: el argumento ya no se sostiene.** Ver abajo |
| 2 | Basarnos en su proyecto de referencia | Lo habíamos analizado el 18/09, pero **cambió mucho desde entonces** | ⏳ Reanalizado el 25/09, ver abajo |

### Por qué el argumento con el que lo rechazamos ya no vale

Lo rechazamos porque "es clasificación de un solo paso, sin árbol de
decisiones". Eso era cierto **para el sistema de entonces**. Desde ahí
cambiaron tres cosas, todas nuestras:

1. **Encadenado de comandos** (25/09): una frase puede pedir varias acciones en
   orden. Ya no es un paso, es una secuencia.
2. **Enrutado por oficial** (`WISHLIST.md` §3.0): "artillero, fuego" elige a
   quién le toca. **Eso es exactamente un handoff de agentes** — un agente de
   triage que despacha al agente del rol, cada uno con sólo sus propias tools.
   Es literalmente lo que §3.0 decía que había que hacer para acotar el
   vocabulario, y el SDK lo trae resuelto.
3. **Manejo de ambigüedad**: cuando una palabra suelta no alcanza, el sistema
   **pregunta** ("¿qué velocidad, capitán?"). Eso es un turno de conversación,
   no una clasificación.

> **Es la tercera vez que pasa lo mismo**, y conviene decirlo: rechazamos el
> audio directo al LLM, después la Realtime API, y ahora el Agents SDK. En los
> tres casos el rechazo era correcto **para el sistema de ese momento**, y en
> los tres el sistema cambió y le dio la razón a Pato. La lección no es que nos
> equivocamos al analizar, es que **conviene revisar los "no adoptado" cada vez
> que cambia el alcance**, en vez de tratarlos como cerrados.

### El proyecto de referencia, reanalizado (cambió desde el 18/09)

`patopitaluga/ejemplo-agente-realtime` — ahora tiene README y el cliente
modularizado. Lo importante que cambió:

- **Pasó a `gpt-live-1` por WebRTC**, no WebSocket con PCM a mano. WebRTC
  maneja jitter y latencia solo, así que **no necesitaríamos nuestro transporte
  de audio propio** (el POST de PCM que escribí el 25/09 quedaría de más).
- **El modelo de voz delega las tools a `gpt-4.1-mini`** ("delegación
  Responses"). O sea que la voz conversa y un modelo de texto más barato elige
  la herramienta. **Ya es un patrón de agentes**, con o sin SDK.
- El circuito de una tool: el browser recibe el `function_call` por el data
  channel, pega a `POST /tool_calls`, y **devuelve el resultado con el mismo
  `call_id` más un `response.create`** para que el turno siga. El README
  documenta que si falta cualquiera de las dos cosas, el turno queda colgado.
- **El browser no conoce el schema de las tools, sólo el backend.** Eso encaja
  exacto con nosotros: el schema es nuestro `catalogo_comandos.py`.

**Dónde entra nuestro código, sin ambigüedad:** `POST /tool_calls` es donde va
`ejecutar_accion()`. Es la única pieza que tiene que quedarse en Python
corriendo como Administrador, y es justamente la que su arquitectura deja
afuera del browser.

### Lo que hay que resolver antes de escribir código

- **`gpt-live-1` es posterior a lo que conozco de primera mano.** No voy a
  afirmar qué soporta: hay que leer la doc de OpenAI y confirmar si el SDK de
  Python expone lo mismo que el de JS, porque su ejemplo es Node/TS y la
  inyección de teclas tiene que ser Python.
- **Python vs Node.** Dos opciones: portar sus dos endpoints a Python con
  `openai-agents`, o dejar su server Node y que le pegue a un servicio Python
  que aprieta teclas. La primera evita tener tres procesos y dos lenguajes.
- **Qué pasa con el parser de reglas.** Es la misma pregunta de siempre: era el
  camino local, gratis y de microsegundos. Con agentes, interpreta el modelo.
  La propuesta sigue siendo: que las teclas las siga apretando el ejecutor
  validado, con sus guardas.
- **El costo por minuto de audio**, que sigue sin mirarse y sigue siendo el
  número que decide si el micrófono puede estar siempre abierto.

### Compromisos para la próxima charla (viernes)

- ⏳ **Leer la doc del Agents SDK y de `gpt-live-1`**, y confirmar qué expone
  el SDK de **Python** (su ejemplo es de JS).
- ⏳ **Mirar el precio por minuto de audio.** Es el único dato que falta para
  decidir escucha permanente vs. wake word local.
- ⏳ **Prueba de concepto mínima:** una sola tool nuestra (`alerta roja`) dando
  toda la vuelta — voz → agente → `/tool_calls` en Python → tecla al juego →
  resultado de vuelta al modelo.
- 🗣️ Contarle que **el encadenado de comandos ya está hecho** (25/09), que es
  medio camino andado hacia lo que el SDK resuelve.

---

## Sesión #4 — viernes __/__/____ — (pendiente)

<!--
Plantilla, copiar y completar después de la charla:

**Tema:**
**Estado general:**

| # | Lo que sugirió Pato | Cómo estábamos | Qué se hizo | Estado |
|---|---|---|---|---|
| 1 |  |  |  |  |

### Compromisos para la próxima charla (viernes)
- ⏳
- 🗣️
-->
