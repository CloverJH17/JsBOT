"""
MÓDULO DE ENTORNO Y RUTAS UNIVERSALES — JsBOT
Resuelve de forma absoluta el sistema de archivos y blinda sys.path en Linux y Windows.
"""
import os
import sys
from pathlib import Path

# Compatibilidad con Canaima GNU/Linux: Forzar renderizado OpenGL por software
# para prevenir fallos de segmentación con drivers Mesa en hardware sin aceleración 3D
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

def verificar_display_linux() -> bool:
    """Verifica si existe un servidor gráfico disponible (DISPLAY o WAYLAND_DISPLAY) en entornos Linux."""
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True

# Raíz absoluta del proyecto (sube un nivel desde modulos/)
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# Inyección blindada en sys.path para permitir ejecuciones desde cualquier subcarpeta
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

MODULOS_DIR = RAIZ_PROYECTO / "modulos"
if str(MODULOS_DIR) not in sys.path:
    sys.path.insert(0, str(MODULOS_DIR))

# Rutas universales de directorios de infraestructura
CARPETA_CONFIG = RAIZ_PROYECTO / "config"
CARPETA_LOGS = RAIZ_PROYECTO / "logs"
CARPETA_SCREENSHOTS = CARPETA_LOGS / "screenshots"
CARPETA_PLANILLAS = RAIZ_PROYECTO / "Planillas"
CARPETA_ASSETS = CARPETA_CONFIG / "assets"
CARPETA_ICONOS = CARPETA_ASSETS / "iconos"
CARPETA_DATA = RAIZ_PROYECTO / "data"

# Rutas canónicas de archivos operativos
ARCHIVO_SETTINGS = CARPETA_CONFIG / "settings.json"
ARCHIVO_PLANTILLA_ODS = CARPETA_CONFIG / "plantilla_base.ods"
ARCHIVO_ESTADO_SESION = CARPETA_LOGS / "session_state.json"
ARCHIVO_ESTADO_SESION_SERVICIOS = CARPETA_LOGS / "session_state_servicios.json"
ARCHIVO_CONFIG_INI = CARPETA_CONFIG / "config.ini"
ARCHIVO_DB = CARPETA_DATA / "jsbot.db"

# Creación garantizada de directorios en disco
CARPETA_CONFIG.mkdir(parents=True, exist_ok=True)
CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
CARPETA_SCREENSHOTS.mkdir(parents=True, exist_ok=True)
CARPETA_PLANILLAS.mkdir(parents=True, exist_ok=True)
CARPETA_DATA.mkdir(parents=True, exist_ok=True)

