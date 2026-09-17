#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: VERIFICADOR DE CARGAS POST-SUBIDA Y ANTI-DUPLICADOS (verificador_cargas_export.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
Propósito : Confirmación instantánea de registros cargados (participantes y servicios)
            consultando la base de datos oficial mediante exportación nativa.
===============================================================================
"""

import io
import time
import requests
import openpyxl
from datetime import datetime
from modulos.motor_export_auditoria import (
    consultar_servicios_infoapp_export,
    consultar_actividades_infoapp_export,
    limpiar_campo_csv
)

def obtener_participantes_existentes_actividad(session: requests.Session, id_activity: str) -> list:
    """
    Descarga en ~0.4s la lista completa de participantes ya registrados en una actividad.
    Retorna una lista de diccionarios con cédula, nombres, teléfono, fecha nacimiento y género.
    """
    if not id_activity:
        return []
        
    url_xlsx = (
        f"https://infoapp2.infocentro.gob.ve/core/app/view/exportxlsx_2.php?"
        f"param=SELECT * from participants_list where id_activity={id_activity} order by id desc"
        f"&param_sql=true&filename=participants_list"
    )
    
    try:
        r = session.get(url_xlsx, verify=False, timeout=25)
        if r.status_code != 200 or not r.content:
            return []
            
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) <= 1:
            return []
            
        # Posiciones de columnas en exportxlsx_2 de participants_list:
        # 0: id, 1: id_user_final, 2: uid_fac, 3: id_activity, 11: name, 12: name_2,
        # 13: lastname, 14: lastname_2, 17: document_id (cédula), 21: user_f_nacimiento,
        # 22: age, 23: gender, 26: phone, 27: email
        participantes = []
        for r_data in rows[1:]:
            if len(r_data) < 18:
                continue
            doc_id = str(r_data[17] or "").strip()
            nombre = f"{r_data[11] or ''} {r_data[12] or ''}".strip()
            apellido = f"{r_data[13] or ''} {r_data[14] or ''}".strip()
            participantes.append({
                "id": str(r_data[0] or ""),
                "dni": doc_id,
                "nombre": nombre,
                "apellido": apellido,
                "nombre_completo": f"{nombre} {apellido}".strip(),
                "genero": str(r_data[23] or ""),
                "edad": str(r_data[22] or ""),
                "f_nacimiento": str(r_data[21] or ""),
                "telefono": str(r_data[26] or ""),
                "correo": str(r_data[27] or "")
            })
        return participantes
    except Exception:
        return []

def verificar_participantes_actividad(session: requests.Session, id_activity: str, lista_dnis_esperados: list) -> dict:
    """
    Verifica instantáneamente si la lista de participantes cargados fue registrada
    completamente en la actividad de InfoApp.
    """
    existentes = obtener_participantes_existentes_actividad(session, id_activity)
    dnis_en_servidor = {p["dni"] for p in existentes if p.get("dni")}
    
    esperados_set = {str(d).strip() for d in lista_dnis_esperados if str(d).strip()}
    confirmados = esperados_set.intersection(dnis_en_servidor)
    faltantes = esperados_set.difference(dnis_en_servidor)
    
    return {
        "id_activity": id_activity,
        "total_en_servidor": len(existentes),
        "esperados_total": len(esperados_set),
        "confirmados_total": len(confirmados),
        "faltantes": list(faltantes),
        "exito_completo": (len(faltantes) == 0),
        "participantes": existentes
    }

def verificar_servicios_cargados_hoy(session: requests.Session, uid: str, dnis_esperados: list = None) -> dict:
    """
    Verifica instantáneamente si los servicios cargados hoy por el facilitador
    fueron guardados exitosamente en la plataforma InfoApp.
    """
    hoy = datetime.now().strftime("%Y-%m-%d")
    _, servicios_hoy = consultar_servicios_infoapp_export(
        session, uid=uid, start_at=hoy, finish_at=hoy
    )
    
    dnis_encontrados = {s.get("dni", "").strip() for s in servicios_hoy if s.get("dni")}
    
    resultado = {
        "fecha": hoy,
        "total_en_servidor": len(servicios_hoy),
        "servicios": servicios_hoy,
        "dnis_encontrados": list(dnis_encontrados),
    }
    
    if dnis_esperados:
        esperados_set = {str(d).strip() for d in dnis_esperados if str(d).strip()}
        coincidentes = esperados_set.intersection(dnis_encontrados)
        faltantes = esperados_set.difference(dnis_encontrados)
        
        resultado["esperados_total"] = len(esperados_set)
        resultado["confirmados_total"] = len(coincidentes)
        resultado["faltantes"] = list(faltantes)
        resultado["exito_completo"] = (len(faltantes) == 0)
    else:
        resultado["exito_completo"] = True
        
    return resultado

def verificar_actividad_cargada(session: requests.Session, uid: str, titulo_o_id: str, fecha: str = None) -> dict:
    """
    Verifica si una actividad específica fue registrada con éxito en InfoApp.
    """
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")
        
    _, acts = consultar_actividades_infoapp_export(
        session, uid=uid, start_at=fecha, finish_at=fecha
    )
    
    criterio = str(titulo_o_id).strip().lower()
    for a in acts:
        if str(a.get("id", "")).strip() == criterio or criterio in str(a.get("titulo", "")).strip().lower():
            return {
                "encontrada": True,
                "actividad": a,
                "id": a.get("id"),
                "participantes": a.get("participantes", 0)
            }
            
    return {
        "encontrada": False,
        "actividad": None,
        "id": "",
        "participantes": 0
    }
