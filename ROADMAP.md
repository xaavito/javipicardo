# Roadmap / Bitácora — SFC Voice Commander

Documento vivo para ir marcando qué se probó, qué funcionó, qué no, y las próximas
acciones. Se actualiza a medida que avanzamos. Ver `README.md` para la teoría y
arquitectura completa, y `docs/hotkeys_sfc2.md` para la lista de hotkeys del juego.

✅ Para **lo que hay que probar en la máquina Windows**, ver **`PRUEBAS.md`**:
checklist numerado y priorizado, con lugar para anotar cada medición. Ese es el
documento de trabajo del día; acá en el ROADMAP quedan los resultados una vez
confirmados.

💡 Para **ideas a futuro todavía no comprometidas** (ej. encadenar varios comandos
en una sola orden), ver **`WISHLIST.md`**. Este ROADMAP es lo que se está
ejecutando; la wishlist es el "algún día".

📋 Para el **resumen ejecutivo de las charlas de feedback con Pato** (quien lidera
el proyecto; charlas estimadas semanalmente los viernes), ver
**`docs/feedback_sesiones.md`** — una tabla por sesión con qué se sugirió, si ya
lo teníamos y qué se hizo, lista para copiar/pegar en Slack. Acá en el ROADMAP
queda el detalle técnico largo de cada decisión.

Convención de estado: `[ ]` pendiente, `[~]` en progreso / parcialmente validado,
`[x]` confirmado funcionando, `[!]` bloqueado / falló, necesita revisión.

---

## Fase 0 — Validar inyección de teclado (SendInput / pydirectinput)

**Objetivo:** confirmar que se puede simular una tecla (ej. `S`) contra el juego
real corriendo en Windows, y que el juego la recibe igual que si fuera un teclado
físico. Esto es un bloqueante: si esto no funciona con este método, hay que buscar
una alternativa antes de construir cualquier otra cosa.

### Checklist

- [x] Confirmar en la máquina Windows: ¿el juego instalado es **SFC1** o **SFC2**?
      → Confirmado: **Star Trek: Starfleet Command Gold Edition** (SFC1 + expansiones
      Empires at War / Neutral Zone integradas en una edición). Usar como referencia
      principal `docs/hotkeys_sfc2.md`, ahora basado directamente en los manuales
      oficiales de la Gold Edition (`SFCfullMan.pdf`, `Supplemental Manual.pdf`,
      `SFCquick.pdf`), provistos por el usuario.
- [x] Confirmar si el juego corre en **modo ventana** o **pantalla completa exclusiva**
      → **Confirmado: pantalla completa exclusiva.** Se probó Alt+Tab (Opción 2):
      hay demora y cambio de resolución al alternar, lo cual confirma fullscreen
      exclusive real (no windowed/borderless). Este es el escenario más delicado
      para `SendInput`/`pydirectinput` — no se sabe aún si va a funcionar sin
      problema o no, hay que probarlo en la Fase 0.
- [x] **Encontrado el mecanismo oficial para forzar modo ventana** — el
      `Supplemental Manual.pdf` documenta el archivo `SFC.INI` (en la carpeta de
      instalación del juego), sección `[3D]`:
      ```ini
      [3D]
      windowed=0   ; poner en 1 para modo ventana
      lowres=3     ; 0:800x600 1:640x480 2:raro 3:1024x768 4:1200x800
      ```
      **Importante:** `windowed=1` sólo funciona si `lowres` da una resolución
      MENOR a la del escritorio de Windows. Ver detalle completo en
      `docs/hotkeys_sfc2.md` (sección "Configuración de video/ventana").
- [x] Aplicar el cambio en `SFC.INI`:
  - [x] Ubicado el archivo, backup hecho
  - [!] Se probaron varias combinaciones de `windowed=1` + `lowres` (0, 3, y
        destildando 640x480) — el juego SÍ abría en ventana, pero quedaba muy
        chico (~1/4 de pantalla), sin bordes visibles, y la interfaz cortada (no
        se veía la selección de razas). Ajustar solo el `.ini` no fue suficiente,
        el renderizado quedaba mal dimensionado con hardware/drivers modernos.
  - Conclusión: el `.ini` por sí solo no alcanzó, se necesitó DxWnd (ver abajo).
