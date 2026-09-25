"""
Panel web minimo: muestra el retrato del oficial que acaba de contestar, con
su frase y el comando que la disparo.

Es la version mas chica posible del "cliente browser + server Python" que pidio
Pato: un server de la libreria estandar (sin instalar NADA) y una pagina que
pregunta el estado cada 300ms. No decide nada sobre la arquitectura final -si
se va a Realtime, esto se tira y no se perdio nada- pero ya se puede mostrar
funcionando al lado del juego.

COMO USAR
---------
Arranca solo junto con fase1 o fase2. Al iniciar imprime la URL:
    http://127.0.0.1:8765
Abrila en el browser y ponela al lado de la ventana del juego.

Para apagarlo: PANEL_WEB = False en oficiales.py.

SEGURIDAD: escucha solo en 127.0.0.1, no en la red.
"""

import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = 8765
_AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_IMAGENES = os.path.join(_AQUI, "..", "images", "oficiales")
DIR_AUDIO = os.path.join(_AQUI, "..", "audio", "oficiales")

# Cuantos segundos sin que la pagina pregunte el estado para darla por cerrada.
# Sirve para saber si hay alguien escuchando: si lo hay, el audio lo reproduce
# el browser; si no, lo reproduce Python (ver oficiales.reproducir).
SEGUNDOS_BROWSER_VIVO = 3.0

# Como se activa el boton de hablar:
#   False -> mantener apretado con el mouse (click)
#   True  -> con solo pasar el mouse por encima, sin click
#
# El hover tiene una ventaja concreta: NO le roba el foco al juego, y un click
# si. La contra es que el mouse cruza el boton yendo a otro lado, asi que se
# usan dos retardos (ver ESPERA_* abajo) para que un cruce al pasar no dispare
# una grabacion.
ACTIVAR_POR_HOVER = True

# Cuanto hay que quedarse encima ANTES de empezar a grabar. Filtra los cruces
# de paso.
ESPERA_PARA_ENTRAR_MS = 250

# Cuanto se sigue grabando despues de salirse. Evita que un temblor de mano te
# corte la frase por la mitad.
ESPERA_PARA_SALIR_MS = 350

# Ultimo estado publicado. Lo lee el handler desde otro thread, por eso el lock.
_estado = {"oficial": None, "nombre": None, "frase": None, "comando": None,
           "audio": None, "uniforme": None, "velocidad": None, "tecla": None,
           "ts": 0, "boton": False, "mic_web": False,
           "hover": ACTIVAR_POR_HOVER,
           "espera_entrar": ESPERA_PARA_ENTRAR_MS,
           "espera_salir": ESPERA_PARA_SALIR_MS}
_lock = threading.Lock()
_servidor = None
_ultimo_poll = 0.0

# True mientras el capitan mantiene apretado el boton de hablar de la pagina.
# Lo usa la Fase 2 en modo "boton", en lugar de la tecla fisica.
_boton = False


def boton_apretado():
    return _boton


# Frases que mando la pagina cuando el microfono vive en el browser
# (MODO_ESCUCHA = "web"). Cada item es (muestras_float32_bytes, sample_rate).
_frases_web = queue.Queue()


def proxima_frase(timeout=0.5):
    """Devuelve la proxima frase que mando la pagina, o None si no hay."""
    try:
        return _frases_web.get(timeout=timeout)
    except queue.Empty:
        return None


def publicar(oficial, nombre, frase, comando, audio=None, uniforme=None,
             velocidad=None, tecla=None):
    """La llama oficiales.responder() cada vez que contesta alguien. `audio` es
    el nombre del wav y `uniforme` el color de division, que la pagina usa como
    color de acento del LCARS.

    `velocidad` es el nivel 0-4 que se acaba de ORDENAR, o None si esta orden no
    era de velocidad. Se guarda pegajoso: la consola muestra lo ultimo que se
    pidio. OJO que es lo ORDENADO, no lo que la nave realmente tiene - eso no
    lo sabemos sin leer el HUD (Fase 3)."""
    with _lock:
        _estado.update({"oficial": oficial, "nombre": nombre, "frase": frase,
                        "comando": comando, "ts": time.time(),
                        "uniforme": uniforme,
                        "tecla": tecla,
                        "audio": f"/audio/{audio}" if audio else None})
        if velocidad is not None:
            _estado["velocidad"] = velocidad


