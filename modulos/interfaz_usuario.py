#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: INTERFAZ DE USUARIO Y EXPERIENCIA UX/UI CONSOLIDADA (interfaz_usuario.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import time
import re
import urllib.parse
from datetime import datetime

from modulos.version import ETIQUETA_VERSION

# Compatibilidad de codificación en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def limpiar_consola():
    """Limpia la terminal en Windows o Linux/Mac."""
    os.system('cls' if os.name == 'nt' else 'clear')

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    Choice = None

ANCHO_BANNER = 74

def imprimir_banner():
    """Muestra el banner principal oficial y limpio de JsBOT con la versión canónica."""
    centro = f"   JsBOT {ETIQUETA_VERSION} — GESTIÓN MASIVA DE ACTIVIDADES Y SERVICIOS INFOCENTRO"
    centro = centro[:ANCHO_BANNER].ljust(ANCHO_BANNER)
    print("╔" + "═" * ANCHO_BANNER + "╗")
    print(f"║{centro}║")
    print("╚" + "═" * ANCHO_BANNER + "╝")

def prompt_menu_principal() -> str:
    """Menú principal unificado del sistema JsBOT."""
    limpiar_consola()
    imprimir_banner()
    choices = [
        Choice("FORMACION", "[1] Formación (Carga de Estudiantes y Planillas ODS)"),
        Choice("SERVICIOS", "[2] Servicios (Atención Comunitaria y Trámites)"),
        Choice("PLANILLA",  "[3] Generar Planilla Oficial ODS"),
        Choice("CONFIG",    "[4] Configuración de Credenciales y Parámetros"),
        Choice("SALIR",     "[5] Salir")
    ]
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message="¿Qué acción deseas realizar? (Usa flechas o presiona número)",
            qmark="",
            pointer="❯ ",
            choices=choices,
            default="FORMACION"
        ).execute()
    else:
        print("\n? ¿Qué acción deseas realizar?")
        print("  [1] Formación (Carga de Estudiantes y Planillas ODS)")
        print("  [2] Servicios (Atención Comunitaria y Trámites)")
        print("  [3] Generar Planilla Oficial ODS")
        print("  [4] Configuración de Credenciales y Parámetros")
        print("  [5] Salir")
        opc = input("Selecciona [1-5] (Enter = 1): ").strip()
        mapa = {'1': 'FORMACION', '2': 'SERVICIOS', '3': 'PLANILLA', '4': 'CONFIG', '5': 'SALIR'}
        return mapa.get(opc, 'FORMACION')

def renderizar_cuadro_sesion_previa(estado_previo: dict, tipo: str = "FORMACION"):
    """Muestra el panel detallado de sesión previa interrumpida (Formación o Servicios)."""
    participantes = estado_previo.get('participantes') or estado_previo.get('personas', [])
    ult_idx = estado_previo.get('indice_ultimo_procesado', 0)
    total = len(participantes)
    pendientes = max(0, total - ult_idx)
    
    fecha_str = estado_previo.get('timestamp_str', datetime.now().strftime("%Y-%m-%d_%H%M"))
    fecha = fecha_str.split('_')[0] if '_' in fecha_str else fecha_str

    ancho = 85
    print("\n┌" + "─" * 22 + " [!] SESION PREVIA INTERRUMPIDA DETECTADA " + "─" * 22 + "┐")
    print(f"│ Se detectó una carga no concluida por apagón o cierre abrupto:                     │")
    
    if tipo == "SERVICIOS" or 'config_servicio' in estado_previo:
        cfg_srv = estado_previo.get('config_servicio', {})
        srv_nom = cfg_srv.get('tipo_servicio', 'Atención General')
        f_srv = cfg_srv.get('fecha_servicio', fecha)
        print(f"│ • Módulo    : Servicios al Usuario ({srv_nom[:40]})".ljust(ancho + 1) + "│")
        print(f"│ • Fecha Srv : {f_srv}".ljust(ancho + 1) + "│")
    else:
        id_act = estado_previo.get('id_actividad', 'S/D')
        url = estado_previo.get('url', '')
        match_act = re.search(r'activity=([^&]+)', url)
        nom_act = urllib.parse.unquote(match_act.group(1)) if match_act else "Actividad Formativa"
        print(f"│ • Actividad : ID {id_act} ({nom_act[:45]})".ljust(ancho + 1) + "│")
        print(f"│ • Fecha     : {fecha}".ljust(ancho + 1) + "│")
        
    print(f"│ • Progreso  : {ult_idx} de {total} procesados ({pendientes} pendientes)".ljust(ancho + 1) + "│")
    
    ultimo_p = participantes[ult_idx - 1] if 0 < ult_idx <= len(participantes) else (participantes[0] if participantes else {})
    nom_ultimo = f"{ultimo_p.get('nombre', '')} {ultimo_p.get('apellido', '')}".strip() or "S/D"
    doc_ultimo = ultimo_p.get('cedula') or ultimo_p.get('cedula_escolar') or ultimo_p.get('cedula_padre') or "S/D"
    print(f"│ • Último    : {nom_ultimo[:32]} ({doc_ultimo})".ljust(ancho + 1) + "│")
    print("└" + "─" * (ancho - 1) + "┘\n")

