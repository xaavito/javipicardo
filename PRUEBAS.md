# Pruebas pendientes en la máquina Windows

Checklist de lo que hay que probar **en la PC del juego**, numerado y con
lugar para anotar la medición. Se actualiza cada vez que se hacen cambios que
requieren validación en vivo.

- Marcar `[x]` cuando se valide, y completar el campo **Resultado**.
- Los resultados confirmados se vuelcan después al `ROADMAP.md` (la bitácora
  histórica); este archivo es la **lista de trabajo del día**.
- Si algo falla, anotarlo igual: un "no funcionó" medido vale tanto como un OK.

**Preparación (siempre):** juego abierto **desde DxWnd** · consola **como
Administrador** · misión con la nave pudiendo moverse.

### Qué necesita cada prueba (leer antes de arrancar)

No todas necesitan lo mismo, y varias fallan "porque sí" si el estado de la
partida no es el correcto — sobre todo las que dependen de tener un objetivo
seleccionado o energía de movimiento libre.

| Prueba | ¿Juego? | Estado de la partida que necesita |
|---|---|---|
| Pre-vuelo (`catalogo_comandos.py`, `oficiales.py`) | **No** | Nada. Corre en cualquier lado |
| #20 oficiales | No hace falta | Con el juego se ve además que la tecla llega; sin él, sólo el texto y la voz |
| #19 ambigüedad | **No** | Ninguno: justamente no tiene que mandar teclas |
| #10 no soportados | **No** | Ninguno: tampoco manda teclas |
| #15 velocidad % | **Sí** | Nave **libre de moverse**, fuera de combate para poder mirar el HUD |
| #4 evasivas | **Sí** | A **cuarto de máquina** (necesita 6 puntos de energía libres), **camuflaje apagado**, y el **Helm MFD abierto** |
| #8 targeting | **Sí** | **Varios contactos a la vista**, y al menos dos hostiles |
| #5 memoria de targets | **Sí** | **2-3 enemigos** distintos, para poder cambiar de objetivo y volver |
| #6 y #7 combos | **Sí** | Enemigos a distancia, con **espacio para acelerar** sin chocar |
| #16 fallback del LLM | No hace falta | Ninguno: lo que se mira es la consola |
| #9 STT | **Sí** | Cualquiera: se mira la transcripción, no el efecto |
| #13 STT local | No hace falta | Ninguno para medir latencia; con juego para confirmar que además ejecuta |
| #11 hotkeys | **Sí** | En el menú **Options → Hotkeys**, no en misión |
| #12 foco | **Sí** | Nave libre de moverse, y la consola **al frente** |

> Las que dicen "No hace falta" igual conviene hacerlas con el juego abierto si
> ya está: no molesta, y de paso se confirma que la tecla llega.

---

## 🔴 Prioridad ALTA — bloquean o invalidan otras cosas

### ~~1. ¿"Seguir a esa nave" (Follow Target) vira la nave o solo la cámara?~~

- [x] **RESUELTA (13/09): VIRA LA NAVE y la persigue.** ✅

No es solo cámara. Es el **único comando por teclado que apunta la nave a un
objetivo** sin usar el mouse — la herramienta de movimiento por voz más útil
que tenemos. Los combos #6 y #7 quedan validados en su paso de rumbo.

> Consecuencia: baja la urgencia de la Fase 6 (rumbo por click con mouse), que
> era el plan previsto para resolver el direccionamiento.

### ~~2. Calibrar las pausas~~

- [x] **RESOLVED (17/09).** ✅ Minimums that worked: `PAUSA_POST_ENFOQUE`
      **0.2s** and `PAUSA_ENTRE_TECLAS` **0.03s**. Applied one step above, at
      **0.3s / 0.05s**.

Real saving: ~0.7s on **every** command and ~1.7s on the 8-key ones. A
single-key command drops from ~1.45s to ~0.55s of execution.

### ~~3. ¿Se arregló el delay del primer comando?~~

- [x] **RESOLVED (17/09).** ✅ The warm-up does its job: it absorbs the 4.23s
      of API connection at startup, and **execution** is a constant 1.45s from
      the very first command.