def mostrar_boton(si=True):
    """La Fase 2 avisa si esta en modo boton, para que la pagina lo muestre."""
    with _lock:
        _estado["boton"] = bool(si)


def pedir_microfono(si=True):
    """La Fase 2 avisa que el microfono lo maneja la pagina (modo "web")."""
    with _lock:
        _estado["mic_web"] = bool(si)


def hay_browser():
    """True si una pagina pregunto el estado hace poco. Con eso se decide quien
    reproduce el audio, para no escucharlo dos veces."""
    return (time.time() - _ultimo_poll) < SEGUNDOS_BROWSER_VIVO


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>LCARS · Puente</title>
<style>
  /* LCARS (el estilo de las consolas de TNG). Sin fuentes de internet: se usa
     la pila condensada que Windows ya trae, para que la pagina ande offline. */
  :root {
    --negro:#000; --durazno:#ff9966; --melon:#ffcc99; --lila:#cc99cc;
    --azul:#9999cc; --manteca:#ffcc66; --ladrillo:#cc6666; --celeste:#99ccff;
    --acento:var(--durazno);
  }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; background:var(--negro); color:var(--melon);
         font-family:"Antonio","Oswald","Arial Narrow",Haettenschweiler,
                     "Franklin Gothic Medium",sans-serif;
         text-transform:uppercase; letter-spacing:.08em; }

  /* Alto fijo y filas explicitas: la barra del boton es una fila propia, asi
     que NO puede quedar tapada aunque el contenido del medio crezca (que fue
     el bug del 25/09). Lo que scrollea, si hace falta, es solo el centro. */
  .lcars { display:grid; grid-template-columns:186px 1fr; gap:10px;
           height:100vh; padding:10px 14px 10px 10px; }

  /* --- panel principal: la columna izquierda --- */
  .izq { display:flex; flex-direction:column; gap:8px; min-height:0; }
  .codo { height:96px; background:var(--acento); border-radius:64px 0 0 0;
          position:relative; flex:none; transition:background .4s; }
  .codo::after { content:""; position:absolute; right:-10px; bottom:0;
                 width:10px; height:30px; background:var(--acento);
                 transition:background .4s; }
  .bloque { padding:.45rem .7rem; text-align:right; font-size:.8rem;
            color:#000; line-height:1.05; flex:none; }
  .b1 { background:var(--lila); height:52px; }
  .b2 { background:var(--azul); height:86px; }
  .b3 { background:var(--manteca); height:40px; }
  .b4 { background:var(--ladrillo); height:40px; }
  .b5 { background:var(--celeste); height:34px; }
  .relleno { flex:1; min-height:8px; background:#161616;
             border-radius:0 0 0 24px; }

  /* Titilar: son luces de actividad, no botones de verdad. */
  @keyframes titilar { 0%,100% { opacity:1 } 50% { opacity:.22 } }
  .titila { animation:titilar 2.6s ease-in-out infinite; }
  .luces { display:grid; grid-template-columns:1fr 1fr 1fr; gap:5px;
           flex:none; }
  .luz { height:22px; border-radius:11px; }
  .luz:nth-child(1) { background:var(--durazno); animation-duration:2.1s; }
  .luz:nth-child(2) { background:var(--lila);    animation-duration:3.3s;
                      animation-delay:.4s; }
  .luz:nth-child(3) { background:var(--manteca); animation-duration:1.7s;
                      animation-delay:.9s; }
  .luz:nth-child(4) { background:var(--celeste); animation-duration:2.9s;
                      animation-delay:.2s; }
  .luz:nth-child(5) { background:var(--ladrillo);animation-duration:2.3s;
                      animation-delay:1.1s; }
  .luz:nth-child(6) { background:var(--azul);    animation-duration:3.7s;
                      animation-delay:.6s; }

  /* El boton de hablar: ultimo bloque del panel principal. */
  #hablar { flex:none; height:112px; border:none; border-radius:0 0 0 64px;
            background:var(--durazno); color:#000; font-family:inherit;
            font-size:1.02rem; line-height:1.15; letter-spacing:.1em;
            text-transform:uppercase; cursor:pointer; text-align:right;
            padding:.6rem .8rem; user-select:none; -webkit-user-select:none;
            transition:background .15s; }
  #hablar:hover { background:var(--melon); }
  /* En modo hover el borde avisa que el boton esta "armado". */
  #hablar[data-hover="1"] { outline:2px dashed var(--melon); outline-offset:-6px; }
  #hablar[data-hover="1"].grabando { outline-color:#fff; }
  #hablar.grabando { background:var(--ladrillo); color:#fff;
                     animation:titilar 1s ease-in-out infinite; }
  #hablar.oculto { display:none; }

  /* --- columna derecha --- */
  .der { display:grid; grid-template-rows:auto 1fr; gap:10px; min-height:0;
         min-width:0; }
  .barra { display:flex; gap:8px; align-items:center; }
  .barra .tira { flex:1; height:32px; background:var(--acento);
                 border-radius:0 32px 32px 0; transition:background .4s; }
  .barra .rot { font-size:1rem; color:var(--acento); white-space:nowrap;
                transition:color .4s; }

  .centro { display:grid; grid-template-columns:auto 1fr 200px; gap:18px;
            align-items:center; min-height:0; overflow:auto; }
  @media (max-width:980px) { .centro { grid-template-columns:auto 1fr; }
                             .consola { display:none; } }
  @media (max-width:620px) { .centro { grid-template-columns:1fr; }
                             .lcars { grid-template-columns:120px 1fr; } }

  .marco { position:relative; width:min(34vw,32vh,240px); aspect-ratio:1;
           border-radius:14px; overflow:hidden; background:#0a0a0a;
           border:4px solid var(--acento); transition:border-color .4s; }
  .marco img { width:100%; height:100%; object-fit:cover; display:block;
               opacity:0; transition:opacity .35s; }
  .marco img.visible { opacity:1; }
  .vacio { position:absolute; inset:0; display:grid; place-items:center;
           color:#3a3a3a; font-size:.78rem; padding:1rem; text-align:center; }

  .datos { min-width:0; }
  .nombre { font-size:2.5rem; line-height:1; color:var(--acento);
            transition:color .4s; }
  .rol { font-size:.82rem; color:var(--lila); margin-top:.3rem; }
  .frase { margin-top:1rem; font-size:1.3rem; line-height:1.3;
           color:var(--melon); text-transform:none; letter-spacing:.02em;
           min-height:2.6em; }
  #micestado { font-size:.7rem; color:#6b6b6b; margin-top:.6rem; }

  /* --- consola de la nave --- */
  .consola { display:flex; flex-direction:column; gap:6px; }
  .consola svg { width:100%; height:auto; display:block; }
  .nave-linea { fill:none; stroke:var(--acento); stroke-width:2.2;
                stroke-linejoin:round; transition:stroke .4s; }
  .nave-relleno { fill:var(--acento); opacity:.16; transition:fill .4s; }
  .nave-tenue { fill:none; stroke:var(--acento); stroke-width:1;
                opacity:.5; stroke-linecap:round; transition:stroke .4s; }

  /* Lecturas: bloques LCARS con lo ULTIMO QUE MANDAMOS. */
  .lectura { display:grid; grid-template-columns:76px 1fr; gap:4px;
             align-items:stretch; }
  .lectura .et { background:var(--azul); color:#000; font-size:.62rem;
                 padding:.3rem .4rem; text-align:right;
                 border-radius:12px 0 0 12px; }
  .lectura .va { background:#161616; color:var(--manteca); font-size:.74rem;
                 padding:.3rem .5rem; border-radius:0 12px 12px 0;
                 overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .tit-consola { font-size:.66rem; color:var(--lila); margin-top:.4rem; }

  #sonido { position:fixed; inset:0; display:none; place-items:center;
            background:rgba(0,0,0,.94); cursor:pointer; z-index:9; }
  #sonido div { text-align:center; color:var(--manteca); font-size:1.1rem;
                line-height:1.8; }
  #sonido b { display:block; font-size:1.8rem; color:var(--durazno); }