def prompt_reanudar_sesion(estado_previo: dict, tipo: str = "FORMACION") -> str:
    """Consulta interactiva numerada ante sesión previa interrumpida."""
    renderizar_cuadro_sesion_previa(estado_previo, tipo)
    ult = estado_previo.get('indice_ultimo_procesado', 0)
    
    choices = [
        Choice("RESUME", f"[1] Reanudar sesión exactamente donde quedó (desde el registro {ult + 1})"),
        Choice("DISCARD", "[2] Descartar sesión anterior e iniciar una nueva carga")
    ]
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message="¿Qué deseas hacer con la sesión anterior? (Usa flechas o presiona número)",
            qmark="",
            pointer="❯ ",
            choices=choices,
            default="RESUME"
        ).execute()
    else:
        print("? ¿Qué deseas hacer con la sesión anterior?")
        print(f"  [1] Reanudar sesión exactamente donde quedó (desde el registro {ult + 1})")
        print("  [2] Descartar sesión anterior e iniciar una nueva carga")
        opc = input("Selecciona [1/2] (Enter = 1): ").strip()
        return "DISCARD" if opc == '2' else "RESUME"

def prompt_confirmacion_prevuelo(participantes: list, config: dict) -> str:
    """
    Pantalla de confirmación de pre-vuelo para Formación.
    Retorna: 'PROCEED', 'CHANGE_URL', 'CHANGE_FILE', 'CANCEL'
    """
    limpiar_consola()
    imprimir_banner()
    
    total = len(participantes)
    n_ced = sum(1 for p in participantes if p.get('cedulado') == 'si')
    n_esc = sum(1 for p in participantes if p.get('cedulado') == 'escolar')
    n_men = sum(1 for p in participantes if p.get('cedulado') == 'no')
    
    partes_doc = []
    if n_ced: partes_doc.append(f"{n_ced} Cedulados")
    if n_esc: partes_doc.append(f"{n_esc} Escolares")
    if n_men: partes_doc.append(f"{n_men} Menores S/C")
    desc_docs = ", ".join(partes_doc) if partes_doc else f"{total} Registros"
    
    id_act = config.get('id_actividad', 'S/D')
    url = config.get('url', '')
    usuario = config.get('usuario', 'jairhernandez')
    
    ancho = 90
    print("\n┌" + "─" * 35 + " Confirmar Carga RPA " + "─" * 34 + "┐")
    print(f"│ Resumen de la Carga de Formación:".ljust(ancho + 1) + "│")
    print(f"│ • Participantes a inscribir: {total} ({desc_docs})".ljust(ancho + 1) + "│")
    print(f"│ • ID Actividad             : {id_act}".ljust(ancho + 1) + "│")
    print(f"│ • Facilitador              : {usuario}".ljust(ancho + 1) + "│")
    print("└" + "─" * (ancho - 1) + "┘\n")
    
    choices = [
        Choice("PROCEED",    "[1] Iniciar carga automática en InfoApp ahora"),
        Choice("CHANGE_URL", "[2] Modificar URL / ID de Actividad"),
        Choice("CHANGE_FILE","[3] Seleccionar otro archivo de datos"),
        Choice("CANCEL",     "[4] Cancelar y volver al menú principal")
    ]
    
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message="¿Cómo deseas proceder? (Usa flechas o presiona número)",
            qmark="",
            pointer="❯ ",
            choices=choices,
            default="PROCEED"
        ).execute()
    else:
        print("? ¿Cómo deseas proceder?")
        print("  [1] Iniciar carga automática en InfoApp ahora")
        print("  [2] Modificar URL / ID de Actividad")
        print("  [3] Seleccionar otro archivo de datos")
        print("  [4] Cancelar y volver al menú principal")
        opc = input("Selecciona [1-4] (Enter = 1): ").strip()
        mapa = {'1': 'PROCEED', '2': 'CHANGE_URL', '3': 'CHANGE_FILE', '4': 'CANCEL'}
        return mapa.get(opc, 'PROCEED')