What is left (STT 3.12s on the first against 2.15-2.57s afterwards) is API
variance, not lazy initialization.

### ~~18. La pausa interna de pydirectinput (`PAUSE = 0`)~~ — RESUELTA

**Why it matters:** the 17/09 numbers put execution at 0.76s for one key and
1.88s for "media máquina", far above what our own pauses explain.
`pydirectinput` sleeps 0.1s after **every** elementary call, and a `press()`
is three of them, so it was adding **~0.3s per key**. It is now 0, and our
calibrated `PAUSA_ENTRE_TECLAS` does the spacing.

**Careful:** the calibration in test #2 ran with that hidden 0.3s in place, so
the real gap between keys was ~0.35s. With `PAUSE = 0` it drops to 0.05s,
which was never tested. **A dropped key is what to watch for**, and that is
why this goes first: if keys get dropped, every other test of the day lies.

**How to test it, in this order:**
1. "alerta roja" → the game must react. Expected `ejecucion:` ~0.45s (0.76s
   yesterday).
2. "alto total", then "media máquina" → **count the speed steps on the HUD**:
   it has to land on the same speed as before, not short. Expected
   `ejecucion:` ~0.6s (1.88s yesterday).
3. Repeat step 2 five times. This is the risky one: 4 presses 0.05s apart.
4. "alpha strike" → it has to fire. `shift`+`z` is the most fragile one.
5. "ataquen con todo" → ECM **and** alpha strike, both.

- [x] **RESUELTA (17/09), los 5 pasos.** ✅ **Ninguna tecla se perdió**, ni en
      las secuencias de velocidad ni con modificador: "alpha strike"
      (`shift`+`z`) y "ataquen con todo" (ECM + alpha strike) andan los dos,
      que eran los casos frágiles.
- [x] **Mediciones, clavadas en lo predicho:** **0.43s** una tecla (era
      0.76s), **0.65-0.69s** "media máquina" (era 1.88s), **0.86-0.89s** "alto
      total", que son 8 teclas.

Con esto la etapa de ejecución queda cerrada: de 1.75s originales a **menos de
0.5s** en un comando de una tecla. Todo lo que queda de latencia es el STT
(prueba #13).

> Si alguna vez empieza a perderse una tecla: `PAUSA_INTERNA_PYDIRECTINPUT` en
> `fase1_text_commands.py`, subirla a `0.02`, después `0.05`, y en último caso
> volver a `0.1` y re-correr `calibrar_latencia.py`.

### 13. Local STT (`tiny`) vs. the API — the biggest saving left

**Why it matters:** with the pauses already calibrated, the **STT is now
60-70% of the total** (1.7-3.1s out of 3.5-5.8s). The API sits well above the
0.5-1.5s estimate. `faster-whisper` with `tiny` drops the network round-trip
and should land around 0.2-0.4s, and our vocabulary is small and closed.

**How to test it:**
1. `pip install faster-whisper` (if it is not installed).
2. In `fase2_voice_commands.py`: `STT_BACKEND = "local"` and
   `MODEL_SIZE = "tiny"`.
3. First run downloads the model (~75MB, once, needs internet).
4. Say the same 5 phrases as test #9 and compare the `STT:` field.

- [ ] **Latency with local `tiny`:** ______s (vs. ~2.3s on the API)
- [ ] Is the accuracy enough for our vocabulary? ⬜ yes · ⬜ no
- [ ] If `tiny` is not accurate enough, try `base` before going back to the API
- Notes:

### ~~17. Guard against the STT echoing its prompt~~

- [x] **RESOLVED (17/09).** ✅ Both guards fired several times each
      (`[grabacion de 0.00s...]` on taps, `[!] La API devolvio el prompt...`
      on silent holds) and **no spurious key reached the game**.

Side effect found and fixed: the warm-up at startup also sends silence, so it
printed that same warning on every run. `precalentar()` now calls the API
without the prompt, which also makes the warm-up cheaper.

---

## 🟡 Prioridad MEDIA — funcionalidad nueva sin validar

### 4. Numpad — "maniobras evasivas" no hace nada visible

**Status (17/09):** the key reaches the game (`-> Tecla: divide`) but nothing
visible happens and nothing appears selected. Two hypotheses were on the
table, and **#4b killed one of them**: numpad keys do arrive (Orbit and Follow
both work), so this is not about key delivery. What is left is the conditions
the manual puts on EM (SFCfullMan pages 102 and 140):

