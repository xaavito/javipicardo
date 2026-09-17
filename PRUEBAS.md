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

### 18. La pausa interna de pydirectinput (`PAUSE = 0`) — el último ahorro grande

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

- [x] **18/09, steps 1-3:** no key dropped over 3 speed cycles, and the
      measurements match the prediction: **0.43s** for one key (was 0.76s),
      **0.65-0.69s** for "media máquina" (was 1.88s), **0.86-0.89s** for
      "alto total", which is 8 keys.
- [ ] **Steps 4 and 5 still pending, and they are the fragile ones:**
      "alpha strike" (`shift`+`z`) and "ataquen con todo" (ECM **and** alpha
      strike). A modifier held across a press is the case most likely to be
      lost with no pause at all.
- [ ] Two more cycles of step 3, to get to the 5 asked for.
- ⚠️ If any key gets dropped: set `PAUSA_INTERNA_PYDIRECTINPUT = 0.02` in
  `fase1_text_commands.py`, retest, then `0.05`. If it still drops, put it
  back to `0.1` and re-run `calibrar_latencia.py`.

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

**Status (18/09):** the key reaches the game (`-> Tecla: divide`) but nothing
visible happens and nothing appears selected. **The manual explains why it can
look like that** (SFCfullMan pages 102 and 140), so the steps below follow
from it rather than guessing:

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
5. If the button never lights up, check Options → Hotkeys for what `Numpad /`
   is actually bound to in this edition.

- [ ] Erratic: ⬜ the MFD button lights up · ⬜ nothing at all
- [ ] Does saying it twice turn it off? ⬜ yes, it toggles · ⬜ no, it stays on

### 4b. Orbit Target: los manuales dicen teclas distintas

**Why it matters:** `SFCfullMan` p.159 says Orbit Target is Numpad **`–`**,
while `SFCquick` p.24 says Numpad **`.`**. Both keys exist on the numpad, so
it is not an obvious typo — and "orbitar" has never been confirmed to work in
the game. We may have been sending the wrong key from the start.

**How to test it:**
1. "objetivo más cercano" to have a target.
2. "orbitar" → does the ship circle it? (currently sends `subtract`)
3. If nothing happens: set `TECLA_ORBITAR = "decimal"` in
   `fase1_text_commands.py` and repeat step 2.
4. Whichever of the two works, tell me and it gets written into
   `docs/hotkeys_sfc2.md` as the confirmed one.

- [ ] `subtract` (Numpad `–`): ⬜ orbits · ⬜ nothing
- [ ] `decimal` (Numpad `.`): ⬜ orbits · ⬜ nothing
- [ ] Follow (`Numpad *`), for the record: ⬜ turns and chases · ⬜ nothing
- Notas:

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

### 15. Speed by explicit percentage

**Why it matters:** "velocidad al 70 por ciento" was parsed but sent no key at
all, so the order was silently dropped. It now rounds to the closest of the 5
levels (70% -> level 3, ~75%). Rounding is all we can do before Fase 3, so
what needs checking is whether it feels right while playing.

**How to test it:** say each phrase and watch the HUD.

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

### 19. Palabra suelta ambigua: que no adivine

**Why it matters:** on 18/09 the STT clipped "media máquina" down to
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

- [ ] **Result:** ⬜ explains and does nothing · ⬜ still fires something
- [ ] Any other fragment the STT produces often → tell me and it goes in
      `FRASES_AMBIGUAS`
- Notes:

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
- **Pruebas completadas:** ____ / 19 (+ 4b)
- **Hallazgos principales:**
- **Qué romper/arreglar primero la próxima vez:**
