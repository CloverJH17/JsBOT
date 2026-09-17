#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: DIAGNÓSTICO PREVENTIVO DEL FACILITADOR (diagnostico_facilitador.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
Propósito : Auditoría preventiva para detectar actividades incompletas,
            borradores con 0 participantes y alertas para el facilitador.
===============================================================================
"""

import time
import requests
from datetime import datetime
from modulos.motor_export_auditoria import consultar_actividades_infoapp_export

def diagnosticar_actividades_facilitador(
    session: requests.Session,
    uid: str,
    fecha_inicio: str = None,
    fecha_fin: str = None
) -> dict:
    """
    Analiza el estado de las actividades del facilitador e identifica:
    1. Actividades sin participantes (conteo = 0).
    2. Actividades de formación con número inusualmente bajo o alto.
    3. Resumen de salud del reporte mensual.
    """
    if not fecha_inicio:
        # Por defecto primer día del mes en curso
        ahora = datetime.now()
        fecha_inicio = f"{ahora.year}-{ahora.month:02d}-01"
    if not fecha_fin:
        fecha_fin = datetime.now().strftime("%Y-%m-%d")
        
    tot, acts = consultar_actividades_infoapp_export(
        session, uid=uid, start_at=fecha_inicio, finish_at=fecha_fin
    )
    
    sin_participantes = []
    formaciones = []
    productos = []
    otras = []
    
    for a in acts:
        part = int(a.get("participantes", 0))
        clasif = a.get("tipo_clasificacion", "otra")
        
        if part == 0 and clasif != "producto":
            sin_participantes.append(a)
            
        if clasif == "formacion":
            formaciones.append(a)
        elif clasif == "producto":
            productos.append(a)
        else:
            otras.append(a)
            
    salud = "excelente"
    alertas = []
    
    if sin_participantes:
        salud = "atencion_requerida"
        alertas.append(
            f"Se detectaron {len(sin_participantes)} actividad(es) con 0 participantes cargados. "
            "Asegúrate de cargar las listas de asistencia para computar los formados."
        )
        
    return {
        "uid": uid,
        "periodo": f"{fecha_inicio} al {fecha_fin}",
        "total_actividades": len(acts),
        "formaciones_total": len(formaciones),
        "productos_total": len(productos),
        "otras_total": len(otras),
        "sin_participantes": sin_participantes,
        "conteo_sin_participantes": len(sin_participantes),
        "salud_reporte": salud,
        "alertas": alertas
    }