- EM **costs 6 points of movement energy**: with no spare energy it does not
  engage at all.
- It **cannot run together with the cloaking device**, they are exclusive.
- The effect is not a showy zigzag, it is "small, swift course changes". What
  does show is the **restrictions**: no shuttles/fighters/missiles/plasma, no
  mines/transporters/tractors, turn rate down by 1.
- Turning it **off** needs the "Normal Maneuvering" button on the Helm MFD,
  which **has no hotkey**.

**How to test it, in this order:**
1. **"cuarto de máquina"**, not full speed: EM needs 6 points of movement
   energy spare, and at full speed there may be none.
2. Confirm the cloak is **off** (if "camuflaje" was used earlier, EM will
   never engage).
3. Open the **Helm Officer MFD** and watch its Erratic button while saying
   "maniobras evasivas". **That button is the real result of this test**: if it
   lights up, the key works and the effect is just subtle.
4. Say "maniobras evasivas" a second time → check whether it toggles off or
   stays on. If it stays on, by voice we can turn it on and **not** off, which
   decides whether it belongs in a combo at all.
5. If the button never lights up even at low speed with no cloak, then the
   binding is the last suspect: check Options → Hotkeys for what `Numpad /` is
   actually bound to in this edition. Note this is now unlikely, since the
   other two numpad keys do work.

**Resultado 24/09:** la consola manda `divide` pero en el juego no pasa nada,
ni se ilumina nada.

**Hipótesis nueva, y encaja con todo lo medido:** de las tres teclas de numpad,
las dos que funcionan (`–` Orbit, `*` Follow) son teclas **normales**, y la
única que falla (`/`) es la única **extendida** — su scancode `0x35` necesita
el flag `E0` para distinguirse de otra tecla. Si `pydirectinput` no lo manda,
el juego recibe una tecla distinta, que es exactamente el síntoma.

**El test que lo decide, 5 segundos:** apretá **físicamente** el `/` del
teclado numérico con el juego en foco.
- Si a mano **sí** funciona → es el flag extendido, y se arregla mandando esa
  tecla con `SendInput` directo por `ctypes`.
- Si a mano **tampoco** → el binding del juego es otro: mirar Options → Hotkeys.

- [ ] A mano funciona: ⬜ sí (es el flag) · ⬜ no (es el binding)
- [ ] Erratic: ⬜ the MFD button lights up · ⬜ nothing at all
- [ ] Does saying it twice turn it off? ⬜ yes, it toggles · ⬜ no, it stays on

### ~~4b. Orbit Target: los manuales dicen teclas distintas~~

- [x] **RESUELTA (17/09): `subtract` (Numpad `–`) orbita.** ✅ Vale
      `SFCfullMan` p.159; el `.` de `SFCquick` p.24 es errata. Escrito en
      `docs/hotkeys_sfc2.md` y en la constante `TECLA_ORBITAR`.

**Corolario que acota la #4:** con Orbit (`–`) y Follow (`*`) confirmados,
**las teclas del numpad sí llegan al juego**. Si "maniobras evasivas" (`/`) no
hace nada, ya no hay que sospechar de `pydirectinput` ni del hotkey — queda
sólo la hipótesis de las condiciones de EM.

### 5. Memoria de targets (seguir a UNA nave concreta)

**Cómo probarlo, en orden:**
1. "siguiente enemigo" → hasta la nave que quieras
2. "guardar objetivo uno" (`ctrl+5`)
3. Cambiar de target varias veces a propósito
4. "objetivo uno" (`5`) → ¿volvió a **esa misma** nave?

- [ ] **Resultado:** ⬜ funciona · ⬜ falla en el paso ____
- Notas (¿`ctrl+5` llega bien al juego?):

