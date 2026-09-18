# Wishlist — ideas a futuro (no comprometidas)

Ideas que queremos hacer pero que **todavía no están planificadas ni en curso**.
No es el `ROADMAP.md` (eso es lo que se está ejecutando): esto es el "algún día",
con el análisis técnico ya hecho para no tener que re-pensarlo cuando se retome.

## Orden de prioridad acordado

> **Reescrito el 18/09:** en la Sesión #2 Pato revisó todo lo hecho, lo aprobó,
> y puso una **agenda nueva** que cambia el orden — el proyecto pasa de
> "estabilizar el control por voz" a **construir una interfaz**. Varias de
> estas ideas dejaron de ser "algún día" y son pedidos. Ver
> `docs/feedback_sesiones.md` §6.

1. **Cliente browser + server Python (§5)** — pedido de Pato, y es lo que
   **habilita** los otros dos pedidos: hoy no hay dónde mostrar una cara ni
   dónde reproducir una voz.
2. **Tripulación virtual (§3)** — pedida también: retratos de oficiales (§3.3)
   y respuestas habladas (§3.2). Empezar por la versión de texto, que no
   necesita ningún modelo.
3. **Lo que quedaba de antes**, ahora por detrás de la agenda:
   - Bajar la latencia (§2): queda **sólo el STT local**, prueba #13 de
     `PRUEBAS.md`. Lo demás ya se hizo y está medido.
   - Encadenar comandos (§1).
   - Fase 6 del ROADMAP (rumbo absoluto por click), la de menos urgencia desde
     que se confirmó que Follow Target ya vira la nave.

## Índice

| § | Idea | Estado |
|---|---|---|
| 1 | Encadenar comandos en una sola orden | analizada, no implementada |
| 2 | Bajar más la latencia | analizada, herramienta lista |
| 3 | Tripulación virtual (wake word + oficiales con cara y voz) | **pedida por Pato (18/09)**, no implementada |
| 4 | Otras ideas sueltas | sin analizar |
| 5 | Cliente browser + server Python en background | **pedida por Pato (18/09)**, analizada |

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

> **Pedida por Pato el 18/09** (puntos 2 y 3 de su agenda): "generar imágenes
> de pilotos, oficiales" y "contestar con voz de computadora". Deja de ser
> wishlist. El análisis de abajo ya estaba escrito y sigue valiendo; lo único
> que cambia es que **§3.3 (retratos) y §3.2 (voz) pasan a ser el trabajo**, y
> que los dos necesitan primero el §5 para tener dónde mostrarse. El orden
> sugerido en §3.5 sigue siendo bueno: texto por oficial primero, que no
> necesita ningún modelo.

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

---

### 3.0 El diseño que define todo: llamar al oficial ES el wake word

> **Decidido el 18/09 (Javi), después de la charla con Pato.** Reemplaza al
> push-to-talk y reencuadra §3.1, §3.2 y §3.3: no son tres features sueltas,
> son **una sola mecánica**.

**Cómo se usa:** el capitán llama a un oficial por su nombre o su rol
—*"computadora"*, *"alférez"*, *"comandante"*, *"timonel"*— y eso hace **tres
cosas a la vez**:

1. **Activa la escucha** (lo que hoy hace F12).
2. **Hace aparecer a ese personaje** en la interfaz, con su retrato
   pre-generado.
3. **Enruta la orden**: cada rol ejecuta lo suyo. Órdenes de pilotaje las
   ejecuta el timonel, órdenes de disparo el artillero, y así.

**Por qué esto es mejor que un wake word cualquiera, y no sólo por el clima:**

- **Enrutar por oficial acota el vocabulario, o sea que mejora la precisión.**
  Si decís "artillero", el sistema ya sabe que lo que viene es una orden de
  armas: el parser puede evaluar primero ese subconjunto y el LLM puede recibir
  **sólo las tools de ese rol** en vez de las 32. Menos candidatos es menos
  chance de confundir "fuego" con otra cosa. Es una mejora de precisión real,
  no decoración.
- **Es el filtro de falsos positivos que un micrófono siempre abierto
  necesita.** La regla "si no arranca con el nombre de un oficial, se
  descarta" es dura y barata, y ataca justo el riesgo de la escucha continua.
- **El juego ya define el plantel** (ver abajo), así que no hay que inventar
  roles ni decidir qué comando le toca a quién: ya está decidido por el manual.

### 3.0.1 El plantel sale del propio juego

