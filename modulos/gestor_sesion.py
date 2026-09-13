#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: GESTOR DE SESIÓN, AUDITORÍA Y CHECKPOINTS (gestor_sesion.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v3.5.2
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import json
import configparser
import re
from datetime import datetime
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from modulos.interfaz_usuario import (
    prompt_credenciales_guardadas,
    prompt_nuevas_credenciales,
    prompt_url_actividad
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
CONFIG_SERV_PATH = os.path.join(CONFIG_DIR, "config_servicios.json")
SESSION_STATE_FILE = os.path.join(LOGS_DIR, "session_state.json")
SESSION_STATE_SERV_FILE = os.path.join(LOGS_DIR, "session_state_servicios.json")

def extraer_id_actividad(url: str) -> str:
    """Extrae el ID de la actividad desde los parámetros de la URL de InfoApp."""
    match = re.search(r'id_activity=(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    match_gen = re.search(r'/(\d+)(?:/|$|\?)', url)
    if match_gen:
        return match_gen.group(1)
    return "general"

def extraer_id_servicio(url: str) -> str:
    """Extrae el ID del servicio desde los parámetros de la URL de InfoApp."""
    match = re.search(r'id_service=(\d+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    match_gen = re.search(r'/(\d+)(?:/|$|\?)', url)
    if match_gen:
        return match_gen.group(1)
    return "general"

def obtener_credenciales() -> tuple:
    """Lee las credenciales guardadas en config.ini (prioriza [LOGIN], fallback [CREDENCIALES])."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE, encoding='utf-8')
            seccion = 'LOGIN' if 'LOGIN' in config else ('CREDENCIALES' if 'CREDENCIALES' in config else None)
            if seccion:
                u = config[seccion].get('usuario', '')
                c = config[seccion].get('clave', '')
                if u and c:
                    return u, c
        except Exception:
            pass
    return "", ""

def guardar_credenciales(usuario: str, clave: str):
    """Guarda las credenciales en config.ini en [LOGIN] y [CREDENCIALES]."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        try:
            config.read(CONFIG_FILE, encoding='utf-8')
        except Exception:
            pass
    config['LOGIN'] = {
        'usuario': usuario,
        'clave': clave
    }
    config['CREDENCIALES'] = {
        'usuario': usuario,
        'clave': clave
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

def gestionar_credenciales() -> tuple:
    """Gestiona el flujo interactivo de autenticación."""
    u, c = obtener_credenciales()
    if u and c:
        if prompt_credenciales_guardadas(u):
            return u, c

    u, c = prompt_nuevas_credenciales()
    guardar_credenciales(u, c)
    return u, c

# =============================================================================
# CHECKPOINTS Y AUDITORÍA DE FORMACIÓN
# =============================================================================

def guardar_estado_sesion(config: dict, participantes: list, indice_ultimo: int):
    """Guarda checkpoint en disco de forma atómica para evitar corrupción ante apagones."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    datos = {
        "id_actividad": config.get("id_actividad"),
        "url": config.get("url"),
        "usuario": config.get("usuario"),
        "timestamp_str": config.get("timestamp_str"),
        "archivo_log": config.get("archivo_log"),
        "indice_ultimo_procesado": indice_ultimo,
        "participantes": participantes
    }
    temp_file = f"{SESSION_STATE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, SESSION_STATE_FILE)

def leer_estado_sesion() -> dict:
    """Lee el checkpoint de formación si existe y no está completado."""
    if not os.path.exists(SESSION_STATE_FILE):
        return None
    try:
        with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        total = len(datos.get("participantes", []))
        ult = datos.get("indice_ultimo_procesado", 0)
        if total > 0 and ult < total:
            return datos
    except Exception:
        pass
    return None

def limpiar_estado_sesion():
    """Elimina el checkpoint de formación tras completar con éxito la carga."""
    if os.path.exists(SESSION_STATE_FILE):
        try:
            os.remove(SESSION_STATE_FILE)
        except Exception:
            pass

def inicializar_sesion_actividad() -> dict:
    """Configura la sesión inicial solicitando la URL."""
    u, c = gestionar_credenciales()
    url = prompt_url_actividad()
    if not url:
        return None

    id_act = extraer_id_actividad(url)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    
    os.makedirs(LOGS_DIR, exist_ok=True)
    archivo_log = os.path.join(LOGS_DIR, f"log_actividad_{id_act}_{ts}.txt")

    with open(archivo_log, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"REGISTRO DE AUDITORÍA — JsBOT RPA v3.1.0\n")
        f.write(f"Actividad ID : {id_act}\n")
        f.write(f"URL          : {url}\n")
        f.write(f"Fecha Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Facilitador  : {u}\n")
        f.write("=" * 80 + "\n\n")

    return {
        "usuario": u,
        "clave": c,
        "url": url,
        "id_actividad": id_act,
        "timestamp_str": ts,
        "archivo_log": archivo_log
    }

def registrar_evento_log(archivo_log: str, cedula: str, nombre: str, estado: str, detalle: str):
    """Registra una línea estructurada de auditoría en el archivo log."""
    if not archivo_log:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    with open(archivo_log, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{estado:<8}] Doc: {cedula:<18} | {nombre:<32} | {detalle}\n")

def finalizar_log_exito(config: dict):
    """Cierra el log y remueve checkpoint."""
    if config and config.get('archivo_log'):
        with open(config['archivo_log'], "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"PROCESO FINALIZADO EXITOSAMENTE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
    limpiar_estado_sesion()

def finalizar_log_incompleto(config: dict, motivo: str = ""):
    """Registra cierre prematuro o pausa en el log."""
    if config and config.get('archivo_log'):
        with open(config['archivo_log'], "a", encoding="utf-8") as f:
            f.write("\n" + "!" * 80 + "\n")
            f.write(f"PROCESO PAUSADO O INCOMPLETO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if motivo:
                f.write(f"Motivo: {motivo}\n")
            f.write("!" * 80 + "\n")

def generar_reporte_auditoria_excel(config: dict, exitosos: list, fallidos: list) -> str:
    """Genera un libro Excel con 2 hojas: 'Exitosos' e 'Incidencias'."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        id_act = config.get('id_actividad', 'general')
        ts = config.get('timestamp_str', datetime.now().strftime("%Y-%m-%d_%H%M"))
        ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Carga_Actividad_{id_act}_{ts}.xlsx")

        datos_exitosos = []
        for i, p in enumerate(exitosos, 1):
            doc = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else "S/C"))
            nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
            datos_exitosos.append({
                "N°": i,
                "Documento": doc,
                "Modalidad": p.get('cedulado', 'si').upper(),
                "Nombres y Apellidos": nom_comp,
                "Fecha Nacimiento": p.get('nacimiento', ''),
                "Teléfono": p.get('telefono', ''),
                "Género": p.get('genero', ''),
                "Estado": "EXITOSO",
                "Verificación DOM": "Confirmado en tabla InfoApp"
            })

        datos_fallidos = []
        if fallidos:
            for i, f_item in enumerate(fallidos, 1):
                p = f_item.get('participante', {})
                doc = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else "S/C"))
                nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
                datos_fallidos.append({
                    "N°": i,
                    "Documento": doc,
                    "Modalidad": p.get('cedulado', 'si').upper(),
                    "Nombres y Apellidos": nom_comp,
                    "Fecha Nacimiento": p.get('nacimiento', ''),
                    "Teléfono": p.get('telefono', ''),
                    "Estado": f_item.get('estado', 'FALLIDO'),
                    "Causa de la Incidencia": f_item.get('detalle', 'No especificado'),
                    "Acción Sugerida": "Verificar en InfoApp manualmente o corregir datos"
                })

        while True:
            try:
                with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
                    df_ex = pd.DataFrame(datos_exitosos) if datos_exitosos else pd.DataFrame([{"Mensaje": "No se registraron participantes exitosos"}])
                    df_ex.to_excel(writer, sheet_name="Exitosos", index=False)

                    if datos_fallidos:
                        df_fa = pd.DataFrame(datos_fallidos)
                        df_fa.to_excel(writer, sheet_name="Incidencias", index=False)
                break
            except PermissionError:
                print(f"\n⚠️ El archivo '{os.path.basename(ruta_excel)}' está abierto en Excel o LibreOffice.")
                input("Por favor ciérralo y presiona Enter para reintentar el guardado...")

        return ruta_excel
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte Excel de auditoría: {e}")
        return ""