### 6. Combo "vamos al enemigo más cercano"

Secuencia esperada: `` ` `` → `Numpad *` → 6× `s`

- [ ] Selecciona el enemigo más cercano
- [ ] Pone rumbo hacia él *(depende de la prueba #1)*
- [ ] Acelera a ~3/4 de máquina
- Notas:

### 7. Combo "busca un enemigo"

Secuencia esperada: `y` → `Numpad *` → 6× `s`

- [ ] Cicla a un enemigo
- [ ] Al repetirlo, **va rotando** entre enemigos distintos
- [ ] Pone rumbo y acelera
- Notas:

### 8. Targeting nuevo

| Comando | Tecla | ¿Funciona? |
|---|---|---|
| "siguiente enemigo" (solo enemigos) | `y` | [x] 17/09 |
| "enemigo anterior" | `shift+y` | [x] 17/09 |
| "objetivo anterior" | `shift+t` | [ ] |
| "deseleccionar objetivo" | `\` | [ ] 17/09: came out as "deseleccionar **a** objetivo" and was not recognised; synonym added, retest |

- [x] "siguiente objetivo" (`t`) also confirmed working on 17/09
- Notas:

### 9. STT nuevo: ¿mejoró precisión y latencia?

**Qué se cambió:** `whisper-1` → `gpt-4o-mini-transcribe`, + vocabulario del
juego vía `prompt`, + `temperature=0`.

**Cómo probarlo:** decir estas frases y ver si las transcribe bien:

| Frase dicha | ¿Transcribió bien? |
|---|---|
| "media máquina" | [x] 17/09 |
| "alerta roja" | [x] 17/09 |
| "alpha strike" | [x] 17/09 |
| "escudos al máximo" | [x] 17/09 — came out as "escudos **a** máximo", which the parser did not have; added as a synonym |
| "maniobras evasivas" | [ ] |

- [x] **Average STT latency:** ~2.3s (1.7-3.1s) — **well above** the estimate,
      see test #13
- [ ] Only "maniobras evasivas" left
- Notas (palabras que sigue transcribiendo mal → agregar a
  `PROMPT_VOCABULARIO`):

### 10. Mensajes de comandos no soportados

- [ ] "alerta amarilla" → explica que existe en el HUD pero sin tecla
- [ ] "interceptar" → explica que es del Helm MFD y sugiere alternativas
- [ ] Confirmar que **no** tarda (no debería llamar al LLM)
- Notas:

### 15. Speed by explicit percentage — el % no llega donde debería

**Why it matters:** "velocidad al 70 por ciento" was parsed but sent no key at
all, so the order was silently dropped. It now rounds to the closest of the 5
levels (70% -> level 3, ~75%). Rounding is all we can do before Fase 3, so
what needs checking is whether it feels right while playing.

**How to test it:** say each phrase and watch the HUD.

**Resultado 24/09:** `alto total` anda; `velocidad al 70 por ciento` **no
llega a 3/4**. La causa no es el redondeo sino que **nunca se midió cuántos
pasos tiene el acelerador de la nave**: las 6 pulsaciones salían de un `8` que
se eligió a ojo en la Fase 1. Ahora `STEPS_VELOCIDAD` se deriva de
`PASOS_HASTA_MAXIMA`, y ese número se mide con `calibrar_velocidad.py`.

**Antes de repetir esta prueba:**
1. `python scripts\calibrar_velocidad.py` — acelera de a una pulsación y te
   pregunta cuándo dejó de subir. Juego abierto, nave libre, HUD a la vista.
2. Poné el número que te dé en `PASOS_HASTA_MAXIMA`, en
   `fase1_text_commands.py`.
3. Recién ahí volvé a la tabla de abajo.

| Phrase | Expected level | Did the ship react? |
|---|---|---|
| "velocidad al 70 por ciento" | 3 (6x `s`) | [ ] |
| "velocidad al 50 por ciento" | 2 (4x `s`) | [ ] |
| "velocidad al 10 por ciento" | 0 (8x `a`) | [ ] |

- [ ] Is rounding to the nearest quarter enough, or is the exact % missed?
- Notes:

### 16. LLM fallback live (never tested) + the commands it was missing

**Why it matters:** the fallback has been implemented since Fase 4 but was
never run against the real API. On top of that, the catalog the LLM sees was
out of sync with the parser: 16 commands the parser understood were missing
from it (cycling enemies, cycling backwards, deselecting, orbiting, erratic
maneuvers and the whole target memory). It now exposes 32 tools.

**How to test it:** say free-form phrases the parser does NOT recognise, to
force the fallback (the console prints "consultando al LLM").

| Phrase (deliberately odd) | Command it should pick | Right? |
|---|---|---|
| "che, dale una vuelta alrededor de esa nave" | orbitar | [ ] |
| "esquivá como puedas" | maniobras evasivas | [ ] |
| "acordate de esta nave en la ranura dos" | guardar objetivo dos | [ ] |
| "pasá al siguiente hostil" | siguiente enemigo | [ ] |
| "soltá el blanco" | deseleccionar objetivo | [ ] |

- [x] **17/09 — first live runs:** it declined correctly on "Me llamo Akira"
      (no tool called) and answered "Seguir enemigo" with cycling, which was
      **wrong** — that one is now a parser synonym for Follow Target.
- [ ] **404s to chase:** two calls died with `Error code: 404` in 0.19s while
      others worked in 0.88-1.45s, so it is intermittent rather than a bad
      model name. The message now prints the exception type, the model and the
      body. Say **"esquivá como puedas"** three times and **"che, dale una
      vuelta alrededor de esa nave"** three times, and paste whatever the
      `detalle:` line says.
- [ ] **First fallback latency:** ______s · **second:** ______s
      *(the OpenAI client is cached now, so the first one should not be slower
      than the rest — write it down if it still is)*
- [ ] Run `python catalogo_comandos.py` and confirm it reports "Cobertura OK"
      and 32 commands
- Notes:

### 19. Palabra suelta ambigua: que no adivine — casi cerrada

**Why it matters:** on 17/09 the STT clipped "media máquina" down to
"Máquina.", the parser did not know it, and **the LLM guessed "cuarto de
máquina"** — so half a word accelerated the ship. Guessing wrong is worse than
doing nothing. A single ambiguous word now answers with the alternatives and
presses no key, without spending an LLM call either.

**How to test it:**
1. Say just **"máquina"** → expected: `es ambiguo, no se ejecuta nada` plus
   the list of speeds. **No** `[consultando al LLM]` line, and no reaction in
   the game.
2. Same with **"velocidad"**, **"objetivo"**, **"escudos"** and **"alerta"**.
3. Then say "media máquina" and "alerta roja" in full → they have to keep
   working exactly as before.
4. Force a truncated phrase on purpose: start talking a beat after pressing
   F12, so only the tail is recorded. Whatever comes out, the ship must not
   move unless the transcription really is a full command.

- [x] **24/09:** las cinco palabras sueltas piden desambiguación correctamente.
- [ ] Falta confirmar que **no** aparece `[consultando al LLM]` en ninguna, y
      el caso de la frase cortada por voz.
- [ ] Any other fragment the STT produces often → tell me and it goes in
      `FRASES_AMBIGUAS`
- Notes:

### 20. Los oficiales contestan (texto, y voz si están los wav)

**Why it matters:** first piece of Pato's agenda that can be shown without the
browser or the server existing. The answers are acknowledgements only — "sí,
capitán" — so the phrase set is fixed and small, which is why the audio is
generated once to disk instead of synthesised live: better voices, no per-use
cost, and playing a file adds ~0ms to a command.

**How to test it, text first (needs nothing installed):**
1. `python scripts\fase1_text_commands.py`
2. "alerta roja" → **Sunek** answers · "media máquina" → **T'Lara** ·
   "disparar" → **Korak** · "escaneo profundo" → **Delon**
3. Something unknown ("hola qué tal") → **Computadora** says it does not know
   how; "máquina" → it asks you to be more precise.
4. Confirm the answer comes **after** the key, never before.

**Then the voice:**
5. `python scripts\generar_voces.py` (once, needs `OPENAI_API_KEY`). It writes
   21 wav files to `audio/oficiales/`.
6. Repeat step 2 and listen. The voices should be different per officer.
7. Check it does not get in the way: the sound plays **async**, so the next
   command should not have to wait for it.

- [x] **24/09, texto:** el oficial correcto contesta en todos los casos.
- [x] **24/09, audio: RESUELTO.** ✅ Sonaron las voces correctas de cada
      oficial. La prueba #20 queda cerrada: el oficial que corresponde al
      comando contesta, por texto y con su voz.
- [ ] Voice: ⬜ sounds · ⬜ nothing plays · ⬜ it plays but lags the command
- [ ] Portraits: ⬜ the 7 came out usable · ⬜ some need their RAZAS entry
      tweaked and a `--rehacer` (say which)
- [ ] Do the voices work with the game audio on, or do they get buried?
- [ ] `VOZ_ACTIVADA = False` in `oficiales.py` turns the audio off and leaves
      the text
- Notes (phrases to change, voices that do not fit the character):

### ~~21. Micrófono Bluetooth: fase2 dejó de escuchar~~

**Por qué importa:** al conectar un auricular BT con micrófono, `fase2` no
capta nada. Windows expone **cada auricular BT como dos dispositivos**: el
perfil **A2DP** (buen sonido, **sin micrófono**) y el **HFP/Hands-Free** (hay
micrófono, pero la salida baja a calidad teléfono). Si Windows quedó en A2DP,
el micrófono no existe para las aplicaciones y se graba silencio **sin ningún
error**.

**Cómo probarlo:**
1. `python scripts\probar_microfono.py`
2. Mirá la lista: tiene que aparecer el auricular **con canales de entrada** y
   con `16000 Hz mono: OK`. Si aparece dos veces, el que sirve es el que dice
   *Hands-Free* o *Headset*, no el que dice *Stereo*.
3. Mientras graba los 4 segundos, **hablá**: la barra de nivel tiene que
   moverse.
4. Si el default no es el que querés: `python scripts\probar_microfono.py 3`
   (el número que muestra la lista) y probá ése.
5. Cuando encuentres el bueno, ponelo en `fase2_voice_commands.py`:
   `DISPOSITIVO_ENTRADA = 3`

- [x] **RESUELTA (24/09):** el micrófono quedó andando. Queda anotado que el
      **reconocimiento es pobre con el BT**, lo cual es esperable: en perfil
      Hands-Free el micrófono va comprimido a calidad teléfono, que es justo
      lo que más le cuesta a un STT. Se va a reintentar con otros micrófonos.
      **Consecuencia:** la prueba #13 (STT local vs. API) queda **en espera de
      un micrófono decente** — con audio de teléfono el micrófono domina el
      resultado y la comparación no mide lo que se quiere medir.
- [ ] ¿Windows lo puso en Hands-Free automáticamente, o hubo que forzarlo en
      Configuración → Sonido?
- **Ojo con la contrapartida:** en modo Hands-Free, **la voz de los oficiales
  también suena a teléfono**, porque es el mismo dispositivo. Si molesta, la
  salida se puede dejar en los parlantes y usar el BT sólo como micrófono.
- Notas:

### 22. Aparece una nave: marcarla como objetivo e ir hacia ella

**No es para ahora** — queda anotada para cuando haya tiempo de jugar en serio.

**Qué se quiere saber:** en medio de una misión aparece un contacto nuevo.
¿Qué se dice para que la nave lo tome como objetivo y navegue hasta él?

**Lo que hay hoy**, y por qué puede no alcanzar:

| Comando | Qué hace | Cuándo falla |
|---|---|---|
| `vamos al enemigo mas cercano` | `` ` `` + Follow + 6× `s` | Si el que apareció **no es el más cercano**, te manda a otro |
| `busca un enemigo` | `y` + Follow + 6× `s` | Cicla al **siguiente** del ciclo, no al que vos viste. Puede tardar varios intentos |
| A mano | `siguiente enemigo` hasta verlo seleccionado → `seguir a esa nave` → `media maquina` | Funciona siempre, pero son tres órdenes y hay que mirar el HUD entre una y otra |