El Officer MFD de SFC (pág. 102 del manual) ya tiene los oficiales, y **coinciden
casi uno a uno con nuestras categorías de comandos**. Colores de uniforme según
la época TNG de las imágenes de referencia del README:

| Oficial | Nombre | Raza | Rango | Alias por los que responde | Qué ejecuta | Uniforme |
|---|---|---|---|---|---|---|
| **Timón** (Helm) | **T'Lara** | Vulcana | Alférez | "timonel", "piloto", "alférez", "lara" | velocidad, alto total, orbitar, maniobras evasivas, seguir/perseguir, combos de aproximación | Rojo (mando) |
| **Armas** (Weapons) | **Korak** | Klingon | Teniente | "artillero", "armas", "korak" | disparar, alpha strike, ataque total, selección y ciclado de objetivos, memoria de targets | Dorado (operaciones) |
| **Defensa** (Defense) | **Sunek** | Andoriano | Teniente | "defensa", "táctico", "sunek" | escudos al máximo, alerta roja, ECM/ECCM, camuflaje | Dorado |
| **Ciencias** (Science) | **Delon** | Trill | Teniente | "ciencias", "científico", "delon" | escaneo profundo / deep scan, sensores | Azul |
| **Ingeniería** (Repair) | **Grax** | Boliano | Comandante | "ingeniero", "ingeniería", "grax" | reparaciones, energía (todavía sin comandos nuestros) | Dorado |
| **Computadora** | — | — | — | "computadora" | **comodín**: acepta cualquier orden y la enruta sola, que es lo que hace el sistema hoy | — (sin cara, o panel LCARS) |

**Los nombres están elegidos con un criterio técnico, no sólo estético:** son el
vocabulario del wake word, así que tienen que **distinguirse entre sí al oído
de un STT**. Por eso arrancan con consonantes distintas (**L**ara, **K**orak,
**S**unek, **D**elon, **G**rax) y tienen distinta cantidad de sílabas. Un
"Kor'lath" o un "T'Prynn" suenan mejor pero los transcribe mal, y si dos
nombres riman el enrutado se vuelve una lotería.

> Regla práctica: **los alias de rol** ("timonel", "artillero") son el camino
> confiable y **los nombres propios** son el inmersivo. Que respondan por los
> dos, y que el sistema no dependa del nombre propio para funcionar.

### 3.0.1b Chequeo de colisiones: ningún alias puede ser una palabra de comando

Esto hay que hacerlo **antes** de fijar los alias, porque un alias que además
es un comando rompe las dos cosas:

**Colisión real, medida** — se corrió cada alias candidato por
`parsear_comando()`:

| Alias descartado | Qué devuelve hoy | Por qué se descarta |
|---|---|---|
| ~~"escudos"~~ para Defensa | **`ambiguo`** | Choca de verdad: es el comando "escudos al máximo" y ya está en `FRASES_AMBIGUAS`. Queda **"defensa"** |

**Descartados por precaución, no por colisión** (el chequeo dice que hoy están
libres, pero igual no conviene usarlos):

| Alias | Qué devuelve hoy | Por qué igual no |
|---|---|---|
| "jefe de máquinas" | `unknown` — **no choca** | "máquinas" en plural no matchea `\bmaquina\b`, así que técnicamente se podría. Pero depender de que el STT no coma la "s" es frágil. Queda **"ingeniero"** |
| "comandante" | `unknown` — **no choca** | No es colisión: es que **el rango lo tienen varios** oficiales, así que no sirve para enrutar. Sirve para dirigirse al capitán |
| "táctico" para Armas | `unknown` | Se lo lleva Defensa, para que los dos oficiales no compitan por la misma palabra |

**Los 17 alias propuestos dan `unknown`**, o sea que ninguno le roba un match a
un comando: "timonel", "piloto", "alférez", "lara", "artillero", "armas",
"korak", "defensa", "táctico", "sunek", "ciencias", "científico", "delon",
"ingeniero", "ingeniería", "grax", "computadora".

También se midió el parecido fonético entre alias: el único par que pasa el
umbral es "ingeniero"/"ingeniería" (0.84), que son **del mismo oficial**, así
que da igual. Ningún par de oficiales distintos se parece.

> Cuando se implemente, esto **no** se chequea a ojo: se agrega al
> `verificar_cobertura()` de `catalogo_comandos.py` un chequeo que falle si un
> alias de oficial matchea alguna frase del parser. El mismo tipo de guarda que
> ya nos salvó del catálogo desincronizado.

