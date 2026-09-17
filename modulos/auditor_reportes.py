#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: AUDITOR DE REPORTES E INSPECCIÓN ADMINISTRATIVA (auditor_reportes.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
Propósito : Extracción acelerada híbrida (Playwright login + HTTP Session concurrent),
            clasificación cualitativa/cuantitativa, balance matemático y
            generación de reportes Excel profesionales agrupados por Infocentro.
===============================================================================
"""

import os
import re
import sys
import time
import json
import zipfile
import csv
import configparser
import concurrent.futures
from datetime import datetime, timedelta
from collections import Counter
import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright

import modulos.entorno as entorno

BASE_DIR = str(entorno.RAIZ_PROYECTO)
CONFIG_DIR = str(entorno.CARPETA_CONFIG)
CONFIG_PATH = str(entorno.ARCHIVO_CONFIG_INI)
REPORTES_DIR = os.path.join(BASE_DIR, "Reportes_Auditoria")
CACHE_INSPECTOR_PATH = os.path.join(str(entorno.CARPETA_LOGS), "ultima_busqueda_inspector.json")
from modulos.identidad_utils import LISTA_ESTADOS_VENEZUELA

def guardar_cache_inspector(resultado: dict, ruta_archivo: str = None) -> str:
    """
    Almacena temporalmente los resultados de auditoría en un archivo JSON ligero
    (logs/ultima_busqueda_inspector.json) para agilizar filtros locales y recargas.
    """
    if not ruta_archivo:
        ruta_archivo = CACHE_INSPECTOR_PATH

    os.makedirs(os.path.dirname(os.path.abspath(ruta_archivo)), exist_ok=True)

    # Sanitizar estructura para asegurar compatibilidad JSON pura (ej. Counter)
    conteo_srv = resultado.get("conteo_servicios", {})
    if hasattr(conteo_srv, "items"):
        conteo_srv = dict(conteo_srv)
    elif not isinstance(conteo_srv, dict):
        conteo_srv = {}

    datos_cache = {
        "timestamp": datetime.now().isoformat(),
        "exito": bool(resultado.get("exito", True)),
        "criterio_tipo": str(resultado.get("criterio_tipo", "uid")),
        "criterio_valor": str(resultado.get("criterio_valor", "")),
        "f_ini": str(resultado.get("f_ini") or resultado.get("fecha_inicio", "")),
        "f_fin": str(resultado.get("f_fin") or resultado.get("fecha_fin", "")),
        "facilitador_principal": str(resultado.get("facilitador_principal", "")),
        "total_actividades": int(resultado.get("total_actividades", 0)),
        "total_procesadas": int(resultado.get("total_procesadas", 0)),
        "formaciones": list(resultado.get("formaciones", [])),
        "productos": list(resultado.get("productos", [])),
        "otras_actividades": list(resultado.get("otras_actividades", [])),
        "total_estudiantes": int(resultado.get("total_estudiantes", 0)),
        "total_servicios": int(resultado.get("total_servicios", 0)),
        "servicios": list(resultado.get("servicios", [])),
        "conteo_servicios": conteo_srv,
        "cedulados_serv": int(resultado.get("cedulados_serv", 0)),
        "no_cedulados_serv": int(resultado.get("no_cedulados_serv", 0)),
        "resumen_facilitadores": dict(resultado.get("resumen_facilitadores", {})),
        "cuadre_perfecto": bool(resultado.get("cuadre_perfecto", False)),
        "archivo_exportado": str(resultado.get("archivo_exportado", ""))
    }

    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(datos_cache, f, ensure_ascii=False, indent=2)
        return ruta_archivo
    except Exception:
        return ""

def cargar_cache_inspector(ruta_archivo: str = None) -> dict:
    """
    Carga los resultados cacheados de la última búsqueda desde el archivo JSON.
    Retorna un diccionario vacío si el archivo no existe o está corrupto.
    """
    if not ruta_archivo:
        ruta_archivo = CACHE_INSPECTOR_PATH

    if not os.path.exists(ruta_archivo):
        return {}

    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if isinstance(datos, dict):
                return datos
            return {}
    except Exception:
        return {}

def cargar_credenciales_auditoria(rol_auditor: bool = False) -> tuple:
    """Carga credenciales desde config/config.ini con soporte de perfil Auditor/Jefe."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        try:
            config.read(CONFIG_PATH, encoding="utf-8")
        except Exception:
            pass
        if rol_auditor and config.has_section("AUDITORIA"):
            u_aud = config.get("AUDITORIA", "usuario", fallback="").strip()
            c_aud = config.get("AUDITORIA", "clave", fallback="").strip()
            if u_aud and c_aud:
                return u_aud, c_aud
        if config.has_section("LOGIN"):
            u = config.get("LOGIN", "usuario", fallback="").strip()
            c = config.get("LOGIN", "clave", fallback="").strip()
            if u and c:
                return u, c
        if config.has_section("CREDENCIALES"):
            u = config.get("CREDENCIALES", "usuario", fallback="").strip()
            c = config.get("CREDENCIALES", "clave", fallback="").strip()
            if u and c:
                return u, c
    return "", ""

def iniciar_driver_auditoria(headless: bool = True):
    """Instancia un contexto Playwright para autenticación en InfoApp respetando la prioridad de navegador."""
    from modulos.driver_factory import obtener_contexto_playwright
    from modulos import config_manager as _cm
    cfg = _cm.obtener_browser_cfg()
    nav = cfg["priority"][0] if cfg["priority"] else "firefox"
    user_data_dir = str(entorno.CARPETA_DATA / "playwright_context")
    pw, context = obtener_contexto_playwright(headless=headless, navegador=nav, user_data_dir=user_data_dir)
    page = context.pages[0] if context.pages else context.new_page()
    # Retornamos un objeto que simula la interfaz usada en ejecutar_auditoria
    return _PlaywrightDriverAdapter(pw, context, page)

class _PlaywrightDriverAdapter:
    """Adaptador interno que expone la interfaz mínima esperada por ejecutar_auditoria."""
    def __init__(self, pw, context, page):
        self._pw = pw
        self._context = context
        self.page = page

    def get_cookies(self):
        """Retorna las cookies del contexto en formato compatible con requests.Session."""
        return [
            {"name": c["name"], "value": c["value"],
             "domain": c.get("domain", ""), "path": c.get("path", "/")}
            for c in self._context.cookies()
        ]

    def quit(self):
        try:
            self._context.close()
        except Exception:
            pass
        try:
            self._pw.stop()
        except Exception:
            pass

def autenticar_infoapp(driver, usuario: str, clave: str) -> bool:
    """Inicia sesión en el portal de administración de InfoApp con Playwright."""
    from modulos.web_utils import realizar_login_infoapp
    return realizar_login_infoapp(driver.page, usuario, clave)