**La limitación de fondo, que conviene tener presente:** el sistema **es
ciego**. No sabe qué naves hay ni cuál apareció — sólo el jugador lo ve en
pantalla. Por eso "esa nave" únicamente puede significar *el objetivo que está
seleccionado ahora*. Para que exista un "marcá la que acaba de aparecer" haría
falta leer el HUD (la misma familia de problema que la Fase 3 y la Fase 6).

**Cómo probarlo:**
1. Misión con enemigos que **entren en escena** en distintos momentos, no todos
   al principio.
2. Cuando aparezca uno nuevo, probar `vamos al enemigo mas cercano` y anotar si
   agarró **ése** o agarró otro.
3. Si agarró otro: probar `busca un enemigo` y contar **cuántas veces** hay que
   repetirlo hasta llegar al que querías.
4. Probar la vía manual de tres órdenes y comparar cuál se siente mejor jugando.
5. Una vez enganchado, mirar si **Follow lo sigue** cuando el enemigo maniobra,
   o si hay que volver a darle rumbo.

- [ ] ¿El combo agarra al que apareció, o a otro? ______
- [ ] Repeticiones de `busca un enemigo` hasta el correcto: ______
- [ ] ¿Follow lo mantiene mientras el enemigo maniobra? ⬜ sí · ⬜ se pierde
- [ ] ¿Cuál de las tres vías se siente mejor jugando?
- Notas (si se extraña un comando que hoy no existe, anotarlo acá):