### 3.0.1c La forma que tendría en código

Un `oficiales.py` con la tabla de arriba como dato, y el resto derivado:

```python
OFICIALES = {
    "timon": {
        "nombre": "T'Lara", "raza": "vulcana", "rango": "alferez",
        "alias": ["timonel", "piloto", "alferez", "lara"],
        "uniforme": "rojo", "voz": "<una de las voces de la API>",
        "retrato": "images/oficiales/tlara.png",
    },
    ...
}
```

El mapeo **rol → comandos no se escribe a mano**: se le agrega un campo
`oficial` a cada entrada del catálogo, que ya está agrupado por tipo. Con eso
sale gratis lo de §3.0: filtrar las tools que ve el LLM según a quién llamaste.

Notas de diseño:

- **"Alférez" y "comandante" son rangos, no roles.** Por eso cada oficial tiene
  nombre, raza, rol **y** rango, con los alias aparte. Así "alférez" mapea al
  timonel (el alférez suele estar en el timón, como Crusher en TNG) sin que el
  modelo de datos mienta.
- **Los retratos se generan una vez** con el prompt armado desde la misma
  tabla: raza + rol + color de uniforme + puente estilo TNG, en los dos estilos
  de `images/image.png` (ilustrado y fotorrealista). Hay que elegir uno y que
  todo el plantel sea coherente — mezclar estilos se nota feo.
- **Una voz por oficial**: Korak grave, T'Lara plana y monótona (es vulcana),
  Grax cálido. La voz es por sesión en la Realtime API, así que sale de
  configurarla al abrir la sesión del oficial.
- **"Computadora" es el comodín y conviene que exista siempre**: si no te
  acordás a quién le toca, se lo pedís a la computadora y funciona como hoy.
- **Si le pedís a un oficial algo que no es suyo**, hay dos salidas y las dos
  son baratas: que lo ejecute igual pero conteste el que corresponde, o que el
  oficial te lo devuelva en personaje ("eso es del timonel, capitán"). La
  segunda tiene más gracia y además sirve de señal de error entendible.
- El mapeo rol → comandos **no hay que escribirlo a mano**:
  `catalogo_comandos.py` ya tiene los comandos agrupados; es agregarle un campo
  `oficial` a cada entrada.

### 3.0.2 Consecuencia que reordena todo: el STT local deja de ser opcional

Con push-to-talk, el STT se llama **una vez por orden**. Con micrófono siempre
abierto, hay que transcribir **todo lo que se escucha** para poder chequear si
empieza con el nombre de un oficial.

**Eso hace inviable el STT de nube**: pagarías la API por cada cosa que se diga
en la habitación, y sumarías 1.5-3s a cada una. Con `faster-whisper` local es
gratis y corre en ~0.3s.

> O sea que la **prueba #13 (STT local) pasa de ser "la última mejora de
> latencia" a ser un requisito de este diseño.** Sube al tope de la lista otra
> vez, ahora por una razón distinta.

### 3.0.3 Lo que se pierde al sacar el push-to-talk (decirlo, no esconderlo)

- **El PTT marca exactamente cuándo termina la orden**; sin él hay que detectar
  el final por silencio (VAD), lo que **agrega entre 0.3 y 1 segundo** de
  espera. Manos libres cuesta latencia: es un intercambio, no una mejora pura.
  Mitigable con un umbral de silencio corto (300-500ms).
- **Falsos positivos**: hablar con alguien y que se cuele una orden. El nombre
  del oficial al principio es un filtro fuerte, pero conviene igual una tecla
  de mute rápida y algún comando de cancelación.
- **No borrar el push-to-talk: dejarlo como modo alternativo** detrás de una
  constante. En un ambiente ruidoso, o para grabar una demo, sigue siendo el
  más confiable.

### 3.1 Wake word: cómo implementarlo (detalle técnico)

Hoy usamos push-to-talk (F12) porque es simple y de baja latencia. Un wake
word permite manos libres — importante si estás peleando con el mouse. Con el
diseño de §3.0, el wake word **es el nombre del oficial**.

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

#### 3.2.1 Los tres caminos, según qué arquitectura gane

