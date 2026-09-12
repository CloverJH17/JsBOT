#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: GESTOR CENTRAL DE CONFIGURACIÓN (config_manager.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v3.5.2
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
Única puerta de entrada a config/settings.json. Si el archivo falta o está
corrupto, se devuelven los DEFAULTS (idénticos al comportamiento histórico),
de modo que el bot nunca deja de arrancar por un problema de configuración.
===============================================================================
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.json")

DEFAULTS = {
    "timeouts": {
        "ajax_wait_seconds": 15,
        "element_wait_seconds": 12,
        "login_wait_seconds": 15
    },
    "urls": {
        "base_login": "https://infoapp2.infocentro.gob.ve/admin/index.php"
    },
    "browser": {
        "priority": ["firefox", "chrome", "edge"],
        "start_maximized": True
    },
    "validation": {
        "default_phone": "0412-0000000",
        "capture_screenshots_on_error": True
    }
}


def _fusionar(base: dict, extra: dict) -> dict:
    """Fusiona dicts en profundidad; los valores del archivo pisan los defaults."""
    resultado = dict(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _fusionar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def cargar_settings(ruta: str = None) -> dict:
    """Lee settings.json y lo fusiona sobre los defaults. Nunca lanza excepciones."""
    ruta = ruta or SETTINGS_PATH
    datos = {}
    try:
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                leido = json.load(f)
            if isinstance(leido, dict):
                datos = leido
    except Exception:
        datos = {}
    return _fusionar(DEFAULTS, datos)


def obtener_timeout(campo: str, default: int = None) -> int:
    """Obtiene un timeout de la sección timeouts (en segundos)."""
    try:
        return int(cargar_settings()["timeouts"].get(campo, default))
    except Exception:
        return int(default)


def obtener_url_login() -> str:
    """URL del panel administrativo de InfoApp."""
    return str(
        cargar_settings().get("urls", {}).get("base_login")
        or DEFAULTS["urls"]["base_login"]
    )


def obtener_browser_cfg() -> dict:
    """Configuración de navegadores: prioridad y ventana maximizada."""
    cfg = cargar_settings().get("browser", {})
    prioridad = cfg.get("priority") or DEFAULTS["browser"]["priority"]
    if not isinstance(prioridad, (list, tuple)) or not prioridad:
        prioridad = DEFAULTS["browser"]["priority"]
    return {
        "priority": [str(p).strip().lower() for p in prioridad],
        "start_maximized": bool(cfg.get("start_maximized", True))
    }


def telefono_por_defecto() -> str:
    """Teléfono neutral usado cuando el registro original no trae número."""
    return str(
        cargar_settings().get("validation", {}).get("default_phone")
        or DEFAULTS["validation"]["default_phone"]
    )


def captura_screenshots_activada() -> bool:
    """Indica si se deben guardar evidencias PNG ante incidencias."""
    return bool(
        cargar_settings().get("validation", {}).get("capture_screenshots_on_error", True)
    )