### 23. El panel web: que aparezca la cara del oficial

**Por qué importa:** es el punto 5 de Pato en su versión mínima, y junta sus
puntos 2, 3 y 5 en una sola demo — decís una orden y aparece el retrato del
oficial que contesta, con su frase. Sin instalar nada: todo librería estándar.

**Preparación:** `git pull` primero. Los retratos tienen que estar en
`images/oficiales/` (7 archivos).

**Pasos:**
1. `python scripts\fase1_text_commands.py`
2. En las primeras líneas tiene que aparecer:
   `Panel de la tripulacion: http://127.0.0.1:8765`
3. Abrí esa URL en el browser. Debería decir *"Esperando órdenes, capitán"*.
4. Acomodá el browser **al lado** de la ventana del juego (o en otro monitor).
5. Escribí, uno por uno, y mirá el panel después de cada uno:

| Escribís | Tiene que aparecer |
|---|---|
| `alerta roja` | **Zheva** (andoriana, uniforme dorado) |
| `media maquina` | **T'Lara** (vulcana, uniforme rojo) |
| `disparar` | **Korak** (klingon) |
| `escaneo profundo` | **Delon** (trill, uniforme azul) |
| `hola que tal` | **COMPUTADORA**, sin retrato |
| `ayuda` | **nada cambia** — la ayuda no lleva acuse de recibo |