# =============================================================================
# CHECKPOINTS Y AUDITORÍA DE SERVICIOS
# =============================================================================

def cargar_config_servicios() -> dict:
    """Carga configuración de servicios desde config/config_servicios.json."""
    if os.path.exists(CONFIG_SERV_PATH):
        try:
            with open(CONFIG_SERV_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
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
            "Uso o descarga de video juegos"
        ],
        "servicio_por_defecto": "Gestión en el Sistema de Protección Social Patria",
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

def guardar_config_servicios(cfg: dict):
    """Persiste configuración de servicios."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_SERV_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error al guardar config de servicios: {e}")

def guardar_estado_sesion_servicios(config_bot: dict, config_servicio: dict, personas: list, indice_ultimo: int):
    """Guarda checkpoint de servicios de forma atómica."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    datos = {
        "usuario": config_bot.get("usuario"),
        "archivo_log": config_bot.get("archivo_log"),
        "timestamp_str": config_bot.get("timestamp_str"),
        "config_servicio": config_servicio,
        "indice_ultimo_procesado": indice_ultimo,
        "personas": personas
    }
    try:
        temp_file = f"{SESSION_STATE_SERV_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, SESSION_STATE_SERV_FILE)
    except Exception:
        pass

def leer_estado_sesion_servicios() -> dict:
    """Lee el checkpoint de servicios si existe."""
    if os.path.exists(SESSION_STATE_SERV_FILE):
        try:
            with open(SESSION_STATE_SERV_FILE, "r", encoding="utf-8") as f:
                datos = json.load(f)
            personas = datos.get("personas", [])
            idx = datos.get("indice_ultimo_procesado", 0)
            if personas and idx < len(personas):
                return datos
        except Exception:
            pass
    return None