</style></head><body>
<div id="sonido"><div>
  <b>&#9654; Activar audio</b>
  Click en cualquier lado
</div></div>

<div class="lcars">
  <div class="izq">
    <div class="codo"></div>
    <div class="bloque b1">LCARS<br>47-2258</div>
    <div class="bloque b2">PUENTE<br>&nbsp;<br>TRIPULACION</div>
    <div class="luces">
      <div class="luz titila"></div><div class="luz titila"></div>
      <div class="luz titila"></div><div class="luz titila"></div>
      <div class="luz titila"></div><div class="luz titila"></div>
    </div>
    <div class="bloque b3" id="reloj">--:--</div>
    <div class="bloque b4">SFC</div>
    <div class="bloque b5 titila">ENLACE</div>
    <div class="relleno"></div>
    <button id="hablar" class="oculto">&#9679;<br>Mantene<br>apretado<br>para hablar</button>
  </div>

  <div class="der">
    <div class="barra">
      <div class="rot">ESTACION DE MANDO</div>
      <div class="tira"></div>
      <div class="rot" id="codigo">0000</div>
    </div>

    <div class="centro">
      <div class="marco">
        <img id="retrato" alt="">
        <div class="vacio" id="vacio">ESPERANDO<br>ORDENES</div>
      </div>
      <div class="datos">
        <div class="nombre" id="nombre">&mdash;</div>
        <div class="rol" id="rol">SIN ASIGNAR</div>
        <div class="frase" id="frase"></div>
        <div id="micestado"></div>
      </div>

      <div class="consola">
        <!-- Nave propia, vista superior. El layout platillo + casco +
             dos gondolas es convencion del genero; el dibujo, las
             proporciones y los detalles son nuestros, y no lleva matricula
             ni marcas de ninguna serie. -->
        <svg viewBox="0 0 240 320" aria-label="Nave">
          <g class="nave-relleno">
            <ellipse cx="120" cy="76" rx="80" ry="60"/>
            <path d="M106 130 C106 146 108 152 110 160 L130 160
                     C132 152 134 146 134 130 Z"/>
            <path d="M120 155 C146 158 154 176 152 200 C150 232 140 258 120 270
                     C100 258 90 232 88 200 C86 176 94 158 120 155 Z"/>
            <path d="M146 194 L188 220 L194 234 L152 212 Z"/>
            <path d="M94 194 L52 220 L46 234 L88 212 Z"/>
            <rect x="182" y="206" width="26" height="98" rx="13"/>
            <rect x="32" y="206" width="26" height="98" rx="13"/>
          </g>

          <g class="nave-linea">
            <ellipse cx="120" cy="76" rx="80" ry="60"/>
            <path d="M106 130 C106 146 108 152 110 160 L130 160
                     C132 152 134 146 134 130"/>
            <path d="M120 155 C146 158 154 176 152 200 C150 232 140 258 120 270
                     C100 258 90 232 88 200 C86 176 94 158 120 155 Z"/>
            <path d="M146 194 L188 220 L194 234 L152 212 Z"/>
            <path d="M94 194 L52 220 L46 234 L88 212 Z"/>
            <rect x="182" y="206" width="26" height="98" rx="13"/>
            <rect x="32" y="206" width="26" height="98" rx="13"/>
          </g>

          <!-- Detalle fino: anillos del platillo, puente, deflector,
               colectores y lineas de casco. Es lo que separa un esquema
               tecnico de una silueta. -->
          <g class="nave-tenue">
            <ellipse cx="120" cy="76" rx="58" ry="43"/>
            <ellipse cx="120" cy="76" rx="34" ry="25"/>
            <ellipse cx="120" cy="76" rx="12" ry="9"/>
            <path d="M40 76 L62 76 M178 76 L200 76"/>
            <path d="M120 16 L120 34 M120 118 L120 136"/>
            <ellipse cx="120" cy="172" rx="17" ry="9"/>
            <path d="M104 196 L136 196 M106 222 L134 222 M110 246 L130 246"/>
            <ellipse cx="195" cy="218" rx="10" ry="7"/>
            <ellipse cx="45" cy="218" rx="10" ry="7"/>
            <path d="M195 232 L195 296 M45 232 L45 296"/>
          </g>
        </svg>

        <div class="tit-consola">ULTIMO QUE MANDAMOS</div>
        <div class="lectura"><div class="et">VELOC</div><div class="va" id="lv">--</div></div>
        <div class="lectura"><div class="et">TECLA</div><div class="va" id="lt">--</div></div>
        <div class="lectura"><div class="et">ORDEN</div><div class="va" id="lc">--</div></div>
        <div class="lectura"><div class="et">MODO</div><div class="va" id="lm">--</div></div>
      </div>
    </div>
  </div>