6. Repetí un comando ya usado: la frase puede cambiar (hay variantes por
   oficial), el retrato no.

- [ ] **Resultado:** ⬜ aparecen bien · ⬜ el panel no carga · ⬜ carga pero no
      cambia · ⬜ falta algún retrato
- [ ] ¿La ventana del browser le roba el foco al juego? *(no debería: el panel
      sólo pregunta el estado, no toca nada)*
- [ ] ¿Se ve bien al lado del juego, o hay que achicarlo?

**Si algo falla:**
- No aparece la línea de la URL → `PANEL_WEB` está en `False` en `oficiales.py`
- La URL no abre → el puerto 8765 está ocupado; lo dice en la consola al
  arrancar. Se cambia `PUERTO` en `panel_web.py`
- Carga pero el retrato sale roto → falta ese PNG en `images/oficiales/`
- Carga y no cambia nunca → el panel está andando pero no le llega nada;
  fijate si la consola imprime la línea `[Nombre] frase`

**Después, por voz:** lo mismo con `fase2_voice_commands.py`. Es el mismo
panel: la voz no tiene ejecutor propio, usa el de la Fase 1.

#### 23b. El audio ahora lo reproduce la página

**Qué cambió:** si hay una página del panel abierta, **el audio lo toca el
browser**, no Python. Si no la hay, lo sigue tocando Python como antes. El
sistema lo detecta solo: la página pregunta el estado cada 300ms, y si hace más
de 3 segundos que nadie pregunta, se da por cerrada.