# =============================================================================
# 1. PARSEO DE CONTENIDO CON BEAUTIFULSOUP (HTML)
# =============================================================================
def parsear_pagina_actividades_bs4(html: str, default_info_id: str = "", default_uid: str = "") -> list:
    """
    Extrae las actividades de una página HTML de InfoApp usando BeautifulSoup con arquitectura de máxima resiliencia:
    1. Selector agnóstico a <tbody> (crítico para Requests HTTP donde InfoApp no incluye <tbody>).
    2. Extracción de metadatos profundos desde los enlaces href de los badges (id_activity, line_action, report_type, code_info, user_id, título completo).
    3. Extracción estructural desde celdas <td> (fecha, facilitador, infocentro, tema/taller, participantes, productos).
    4. Fallback a etiquetas <p> si existieran en el DOM.
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    # Selector agnóstico a <tbody> (resuelve discrepancia entre Selenium DOM y Requests raw HTML)
    filas = soup.select("table.table-hover tr") or soup.select("table.table tr") or soup.select("table tr")
    actividades = []

    for f in filas:
        tds = f.find_all("td")
        if len(tds) < 4:
            continue

        # Descartar filas de cabecera o avisos informativos
        if f.find("th") or not any(td.get_text(strip=True) for td in tds):
            continue

        textos_td = [td.get_text(strip=True) for td in tds]
        if len(tds) == 1 and ("no hay" in textos_td[0].lower() or "no se encontraron" in textos_td[0].lower()):
            continue

        # 1. Badges de Participantes y Productos
        b_part = (
            f.select_one("a[href*='view=participants_list']")
            or f.select_one("a.btn-info")
            or f.select_one(".badge-info")
            or f.select_one("a[class*='btn-info']")
            or f.select_one("span[class*='badge-info']")
            or f.select_one("a[href*='id_activity'][class*='info']")
        )
        b_prod = (
            f.select_one("a[href*='view=products_list']")
            or f.select_one("a.btn-danger")
            or f.select_one(".badge-danger")
            or f.select_one("a[class*='btn-danger']")
            or f.select_one("span[class*='badge-danger']")
            or f.select_one("a[href*='id_activity'][class*='danger']")
        )

        part = 0
        if b_part:
            m_part = re.search(r'\b(\d+)\b', b_part.get_text(strip=True))
            if m_part:
                part = int(m_part.group(1))

        prod = 0
        if b_prod:
            m_prod = re.search(r'\b(\d+)\b', b_prod.get_text(strip=True))
            if m_prod:
                prod = int(m_prod.group(1))

        # Si aún es 0 o no se encontró el badge, buscar en las columnas de la tabla
        if part == 0 and len(tds) > 4:
            for td_elem in tds[4:]:
                if "participants" in str(td_elem).lower() or td_elem.select_one(".badge-info, .btn-info, a[href*='participants']"):
                    m = re.search(r'\b(\d+)\b', td_elem.get_text(strip=True))
                    if m and int(m.group(1)) > 0:
                        part = int(m.group(1))
                        break

        # Fallback posicional para tabla estándar de InfoApp view=report (9 columnas)
        if len(tds) >= 7:
            if part == 0:
                m_td5 = re.search(r'\b(\d+)\b', tds[5].get_text(strip=True))
                if m_td5:
                    part = int(m_td5.group(1))
            if prod == 0:
                m_td6 = re.search(r'\b(\d+)\b', tds[6].get_text(strip=True))
                if m_td6:
                    prod = int(m_td6.group(1))

        # Extraer parámetros de consulta desde los enlaces href de la fila
        params_href = {}
        for a in f.select("a[href]"):
            href = a.get("href", "")
            if "id_activity=" in href or "view=participants_list" in href or "view=products_list" in href or "view=image_edit" in href:
                parsed = parse_qs(urlparse(href).query)
                for k, v in parsed.items():
                    if v and k not in params_href:
                        params_href[k] = v[0]

        id_act = params_href.get("id_activity", "")
        f_uid = params_href.get("user_id", "")
        sede_info = params_href.get("code_info", "")
        titulo_href = params_href.get("activity") or params_href.get("activity_title", "") or params_href.get("title", "")

        # 2. Fecha de ejecución (td 0)
        span_fecha = f.select_one("td:nth-of-type(1) span") or tds[0].find("span")
        fecha_ejec = span_fecha.get_text(strip=True) if span_fecha else tds[0].get_text(strip=True)

        # 3. Metadatos de etiquetas <p> ocultas (si existieran en el DOM)
        r_id = f.select_one("p.id_activity")
        r_tit = f.select_one("p.data_titulo")
        r_dim = f.select_one("p.data_dimensiones")
        r_resp = f.select_one("p.responsible_name")
        r_uid = f.select_one("p.user_id")

        if not id_act and r_id:
            id_act = r_id.get("id") or r_id.get_text(strip=True)
        if r_tit and not titulo_href:
            titulo_href = r_tit.get("id") or r_tit.get_text(strip=True)
        dims_p = (r_dim.get("id") or r_dim.get_text(strip=True)) if r_dim else ""
        resp_p = (r_resp.get("id") or r_resp.get_text(strip=True)) if r_resp else ""
        if not f_uid and r_uid:
            f_uid = r_uid.get("id") or r_uid.get_text(strip=True)

        # 4. Fallback estructural desde celdas <td>
        if len(tds) >= 7:
            # Formato estándar de InfoApp view=report (9 columnas):
            # td[0]: Fecha ejec, td[1]: Publicado, td[2]: Facilitador/Sede/UID, td[3]: Línea de acción, td[4]: Título, td[5]: Part, td[6]: Prod
            txt_fac = tds[2].get_text(" ", strip=True)
            if not f_uid:
                m_uid = re.search(r"UID:\s*(\d+)", txt_fac, re.IGNORECASE)
                f_uid = m_uid.group(1) if m_uid else ""
            if not sede_info:
                m_info = re.search(r"\b([A-Z]{3,}\d+)\b", txt_fac)
                sede_info = m_info.group(1) if m_info else ""

            resp = resp_p or txt_fac
            resp = re.sub(r"UID:\s*\d+", "", resp, flags=re.IGNORECASE)
            if sede_info:
                resp = resp.replace(sede_info, "")
            resp = re.sub(r"\bFacilitador\b|\bCoordinador\b|\bAdministrador\b", "", resp, flags=re.IGNORECASE).strip()

            linea_accion_td = tds[3].get_text(" % ", strip=True)
            linea_href = params_href.get("line_action", "")
            rep_type_href = params_href.get("report_type", "")
            dims_list = [d.strip() for d in [linea_href, rep_type_href, linea_accion_td] if d.strip()]
            dims = " % ".join(dims_list) if dims_list else (dims_p or linea_accion_td)

            titulo_td = tds[4].get_text(" ", strip=True)
            titulo = titulo_href or titulo_td
        else:
            # Formato simplificado (ej. mocks con 5 columnas):
            titulo = titulo_href or (tds[1].get_text(" ", strip=True) if len(tds) > 1 else "")
            dims = dims_p or (tds[1].get_text(" % ", strip=True) if len(tds) > 1 else "")
            if not sede_info and len(tds) > 2:
                sede_info = tds[2].get_text(strip=True)
            txt_resp = tds[3].get_text(" ", strip=True) if len(tds) > 3 else ""
            m_uid = re.search(r"^(\d+)\s*[-:]\s*(.+)$", txt_resp) or re.search(r"UID:\s*(\d+)", txt_resp)
            if m_uid:
                if not f_uid:
                    f_uid = m_uid.group(1)
                resp = resp_p or (m_uid.group(2).strip() if len(m_uid.groups()) > 1 and m_uid.group(2) else txt_resp)
            else:
                resp = resp_p or txt_resp

        if not f_uid:
            f_uid = default_uid
        if not sede_info:
            sede_info = default_info_id

        # Validar si la fila representa una actividad válida
        if not id_act and not titulo and not dims and not resp and b_part is None and b_prod is None:
            continue

        if not id_act:
            if f.get("id"):
                id_act = f.get("id")
            else:
                id_act = f"ACT_{len(actividades) + 1}_{fecha_ejec.replace('-', '').replace('/', '')}"

        dims_partes = [d.strip() for d in dims.split("%") if d.strip()]
        taller = dims_partes[-1] if dims_partes else titulo
        area = dims_partes[-2] if len(dims_partes) > 1 else taller

        actividades.append({
            "id": id_act,
            "id_activity": id_act,
            "fecha": fecha_ejec,
            "titulo": titulo,
            "dimensiones": dims,
            "area": area,
            "taller": taller,
            "responsable": resp,
            "uid": f_uid or default_uid,
            "info_id": sede_info or default_info_id,
            "participantes": part,
            "productos": prod
        })

    return actividades

def parsear_pagina_servicios_bs4(html: str, default_info_id: str = "", default_uid: str = "") -> list:
    """Extrae los servicios de una página HTML de InfoApp usando BeautifulSoup agnóstico a <tbody>."""
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    filas = soup.select("table.table-bordered tr") or soup.select("table.table-hover tr") or soup.select("table tr")
    servicios = []

    for f in filas:
        if f.find("th"):
            continue
        tds = f.find_all("td")
        if len(tds) >= 10:
            if not any(td.get_text(strip=True) for td in tds):
                continue
            uid_row = tds[0].get_text(strip=True)
            fecha_s = tds[1].get_text(strip=True)
            info_row = tds[3].get_text(strip=True)
            tipo_s = tds[5].get_text(strip=True)
            cedula = tds[6].get_text(strip=True)
            id_usr = tds[7].get_text(strip=True)
            nombre_usr = tds[8].get_text(strip=True)
            profesion = tds[9].get_text(strip=True)

            servicios.append({
                "uid": uid_row or default_uid,
                "fecha": fecha_s,
                "info_id": info_row or default_info_id,
                "servicio": tipo_s,
                "cedula": cedula,
                "id_usuario": id_usr,
                "usuario": nombre_usr,
                "profesion": profesion
            })

    return servicios

# =============================================================================
# 2. EXTRACCIÓN ACELERADA HTTP CON REQUESTS + CONCURRENCIA
# =============================================================================
def _generar_rango_dias_auditoria(start_at: str, finish_at: str) -> list:
    """Genera lista de fechas YYYY-MM-DD entre start_at y finish_at inclusive."""
    try:
        dt_ini = datetime.strptime(str(start_at).strip(), "%Y-%m-%d")
        dt_fin = datetime.strptime(str(finish_at).strip(), "%Y-%m-%d")
        if dt_ini > dt_fin:
            return []
        dias = []
        curr = dt_ini
        while curr <= dt_fin:
            dias.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)
        return dias
    except Exception:
        return []

def consultar_actividades_infoapp_http(session: requests.Session, info_id: str, uid: str, estado: str,
                                       start_at: str, finish_at: str, callback_log=None) -> tuple:
    """Extrae todas las actividades en view=report mediante exportación nativa directa con fallback concurrente."""
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    # Intento 1: Motor de exportación nativa ultra rápido v4.8.0
    try:
        from modulos.motor_export_auditoria import consultar_actividades_infoapp_export
        total_exp, acts_exp = consultar_actividades_infoapp_export(
            session, info_id=info_id, uid=uid, estado=estado,
            start_at=start_at, finish_at=finish_at, callback_log=callback_log
        )
        if total_exp > 0:
            return total_exp, acts_exp
    except Exception as err_exp:
        log(f"⚠️ Nota de aceleración nativa: {err_exp}. Continuando con escaneo...")

    # Si hay rango de fechas de hasta 90 días, particionar por día para evitar el bug de paginación del backend InfoApp
    dias = _generar_rango_dias_auditoria(start_at, finish_at)
    if dias and len(dias) <= 90:
        log(f"⚡ [Auditoría Acelerada] Escaneando {len(dias)} días en paralelo ({start_at} al {finish_at})...")
        mapa_actividades = {}
        sin_id = []

        def descargar_dia(dia_str):
            acts_dia = []
            url_dia = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
                f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
                f"&start_at={dia_str}&finish_at={dia_str}&id_act=&pag=1"
            )
            try:
                r = session.get(url_dia, timeout=25)
                html_dia = r.text
                m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html_dia, re.IGNORECASE)
                pags_dia = int(m_pag.group(1)) if m_pag else 1
                parsed = parsear_pagina_actividades_bs4(html_dia, default_info_id=info_id, default_uid=uid)
                acts_dia.extend(parsed)

                if pags_dia > 1:
                    for p_sub in range(2, pags_dia + 1):
                        url_sub = (
                            f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
                            f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
                            f"&start_at={dia_str}&finish_at={dia_str}&id_act=&pag={p_sub}"
                        )
                        r_sub = session.get(url_sub, timeout=25)
                        acts_dia.extend(parsear_pagina_actividades_bs4(r_sub.text, default_info_id=info_id, default_uid=uid))
            except Exception:
                pass
            return dia_str, acts_dia

        max_workers = min(15, max(4, len(dias)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = [executor.submit(descargar_dia, d) for d in dias]
            for fut in concurrent.futures.as_completed(futuros):
                d_str, acts = fut.result()
                for a in acts:
                    id_act = a.get("id") or a.get("id_actividad") or a.get("id_activity")
                    if id_act:
                        if id_act not in mapa_actividades:
                            mapa_actividades[id_act] = a
                    else:
                        sin_id.append(a)

        todas_actividades = list(mapa_actividades.values()) + sin_id
        # Ordenar por fecha cronológica descendente si es posible
        todas_actividades.sort(key=lambda x: str(x.get("fecha", "")), reverse=True)
        total_registros = len(todas_actividades)
        log(f"✅ [Actividades HTTP] Total único consolidado: {total_registros} actividades extraídas sin omisiones.")
        return total_registros, todas_actividades

    url_base = (
        f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
        f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
        f"&start_at={start_at}&finish_at={finish_at}&id_act=&pag=1"
    )

    try:
        resp = session.get(url_base, timeout=25)
        html = resp.text
    except requests.exceptions.RequestException as req_err:
        log(f"❌ [Error de Red] No se pudo conectar a InfoApp: {req_err}")
        raise RuntimeError(f"Fallo de conexión con InfoApp (verifique su conexión a Internet o DNS): {req_err}") from req_err

    m_tot = re.search(r'Hay\s+(\d+)\s+Registros', html, re.IGNORECASE)
    m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html, re.IGNORECASE)

    total_registros = int(m_tot.group(1)) if m_tot else 0
    total_paginas = int(m_pag.group(1)) if m_pag else 1

    log(f"⚡ [Actividades HTTP] Reportadas en plataforma: {total_registros} ({total_paginas} página/s)")

    if total_registros == 0:
        return 0, []

    actividades_por_pag = {1: parsear_pagina_actividades_bs4(html, default_info_id=info_id, default_uid=uid)}
    log(f"   ✓ Página 1/{total_paginas} procesada ({len(actividades_por_pag[1])} actividades)")

    if total_paginas > 1:
        def descargar_pag(p):
            url_p = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
                f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
                f"&start_at={start_at}&finish_at={finish_at}&id_act=&pag={p}"
            )
            try:
                r = session.get(url_p, timeout=25)
                return p, parsear_pagina_actividades_bs4(r.text, default_info_id=info_id, default_uid=uid)
            except Exception:
                return p, []

        max_workers = min(10, total_paginas)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = [executor.submit(descargar_pag, p) for p in range(2, total_paginas + 1)]
            for fut in concurrent.futures.as_completed(futuros):
                p_num, acts = fut.result()
                actividades_por_pag[p_num] = acts
                log(f"   ✓ Página {p_num}/{total_paginas} procesada ({len(acts)} actividades)")

    todas_actividades = []
    for p in range(1, total_paginas + 1):
        todas_actividades.extend(actividades_por_pag.get(p, []))

    return total_registros, todas_actividades

def consultar_servicios_infoapp_http(session: requests.Session, info_id: str, uid: str, estado: str,
                                     start_at: str, finish_at: str, callback_log=None) -> tuple:
    """Extrae todos los servicios en view=services mediante exportación nativa directa con fallback concurrente."""
    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    # Intento 1: Motor de exportación nativa ultra rápido v4.8.0
    try:
        from modulos.motor_export_auditoria import consultar_servicios_infoapp_export
        total_exp, srvs_exp = consultar_servicios_infoapp_export(
            session, info_id=info_id, uid=uid, estado=estado,
            start_at=start_at, finish_at=finish_at, callback_log=callback_log
        )
        if total_exp > 0:
            return total_exp, srvs_exp
    except Exception as err_exp:
        log(f"⚠️ Nota de aceleración nativa: {err_exp}. Continuando con escaneo...")

    dias = _generar_rango_dias_auditoria(start_at, finish_at)
    if dias and len(dias) <= 90:
        log(f"⚡ [Servicios Acelerados] Escaneando {len(dias)} días en paralelo ({start_at} al {finish_at})...")
        todos_servicios = []

        def descargar_dia_srv(dia_str):
            srvs_dia = []
            url_dia = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
                f"&info_id={info_id}&uid={uid}&user_estado={estado}"
                f"&start_at={dia_str}&finish_at={dia_str}&pag=1"
            )
            try:
                r = session.get(url_dia, timeout=25)
                html_dia = r.text
                m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html_dia, re.IGNORECASE)
                pags_dia = int(m_pag.group(1)) if m_pag else 1
                parsed = parsear_pagina_servicios_bs4(html_dia, default_info_id=info_id, default_uid=uid)
                srvs_dia.extend(parsed)

                if pags_dia > 1:
                    for p_sub in range(2, pags_dia + 1):
                        url_sub = (
                            f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
                            f"&info_id={info_id}&uid={uid}&user_estado={estado}"
                            f"&start_at={dia_str}&finish_at={dia_str}&pag={p_sub}"
                        )
                        r_sub = session.get(url_sub, timeout=25)
                        srvs_dia.extend(parsear_pagina_servicios_bs4(r_sub.text, default_info_id=info_id, default_uid=uid))
            except Exception:
                pass
            return dia_str, srvs_dia

        max_workers = min(15, max(4, len(dias)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = [executor.submit(descargar_dia_srv, d) for d in dias]
            for fut in concurrent.futures.as_completed(futuros):
                _, srvs = fut.result()
                todos_servicios.extend(srvs)

        todos_servicios.sort(key=lambda x: str(x.get("fecha", "")), reverse=True)
        total_servicios = len(todos_servicios)
        log(f"✅ [Servicios HTTP] Total único consolidado: {total_servicios} atenciones extraídas.")
        return total_servicios, todos_servicios

    url_base = (
        f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
        f"&info_id={info_id}&uid={uid}&user_estado={estado}"
        f"&start_at={start_at}&finish_at={finish_at}&pag=1"
    )

    try:
        resp = session.get(url_base, timeout=25)
        html = resp.text
    except requests.exceptions.RequestException as req_err:
        log(f"❌ [Error de Red] No se pudo consultar servicios en InfoApp: {req_err}")
        raise RuntimeError(f"Fallo de conexión al consultar servicios en InfoApp: {req_err}") from req_err

    m_tot = re.search(r'Hay\s+(\d+)\s+Registros', html, re.IGNORECASE)
    m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html, re.IGNORECASE)

    total_servicios = int(m_tot.group(1)) if m_tot else 0
    total_paginas = int(m_pag.group(1)) if m_pag else 1

    log(f"⚡ [Servicios HTTP] Reportados en plataforma: {total_servicios} ({total_paginas} página/s)")

    if total_servicios == 0:
        return 0, []

    servicios_por_pag = {1: parsear_pagina_servicios_bs4(html, default_info_id=info_id, default_uid=uid)}
    log(f"   ✓ Página 1/{total_paginas} de servicios procesada ({len(servicios_por_pag[1])} atenciones)")

    if total_paginas > 1:
        def descargar_pag(p):
            url_p = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
                f"&info_id={info_id}&uid={uid}&user_estado={estado}"
                f"&start_at={start_at}&finish_at={finish_at}&pag={p}"
            )
            try:
                r = session.get(url_p, timeout=25)
                return p, parsear_pagina_servicios_bs4(r.text, default_info_id=info_id, default_uid=uid)
            except Exception:
                return p, []

        max_workers = min(10, total_paginas)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = [executor.submit(descargar_pag, p) for p in range(2, total_paginas + 1)]
            for fut in concurrent.futures.as_completed(futuros):
                p_num, srvs = fut.result()
                servicios_por_pag[p_num] = srvs
                log(f"   ✓ Página {p_num}/{total_paginas} de servicios procesada ({len(srvs)} atenciones)")

    todos_servicios = []
    for p in range(1, total_paginas + 1):
        todos_servicios.extend(servicios_por_pag.get(p, []))

    return total_servicios, todos_servicios

# =============================================================================
# 3. MÉTODOS COMPATIBLES DE EXTRACCIÓN (PLAYWRIGHT FALLBACK)
# =============================================================================
def consultar_actividades_infoapp_playwright(page, info_id: str, uid: str, estado: str,
                                              start_at: str, finish_at: str,
                                              callback_log=None) -> tuple:
    """Fallback de extracción de actividades mediante Playwright (page.goto + page.content)."""
    from modulos.web_utils import esperar_desbloqueo_ajax, limpiar_overlays

    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    url_base = (
        f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
        f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
        f"&start_at={start_at}&finish_at={finish_at}&id_act=&pag=1"
    )
    page.goto(url_base, wait_until="domcontentloaded")
    esperar_desbloqueo_ajax(page)

    html = page.content()
    m_tot = re.search(r'Hay\s+(\d+)\s+Registros', html, re.IGNORECASE)
    m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html, re.IGNORECASE)

    total_registros = int(m_tot.group(1)) if m_tot else 0
    total_paginas = int(m_pag.group(1)) if m_pag else 1

    log(f"📊 [Actividades] Reportadas en plataforma: {total_registros} ({total_paginas} página/s)")

    actividades = []
    if total_registros == 0:
        return 0, actividades

    for p in range(1, total_paginas + 1):
        if p > 1:
            url_p = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=report"
                f"&linea_accion=&q=&info_id={info_id}&uid={uid}&estado={estado}"
                f"&start_at={start_at}&finish_at={finish_at}&id_act=&pag={p}"
            )
            page.goto(url_p, wait_until="domcontentloaded")
            esperar_desbloqueo_ajax(page)

        p_acts = parsear_pagina_actividades_bs4(page.content(), default_info_id=info_id, default_uid=uid)
        actividades.extend(p_acts)
        log(f"   ✓ Página {p}/{total_paginas} procesada ({len(actividades)} actividades acumuladas)")

    return total_registros, actividades

def consultar_servicios_infoapp_playwright(page, info_id: str, uid: str, estado: str,
                                            start_at: str, finish_at: str,
                                            callback_log=None) -> tuple:
    """Fallback de extracción de servicios mediante Playwright (page.goto + page.content)."""
    from modulos.web_utils import esperar_desbloqueo_ajax, limpiar_overlays

    def log(msg):
        if callback_log:
            callback_log(msg)
        else:
            print(msg)

    url_base = (
        f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
        f"&info_id={info_id}&uid={uid}&user_estado={estado}"
        f"&start_at={start_at}&finish_at={finish_at}&pag=1"
    )
    page.goto(url_base, wait_until="domcontentloaded")
    esperar_desbloqueo_ajax(page)

    html = page.content()
    m_tot = re.search(r'Hay\s+(\d+)\s+Registros', html, re.IGNORECASE)
    m_pag = re.search(r'dividió a\s+(\d+)\s+páginas', html, re.IGNORECASE)

    total_servicios = int(m_tot.group(1)) if m_tot else 0
    total_paginas = int(m_pag.group(1)) if m_pag else 1

    log(f"🛠️ [Servicios] Reportados en plataforma: {total_servicios} ({total_paginas} página/s)")

    servicios = []
    if total_servicios == 0:
        return 0, servicios

    for p in range(1, total_paginas + 1):
        if p > 1:
            url_p = (
                f"https://infoapp2.infocentro.gob.ve/admin/index.php?view=services&q="
                f"&info_id={info_id}&uid={uid}&user_estado={estado}"
                f"&start_at={start_at}&finish_at={finish_at}&pag={p}"
            )
            page.goto(url_p, wait_until="domcontentloaded")
            esperar_desbloqueo_ajax(page)

        p_srvs = parsear_pagina_servicios_bs4(page.content(), default_info_id=info_id, default_uid=uid)
        servicios.extend(p_srvs)
        log(f"   ✓ Página {p}/{total_paginas} de servicios procesada ({len(servicios)} atenciones acumuladas)")

    return total_servicios, servicios

def consultar_actividades_infoapp(target, info_id: str, uid: str, estado: str,
                                  start_at: str, finish_at: str,
                                  callback_log=None) -> tuple:
    """Punto de entrada universal: despacha a HTTP Session o Playwright Page según el tipo de objeto."""
    if isinstance(target, requests.Session):
        return consultar_actividades_infoapp_http(
            target, info_id, uid, estado, start_at, finish_at, callback_log=callback_log
        )
    # Fallback Playwright — target es una Playwright Page
    return consultar_actividades_infoapp_playwright(
        target, info_id, uid, estado, start_at, finish_at, callback_log=callback_log
    )

def consultar_servicios_infoapp(target, info_id: str, uid: str, estado: str,
                                start_at: str, finish_at: str,
                                callback_log=None) -> tuple:
    """Punto de entrada universal: despacha a HTTP Session o Playwright Page según el tipo de objeto."""
    if isinstance(target, requests.Session):
        return consultar_servicios_infoapp_http(
            target, info_id, uid, estado, start_at, finish_at, callback_log=callback_log
        )
    # Fallback Playwright — target es una Playwright Page
    return consultar_servicios_infoapp_playwright(
        target, info_id, uid, estado, start_at, finish_at, callback_log=callback_log
    )

# =============================================================================
# 4. EXPORTADOR PROFESIONAL MULTIFORMATO (EXCEL, ODT, PDF, CSV, CONSOLA)
# =============================================================================

def generar_resumen_consola(resultado: dict) -> str:
    """Genera un reporte ejecutivo en formato texto plano de alta legibilidad para consola/telemetría."""
    criterio = f"{resultado.get('criterio_tipo', '').upper()}: {resultado.get('criterio_valor', '')}"
    f_ini = resultado.get('f_ini') or resultado.get('fecha_inicio', '')
    f_fin = resultado.get('f_fin') or resultado.get('fecha_fin', '')
    fac_prin = resultado.get('facilitador_principal', '')
    tot_act = resultado.get('total_actividades', 0)
    tot_est = resultado.get('total_estudiantes', 0)
    tot_srv = resultado.get('total_servicios', 0)
    n_form = len(resultado.get('formaciones', []))
    n_prod = len(resultado.get('productos', []))
    n_otr = len(resultado.get('otras_actividades', []))
    cuadre = "● CUADRADO (100%)" if resultado.get("cuadre_perfecto") else "● DISCREPANCIA"

    lineas = [
        "═" * 78,
        "          INFORME OFICIAL DE AUDITORÍA Y BALANCE OPERATIVO — JsBOT",
        "═" * 78,
        f" Criterio Evaluado     : [{criterio}]",
        f" Período de Búsqueda   : {f_ini} al {f_fin}",
        f" Facilitador / Sede    : {fac_prin}",
        f" Balance Matemático    : {cuadre}",
        "─" * 78,
        " MÉTRICAS GENERALES:",
        f"  • Total Actividades   : {tot_act} (Formaciones: {n_form} | Productos: {n_prod} | Otras: {n_otr})",
        f"  • Estudiantes en Aula : {tot_est}",
        f"  • Servicios a Usuarios: {tot_srv}",
        "─" * 78,
    ]

    res_facs = resultado.get("resumen_facilitadores", {})
    if res_facs:
        lineas.append(" DESGLOSE POR FACILITADOR:")
        for uid_k, d in res_facs.items():
            lineas.append(f"  • [UID {uid_k}] {d.get('nombre', '')} (Sede: {d.get('info_id', 'S/D')})")
            lineas.append(f"    Formaciones: {d.get('formaciones', 0)} | Formados: {d.get('estudiantes', 0)} | Prod: {d.get('productos', 0)} | Otr: {d.get('otras', 0)} | Serv: {d.get('servicios', 0)} | Total: {d.get('total_act', 0)}")
        lineas.append("─" * 78)

    forms = resultado.get("formaciones", [])
    if forms:
        lineas.append(f" PRINCIPALES FORMACIONES ACADÉMICAS ({min(len(forms), 5)} de {len(forms)}):")
        for idx, act in enumerate(forms[:5], 1):
            lineas.append(f"  {idx}. [{act.get('fecha', '')}] {act.get('titulo', '')} (Taller: {act.get('taller', '')} — {act.get('participantes', 0)} part.)")
        lineas.append("═" * 78)

    return "\n".join(lineas)


def exportar_reporte_odt(resultado: dict, ruta_destino: str = None) -> str:
    """Genera un documento oficial OpenDocument Text (.odt) para LibreOffice Writer."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    if not ruta_destino:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        crit_tag = f"{resultado['criterio_tipo']}_{resultado['criterio_valor']}".replace(" ", "_")
        ruta_destino = os.path.join(REPORTES_DIR, f"Auditoria_{crit_tag}_{ts}.odt")

    criterio = f"{resultado.get('criterio_tipo', '').upper()}: {resultado.get('criterio_valor', '')}"
    f_ini = resultado.get('f_ini') or resultado.get('fecha_inicio', '')
    f_fin = resultado.get('f_fin') or resultado.get('fecha_fin', '')
    fac_prin = resultado.get('facilitador_principal', '')
    tot_act = resultado.get('total_actividades', 0)
    tot_est = resultado.get('total_estudiantes', 0)
    tot_srv = resultado.get('total_servicios', 0)
    cuadre = "Cuadrado (100%)" if resultado.get("cuadre_perfecto") else "Discrepancia"

    manifest_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>'''

    filas_xml = [
        '<text:h text:outline-level="1">INFORME OFICIAL DE AUDITORÍA Y BALANCE OPERATIVO — JsBOT</text:h>',
        f'<text:p><text:span text:style-name="Bold">Criterio evaluado:</text:span> {criterio} | <text:span text:style-name="Bold">Período:</text:span> {f_ini} al {f_fin}</text:p>',
        f'<text:p><text:span text:style-name="Bold">Facilitador / Sede:</text:span> {fac_prin}</text:p>',
        '<text:p></text:p>',
        '<text:h text:outline-level="2">Métricas Principales</text:h>',
        f'<text:p>• Total Actividades Registradas: {tot_act}</text:p>',
        f'<text:p>• Estudiantes Formados en Aula: {tot_est}</text:p>',
        f'<text:p>• Servicios a Usuarios: {tot_srv}</text:p>',
        f'<text:p>• Balance Matemático: {cuadre}</text:p>',
        '<text:p></text:p>'
    ]

    res_facs = resultado.get("resumen_facilitadores", {})
    if res_facs:
        filas_xml.append('<text:h text:outline-level="2">Desglose por Facilitador</text:h>')
        for uid_k, d in res_facs.items():
            filas_xml.append(f'<text:p>• [UID {uid_k}] {d.get("nombre", "")} (Sede: {d.get("info_id", "")}) — Formaciones: {d.get("formaciones", 0)} | Formados: {d.get("estudiantes", 0)} | Productos: {d.get("productos", 0)} | Otras: {d.get("otras", 0)} | Servicios: {d.get("servicios", 0)} | Total Act: {d.get("total_act", 0)}</text:p>')

    forms = resultado.get("formaciones", [])
    if forms:
        filas_xml.append('<text:p></text:p>')
        filas_xml.append(f'<text:h text:outline-level="2">Detalle de Formaciones ({len(forms)})</text:h>')
        for idx, act in enumerate(forms, 1):
            filas_xml.append(f'<text:p>{idx}. [{act.get("fecha", "")}] {act.get("titulo", "")} — Taller: {act.get("taller", "")} ({act.get("participantes", 0)} participantes) — Facilitador: {act.get("responsable", "")}</text:p>')

    srvs = resultado.get("servicios", [])
    if srvs:
        filas_xml.append('<text:p></text:p>')
        filas_xml.append(f'<text:h text:outline-level="2">Detalle de Servicios a Usuarios ({len(srvs)})</text:h>')
        for idx, s in enumerate(srvs, 1):
            filas_xml.append(f'<text:p>{idx}. [{s.get("fecha", "")}] Trámite: {s.get("servicio", "")} — Usuario: {s.get("usuario", "")} (Doc: {s.get("cedula", "")}) — Sede: {s.get("info_id", "")}</text:p>')

    content_body = "\n".join(filas_xml)
    content_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2">
 <office:body>
  <office:text>
   {content_body}
  </office:text>
 </office:body>
</office:document-content>'''

    with zipfile.ZipFile(ruta_destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/manifest.xml", manifest_xml)
        z.writestr("content.xml", content_xml.encode("utf-8"))

    return ruta_destino


def exportar_reporte_pdf(resultado: dict, ruta_destino: str = None) -> str:
    """Genera un archivo PDF 1.4 oficial sin requerir librerías externas."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    if not ruta_destino:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        crit_tag = f"{resultado['criterio_tipo']}_{resultado['criterio_valor']}".replace(" ", "_")
        ruta_destino = os.path.join(REPORTES_DIR, f"Auditoria_{crit_tag}_{ts}.pdf")

    criterio = f"{resultado.get('criterio_tipo', '').upper()}: {resultado.get('criterio_valor', '')}"
    f_ini = resultado.get('f_ini') or resultado.get('fecha_inicio', '')
    f_fin = resultado.get('f_fin') or resultado.get('fecha_fin', '')
    fac_prin = resultado.get('facilitador_principal', '')
    tot_act = resultado.get('total_actividades', 0)
    tot_est = resultado.get('total_estudiantes', 0)
    tot_srv = resultado.get('total_servicios', 0)
    n_form = len(resultado.get('formaciones', []))
    n_prod = len(resultado.get('productos', []))
    n_otr = len(resultado.get('otras_actividades', []))
    cuadre = "Cuadrado (100%)" if resultado.get("cuadre_perfecto") else "Discrepancia"

    lineas = [
        "INFORME DE AUDITORIA Y BALANCE OPERATIVO - JsBOT",
        "----------------------------------------------------------------",
        f"Criterio: {criterio} | Periodo: {f_ini} al {f_fin}",
        f"Facilitador / Sede: {fac_prin}",
        f"Balance Matematico: {cuadre}",
        "----------------------------------------------------------------",
        "METRICAS CONSOLIDADAS:",
        f" - Total Actividades: {tot_act} (Form: {n_form} | Prod: {n_prod} | Otr: {n_otr})",
        f" - Estudiantes Formados en Aula: {tot_est}",
        f" - Servicios a Usuarios Brindados: {tot_srv}",
        "----------------------------------------------------------------",
        "RESUMEN DE DESEMPENO POR FACILITADOR:"
    ]

    for uid_k, d in resultado.get("resumen_facilitadores", {}).items():
        lineas.append(f" UID {uid_k}: {d.get('nombre', '')} - Form: {d.get('formaciones', 0)}, Est: {d.get('estudiantes', 0)}, Serv: {d.get('servicios', 0)}, Tot: {d.get('total_act', 0)}")

    forms = resultado.get("formaciones", [])
    if forms:
        lineas.append("----------------------------------------------------------------")
        lineas.append("DETALLE FORMACIONES RECIENTES:")
        for idx, act in enumerate(forms[:15], 1):
            lineas.append(f" {idx}. [{act.get('fecha', '')}] {act.get('titulo', '')[:45]} ({act.get('participantes', 0)} part.)")

    obj_offsets = []
    content_lines = ['BT', '/F1 12 Tf', '40 760 Td']
    first = True
    for l in lineas:
        sanitized = l.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        sanitized = sanitized.encode('ascii', 'replace').decode('ascii')
        if first:
            content_lines.append(f'({sanitized}) Tj')
            first = False
        else:
            content_lines.append(f'0 -13 Td ({sanitized}) Tj')
    content_lines.append('ET')
    content_stream = '\n'.join(content_lines).encode('latin-1', 'replace')

    body = b'%PDF-1.4\n'
    obj_offsets.append(len(body))
    body += b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
    obj_offsets.append(len(body))
    body += b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
    obj_offsets.append(len(body))
    body += b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
    obj_offsets.append(len(body))
    body += f'4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n'.encode('ascii') + content_stream + b'\nendstream\nendobj\n'
    obj_offsets.append(len(body))
    body += b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'

    xref_start = len(body)
    body += b'xref\n0 6\n0000000000 65535 f \n'
    for offset in obj_offsets:
        body += f'{offset:010d} 00000 n \n'.encode('ascii')
    body += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF'.encode('ascii')

    with open(ruta_destino, 'wb') as f:
        f.write(body)

    return ruta_destino


def exportar_reporte_excel(resultado: dict, ruta_destino: str = None) -> str:
    """Genera archivo de auditoría consolidado en Excel (.xlsx) con openpyxl."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    if not ruta_destino:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        crit_tag = f"{resultado['criterio_tipo']}_{resultado['criterio_valor']}".replace(" ", "_")
        ruta_destino = os.path.join(REPORTES_DIR, f"Auditoria_{crit_tag}_{ts}.xlsx")

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    azul_oscuro = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    azul_sede = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    gris_subtotal = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    verde_total = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    fuente_blanca = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fuente_bold_sede = Font(name="Calibri", size=11, bold=True, color="1F4E78")
    fuente_bold = Font(name="Calibri", size=10, bold=True)
    fuente_normal = Font(name="Calibri", size=10)
    fuente_titulo = Font(name="Calibri", size=14, bold=True, color="1F4E78")

    borde_fino = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    borde_subtotal = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='1F4E78'),
        bottom=Side(style='double', color='1F4E78')
    )

    # Hoja 1: Resumen por Facilitador
    ws_fac = wb.active
    ws_fac.title = "Resumen por Facilitador"
    ws_fac.views.sheetView[0].showGridLines = True
    ws_fac.freeze_panes = "A2"

    headers_fac = [
        "UID", "Facilitador / Responsable", "Formaciones",
        "Estudiantes", "Productos", "Otras Actividades", "Servicios", "Total Act."
    ]
    for col_idx, h in enumerate(headers_fac, start=1):
        c = ws_fac.cell(row=1, column=col_idx, value=h)
        c.fill = azul_oscuro
        c.font = fuente_blanca
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws_fac.row_dimensions[1].height = 28

    res_facs = resultado.get("resumen_facilitadores", {})
    sedes_dict = {}
    for f_uid, f_data in res_facs.items():
        sede = f_data.get("info_id") or "Sin Sede / S/D"
        if sede not in sedes_dict:
            sedes_dict[sede] = []
        sedes_dict[sede].append((f_uid, f_data))

    current_row = 2
    tot_gral_form = 0
    tot_gral_est = 0
    tot_gral_prod = 0
    tot_gral_otr = 0
    tot_gral_serv = 0
    tot_gral_act = 0

    for codigo_sede, lista_f in sedes_dict.items():
        ws_fac.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=8)
        c_head = ws_fac.cell(row=current_row, column=1, value=f"🏢 INFOCENTRO: {codigo_sede}")
        c_head.fill = azul_sede
        c_head.font = fuente_bold_sede
        c_head.alignment = Alignment(horizontal="left", vertical="center")
        ws_fac.row_dimensions[current_row].height = 24
        current_row += 1

        sub_form = sub_est = sub_prod = sub_otr = sub_serv = sub_act = 0
        for f_uid, f_data in lista_f:
            f_act = f_data.get("total_act", 0)
            f_est = f_data.get("estudiantes", 0)
            f_frm = f_data.get("formaciones", 0)
            f_prd = f_data.get("productos", 0)
            f_otr = f_data.get("otras", 0)
            f_srv = f_data.get("servicios", 0)

            sub_form += f_frm
            sub_est += f_est
            sub_prod += f_prd
            sub_otr += f_otr
            sub_serv += f_srv
            sub_act += f_act

            fila_vals = [f_uid, f_data.get("nombre", f"UID {f_uid}"), f_frm, f_est, f_prd, f_otr, f_srv, f_act]
            for col_idx, val in enumerate(fila_vals, start=1):
                c = ws_fac.cell(row=current_row, column=col_idx, value=val)
                c.font = fuente_normal
                c.border = borde_fino
                if col_idx in (1, 3, 4, 5, 6, 7, 8):
                    c.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")
            ws_fac.row_dimensions[current_row].height = 20
            current_row += 1

        tot_gral_form += sub_form
        tot_gral_est += sub_est
        tot_gral_prod += sub_prod
        tot_gral_otr += sub_otr
        tot_gral_serv += sub_serv
        tot_gral_act += sub_act

        fila_sub = ["", f"Subtotal {codigo_sede}", sub_form, sub_est, sub_prod, sub_otr, sub_serv, sub_act]
        for col_idx, val in enumerate(fila_sub, start=1):
            c = ws_fac.cell(row=current_row, column=col_idx, value=val)
            c.fill = gris_subtotal
            c.font = fuente_bold
            c.border = borde_subtotal
            if col_idx in (1, 3, 4, 5, 6, 7, 8):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        ws_fac.row_dimensions[current_row].height = 22
        current_row += 1

    fila_total = ["", "TOTAL GENERAL CONSOLIDADO", tot_gral_form, tot_gral_est, tot_gral_prod, tot_gral_otr, tot_gral_serv, tot_gral_act]
    for col_idx, val in enumerate(fila_total, start=1):
        c = ws_fac.cell(row=current_row, column=col_idx, value=val)
        c.fill = verde_total
        c.font = fuente_bold
        c.border = borde_subtotal
        if col_idx in (1, 3, 4, 5, 6, 7, 8):
            c.alignment = Alignment(horizontal="center", vertical="center")
        else:
            c.alignment = Alignment(horizontal="left", vertical="center")
    ws_fac.row_dimensions[current_row].height = 26

    # Habilitar filtro automático en la primera pestaña (Resumen por Facilitador)
    ws_fac.auto_filter.ref = f"A1:H{max(current_row, 2)}"

    # Hoja 2: Actividades
    ws_act = wb.create_sheet(title="Actividades")
    ws_act.views.sheetView[0].showGridLines = True
    ws_act.freeze_panes = "A2"
    headers_act = [
        "Fecha", "ID InfoApp", "UID", "Infocentro", "Tipo Actividad",
        "Área Formativa", "Taller Específico", "Título Pedagógico",
        "Responsable", "Participantes", "Productos"
    ]
    for col_idx, h in enumerate(headers_act, start=1):
        c = ws_act.cell(row=1, column=col_idx, value=h)
        c.fill = azul_oscuro
        c.font = fuente_blanca
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws_act.row_dimensions[1].height = 28

    todas_act = resultado.get("formaciones", []) + resultado.get("productos", []) + resultado.get("otras_actividades", [])
    for r_idx, act in enumerate(todas_act, start=2):
        dims_lower = act.get("dimensiones", "").lower()
        if "aprendizaje" in dims_lower or "robótica" in dims_lower or "taller" in dims_lower:
            tipo_desc = "Formación"
        elif act.get("productos", 0) > 0 or "contenido" in dims_lower or "medios digitales" in dims_lower:
            tipo_desc = "Producto"
        else:
            tipo_desc = "Otras Actividades"

        fila_act = [
            act.get("fecha", ""),
            act.get("id") or act.get("id_activity", ""),
            act.get("uid", ""),
            act.get("info_id", ""),
            tipo_desc,
            act.get("area", ""),
            act.get("taller", ""),
            act.get("titulo", ""),
            act.get("responsable", ""),
            act.get("participantes", 0),
            act.get("productos", 0)
        ]
        for col_idx, val in enumerate(fila_act, start=1):
            cel = ws_act.cell(row=r_idx, column=col_idx, value=val)
            cel.font = fuente_normal
            cel.border = borde_fino
            if col_idx in (1, 2, 3, 4, 5, 10, 11):
                cel.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cel.alignment = Alignment(horizontal="left", vertical="center")
        ws_act.row_dimensions[r_idx].height = 20

    ws_act.auto_filter.ref = f"A1:K{max(len(todas_act) + 1, 2)}"

    # Hoja 3: Servicios
    ws_serv = wb.create_sheet(title="Servicios")
    ws_serv.views.sheetView[0].showGridLines = True
    ws_serv.freeze_panes = "A2"
    headers_serv = [
        "Fecha", "UID", "Infocentro", "Servicio / Trámite",
        "Cédula", "ID Usuario", "Nombre del Usuario", "Profesión / Ocupación"
    ]
    for col_idx, h in enumerate(headers_serv, start=1):
        c = ws_serv.cell(row=1, column=col_idx, value=h)
        c.fill = azul_oscuro
        c.font = fuente_blanca
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws_serv.row_dimensions[1].height = 28

    servicios_list = resultado.get("servicios", [])
    for r_idx, serv in enumerate(servicios_list, start=2):
        fila_serv = [
            serv.get("fecha", ""),
            serv.get("uid", ""),
            serv.get("info_id", ""),
            serv.get("servicio", ""),
            serv.get("cedula", ""),
            serv.get("id_usuario", ""),
            serv.get("usuario", ""),
            serv.get("profesion", "")
        ]
        for col_idx, val in enumerate(fila_serv, start=1):
            cel = ws_serv.cell(row=r_idx, column=col_idx, value=val)
            cel.font = fuente_normal
            cel.border = borde_fino
            if col_idx in (1, 2, 3, 5, 6):
                cel.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cel.alignment = Alignment(horizontal="left", vertical="center")
        ws_serv.row_dimensions[r_idx].height = 20

    ws_serv.auto_filter.ref = f"A1:H{max(len(servicios_list) + 1, 2)}"

    # Hoja 4: Resumen Ejecutivo
    ws_resumen = wb.create_sheet(title="Resumen Ejecutivo")
    ws_resumen.views.sheetView[0].showGridLines = True

    ws_resumen.merge_cells("A1:E1")
    celda_tit = ws_resumen["A1"]
    celda_tit.value = "INFORME OFICIAL DE AUDITORÍA Y INSPECCIÓN — JsBOT"
    celda_tit.font = fuente_titulo
    celda_tit.alignment = Alignment(horizontal="center", vertical="center")
    ws_resumen.row_dimensions[1].height = 30

    metadatos = [
        ("Criterio de Auditoría", f"{resultado['criterio_tipo'].upper()}: {resultado['criterio_valor']}"),
        ("Facilitador / Referencia", resultado['facilitador_principal']),
        ("Rango de Fechas Evaluado", f"{resultado['f_ini']} al {resultado['f_fin']}"),
        ("Fecha de Generación", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ("Estado de Cuadre Matemático", "CUADRE EXACTO (100%)" if resultado.get("cuadre_perfecto") else "DISCREPANCIA DETECTADA"),
    ]
    for r_idx, (k, v) in enumerate(metadatos, start=3):
        ws_resumen.cell(row=r_idx, column=1, value=k).font = fuente_bold
        ws_resumen.cell(row=r_idx, column=2, value=v)

    ws_resumen.cell(row=9, column=1, value="MÉTRICA AUDITADA").fill = azul_oscuro
    ws_resumen.cell(row=9, column=1).font = fuente_blanca
    ws_resumen.cell(row=9, column=2, value="VALOR CONSOLIDADO").fill = azul_oscuro
    ws_resumen.cell(row=9, column=2).font = fuente_blanca

    kpis = [
        ("Total Actividades en Plataforma", resultado.get("total_actividades", 0)),
        ("Total Actividades Procesadas", resultado.get("total_procesadas", 0)),
        ("Formaciones Académicas", len(resultado.get("formaciones", []))),
        ("Productos Comunicacionales", len(resultado.get("productos", []))),
        ("Otras Actividades / Gestión Comunal", len(resultado.get("otras_actividades", []))),
        ("Estudiantes Formados en Aula", resultado.get("total_estudiantes", 0)),
        ("Atenciones de Servicios Brindadas", resultado.get("total_servicios", 0)),
        ("Usuarios Cedulados Atendidos", resultado.get("cedulados_serv", 0)),
        ("Usuarios No Cedulados Atendidos", resultado.get("no_cedulados_serv", 0)),
    ]
    for r_idx, (k, v) in enumerate(kpis, start=10):
        c1 = ws_resumen.cell(row=r_idx, column=1, value=k)
        c2 = ws_resumen.cell(row=r_idx, column=2, value=v)
        c1.border = borde_fino
        c2.border = borde_fino
        c2.alignment = Alignment(horizontal="right", vertical="center")

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 65)

    wb.save(ruta_destino)
    return ruta_destino


