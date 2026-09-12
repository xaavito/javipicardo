"""
Script de diagnostico - Fase 2
Prueba SOLO la carga del modelo Whisper (faster-whisper), aislado del resto
del pipeline de voz, para diagnosticar el crash de Python reportado al cargar
el modelo "small" por primera vez.

Correr con: python probar_whisper.py

Si este script tambien crashea, confirma que el problema es especifico de
faster-whisper/ctranslate2 (probablemente falta el Microsoft Visual C++
Redistributable x64, o hay incompatibilidad con la version de Python usada),
no algo relacionado al resto del pipeline (audio, teclado, etc.).
"""

import sys

print(f"Python: {sys.version}")
print("Intentando importar faster_whisper...")

from faster_whisper import WhisperModel

print("Import OK. Intentando cargar modelo 'tiny' (el mas chico, para "
      "descartar problemas de tamaño/memoria)...")

modelo = WhisperModel("tiny", device="cpu", compute_type="int8")

print("Modelo 'tiny' cargado con exito!")
print("Si esto funciono pero 'small' fallaba, probablemente sea un tema de "
      "memoria o de timeout en la descarga del modelo mas grande.")