def limpiar_estado_sesion_servicios():
    """Elimina el checkpoint de servicios al concluir exitosamente."""
    if os.path.exists(SESSION_STATE_SERV_FILE):
        try:
            os.remove(SESSION_STATE_SERV_FILE)
        except Exception:
            pass

def generar_reporte_auditoria_servicios(config: dict, config_servicio: dict, personas_exitosas: list, fallidos: list) -> str:
    """Genera reporte Excel de auditoría para servicios asentados."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = config.get("timestamp_str") or datetime.now().strftime("%Y-%m-%d_%H%M")
        ruta_excel = os.path.join(LOGS_DIR, f"Auditoria_Servicios_{ts}.xlsx")

        datos_ex = []
        for i, p in enumerate(personas_exitosas, 1):
            nom = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip() or "Usuario Registrado"
            datos_ex.append({
                "N°": i,
                "Cédula": f"V-{p['cedula']}" if not str(p['cedula']).startswith('E-') else str(p['cedula']),
                "Nombre y Apellido": nom,
                "Servicio Prestado": p.get('servicio_fila') or config_servicio.get('tipo_servicio'),
                "Fecha": p.get('fecha_fila') or config_servicio.get('fecha_servicio'),
                "Teléfono": p.get('telefono', ''),
                "Estado": "EXITOSO"
            })

        datos_fa = []
        for i, f in enumerate(fallidos, 1):
            p = f.get('participante', {})
            nom = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip() or "Usuario"
            datos_fa.append({
                "N°": i,
                "Cédula": f"V-{p.get('cedula', '')}" if not str(p.get('cedula', '')).startswith('E-') else str(p.get('cedula', '')),
                "Nombre y Apellido": nom,
                "Estado": f.get('estado', 'FALLIDO'),
                "Incidencia / Detalle": f.get('detalle', 'Error no especificado')
            })

        while True:
            try:
                with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
                    df_ex = pd.DataFrame(datos_ex) if datos_ex else pd.DataFrame([{"Mensaje": "Sin exitosos"}])
                    df_ex.to_excel(writer, sheet_name="Servicios Exitosos", index=False)
                    if datos_fa:
                        df_fa = pd.DataFrame(datos_fa)
                        df_fa.to_excel(writer, sheet_name="Incidencias", index=False)
                break
            except PermissionError:
                print(f"\n⚠️ El archivo '{os.path.basename(ruta_excel)}' está abierto en Excel o LibreOffice.")
                input("Por favor ciérralo y presiona Enter para reintentar el guardado...")

        return ruta_excel
    except Exception as e:
        print(f"⚠️ No se pudo generar el reporte Excel de servicios: {e}")
        return ""