def exportar_reporte_csv(resultado: dict, ruta_destino: str = None) -> str:
    """Genera archivo de auditoría consolidado en CSV plano compatible con Calc y Excel."""
    os.makedirs(REPORTES_DIR, exist_ok=True)
    if not ruta_destino:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        crit_tag = f"{resultado['criterio_tipo']}_{resultado['criterio_valor']}".replace(" ", "_")
        ruta_destino = os.path.join(REPORTES_DIR, f"Auditoria_{crit_tag}_{ts}_actividades.csv")

    with open(ruta_destino, mode="w", encoding="utf-8-sig", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["ID", "Fecha", "UID", "Infocentro", "Titulo", "Dimensiones", "Participantes", "Productos", "Responsable"])
        for act in resultado.get("formaciones", []) + resultado.get("productos", []) + resultado.get("otras_actividades", []):
            writer.writerow([
                act.get("id") or act.get("id_activity", ""),
                act.get("fecha", ""),
                act.get("uid", ""),
                act.get("info_id", ""),
                act.get("titulo", ""),
                act.get("dimensiones", ""),
                act.get("participantes", 0),
                act.get("productos", 0),
                act.get("responsable", "")
            ])
    return ruta_destino


def exportar_reporte_auditoria(resultado: dict, formato: str = "excel", ruta_destino: str = None) -> str:
    """Despachador unificado para exportar auditoría en Excel, ODT, PDF, CSV o pantalla."""
    fmt = (formato or "excel").lower().strip()

    if "consola" in fmt or "pantalla" in fmt:
        return generar_resumen_consola(resultado)

    if "odt" in fmt or "libreoffice" in fmt:
        return exportar_reporte_odt(resultado, ruta_destino=ruta_destino)

    if "pdf" in fmt:
        return exportar_reporte_pdf(resultado, ruta_destino=ruta_destino)

    if "csv" in fmt:
        return exportar_reporte_csv(resultado, ruta_destino=ruta_destino)

    if fmt == "ambos":
        r_xlsx = exportar_reporte_excel(resultado)
        exportar_reporte_csv(resultado)
        return r_xlsx

    return exportar_reporte_excel(resultado, ruta_destino=ruta_destino)

