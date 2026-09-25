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

# Ultimo estado publicado. Lo lee el handler desde otro thread, por eso el lock.
_estado = {"oficial": None, "nombre": None, "frase": None, "comando": None,
           "audio": None, "uniforme": None, "ts": 0, "boton": False,
           "mic_web": False}
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


def publicar(oficial, nombre, frase, comando, audio=None, uniforme=None):
    """La llama oficiales.responder() cada vez que contesta alguien. `audio` es
    el nombre del wav y `uniforme` el color de division, que la pagina usa como
    color de acento del LCARS."""
    with _lock:
        _estado.update({"oficial": oficial, "nombre": nombre, "frase": frase,
                        "comando": comando, "ts": time.time(),
                        "uniforme": uniforme,
                        "audio": f"/audio/{audio}" if audio else None})


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

  .lcars { display:grid; grid-template-columns:132px 1fr; gap:10px;
           min-height:100vh; padding:10px 14px 10px 10px; }

  /* --- columna izquierda: el codo y los bloques --- */
  .izq { display:flex; flex-direction:column; gap:10px; }
  .codo { height:110px; background:var(--acento);
          border-radius:60px 0 0 0; position:relative;
          transition:background .4s; }
  .codo::after { content:""; position:absolute; right:-10px; bottom:0;
                 width:10px; height:34px; background:var(--acento);
                 transition:background .4s; }
  .bloque { border-radius:0 0 0 0; padding:.5rem .7rem; text-align:right;
            font-size:.82rem; color:#000; line-height:1; }
  .b1 { background:var(--lila); height:64px; }
  .b2 { background:var(--azul); height:120px; }
  .b3 { background:var(--manteca); height:46px; }
  .b4 { background:var(--ladrillo); flex:1; min-height:60px;
        border-radius:0 0 0 60px; }

  /* --- columna derecha --- */
  .der { display:flex; flex-direction:column; gap:10px; min-width:0; }
  .barra { display:flex; gap:8px; align-items:center; }
  .barra .tira { flex:1; height:34px; background:var(--acento);
                 border-radius:0 34px 34px 0; transition:background .4s; }
  .barra .rot { font-size:1.05rem; color:var(--acento); white-space:nowrap;
                transition:color .4s; }

  .centro { flex:1; display:grid; grid-template-columns:auto 1fr; gap:18px;
            align-items:center; padding:.5rem 0 5rem; }
  @media (max-width:560px) { .centro { grid-template-columns:1fr; } }

  .marco { position:relative; width:min(38vw,34vh,260px); aspect-ratio:1;
           border-radius:14px; overflow:hidden; background:#0a0a0a;
           border:4px solid var(--acento); transition:border-color .4s; }
  .marco img { width:100%; height:100%; object-fit:cover; display:block;
               opacity:0; transition:opacity .35s; filter:saturate(.9); }
  .marco img.visible { opacity:1; }
  .vacio { position:absolute; inset:0; display:grid; place-items:center;
           color:#3a3a3a; font-size:.8rem; padding:1rem; text-align:center; }

  .datos { min-width:0; }
  .nombre { font-size:2.6rem; line-height:1; color:var(--acento);
            transition:color .4s; }
  .rol { font-size:.85rem; color:var(--lila); margin-top:.35rem; }
  .frase { margin-top:1.1rem; font-size:1.35rem; line-height:1.3;
           color:var(--melon); text-transform:none; letter-spacing:.02em;
           min-height:2.6em; }
  .comando { margin-top:.9rem; font-size:.78rem; color:var(--azul); }
  .comando b { color:var(--celeste); }
  #micestado { font-size:.72rem; color:#6b6b6b; margin-top:.5rem; }

  /* El boton va fijo: tiene que estar SIEMPRE, no importa el contenido. */
  #hablar { position:fixed; left:152px; right:14px; bottom:14px; height:64px;
            border:none; border-radius:0 32px 32px 0; background:var(--durazno);
            color:#000; font-family:inherit; font-size:1.2rem;
            letter-spacing:.12em; text-transform:uppercase; cursor:pointer;
            user-select:none; -webkit-user-select:none; text-align:right;
            padding-right:2rem; transition:background .15s; z-index:5; }
  #hablar:hover { background:var(--melon); }
  #hablar.grabando { background:var(--ladrillo); color:#fff; }
  #hablar.oculto { display:none; }
  @media (max-width:560px) { #hablar { left:14px; } }

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
    <div class="bloque b1">LCARS<br>47-1701</div>
    <div class="bloque b2">PUENTE<br>&nbsp;<br>TRIPULACION<br>ACTIVA</div>
    <div class="bloque b3" id="reloj">--:--</div>
    <div class="bloque b4">SFC<br>COMMANDER</div>
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
        <div class="comando" id="comando"></div>
        <div id="micestado"></div>
      </div>
    </div>
  </div>
</div>

<button id="hablar" class="oculto">&#9679; Mantene apretado para hablar</button>

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
      document.getElementById('comando').innerHTML =
        e.comando ? 'ORDEN: <b>' + e.comando + '</b>' : '';
      reproducir(e.audio);
    }
    mostrarBoton(!!e.boton);
    if (e.mic_web && !micActivo) iniciarMicWeb();
  } catch (err) { /* el server todavia no arranco, se reintenta solo */ }
}

const btn = document.getElementById('hablar');
let apretado = false;

async function avisar(activo) {
  if (activo === apretado) return;
  apretado = activo;
  btn.classList.toggle('grabando', activo);
  btn.innerHTML = activo ? '&#9679; Grabando&hellip; solta al terminar'
                         : '&#9679; Mantene apretado para hablar';
  try {
    await fetch('/hablar', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({activo})});
  } catch (e) {}
}

btn.addEventListener('mousedown', () => avisar(true));
btn.addEventListener('touchstart', (e) => { e.preventDefault(); avisar(true); });
['mouseup','mouseleave','touchend','touchcancel'].forEach(
  ev => btn.addEventListener(ev, () => avisar(false)));
window.addEventListener('blur', () => avisar(false));

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
