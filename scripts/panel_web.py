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
           "audio": None, "ts": 0, "boton": False, "mic_web": False}
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


def publicar(oficial, nombre, frase, comando, audio=None):
    """La llama oficiales.responder() cada vez que contesta alguien. `audio` es
    el nombre del wav, o None si no hay."""
    with _lock:
        _estado.update({"oficial": oficial, "nombre": nombre, "frase": frase,
                        "comando": comando, "ts": time.time(),
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
<title>Puente</title>
<style>
  * { box-sizing: border-box; }
  /* min-height y no height: si el contenido crece, la pagina se estira y se
     puede scrollear. Con height:100vh + overflow:hidden, al aparecer un
     oficial el boton de hablar quedaba recortado abajo y no habia forma de
     llegar a el (bug del 25/09). */
  body { margin:0; min-height:100vh; display:grid; place-items:center;
         background:#07090f; color:#e8eaf0;
         font-family: system-ui, -apple-system, Segoe UI, sans-serif; }
  /* El padding de abajo deja lugar para el boton, que va fijo al viewport. */
  .puente { width:min(92vw,520px); text-align:center;
            padding:1.5rem 1rem 8rem; }
  /* El retrato se mide tambien contra el ALTO de la ventana: en una ventana
     baja se achica solo en vez de empujar todo lo demas fuera de la pantalla. */
  .marco { position:relative; width:min(78vw,42vh,380px); aspect-ratio:1;
           margin:0 auto 1.4rem; border-radius:50%; overflow:hidden;
           border:3px solid #2a3350; background:#0d1220;
           box-shadow:0 0 60px rgba(90,130,255,.18); }
  .marco img { width:100%; height:100%; object-fit:cover; display:block;
               opacity:0; transition:opacity .35s ease; }
  .marco img.visible { opacity:1; }
  .vacio { position:absolute; inset:0; display:grid; place-items:center;
           color:#41496b; font-size:.95rem; padding:2rem; }
  .nombre { font-size:1.5rem; font-weight:650; letter-spacing:.06em;
            text-transform:uppercase; color:#cfd8ff; }
  .rol { font-size:.8rem; letter-spacing:.22em; text-transform:uppercase;
         color:#5b6690; margin-top:.3rem; }
  .frase { margin-top:1.5rem; font-size:1.35rem; line-height:1.45;
           min-height:2.6em; color:#f2f4fa; }
  .comando { margin-top:1.6rem; font-size:.78rem; letter-spacing:.14em;
             text-transform:uppercase; color:#4a5372; }
  .comando b { color:#8fa0d8; font-weight:600; }
  #sonido { position:fixed; inset:0; display:none; place-items:center;
            background:rgba(7,9,15,.94); cursor:pointer; z-index:9; }
  #sonido div { text-align:center; color:#cfd8ff; font-size:1.1rem;
                line-height:1.7; }
  #sonido b { display:block; font-size:1.5rem; margin-bottom:.5rem; }
  #sonido span { color:#5b6690; font-size:.85rem; }
  /* Fijo al viewport: el boton de hablar tiene que estar SIEMPRE disponible,
     no importa cuanto contenido haya arriba. */
  #hablar { position:fixed; left:50%; transform:translateX(-50%);
            bottom:1.5rem; width:min(88vw,480px); padding:1.1rem; border:none;
            border-radius:999px; background:#1c2a4d; color:#cfd8ff;
            font-size:1.05rem; font-weight:600; letter-spacing:.06em;
            cursor:pointer; user-select:none; -webkit-user-select:none;
            box-shadow:0 8px 32px rgba(7,9,15,.9);
            transition:background .15s, transform .1s; z-index:5; }
  #hablar:hover { background:#24365f; }
  /* Cuando no hay boton (otros modos), no hay que reservarle lugar. */
  body.sin-boton .puente { padding-bottom:1.5rem; }
  #hablar.grabando { background:#8c2231; color:#fff;
                     transform:translateX(-50%) scale(.99); }
  #hablar.oculto { display:none; }
</style></head><body>
<div id="sonido"><div>
  <b>🔊 Activar sonido</b>
  Click en cualquier lado
  <span>El browser bloquea el audio hasta que la página se toca una vez</span>
</div></div>
<div class="puente">
  <div class="marco">
    <img id="retrato" alt="">
    <div class="vacio" id="vacio">Esperando órdenes, capitán</div>
  </div>
  <div class="nombre" id="nombre"></div>
  <div class="rol" id="rol"></div>
  <div class="frase" id="frase"></div>
  <div class="comando" id="comando"></div>
  <button id="hablar" class="oculto">🎙 Mantené apretado para hablar</button>
  <div class="comando" id="micestado"></div>
</div>
<script>
let ultimo = 0;
let sonidoOk = false;
const gate = document.getElementById('sonido');

// El browser no deja reproducir audio hasta que el usuario toca la pagina.
// En vez de pedirlo de entrada, se intenta reproducir y solo si falla se
// muestra el cartel: asi el que ya interactuo no lo ve nunca.
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

async function tick() {
  try {
    const e = await (await fetch('/estado')).json();
    if (e.ts && e.ts !== ultimo) {
      ultimo = e.ts;
      const img = document.getElementById('retrato');
      const vacio = document.getElementById('vacio');
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
        vacio.textContent = 'COMPUTADORA';
      }
      document.getElementById('nombre').textContent = e.nombre || '';
      document.getElementById('rol').textContent = e.oficial || '';
      document.getElementById('frase').textContent = e.frase || '';
      document.getElementById('comando').innerHTML =
        e.comando ? 'orden: <b>' + e.comando + '</b>' : '';
      reproducir(e.audio);
    }
    mostrarBoton(!!e.boton);
    if (e.mic_web && !micActivo) iniciarMicWeb();
  } catch (err) { /* el server todavia no arranco, se reintenta solo */ }
}
// Boton de hablar: mantener apretado, como el push-to-talk pero con el mouse.
// El audio lo sigue grabando Python; esto solo avisa cuando empezar y cuando
// terminar, asi no hay que tocar el teclado.
const btn = document.getElementById('hablar');
let apretado = false;

async function avisar(activo) {
  if (activo === apretado) return;
  apretado = activo;
  btn.classList.toggle('grabando', activo);
  btn.textContent = activo ? '🔴 Grabando… soltá al terminar'
                           : '🎙 Mantené apretado para hablar';
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

// El boton solo aparece si la Fase 2 esta en modo "boton": lo dice el estado.
function mostrarBoton(si) {
  btn.classList.toggle('oculto', !si);
  document.body.classList.toggle('sin-boton', !si);
}

// -------------------------------------------------------------------------
// Microfono en el browser (modo "web").
//
// Por que aca y no en Python: pidiendo echoCancellation, el browser cancela SU
// PROPIA salida de la entrada. Como la voz de los oficiales suena por esta
// misma pagina, eso resuelve el eco de raiz, en vez de silenciar el microfono
// mientras habla el oficial. Ademas trae supresion de ruido y control de
// ganancia gratis.
//
// La deteccion de voz es la de hark (github.com/otalk/hark): medir el volumen
// cada tanto y disparar al cruzar un umbral. Va escrita a mano y no como
// dependencia para que la pagina siga andando sin internet.
// -------------------------------------------------------------------------
const VAD = {
  umbral: 0.015,      // RMS a partir del cual se considera voz
  silencioCorte: 0.7, // segundos de silencio que cierran la frase
  preRoll: 0.4,       // segundos guardados ANTES de detectar voz
  maxFrase: 8.0,
};

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
      '🎙 escuchando · ' + Math.round(hz/1000) + ' kHz · eco cancelado';
  } catch (e) {
    document.getElementById('micestado').textContent =
      '🎙 sin micrófono: ' + e.name;
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