| Camino | Cómo | Cuándo conviene |
|---|---|---|
| **A. Sale gratis con Realtime** | `output_modalities: ['audio']` + `voice` en la config de sesión (§5.6). El modelo **ya contesta hablando**, no hay paso de TTS | Si vamos por la arquitectura del ejemplo de Pato. Cero trabajo extra |
| **B. TTS de OpenAI** | Una llamada aparte: texto → audio (`gpt-4o-mini-tts`, o `tts-1` que es la rápida). Una voz por oficial | Si el sistema sigue siendo el de hoy y queremos calidad alta |
| **C. TTS local** | `piper` (rápido, offline, gratis, voces descargables) o `pyttsx3` (usa las voces SAPI que Windows ya tiene) | **Se puede hacer HOY, sin server, sin browser y sin internet** |

> **El camino C merece atención**: `pyttsx3` sobre las voces que Windows ya
> trae son dos líneas de código y ninguna dependencia nueva de peso. Y que
> suene **robótico no es un defecto acá, es el personaje**: "contestar con voz
> de computadora" es literalmente lo que pidió Pato. O sea que hay una versión
> de este punto que se puede tener andando **antes** que el server y el
> browser, y que ya es demostrable.

#### 3.2.2 El problema que aparece al juntar voz con micrófono abierto

Con push-to-talk esto no existía. Con el diseño de §3.0 (micrófono siempre
escuchando) sí: **la voz del oficial la va a escuchar el micrófono**, y el
sistema puede terminar hablándose a sí mismo — peor todavía con
`turn_detection: server_vad`, que va a interpretar esa voz como un turno.

Tres salidas, de más simple a más cara:

1. **Silenciar el micrófono mientras suena el TTS.** Controlamos las dos
   puntas, así que es cuestión de cortar la captura mientras dura el audio y
   reanudarla al terminar. Es la solución barata y suficiente.
2. **Auriculares.** Resuelve esto y el problema del volumen del juego de una.
3. **Cancelación de eco** (`echoCancellation` de `getUserMedia` en el browser).
   Existe, pero está pensada para llamadas, no para esto.

**Consecuencia de diseño:** mientras habla un oficial, el capitán **no puede
dar una orden nueva**. Con respuestas de una línea no molesta; si las
respuestas se ponen largas, sí. Argumento para que los oficiales sean
**breves** — que además es lo que suena bien en un puente de nave.

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

---

## 5. Cliente browser + server Python en background

> **Pedido por Pato el 18/09** (punto 5 de su agenda). Análisis hecho el mismo
> día, en caliente.

**Qué es:** partir el sistema en dos procesos en la misma máquina — un **server
Python** que sigue haciendo lo que hace hoy (STT, parser, LLM, inyección de
teclas) y una **página en el browser** como interfaz. No es el "Escenario B"
del README, que separaba en dos máquinas por red: acá las dos piezas viven en
la Windows y hablan por `localhost`.

**Por qué va primero:** los otros dos pedidos (retratos de oficiales,
respuestas habladas) necesitan **un lugar donde mostrarse y sonar**, y hoy no
existe: la consola es todo lo que hay. Dibujar encima del juego no es opción,
es frágil y puede romper el render de DirectX (ya anotado en §3.3). Una ventana
de browser al lado del juego —que corre en ventana vía DxWnd— resuelve eso sin
tocar el juego.

### 5.1 La restricción que no se negocia

**La inyección de teclas se queda en el proceso Python corriendo como
Administrador.** Un browser no puede mandar teclas al juego, y el requisito de
privilegios elevados viene de la Fase 0 (UIPI de Windows). O sea: **el cliente
web es interfaz, nunca control.** Todo lo que hoy funciona —parser, ejecutor,
foco de ventana, guardas— se queda donde está y no se reescribe.

### 5.2 Dónde vive el micrófono: la decisión que define todo

Acá se cruza con el punto 1 de la agenda ("probar push to talk"), y es la
decisión de arquitectura real:

- **Opción A — Micrófono y push-to-talk se quedan en Python; el browser sólo
  muestra.** El server le empuja eventos a la página (transcripción, acción
  ejecutada, respuesta del oficial) por WebSocket o SSE. **Recomendada para
  empezar:** nada de lo que anda hoy cambia, el browser es puramente aditivo, y
  el hook global de `keyboard` ya funciona con el juego en foco.
- **Opción B — El micrófono se muda al browser** (`getUserMedia`). Problema
  serio: **mientras jugás, el foco lo tiene el juego, no el tab del browser**, y
  una página no puede capturar una tecla global. Con esta opción el
  push-to-talk **deja de ser posible** y hay que ir sí o sí a wake word o VAD
  permanente (§3.1), con los falsos positivos que eso trae.
