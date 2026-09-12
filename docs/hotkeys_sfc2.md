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
| Numpad – | Orbit Target |
| Numpad / | Erratic Maneuvers |
| Numpad * | Follow Target |

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

(No aparece una tecla dedicada a Yellow Alert en esta lista de la Gold Edition;
a confirmar en el juego si existe o si se maneja desde algún panel.)

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
