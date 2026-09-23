#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO DE TELEMETRÍA CLOUD Y DIAGNÓSTICO DE USO — JsBOT RPA
===============================================================================
Sistema   : JsBOT (Robotic Process Automation)
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela

Este módulo gestiona el registro de eventos y telemetría de instalación,
inicio y uso del sistema hacia Google Sheets (o endpoints HTTP compatibles).
Opera en hilos secundarios desacoplados (non-blocking) con timeout estricto,
garantizando cero impacto en el rendimiento y resiliencia total sin conexión.
===============================================================================
"""

import os
import sys
import uuid
import socket
import platform
import threading
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from modulos.version import __version__
from modulos.config_manager import cargar_settings

def obtener_identificador_maquina() -> str:
    """
    Genera un hash / identificador único de la máquina basado en la MAC address
    y el nombre de host, para contar usuarios únicos sin almacenar datos vulnerables.
    """
    try:
        raw_node = str(uuid.getnode())
        host = platform.node() or "unknown_host"
        import hashlib
        return hashlib.sha256(f"{raw_node}-{host}".encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "anon-" + str(uuid.uuid4())[:8]

def obtener_metadatos_sistema() -> Dict[str, Any]:
    """
    Obtiene los metadatos esenciales del entorno de ejecución de forma segura.
    """
    try:
        usuario = os.getlogin()
    except Exception:
        usuario = os.environ.get("USERNAME") or os.environ.get("USER") or "desconocido"

    try:
        nombre_equipo = platform.node() or socket.gethostname()
    except Exception:
        nombre_equipo = "desconocido"

    try:
        so_detalle = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
    except Exception:
        so_detalle = sys.platform

    return {
        "marca_temporal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_maquina": obtener_identificador_maquina(),
        "equipo": nombre_equipo,
        "usuario": usuario,
        "sistema_operativo": so_detalle,
        "version_jsbot": f"v{__version__}",
        "python_version": platform.python_version()
    }

def _enviar_payload_http(url: str, payload: Dict[str, Any], timeout: float = 3.5) -> bool:
    """
    Envía el payload a la URL de Google Apps Script mediante una petición POST.
    Resiliente: no genera excepciones ante fallas de red, DNS o timeout.
    """
    if not url or not requests:
        return False

    try:
        # Google Apps Script requiere json= o data= y redirecciones automáticas habilitadas
        resp = requests.post(url, json=payload, timeout=timeout, allow_redirects=True)
        return resp.status_code in (200, 201, 302)
    except Exception:
        return False

def despachar_evento_asincrono(tipo_evento: str, detalle: Optional[str] = None, url_override: Optional[str] = None) -> None:
    """
    Despacha un evento de telemetría en un hilo demonio desacoplado.
    Tipos de evento estándar:
      - 'INSTALACION'
      - 'INICIO'
      - 'DESINSTALACION'
      - 'ACTUALIZACION'
    """
    settings = cargar_settings() or {}
    cfg_telemetria = settings.get("telemetria", {})
    
    # Si la telemetría está desactivada explícitamente en la configuración, omitir
    if not cfg_telemetria.get("activa", True):
        return

    url = url_override or cfg_telemetria.get("google_sheets_url", "").strip()
    if not url:
        return

    payload = obtener_metadatos_sistema()
    payload["tipo_evento"] = tipo_evento
    payload["detalle"] = detalle or "Operación estándar"

    # Despacho en hilo secundario (fire and forget)
    hilo = threading.Thread(
        target=_enviar_payload_http,
        args=(url, payload),
        daemon=True,
        name=f"TelemetriaThread-{tipo_evento}"
    )
    hilo.start()

def registrar_evento_instalacion(url_override: Optional[str] = None) -> None:
    """Registra evento de primera instalación completada con éxito."""
    despachar_evento_asincrono("INSTALACION", "Instalador autónomo One-Liner completado", url_override)

def registrar_evento_inicio(modo: str = "GUI") -> None:
    """Registra evento de arranque de la aplicación."""
    despachar_evento_asincrono("INICIO", f"Arranque exitoso en modo {modo}")

def registrar_evento_desinstalacion(url_override: Optional[str] = None) -> None:
    """Registra evento de desinstalación limpia del sistema."""
    despachar_evento_asincrono("DESINSTALACION", "Desinstalador ejecutado por el usuario", url_override)
