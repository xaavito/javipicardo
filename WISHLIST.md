# Wishlist — ideas a futuro (no comprometidas)

Ideas que queremos hacer pero que **todavía no están planificadas ni en curso**.
No es el `ROADMAP.md` (eso es lo que se está ejecutando): esto es el "algún día",
con el análisis técnico ya hecho para no tener que re-pensarlo cuando se retome.

## Orden de prioridad acordado

1. **PRIMERO: probar y estabilizar lo que ya existe.** Ver `PRUEBAS.md` — hay
   13 pruebas pendientes en la máquina Windows (latencia, STT nuevo, teclas de
   numpad, combos). No tiene sentido agregar features encima de algo no probado.
2. **DESPUÉS:** bajar la latencia (§2 — el mayor ahorro está en calibrar las
   pausas, que es una prueba ya lista de correr).
3. **MÁS ADELANTE, a elección según qué se extrañe más al jugar:**
   - Encadenar comandos (§1).
   - Tripulación virtual: oficiales que contestan, con cara y voz (§3).
   - Fase 6 del ROADMAP (rumbo absoluto por click). **Bajó de prioridad** al
     confirmarse que Follow Target ya vira la nave hacia un objetivo.

## Índice

| § | Idea | Estado |
|---|---|---|
| 1 | Encadenar comandos en una sola orden | analizada, no implementada |
| 2 | Bajar más la latencia | analizada, herramienta lista |
| 3 | Tripulación virtual (wake word + oficiales con cara y voz) | analizada, no implementada |
| 4 | Otras ideas sueltas | sin analizar |

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

## 2. Bajar más la latencia

> **Actualizado 17/09 — ya medido en vivo, no queda pendiente de estimar.**
> La ejecución bajó de **1.75s a 0.43s** (una tecla) y a 0.65s (cuatro): se
> calibraron las pausas (1.0s → 0.3s y 0.15s → 0.05s) y apareció un costo que
> no estaba en esta tabla, la **pausa interna de `pydirectinput`** (0.1s por
> llamada elemental, ~0.3s por tecla), ahora en 0. El STT medido real es
> **1.5-3.1s**, no 0.5-1.5s, así que hoy es **el 80% de lo que queda**: ver
> §2.2, que pasó a ser lo único con margen grande. Detalle en el ROADMAP.

Dónde se iba el tiempo (tabla original, antes de medir):

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

### 2.1 Pausas — ✅ HECHO (17/09)
Los valores `PAUSA_POST_ENFOQUE = 1.0` y `PAUSA_ENTRE_TECLAS = 0.15` se
eligieron de forma **conservadora, no medida** (ver Fase 0). Se agregó
`scripts/calibrar_latencia.py` para encontrar el mínimo seguro real en la
máquina, probando valores decrecientes y confirmando visualmente que la nave
reacciona. **Hecho:** mínimos reales 0.2s y 0.03s, aplicados con un paso de
margen (0.3s / 0.05s). Ojo con un detalle: esa calibración corrió con los
~0.3s de `pydirectinput` adentro, así que el hueco real entre teclas medido
era ~0.35s y no 0.05s.

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

## 3. Tripulación virtual: wake word + oficiales que contestan con cara

**La idea:** dejar de ser "un sistema que aprieta teclas" y pasar a sentir que
hay una **tripulación** a bordo. Tres piezas que se suman:

1. **Wake word** — decir *"Computadora..."* (o *"Oficial de armas..."*) en vez
   de mantener apretado F12.
2. **Que contesten** — respuesta hablada y/o escrita, en el tono del personaje
   ("Phasers cargados, Capitán").
3. **Que tengan cara** — una **imagen generada por IA** del oficial (un
   klingon, un vulcano, etc.) mostrada junto a su respuesta escrita abajo.

Es la idea más ambiciosa de la wishlist, pero también la que más cambia la
experiencia. Se puede hacer por partes, en el orden de abajo.

### 3.1 Wake word (reemplazar el push-to-talk)

Hoy usamos push-to-talk (F12) porque es simple y de baja latencia. Un wake
word permite manos libres — importante si estás peleando con el mouse.

- **Opciones:** `openWakeWord` o `Porcupine` (Picovoice) son las librerías
  típicas; ambas corren local y liviano. Porcupine permite entrenar palabras
  custom (ej. "Computadora") pero su licencia gratis es limitada;
  openWakeWord es open source.
- **Alternativa barata:** dejar el micrófono escuchando con VAD (detección de
  voz) y filtrar por texto — si la transcripción **empieza con** "computadora"
  o el nombre de un oficial, se procesa; si no, se descarta. Más simple, pero
  gasta STT en todo lo que escucha (con backend local eso es gratis).