- **Opción C — Híbrida.** Tecla global y micrófono en Python, y además un botón
  de "hablar" en la página para cuando estás mirando la interfaz.

> Esto probablemente explica por qué Pato puso "probar push to talk" **primero**
> en la lista: es lo que define si el cliente puede ser A o tiene que ser B.
> **Confirmarlo con él antes de escribir código.**

### 5.3 Forma mínima que tendría

- Server HTTP + WebSocket en el mismo proceso que el loop actual. `fastapi` +
  `uvicorn` alcanza y sobra; `flask` + `flask-sock` también.
- **Ojo:** el loop de hoy es bloqueante (`while True` + `keyboard.is_pressed`),
  así que el server va en un **thread aparte**, o el loop se reescribe async.
  Es el único cambio estructural real sobre el código actual.
- Escuchar **sólo en `127.0.0.1`**: no hay razón para exponerlo a la red.
- La página arranca mostrando lo que hoy va a consola (transcripción, acción,
  desglose de tiempos). Eso solo ya es entregable y demostrable, y no rompe
  nada de lo que anda.
- Después se le cuelgan encima los retratos (§3.3), el texto del oficial (§3.2)
  y, si aplica, el video (punto 4 de la agenda, todavía sin definir).

### 5.4 Ventaja secundaria que vale la pena

**El audio de salida sale gratis.** Reproducir el TTS desde el browser evita
meter reproducción de audio en Python, que en Windows es más molesto de lo que
parece. Riesgos a tener en cuenta: el juego y el browser peleando por el
dispositivo de audio, y el volumen del juego tapando la voz del oficial (ya
anotado en §3.2).

### 5.5 Qué preguntar antes de escribir código

- ¿"Probar push to talk" apunta a elegir entre las opciones A/B/C de §5.2, a
  probar otra tecla, o a probar wake word?
- ¿"Videítos del juego" es **grabar** clips (para mostrar el proyecto) o
  **mostrar** video dentro de la interfaz? Son dos trabajos distintos.
- ¿La interfaz es para el que está jugando (segundo monitor, al lado del juego)
  o para mostrarle el proyecto a otro? Cambia bastante el diseño.

### 5.6 El ejemplo que pasó Pato: qué hace exactamente

`https://github.com/patopitaluga/ejemplo-agente-realtime` (el `package.json` se
llama **"voicecommander"**: lo armó para esto). Node + Express + `openai`, y
son tres endpoints:

| Endpoint | Qué hace |
|---|---|
| `GET /` | Sirve `views/index.html` |
| `GET /session` | Crea un **client secret efímero** de la **Realtime API** (`openai.realtime.clientSecrets.create`) con la config de sesión: modelo `gpt-realtime`, `output_modalities: ['audio']`, las **tools**, `turn_detection: server_vad`, voz `alloy` e `instructions` |
| `POST /tool_calls` | **Recibe la tool call y la ejecuta.** En el ejemplo es un `send_email` que sólo loguea |

Y el browser (`views/index.html`): captura PCM con un **AudioWorklet** y abre
un **WebSocket directo a `wss://api.openai.com/v1/realtime`** con la key
efímera. **El audio nunca pasa por el server.** El server sólo firma la sesión
y recibe las tool calls.

**Lo importante para nosotros:** en esa arquitectura, el trabajo del server es
*firmar la sesión y ejecutar tool calls*. O sea que **`POST /tool_calls` es
exactamente donde va nuestro `ejecutar_accion()`**. Encaja solo.

Y algo que resuelve un problema que teníamos abierto: **`turn_detection:
server_vad`** — la API detecta cuándo dejaste de hablar. Es justo lo que §3.0.3
marcaba como el costo de sacar el push-to-talk.

### 5.7 ¿Se puede usar Node para el input? (la pregunta directa)

**Técnicamente sí, pero es la peor parte para migrar, y no hace falta.**

Lo que ya sabemos de la Fase 0, y es evidencia dura: el juego es de 2000
(DirectX 7/8) y **sólo reaccionó a `pydirectinput`**, que manda **scancodes**
vía `SendInput` (`KEYEVENTF_SCANCODE`). `pyautogui`, que usa virtual-keys y
mensajes de ventana, **no hizo nada**. Los juegos con DirectInput leen
scancodes, no virtual-keys.