**Y el foco:** por **voz**, el script ya **no le devuelve el foco a la
consola** — se queda en el juego, que es donde tiene que estar. Por texto sigue
volviendo, porque ahí sí hay que seguir escribiendo.

**Pasos:**
1. Con el panel abierto, dar una orden. La primera vez el browser **bloquea el
   audio** y aparece un cartel **"🔊 Activar sonido"**: click en cualquier lado
   y listo, no vuelve a aparecer.
2. Confirmar que la voz **se escucha una sola vez**, no dos.
3. Cerrar la pestaña del panel, esperar 3 segundos y dar otra orden → la voz
   tiene que volver a salir por Python.
4. Volver a abrir el panel y dar otra → vuelve a salir por el browser.
5. Por voz (`fase2`), después de una orden: **el foco tiene que quedar en el
   juego**, no saltar a la consola.

- [ ] ⬜ se escucha una vez · ⬜ se escucha doble · ⬜ no se escucha
- [ ] El cartel de activar sonido: ⬜ apareció y se fue con un click · ⬜ no
      apareció (ya habías tocado la página) · ⬜ quedó trabado
- [ ] Con el panel cerrado, ¿vuelve el audio por Python? ⬜ sí · ⬜ no
- [ ] Por voz, ¿el foco se queda en el juego? ⬜ sí · ⬜ salta a la consola
- **Ventaja de tener el audio en el browser:** se le puede mandar a un
  dispositivo distinto del juego, y el volumen se regula aparte.

### 24. Regenerar los dos retratos que quedaron con defectos

**Pendiente desde el 22/09**, los prompts ya están corregidos y pusheados:

- **`comunicaciones.png` (Nima)** — salió con **ojos normales y orejas
  puntiagudas**, o sea que lee como vulcana. Los ojos completamente negros son
  el rasgo betazoide y se perdieron.
- **`defensa.png` (Zheva)** — salió con la **variante invertida del uniforme**
  (hombros de color, pecho negro). Es la única del plantel así y se nota al
  ponerlas juntas.

**Pasos:**
1. `del images\oficiales\comunicaciones.png images\oficiales\defensa.png`
2. `python scripts\generar_retratos.py` — regenera sólo esas dos, las otras
   cinco no se tocan
3. Pusheá y avisame, que las miro

- [ ] Nima: ⬜ ojos negros y orejas redondas · ⬜ sigue igual
- [ ] Zheva: ⬜ uniforme como el resto · ⬜ sigue invertido

---

## 🟢 Prioridad BAJA — exploratorio, para cuando haya tiempo

### 11. ¿Se pueden asignar hotkeys a Yellow Alert e Intercept Target?

En **Options → Hotkeys** del juego, fijarse si aparecen como asignables.

- [ ] Yellow Alert: ⬜ se puede · ⬜ no aparece
- [ ] Intercept Target: ⬜ se puede · ⬜ no aparece

> Si se pueden, salen de `NO_SOPORTADO` y pasan a ser comandos normales.
> Intercept Target sería **"andá hacia esa nave"** de verdad.

### 12. ¿Hace falta que el juego tenga el foco?

Probar mandar un comando con el juego **de fondo** (consola al frente).

- [ ] **Resultado:** ⬜ funciona sin foco · ⬜ necesita foco sí o sí
- Notas:

### ~~14. F12 no colisiona con el juego~~

- [x] **RESOLVED in practice (17/09):** ~8 voice commands in a row holding
      F12, with no odd effect in the game.

---

## Resumen de la sesión

- **Fecha:**
- **Pruebas completadas:** ____ / 24 (+ 4b)
- **Hallazgos principales:**
- **Qué romper/arreglar primero la próxima vez:**
