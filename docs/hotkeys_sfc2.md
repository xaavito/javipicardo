# Star Trek: Starfleet Command (Gold Edition) — Hotkeys y config de video

Fuente: manuales oficiales de la **Gold Edition**, provistos por el usuario, ubicados
en `manuals/`:
- `SFCfullMan.pdf` — Manual completo (Gameplay Manual & Reference Guide), sección
  "COMPREHENSIVE HOTKEY LIST", págs. 156-159.
- `Supplemental Manual.pdf` — Notas adicionales v1.02, incluye la explicación del
  archivo `SFC.INI` (pág. 6-7), clave para el tema de modo ventana/pantalla completa.
- `SFCquick.pdf` — Manual de instalación/quickstart (coincide con las hotkeys del
  manual completo).
- `Updated Ship Data.pdf` — Solo tablas de estadísticas de naves, sin hotkeys.

Nota: reemplaza la versión anterior de este documento, que estaba basada en el
manual genérico de SFC2 (`sfc2.pdf`, ya no presente en `manuals/`). La Gold Edition
es SFC1 + expansiones (Empires at War / Neutral Zone), y esta es ahora la fuente
oficial y específica de la edición instalada.

Estos son los bindings **por defecto**; el juego permite remaparlos desde el menú
Options → Hotkeys.

## ⚙️ Configuración de video/ventana — `SFC.INI` (relevante para la Fase 0 del roadmap)

Según el Supplemental Manual, el archivo `SFC.INI` (carpeta de instalación del
juego) tiene una sección `[3D]` con el setting que buscábamos:

```ini
[3D]
wireframe=0   ; 0: hardware-acceleration, 1: software rendered mode
windowed=0    ; 0: deshabilitado, 1: si la resolución del juego es MENOR a la del
              ;    escritorio, el juego correrá en una ventana
zbuffer=1     ; 0: deshabilitado, 1: habilitado (Z-buffering)
lowres=3      ; 0: 800x600, 1: 640x480, 2: resolución rara, 3: 1024x768, 4: 1200x800
backdrop=1    ; 0: deshabilitado, 1: fondo habilitado
```

**Importante:** para lograr modo ventana según el manual, no alcanza con poner
`windowed=1` — la **resolución del juego (`lowres`) tiene que ser menor a la
resolución del escritorio de Windows**. Ej: si el escritorio está en 1920x1080,
configurar `lowres=3` (1024x768) + `windowed=1` debería forzar modo ventana.

Pasos sugeridos para la Fase 0 del roadmap:
1. Ubicar `SFC.INI` en la carpeta de instalación del juego.
2. Hacer backup del archivo antes de tocarlo (recomendado explícitamente por el
   manual).
3. Editar `windowed=1` y `lowres=3` (o un valor de resolución menor al del
   escritorio).
4. Guardar, abrir el juego y confirmar visualmente que corre en ventana.

Otros settings interesantes del `.ini` (sección `[UI]`):
- `OrderDelay=30` — controla el delay entre el clic del mouse y la respuesta de la
  nave, en milisegundos. Relevante para entender la latencia base del juego mismo,
  aparte de la latencia que agreguemos con el pipeline de voz.

