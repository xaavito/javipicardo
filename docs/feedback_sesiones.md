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
| 5 | Usar `@openai/agents` (Agents SDK) en vez de parsear el JSON a mano | — | **No adoptado por ahora.** `@openai/agents` es de JS/TS y el proyecto es 100% Python (obligado por `pydirectinput` para controlar Windows); el equivalente sería `openai-agents`. El caso de uso actual es clasificación de **un solo paso** ("frase → tool"), sin árbol de decisiones. **Sí lo reevaluaríamos** si hiciéramos comandos encadenados tipo "atacá con todo, y si no hay objetivo, seleccioná el más cercano primero" | ❌ No adoptado *(a explicar)* |

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
| 1 | **Probar push to talk** | Ya usamos push-to-talk (F12, hook global vía `keyboard`, anda con el juego en foco). Falta aclarar a qué apunta: ¿probar alternativas (wake word / VAD), otra tecla, o cómo sobrevive el PTT al cliente browser del punto 5? | ⏳ **A aclarar con él** |
| 2 | **Generar imágenes de pilotos, oficiales** | Analizado hace rato en `WISHLIST.md` §3.3: retratos por IA **pre-generados una vez** y guardados en disco (generarlos en vivo es inviable por tiempo y costo), plantel fijo de 4-6 oficiales, opcionalmente 2-3 expresiones cada uno | ⏳ Comprometido |
| 3 | **Contestar con voz de computadora** | Analizado en `WISHLIST.md` §3.2: TTS con una voz por oficial, cacheando las frases fijas. Clave de latencia: **ejecutar la tecla primero** y que la voz suene mientras el juego ya reaccionó | ⏳ Comprometido |
| 4 | **¿Videítos del juego?** | Nuevo, y lo dijo con signo de pregunta. Sin analizar: no está claro si es grabar clips del juego o mostrar video en la interfaz | ⏳ **A aclarar con él** |
| 5 | **Cliente browser + server Python en background** | Nuevo como arquitectura. Analizado en caliente en `WISHLIST.md` §5 | ⏳ Comprometido |

**Lo que ordena esta agenda:** los puntos 2, 3 y 4 son cosas que hay que
**mostrar o reproducir en algún lado**, y hoy no existe ese lugar — la consola
es todo lo que tenemos. El punto 5 es ese lugar. Así que **el 5 habilita al 2,
3 y 4**, y el 1 puede ser un requisito del 5: un tab de browser no puede
capturar una tecla global mientras el foco lo tiene el juego, así que la
captura de voz define qué arquitectura es posible. Ver `WISHLIST.md` §5.

**Restricción dura que no cambia:** la inyección de teclas tiene que seguir
viviendo en el proceso Python corriendo **como Administrador** — un browser no
puede mandar teclas al juego. Cualquier cliente web es interfaz, no control.

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

## Sesión #3 — viernes __/__/____ — (pendiente)

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