- **Riesgo a tener en cuenta:** falsos positivos. Si estás hablando con
  alguien y el sistema cree que le diste una orden, te puede meter la nave a
  toda máquina en medio de un combate. Conviene poder apagarlo rápido.

### 3.2 Que contesten (TTS + personalidad)

- **Texto primero (fácil):** el oficial responde por consola, con frases
  propias del rol. Esto ya se puede hacer hoy con un diccionario de respuestas
  por tipo de comando, sin ningún modelo.
- **Voz (TTS):** la API de OpenAI tiene text-to-speech con varias voces
  (`tts-1` es la rápida). Se le puede asignar **una voz distinta a cada
  oficial**, lo cual ayuda muchísimo a la ilusión de tripulación. También hay
  opciones locales (`piper`, `pyttsx3`) si no se quiere pagar/depender de red.
- **Cuidado con la latencia:** si el oficial contesta *antes* de que la acción
  se ejecute, se siente lento. Mejor: ejecutar la tecla primero y que la voz
  suene **mientras** el juego ya reaccionó. También conviene **cachear** los
  audios de las frases fijas más comunes ("Afirmativo, Capitán") en vez de
  generarlos cada vez.
- **Ojo con el audio del juego:** si el juego está fuerte, la voz del oficial
  se puede perder. Quizá haya que bajar el volumen del juego o usar auriculares.

### 3.3 Oficiales con cara generada por IA

- **Idea:** cada oficial es un personaje con **raza** (klingon, vulcano,
  humano, andoriano...) y **rol** (armas, timón, ingeniería, ciencias). Al
  contestar, se muestra su retrato + su respuesta escrita abajo, tipo viñeta
  de cómic o ficha de personaje.
- **Cómo generar las imágenes:** con `gpt-image-1` / DALL·E de OpenAI. Clave:
  **generarlas UNA vez y guardarlas en disco**, no en cada respuesta —
  generar una imagen tarda segundos y cuesta, sería inviable en tiempo real.
  La idea es tener un "plantel" fijo de 4-6 oficiales ya generados.
- **Nivel intermedio (más rico, más trabajo):** generar **2-3 variantes de
  expresión** por oficial (neutral, alarmado, satisfecho) y elegir según el
  contexto: si la nave está recibiendo daño, mostrar la cara de alarma. Sigue
  siendo pre-generado, solo hay que elegir qué archivo mostrar.
- **Dónde mostrarlo:** el juego corre en ventana vía DxWnd, así que se puede
  poner una **ventanita aparte** al costado (Tkinter/PyQt, o incluso una
  página HTML local que se auto-actualice). No conviene intentar dibujar
  encima del juego: es frágil y puede romper el render de DirectX.
- **Bonus barato:** que el **texto** del oficial lo genere el LLM que ya
  usamos como fallback, pidiéndole que responda en el tono del personaje
  ("sos un artillero klingon, contestá en una línea, agresivo"). Reusa
  infraestructura que ya está.

### 3.4 Por qué esto encaja bien con lo que ya tenemos

- El **catálogo dinámico** (`catalogo_comandos.py`) ya sabe qué comandos
  existen y de qué tipo son — se le puede agregar a cada uno **qué oficial lo
  responde** (armas → artillero, velocidad → timonel) sin rehacer nada.
- El **LLM de fallback** ya está integrado: sirve tanto para interpretar
  órdenes raras como para redactar las respuestas en personaje.
- Como el parser ya devuelve **acciones estructuradas**, es fácil enganchar
  "después de ejecutar, que conteste el oficial X" sin tocar la lógica de
  teclas.

### 3.5 Orden sugerido para atacarlo

1. Respuestas **de texto** por oficial, en consola (barato, ya se puede).
2. Ventanita aparte con **retratos pre-generados** + el texto abajo.
3. **TTS** con una voz por oficial (con caché de frases comunes).
4. **Wake word** para manos libres (lo más riesgoso por los falsos positivos,
   mejor dejarlo para cuando el resto esté sólido).

---

## 4. Otras ideas sueltas (sin analizar todavía)

- Perfiles de nave: que "media máquina" se calibre distinto según la clase de
  nave (relacionado con la Fase 3 del ROADMAP).
- HET 180° para el combo de retirada: hoy "aléjense a máxima velocidad" solo
  acelera, no gira. **Corrección (17/09):** `Numpad 5` no es el HET 180°, es un
  **"Start HET"** genérico; las direcciones del HET (izquierda, derecha, 180°,
  hard) están sólo como botones del Helm MFD, sin hotkey (`SFCquick.pdf`
  pág. 9). O sea que el HET 180° por voz **no es posible hoy** sin control de
  mouse. Queda a la espera de la Fase 6.
