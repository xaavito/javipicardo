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
_estado = {"oficial": None, "nombre": None, "frase": None,
           "comando": None, "audio": None, "ts": 0, "boton": False}
_lock = threading.Lock()
_servidor = None
_ultimo_poll = 0.0

# True mientras el capitan mantiene apretado el boton de hablar de la pagina.
# Lo usa la Fase 2 en modo "boton", en lugar de la tecla fisica.
_boton = False


def boton_apretado():
    return _boton


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


def hay_browser():
    """True si una pagina pregunto el estado hace poco. Con eso se decide quien
    reproduce el audio, para no escucharlo dos veces."""
    return (time.time() - _ultimo_poll) < SEGUNDOS_BROWSER_VIVO


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Puente</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; height:100vh; display:grid; place-items:center;
         background:#07090f; color:#e8eaf0; overflow:hidden;
         font-family: system-ui, -apple-system, Segoe UI, sans-serif; }
  .puente { width:min(92vw,520px); text-align:center; }
  .marco { position:relative; width:min(78vw,380px); aspect-ratio:1;
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
  #hablar { margin-top:1.8rem; width:100%; padding:1.1rem; border:none;
            border-radius:999px; background:#1c2a4d; color:#cfd8ff;
            font-size:1.05rem; font-weight:600; letter-spacing:.06em;
            cursor:pointer; user-select:none; -webkit-user-select:none;
            transition:background .15s, transform .1s; }
  #hablar:hover { background:#24365f; }
  #hablar.grabando { background:#8c2231; color:#fff; transform:scale(.99); }
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
function mostrarBoton(si) { btn.classList.toggle('oculto', !si); }

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
        if not self.path.startswith("/hablar"):
            return self._responder(404, "text/plain", b"no")
        largo = int(self.headers.get("Content-Length") or 0)
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
