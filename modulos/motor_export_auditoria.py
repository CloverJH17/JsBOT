#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: MOTOR DE AUDITORÍA Y EXTRACCIÓN POR EXPORTACIÓN NATIVA (motor_export_auditoria.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation)
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
Propósito : Extracción ultra acelerada de datos oficiales de InfoApp mediante
            endpoints nativos de exportación CSV con mapeo dinámico de esquemas.
===============================================================================
"""

import io
import re
import csv
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup

def limpiar_campo_csv(val: str) -> str:
    """Elimina comillas envolventes y espacios innecesarios de los campos exportados."""
    if val is None:
        return ""
    s = str(val).strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1].strip()
    return s

def clasificar_actividad_datos(line_action: str, report_type: str, taller: str, title: str, prod_val: int) -> str:
    """
    Clasificación matemática y cualitativa oficial de actividades de Infocentro:
    1. Formaciones (Comunidades de aprendizaje / robótica / taller / cursos / alfabetización)
    2. Productos (Contenido digital / productos > 0 / comunicación popular)
    3. Otras actividades (Comunidades de participación digital / servicios de info / reuniones)
    """
    dims_lower = f"{line_action} {report_type} {taller} {title}".lower()
    
    if any(k in dims_lower for k in [
        "aprendizaje", "robótica", "robotica", "taller", "curso",
        "formación", "formacion", "capacitación", "capacitacion",
        "diplomado", "seminario", "alfabetización", "alfabetizacion", "inducción", "induccion"
    ]):
        return "formacion"
    elif prod_val > 0 or any(k in dims_lower for k in ["producto", "contenido", "medios digitales", "comunicación", "comunicacion", "diseño", "audiovisual"]):
        return "producto"
    else:
        return "otra"

def parsear_csv_actividades_infoapp(contenido_csv_bytes: bytes) -> list:
    """
    Parsea el contenido binario del CSV de actividades de InfoApp delimitado por pipe '|'.
    Mapea dinámicamente las columnas por nombre para máxima tolerancia a cambios de esquema.
    """
    if not contenido_csv_bytes:
        return []
        
    try:
        texto = contenido_csv_bytes.decode("utf-8")
    except UnicodeDecodeError:
        texto = contenido_csv_bytes.decode("latin1", errors="replace")
        
    reader = csv.reader(io.StringIO(texto), delimiter="|")
    filas = list(reader)
    if not filas or len(filas) <= 1:
        return []
        
    cabecera = [limpiar_campo_csv(c).lower() for c in filas[0]]
    col_map = {nombre: idx for idx, nombre in enumerate(cabecera)}
    
    def _val(r, col_name, idx_def=""):
        if col_name in col_map and col_map[col_name] < len(r):
            return limpiar_campo_csv(r[col_map[col_name]])
        if isinstance(idx_def, int) and idx_def < len(r):
            return limpiar_campo_csv(r[idx_def])
        return ""

    actividades = []
    ids_vistos = set()
    
    for r in filas[1:]:
        if len(r) < 10:
            continue
            
        act_id = _val(r, "id", 0)
        if not act_id or act_id in ids_vistos:
            continue
        ids_vistos.add(act_id)
        
        info_id_db = _val(r, "info_id", 1)
        code_info = _val(r, "code_info", 4)
        user_id = _val(r, "user_id", 5)
        line_action = _val(r, "line_action", 6)
        report_type = _val(r, "report_type", 7)
        estate_val = _val(r, "estate", 11)
        muni_val = _val(r, "municipality", 12)
        parish_val = _val(r, "parish", 13)
        title = _val(r, "activity_title", 16)
        date_ini = _val(r, "date_ini", 18)
        
        fe_str = _val(r, "person_fe", 25)
        ma_str = _val(r, "person_ma", 26)
        fe = int(fe_str) if fe_str.isdigit() else 0
        ma = int(ma_str) if ma_str.isdigit() else 0
        part_tot = fe + ma
        
        resp_name = _val(r, "responsible_name", 27)
        prod_str = _val(r, "total_products", 41)
        prod_val = int(prod_str) if prod_str.isdigit() else 0
        taller = _val(r, "tipo_taller", 42)
        
        if "-" in date_ini:
            partes_f = date_ini.split("-")
            if len(partes_f) == 3 and len(partes_f[0]) == 4:
                fecha_formato = f"{partes_f[2]}/{partes_f[1]}/{partes_f[0]}"
            else:
                fecha_formato = date_ini
        else:
            fecha_formato = date_ini
            
        dims = f"{line_action} % {report_type} % {taller}".strip(" %")
        if not dims:
            dims = title or "General"
            
        tipo_clasif = clasificar_actividad_datos(line_action, report_type, taller, title, prod_val)
        
        actividades.append({
            "id": act_id,
            "id_activity": act_id,
            "uid": user_id,
            "info_id": code_info or info_id_db,
            "dimensiones": dims,
            "area": report_type or line_action or "General",
            "taller": taller or title or "Actividad Institucional",
            "responsable": resp_name or f"UID {user_id}",
            "facilitador": resp_name or f"UID {user_id}",
            "linea_accion": line_action,
            "tipo_reporte": report_type,
            "titulo": title or taller or dims,
            "fecha": fecha_formato,
            "fecha_raw": date_ini,
            "participantes": part_tot,
            "part_fe": fe,
            "part_ma": ma,
            "productos": prod_val,
            "tipo_clasificacion": tipo_clasif,
            "estado": estate_val,
            "municipio": muni_val,
            "parroquia": parish_val,
        })
        
    return actividades

def parsear_csv_servicios_infoapp(contenido_csv_bytes: bytes) -> list:
    """
    Parsea el contenido binario del CSV de servicios de InfoApp delimitado por pipe '|'.
    Mapea dinámicamente las columnas por nombre para máxima tolerancia.
    """
    if not contenido_csv_bytes:
        return []
        
    try:
        texto = contenido_csv_bytes.decode("utf-8")
    except UnicodeDecodeError:
        texto = contenido_csv_bytes.decode("latin1", errors="replace")
        
    reader = csv.reader(io.StringIO(texto), delimiter="|")
    filas = list(reader)
    if not filas or len(filas) <= 1:
        return []
        
    cabecera = [limpiar_campo_csv(c).lower() for c in filas[0]]
    col_map = {nombre: idx for idx, nombre in enumerate(cabecera)}
    
    def _val(r, col_name, idx_def=""):
        if col_name in col_map and col_map[col_name] < len(r):
            return limpiar_campo_csv(r[col_map[col_name]])
        if isinstance(idx_def, int) and idx_def < len(r):
            return limpiar_campo_csv(r[idx_def])
        return ""

    servicios = []
    ids_vistos = set()
    
    for r in filas[1:]:
        if len(r) < 8:
            continue
            
        srv_id = _val(r, "id", 0)
        if not srv_id or srv_id in ids_vistos:
            continue
        ids_vistos.add(srv_id)
        
        user_id = _val(r, "user_id", 1)
        info_id_db = _val(r, "info_id", 2)
        info_cod = _val(r, "user_info_cod", 3)
        nombres = _val(r, "user_nombres", 4)
        apellidos = _val(r, "user_apellidos", 5)
        dni = _val(r, "user_dni", 6)
        tipo_srv = _val(r, "user_tipo_servicio", 24)
        fecha_srv = _val(r, "user_fecha_servicio", 25)
        profesion = _val(r, "user_profesion", 17)
        genero = _val(r, "user_genero", 9)
        edad = _val(r, "user_edad", 15)
        estado_val = _val(r, "user_estado", 21)
        muni_val = _val(r, "user_municipio", 22)
        
        if "-" in fecha_srv:
            partes_f = fecha_srv.split("-")
            if len(partes_f) == 3 and len(partes_f[0]) == 4:
                fecha_formato = f"{partes_f[2]}/{partes_f[1]}/{partes_f[0]}"
            else:
                fecha_formato = fecha_srv
        else:
            fecha_formato = fecha_srv
            
        nombre_completo = f"{nombres} {apellidos}".strip() or f"Usuario {srv_id}"
        cedula_val = dni if (dni and dni != "0") else "No cedulado"
        
        servicios.append({
            "id": srv_id,
            "uid": user_id,
            "info_id": info_cod or info_id_db,
            "servicio": tipo_srv or "Servicio Comunitario",
            "tipo_servicio": tipo_srv or "Servicio Comunitario",
            "cedula": cedula_val,
            "dni": dni,
            "id_usuario": user_id,
            "usuario": nombre_completo,
            "usuario_nombre": nombre_completo,
            "nombres": nombres,
            "apellidos": apellidos,
            "profesion": profesion or "S/D",
            "cedulado": bool(dni and dni != "0" and len(dni) >= 5),
            "fecha": fecha_formato,
            "fecha_raw": fecha_srv,
            "genero": genero,
            "edad": edad,
            "estado": estado_val,
            "municipio": muni_val,
        })
        
    return servicios

def consultar_actividades_infoapp_export(
    session: requests.Session,
    info_id: str = "",
    uid: str = "",
    estado: str = "",
    start_at: str = "2026-01-01",
    finish_at: str = "",
    callback_log=None
) -> tuple:
    """
    Descarga directamente el CSV de actividades de InfoApp en 1 petición HTTP.
    Utiliza consulta SQL directa a la tabla reports para obtener el 100% de los datos y conteos.
    """
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)
            
    log(f"⚡ [Auditor Nativo] Consultando endpoint de actividades ({start_at} al {finish_at})...")
    t0 = time.time()
    
    where_parts = []
    if estado:
        where_parts.append(f"estate LIKE '%{estado}%'")
    if info_id:
        where_parts.append(f"code_info = '{info_id}'")
    if uid:
        where_parts.append(f"user_id = '{uid}'")
    if start_at and finish_at:
        where_parts.append(f"(date_ini >= '{start_at}' AND date_ini <= '{finish_at}')")
    elif start_at:
        where_parts.append(f"date_ini >= '{start_at}'")
    elif finish_at:
        where_parts.append(f"date_ini <= '{finish_at}'")
        
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    sql = f"SELECT * FROM reports WHERE {where_sql} ORDER BY date_ini DESC"
    
    url_csv = "https://infoapp2.infocentro.gob.ve/admin/pdf/csv_pdo.php"
    params = {
        "param_csv": sql,
        "param_sql": "true",
        "DB_name": "reports"
    }
    
    log("📥 Descargando archivo consolidado oficial de Actividades desde InfoApp...")
    try:
        r_csv = session.get(url_csv, params=params, verify=False, timeout=45)
        if r_csv.status_code == 200 and r_csv.content and b"Fatal error" not in r_csv.content:
            actividades_csv = parsear_csv_actividades_infoapp(r_csv.content)
            if actividades_csv:
                t_tot = time.time() - t0
                log(f"✅ [Actividades Consolidadas] {len(actividades_csv)} registros procesados en {t_tot:.2f}s.")
                return len(actividades_csv), actividades_csv
    except Exception as e:
        log(f"⚠️ Error en descarga directa CSV: {e}")
        
    # Fallback tradicional HTTP Crawler
    log("ℹ️ Conmutando a rastreador HTTP concurrente de contingencia...")
    from modulos.auditor_reportes import consultar_actividades_infoapp_http_crawler
    return consultar_actividades_infoapp_http_crawler(session, info_id, uid, estado, start_at, finish_at, callback_log=callback_log)

def consultar_servicios_infoapp_export(
    session: requests.Session,
    info_id: str = "",
    uid: str = "",
    estado: str = "",
    start_at: str = "2026-01-01",
    finish_at: str = "",
    callback_log=None
) -> tuple:
    """
    Descarga directamente el CSV de servicios de InfoApp en 1 petición HTTP.
    100% exacto e instantáneo.
    """
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)
            
    log(f"⚡ [Servicios Nativo] Consultando endpoint de servicios ({start_at} al {finish_at})...")
    t0 = time.time()
    
    where_parts = []
    if estado:
        where_parts.append(f"user_estado LIKE '%{estado}%'")
    if info_id:
        where_parts.append(f"user_info_cod = '{info_id}'")
    if uid:
        where_parts.append(f"user_id = '{uid}'")
    if start_at and finish_at:
        where_parts.append(f"(user_fecha_servicio >= '{start_at}' AND user_fecha_servicio <= '{finish_at}')")
    elif start_at:
        where_parts.append(f"user_fecha_servicio >= '{start_at}'")
    elif finish_at:
        where_parts.append(f"user_fecha_servicio <= '{finish_at}'")
        
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    sql = f"SELECT * FROM services_users WHERE {where_sql} ORDER BY user_fecha_servicio DESC"
    
    url_csv = "https://infoapp2.infocentro.gob.ve/admin/pdf/csv_pdo.php"
    params = {
        "param_csv": sql,
        "param_sql": "true",
        "DB_name": "services_users"
    }
    
    log("📥 Descargando archivo consolidado oficial de Servicios desde InfoApp...")
    try:
        r_csv = session.get(url_csv, params=params, verify=False, timeout=45)
        if r_csv.status_code == 200 and r_csv.content and b"Fatal error" not in r_csv.content:
            servicios_csv = parsear_csv_servicios_infoapp(r_csv.content)
            t_tot = time.time() - t0
            log(f"✅ [Servicios Consolidados] {len(servicios_csv)} atenciones extraídas en {t_tot:.2f}s.")
            return len(servicios_csv), servicios_csv
    except Exception as e:
        log(f"⚠️ Error en descarga directa CSV servicios: {e}")
        
    # Fallback tradicional HTTP
    log("ℹ️ Conmutando a rastreador HTTP de servicios...")
    from modulos.auditor_reportes import consultar_servicios_infoapp_http_crawler
    return consultar_servicios_infoapp_http_crawler(session, info_id, uid, estado, start_at, finish_at, callback_log=callback_log)
