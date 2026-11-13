# Manual de comandos — SFC Voice Commander

> Generado por `scripts/generar_manual.py` a partir de los diccionarios del parser. No editar a mano: agregar el sinónimo en `fase1_text_commands.py` y volver a generar.

## Cómo se habla

- **Primero el nombre, después la orden.** Toda orden empieza llamando a alguien: *«computadora, alerta roja»*, *«artillero, fuego»*, *«timonel, media máquina»*. Sin nombre no se ejecuta nada: así la charla del puente no dispara teclas.
- **La computadora atiende todo.** Si no sabés a quién le toca, llamala a ella. Igual contesta, con su voz y su retrato, el oficial del puesto de la orden.
- **Se llama por el puesto, no por el nombre propio.** El detector local (Vosk) no conoce *Korak*, *Zheva* ni *T'Lara*: decí *artillero*, *defensa* o *timonel*. Los nombres propios sólo sirven en los modos de fase 2.
- **Varias órdenes en una frase:** *«computadora, alerta roja y media máquina»*. Se ejecutan en orden; como mucho 5 por frase.
- **Lenguaje libre:** con el agente (`fase3_agente_voz.py`) no hace falta la frase exacta: *«poné la alarma y tirale con todo»* también anda. Las frases de abajo son las que el parser reconoce al instante y sin costo.
- **Si dudás, pregunta:** una palabra suelta como *«máquina»* o *«velocidad»* no se adivina; te pregunta cuál.

## La tripulación

| Puesto | Oficial | Se lo llama |
|---|---|---|
| Timón | T'Lara | *timonel*, *piloto*, *alferez*, *lara*, *t lara*, *tlara* |
| Armas | Korak | *artillero*, *armas*, *korak* |
| Defensa | Zheva | *defensa*, *tactico*, *zheva* |
| Ciencias | Delon | *ciencias*, *cientifico*, *delon* |
| Computadora | Computadora | *computadora* |

Ingeniería, seguridad y comunicaciones todavía no tienen comandos.

## Timón: velocidad y maniobras (T'Lara)

### Detener

Ajustar velocidad a nivel 0 de 4 (detener). Tecla: `A` × 11 (frena hasta 0).

«alto total» · «parar» · «detener» · «pare maquinas» · «parada de emergencia» · «frenar» · «frena» · «pare la nave» · «detene la nave» · «motores a cero»

### Cuarto maquina

Ajustar velocidad a nivel 1 de 4 (cuarto maquina). Tecla: `S` × 2 desde parado.

«cuarto de maquina» · «un cuarto de maquina» · «un cuarto» · «a cuarto de maquina»

### Media maquina

Ajustar velocidad a nivel 2 de 4 (media maquina). Tecla: `S` × 4 desde parado.

«media maquina» · «mitad de maquina» · «mitad» · «a media maquina» · «mitad de potencia» · «media potencia»

### Tres cuartos maquina

Ajustar velocidad a nivel 3 de 4 (tres cuartos maquina). Tecla: `S` × 6 desde parado.

«tres cuartos de maquina» · «tres cuartos» · «a tres cuartos de maquina»

### Toda maquina

Ajustar velocidad a nivel 4 de 4 (toda maquina). Tecla: `S` × 8 desde parado.

«toda maquina» · «maxima velocidad» · «maxima» · «avante toda» · «velocidad maxima» · «a toda maquina» · «a todo motor» · «maxima potencia» · «toda velocidad» · «a toda velocidad» · «aceleren al maximo»

### Seguir target

Seguir automaticamente a la nave/objetivo seleccionado. Tecla: `*` del teclado numérico.

«seguir a esa nave» · «seguir la nave» · «seguir nave» · «seguir a la amenaza» · «seguir amenaza» · «seguir al objetivo» · «seguir objetivo» · «seguir target» · «sigan a esa nave» · «sigan la nave» · «persigan a esa nave» · «perseguir nave» · «seguir enemigo» · «seguir al enemigo» · «seguir a ese enemigo» · «perseguir al enemigo» · «persigan al enemigo»

### Orbitar objetivo

Poner la nave en orbita alrededor del objetivo. Tecla: `-` del teclado numérico.

«orbitar» · «orbitar objetivo» · «ponerse en orbita» · «orbiten la nave» · «orbitar la nave» · «pone en orbita» · «orbita el objetivo» · «girar alrededor del objetivo» · «dar vueltas alrededor»

### Maniobras evasivas

Maniobras erraticas: +4 de ECM natural, a costa de nuestra punteria y de no poder lanzar shuttles/minas/torpedos. Tecla: `/` del teclado numérico.

