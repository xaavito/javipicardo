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

## Sesión #2 — viernes __/__/____ — (pendiente)

**A repasar al inicio de esta charla** (viene de la Sesión #1):
- Resultado de la prueba en vivo del STT nuevo (modelo + vocabulary biasing).
- Explicar los 2 puntos no adoptados: audio directo al LLM, y Agents SDK.

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
