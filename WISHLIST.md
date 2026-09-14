# Wishlist — ideas a futuro (no comprometidas)

Ideas que queremos hacer pero que **todavía no están planificadas ni en curso**.
No es el `ROADMAP.md` (eso es lo que se está ejecutando): esto es el "algún día",
con el análisis técnico ya hecho para no tener que re-pensarlo cuando se retome.

## Orden de prioridad acordado

1. **PRIMERO: probar y estabilizar lo que ya existe.** Fases 0-2 + LLM fallback
   están implementadas pero falta validación en vivo en la Windows (STT nuevo,
   latencia real, precisión de transcripción con micrófono). No tiene sentido
   agregar features encima de algo no probado.
2. **DESPUÉS: la parte visual / direccionamiento de la nave** (Fase 6 del
   ROADMAP — girar la nave por voz, que hoy no se puede porque el rumbo no se
   controla por teclado sino con mouse sobre la vista táctica).
3. **MÁS ADELANTE: encadenar comandos** (este documento, ítem 1).

---

## 1. Encadenar comandos en una sola orden

**Qué queremos:** poder decir una sola frase con varias órdenes y que se ejecuten
en secuencia, en vez de tener que pedir una, esperar, y volver a pedir. Ejemplos:

> "alerta roja **y** media máquina **y** disparen"
> "seleccioná el enemigo más cercano, seguilo **y** abrí fuego"
> "escudos al máximo **y después** alejate a máxima velocidad"

**Por qué no está hoy:** el parser (`parsear_comando()`) está diseñado para
devolver **una sola acción** — recorre los diccionarios y hace `return` en la
primera coincidencia. Todo lo que venga después en la frase se ignora
silenciosamente. O sea que hoy "alerta roja y disparen" ejecuta solo la alerta
roja, sin avisar que descartó la segunda parte.

**Lo que ya tenemos a favor (no arrancamos de cero):**

- **El mecanismo de ejecución en secuencia ya existe.** Los `COMBOS` ya ejecutan
  varios pasos con una sola frase, con `_presionar_paso()` soportando teclas
  simples, teclas con modificador (`"shift+z"`) y repeticiones (`("s", 8)`). Y
  ya está resuelto lo más molesto: **el foco de ventana se hace UNA sola vez
  para todo el combo**, no una vez por paso (si no, se pagaría la
  `PAUSA_POST_ENFOQUE` de 1s por cada acción encadenada).
- **La diferencia con los combos:** los `COMBOS` son cadenas **predefinidas**
  (nosotros decidimos de antemano que "ataquen con todo" = ECM + Alpha Strike).
  Lo que falta es el encadenado **ad-hoc**: que el capitán arme la secuencia que
  se le ocurra en el momento.
- **El LLM ya podría devolver varias acciones y lo estamos desperdiciando.** La
  API de OpenAI puede devolver **múltiples `tool_calls`** en una sola respuesta,
  pero en `llm_fallback._interpretar_con_openai_function_calling()` hoy leemos
  solo `tool_calls[0]` y descartamos el resto. Habilitar el encadenado por el
  lado del LLM es de las cosas más baratas de esta wishlist.

**Enfoques posibles (a decidir cuando se retome):**

- **Opción A — Split por conectores (parser de reglas, sin LLM).** Partir la
  frase normalizada por conectores (" y ", " y después ", " luego ", ", ") y
  correr `parsear_comando()` sobre cada segmento, devolviendo una lista de
  acciones. Ventaja: gratis, local, sin latencia, reusa todo lo que ya funciona.
  Riesgo: frases donde " y " es parte del comando y no un separador — hay que
  validar segmento por segmento y, si un pedazo da `unknown`, decidir si se
  ignora, se aborta todo, o se manda esa parte al LLM.
- **Opción B — Multiple tool_calls del LLM.** Cambiar el `[0]` por un loop sobre
  todos los `tool_calls` y ejecutarlos en orden. Ventaja: entiende lenguaje
  libre y ordena la secuencia solo, casi sin código nuevo. Desventaja: paga
  latencia + costo de API en cada frase encadenada.
- **Opción C (probablemente la buena) — A con fallback a B.** Igual que la
  arquitectura actual: intentar el split por reglas primero (rápido y gratis) y
  recurrir al LLM solo si algún segmento no se entiende. Mantiene la filosofía
  que ya tiene el proyecto.