«maniobras evasivas» · «maniobra evasiva» · «evasivas» · «zigzag» · «maniobras erraticas» · «esquiven» · «zigzaguear» · «maniobras de evasion» · «muevanse en zigzag»

### Retirada maxima

Acelera a máxima velocidad (no gira la nave). Tecla: `S` × 8.

«alejense a maxima velocidad» · «alejarse a maxima velocidad» · «retirada a maxima velocidad» · «huyan a maxima velocidad»

### Ir al mas cercano

Selecciona el enemigo MAS CERCANO, pone rumbo hacia él y acelera a 3/4 de máquina. Tecla: `` ` `` (a la izquierda del 1), después `*` del teclado numérico, después `S` × 6.

«vamos al enemigo mas cercano» · «al enemigo mas cercano» · «vamos por el mas cercano» · «atacar al mas cercano» · «ir al enemigo mas cercano» · «vayan al mas cercano» · «acercarse al enemigo mas cercano»

### Ir a cualquiera

Busca un enemigo (el siguiente del ciclo), pone rumbo hacia él y acelera a 3/4 de máquina. Tecla: `Y`, después `*` del teclado numérico, después `S` × 6.

«busca un enemigo» · «busquen un enemigo» · «buscar enemigo» · «vamos por cualquiera» · «atacar a cualquiera» · «vamos por otro enemigo» · «busca otro enemigo» · «elegi un enemigo» · «buscar un objetivo» · «ir a enemigo» · «ir al enemigo» · «vamos por un enemigo»

### Velocidad en porcentaje

*«velocidad al 70 por ciento»*, *«velocidad 40%»*: se redondea al cuarto más cercano (0, 25, 50, 75 o 100%).

> Las órdenes de velocidad mandan una cantidad fija de pulsaciones, calculada desde parado (8 hasta la máxima, `PASOS_HASTA_MAXIMA`, depende de la nave). Si la nave ya se movía, se suman: para un nivel exacto, primero *«alto total»*.

## Armas: disparo y objetivos (Korak)

### Disparar

Disparar armas (una descarga). Tecla: `Z`.

«disparar» · «fuego» · «abran fuego» · «dispare» · «disparen» · «tiren» · «hagan fuego» · «fuego al blanco» · «disparenle»

### Siguiente objetivo

Ciclar al siguiente objetivo disponible. Tecla: `T`.

«siguiente objetivo» · «cambiar de blanco» · «cambiar objetivo» · «proximo objetivo»

### Objetivo mas cercano

Seleccionar como objetivo al enemigo mas cercano. Tecla: `` ` `` (a la izquierda del 1).

«objetivo mas cercano» · «enemigo mas cercano» · «apunten al mas cercano» · «target mas cercano» · «blanco mas cercano» · «marca al mas cercano» · «apunta al mas cercano»

### Siguiente enemigo

Ciclar al siguiente enemigo, salteando unidades no hostiles. Tecla: `Y`.

«siguiente enemigo» · «proximo enemigo» · «otro enemigo» · «cambiar de enemigo» · «siguiente nave enemiga» · «pasa al siguiente enemigo» · «otra nave enemiga»

### Deseleccionar objetivo