def prompt_confirmacion_servicios(personas: list, config_servicio: dict) -> str:
    """Pantalla de confirmación previa para Servicios."""
    limpiar_consola()
    imprimir_banner()

    total = len(personas)
    srv_tipo = config_servicio.get("tipo_servicio", "Gestión en el Sistema de Protección Social Patria")
    f_srv = config_servicio.get("fecha_servicio", datetime.now().strftime("%Y-%m-%d"))

    ancho = 90
    print("\n┌" + "─" * 33 + " Confirmar Carga Servicios " + "─" * 30 + "┐")
    print(f"│ Resumen de la Carga de Servicios:".ljust(ancho + 1) + "│")
    print(f"│ • Total Personas a Asentar : {total}".ljust(ancho + 1) + "│")
    print(f"│ • Servicio Asignado        : {srv_tipo[:50]}".ljust(ancho + 1) + "│")
    print(f"│ • Fecha del Servicio       : {f_srv}".ljust(ancho + 1) + "│")
    print("└" + "─" * (ancho - 1) + "┘\n")

    mostrar_tabla_participantes(personas)

    choices = [
        Choice("PROCEED",     "[1] Iniciar carga automática de servicios ahora"),
        Choice("CHANGE_TYPE", "[2] Modificar tipo de servicio"),
        Choice("CHANGE_DATE", "[3] Modificar fecha del servicio"),
        Choice("CHANGE_FILE", "[4] Seleccionar otro archivo de datos"),
        Choice("CANCEL",      "[5] Cancelar y volver al menú principal")
    ]

    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message="¿Cómo deseas proceder? (Usa flechas o presiona número)",
            qmark="",
            pointer="❯ ",
            choices=choices,
            default="PROCEED"
        ).execute()
    else:
        print("? ¿Cómo deseas proceder?")
        print("  [1] Iniciar carga automática de servicios ahora")
        print("  [2] Modificar tipo de servicio")
        print("  [3] Modificar fecha del servicio")
        print("  [4] Seleccionar otro archivo de datos")
        print("  [5] Cancelar y volver al menú principal")
        opc = input("Selecciona [1-5] (Enter = 1): ").strip()
        mapa = {'1': 'PROCEED', '2': 'CHANGE_TYPE', '3': 'CHANGE_DATE', '4': 'CHANGE_FILE', '5': 'CANCEL'}
        return mapa.get(opc, 'PROCEED')