</div>

<script>
let ultimo = 0;
let sonidoOk = false;
const gate = document.getElementById('sonido');

// Cada division tiene su color, igual que los uniformes del plantel: la
// interfaz cambia de acento segun quien este hablando.
const COLOR_DIVISION = {
  rojo: '#cc6666', dorado: '#ffcc66', azul: '#99ccff'
};

gate.addEventListener('click', () => {
  sonidoOk = true;
  gate.style.display = 'none';
  new Audio().play().catch(() => {});
});

function reproducir(url) {
  if (!url) return;
  const a = new Audio(url);
  a.play().then(() => { sonidoOk = true; })
   .catch(() => { if (!sonidoOk) gate.style.display = 'grid'; });
}

function pintar(uniforme) {
  const c = COLOR_DIVISION[uniforme] || '#ff9966';
  document.documentElement.style.setProperty('--acento', c);
}

function tictac() {
  const d = new Date();
  document.getElementById('reloj').innerHTML =
    String(d.getHours()).padStart(2,'0') + ':' +
    String(d.getMinutes()).padStart(2,'0');
}
setInterval(tictac, 1000); tictac();

async function tick() {
  try {
    const e = await (await fetch('/estado')).json();
    if (e.ts && e.ts !== ultimo) {
      ultimo = e.ts;
      const img = document.getElementById('retrato');
      const vacio = document.getElementById('vacio');
      pintar(e.uniforme);
      document.getElementById('codigo').textContent =
        String(Math.floor(e.ts) % 10000).padStart(4,'0');

      if (e.oficial && e.oficial !== 'computadora') {
        img.classList.remove('visible');
        setTimeout(() => {
          img.src = '/retrato/' + e.oficial + '.png?t=' + e.ts;
          img.onload = () => img.classList.add('visible');
        }, 120);
        vacio.style.display = 'none';
      } else {
        img.classList.remove('visible');
        vacio.style.display = 'grid';
        vacio.innerHTML = 'COMPUTADORA';
      }
      document.getElementById('nombre').textContent = e.nombre || '\u2014';
      document.getElementById('rol').textContent = e.oficial || 'SIN ASIGNAR';
      document.getElementById('frase').textContent = e.frase || '';
      const NIVEL = ['detenida','1/4','1/2','3/4','maxima'];
      document.getElementById('lv').textContent =
        (e.velocidad === null || typeof e.velocidad === 'undefined')
          ? '--' : NIVEL[e.velocidad];
      document.getElementById('lt').textContent = e.tecla || '--';
      document.getElementById('lc').textContent = e.comando || '--';
      document.getElementById('lm').textContent =
        e.mic_web ? 'voz' : (e.boton ? 'boton' : 'tecla');

      reproducir(e.audio);
    }
    mostrarBoton(!!e.boton);
    configurarBoton(e);
    if (e.mic_web && !micActivo) iniciarMicWeb();
  } catch (err) { /* el server todavia no arranco, se reintenta solo */ }
}

