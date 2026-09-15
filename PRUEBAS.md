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

### 2. Calibrar las pausas (el mayor ahorro de latencia disponible)

**Por qué importa:** hoy se pierden ~1.75s por comando en pausas fijas que
**nunca se midieron** (se eligieron conservadoras en la Fase 0). El ahorro
estimado es de **más de 1 segundo por comando**.

**Cómo probarlo:**
```
python calibrar_latencia.py
```
Sigue las instrucciones: manda teclas y pregunta si la nave reaccionó.

- [ ] **Resultado:** `PAUSA_POST_ENFOQUE` = ______ · `PAUSA_ENTRE_TECLAS` = ______
- [ ] Valores aplicados en `fase1_text_commands.py`
- Notas:

### 3. ¿Se arregló el delay del primer comando?

**Qué se cambió:** cliente de OpenAI cacheado, micrófono y ventana
precalentados al arrancar (`precalentar_todo()`).

**Cómo probarlo:** arrancar `fase2_voice_commands.py` y dar 3-4 comandos
seguidos, mirando la línea `[tiempos]` de cada uno.

- [ ] **Resultado:** 1er comando: ______s · 2do: ______s · 3ro: ______s
- [ ] ¿Sigue habiendo diferencia notable con el primero? ⬜ sí · ⬜ no
- Notas:

---

## 🟡 Prioridad MEDIA — funcionalidad nueva sin validar

### 4. Teclas de numpad

**Por qué importa:** son las que más riesgo tienen de no pasar por
`pydirectinput`. Si fallan, caen "orbitar", "evasivas" y los dos combos.

| Comando | Tecla | ¿Funciona? |
|---|---|---|
| "orbitar" | `Numpad -` | [ ] |
| "maniobras evasivas" | `Numpad /` | [ ] |
| "seguir a esa nave" | `Numpad *` | [ ] |

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
| "siguiente enemigo" (solo enemigos) | `y` | [ ] |
| "enemigo anterior" | `shift+y` | [ ] |
| "objetivo anterior" | `shift+t` | [ ] |
| "deseleccionar objetivo" | `\` | [ ] |

- Notas:

### 9. STT nuevo: ¿mejoró precisión y latencia?

**Qué se cambió:** `whisper-1` → `gpt-4o-mini-transcribe`, + vocabulario del
juego vía `prompt`, + `temperature=0`.

**Cómo probarlo:** decir estas frases y ver si las transcribe bien:

| Frase dicha | ¿Transcribió bien? |
|---|---|
| "media máquina" | [ ] |
| "alerta roja" | [ ] |
| "alpha strike" | [ ] |
| "escudos al máximo" | [ ] |
| "maniobras evasivas" | [ ] |

- [ ] **Latencia STT promedio:** ______s (de la línea `[tiempos]`)
- Notas (palabras que sigue transcribiendo mal → agregar a
  `PROMPT_VOCABULARIO`):

### 10. Mensajes de comandos no soportados

- [ ] "alerta amarilla" → explica que existe en el HUD pero sin tecla
- [ ] "interceptar" → explica que es del Helm MFD y sugiere alternativas
- [ ] Confirmar que **no** tarda (no debería llamar al LLM)
- Notas:

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

### 13. Comparar STT local vs. API

Cambiar `STT_BACKEND = "local"` y `MODEL_SIZE = "tiny"` en
`fase2_voice_commands.py`.

- [ ] Latencia con `tiny` local: ______s (vs. ______s de la API)
- [ ] ¿La precisión alcanza para nuestro vocabulario? ⬜ sí · ⬜ no
- Notas:

### 14. F12 no colisiona con el juego

- [ ] Confirmar que mantener `F12` no dispara ninguna acción en el juego
- Notas:

---

## Resumen de la sesión

- **Fecha:**
- **Pruebas completadas:** ____ / 14
- **Hallazgos principales:**
- **Qué romper/arreglar primero la próxima vez:**