# =============================================================================
# 5. ORQUESTADOR CENTRAL DE AUDITORÍA
# =============================================================================

def ejecutar_auditoria(
    criterio_tipo=None,
    criterio_valor=None,
    f_ini=None,
    f_fin=None,
    rol_auditor=False,
    callback_log=None,
    uid=None,
    info_id=None,
    estado=None,
    start_at=None,
    finish_at=None,
    fecha_inicio=None,
    fecha_fin=None,
    formato="excel",
    exportar_formato=None,
    progreso_callback=None,
    browser_cfg=None,
    modo_turbo=True,
    **kwargs
) -> dict:
    """
    Motor de auditoría polimórfico acelerado (Selenium Auth -> HTTP Requests Session o Selenium Visual).
    Acepta tanto (criterio_tipo, criterio_valor) como parámetros directos (uid=..., info_id=..., estado=...).
    """
    cb = callback_log or progreso_callback or kwargs.get("log_callback")
    def log(msg):
        if cb:
            try:
                cb(msg)
            except Exception:
                pass
        else:
            try:
                print(msg)
            except UnicodeEncodeError:
                try:
                    print(msg.encode("ascii", errors="replace").decode("ascii"))
                except Exception:
                    pass

    usuario, clave = cargar_credenciales_auditoria(rol_auditor=rol_auditor)
    if not usuario or not clave:
        log("❌ Error: No hay credenciales configuradas en config/config.ini")
        return {"exito": False, "error": "Credenciales ausentes"}

    # Resolución flexible del criterio de búsqueda
    if uid is not None and str(uid).strip():
        criterio_tipo = "uid"
        criterio_valor = str(uid).strip()
    elif info_id is not None and str(info_id).strip():
        criterio_tipo = "info_id"
        criterio_valor = str(info_id).strip().upper()
    elif estado is not None and str(estado).strip() and str(estado).strip().lower() != "todos":
        criterio_tipo = "estado"
        criterio_valor = str(estado).strip()
    elif criterio_tipo and criterio_valor:
        criterio_tipo = str(criterio_tipo).lower().strip()
        criterio_valor = str(criterio_valor).strip()
    else:
        criterio_tipo = "uid"
        criterio_valor = "1325"

    # Valores específicos para filtros InfoApp (Aislamiento estricto por criterio de búsqueda)
    if criterio_tipo == "uid":
        uid_filtro = criterio_valor
        info_filtro = ""
        estado_filtro = ""
    elif criterio_tipo == "info_id":
        uid_filtro = ""
        info_filtro = criterio_valor
        estado_filtro = ""
    elif criterio_tipo == "estado":
        uid_filtro = ""
        info_filtro = ""
        estado_filtro = criterio_valor
    else:
        uid_filtro = criterio_valor
        info_filtro = ""
        estado_filtro = ""

    # Resolución flexible de fechas
    fecha_inicio_res = str(f_ini or start_at or fecha_inicio or "").strip() or "2026-01-01"
    fecha_fin_res = str(f_fin or finish_at or fecha_fin or "").strip() or datetime.now().strftime("%Y-%m-%d")

    # Resolución de formato
    formato_exp = exportar_formato or formato or "excel"
    if isinstance(formato_exp, str):
        formato_exp = formato_exp.lower().strip()

    headless = True if modo_turbo else False
    if browser_cfg and isinstance(browser_cfg, dict) and "headless" in browser_cfg:
        headless = bool(browser_cfg.get("headless", headless))

    log("=" * 80)
    log(f"🔍 INICIANDO AUDITORÍA INTEGRAL — Criterio: [{criterio_tipo.upper()}: {criterio_valor}]")
    log(f"📅 Rango evaluado: {fecha_inicio_res} al {fecha_fin_res} | Modo Auditor: {'Sí' if rol_auditor else 'No'} | Turbo: {'Sí' if modo_turbo else 'No'}")
    log("=" * 80)

    driver = iniciar_driver_auditoria(headless=headless)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://infoapp2.infocentro.gob.ve/admin/index.php"
    })

    try:
        log("🔐 Autenticando en InfoApp con WebDriver...")
        autenticar_infoapp(driver, usuario, clave)
        log("✅ Sesión web abierta exitosamente.")

        # Tarea 2: Switch Modo Turbo
        if modo_turbo:
            # Extraer cookies de Selenium para inyectarlas en requests.Session
            try:
                cookies = driver.get_cookies()
                for c in cookies:
                    session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/"))
                log(f"⚡ Sesión HTTP inicializada ({len(cookies)} cookies). Desacoplando WebDriver para aceleración máxima...")
            except Exception as err_cookies:
                log(f"⚠️ Nota de cookies: {err_cookies}")

            # Cerrar el WebDriver inmediatamente para liberar memoria y CPU
            try:
                driver.quit()
            except Exception:
                pass
            driver = None
            motor_extraccion = session
        else:
            log("🧭 Modo Visual / Selenium activo: Navegando páginas directamente con WebDriver...")
            motor_extraccion = driver.page

        # 1. Auditoría de Actividades
        tot_act, lista_act = consultar_actividades_infoapp(
            motor_extraccion, info_id=info_filtro, uid=uid_filtro, estado=estado_filtro,
            start_at=fecha_inicio_res, finish_at=fecha_fin_res, callback_log=log
        )

        # 2. Auditoría de Servicios
        tot_serv, lista_serv = consultar_servicios_infoapp(
            motor_extraccion, info_id=info_filtro, uid=uid_filtro, estado=estado_filtro,
            start_at=fecha_inicio_res, finish_at=fecha_fin_res, callback_log=log
        )

        # 3. Clasificación Matemática de Actividades
        formaciones = []
        productos = []
        otras_actividades = []
        total_estudiantes = 0

        for act in lista_act:
            dims_lower = (act.get("dimensiones") or "").lower()
            p_cnt = act.get("participantes", 0)
            prod_cnt = act.get("productos", 0)

            if "aprendizaje" in dims_lower or "robótica" in dims_lower or "robotica" in dims_lower or "taller" in dims_lower:
                formaciones.append(act)
                total_estudiantes += p_cnt
            elif prod_cnt > 0 or "contenido" in dims_lower or "medios digitales" in dims_lower:
                productos.append(act)
            else:
                otras_actividades.append(act)

        total_procesadas = len(formaciones) + len(productos) + len(otras_actividades)
        cuadre_perfecto = (tot_act == total_procesadas)

        # Desglose de Servicios
        conteo_servicios = Counter([s.get("servicio", s.get("tipo_servicio", "Servicio Comunitario")) for s in lista_serv])
        cedulados_serv = sum(1 for s in lista_serv if s.get("cedula") and s.get("cedula") != "No cedulado")
        no_cedulados_serv = len(lista_serv) - cedulados_serv

        # 4. Agrupación por Facilitador (para sedes o estados)
        resumen_facilitadores = {}
        for act in lista_act:
            f_uid = str(act.get("uid") or "").strip()
            resp_nom = str(act.get("responsable") or act.get("facilitador") or "").strip()
            clave_fac = f_uid if (f_uid and f_uid != "S/D") else (resp_nom if resp_nom else "S/D")

            if clave_fac not in resumen_facilitadores:
                resumen_facilitadores[clave_fac] = {
                    "uid": f_uid if (f_uid and f_uid != "S/D") else "S/D",
                    "nombre": resp_nom or (f"UID {f_uid}" if f_uid else "Sin Facilitador"),
                    "info_id": act.get("info_id") or info_id,
                    "formaciones": 0,
                    "estudiantes": 0,
                    "productos": 0,
                    "otras": 0,
                    "total_act": 0,
                    "servicios": 0
                }
            
            dims_lower = (act.get("dimensiones") or "").lower()
            p_cnt = act.get("participantes", 0)
            prod_cnt = act.get("productos", 0)

            if "aprendizaje" in dims_lower or "robótica" in dims_lower or "robotica" in dims_lower or "taller" in dims_lower or act.get("tipo_clasificacion") == "formacion":
                resumen_facilitadores[clave_fac]["formaciones"] += 1
                resumen_facilitadores[clave_fac]["estudiantes"] += p_cnt
            elif prod_cnt > 0 or "contenido" in dims_lower or "medios digitales" in dims_lower or act.get("tipo_clasificacion") == "producto":
                resumen_facilitadores[clave_fac]["productos"] += 1
            else:
                resumen_facilitadores[clave_fac]["otras"] += 1
            resumen_facilitadores[clave_fac]["total_act"] += 1

        for s in lista_serv:
            s_uid = str(s.get("uid") or "").strip()
            s_nom = str(s.get("usuario") or s.get("usuario_nombre") or "").strip()
            s_infoid = s.get("info_id") or info_filtro
            clave_s = s_uid if (s_uid and s_uid != "S/D") else (s_nom if s_nom else "S/D")

            if clave_s in resumen_facilitadores:
                resumen_facilitadores[clave_s]["servicios"] += 1
            else:
                resumen_facilitadores[clave_s] = {
                    "uid": s_uid if (s_uid and s_uid != "S/D") else "S/D",
                    "nombre": s_nom or f"UID {s_uid}",
                    "info_id": s_infoid,
                    "formaciones": 0,
                    "estudiantes": 0,
                    "productos": 0,
                    "otras": 0,
                    "total_act": 0,
                    "servicios": 1
                }

        # Nombre principal para la cabecera
        nombre_fac = lista_act[0]["responsable"] if lista_act and lista_act[0].get("responsable") else f"Criterio {criterio_tipo.upper()}: {criterio_valor}"

        resultado = {
            "exito": True,
            "criterio_tipo": criterio_tipo,
            "criterio_valor": criterio_valor,
            "f_ini": fecha_inicio_res,
            "f_fin": fecha_fin_res,
            "facilitador_principal": nombre_fac,
            "total_actividades": tot_act,
            "total_procesadas": total_procesadas,
            "formaciones": formaciones,
            "productos": productos,
            "otras_actividades": otras_actividades,
            "total_estudiantes": total_estudiantes,
            "total_servicios": tot_serv,
            "servicios": lista_serv,
            "conteo_servicios": conteo_servicios,
            "cedulados_serv": cedulados_serv,
            "no_cedulados_serv": no_cedulados_serv,
            "resumen_facilitadores": resumen_facilitadores,
            "cuadre_perfecto": cuadre_perfecto,
            "archivo_exportado": ""
        }

        # 5. Exportar si fue solicitado
        if formato_exp in ("excel", "csv", "ambos", "odt", "pdf", "consola", "pantalla"):
            ruta_exp = exportar_reporte_auditoria(resultado, formato=formato_exp)
            resultado["archivo_exportado"] = ruta_exp
            if formato_exp in ("consola", "pantalla"):
                log("\n" + ruta_exp)
            else:
                log(f"💾 Reporte exportado exitosamente: {ruta_exp}")

        # Guardar en caché ligero JSON (Directiva v4.2.4)
        try:
            guardar_cache_inspector(resultado)
        except Exception:
            pass

        if tot_act == 0 and tot_serv == 0:
            log("\n" + "═" * 80)
            log("ℹ️ [AVISO] No se encontraron actividades o usuarios en el rango seleccionado.")
            log("═" * 80)
        else:
            log("\n" + "═" * 80)
            log("✅ AUDITORÍA INTEGRAL CONCLUIDA EXITOSAMENTE")
            log(f" • Total Actividades: {tot_act} | Procesadas: {total_procesadas} (Cuadre: {'100%' if cuadre_perfecto else 'Discrepancia'})")
            log(f" • Estudiantes Formados: {total_estudiantes} | Servicios: {tot_serv}")
            log("═" * 80)

        return resultado

    except Exception as e:
        log(f"❌ Error durante la auditoría: {str(e)}")
        return {"exito": False, "error": str(e)}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