const btn = document.getElementById('hablar');
let apretado = false;

async function avisar(activo) {
  if (activo === apretado) return;
  apretado = activo;
  btn.classList.toggle('grabando', activo);
  textoBoton(activo);
  try {
    await fetch('/hablar', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({activo})});
  } catch (e) {}
}

// Dos formas de activarlo. El modo hover lo decide el server (estado.hover).
let porHover = false, tEntrar = null, tSalir = null;
let esperaEntrar = 250, esperaSalir = 350;

function configurarBoton(estado) {
  if (porHover === !!estado.hover) return;
  porHover = !!estado.hover;
  esperaEntrar = estado.espera_entrar || 250;
  esperaSalir = estado.espera_salir || 350;
  btn.dataset.hover = porHover ? '1' : '0';
  textoBoton(false);
}

function textoBoton(grabando) {
  if (grabando) {
    btn.innerHTML = '&#9679;<br>Grabando&hellip;<br>' +
      (porHover ? 'sali para<br>terminar' : 'solta al<br>terminar');
  } else {
    btn.innerHTML = porHover
      ? '&#9679;<br>Pasa el mouse<br>por aca<br>para hablar'
      : '&#9679;<br>Mantene<br>apretado<br>para hablar';
  }
}

// --- por click (mantener apretado) ---
btn.addEventListener('mousedown', () => { if (!porHover) avisar(true); });
btn.addEventListener('touchstart', (e) => {
  if (porHover) return;
  e.preventDefault(); avisar(true);
});
['mouseup','touchend','touchcancel'].forEach(
  ev => btn.addEventListener(ev, () => { if (!porHover) avisar(false); }));