- [x] **Resuelto con DxWnd.** Configuración validada y funcionando (juego abre en
      ventana correcta, se ve completa la interfaz, se llega a selección de razas):
  1. Revertir `SFC.INI` a `windowed=0` (el modo ventana lo maneja DxWnd, no el .ini)
  2. Descargar DxWnd (https://dxwnd.org / repo en SourceForge), descomprimir
  3. Ejecutar `dxwnd.exe` como Administrador (clic derecho → "Ejecutar como
     administrador") — **imprescindible**, sin esto tira error 740 "Create Process"
     (falta de elevación de permisos) al intentar lanzar el juego
  4. Menú **Edit → Add** para crear un nuevo perfil
  5. Configurar **Name**, y tanto **Path** como **Launch** apuntando directo al
     ejecutable principal del juego
  6. Pestaña **Main**: tildar **"keep aspect ratio"** y **"Run in Window"**
  7. Pestaña **Video**: **Window Size & Position → Locked Size** (evita crashes al
     arrastrar/redimensionar la ventana), y configurar **Initial Resolution** /
     **Limit Resolution** con los valores deseados (ej. 1024x768)
  8. Guardar el perfil (OK), y lanzar el juego con **doble click sobre la entrada
     del perfil en la lista de DxWnd** (nunca desde el ícono/acceso directo normal
     del juego)
  - Nota: la pestaña "Hooking" no está presente en esta versión de DxWnd usada —
    no hizo falta para que funcione.
  - Nota: **DxWnd tiene que ejecutarse siempre como Administrador** para lanzar el
    juego sin el error 740. Si se quiere evitar tener que elegir "ejecutar como
    admin" cada vez, se puede fijar esto en Propiedades → Compatibilidad del
    `dxwnd.exe` de forma permanente.
- [x] Instalar Python en la máquina Windows → **Python 3.14** instalado
  - [!] Problema encontrado: tras agregar Python al PATH, `pip` funcionaba pero
        `python`/`py` no se reconocían (`where python` no devolvía nada). Causa:
        al PATH le faltaba la carpeta raíz de la instalación (donde vive
        `python.exe`), solo tenía la de `Scripts` (donde vive `pip.exe`).
        Solución: ubicar la ruta real vía `pip --version` (muestra la ruta
        completa, ej. `...\Python314\Lib\site-packages\pip`), agregar la carpeta
        raíz `...\Python314\` a la variable de entorno **Path** (además de la de
        `Scripts`, que ya estaba), y abrir una consola nueva para que tome el
        cambio. Resuelto.
- [x] Instalar dependencia: `pip install pydirectinput` → instalado sin problemas
      en Python 3.14 (no hubo incompatibilidad pese a ser una versión muy reciente)
- [x] Escribir script mínimo `fase0_test_key.py` → **listo** en
      `scripts/fase0_test_key.py` (manda `S` x3, espera, manda `A` x3, con cuenta
      regresiva previa para dar tiempo a enfocar la ventana del juego)
- [x] Copiar `scripts/fase0_test_key.py` a la máquina Windows
- [x] Ejecutar el script con el juego abierto (vía DxWnd, en ventana) y en una
      misión/escenario donde la nave pueda moverse
- [x] **Confirmado visualmente: la velocidad de la nave SÍ cambia al correr el
      script.** ✅ Bloqueante principal de la Fase 0 resuelto.
- [x] Confirmar si hace falta correr el script como Administrador → **SÍ, hace
      falta.** Primer intento sin permisos elevados no tuvo ningún efecto (no
      aceleró ni frenó). Al correr la consola de Python **como Administrador**
      (mismo nivel de privilegios que DxWnd/el juego, evitando el bloqueo UIPI de
      Windows que impide que procesos sin privilegios manden input a procesos con
      privilegios elevados), funcionó correctamente.
- [ ] Confirmar que funciona también si la ventana del juego **no tiene foco** en el
      momento del envío (o documentar que sí hace falta foco, y que hay que
      auto-enfocar la ventana antes de cada comando) — pendiente, no bloqueante
      para seguir avanzando a la Fase 1.

### Resultado (completar después de probar)
- **Sub-hito 1 (modo ventana) — RESUELTO:** el juego corre en ventana correctamente
  vía DxWnd (config detallada arriba).
- **Sub-hito 2 (inyección de teclado con pydirectinput) — RESUELTO ✅:** el script
  `fase0_test_key.py` mandó `S`/`A` exitosamente y la nave reaccionó (aceleró y
  frenó), corriendo la consola de Python **como Administrador**.
- **Fase 0 completa.** Bloqueante principal del proyecto resuelto — la arquitectura
  de inyección de teclado (Python + pydirectinput + consola como Administrador +
  juego vía DxWnd en modo ventana) está validada extremo a extremo.
- Configuración final que funcionó: Python 3.14 + `pydirectinput`, consola
  ejecutada como Administrador, juego abierto desde el perfil de DxWnd (con
  "Run in Window" + "keep aspect ratio" + "Locked Size").
- Nota para las próximas fases: cualquier script que mande teclas al juego va a
  necesitar correrse desde una consola/proceso con privilegios de Administrador.

---

## Fase 1 — Comandos por texto (sin voz, sin red)

**Objetivo:** validar el mapeo "intención → teclas" con un input simple de texto,
sin la complejidad de STT ni de micrófono. Depende de que la Fase 0 esté resuelta.

### Checklist
- [x] Armar diccionario de sinónimos inicial (velocidad, alerta, disparo, escudos,
      camuflaje, deep scan) → **listo** en `scripts/fase1_text_commands.py`
      (`SPEED_WORDS`, `STEPS_VELOCIDAD`, `ALERT_WORDS`, `FIRE_WORDS`,
      `ALPHA_STRIKE_WORDS`, `SHIELD_MAX_WORDS`, `CLOAK_WORDS`, `DEEPSCAN_WORDS`)
- [x] Armar función `parsear_comando(texto)` → implementada, con normalización
      (minúsculas + sin tildes) y matching por límites de palabra (`contiene_frase`)
      para evitar falsos positivos (ej. "parar" adentro de "disparar" — bug
      encontrado y corregido durante pruebas locales antes de pasar el script)
- [x] Armar función `ejecutar_accion(accion)` → implementada, soporta teclas
      simples, combos (ej. Shift+Z para Alpha Strike), y set_speed con cantidad
      aproximada de pasos S/A por nivel (heurística temporal, ver Fase 3)
- [x] Loop simple: `input()` en consola → parsear → ejecutar → repetir →
      implementado en `main()`, con salida por "salir"/"exit"/"quit"
- [x] Validación de lógica del parser hecha localmente (sin el juego, con
      `pydirectinput` mockeado) — confirmado que reconoce correctamente todos los
      comandos de prueba (alerta roja, disparar, niveles de velocidad, alpha
      strike, escudos, % explícito, comando desconocido)
- [x] **Problema encontrado y resuelto: foco de ventana.** Al escribir el comando
      en la consola, la CONSOLA tiene el foco (no el juego) en el momento de
      ejecutar la acción — con el flujo original ("click manual en el juego antes
      de correr"), esto no aplica al loop de texto porque el usuario necesita
      tipear en la consola constantemente. Solución implementada: se agregó la
      dependencia `pygetwindow` y las funciones `encontrar_ventana_juego()` /
      `enfocar_ventana_juego()`, que buscan la ventana del juego por su título
      (lista configurable en `WINDOW_TITLE_KEYWORDS`) y la traen al frente
      automáticamente ANTES de mandar cualquier tecla. `ejecutar_accion()` ahora
      llama a esto antes de cualquier `key`/`key_combo`/`set_speed`. Validado
      localmente con un mock de `pygetwindow` — funciona como se espera.
      Este mismo mecanismo es el que se va a reusar en la Fase 2 (voz), donde el
      problema de foco es aún más relevante (no hay "tipear", hay que hablar).
  - **Mejora adicional: ida y vuelta automática de foco.** Se agregó también
    `enfocar_consola()` (usando `ctypes` + `GetConsoleWindow`/`SetForegroundWindow`
    de la API de Windows, sin depender de buscar por título ya que el título de
    la consola puede variar). `ejecutar_accion()` ahora hace: 1) enfocar el
    juego, 2) mandar la(s) tecla(s), 3) volver el foco a la consola — todo
    automático, sin que el usuario tenga que hacer Alt+Tab ni click manual en
    ningún momento del ciclo. Validado localmente con mocks de `pygetwindow` y
    `ctypes.windll` — funciona como se espera.
  - **Bug real encontrado en la máquina Windows y resuelto:** al probar en vivo,
    el auto-enfoque SÍ cambiaba visualmente el foco (confirmado con
    `scripts/probar_activar.py`: Windows marcaba "Starfleet Command" como
    ventana activa), pero la tecla igual no llegaba a afectar al juego.
    Diagnóstico con `scripts/probar_tecla_con_foco.py`: la causa era **timing**
    — con una pausa corta (0.15s) después de enfocar, el juego no llegaba a
    "asentar" el cambio de foco antes de recibir la tecla. Con una pausa más
    larga (1-2s) sí funcionó, confirmado en vivo (la velocidad subió
    correctamente varias veces). **Solución aplicada:** se reemplazó
    `pygetwindow.activate()` por `BringWindowToTop` + `SetForegroundWindow`
    directo vía `ctypes` (mismo mecanismo confirmado en las pruebas), y se
    agregó la constante `PAUSA_POST_ENFOQUE = 1.0` (segundo) después de
    enfocar la ventana, antes de mandar la primera tecla. Título real
    confirmado de la ventana del juego: **"Starfleet Command"** (coincide con
    las `WINDOW_TITLE_KEYWORDS` ya configuradas, no hizo falta ajustarlas).
  - Nota: esta pausa de 1 segundo por comando es una latencia a tener en cuenta
    para la Fase 2 (voz) — sumada a la latencia de STT, el delay total percibido
    puede ser mayor a lo estimado originalmente en el README. A revisar si se
    puede reducir el valor de `PAUSA_POST_ENFOQUE` con más pruebas (quizás 0.5s
    alcance, no se probó ese valor intermedio todavía).
  - Scripts de diagnóstico creados durante esta investigación (quedan en
    `scripts/` como referencia): `probar_activar.py`, `probar_tecla_con_foco.py`.
  - **Ajuste posterior:** se reemplazó `WINDOW_TITLE_KEYWORDS` (matching laxo por
    substring) como criterio principal por una nueva constante
    `WINDOW_TITLE_EXACTO = "Starfleet Command"` (el título real confirmado),
    usando `pygetwindow.getWindowsWithTitle()` como primer intento — más preciso,
    evita falsos positivos con otras ventanas que puedan contener palabras
    parecidas en el título (ej. una pestaña de navegador). `WINDOW_TITLE_KEYWORDS`
    se mantiene solo como respaldo, si la búsqueda por título exacto no
    encuentra nada. Validado con test que confirma que ignora correctamente una
    ventana señuelo con "Starfleet Command" en el título pero distinto al
    exacto.
  - **[!] Regresión encontrada:** tras el ajuste anterior, en la máquina Windows
    dejó de funcionar (aparece "Tecla: X" en consola pero el juego no
    reacciona), pese a que localmente los tests con mocks pasaban bien.
    Sospecha principal: `pygetwindow.getWindowsWithTitle()` puede ser sensible
    a mayúsculas/espacios y no estar encontrando la ventana en la práctica (a
    diferencia del mock). Se revirtió el método de búsqueda para volver a
    recorrer `getAllWindows()` a mano (como en la versión que sí funcionaba),
    pero ahora comparando el título exacto en minúsculas + strip (más
    tolerante), con fallback a las palabras clave si no encuentra nada. Se
    agregaron **2 líneas de debug siempre visibles** en `enfocar_ventana_juego()`:
    una que muestra qué ventana encontró (título + hwnd) antes de intentar
    enfocarla, y otra que muestra cuál ventana quedó realmente activa según
    Windows después de la pausa. Pendiente: volver a probar en vivo y revisar
    la salida de estas 2 líneas de debug para confirmar si el problema es
    "no encuentra la ventana" o "la encuentra pero el enfoque real sigue sin
    surtir efecto" (este último caso apuntaría a que el problema no es de
    búsqueda de ventana, sino que cambió algo más entre esta versión y la
    anterior que sí funcionaba).
  - **[x] CAUSA REAL ENCONTRADA Y CORREGIDA:** con el debug agregado, se
    confirmó que el foco SÍ quedaba correctamente en "Starfleet Command"
    (ambas líneas de debug coincidían) — el problema no era de foco. La causa
    real: **las teclas en los diccionarios estaban en MAYÚSCULA** (`"R"` para
    alerta roja, `"A"`/`"S"` en `STEPS_VELOCIDAD` para velocidad), mientras
    que `fase0_test_key.py` (que sí funcionaba) siempre usó minúsculas
    (`'s'`, `'a'`). `pydirectinput`/`pyautogui` esperan los nombres de tecla
    de letras en minúscula en su mapeo interno — mandar `'R'` en vez de `'r'`
    no tira error pero tampoco llega a afectar al juego, lo cual explica
    perfectamente el síntoma ("Tecla: R" se imprimía bien por nuestro propio
    `print()`, pero `pydirectinput.press('R')` no hacía nada real).
    **Corregido:** `ALERT_WORDS` (`"R"` → `"r"`) y `STEPS_VELOCIDAD`
    (`"A"`/`"S"` → `"a"`/`"s"`) actualizados a minúsculas. El resto de las
    teclas del diccionario (`z`, `k`, `x`, `i`) ya estaban correctamente en
    minúscula desde el principio, por eso "disparar" en las pruebas de
    `probar_tecla_con_foco.py` sí había funcionado antes (esa prueba solo usó
    `'s'` en minúscula). Pendiente: volver a probar en vivo "alerta roja" y
    los niveles de velocidad con esta corrección.
- [x] Instalar la dependencia nueva en la máquina Windows: `pip install pygetwindow`
- [x] Confirmar en vivo cuál es el título real de la ventana del juego →
      confirmado: **"Starfleet Command"** (ver detalle arriba)
- [x] **Probado en vivo con éxito: "alerta roja" activó la alerta roja en el
      juego.** ✅ Confirmado también que el auto-enfoque de ventana (ida y
      vuelta juego↔consola) funciona sin necesitar click manual.
- [x] Confirmado que el comando de texto dispara la tecla correcta y el juego
      reacciona en vivo.
- [ ] Probar el resto de comandos para cobertura completa (no bloqueante, la
      lógica ya es la misma que la validada con "alerta roja"):
  - "disparar"
  - "media máquina" / "cuarto de máquina" / "alto total"
  - "escudos al máximo"
  - "fuego a discreción" (alpha strike)

### Resultado (completar después de probar)
- **Fase 1 completa y funcionando en vivo.** ✅
- Bugs encontrados y resueltos en el camino:
  1. Auto-enfoque con `pygetwindow.activate()` + pausa corta no alcanzaba —
     resuelto con `BringWindowToTop`+`SetForegroundWindow` (ctypes) + pausa de
     1 segundo (`PAUSA_POST_ENFOQUE`).
  2. Búsqueda por título exacto vía `getWindowsWithTitle()` dejó de encontrar
     la ventana en la práctica — resuelto volviendo a recorrer
     `getAllWindows()` a mano, comparando título en minúsculas + strip.
  3. **Bug principal:** teclas en mayúscula (`"R"`, `"A"`, `"S"`) en
     `ALERT_WORDS`/`STEPS_VELOCIDAD` no eran reconocidas por
     `pydirectinput` (que espera minúsculas) — corregido a `"r"`, `"a"`, `"s"`.
- Notas: mantener siempre las teclas de letras en minúscula en cualquier
  diccionario nuevo que se agregue a futuro (Fase 5 y en adelante), para no
  repetir el bug #3.

---

## Fase 2 — Voz (STT local u OpenAI)

**Objetivo:** reemplazar el `input()` de texto por micrófono + STT,
alimentando el mismo parser de la Fase 1. Soporta dos backends intercambiables
(ver actualización más abajo): local (faster-whisper) o nube (API de OpenAI).

### 🆕 Actualización: acceso a API token de OpenAI
El usuario consiguió acceso a la API de OpenAI. Esto habilitó dos mejoras
independientes, ambas implementadas como backends configurables (no
reemplazan lo local, se puede volver atrás cambiando una constante):

- [x] **`scripts/stt_openai.py`** (nuevo): transcribe usando la API de Whisper
      de OpenAI (`whisper-1`) en vez de `faster-whisper` local. Arma un WAV en
      memoria (sin guardar nada a disco) con `soundfile` y lo manda a la API.
      Se activa seteando `STT_BACKEND = "openai"` en
      `fase2_voice_commands.py` (por defecto quedó en `"openai"`; cambiar a
      `"local"` para volver a faster-whisper).
- [x] **`llm_fallback.py` actualizado** para soportar backend `"openai"`
      además de `"ollama"` (constante `LLM_BACKEND`, por defecto en
      `"openai"` ahora). Usa `gpt-4o-mini` por defecto (rápido y barato,
      de sobra para esta tarea de clasificación). Ventaja extra sobre Ollama:
      la API de OpenAI soporta `response_format={"type": "json_object"}`,
      que fuerza a que la respuesta sea SIEMPRE JSON válido (Ollama no
      garantiza esto tan estrictamente).
- [x] **Configuración de API key documentada** (en `stt_openai.py`, reusada
      por `llm_fallback.py` ya que es el mismo servicio): variable de entorno
      `OPENAI_API_KEY`, nunca hardcodeada en el código. Instrucciones para
      Windows (PowerShell, CMD, o de forma permanente vía Variables de
      entorno del sistema) incluidas en el docstring del archivo.
- [x] Validado localmente con mocks del SDK de `openai` (para STT y para LLM
      por separado) — confirmado que arma bien el WAV en memoria, llama a la
      API con los parámetros esperados, y que el caso de audio vacío no
      genera ninguna llamada innecesaria a la API (ahorra costo).
- [ ] Confirmar en la máquina Windows: instalar `pip install openai
      soundfile`, configurar `OPENAI_API_KEY`, y probar en vivo si el
      reconocimiento de voz efectivamente se siente más rápido que con
      Whisper local (que fue la motivación original de este cambio — ver
      pregunta del usuario sobre latencia).
- [ ] Comparar en la práctica: latencia con STT local (`base`) vs. STT OpenAI,
      con la misma conexión a internet real de la máquina Windows.

### Checklist
- [x] Decidir modo de activación → **push-to-talk** (tecla mantenida), por ser
      más simple y de menor latencia que VAD (ver README)
- [x] **Colisión de tecla detectada y corregida:** la primera versión usaba
      `F9` por defecto, pero `docs/hotkeys_sfc2.md` confirma que F9 (y F10/F11)
      están mapeadas en el juego a HUD Minimal/Normal/Maximum Information — como
      el foco queda en la ventana del juego mientras se mantiene apretada la
      tecla de push-to-talk, esto podría hacer que el juego cambiara de HUD sin
      querer cada vez que se habla un comando. Cambiado a **`F12`**, que no
      aparece en ninguna parte de la lista completa de hotkeys de la Gold
      Edition. Pendiente confirmar en el juego real (Options → Hotkeys, o
      probando en una misión) que F12 efectivamente no dispara nada.
- [x] Script que capture audio del mic, lo pase a Whisper, y mande el texto
      resultante al `parsear_comando()` de la Fase 1 → **listo** en
      `scripts/fase2_voice_commands.py`. Reusa TODA la lógica ya validada de
      `fase1_text_commands.py` (parser, ejecutor, manejo de foco de ventana)
      importándolo como módulo, en vez de duplicar código.
- [x] Validación de lógica hecha localmente (sin mic/juego reales, con mocks de
      `pydirectinput`, `pygetwindow`, `ctypes.windll`, `sounddevice`, `keyboard`
      y `faster_whisper`) — confirmado que el flujo completo (transcribir →
      parsear → ejecutar) funciona sin errores de sintaxis/import, y que el
      parser sigue devolviendo teclas en minúscula correctamente (no se
      reintrodujo el bug de mayúsculas de la Fase 1).
- [ ] Confirmar en el juego real que **F12** no dispara ninguna acción (probar
      en una misión: apretarla sola, sin push-to-talk activo, y ver que no
      pase nada raro en el juego) — si llegara a colisionar con algo no
      documentado, cambiar `PUSH_TO_TALK_KEY` a `"insert"` o `"num enter"`
- [x] **Primera prueba en vivo con audio real: modelo cargó y funcionó.**
      Feedback del usuario: (1) la latencia se siente un poco más alta de lo
      deseado, (2) faltaban comandos de seguimiento de nave/amenaza, (3)
      confirmar que el foco vuelve a la consola tras ejecutar la acción.
- [x] **Ajuste de latencia (primer intento):** cambiado `MODEL_SIZE` de
      `"small"` a `"base"` (~145MB vs ~480MB) — mejor equilibrio
      velocidad/precisión para comandos cortos de vocabulario acotado. A
      confirmar en la próxima prueba si la latencia mejora sin perder
      demasiada precisión de transcripción. Si hiciera falta más velocidad
      aún, la siguiente opción sería `"tiny"`.
- [x] **Nuevos comandos agregados** en `fase1_text_commands.py` (heredados
      automáticamente por la Fase 2, ya que reusa el mismo parser):
  - `FOLLOW_WORDS` → tecla `multiply` (Numpad `*`, Follow Target): "seguir a
    esa nave", "seguir a la amenaza", "seguir al objetivo", etc. El manual no
    distingue "nave" de "amenaza" — Follow Target sigue al target que esté
    seleccionado en ese momento.
  - `NEXT_TARGET_WORDS` → tecla `t` (Cycle Target): "siguiente objetivo",
    "cambiar de blanco", útil para cambiar el target antes de decir "seguir
    a esa nave" si no es el que se quiere seguir.
  - `NEAREST_ENEMY_WORDS` → tecla `` ` `` (Target Nearest Enemy): "objetivo
    más cercano", "enemigo más cercano".
  - Validado localmente con mocks — los 3 nuevos comandos parsean
    correctamente a la tecla esperada.
- [x] **Foco de vuelta a consola tras ejecutar la acción: ya estaba
      implementado** desde la Fase 1 (`enfocar_consola()` se llama al final de
      `ejecutar_accion()`, reusado tal cual por la Fase 2). La librería
      `keyboard` (usada para detectar F12) hace un hook global de teclado que
      no depende del foco de ventana, así que este comportamiento debería
      funcionar igual con voz que con texto. A confirmar visualmente en la
      próxima prueba en vivo si se percibe correctamente.
- [ ] **Pendiente de revisar (no aplicado todavía):** bajar `PAUSA_POST_ENFOQUE`
      (actualmente 1.0s, definida en `fase1_text_commands.py`) es otra fuente
      de latencia que se suma en cada comando. No se tocó todavía para no
      arriesgar reintroducir el bug de "tecla no llega al juego" sin volver a
      probar con cuidado — a evaluar bajarla a `0.5` con pruebas controladas.
- [x] **Comando de ayuda agregado:** decir/escribir "ayuda", "qué comandos hay",
      etc. (`HELP_WORDS`) ahora imprime en consola la lista completa de
      comandos disponibles, organizada por categoría (velocidad, armas,
      defensa, combos, otros), vía la nueva función `listar_comandos()`.
- [x] **Mecanismo de COMBOS agregado** (una sola frase → varias teclas en
      secuencia): nuevo diccionario `COMBOS` en `fase1_text_commands.py`, con
      una nueva función auxiliar `_presionar_paso()` que soporta teclas
      simples, combos con modificador (`"shift+z"`), y repetición
      (`("s", 8)`). El foco de ventana se hace una sola vez para todo el
      combo (no una vez por paso), para no repetir la pausa de 1s
      innecesariamente. Combos iniciales cargados:
  - **"ataquen con todo"** → Max ECM (`f`) + Alpha Strike (`shift+z`).
  - **"aléjense a máxima velocidad"** → acelerar al 100% (8x `s`). Nota: el
    juego no permite controlar el RUMBO por teclado (se hace con mouse/
    waypoints, fuera del alcance de este proyecto por ahora), así que este
    combo ignora la parte de "girar y huir" y solo acelera al máximo.
  - Agregar más combos a futuro es simple: una entrada nueva en `COMBOS` con
    `"palabras"`, `"pasos"` y `"descripcion"`.
- [x] Validado localmente con mocks: los combos ejecutan la secuencia de
      teclas esperada, "ayuda" imprime el listado completo, y se confirmó que
      no colisionan con los comandos individuales ya existentes (ej.
      "disparar" y "fuego a discreción" siguen funcionando igual que antes).
- [ ] Conseguir/instalar micrófono en la máquina Windows
- [ ] Instalar las dependencias nuevas en la Windows:
      `pip install faster-whisper sounddevice numpy keyboard`
- [ ] Correr el script por primera vez y confirmar que descarga el modelo
      `small` de Whisper sin problemas (requiere internet solo esta vez)
- [ ] Probar en vivo varias frases de voz reales (no solo texto tipeado) y ver
      qué tan bien transcribe Whisper el vocabulario específico ("media máquina",
      "alerta roja", etc.), con el juego abierto vía DxWnd y la consola como
      Administrador (igual que en Fases 0/1)
- [ ] Medir latencia real end-to-end (desde que se suelta la tecla de push-to-talk
      hasta que se ejecuta la acción en el juego) y compararla con lo estimado
      en el README — tener en cuenta que ya sabemos que se suma la
      `PAUSA_POST_ENFOQUE` (1 segundo) de la Fase 1 al tiempo de transcripción

### Resultado (completar después de probar)
- Fecha:
- Latencia medida:
- Precisión de transcripción (aceptable / requiere ajustes):
- Notas:

### Hallazgos de las pruebas en vivo

- **[12/09] "alerta amarilla" no era reconocido.** Reportado en prueba real.
  Causa: **no era un bug de transcripción ni un sinónimo faltante** — el
  comando simplemente **nunca existió** en el parser. `ALERT_WORDS` solo tenía
  Red Alert, con un comentario avisando que el manual de la Gold Edition no
  documenta una tecla de Yellow Alert. La documentación (README) sí prometía
  "alerta roja/amarilla", lo cual era incorrecto y generaba la expectativa.
  - **Solución aplicada:** se agregó el diccionario `NO_SOPORTADO` en
    `fase1_text_commands.py` y una acción nueva `no_soportado`. Ahora, en vez
    de un genérico "comando no reconocido" (que hace pensar que falló el STT o
    que falta un sinónimo), el sistema responde explicando **el motivo real**:
    que el juego no tiene esa tecla, y sugiriendo la alternativa ("alerta
    roja").
  - Se chequea **antes** que `ALERT_WORDS` a propósito: "alerta amarilla"
    contiene "alerta", así que si se evaluara después podría matchear un
    comando de alerta equivocado.
  - **Bonus:** estos comandos **no disparan el fallback del LLM** (el fallback
    solo se activa con `unknown`), así que no se gasta una llamada de API en
    algo que ya sabemos que no se puede ejecutar.
  - También aparecen ahora en el listado de `ayuda`, bajo la sección
    "NO DISPONIBLES (el juego no los soporta)", para que se sepa de antemano.
  - Se corrigió el README, que afirmaba tener "alerta roja/amarilla".
  - [x] **RESUELTA la duda sobre Yellow Alert** (ver relectura del manual más
        abajo): **existe como botón en el HUD** (pág. 101 — sube escudos sin
        armar las armas, a diferencia de Red Alert que hace ambas), pero
        **no tiene tecla asignada**, así que sigue en `NO_SOPORTADO`. El
        mensaje ahora explica esa diferencia funcional.

- **[12/09] Relectura de los manuales buscando "seguir a una nave determinada".**
  Se extrajo el texto de los PDFs (con `pypdf`) para revisar las páginas de
  targeting y maniobras, en vez de quedarnos solo con la lista de hotkeys.
  Hallazgos:
  - **El juego NO permite identificar una nave por nombre** — no existe forma
    de decir "seguí a la Enterprise". Pero **sí hay memoria de targets**
    (teclas `5`-`8` para seleccionar, `CTRL+5`-`8` para guardar, pág. 157),
    que es lo más cercano posible: se cicla hasta la nave deseada, se la
    guarda en una ranura, y después se la puede volver a seleccionar aunque
    se haya cambiado de target mil veces.
  - **Estábamos desaprovechando varios comandos de targeting documentados.**
    Se agregaron al parser: `Y`/`SHIFT+Y` (ciclar **solo enemigos**, mucho más
    útil que `T` que cicla todo, incluidas unidades no hostiles),
    `SHIFT+T` (ciclar hacia atrás) y `\` (deseleccionar).
  - **Maniobras del Helm officer que no teníamos:** `Numpad -` (Orbit Target)
    y `Numpad /` (Erratic Maneuvers, +4 puntos de ECM natural). Son
    especialmente valiosas porque **las pilotea el oficial de timón**, o sea
    que dan control de movimiento SIN depender del mouse — que es justo la
    limitación que bloquea la Fase 6.
  - **Intercept Target existe pero NO tiene hotkey** (pág. 103): es un botón
    del Helm Officer MFD. Se agregó a `NO_SOPORTADO` sugiriendo Follow/Orbit
    como alternativas, para no mapear una tecla inexistente.
  - Validado con mocks: 26 frases parseadas correctamente, sin regresiones en
    los comandos que ya andaban.
  - [ ] **Pendiente de probar en vivo:** confirmar que las teclas de numpad
        (`subtract`/`divide`/`multiply`) y `CTRL+5-8` llegan bien al juego vía
        `pydirectinput`. Confirmar también si desde Options → Hotkeys se
        pueden asignar teclas a Yellow Alert e Intercept Target (si se puede,
        salen de `NO_SOPORTADO` y pasan a ser comandos normales).

- **[12/09] DUDA ABIERTA: ¿"seguir a esa nave" (Follow Target) vira la nave o
  solo sigue con la cámara?** Surgió al preguntarse si el comando realmente
  apunta la nave hacia el objetivo. **El manual no lo aclara.** Se revisaron
  los 3 PDFs completos: `Numpad * Follow Target` aparece **solo** en la tabla
  de hotkeys (pág. 159), sin ninguna descripción en el cuerpo del manual — y
  es la **única** maniobra en esa situación:
  - Orbit Target, Intercept Target y Erratic Maneuvers **sí** están descritas
    (pág. 102-103) **y** aparecen en el Helm Officer MFD.
  - Follow Target **no** está descrita **ni** aparece en el Helm MFD.
  - **A favor de que mueva la nave:** está en el numpad junto a Orbit y
    Erratic, que son inequívocamente maniobras de la nave; las teclas de
    cámara están agrupadas aparte (F1-F5, HOME/END/PGUP/PGDN).
  - **A favor de que sea solo visual:** el juego ya usa "Follow" para cámara
    (`F3 Follow Camera`, `F5 Target Padlock`), y no figura entre las órdenes
    de pilotaje del Helm.
  - **Implicancia para el proyecto:** si resultara ser solo cámara, entonces
    **hoy no tenemos NINGÚN comando por voz que mueva la nave hacia un
    objetivo** (más allá de Orbit). La alternativa real sería Intercept
    Target, que no tiene hotkey pero quizá se le pueda asignar una desde
    Options → Hotkeys.
  - [x] **RESUELTO (13/09) — probado en el juego: Follow Target SÍ VIRA LA
        NAVE hacia el objetivo y lo persigue.** ✅ No es solo cámara.
  - **Implicancias (importantes):**
    - Es el **único comando por teclado que apunta la nave a un objetivo**,
      sin depender del mouse sobre la vista táctica.
    - **Valida el paso de rumbo de los combos** `ir_al_mas_cercano` e
      `ir_a_cualquiera` — no hay que cambiar `"multiply"` por `"subtract"`.
    - **Baja la urgencia de la Fase 6** (girar por click con trigonometría):
      esa fase existía porque se creía que no había ninguna forma de dirigir
      la nave por teclado. Sigue teniendo sentido para "girá 90 grados a
      babor" (rumbo absoluto sin objetivo), pero el caso de uso más común
      —ir hacia una nave enemiga— ya está cubierto.
  - Se limpiaron todas las advertencias de "sin confirmar" del código, la
    ayuda y `docs/hotkeys_sfc2.md`.

- **[12/09] Delay excesivo SOLO en el primer comando.** Reportado en prueba
  real: el primer comando tardaba notablemente más que los siguientes, que
  iban bien. Diagnóstico: **inicialización perezosa** — varias cosas caras se
  hacían recién la primera vez que se usaban, y ese costo se lo comía el
  primer comando. Se encontraron 3 causas, todas arregladas:
  1. **Cliente de OpenAI creado de cero en CADA transcripción**
     (`stt_openai._cliente()`). La primera vez incluye arranque del SDK,
     resolución DNS y **handshake TLS** contra la API. → Ahora el cliente se
     **cachea a nivel de módulo** y se reusa.
  2. **Micrófono inicializado al apretar F12 por primera vez.** Windows tarda
     bastante en abrir el primer `InputStream` (inicializa el driver, negocia
     formato, reserva el dispositivo). Peor aún: ese delay **se comía los
     primeros milisegundos de lo que se decía**. → Se abre y cierra un stream
     al arrancar (`precalentar_microfono()`).
  3. **`gw.getAllWindows()` en cada comando** para encontrar la ventana del
     juego: enumera TODAS las ventanas de Windows y crea un objeto por cada
     una. Era la parte más lenta del envío, y se repetía siempre. → Se
     **cachea la ventana** encontrada (`_ventana_cacheada`), con
     auto-invalidación vía `IsWindow()` si el juego se cierra o se reabre.
     Esto mejora **todos** los comandos, no solo el primero.
  - **Solución integral:** nueva función `precalentar_todo()` que corre al
    arrancar el script y hace las 3 inicializaciones (+ parser y catálogo),
    mostrando cuánto tardó cada una. El precalentado de la API manda 0.1s de
    silencio (costo despreciable) porque crear el cliente no abre la conexión
    por sí solo — el SDK es lazy.
  - **Bonus para diagnosticar:** ahora cada comando imprime un desglose
    `[tiempos] STT: Xs | ejecucion: Ys | TOTAL: Zs`, para poder ver si la
    latencia restante está en la transcripción o en el enfoque de ventana.
  - Validado con mocks: 5 búsquedas seguidas de ventana → **1 sola** llamada
    real a `getAllWindows()` (antes 5), y se confirmó que re-busca
    correctamente si la ventana deja de existir.
  - [ ] **Pendiente de medir en vivo:** con esto, el primer comando debería
        tardar casi lo mismo que el resto. Si sigue habiendo diferencia,
        mirar el desglose de tiempos para ver en qué etapa está.
  - Nota: la `PAUSA_POST_ENFOQUE` de 1.0s sigue afectando a **todos** los
    comandos por igual (no solo al primero) — sigue pendiente evaluar bajarla
    a 0.5s, ver el ítem correspondiente en la Fase 2.

- **[25/09] DECISIÓN: se descarta correr modelos locales. Todo online.**
  Ni STT local (`faster-whisper`) ni LLM local (Ollama).
  - **Por qué:** el local se probó y perdió las dos comparaciones (ver la
    entrada de abajo), y la dirección que tomó el proyecto —Agents SDK, modelo
    de voz en vivo— es online de punta a punta. Mantener dos caminos era pagar
    complejidad por uno que ya no se usa.
  - **Lo que se acepta, dicho explícitamente:** sin internet no hay control por
    voz (antes el parser resolvía la mayoría sin red), y se paga por uso.
  - **La consecuencia encadenada, resuelta:** el STT local era la respuesta al
    costo de la escucha permanente. Sin él, **la compuerta es el botón/hover**
    del panel, que ya está hecho: se manda audio sólo cuando se pide. La
    experiencia de llamar al oficial por su nombre se conserva —se aprieta o se
    pasa el mouse y se dice "artillero, fuego"—, lo único que se pierde es el
    manos libres total. El modo de micrófono siempre abierto queda disponible
    pero **no recomendado** hasta ver el costo por minuto.
  - **El código local no se borra todavía.** `STT_BACKEND = "local"` y
    `LLM_BACKEND = "ollama"` quedan como salida de emergencia hasta que la
    arquitectura nueva esté andando, pero **no se mantienen**. Si siguen sin
    usarse cuando eso pase, se borran.
  - Queda marcado en el README, que fue escrito con el plan inverso: sus
    secciones 2.1 y 2.4 recomiendan modelos locales y pasan a ser historial.

- **[25/09] Prueba #13 medida: el STT local, tal como estaba, PERDIÓ.** Con
  micrófono cableado y las mismas 5 frases:

  | | API (`gpt-4o-mini-transcribe`) | local `tiny` |
  |---|---|---|
  | Tiempos | 2.91 · 1.98 · 1.94 · 2.48 · 2.80 | 1.79 · 2.41 · 2.43 · 2.59 · 4.16 |
  | Promedio | **2.42s** | **2.68s** |
  | Precisión | correcta | **mala: ejecutó comandos equivocados** |

  - **La estimación previa de 0.2-0.4s era mía y estaba mal.** Quedó escrita en
    el README y en la wishlist como si fuera un dato, y no lo era.
  - **Pero la prueba midió `faster-whisper` sin configurar**, con los defaults
    pensados para transcribir audio largo, no órdenes de dos palabras. El
    sospechoso principal es **`beam_size=5`** (el default), que explora cinco
    caminos de decodificación por cada frase. También estaban sin tocar los
    hilos de CPU y el recorte de silencio, y nuestro audio viene con silencio
    de los dos lados por el pre-roll.
  - Se afinó: `beam_size=1`, `cpu_threads=4`, `vad_filter=True`,
    `condition_on_previous_text=False`, y el `initial_prompt` quedó detrás de
    `PROMPT_EN_LOCAL` porque en un modelo chico ocupa contexto y puede
    empeorar las dos cosas a la vez.
  - **Pendiente: repetir la medición con eso puesto**, y si la precisión sigue
    corta, `base` antes que `small`. Mientras tanto **la API se queda como
    backend**, lo cual deja la escucha activa pagando por frase — que era
    justamente lo que el local venía a resolver.

- **[25/09] Micrófono cableado: se destraba la prueba #13 y cambia el orden.**
  Se reemplazó el auricular Bluetooth por un micrófono físico cableado, que
  evita el códec HFP y su calidad teléfono. La prueba #13 (STT local vs. API)
  estaba en espera exactamente por eso y pasa a ser **la primera de la lista**,
  por dos motivos que ahora se suman: es la última palanca grande de latencia
  (el STT es ~80% de un comando), y es lo que vuelve **gratis** a la escucha
  activa, que con micrófono siempre abierto tiene que transcribir todo lo que
  oye.

- **[25/09] Dos formas nuevas de hablar, sin mantener una tecla.**
  `MODO_ESCUCHA` toma tres valores; `push_to_talk` sigue igual.
  - **`boton`**: un botón de mantener apretado en el panel web, para no tocar
    el teclado mientras se juega con el mouse. El audio lo sigue grabando
    Python y la página sólo avisa cuándo empezar y terminar, así el manejo del
    micrófono se queda donde ya funciona. La función de grabar se generalizó a
    recibir un predicado, así la tecla y el botón comparten todo el camino.
  - **`activa`**: micrófono siempre abierto, sin disparador. Corte de frases
    por VAD de energía con **pre-roll**, porque si no se pierde siempre la
    primera sílaba, que es justo donde está el nombre del oficial. Sólo se
    ejecuta lo que **empieza llamando a un oficial** — ese es el filtro que
    separa una orden de una charla. Llamarlo sin darle orden devuelve un
    "¿Sí, capitán?" en personaje.
  - Los dos problemas que trae el modo activo quedaron resueltos, no abiertos:
    el micrófono **se silencia mientras habla un oficial** (usando la duración
    del wav que acaba de disparar) para que el sistema no se transcriba a sí
    mismo, y el script **avisa al arrancar** si se usa escucha activa con el
    backend pago.
  - Validado con audio sintético inyectado por el callback del stream: una
    frase que nombra a un oficial ejecuta, una sin nombre no ejecuta y lo
    informa, una charla cualquiera se ignora, y **el silencio puro no llama al
    STT ni una vez**.

- **[24/09] Prueba #20 cerrada: los oficiales contestan con su voz.** ✅
  Confirmado en vivo que suena la voz correcta de cada oficial, después de que
  el juego reaccionó. Con eso queda cumplido el **punto 3 de la agenda de
  Pato** ("contestar con voz de computadora"), y junto con los retratos del
  punto 2, hay dos de sus cinco pedidos andando.

- **[24/09] Sesión de pruebas: oficiales OK en texto, ambigüedad OK, y dos
  bugs de audio.** Confirmado en vivo que **el oficial correcto contesta cada
  orden** (prueba #20 en su mitad de texto) y que **las cinco palabras sueltas
  ambiguas piden desambiguación** sin ejecutar nada (#19).
  - **Bug 1: no sonaba ningún wav.** Los nombres de archivo coincidían y el
    formato era correcto (mono, 16 bits, 24 kHz), pero la cabecera declaraba
    **2.147.483.647 frames** (`0x7FFFFFFF`): pedirle `wav` a la API de TTS
    devuelve el audio en streaming, con el tamaño del chunk `data`
    indeterminado, así que un archivo de 88 KB dice contener 4 GB. Los
    reproductores tolerantes lo aguantan; `winsound` lee esa cabecera y **no
    reproduce nada, sin tirar error**. El generador ahora pide **PCM crudo** y
    escribe la cabecera con el módulo `wave`; los 25 archivos ya generados se
    repararon en el lugar, sin volver a pagarlos.
  - **Bug 2: micrófono Bluetooth mudo.** Windows expone cada auricular BT como
    **dos dispositivos**: A2DP (buen sonido, **sin micrófono**) y HFP (con
    micrófono, salida a calidad teléfono). En A2DP se graba silencio sin ningún
    error. Se agregó `scripts/probar_microfono.py` (lista dispositivos, prueba
    si aceptan 16 kHz mono, graba con medidor de nivel) y
    `DISPOSITIVO_ENTRADA` en la Fase 2 para fijar cuál usar.
  - **Dato que reordena una prueba:** con el BT el reconocimiento es pobre, y
    es esperable — en Hands-Free el micrófono va comprimido a calidad teléfono,
    que es justo lo que peor transcribe un STT. Por eso la **prueba #13 (STT
    local vs. API) queda en espera de un micrófono decente**: con ese audio, el
    micrófono domina el resultado y la comparación no mide lo que se quiere
    medir.

- **[18/09] Los oficiales ya contestan (punto 3 de la agenda de Pato, versión
  mínima).** Aclarado el alcance: las respuestas son **acuses de recibo**, no
  conversación — "sí, capitán", "no sé cómo, capitán". Eso cambia la solución
  técnica: con un set de frases **fijo y chico** conviene generar el audio
  **una sola vez** con las voces buenas y guardarlo en disco, en vez de
  sintetizar en vivo. Sale más barato, suena mejor que un TTS local, y
  reproducir un wav tarda ~0ms.
  - `scripts/oficiales.py`: el plantel como dato (nombre, raza, rango, alias,
    uniforme) y el reparto de comandos **por tecla**, que es el átomo que
    devuelve el parser y no se rompe al agregar sinónimos. Cuatro desenlaces
    (ok / no entendido / ambiguo / no soportado) con varias variantes cada uno
    para que no suene siempre igual.
  - `scripts/generar_voces.py`: genera los **21 wav** con `gpt-4o-mini-tts`,
    una voz y un tono por oficial. Se corre una vez; vuelve a generar sólo lo
    que falta.
  - Reproducción con **`winsound`**, que es de la librería estándar de Windows:
    **cero dependencias nuevas**, y en modo asíncrono, así que no bloquea el
    loop de comandos.
  - **El acuse va al final de `ejecutar_accion()`**, con la tecla ya mandada:
    el juego reacciona mientras suena la voz, en vez de sentirse lento.
  - Todo opcional y degradable: sin `oficiales.py` el sistema funciona igual,
    sin wav generados imprime la frase y sigue, y `VOZ_ACTIVADA = False` deja
    sólo el texto.
  - Validado con mocks: 21 órdenes enrutadas al oficial correcto, los tres
    desenlaces de error van a la Computadora, "ayuda" no lleva acuse, los
    nombres de archivo son ASCII puro, y **las teclas enviadas no cambian**.
  - [ ] Pendiente en vivo: prueba **#20** de `PRUEBAS.md`.

- **[17/09] Test #18 closed: `pydirectinput.PAUSE = 0` is safe, modifiers
  included.** The two fragile steps passed in the game — "alpha strike"
  (`shift`+`z`) and "ataquen con todo" (Max ECM + alpha strike) both work, and
  **no key was dropped** anywhere, neither in the 4 and 8 key speed sequences
  nor with a modifier held across a press. Final numbers: **0.43s** for one
  key (from 0.76s), **0.65-0.69s** for "media máquina" (from 1.88s) and
  0.86-0.89s for the 8 keys of "alto total".
  - **The execution stage is now closed**: from the 1.75s of the original
    estimate down to under 0.5s for a single-key command, across two findings
    (the calibrated pauses and pydirectinput's own hidden 0.3s per key).
  - Everything left in latency is the STT, 1.5-3.1s, which is now roughly 80%
    of a command. Test #13 is the only big lever left.

- **[17/09] Orbit Target confirmed: `subtract`, and the quickstart is wrong.**
  Tested in the game right after the discrepancy came up: Numpad `–` does
  orbit the selected target, so `SFCfullMan` p.159 is right and `SFCquick`
  p.24 (Numpad `.`) is an erratum. Written into `docs/hotkeys_sfc2.md` and
  kept in the `TECLA_ORBITAR` constant.
  - **This narrows the erratic maneuvers question.** With Orbit (`–`) and
    Follow (`*`) both confirmed, numpad keys demonstrably reach the game
    through `pydirectinput`, so "maniobras evasivas" doing nothing is **not**
    a key delivery or hotkey problem. What is left is the conditions of EM:
    6 points of movement energy spare, and no cloak active.
  - Third of the three manoeuvre keys confirmed working end to end, after
    Follow on 13/09. Only the effect of `/` is in question, not the plumbing.

- **[17/09] Re-read of the manuals over erratic maneuvers, and a hotkey
  discrepancy came out of it.** Reported live: the key arrives but nothing
  visible happens and nothing looks selected. Extracted the text of the three
  PDFs again looking for "erratic". Findings:
  - **EM costs 6 points of movement energy** (SFCfullMan p.102). With no spare
    energy it simply does not engage, which is the most likely explanation of
    "nothing happens" — so it has to be tested at low speed, not full.
  - **EM and the cloaking device are mutually exclusive** (p.140).
  - The effect is "small, swift course changes", not a visible zigzag. What
    shows is the restrictions: no shuttles/fighters/missiles/plasma, no
    mines/transporters/tractors, turn rate down by 1, HETs ~17% more likely to
    fail.
  - **Turning EM off needs the "Normal Maneuvering" button of the Helm MFD**
    (SFCquick p.9, item 12), which has **no hotkey**. By voice we can turn it
    on and not off — that decides whether it belongs in a combo.
  - **⚠️ The two manuals disagree on the Orbit Target key:** SFCfullMan p.159
    says Numpad `–` (`subtract`), SFCquick p.24 says Numpad `.` (`decimal`).
    Both keys exist on the numpad, so it is not an obvious typo, and "orbitar"
    was never confirmed working in the game. The key moved into the
    `TECLA_ORBITAR` constant so the alternative is a one-line change, and it
    became test **#4b**.
  - Also noticed, unrelated: `WISHLIST.md` claims HET 180° is `Numpad 5`, but
    the manual maps Numpad 5 to a generic **"Start HET"** and puts the HET
    directions (left/right/180/hard) in the Helm MFD only, without hotkeys.

- **[17/09] The LLM guessed a speed out of half a word, and accelerated the
  ship.** The STT clipped "media máquina" down to "Máquina.", the rules parser
  did not know it, and the fallback answered `set_speed` level 1 (cuarto de
  máquina) — a real key sequence out of an ambiguous fragment, plus 2.43s of
  latency to get it wrong. Same family as the prompt echo: an unclear input
  producing a confident action.
  - `FRASES_AMBIGUAS` in the parser answers a single ambiguous word ("maquina",
    "velocidad", "alerta", "escudos", "objetivo", "enemigo") with the list of
    what to say instead, presses nothing and **never reaches the LLM**. It is
    matched against the COMPLETE text without punctuation, so it cannot steal
    a match from a longer phrase: "media maquina" resolves as always.
  - The LLM system prompt was hardened as well, on both backends: if the
    phrase looks truncated or is one word matching several commands, call no
    function — running the wrong command is worse than running nothing.
  - Checked with mocks: 8 ambiguous fragments execute zero keys, and the 22
    full commands are untouched.
  - [ ] Live: test **#19** of `PRUEBAS.md`.

- **[17/09] pydirectinput's hidden pause confirmed (test #18, steps 1-3).**
  Setting `PAUSE = 0` landed exactly on the prediction and **no key was
  dropped** over 3 speed cycles: 0.76s → **0.43s** for one key, 1.88s →
  **0.65-0.69s** for "media máquina", and 0.86-0.89s for the 8 keys of "alto
  total". Total execution cost for a full command is now under a second.
  Pending: steps 4-5, `shift+z` and the ECM + alpha strike combo, which are
  the cases most likely to lose a key with no pause at all.

- **[17/09, later] pydirectinput was adding ~0.3s PER KEY on its own.** Found
  by reading the timings of the second session: execution was 0.76s for a
  single key and 1.88s for "media máquina" (4 keys), while our own pauses only
  account for 0.3s of focus + 0.1s of console + 0.05s per key. The model that
  fits all three measurements (1 key 0.76s, `shift+z` 1.05s, 4 keys 1.88s) is
  **0.1s per elementary call**, which is `pydirectinput.PAUSE`: a `press()` is
  keyDown + keyUp + wrapper, so 0.3s.
  - Set to 0 through the new `PAUSA_INTERNA_PYDIRECTINPUT`, since our own
    `PAUSA_ENTRE_TECLAS` already spaces the keys. Expected: one key 0.76s →
    ~0.45s, "media maquina" 1.88s → ~0.6s.
  - **Caveat that makes this test #18 and not a closed fix:** the calibration
    of test #2 ran with that hidden 0.3s in place, so the real gap between
    keys was ~0.35s, not the 0.05s we thought we had validated. With PAUSE at
    0 the gap really is 0.05s, which was never tested — a dropped key is the
    thing to watch, especially on the 4-key speed commands.

- **[17/09, later] The echo guard fired on our own warm-up.** Working as
  designed but noisy: `precalentar()` sends 0.1s of silence, which is exactly
  what makes the model echo the prompt, so every startup printed the warning.
  `transcribir_openai()` took a `usar_prompt` flag and the warm-up now calls
  without the prompt, which also makes the warm-up cheaper (fewer tokens).

- **[17/09, later] Two more synonyms lost to the LLM, one of them answered
  wrong.** "Seguir enemigo" was not in `FOLLOW_WORDS`, went to the fallback,
  and the LLM picked **cycling enemies** (`y`) instead of Follow Target — the
  right key for a phrase we should never have delegated. "Deseleccionar a
  objetivo" and "Ir a enemigo" were not recognised either. All three are in
  the parser now. Same lesson as the shields one, twice over.

- **[17/09, later] Intermittent 404 from the LLM, unresolved.** Two calls died
  with `Error code: 404` in 0.19s while others in the same session worked in
  0.88-1.45s, so it is not a wrong model name (that would fail every time).
  The error message now prints the exception type, the model and the response
  body, to have something to work with next time. Test #16 carries the steps
  to reproduce it.

- **[17/09] SERIOUS BUG: the STT echoed the vocabulary prompt back and the
  parser fired an attack combo on its own.** Reported in a live test. After a
  push-to-talk with no speech in it, the API answered with the whole
  `PROMPT_VOCABULARIO` as if it were the transcription. That text **ends with
  "ataquen con todo"**, so `parsear_comando()` matched it and fired Max ECM +
  Alpha Strike **with nobody giving an order**.
  - It is a known failure mode of the transcription models: given audio
    without speech, they return the `prompt` they were handed. The underlying
    cause on our side is that the parser matches a command **anywhere** in
    the text, so any long spurious transcription can end up pressing a real
    key.
  - **Three independent guards added:**
    1. `stt_openai.es_eco_del_prompt()`: if the answer is a long verbatim
       chunk of the prompt, or >=85% of its words belong to the prompt with
       >=12 words, it is dropped and `transcribir_openai()` returns `""`.
    2. `MIN_DURACION_AUDIO_SEG = 0.3` in Fase 2: a tap on F12 never reaches
       the API, which saves the round-trip and the cost as well as the risk.
    3. `MAX_CARACTERES_COMANDO = 150` in Fase 2: no transcription longer
       than that reaches the parser. This also covers the usual
       hallucinations on silence, which look nothing like the prompt.
  - Checked with mocks: the bug was reproduced (the echo parses as
    `combo/ataque_total`) and with the guard in place the transcription comes
    back empty and **no key is sent**. Confirmed it does not touch the normal
    cases ("alerta roja", "media maquina", "seguir a esa nave", nor a long
    chained phrase of real commands).
  - [ ] Still to confirm live: test **#17** of `PRUEBAS.md`.

- **[17/09] Pauses calibrated on the real machine (test #2 resolved).** The
  minimums that worked were `PAUSA_POST_ENFOQUE` **0.2s** and
  `PAUSA_ENTRE_TECLAS` **0.03s**; they were applied one step above, at
  **0.3s** and **0.05s**. Real saving: ~0.7s on every command and ~1.7s on
  the 8-key ones (a single-key command goes from ~1.45s to ~0.55s of
  execution). The original 1.0s, picked by eye back in Fase 0, was **5 times**
  the minimum.

- **[17/09] First-command delay: closed (test #3 resolved).** With the
  warm-up, the **execution** stage is a constant 1.45s from the very first
  command, and the 4.23s of API connection are paid at startup instead. The
  difference left (STT 3.12s on the first against 2.15-2.57s afterwards) is
  API variance, not lazy initialization.

- **[17/09] The STT is now the bottleneck, by a wide margin.** Measured live:
  1.7-3.1s of STT out of a 3.5-5.8s total, that is **60-70% of the time**,
  well above the 0.5-1.5s the README estimated for the cloud backend. With
  the pauses already calibrated, everything left to win is there:
  `faster-whisper` with `tiny` should land around 0.2-0.4s and pays no
  network. That is why test **#13 was promoted to HIGH priority** in
  `PRUEBAS.md` (it was LOW).

- **[17/09] "escudos a maximo" fell through to the LLM over a missing
  synonym.** The STT transcribed exactly what was said ("Escudos a máximo."),
  but `SHIELD_MAX_WORDS` only had "escudos al maximo" (with the "l"), so it
  went to the fallback: 1.46s and one API call for something the rules parser
  answers in microseconds. The variants were added ("escudos a maximo",
  "subir escudos", "levantar escudos", "escudos arriba", "refuercen
  escudos"). General lesson: **when something falls through to the LLM, look
  for a missing synonym first** before accepting the fallback as the answer.
  - Side note: this was the first live run of the LLM fallback ever, and it
    picked the shields command correctly, so Fase 4 got validated end to end
    by accident.

- **[12/09] Combos nuevos: "buscar objetivo + rumbo + velocidad" en una orden.**
  Pedido concreto: un comando que busque un objetivo (el más cercano o
  cualquiera), le ponga rumbo y acelere hacia él, sin tener que encadenar tres
  órdenes a mano. Se agregaron dos combos a `COMBOS`:
  - **`ir_al_mas_cercano`** ("vamos al enemigo más cercano"):
    `` ` `` (Target Nearest Enemy) → `Numpad *` (Follow) → 6x `s` (~3/4 máquina).
  - **`ir_a_cualquiera`** ("busca un enemigo"):
    `Y` (ciclar enemigos) → `Numpad *` (Follow) → 6x `s`.
  - **Sobre el "al azar":** el juego **no tiene un comando de target
    aleatorio**. Lo más parecido es `Y` (Target Enemy cycles), que avanza al
    siguiente del ciclo — repetir la orden va rotando entre los enemigos, que
    en la práctica cubre el caso de uso de "elegí cualquiera".
  - **Se eligió 3/4 de máquina (6x `s`) y no máxima** a propósito: llegar a
    toda velocidad hace difícil frenar/maniobrar al llegar al objetivo.
  - **Dependencia del hallazgo anterior:** el paso de rumbo usa Follow Target,
    que es justo lo que no está confirmado. Si al probar resulta que no vira,
    el arreglo es de una línea por combo: cambiar `"multiply"` por
    `"subtract"` (Orbit Target, que el manual sí confirma que mueve la nave),
    o asignarle tecla a Intercept Target desde Options → Hotkeys. Queda
    documentado en el propio código, al lado de los pasos.
  - Validado con mocks: las secuencias enviadas son exactamente
    `` ` multiply s s s s s s `` y `y multiply s s s s s s`, con el foco de
    ventana hecho **una sola vez** para todo el combo. Sin regresiones: se
    verificó que "objetivo mas cercano", "siguiente enemigo", "otro enemigo",
    "seguir a esa nave" y el resto siguen resolviendo igual que antes (las
    frases nuevas son más específicas y se chequean primero, por estar en
    `COMBOS`).

---

## Fase 3 — Velocidad relativa precisa (OCR o calibración de pasos)

**Objetivo:** que "media máquina" resulte en una velocidad deseada realmente cercana
al 50% de la máxima de la nave actual, no una aproximación arbitraria.

### Checklist
- [ ] Decidir enfoque: OCR del HUD vs. conteo de pulsaciones calibrado manualmente
      (ver README sección 2.5 para el detalle de ambas opciones)
- [ ] Si OCR: instalar Tesseract, definir región de pantalla del HUD a capturar
      (elementos "Current Speed" / "Desired Speed" del manual), probar precisión
      de lectura
- [ ] Si conteo manual: jugar y contar cuántos `S` hacen falta desde 0 hasta
      distintos niveles, para 2-3 clases de nave distintas, y documentar la tabla
- [x] **[16/09] An explicit percentage now executes, rounded to the closest
      level.** "velocidad al 70 por ciento" parsed fine, but `set_speed_pct`
      only printed a "pending Fase 3" notice and **sent no key at all**: the
      order was silently lost, which is worse than an approximation. It now
      rounds to one of the 5 levels (70% → level 3, ~75%) and presses the
      matching S/A sequence, through `pct_a_nivel()`. This is the "simplified
      approach without OCR" the README already proposed for the MVP; it does
      **not** close the phase: real per-ship precision is still pending.
      Checked with mocks (70/50/10/100%, plus out-of-range clamping).
- [ ] Implementar la lógica de "ir pulsando S/A hasta llegar al objetivo"
- [ ] Probar en vivo con distintas naves/velocidades de partida

### Resultado (completar después de probar)
- Fecha:
- Enfoque elegido:
- Precisión lograda:
- Notas:

---

## Fase 4 (opcional) — LLM local como fallback

**Objetivo:** cubrir frases de lenguaje libre que el parser de reglas no reconozca.
Solo abordar esta fase si en la práctica el parser se queda corto seguido (ver
README sección 2.4 para tamaños de modelo recomendados).

### Checklist
- [x] **Catálogo de comandos dinámico** → `scripts/catalogo_comandos.py`.
      Genera automáticamente, a partir de los diccionarios que YA existen en
      `fase1_text_commands.py` (`SPEED_WORDS`, `ALERT_WORDS`, `COMBOS`, etc.),
      una lista estructurada de todas las acciones que el sistema puede
      ejecutar. Esto evita que el LLM y el parser de reglas queden
      desincronizados: si se agrega un comando nuevo a los diccionarios de la
      Fase 1, automáticamente aparece también en el catálogo que ve el LLM,
      sin tener que mantener dos listas por separado. Se puede correr
      `python catalogo_comandos.py` para ver el catálogo generado en texto.
- [x] **Integración con Ollama** → `scripts/llm_fallback.py`. Arma un system
      prompt que incluye el catálogo completo (acción + parámetros + ejemplos
      de frases por cada una) y le pide al LLM que devuelva **solo JSON**
      (`{"accion": "...", "parametros": {...}}` o `{"accion": null}` si nada
      aplica) — nunca texto libre, para poder ejecutar la respuesta con
      confianza. Incluye `_extraer_json()` para tolerar respuestas envueltas
      en markdown o con texto extra alrededor (común en LLMs chicos).
- [x] **🆕 Mejora: Function Calling nativo de OpenAI (más rápido y confiable
      que JSON libre)** → el usuario preguntó cómo "alimentar al modelo con
      los comandos reales del juego" de forma más directa. En vez de
      describir los comandos como texto plano en el prompt (lo que obliga al
      modelo a "leer" y generar JSON libre él mismo), ahora se usa la función
      nativa de **tools/function calling** de la API de OpenAI:
  - `catalogo_comandos.generar_tools_openai()` (nuevo): convierte
    dinámicamente el mismo catálogo de siempre en un esquema de "funciones"
    en el formato exacto que espera la API (`tools=[...]`), una función por
    cada comando real del juego (ej. `media_maquina`, `red_alert`,
    `ataque_total`), cada una sin argumentos libres — el nombre de la
    función ya identifica la acción exacta.
  - `llm_fallback._interpretar_con_openai_function_calling()` (nuevo): le
    pasa ese esquema a la API con `tool_choice="auto"`, y el modelo **elige**
    cuál función invocar (o ninguna, si no aplica) — la API valida que el
    nombre elegido exista en el esquema, no puede "inventar" un comando que
    no esté en la lista. Esto es más rápido (tarea para la que el modelo
    está específicamente entrenado) y más confiable (sin depender de que el
    modelo "obedezca" la instrucción de solo devolver JSON).
  - El backend `"ollama"` se mantiene con el enfoque anterior de JSON libre
    en el texto (`_interpretar_con_ollama_json_libre()`), porque no todos
    los modelos chicos que corren bien en CPU soportan function calling de
    forma confiable — la elección de método ahora depende de `LLM_BACKEND`.
  - Validado con mocks del SDK de OpenAI simulando 4 escenarios: elegir un
    comando simple, un comando de una sola tecla, un combo, y el caso de
    "ninguna función aplica" — los 4 tradujeron correctamente a la acción
    interna esperada.
- [x] Integrado como fallback en ambos scripts (`fase1_text_commands.py` y
      `fase2_voice_commands.py`): solo se consulta al LLM cuando
      `parsear_comando()` devuelve `{"action": "unknown"}`. Import diferido
      (dentro de `main()`, no a nivel de módulo) para evitar import circular
      (`llm_fallback` → `catalogo_comandos` → `fase1_text_commands`). Si
      Ollama/el paquete `ollama` no está instalado, ambos scripts detectan el
      `ImportError` y siguen funcionando igual solo con el parser de reglas
      (fallback verdaderamente opcional, no rompe nada si no está disponible).
- [x] Validado localmente con mocks de `ollama` (incluyendo respuestas con
      markdown, con texto extra alrededor del JSON, `{"accion": null}`, y
      texto no-JSON que debe caer a `unknown` sin crashear) y con un test de
      integración completo confirmando que no hay import circular en la
      práctica.
- [x] **[16/09] The catalog WAS out of sync with the parser (fixed).**
      `catalogo_comandos.py` promised to derive itself from the Fase 1
      dictionaries alone, but `generar_catalogo()` carried a hardcoded list
      that never grew with the commands added on 12/09: cycling enemies only
      (`y`), cycling backwards (`shift+y` / `shift+t`), deselecting (`\`),
      Orbit (`subtract`), Erratic Maneuvers (`divide`) and the whole target
      memory (`5`-`8`, `ctrl+5`-`8`) were **unreachable for the LLM**: the
      parser understood them, the LLM could not pick them. The catalog went
      from **16 to 32 tools**.
  - So it does not happen again: `verificar_cobertura()` compares the first
    phrase of every `*_WORDS` collection of `fase1_text_commands.py` against
    the catalog examples and reports whatever is missing. Run it with
    `python catalogo_comandos.py`. `HELP_WORDS` is excluded on purpose
    (listing the commands is not a key press).
  - Checked with mocks: no gaps in coverage, tool names unique and valid for
    the API, and the 16 new actions press the right key once they go through
    `_item_catalogo_a_accion()`.
- [x] **[16/09] OpenAI client cached in `llm_fallback.py`.** The same lazy
      initialization fixed on 12/09 for the STT was still untouched in the
      LLM: a new `OpenAI(...)` was created **on every call**, so the first
      fallback of each session paid DNS + TLS handshake. It now reuses the
      client `stt_openai.py` already warms up at startup (or opens its own, if
      the STT runs on the local backend).
  - `generar_tools_openai()` is cached too: without that, the warm-up call in
    `precalentar_todo()` achieved nothing and every fallback rebuilt the whole
    32-tool schema before being able to ask anything.
- [ ] Instalar Ollama en la máquina Windows: https://ollama.com/download
- [ ] Descargar modelo chico: `ollama pull llama3.2:3b` (o `llama3.2:1b` si
      se quiere algo aún más liviano/rápido)
- [ ] Instalar el cliente de Python: `pip install ollama`
- [ ] Probar en vivo con frases de lenguaje libre que el parser de reglas no
      reconozca (ej. "aumentá bastante la velocidad", "che, pongan la alerta
      esa roja") y confirmar que el LLM interpreta razonablemente bien usando
      el catálogo real de comandos
- [ ] Medir latencia extra que agrega este paso (la consulta al LLM se suma
      al tiempo de STT + `PAUSA_POST_ENFOQUE` ya conocidos)

### Resultado (completar después de probar)
- Fecha:
- ¿Hizo falta finalmente? (evaluar tras un tiempo de uso si el parser de
  reglas solo ya cubre casi todo, o si el LLM se termina usando seguido):
- Notas:

---

## Fase 5 (opcional) — Más comandos

**Objetivo:** extender cobertura a escudos, alertas, ECM/ECCM, cámaras, etc.,
usando `docs/hotkeys_sfc2.md` como referencia completa.

### Checklist
- [ ] Priorizar lista de comandos adicionales más útiles/divertidos de tener
- [ ] Agregar cada uno al diccionario de sinónimos del parser
- [ ] Probar en vivo

---

## Fase 6 (pendiente, decidida posponer) — Control de rumbo/giro con mouse

**Objetivo:** soportar comandos de giro relativo tipo "girar 90 grados a la
derecha", "virar a la izquierda 45 grados". **Decisión tomada:** posponer
esta fase hasta consolidar y probar bien en uso real lo ya construido (Fases
0-4) — se retoma cuando el usuario lo pida.

### Contexto / diseño discutido (para no perder el hilo)
- El juego fija el rumbo con **click izquierdo del mouse** en la pantalla
  táctica (la nave gira hacia el punto clickeado) — no hay tecla para "girar
  X grados", es puramente posicional.
- El juego no expone por ninguna API el rumbo actual de la nave (igual que
  con la velocidad, ver Fase 3) — solo se ve visualmente en el HUD.
- **Opción A (recomendada para empezar, sin OCR):** asumir que la cámara
  siempre muestra la nave centrada y apuntando "hacia arriba" en pantalla
  (razonable con cámara Chase/Follow, que es la que se usa por defecto).
  Con esa asunción, "girar X grados" se reduce a calcular con trigonometría
  simple un punto de click a cierta distancia del centro de pantalla, en el
  ángulo pedido, sin necesitar leer nada de pantalla. Requiere calibrar en
  la máquina real: centro de la vista táctica (X, Y) y un radio de click
  razonable.
- **Opción B (más precisa, más compleja):** leer el rumbo real actual con
  OCR del HUD, calcular el rumbo objetivo, y traducirlo a coordenadas de
  pantalla reales. Comparte la misma complejidad/herramientas que la Fase 3
  (OCR) — tiene sentido resolver ambas juntas más adelante, no antes.
- `pydirectinput` ya soporta `moveTo(x, y)` y `click()` — no hace falta
  ninguna dependencia nueva para esto, la complejidad es de cálculo/
  calibración, no de herramientas.

**⚠️ Prioridad REVISADA (13/09):** esta fase era prioritaria porque se creía
que **no había ninguna forma de dirigir la nave por teclado**. Pero se
confirmó que **Follow Target (`Numpad *`) sí vira la nave hacia el objetivo
seleccionado** — o sea que el caso de uso más frecuente ("andá hacia esa nave
enemiga") ya está resuelto por voz, sin mouse ni trigonometría.

Lo que esta fase seguiría aportando: **rumbo absoluto sin objetivo**, del tipo
"girá 90 grados a babor" o "rumbo 270" — útil para maniobras de evasión o
posicionamiento, pero bastante menos frecuente que perseguir a alguien.

Conclusión: **deja de ser la próxima fase obligatoria.** Conviene primero
estabilizar y medir lo que ya existe (ver `PRUEBAS.md`), y después decidir
entre esta fase y el encadenado de comandos (`WISHLIST.md`) según qué se
extrañe más al jugar.

### Checklist (para cuando se retome)
- [ ] Confirmar con el usuario si seguir con Opción A o ir directo a Opción B
- [ ] Calibrar centro de pantalla táctica y radio de click en la máquina real
- [ ] Implementar parser de frases tipo "girar/virar N grados a la
      derecha/izquierda" (extraer ángulo + dirección con regex)
- [ ] Implementar cálculo trigonométrico + `pydirectinput.click(x, y)`
- [ ] Probar en vivo con distintos ángulos

---

## Fase 7 — Feedback sobre arquitectura de IA (sesiones con Pato)

**Pato** (quien lidera/controla el proyecto, con experiencia en IA) dio feedback
sobre el enfoque de LLM/STT usado. Se analizó cada punto; queda documentado acá
qué se adoptó, qué se descartó (y por qué), y qué queda anotado para el futuro.

> 📋 **Resumen ejecutivo en formato tabla (para Slack):**
> ver `docs/feedback_sesiones.md` → **Sesión #1**. Esta sección del ROADMAP es
> el detalle técnico largo de esa misma charla.

### Feedback recibido (resumen)
1. Usar la guía oficial de "Speech-to-Text" de OpenAI
   (https://developers.openai.com/api/docs/guides/speech-to-text).
2. Sugerencia de no ir por "STT separado" sino directo por LLMs, mandándole
   audio + lista de "tools" (comandos disponibles), y que el LLM devuelva
   `tool_calls` en el JSON de respuesta en vez de texto libre.
3. Mencionó dos librerías/SDKs de OpenAI: el fetch común (parsear el JSON de
   `tool_calls` a mano y volver a llamar si hace falta) vs. `@openai/agents`
   (Agents SDK), que segun el compañero es "mejor" porque maneja solo el
   árbol de decisiones (reintentos, fallbacks encadenados) sin necesidad de
   parsear/refetchear manualmente.

### Análisis punto por punto

**Punto 1 (guía de STT) y function calling con `tools`/`tool_calls`:**
✅ **Ya implementado, coincide con lo que ya se había armado antes de este
feedback.** `stt_openai.py` ya usa la API de Whisper de OpenAI para STT, y
`llm_fallback.py` (backend `"openai"`) ya usa el mecanismo nativo de
`tools=[...]` + `tool_choice="auto"` de la API de Chat Completions (ver
`catalogo_comandos.generar_tools_openai()` y
`llm_fallback._interpretar_con_openai_function_calling()`), NO el enfoque
viejo de "pedile JSON libre y parseálo a mano". En esto el proyecto ya
estaba alineado con la recomendación antes de recibirla.

**Punto 2 (mandar audio directo al LLM, sin transcribir primero por
separado) — evaluado y DESCARTADO por ahora, con justificación:**
Existen modelos de OpenAI (ej. `gpt-4o-audio-preview`, Realtime API) que
aceptan audio directo en el mensaje de chat y pueden devolver `tool_calls`
sin un paso de STT separado — en teoría ahorra un round-trip de red y
podría bajar latencia. **Por qué no se adopta:** el proyecto depende
fuertemente de un **parser de reglas local y gratuito**
(`fase1_text_commands.py`) que resuelve la mayoría de los comandos típicos
en microsegundos, sin usar la API en absoluto. Para poder chequear ese
parser de reglas ANTES de recurrir al LLM, de todos modos hace falta el
texto transcripto — mandar el audio directo al LLM eliminaría la posibilidad
de ese camino rápido/gratis para la mayoría de los comandos, o forzaría a
transcribir dos veces con métodos distintos (sin sentido). Queda anotado
como posible optimización de bajo impacto para revisar en el futuro, no
como algo urgente.

**Punto 3 (Agents SDK, `@openai/agents`) — evaluado, matizado, no adoptado
por ahora:**
Aclaración importante: `@openai/agents` es el paquete de **JavaScript/
TypeScript** (npm). El equivalente en Python (el lenguaje de todo este
proyecto, por depender de `pydirectinput`/`pygetwindow`/control de Windows)
es **`openai-agents`** (`pip install openai-agents`). Es real y más avanzado
que el `llm_fallback.py` armado a mano: permite declarar árboles de
decisión, reintentos, handoffs entre agentes, guardrails, etc. **Por qué no
se adopta todavía:** nuestro caso de uso actual es una clasificación simple
de un solo paso ("esta frase → esta tool"), sin necesidad de razonamiento
multi-paso encadenado — usar el Agents SDK para esto sería complejidad
innecesaria. **Cuándo SÍ tendría sentido revisar esto a futuro:** si se
quisieran comandos con lógica condicional encadenada, ej. "atacá con todo,
y si no hay objetivo seleccionado, primero seleccioná el más cercano
automáticamente" — ahí el Agents SDK ahorraría bastante código manual de
árbol de decisiones.

### Conclusión / decisión
No se hicieron cambios de código a partir de este feedback (el punto 1 y
parte del punto 3 ya estaban cubiertos; los puntos de audio-directo y
Agents SDK quedan evaluados y pospuestos, con la justificación de por qué,
documentada arriba, para no tener que re-analizarlo si se vuelve a plantear
más adelante).

### Sesión #2 — viernes 18/09/2026: todo aprobado, y agenda nueva

> 📋 Resumen ejecutivo en tabla: `docs/feedback_sesiones.md` → **Sesión #2**.

Se repasó todo lo construido desde la Sesión #1 y **quedó aprobado, sin
correcciones**. Los dos compromisos de esa charla están cerrados: el STT nuevo
se midió en vivo (4 de 5 frases perfectas, 1.5-3.1s) y los dos puntos no
adoptados se explicaron — de los cuales **uno cambió de estado con la
medición**: el STT resultó ser el 80% del tiempo de un comando, así que mandar
audio directo al LLM ya no se puede descartar por costo. Se mantiene igual el
plan de probar primero `faster-whisper` local, que a 0.2-0.4s ganaría en
latencia y en costo conservando el parser gratis.

**Pato puso una agenda nueva de 5 puntos**, que mueve el proyecto de
"estabilizar el control por voz" a **construir una interfaz**:

1. Probar push to talk.
2. Generar imágenes de pilotos, oficiales.
3. Contestar con voz de computadora.
4. ¿Videítos del juego?
5. Cliente browser + server Python en background.

**Lectura de esa agenda:** los puntos 2, 3 y 4 necesitan **un lugar donde
mostrarse y sonar**, y hoy no existe — la consola es todo lo que hay. El punto
5 es ese lugar, así que **habilita a los otros tres** y va primero. Y el punto 1
puede ser un requisito del 5: un tab de browser no puede capturar una tecla
global mientras el foco lo tiene el juego, así que dónde vive el micrófono
define qué arquitectura es posible. Análisis completo en `WISHLIST.md` §5.

**Restricción que no cambia:** la inyección de teclas se queda en el proceso
Python como Administrador. Un cliente web es interfaz, nunca control.

Dos puntos admiten varias lecturas y hay que aclararlos antes de escribir
código: qué quiere decir "probar push to talk" (¿alternativas al PTT? ¿otra
tecla? ¿wake word?) y si "videítos del juego" es grabar clips o mostrar video
en la interfaz.

**Costo de esta agenda:** la prueba #13 (STT local), que era la última palanca
grande de latencia, queda sin correr por ahora.

### Sesión #3 — viernes 25/09/2026: todo OK, y piden el Agents SDK

> 📋 Resumen ejecutivo: `docs/feedback_sesiones.md` → **Sesión #3**.

Los puntos que había que repasar quedaron **todos OK, sin correcciones**. Sale
un pedido nuevo: **usar el Agents SDK de OpenAI**, que Pato mostró andando con
nuestro propio diccionario de comandos.

**Lo importante es que lo habíamos rechazado dos veces**, con el argumento de
que nuestro caso era clasificación de un solo paso. Ese argumento **era válido
para el sistema de entonces y dejó de valer**, por tres cambios nuestros:
el **encadenado de comandos** (implementado ese mismo día), el **enrutado por
oficial** —que es literalmente un handoff de agentes— y el **manejo de
ambigüedad**, que es un turno de conversación y no una clasificación.

Es la tercera vez que ocurre el mismo patrón: rechazamos el audio directo al
LLM, después la Realtime API, y ahora el Agents SDK; y en los tres casos el
rechazo era correcto para el sistema del momento y el sistema cambió después.
**La conclusión operativa no es que analizamos mal, es que los "no adoptado"
hay que revisarlos cada vez que cambia el alcance**, en vez de darlos por
cerrados.

Su ejemplo de referencia también cambió desde el análisis del 18/09: pasó a
`gpt-live-1` **por WebRTC** (lo cual deja de más el transporte de audio propio
que habíamos escrito) y el modelo de voz **delega las tools a un modelo de
texto más barato**. Detalle y el mapeo pieza por pieza, en `WISHLIST.md` §5.9.

**Sin resolver, y hay que hacerlo antes de escribir código:** `gpt-live-1` es
posterior a lo que conozco de primera mano, así que hay que leer la doc y
confirmar qué expone el SDK de **Python** (su ejemplo es de JS); y sigue sin
mirarse el **precio por minuto de audio**, que es el único dato que falta para
decidir entre escucha permanente y wake word local.

### Segunda pasada sobre el mismo feedback (con lectura de la guía oficial)

Se volvió a plantear el mismo feedback, esta vez leyendo a fondo la guía
oficial de Speech-to-Text linkeada. Confirmado que la parte de "tools /
tool_calls" **ya estaba implementada** (ver análisis arriba), pero la
lectura de la guía sí reveló **dos mejoras concretas que NO estábamos
aprovechando** y que se aplicaron:

- [x] **Modelo de STT actualizado: `whisper-1` → `gpt-4o-mini-transcribe`**
      (`stt_openai.py`). La guía oficial ya recomienda los modelos
      `gpt-4o-transcribe` / `gpt-4o-mini-transcribe` por sobre `whisper-1`:
      son más precisos, más baratos y más rápidos. Veníamos usando `whisper-1`
      porque era el modelo vigente cuando se escribió el script. Cambio de una
      línea, sin impacto en el resto del pipeline (la firma de
      `transcribir_openai()` no cambió).
- [x] **Vocabulary biasing con el parámetro `prompt`** (`stt_openai.py`,
      constante `PROMPT_VOCABULARIO`). La guía documenta que se le puede
      pasar un `prompt` con vocabulario del dominio para sesgar la
      transcripción. Esto ataca directamente el riesgo #1 de la Fase 2 (que
      Whisper transcriba mal la jerga específica: "media máquina" → "media
      manzana", "ECCM" → "eceeme"), que estaba anotado como pendiente de
      probar en vivo. Se cargó una lista acotada con los términos más
      propensos a confundirse (la ventana de prompt del STT es de ~224
      tokens, no entra el catálogo completo ni tiene sentido meterlo).
- [x] **`temperature=0` en la transcripción**: para que el STT sea lo más
      determinista posible y no "improvise" palabras cuando el audio es
      ambiguo — deseable en un caso de uso de comandos cerrados como este.
- [x] Validado localmente con mocks (el SDK de `openai` y `pydirectinput` no
      están instalados en la Mac): el módulo importa bien, `MODELO_STT` es el
      nuevo, y la llamada a la API incluye `prompt=` y `temperature=0`.
      Confirmado también que `catalogo_comandos.generar_tools_openai()` sigue
      generando las 16 tools correctamente.
- [ ] **Pendiente de probar en vivo en la Windows:** medir si el cambio de
      modelo mejora la latencia real, y si el `prompt` de vocabulario
      efectivamente reduce los errores de transcripción de la jerga del
      juego. Ajustar `PROMPT_VOCABULARIO` con los términos que en la práctica
      se sigan transcribiendo mal.

**Lo que se mantiene descartado (sin cambios respecto al análisis de arriba):**
mandar el audio directo al LLM sin STT separado (rompería el camino rápido/
gratis del parser de reglas) y el Agents SDK (`openai-agents`) — sigue siendo
complejidad innecesaria para una clasificación de un solo paso. El
"diccionario de desambiguación" que mencionó el compañero en su ejemplo es,
en nuestro caso, exactamente lo que ya hace `catalogo_comandos.py`: generar
dinámicamente el mapa de comandos válidos, con la ventaja adicional de que se
deriva de los mismos diccionarios del parser de reglas y por lo tanto nunca
queda desincronizado.

---

## Log general de sesiones de prueba

Usar esta sección para ir anotando, en orden cronológico, qué se hizo en cada
sesión de trabajo/prueba, independientemente de la fase.

- **[fecha]** — Ejemplo de entrada: "Se instaló pydirectinput, se probó tecla S,
  no hubo reacción visible en el juego en modo fullscreen exclusivo. Pendiente
  probar en modo ventana."
- **Sesión Fase 0 (completa):** Se identificó el juego (Star Trek: Starfleet
  Command Gold Edition) y se reemplazaron los manuales genéricos por los oficiales
  de la edición (`SFCfullMan.pdf`, `Supplemental Manual.pdf`, `SFCquick.pdf`),
  actualizando `docs/hotkeys_sfc2.md`. Se confirmó que el juego corría en pantalla
  completa exclusiva; se intentó resolver editando `SFC.INI` (`windowed=1` +
  `lowres`) pero la ventana resultante quedaba mal dimensionada/cortada. Se resolvió
  instalando y configurando **DxWnd** (ejecutado como Administrador para evitar
  error 740), con perfil: "Run in Window" + "keep aspect ratio" (pestaña Main) y
  "Locked Size" + resolución inicial/límite (pestaña Video) — juego abre
  correctamente en ventana, interfaz completa visible. Se instaló Python 3.14 en
  la Windows (con un impasse resuelto de PATH incompleto: faltaba la carpeta raíz
  de la instalación, solo estaba la de `Scripts`). Se instaló `pydirectinput` sin
  problemas de compatibilidad. Se creó y corrió `scripts/fase0_test_key.py`: la
  primera prueba sin permisos elevados no tuvo efecto; corriendo la consola de
  Python **como Administrador**, el script funcionó correctamente y la nave
  aceleró/frenó como se esperaba. **Fase 0 cerrada con éxito.** Próximo paso:
  Fase 1 (parser de comandos por texto, sin voz).
- **[16/09] Full read of the project + 3 code fixes** (Windows machine not
  touched, everything checked with mocks): (1) the LLM catalog was out of sync
  with the parser and 16 commands were missing from it — it went from 16 to 32
  tools, with a coverage check so it does not happen again; (2)
  `llm_fallback.py` created one OpenAI client per call, the same latency bug
  already fixed in the STT — it now reuses the warmed-up client, and the tool
  schema is cached; (3) "velocidad al N por ciento" was understood but sent no
  key — it now rounds to the closest level. Detail under Fase 3 and Fase 4.
  Still to validate live: tests **#15 and #16** of `PRUEBAS.md`.
- **[17/09] First testing session on the Windows machine with the new code.**
  Tests #2 (pauses calibrated: 1.0s → 0.3s), #3 (first-command delay closed)
  and #14 (F12 does not collide) were resolved, and #9 (STT) moved forward.
  **A serious bug came out**: the STT echoed the vocabulary prompt as a
  transcription and the parser fired an Alpha Strike on its own — fixed with
  three independent guards, still to be confirmed live (#17). The finding that
  changes priorities: the **STT is now 60-70% of the latency**, so #13 (local
  STT) was promoted to HIGH. Full detail under the Fase 2 findings.
- **[17/09, second session] The guards work, and a bigger latency culprit
  turned up.** Tests #17 (echo guards, no spurious key reached the game) and
  the pause sanity check came out clean, execution dropped from 1.45s to 0.76s
  per key, and #8 (targeting) is almost done. Reading the numbers exposed
  `pydirectinput.PAUSE`, which was quietly adding ~0.3s per key — set to 0,
  and it is now test **#18**, the first thing to validate tomorrow because a
  dropped key would invalidate the rest of the session. Also found: erratic
  maneuvers sends its key but does nothing visible (#4), an intermittent 404
  from the LLM, and two more missing synonyms.