def renderizar_panel_carga(indice_actual: int, total: int, alumno: dict, exitosos: int, fallidos: int, t_inicio: float, mensaje_estado: str = "", id_actividad: str = ""):
    """Renderiza el panel interactivo limpio sin emojis rotos para Formación."""
    nom_comp = f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}".strip()
    doc_raw = alumno.get('cedula') or (f"CE:{alumno.get('cedula_escolar')}" if alumno.get('cedulado') == 'escolar' else (f"Rep:{alumno.get('cedula_padre')}" if alumno.get('cedula_padre') else "S/C"))
    doc_str = f"V-{doc_raw}" if alumno.get('cedulado') == 'si' and not str(doc_raw).startswith('E-') else str(doc_raw)
    tipo_str = alumno.get('cedulado', 'si').upper()

    limpiar_consola()
    imprimir_banner()

    t_transcurrido = max(0.1, time.time() - t_inicio)
    procesados = max(1, indice_actual - 1)
    velocidad = t_transcurrido / procesados if procesados > 0 else 0.0
    restantes = max(0, total - indice_actual + 1)
    eta_seg = int(velocidad * restantes) if velocidad > 0 else 0

    mins_t = int(t_transcurrido // 60)
    segs_t = int(t_transcurrido % 60)
    mins_eta = int(eta_seg // 60)
    segs_eta = int(eta_seg % 60)

    porcentaje = int(((indice_actual - 1) / total) * 100) if total > 0 else 0
    bloques_llenos = max(0, min(12, int(porcentaje / 8.33)))
    barra = f"{'█' * bloques_llenos}{'░' * (12 - bloques_llenos)}"
    
    ancho = 95
    header_title = f" CARGA DE PARTICIPANTES EN INFOAPP — [{indice_actual}/{total}] "
    pad_izq = 25
    pad_der = max(2, ancho - pad_izq - len(header_title) - 2)
    print("\n┌" + "─" * pad_izq + header_title + "─" * pad_der + "┐")
    
    col1_1 = f"│ Participante: {nom_comp[:38]}".ljust(53)
    col1_2 = f"Progreso: [{barra}] {porcentaje}% ({indice_actual}/{total})".ljust(42) + "│"
    print(col1_1 + col1_2)

    col2_1 = f"│ Documento   : {doc_str} ({tipo_str})".ljust(53)
    col2_2 = f"Rendimiento: {exitosos} Exitosos • {fallidos} Fallidos".ljust(42) + "│"
    print(col2_1 + col2_2)

    id_act_str = f"ID {id_actividad}" if id_actividad else "N/D"
    col3_1 = f"│ Actividad   : {id_act_str}".ljust(53)
    col3_2 = f"Tiempo: {mins_t:02d}:{segs_t:02d} (ETA: {mins_eta:02d}:{segs_eta:02d})".ljust(42) + "│"
    print(col3_1 + col3_2)

    col4_1 = f"│ Estado      : {mensaje_estado[:38]}".ljust(53)
    col4_2 = f"Velocidad: {velocidad:.1f} s/participante".ljust(42) + "│"
    print(col4_1 + col4_2)
    print("└" + "─" * (ancho - 1) + "┘\n")

def renderizar_panel_servicios(indice_actual: int, total: int, persona: dict, exitosos: int, fallidos: int, t_inicio: float, tipo_servicio: str, fecha_servicio: str, mensaje_estado: str = ""):
    """Renderiza el panel interactivo de Servicios al Usuario."""
    nom_comp = f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip() or "Usuario C.I. " + str(persona.get('cedula', ''))
    if persona.get('cedula'):
        doc_str = f"V-{persona.get('cedula')}" if not str(persona.get('cedula')).startswith(('V-', 'E-')) else str(persona.get('cedula'))
    elif persona.get('cedula_escolar'):
        doc_str = f"CE:{persona.get('cedula_escolar')}"
    elif persona.get('cedula_padre'):
        doc_str = f"Rep:{persona.get('cedula_padre')}"
    else:
        doc_str = "S/D"

    limpiar_consola()
    imprimir_banner()

    t_transcurrido = max(0.1, time.time() - t_inicio)
    procesados = max(1, indice_actual - 1)
    velocidad = t_transcurrido / procesados if procesados > 0 else 0.0
    restantes = max(0, total - indice_actual + 1)
    eta_seg = int(velocidad * restantes) if velocidad > 0 else 0

    mins_t = int(t_transcurrido // 60)
    segs_t = int(t_transcurrido % 60)
    mins_eta = int(eta_seg // 60)
    segs_eta = int(eta_seg % 60)

    porcentaje = int(((indice_actual - 1) / total) * 100) if total > 0 else 0
    bloques_llenos = max(0, min(12, int(porcentaje / 8.33)))
    barra = f"{'█' * bloques_llenos}{'░' * (12 - bloques_llenos)}"

    ancho = 95
    header_title = f" CARGA DE SERVICIOS EN INFOAPP — [{indice_actual}/{total}] "
    pad_izq = 25
    pad_der = max(2, ancho - pad_izq - len(header_title) - 2)
    print("\n┌" + "─" * pad_izq + header_title + "─" * pad_der + "┐")

    col1_1 = f"│ Usuario     : {nom_comp[:38]}".ljust(53)
    col1_2 = f"Progreso: [{barra}] {porcentaje}% ({indice_actual}/{total})".ljust(42) + "│"
    print(col1_1 + col1_2)

    col2_1 = f"│ Cédula      : {doc_str}".ljust(53)
    col2_2 = f"Rendimiento: {exitosos} Exitosos • {fallidos} Fallidos".ljust(42) + "│"
    print(col2_1 + col2_2)

    col3_1 = f"│ Servicio    : {tipo_servicio[:38]}".ljust(53)
    col3_2 = f"Tiempo: {mins_t:02d}:{segs_t:02d} (ETA: {mins_eta:02d}:{segs_eta:02d})".ljust(42) + "│"
    print(col3_1 + col3_2)

    col4_1 = f"│ Estado      : {mensaje_estado[:38]}".ljust(53)
    col4_2 = f"Velocidad: {velocidad:.1f} s/servicio".ljust(42) + "│"
    print(col4_1 + col4_2)
    print("└" + "─" * (ancho - 1) + "┘\n")

def mostrar_resumen_estadistico(cargados: list, total_leidos: int, tiempo_total_seg: float, fallidos_count: int = 0):
    """Presenta el balance final con tabla ASCII limpia de dos columnas para Formación."""
    exitosos = len(cargados)
    pct_exito = int((exitosos / total_leidos) * 100) if total_leidos > 0 else 0
    mins = int(tiempo_total_seg // 60)
    segs = int(tiempo_total_seg % 60)
    promedio = (tiempo_total_seg / total_leidos) if total_leidos > 0 else 0.0

    print("\n" + " " * 18 + "BALANCE FINAL — CARGA DE FORMACIÓN EN INFOAPP")
    print("┌──────────────────────────────────────────────┬────────────────────────────────┐")
    print("│ Métrica                                      │                          Valor │")
    print("├──────────────────────────────────────────────┼────────────────────────────────┤")
    print(f"│ Total Participantes Procesados               │ {total_leidos:>30} │")
    print(f"│ Participantes Registrados Exitosamente       │ {f'{exitosos} ({pct_exito}%)':>30} │")
    print(f"│ Incidencias / Omitidos                       │ {fallidos_count:>30} │")
    print(f"│ Tiempo Total                                 │ {f'{mins}m {segs:02d}s':>30} │")
    print(f"│ Velocidad Promedio                           │ {f'{promedio:.1f} s/partic.':>30} │")
    print("└──────────────────────────────────────────────┴────────────────────────────────┘\n")

def mostrar_resumen_estadistico_servicios(exitosos: list, total_leidos: int, tiempo_total_seg: float, fallidos_count: int = 0):
    """Presenta el balance final con tabla ASCII limpia para Servicios."""
    pct_exito = int((len(exitosos) / total_leidos) * 100) if total_leidos > 0 else 0
    mins = int(tiempo_total_seg // 60)
    segs = int(tiempo_total_seg % 60)
    promedio = (tiempo_total_seg / total_leidos) if total_leidos > 0 else 0.0

    print("\n" + " " * 18 + "BALANCE FINAL — CARGA DE SERVICIOS EN INFOAPP")
    print("┌──────────────────────────────────────────────┬────────────────────────────────┐")
    print("│ Métrica                                      │                          Valor │")
    print("├──────────────────────────────────────────────┼────────────────────────────────┤")
    print(f"│ Total Personas Atendidas                     │ {total_leidos:>30} │")
    print(f"│ Servicios Asentados Exitosamente             │ {f'{len(exitosos)} ({pct_exito}%)':>30} │")
    print(f"│ Incidencias / Omitidos                       │ {fallidos_count:>30} │")
    print(f"│ Tiempo Total                                 │ {f'{mins}m {segs:02d}s':>30} │")
    print(f"│ Velocidad Promedio                           │ {f'{promedio:.1f} s/servicio':>30} │")
    print("└──────────────────────────────────────────────┴────────────────────────────────┘\n")

def prompt_menu_post_carga(ruta_excel: str) -> str:
    """Menú post-carga para abrir reporte, volver al menú o salir."""
    if ruta_excel and os.path.exists(ruta_excel):
        print(f"[OK] Reporte de Auditoría Excel generado en:\n{ruta_excel}\n")
    
    choices = [
        Choice("OPEN_EXCEL", "[1] Abrir reporte de auditoría en Excel / Calc"),
        Choice("MENU",       "[2] Volver al menú principal"),
        Choice("EXIT",       "[3] Salir y cerrar bot")
    ]
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message="¿Qué deseas hacer a continuación? (Usa flechas o presiona número)",
            qmark="",
            pointer="❯ ",
            choices=choices,
            default="MENU"
        ).execute()
    else:
        print("? ¿Qué deseas hacer a continuación?")
        print("  [1] Abrir reporte de auditoría en Excel / Calc")
        print("  [2] Volver al menú principal")
        print("  [3] Salir y cerrar bot")
        opc = input("Selecciona [1/2/3] (Enter = 2): ").strip()
        mapa = {'1': 'OPEN_EXCEL', '2': 'MENU', '3': 'EXIT'}
        return mapa.get(opc, 'MENU')

def prompt_tipo_servicio(catalogo: list, default_servicio: str = "") -> str:
    """Permite seleccionar de forma interactiva el tipo de servicio."""
    if not catalogo:
        catalogo = ["Gestión en el Sistema de Protección Social Patria"]
    
    opciones = [Choice(s, f"[{i}] {s}") for i, s in enumerate(catalogo, 1)]
    opciones.append(Choice("__CUSTOM__", "[+] Ingresar otro tipo de servicio manualmente"))
    opciones.append(Choice("__CANCEL__", "[0] Cancelar y volver"))

    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        res = inquirer.select(
            message="Selecciona el Tipo de Servicio prestado en InfoApp:",
            qmark="",
            choices=opciones,
            default=default_servicio if default_servicio in catalogo else catalogo[0],
            pointer="❯ "
        ).execute()
    else:
        print("\nCatálogo de Servicios:")
        for i, s in enumerate(catalogo, 1):
            print(f"  [{i}] {s}")
        print(f"  [+] Ingresar manualmente")
        print(f"  [0] Cancelar")
        opc = input(f"Selecciona [1-{len(catalogo)}]: ").strip()
        if opc == '0':
            return "__CANCEL__"
        if opc == '+':
            res = "__CUSTOM__"
        else:
            try:
                idx = int(opc) - 1
                res = catalogo[idx] if 0 <= idx < len(catalogo) else catalogo[0]
            except Exception:
                res = catalogo[0]

    if res == "__CUSTOM__":
        c = input("\nIngresa el nombre del servicio exactamente como figura en InfoApp: ").strip()
        return c if c else catalogo[0]
    return res

def prompt_fecha_servicio() -> str:
    """Solicita la fecha del servicio con validación estricta YYYY-MM-DD o 'hoy'."""
    hoy_iso = datetime.now().strftime("%Y-%m-%d")
    print(f"\nFecha del servicio a registrar (Presiona Enter para la fecha de hoy: {hoy_iso})")
    f_in = input("Ingresa fecha (YYYY-MM-DD o DD/MM/YYYY) o '0' para cancelar: ").strip()
    if f_in.lower() in ('0', 'cancelar', 'salir'):
        return ""
    if not f_in:
        return hoy_iso
    
    from modulos.normalizador_datos import limpiar_fecha
    f_norm = limpiar_fecha(f_in)
    return f_norm if f_norm else hoy_iso

def mostrar_tabla_participantes(participantes: list):
    """Renderiza la tabla de participantes con alto contraste."""
    total = len(participantes)
    cedulados = sum(1 for p in participantes if p.get('cedulado') == 'si')
    escolares = sum(1 for p in participantes if p.get('cedulado') == 'escolar')
    menores = sum(1 for p in participantes if p.get('cedulado') == 'no')
    varones = sum(1 for p in participantes if p.get('genero') == 'M')
    hembras = sum(1 for p in participantes if p.get('genero') == 'F')

    if RICH_AVAILABLE and console:
        table = Table(expand=True, border_style="blue", header_style="bold white on navy_blue")
        table.add_column("#", justify="center", style="dim cyan", no_wrap=True)
        table.add_column("Documento / Cédula", justify="left", no_wrap=True)
        table.add_column("Tipo Doc", justify="center", no_wrap=True)
        table.add_column("Nombre y Apellido", justify="left", style="bold white")
        table.add_column("F. Nacimiento", justify="center", style="bright_cyan", no_wrap=True)
        table.add_column("Teléfono", justify="center", style="green", no_wrap=True)
        table.add_column("Género", justify="center", no_wrap=True)

        for i, p in enumerate(participantes, 1):
            if p.get('cedulado') == 'si':
                doc_styled = f"[bold bright_yellow]{p.get('cedula', '')}[/]"
                tipo_styled = "[bold green]CEDULADO[/]"
            elif p.get('cedulado') == 'escolar':
                doc_styled = f"[bold magenta]CE:{p.get('cedula_escolar', '')}[/]"
                tipo_styled = "[bold magenta]C. ESCOLAR[/]"
            else:
                rep_ci = p.get('cedula_padre', '')
                doc_styled = f"[bold orange3]Rep:{rep_ci}[/]" if rep_ci else "[dim red]SIN DOC[/]"
                tipo_styled = "[bold yellow]MENOR S/C[/]"

            gen = p.get('genero', '')
            gen_styled = "[bold blue]M[/]" if gen == 'M' else ("[bold magenta]F[/]" if gen == 'F' else "[dim white]-[/]")
            nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()

            table.add_row(
                str(i),
                doc_styled,
                tipo_styled,
                nom_comp,
                p.get('nacimiento') or "[dim red]S/F[/]",
                p.get('telefono') or "[dim red]S/T[/]",
                gen_styled
            )

        subtitulo = (
            f"[bold white]Total: {total}[/] | "
            f"[bold bright_yellow]Cedulados: {cedulados}[/] • "
            f"[bold magenta]Cédula Escolar: {escolares}[/] • "
            f"[bold yellow]Menores: {menores}[/] | "
            f"[bold blue]Varones: {varones}[/] • [bold magenta]Hembras: {hembras}[/]"
        )

        console.print()
        console.print(Panel(
            table,
            title="[bold green]✦ LISTA DE PARTICIPANTES PRE-VALIDADOS PARA CARGA ✦[/bold green]",
            subtitle=subtitulo,
            border_style="green",
            padding=(0, 1)
        ))
    else:
        print("\n" + "=" * 95)
        print(f"             RESUMEN PREVIO: {total} REGISTROS EXTRAÍDOS")
        print("=" * 95)
        for i, p in enumerate(participantes, 1):
            doc_str = p.get('cedula') or (f"CE:{p.get('cedula_escolar')}" if p.get('cedulado') == 'escolar' else (f"Rep:{p.get('cedula_padre')}" if p.get('cedula_padre') else 'S/C'))
            nom_comp = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip()
            print(f"{i:<3} | {doc_str:<16} | {p.get('cedulado','').upper():<12} | {nom_comp[:30]:<30} | {p.get('nacimiento',''):<13} | {p.get('telefono',''):<13} | {p.get('genero',''):<3}")
        print("=" * 95)

def prompt_confirmar_carga(total: int, es_solo_planilla: bool = False) -> bool:
    """Solicita confirmación al usuario para continuar con la carga o generación de planilla."""
    if es_solo_planilla:
        msg = f"¿Deseas generar la Planilla Oficial ODS con los {total} registros?"
        txt_ok = f"Proceder a generar la Planilla Oficial ODS ({total} participantes)"
        txt_cancel = "Cancelar y volver al menú principal"
    else:
        msg = f"¿Deseas proceder con la carga de los {total} registros en InfoApp?"
        txt_ok = f"Proceder a cargar {total} registros en InfoApp"
        txt_cancel = "Cancelar y volver al menú"

    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message=msg,
            qmark="[*]",
            pointer="> ",
            choices=[
                Choice(True, name=txt_ok),
                Choice(False, name=txt_cancel)
            ],
            default=True
        ).execute()
    else:
        conf = input(f"\n{msg} [S/N] (Enter = Sí): ").strip().lower()
        return conf != 'n'

def prompt_seleccionar_hojas(hojas_disponibles: list) -> list:
    """Permite seleccionar la hoja del libro a procesar."""
    if len(hojas_disponibles) <= 1:
        return hojas_disponibles

    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        opciones = [Choice(h, name=f"Hoja: {h}") for h in hojas_disponibles]
        opciones.append(Choice("__ALL__", name=">> PROCESAR TODAS LAS HOJAS <<"))
        
        eleccion = inquirer.select(
            message="El libro contiene varias hojas. Selecciona cuál procesar:",
            qmark="[*]",
            pointer="> ",
            choices=opciones,
            default=hojas_disponibles[0]
        ).execute()

        return hojas_disponibles if eleccion == "__ALL__" else [eleccion]
    else:
        print("\n" + "=" * 70)
        print("                 SELECCIÓN DE HOJAS DEL LIBRO")
        print("=" * 70)
        for i, h in enumerate(hojas_disponibles, 1):
            print(f"  [{i}] {h}")
        print(f"  [{len(hojas_disponibles) + 1}] PROCESAR TODAS LAS HOJAS")
        opc = input(f"Selecciona [1-{len(hojas_disponibles) + 1}] (Enter = 1): ").strip()
        try:
            val = int(opc)
            if 1 <= val <= len(hojas_disponibles):
                return [hojas_disponibles[val - 1]]
            elif val == len(hojas_disponibles) + 1:
                return hojas_disponibles
        except ValueError:
            pass
        return [hojas_disponibles[0]]

def prompt_credenciales_guardadas(usuario: str) -> bool:
    """Pregunta si se desea usar la cuenta registrada."""
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message=f"Cuenta de InfoApp guardada: '{usuario}':",
            qmark="[*]",
            pointer="> ",
            choices=[
                Choice(True, name=f"Usar cuenta guardada ({usuario})"),
                Choice(False, name="Ingresar nuevas credenciales de InfoApp")
            ],
            default=True
        ).execute()
    else:
        print(f"\n[*] Usuario guardado: {usuario}")
        opc = input("¿Deseas usar esta cuenta de InfoApp? [S/N] (Enter = Sí): ").strip().lower()
        return opc != 'n'

def prompt_nuevas_credenciales() -> tuple:
    """Solicita usuario y contraseña con máscara de seguridad."""
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        usuario = inquirer.text(
            message="Usuario / Correo de InfoApp:",
            qmark="[*]",
            validate=lambda val: len(val.strip()) > 0 or "El usuario no puede estar vacío"
        ).execute().strip()
        clave = inquirer.secret(
            message="Contraseña de InfoApp:",
            qmark="[*]",
            validate=lambda val: len(val.strip()) > 0 or "La contraseña no puede estar vacía"
        ).execute().strip()
        return usuario, clave
    else:
        print("\n--- NUEVAS CREDENCIALES INFOAPP ---")
        u = input("Usuario / Correo: ").strip()
        c = input("Contraseña: ").strip()
        return u, c

def prompt_url_actividad() -> str:
    """
    Solicita la URL de la actividad con validación de formato.
    Permite escribir '0' o 'cancelar' para volver atrás.
    """
    def validar(val):
        v = val.strip().lower()
        if v in ('0', 'cancelar', 'salir', 'volver', 'back', 'q'):
            return True
        if not (v.startswith("http://") or v.startswith("https://")):
            return "Debes ingresar una URL válida (ej: https://infoapp2.infocentro.gob.ve/...) o '0' para cancelar"
        if "id_activity=" not in v and "participants_list" not in v and "infoapp" not in v:
            return "La URL debe corresponder a la lista de participantes de InfoApp (o escribe '0' para cancelar)"
        return True

    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        res = inquirer.text(
            message="Pega la URL completa de la actividad en InfoApp (o '0' para cancelar):",
            qmark="[*]",
            validate=validar
        ).execute().strip()
    else:
        while True:
            res = input("\nPega la URL completa de la actividad InfoApp (o '0' para cancelar): ").strip()
            v = validar(res)
            if v is True:
                break
            print(f"❌ {v}")

    if res.lower() in ('0', 'cancelar', 'salir', 'volver', 'back', 'q'):
        return ""
    return res

def prompt_reintentar_alumno(nombre: str, detalle: str) -> str:
    """Menú interactivo de decisión ante fallo de registro."""
    if INQUIRER_AVAILABLE and sys.stdin.isatty():
        return inquirer.select(
            message=f"Incidencia con '{nombre}' ({detalle}). Acción:",
            qmark="[*]",
            pointer="> ",
            choices=[
                Choice("RETRY", name="Reintentar este participante"),
                Choice("SKIP", name="Saltar y continuar con el siguiente"),
                Choice("PAUSE", name="Pausar proceso y guardar estado en disco")
            ],
            default="RETRY"
        ).execute()
    else:
        print(f"\n[1] Reintentar este participante")
        print("[2] Saltar y continuar con el siguiente")
        print("[3] Pausar y guardar estado")
        opc = input("Selecciona una opción [1/2/3] (Enter = 1): ").strip()
        if opc == '2':
            return "SKIP"
        elif opc == '3':
            return "PAUSE"
        return "RETRY"