// --- por hover, con los dos retardos ---
btn.addEventListener('mouseenter', () => {
  if (!porHover) return;
  clearTimeout(tSalir); tSalir = null;
  if (apretado) return;
  // Quedarse un rato antes de arrancar: asi cruzar el boton de paso no graba.
  tEntrar = setTimeout(() => avisar(true), esperaEntrar);
});

btn.addEventListener('mouseleave', () => {
  clearTimeout(tEntrar); tEntrar = null;
  if (!porHover) { avisar(false); return; }
  // Y un margen al salir, para no cortar la frase por un temblor de mano.
  tSalir = setTimeout(() => avisar(false), esperaSalir);
});

// Si la ventana pierde el mouse del todo, cortar sin esperar.
window.addEventListener('blur', () => {
  clearTimeout(tEntrar); clearTimeout(tSalir);
  avisar(false);
});
document.addEventListener('mouseleave', () => {
  if (!porHover) return;
  clearTimeout(tEntrar);
  clearTimeout(tSalir);
  avisar(false);
});

function mostrarBoton(si) { btn.classList.toggle('oculto', !si); }

// -------------------------------------------------------------------------
// Microfono en el browser (modo "web"). Ver el comentario largo en el modo
// "web" de fase2_voice_commands.py: la ventaja real es echoCancellation.
// La deteccion de voz es la idea de hark (github.com/otalk/hark), escrita a
// mano para que la pagina siga andando sin internet.
// -------------------------------------------------------------------------
const VAD = { umbral:0.015, silencioCorte:0.7, preRoll:0.4, maxFrase:8.0 };
let micActivo = false;

async function iniciarMicWeb() {
  if (micActivo) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: {
      echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    const ctx = new AudioContext();
    const codigo = `
      class Captura extends AudioWorkletProcessor {
        process(inputs) {
          const canal = inputs[0] && inputs[0][0];
          if (canal) this.port.postMessage(new Float32Array(canal));
          return true;
        }
      }
      registerProcessor('captura', Captura);`;
    const url = URL.createObjectURL(new Blob([codigo], {type:'text/javascript'}));
    await ctx.audioWorklet.addModule(url);

    const nodo = new AudioWorkletNode(ctx, 'captura');
    ctx.createMediaStreamSource(stream).connect(nodo);

    const hz = ctx.sampleRate;
    const porBloque = 128 / hz;
    const maxPre = Math.ceil(VAD.preRoll / porBloque);
    let pre = [], frase = [], grabando = false, silencio = 0;

    nodo.port.onmessage = (ev) => {
      const b = ev.data;
      let suma = 0;
      for (let i = 0; i < b.length; i++) suma += b[i] * b[i];
      const rms = Math.sqrt(suma / b.length);

      if (!grabando) {
        pre.push(b);
        if (pre.length > maxPre) pre.shift();
        if (rms >= VAD.umbral) { grabando = true; frase = pre.slice(); silencio = 0; }
        return;
      }
      frase.push(b);
      silencio = rms >= VAD.umbral ? 0 : silencio + porBloque;
      const largo = frase.length * porBloque;
      if (silencio < VAD.silencioCorte && largo < VAD.maxFrase) return;

      const total = frase.reduce((n, x) => n + x.length, 0);
      const junto = new Float32Array(total);
      let o = 0;
      for (const x of frase) { junto.set(x, o); o += x.length; }
      grabando = false; frase = []; pre = []; silencio = 0;
      if (largo >= 0.3) enviarVoz(junto, hz);
    };

    micActivo = true;
    document.getElementById('micestado').textContent =
      'MIC ' + Math.round(hz/1000) + ' KHZ · ECO CANCELADO';
  } catch (e) {
    document.getElementById('micestado').textContent = 'SIN MICROFONO: ' + e.name;
  }
}