## Cámara / UI
| Tecla | Acción |
|---|---|
| ESC | Salir de la misión (End Mission) |
| F1 | Cámara Overhead |
| F2 | Cámara Chase |
| F3 | Cámara Follow (default) |
| F4 | Cámara Enemy |
| F5 | Toggle Target Padlock |
| F6 / F7 / F8 | Saltar a nave #1 / #2 / #3 |
| F9 / F10 / F11 | HUD info mínima / normal / máxima |
| ` (backtick) | Target al enemigo más cercano |
| TAB | Panel de mapa táctico |
| 9 | Panel de control de flota (Fleet Control Panel) |
| D | Deslizar la barra de interfaz dentro/fuera de la pantalla |
| O | Cambiar displays esquemáticos |
| \[ / \] | Velocidad de juego más lenta / más rápida |
| PAUSE | Pausar y dar órdenes (solo un jugador) |
| HOME | Mover cámara a la derecha |
| END | Mover cámara a la izquierda |
| PAGE UP / PAGE DOWN | Inclinar cámara arriba / abajo |

## Movimiento / Velocidad (lo más relevante para el control por voz)
| Tecla | Acción |
|---|---|
| **S** | **Acelerar (Speed Up)** — incrementa la velocidad deseada un paso |
| **A** | **Desacelerar (Slow Down)** — reduce la velocidad deseada un paso |
| Numpad 0 | Emergency Deceleration (frenado de emergencia) |
| Numpad 5 | Start HET (High Energy Turn) |
| Numpad – | Orbit Target — ✅ confirmado en el juego (17/09) |
| Numpad / | Erratic Maneuvers — ⚠️ ver condiciones abajo |
| Numpad * | Follow Target |

### ✅ Orbit Target: era Numpad `–`, el quickstart está mal

Los dos manuales decían teclas distintas: `SFCfullMan.pdf` pág. 159 daba
Numpad **`–`** (`subtract`) y `SFCquick.pdf` pág. 24 daba Numpad **`.`**
(`decimal`). **Probado en el juego el 17/09: `subtract` orbita.** Vale la
pág. 159; la del quickstart es errata. El parser lo tiene en la constante
`TECLA_ORBITAR` de `fase1_text_commands.py`.

**Corolario importante:** con Orbit (`–`) y Follow (`*`) los dos confirmados,
queda probado que **las teclas del numpad sí llegan al juego** vía
`pydirectinput`. O sea que si "maniobras evasivas" (`/`) no hace nada, **no es
un problema de que la tecla no llegue** — es por las condiciones de EM
(energía de movimiento, camuflaje) que se documentan abajo.

### ⚠️ Erratic Maneuvers: por qué puede "no hacer nada"

Del `SFCfullMan.pdf` pág. 102 y 140 — la tecla puede llegar bien y la nave no
hacer nada visible, porque EM tiene condiciones:

- **Cuesta 6 puntos de energía de movimiento.** Si la nave no tiene energía de
  sobra (por ejemplo a toda máquina, con todo comprometido), no engancha.
- **No se puede usar junto con el camuflaje** (pág. 140): son excluyentes.
- **El efecto no es un zigzag llamativo**: son "small, swift course changes".
  Lo que sí se nota son las restricciones que impone — no se pueden lanzar
  shuttles, fighters, misiles ni torpedos de plasma, no se pueden tirar minas
  ni usar transportadores/rayos tractores, la tasa de giro baja en 1, y los
  HET fallan ~17% más seguido.
- **Para apagarlo hay que clickear "Normal Maneuvering"** en el Helm MFD
  (ítem 12 de la pág. 9 del `SFCquick.pdf`): **no tiene hotkey**. O sea que
  por voz se puede prender pero *no* apagar — tenerlo en cuenta antes de
  meterlo en un combo.

> Igual que documentamos antes: no hay un valor numérico fijo de "velocidad máxima"
> en el manual — depende de la nave. S/A incrementan o decrementan de a un paso por
> pulsación. Para "media máquina" hay que conocer/inferir la velocidad máxima de la
> nave actual y contar pasos (o leer el HUD por OCR). Ver README sección 2.5 y
> ROADMAP Fase 3.

## Armas
| Tecla | Acción |
|---|---|
| 1-4 | Seleccionar grupo de armas # |
| CTRL + 1-4 | Configurar grupo de armas # |
| 5-8 | Seleccionar target desde memoria |
| CTRL + 5-8 | Guardar target actual en memoria |
| Z | Disparar (una descarga por cada hardpoint) |
| SHIFT + Z | Alpha Strike (disparar todo a la vez) |
| T | Ciclar entre targets |
| SHIFT + T | Ciclar entre targets (orden inverso) |
| Y | Ciclar entre targets enemigos |
| SHIFT + Y | Ciclar entre targets enemigos (orden inverso) |
| SPACE | Target al arma buscadora hostil más cercana |
| \\ | Deseleccionar target |
| P | Disparar sonda (Probe) |
| I | Toggle Deep Scan |

## Escudos / Defensa
| Tecla | Acción |
|---|---|
| K | Panel de escudos |
| L | Panel de defensa |
| C | Máxima tracción defensiva (Max Defensive Tractor) |
| V | Máximo Point Defense |
| Numpad 1 | Reforzar escudo Aft Left |
| Numpad 2 | Reforzar escudo Aft |
| Numpad 3 | Reforzar escudo Aft Right |
| Numpad 4 | Reforzar escudo Left |
| Numpad 6 | Reforzar escudo Right |
| Numpad 7 | Reforzar escudo Forward Left |
| Numpad 8 | Reforzar escudo Forward |
| Numpad 9 | Reforzar escudo Forward Right |

## Guerra electrónica / Energía / Sistemas
| Tecla | Acción |
|---|---|
| F | ECM máximo |
| G | ECCM máximo |
| H | Panel de sensores (ECM/ECCM) |
| J | Panel de tracción (Tractor) |
| ; | Panel de reparación |
| ' | Panel del Helm (timón) |
| N | Panel de transporte |
| , | Panel de shuttles |
| . | Panel de energía |
| / | Panel de preferencias |
| X | Toggle Cloak (camuflaje) |

## Alertas
| Tecla | Acción |
|---|---|
| R | Red Alert! |

**Yellow Alert: existe en el juego, pero NO tiene tecla.** La pág. 101 del
`SFCfullMan.pdf` confirma que hay tres botones de alerta en el HUD (GREEN,
YELLOW y RED ALERT), con esta diferencia funcional:
- **RED ALERT** → sube escudos **y** arma todas las armas.
- **YELLOW ALERT** → sube escudos solamente. El manual recomienda usarlo "en
  situaciones desconocidas o peligrosas", y pasar a Red Alert antes de entrar
  en combate.

Como solo Red Alert aparece en la lista de hotkeys (pág. 157), Yellow/Green
Alert hoy únicamente se pueden clickear. Ver `NO_SOPORTADO` en
`scripts/fase1_text_commands.py`.

## Seguir / perseguir a una nave determinada

El juego **no permite identificar una nave por nombre**, pero sí combinar
targeting + memoria para seguir a una nave concreta y volver a ella:

| Tecla | Acción |
|---|---|
| T / SHIFT+T | Ciclar entre **todos** los targets (adelante / atrás) |
| Y / SHIFT+Y | Ciclar **solo entre enemigos** (adelante / atrás) |
| ` | Target al enemigo más cercano |
| 5 – 8 | **Seleccionar** target guardado en memoria (4 ranuras) |
| CTRL + 5 – 8 | **Guardar** el target actual en esa ranura de memoria |
| \\ | Deseleccionar target |
| Numpad * | **Follow Target** — perseguir al target actual |
| Numpad – | **Orbit Target** — orbitar alrededor del target |