Las opciones en Node tienen justo ese problema:

| Opción | Estado |
|---|---|
| `robotjs` | Sin mantenimiento hace años, compila con node-gyp, y manda **virtual-keys** — el enfoque que ya probamos que no funciona acá |
| `@nut-tree/nut-js` | Activo, pero cambió de licencia, y también es virtual-key por defecto |
| FFI (`koffi`/`ffi-napi`) llamando `SendInput` a mano | **Funcionaría**, porque podés setear el flag de scancode — pero es marshalling de structs de Win32 escrito a mano |

Y el requisito de **correr como Administrador** (UIPI) no cambia con el
lenguaje: es del sistema operativo, no de Python.

> Traducido: migrar el input a Node es **re-hacer la Fase 0 entera**, con
> librerías que arrancan con el enfoque que ya sabemos que falla, para ganar
> cero. La parte que *no* hay que tocar es justo esa.

**Y no hay que elegir**, porque el server de Pato hace muy poco: `/session` son
~20 líneas y el SDK de Python tiene el mismo `realtime.client_secrets.create`;
`/tool_calls` es donde enchufamos lo nuestro. **Portar sus dos endpoints a
Python (FastAPI) es muchísimo menos trabajo que resolver el input en Node**, y
el `index.html` se reusa tal cual: el browser habla con OpenAI, no con el
server, así que le da igual en qué lenguaje esté.

> La otra opción —dejar su server Node y que le pegue a un microservicio Python
> que aprieta teclas— son 3 procesos y 2 lenguajes para no ganar nada. Sólo
> tiene sentido si el objetivo es no tocarle el código a él.

### 5.8 La bifurcación real que abre la Realtime API

Hay que decirlo de frente: **esto es exactamente el "audio directo al LLM" que
Pato propuso en la Sesión #1 y que rechazamos dos veces** — ahora con código
andando. Y en la Sesión #2 ya habíamos admitido que la medición corría a su
favor (el STT es el 80% del tiempo). Con la Realtime API el argumento se
termina de dar vuelta.

**Lo que ganamos:** detección de fin de turno (`server_vad`), voz de salida
—el punto 3 de su agenda, gratis—, tool calls nativas, y el browser como
interfaz para los puntos 2 y 4.

**Lo que perdemos:** el **parser de reglas deja de interpretar**. Era el camino
local, gratis y de microsegundos que resolvía la mayoría de los comandos y que
defendimos dos veces. Con Realtime, todo pasa por la API.

Tres formas de resolverlo:

- **Opción A — Realtime para todo.** Lo más rápido de demostrar. Se paga API
  por todo el audio, y se pierde el camino offline.
- **Opción B — Realtime + nuestro ejecutor detrás de `/tool_calls`.**
  La interpretación la hace el modelo, pero las teclas las sigue apretando el
  código validado, con sus guardas. Es lo que el ejemplo de Pato ya es, con
  nuestro `ejecutar_accion()` en lugar del `send_email`. **La base sensata.**
- **Opción C — Wake word local que abre el micrófono.** Como el browser decide
  **cuándo manda audio**, se puede detectar el nombre del oficial en local
  (gratis) y recién ahí empezar a streamear. Acota el costo, conserva el manos
  libres, y **mantiene vivo el diseño de §3.0**.

**Recomendación: B como base, y C encima cuando el costo moleste.** Las dos son
compatibles: C es una compuerta delante de B.

**A chequear antes de comprometerse:**

- **Precio por minuto de audio** de `gpt-realtime` (entrada y salida). Con
  micrófono siempre abierto es *el* número que decide si hace falta la Opción C.
  No inventar el dato: mirarlo.
- **El esquema de tools cambia de forma**: Realtime las quiere planas
  (`{type, name, description, parameters}`) y Chat Completions anidadas
  (`{type, function: {...}}`). `catalogo_comandos.generar_tools_openai()` ya
  genera todo dinámicamente, así que es una función adaptadora corta, no un
  rediseño.
- **El diseño de oficiales (§3.0) sobrevive**: el enrutamiento por rol se
  expresa en las `instructions`, y `voice` es por sesión — o sea que **una voz
  por oficial** sale de cambiar la sesión o abrir una por oficial.
- **Qué pasa si se cae internet.** Hoy el parser local responde igual; con
  Realtime, no. Vale decidir si queremos un modo degradado (parser + teclas,
  sin voz) o no.