Soltar el objetivo seleccionado, sin elegir otro. Tecla: `\`.

«deseleccionar objetivo» · «deseleccionar a objetivo» · «deseleccionar el objetivo» · «deseleccionar target» · «soltar objetivo» · «soltar el objetivo» · «cancelar objetivo» · «olvidar objetivo»

### Alpha strike

Disparar todas las armas de todos los hardpoints a la vez. Tecla: `Shift` + `Z`.

«alpha strike» · «fuego total» · «disparen todo» · «todas las armas» · «fuego a discrecion»

### Enemigo anterior

Ciclar hacia atras entre enemigos, volver al anterior. Tecla: `Shift` + `Y`.

«enemigo anterior» · «volver al enemigo anterior»

### Objetivo anterior

Ciclar hacia atras entre objetivos, volver al anterior. Tecla: `Shift` + `T`.

«objetivo anterior» · «volver al objetivo anterior» · «blanco anterior»

### Seleccionar objetivo memorizado 1

Volver a seleccionar la nave guardada en la ranura de memoria 1. Tecla: `5`.

«objetivo uno» · «objetivo 1» · «primer objetivo»

### Seleccionar objetivo memorizado 2

Volver a seleccionar la nave guardada en la ranura de memoria 2. Tecla: `6`.

«objetivo dos» · «objetivo 2» · «segundo objetivo»

### Seleccionar objetivo memorizado 3

Volver a seleccionar la nave guardada en la ranura de memoria 3. Tecla: `7`.

«objetivo tres» · «objetivo 3» · «tercer objetivo»

### Seleccionar objetivo memorizado 4

Volver a seleccionar la nave guardada en la ranura de memoria 4. Tecla: `8`.

«objetivo cuatro» · «objetivo 4» · «cuarto objetivo»

### Guardar objetivo en memoria 1

Guardar el objetivo actual en la ranura de memoria 1, para volver a el mas tarde. Tecla: `Ctrl` + `5`.

«guardar objetivo uno» · «memorizar objetivo uno»

### Guardar objetivo en memoria 2

Guardar el objetivo actual en la ranura de memoria 2, para volver a el mas tarde. Tecla: `Ctrl` + `6`.

«guardar objetivo dos» · «memorizar objetivo dos»

### Guardar objetivo en memoria 3

Guardar el objetivo actual en la ranura de memoria 3, para volver a el mas tarde. Tecla: `Ctrl` + `7`.

«guardar objetivo tres» · «memorizar objetivo tres»

### Guardar objetivo en memoria 4

Guardar el objetivo actual en la ranura de memoria 4, para volver a el mas tarde. Tecla: `Ctrl` + `8`.

«guardar objetivo cuatro» · «memorizar objetivo cuatro»

### Ataque total

Maximiza ECM y dispara Alpha Strike (todas las armas). Tecla: `F`, después `Shift` + `Z`.

«ataquen con todo» · «ataque total» · «todo el poder de fuego» · «usen todas las armas» · «fuego con todo»

### Armas carga normal

Saca el overload: armas pesadas en carga normal. Tecla: `Insert`.

«sin sobrecarga» · «quitar sobrecarga» · «sacar sobrecarga» · «carga normal» · «armas en modo normal» · «armas normales»

### Sobrecargar armas

Pone las armas pesadas en overload: mas daño, alcance maximo 8. Tecla: `U`.

«sobrecargar armas» · «sobrecarguen las armas» · «armas en sobrecarga» · «sobrecarguen» · «sobrecarga» · «overload»

## Defensa: alertas, escudos y camuflaje (Zheva)

### Red alert

Activar alerta roja. Tecla: `R`.

«alerta roja» · «roja» · «red alert» · «codigo rojo» · «condicion roja» · «a sus puestos de combate» · «zafarrancho de combate» · «alerta de combate»

### Escudos maximo

Abrir panel de escudos / reforzar escudos. Tecla: `K`.

«escudos al maximo» · «escudos a maximo» · «reforzar escudos» · «refuercen escudos» · «maximo escudo» · «subir escudos» · «levantar escudos» · «escudos arriba» · «arriba los escudos» · «potencia a los escudos» · «todo a los escudos» · «escudos al maximo nivel» · «maxima proteccion»

### Camuflaje

Activar/desactivar camuflaje. Tecla: `X`.

«camuflaje» · «cloaking» · «activar camuflaje» · «modo sigilo» · «ocultarnos» · «escondannos» · «activar sigilo» · «modo invisible» · «camuflense» · «volvernos invisibles»

## Ciencias: sensores (Delon)

### Deep scan

Activar/desactivar deep scan. Tecla: `I`.

«escaneo profundo» · «deep scan» · «escanear» · «escanea» · «escaneen» · «rastreo profundo» · «analisis profundo» · «escaneo a fondo»

## Comandos que esperan una tecla

El juego no les asigna tecla por defecto. Asignales una en **Options → hotkeys** del juego y ponela en la constante de `fase1_text_commands.py`; hasta entonces, decirlos avisa y no hace nada.

### Yellow Alert

Sube escudos sin armar las armas. Constante: `TECLA_YELLOW_ALERT`.

«alerta amarilla» · «yellow alert» · «amarilla» · «condicion amarilla» · «codigo amarillo»

## Otros

- **Ayuda:** «que comandos hay» · «ayuda» · «que puedo decir» · «lista de comandos» · «mostrar comandos» · «help» — lista los comandos en la consola.
- **Llamar sin orden:** decir sólo el nombre (*«computadora»*) hace que conteste *«¿Sí, capitán?»* y espere.
- **Salir:** `Esc` en los modos de fase 2; `Ctrl+C` en el agente.

## Jugadas útiles

- **Perseguir a una nave concreta:** *«artillero, siguiente enemigo»* hasta que sea la que querés → *«artillero, guardar objetivo uno»* → en cualquier momento *«artillero, objetivo uno»* y *«timonel, seguir a esa nave»*.
- **Entrar al combate:** *«computadora, alerta roja y vamos al enemigo más cercano»*.
- **Golpe fuerte de cerca:** *«computadora, ataquen con todo»* (máximo ECM y Alpha Strike).
- **Salir del fuego:** *«timonel, maniobras evasivas»* (+4 de ECM, a costa de nuestra puntería) o *«timonel, aléjense a máxima velocidad»*.