**Flujo recomendado por voz** (implementado en la Fase 1):

1. `"siguiente enemigo"` (`Y`) → ciclar hasta la nave deseada.
2. `"guardar objetivo uno"` (`CTRL+5`) → memorizarla.
3. …combate, se cambia de target varias veces…
4. `"objetivo uno"` (`5`) → volver a seleccionar **esa misma** nave.
5. `"seguir a esa nave"` (`Numpad *`) → perseguirla.

**Intercept Target: existe pero NO tiene hotkey.** La pág. 103 lo documenta
como orden del Helm Officer ("el oficial de timón toma el control e intenta
interceptar al target actual"), pero no figura en la lista de teclas — se da
con el mouse desde el MFD del Helm. Alternativas por teclado: Follow Target u
Orbit Target.

### ✅ Follow Target (Numpad `*`): VIRA LA NAVE — confirmado en el juego

**Confirmado empíricamente (prueba del 13/09): `Numpad *` hace que la nave
gire hacia el objetivo seleccionado y lo persiga.** No es solo seguimiento de
cámara.

Hubo que verificarlo en el juego porque **el manual nunca lo describe**: se
revisaron los tres PDFs completos y `Numpad * Follow Target` aparece
únicamente en la tabla de hotkeys (pág. 159), sin explicación en el cuerpo del
manual — la única maniobra en esa situación:

| Acción | ¿Descrita en el manual? | ¿En el Helm MFD? |
|---|---|---|
| Orbit Target | ✅ Sí (pág. 103) | ✅ Sí (ítem 10) |
| Intercept Target | ✅ Sí (pág. 103) | ✅ Sí (ítem 11) |
| Erratic Maneuvers | ✅ Sí (pág. 102) | ✅ Sí (ítem 2) |
| **Follow Target** | ❌ No aparece | ❌ No está |

**Por qué esto es importante para el proyecto:** es el **único comando por
teclado que apunta la nave hacia un objetivo**, sin depender del mouse sobre
la vista táctica. Eso lo convierte en la herramienta de movimiento más útil
que tenemos por voz, y reduce bastante la urgencia de la Fase 6 (control de
rumbo por click), que era la forma prevista de resolver el direccionamiento.

Los combos `ir_al_mas_cercano` e `ir_a_cualquiera` se apoyan en esta tecla.

## Shuttles / Misceláneos
| Tecla | Acción |
|---|---|
| Q | Lanzar Suicide Shuttle |
| W | Lanzar Wild Weasel |
| E | Lanzar Scatterpack |
| M | Soltar mina |
| SHIFT + M | Soltar NSM (mina especial, solo Romulanos) |
| B | Colocar Transporter Bomb |

## Comunicaciones / Multijugador
| Tecla | Acción |
|---|---|
| 0 | Panel de Comunicaciones |
| ENTER | Chat Toggle |
| CTRL + ENTER | Chat Toggle (mensaje de equipo) |
| BACKSPACE | Saltar rápido a la nave del jugador target |

---

**Diferencias notadas vs. la versión anterior de este documento** (basada en el
manual genérico de SFC2, ya no usado):
- `HOME`/`END` acá mueven la cámara a la derecha/izquierda (antes decía sentido
  horario/antihorario — redactado distinto en cada manual, mismo tipo de acción).
- `9` es Fleet Control Panel en esta edición (no aparecía en la lista anterior).
- `SHIFT+M` acá es "Drop NSM (Romulans only)" en vez de "mina nuclear" genérica.
- No se lista una tecla de Yellow Alert explícita en este manual (a confirmar en
  el juego real).
- Movement/velocidad (S/A) y disparo (Z/Shift+Z) coinciden en ambas fuentes.
