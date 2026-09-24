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
DIR_IMAGENES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "images", "oficiales")

# Ultimo estado publicado. Lo lee el handler desde otro thread, por eso el lock.
_estado = {"oficial": None, "nombre": None, "frase": None,
           "comando": None, "ts": 0}
_lock = threading.Lock()
_servidor = None


def publicar(oficial, nombre, frase, comando):
    """La llama oficiales.responder() cada vez que contesta alguien."""
    with _lock:
        _estado.update({"oficial": oficial, "nombre": nombre, "frase": frase,
                        "comando": comando, "ts": time.time()})


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
</style></head><body>
<div class="puente">
  <div class="marco">
    <img id="retrato" alt="">
    <div class="vacio" id="vacio">Esperando órdenes, capitán</div>
  </div>
  <div class="nombre" id="nombre"></div>
  <div class="rol" id="rol"></div>
  <div class="frase" id="frase"></div>
  <div class="comando" id="comando"></div>
</div>
<script>
let ultimo = 0;
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
    }
  } catch (err) { /* el server todavia no arranco, se reintenta solo */ }
}
setInterval(tick, 300); tick();
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            self._responder(200, "text/html; charset=utf-8",
                            PAGINA.encode("utf-8"))
        elif self.path.startswith("/estado"):
            with _lock:
                cuerpo = json.dumps(_estado).encode("utf-8")
            self._responder(200, "application/json", cuerpo)
        elif self.path.startswith("/retrato/"):
            self._retrato(self.path.split("?")[0][len("/retrato/"):])
        else:
            self._responder(404, "text/plain", b"no")

    def _retrato(self, nombre):
        # Solo el nombre de archivo, nunca una ruta: sin esto, un pedido como
        # /retrato/../../algo saldria de la carpeta de imagenes.
        nombre = os.path.basename(nombre)
        ruta = os.path.join(DIR_IMAGENES, nombre)
        if not nombre.endswith(".png") or not os.path.isfile(ruta):
            return self._responder(404, "text/plain", b"no hay retrato")
        with open(ruta, "rb") as f:
            self._responder(200, "image/png", f.read())

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
    publicar("armas", "Korak", "Armas listas.", "disparar")
    print(f"Panel de prueba en {url} — Ctrl+C para salir")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