async function enviarVoz(muestras, hz) {
  try {
    await fetch('/voz', {method:'POST',
      headers:{'Content-Type':'application/octet-stream','X-Sample-Rate':hz},
      body: muestras.buffer});
  } catch (e) {}
}

setInterval(tick, 300); tick();
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._responder(200, "text/html; charset=utf-8",
                            PAGINA.encode("utf-8"))
        elif self.path.startswith("/estado"):
            global _ultimo_poll
            _ultimo_poll = time.time()
            with _lock:
                cuerpo = json.dumps(_estado).encode("utf-8")
            self._responder(200, "application/json", cuerpo)
        elif self.path.startswith("/retrato/"):
            self._archivo(DIR_IMAGENES, self.path.split("?")[0][9:],
                          ".png", "image/png")
        elif self.path.startswith("/audio/"):
            self._archivo(DIR_AUDIO, self.path.split("?")[0][7:],
                          ".wav", "audio/wav")
        else:
            self._responder(404, "text/plain", b"no")

    def do_POST(self):
        global _boton
        largo = int(self.headers.get("Content-Length") or 0)

        if self.path.startswith("/voz"):
            # Audio crudo (float32) grabado por la pagina. Se manda en binario
            # y no en base64 para no inflarlo un 33% al pedo.
            crudo = self.rfile.read(largo)
            try:
                hz = int(self.headers.get("X-Sample-Rate") or 48000)
            except ValueError:
                hz = 48000
            if crudo:
                _frases_web.put((crudo, hz))
            return self._responder(200, "application/json", b'{"ok":true}')

        if not self.path.startswith("/hablar"):
            return self._responder(404, "text/plain", b"no")
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except Exception:
            datos = {}
        _boton = bool(datos.get("activo"))
        self._responder(200, "application/json", b'{"ok":true}')

    def _archivo(self, carpeta, nombre, extension, tipo):
        # Solo el nombre de archivo, nunca una ruta: sin esto, un pedido como
        # /retrato/../../algo saldria de la carpeta.
        nombre = os.path.basename(nombre)
        ruta = os.path.join(carpeta, nombre)
        if not nombre.endswith(extension) or not os.path.isfile(ruta):
            return self._responder(404, "text/plain", b"no esta")
        with open(ruta, "rb") as f:
            self._responder(200, tipo, f.read())

    def _responder(self, codigo, tipo, cuerpo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass  # sin log: ensuciaria la consola de comandos


def iniciar():
    """Arranca el server en un thread aparte. Devuelve la URL, o None si no
    pudo (por ejemplo si el puerto ya esta ocupado)."""
    global _servidor
    if _servidor is not None:
        return f"http://127.0.0.1:{PUERTO}"
    try:
        _servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), _Handler)
    except OSError as e:
        print(f"  [!] No se pudo abrir el panel web en el puerto {PUERTO}: {e}")
        return None
    threading.Thread(target=_servidor.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{PUERTO}"


if __name__ == "__main__":
    url = iniciar()
    publicar("armas", "Korak", "Armas listas.", "disparar",
             "armas__armas_listas.wav")
    print(f"Panel de prueba en {url} — Ctrl+C para salir")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
