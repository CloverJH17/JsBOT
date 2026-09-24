#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: GESTOR CENTRAL DE CONFIGURACIÓN (config_manager.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
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
import tempfile
import modulos.entorno as entorno

BASE_DIR = str(entorno.RAIZ_PROYECTO)
SETTINGS_PATH = str(entorno.ARCHIVO_SETTINGS)

DEFAULTS = {
    "urls": {
        "base_login": "https://infoapp2.infocentro.gob.ve/admin/index.php"
    },
    "browser": {
        "priority": ["chromium", "firefox", "webkit"]
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


def _guardar_json_atomico(ruta: str, datos: dict) -> None:
    """Escribe JSON en un archivo temporal y lo publica con reemplazo atómico."""
    directorio = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(directorio, exist_ok=True)
    descriptor, temporal = tempfile.mkstemp(
        prefix=f".{os.path.basename(ruta)}.",
        suffix=".tmp",
        dir=directorio,
        text=True,
    )
    os.close(descriptor)
    try:
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=4, ensure_ascii=False)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ruta)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)


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


def guardar_settings(nuevos_settings: dict, ruta: str = None) -> bool:
    """
    Persiste la configuración en config/settings.json fusionando los nuevos valores.
    Preserva las secciones no modificadas y asegura escritura atómica y limpia.
    """
    ruta = ruta or SETTINGS_PATH
    try:
        actuales = {}
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                leido = json.load(f)
                if isinstance(leido, dict):
                    actuales = leido
        if not actuales:
            actuales = dict(DEFAULTS)

        fusionado = _fusionar(actuales, nuevos_settings)
        _guardar_json_atomico(ruta, fusionado)
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar settings en {ruta}: {e}")
        return False


def obtener_url_login() -> str:
    """URL del panel administrativo de InfoApp."""
    return str(
        cargar_settings().get("urls", {}).get("base_login")
        or DEFAULTS["urls"]["base_login"]
    )


def obtener_browser_cfg() -> dict:
    """Configuración de navegadores Playwright: prioridad."""
    cfg = cargar_settings().get("browser", {})
    prioridad = cfg.get("priority") or DEFAULTS["browser"]["priority"]
    if not isinstance(prioridad, (list, tuple)) or not prioridad:
        prioridad = DEFAULTS["browser"]["priority"]
    return {
        "priority": [str(p).strip().lower() for p in prioridad]
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


# ===============================================================================
# GESTIÓN CENTRALIZADA DE SERVICIOS (config_servicios.json)
# ===============================================================================
CONFIG_SERVICIOS_PATH = str(getattr(entorno, "ARCHIVO_CONFIG_SERVICIOS", os.path.join(BASE_DIR, "config", "config_servicios.json")))

DEFAULTS_SERVICIOS = {
    "catalogo_servicios": [
        "Gestión en el Sistema de Protección Social Patria",
        "Actividades de educación o aprendizaje",
        "Operaciones bancarias por Internet",
        "Interacción con organizaciones gubernamentales en general",
        "Préstamo de espacios del Infocentro",
        "Descarga de películas, imágenes y música, programas de televisión o videos, programas de radio o música",
        "Interacción y producción de contenidos en redes sociales y medios digitales de comunicación",
        "Envío o recepción de mensajes electrónicos",
        "Lectura o descarga de periódicos, revistas en línea o libros electrónicos",
        "Obtención de información sobre organizaciones gubernamentales en general",
        "Obtención de información relacionada con la salud o con servicios médicos",
        "Compra o pedido de bienes y servicios",
        "Descarga de programas informáticos",
        "Llamadas telefónicas a través del Protocolo de Internet",
        "Publicación de información o de mensajes instantáneos",
        "Registro/Actualización enmarcados en las Políticas de Gobierno",
        "Uso o descarga de video juegos",
        "Reunión Sede Central",
        "Visita Sede Central"
    ],
    "servicio_por_defecto": "Actividades de educación o aprendizaje",
    "infocentro": {
        "user_id": "1325",
        "code_info": "NRYAR24",
        "estado_nombre": "Yaracuy",
        "estado_id": "22",
        "municipio_nombre": "San Felipe",
        "municipio_id": "1",
        "direccion": "Av. principal El Jovito, Antigua Sede Del Inan"
    }
}


def cargar_config_servicios(ruta: str = None) -> dict:
    """
    Carga la configuración de servicios comunitarios desde config/config_servicios.json.
    Si el archivo no existe o está dañado, devuelve los DEFAULTS_SERVICIOS de forma segura.
    """
    ruta = ruta or str(getattr(entorno, "ARCHIVO_CONFIG_SERVICIOS", CONFIG_SERVICIOS_PATH))
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict) and datos.get("catalogo_servicios"):
                return datos
        except Exception:
            pass
    return dict(DEFAULTS_SERVICIOS)


def guardar_config_servicios(datos: dict, ruta: str = None) -> bool:
    """
    Persiste la configuración de servicios en config/config_servicios.json de forma atómica.
    """
    ruta = ruta or str(getattr(entorno, "ARCHIVO_CONFIG_SERVICIOS", CONFIG_SERVICIOS_PATH))
    try:
        _guardar_json_atomico(ruta, datos)
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar config_servicios en {ruta}: {e}")
        return False


# ===============================================================================
# GESTIÓN CENTRALIZADA DE FICHA FORMATIVA (datos_actividad.json)
# ===============================================================================
CONFIG_DATOS_ACTIVIDAD_PATH = str(getattr(entorno, "ARCHIVO_DATOS_ACTIVIDAD", os.path.join(BASE_DIR, "config", "datos_actividad.json")))

DEFAULTS_DATOS_ACTIVIDAD = {
    "estado": "Yaracuy",
    "nombre_infocentro": "Infocentro UNEFA",
    "codigo_infocentro": "NRYAR24",
    "nombre_facilitador": "Jair Alejandro Hernández González",
    "cedula_facilitador": "30.348.783",
    "modulo": "Robótica",
    "contenido": "Plan Vacacional",
    "hora_inicio": "9:00 am",
    "hora_fin": "12:00 pm"
}


def cargar_datos_actividad(ruta: str = None) -> dict:
    """
    Carga la ficha formativa y metadatos pedagógicos desde config/datos_actividad.json.
    Si el archivo no existe o está corrupto, devuelve DEFAULTS_DATOS_ACTIVIDAD de forma segura.
    """
    ruta = ruta or str(getattr(entorno, "ARCHIVO_DATOS_ACTIVIDAD", CONFIG_DATOS_ACTIVIDAD_PATH))
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if isinstance(datos, dict) and datos.get("nombre_facilitador"):
                return {**DEFAULTS_DATOS_ACTIVIDAD, **datos}
        except Exception:
            pass
    return dict(DEFAULTS_DATOS_ACTIVIDAD)


def guardar_datos_actividad(datos: dict, ruta: str = None) -> bool:
    """
    Persiste los metadatos de la ficha formativa en config/datos_actividad.json.
    """
    ruta = ruta or str(getattr(entorno, "ARCHIVO_DATOS_ACTIVIDAD", CONFIG_DATOS_ACTIVIDAD_PATH))
    try:
        fusionado = {**DEFAULTS_DATOS_ACTIVIDAD, **datos}
        _guardar_json_atomico(ruta, fusionado)
        return True
    except Exception as e:
        print(f"⚠️ Error al guardar datos_actividad en {ruta}: {e}")
        return False