**Cosas a resolver sí o sí antes de implementarlo:**

- **Foco de ventana una sola vez** para toda la cadena (igual que los combos),
  o la latencia se vuelve inusable con 3+ acciones.
- **Orden de ejecución:** respetar el orden dicho. "seleccioná el más cercano y
  disparen" no es lo mismo al revés.
- **Qué hacer si falla un eslabón:** ¿seguir con el resto o abortar? Para
  comandos de combate probablemente convenga abortar y avisar.
- **Confirmación en consola** de la cadena completa antes/durante la ejecución,
  para que se entienda qué se interpretó (sobre todo si vino de voz, donde una
  mala transcripción podría encadenar cualquier cosa).
- **Tope de acciones por cadena** (¿3? ¿5?) para que una transcripción delirante
  no dispare 20 teclas contra el juego.

---

## 2. Bajar más la latencia (análisis hecho, pendiente de medir en vivo)

Dónde se va el tiempo hoy, por comando (medido sobre el código real):

| Etapa | Costo actual | Notas |
|---|---|---|
| Grabación | lo que hablás | no se puede bajar (es el audio) |
| **STT (API OpenAI)** | ~0.5-1.5s | red + inferencia |
| Parser de reglas | ~0.0001s | despreciable |
| **Pausa post-enfoque** | **1.0s fijo** | se paga SIEMPRE |
| **Pausas entre teclas** | 0.15s × hasta 8 | 1.2s en comandos de velocidad |

Promedio actual de la etapa de ejecución: **1.75s**. Con valores optimizados
(0.4s de enfoque + 0.05s entre teclas) bajaría a **0.65s** — es decir, más de
**1 segundo de ahorro por comando**, sin tocar el STT.

### 2.1 Pausas (lo más rentable, y ya hay herramienta)
Los valores `PAUSA_POST_ENFOQUE = 1.0` y `PAUSA_ENTRE_TECLAS = 0.15` se
eligieron de forma **conservadora, no medida** (ver Fase 0). Se agregó
`scripts/calibrar_latencia.py` para encontrar el mínimo seguro real en la
máquina, probando valores decrecientes y confirmando visualmente que la nave
reacciona. **Es lo primero que conviene hacer.**

### 2.2 Modelo de STT
- `gpt-4o-mini-transcribe` (actual) ya es el rápido de la familia nueva.
- **`whisper-1` puede ser más rápido** para audios muy cortos (menos overhead
  de modelo), aunque menos preciso. Vale medirlo con el desglose de tiempos.
- **`faster-whisper` local con modelo `tiny`/`base`**: elimina el round-trip
  de red por completo. En un i7 moderno, `tiny` transcribe una frase corta en
  ~0.2-0.4s. Como nuestro vocabulario es **acotado y cerrado**, un modelo
  chico puede alcanzar perfectamente — y el parser de reglas tolera bastante
  error de transcripción. **Es la opción con mayor potencial de mejora.**
- Ya está soportado: es cambiar `STT_BACKEND = "local"` y `MODEL_SIZE`.

### 2.3 Streaming de audio (más ambicioso)
Hoy se graba todo, se manda, y recién ahí se transcribe. Con la API Realtime
de OpenAI (o VAD local) se podría ir transcribiendo **mientras hablás**, de
modo que al soltar la tecla el texto ya esté casi listo. Ahorraría casi todo
el tiempo de STT percibido, a costa de bastante complejidad.

### 2.4 Micro-optimizaciones ya aplicadas
- Cliente de OpenAI cacheado + precalentado (ver ROADMAP, fix del 12/09).
- Ventana del juego cacheada (evita `getAllWindows()` en cada comando).
- Logs de debug apagados por defecto (`DEBUG_VENTANA = False`): ahorraban dos
  llamadas a la API de Windows y dos prints por comando.

---

## 3. Otras ideas sueltas (sin analizar todavía)

- Feedback por voz del sistema (TTS): que la nave conteste "afirmativo, capitán"
  al ejecutar una orden, en vez de solo imprimir en consola.
- Modo "manos libres" real: reemplazar el push-to-talk por wake word
  ("Capitán...", "Computadora...") una vez que la precisión del STT esté
  validada.
- Perfiles de nave: que "media máquina" se calibre distinto según la clase de
  nave (relacionado con la Fase 3 del ROADMAP).
