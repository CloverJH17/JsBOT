#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: ORQUESTADOR MAESTRO CONSOLIDADO (orquestador.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v4.0.0
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime

# Compatibilidad UTF-8 para consolas de Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Asegurar que el directorio raíz esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.interfaz_usuario import (
    imprimir_banner,
    prompt_menu_principal,
    prompt_reanudar_sesion,
    prompt_confirmacion_prevuelo,
    prompt_confirmacion_servicios,
    prompt_menu_post_carga,
    mostrar_resumen_estadistico,
    mostrar_resumen_estadistico_servicios,
    prompt_tipo_servicio,
    prompt_fecha_servicio,
    limpiar_consola
)
from modulos.normalizador_datos import (
    ejecutar_modulo_etl,
    normalizar_personas_servicios
)
from modulos.gestor_sesion import (
    inicializar_sesion_actividad,
    guardar_estado_sesion,
    leer_estado_sesion,
    limpiar_estado_sesion,
    guardar_estado_sesion_servicios,
    leer_estado_sesion_servicios,
    limpiar_estado_sesion_servicios,
    cargar_config_servicios,
    finalizar_log_exito,
    finalizar_log_incompleto,
    obtener_credenciales,
    guardar_credenciales,
    gestionar_credenciales,
    generar_reporte_auditoria_excel,
    generar_reporte_auditoria_servicios,
    extraer_id_actividad
)
from modulos.automatizador_web import (
    ejecutar_carga_infoapp,
    ejecutar_carga_servicios_infoapp
)
from modulos.generador_planilla import generar_planilla_oficial
from modulos.verificador_entorno import ejecutar_checklist_sistema

def abrir_archivo_sistema(ruta: str):
    """Abre un archivo con la aplicación predeterminada del sistema operativo."""
    if not ruta or not os.path.exists(ruta):
        print(f"⚠️ El archivo no existe: {ruta}")
        return
    try:
        if sys.platform.startswith('win'):
            os.startfile(ruta)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', ruta])
        else:
            subprocess.Popen(['xdg-open', ruta])
    except Exception as e:
        print(f"⚠️ No se pudo abrir el archivo automáticamente: {e}")

def flujo_configuracion():
    """Sub-menú para gestionar credenciales y parámetros del bot."""
    limpiar_consola()
    imprimir_banner()
    u, _ = obtener_credenciales()
    print(f"\n[*] Usuario actual guardado: {u if u else 'No configurado'}")
    print("\n [1] Actualizar Usuario y Contraseña de InfoApp")
    print(" [2] Volver al Menú Principal")
    opc = input("\nSelecciona [1/2] (Enter = 2): ").strip()
    if opc == "1":
        from modulos.interfaz_usuario import prompt_nuevas_credenciales
        nu, nc = prompt_nuevas_credenciales()
        guardar_credenciales(nu, nc)
        print("✅ Credenciales actualizadas con éxito.")
        time.sleep(1.5)

def flujo_planilla_directa():
    """Genera la planilla ODS directamente seleccionando el archivo deseado."""
    limpiar_consola()
    imprimir_banner()
    participantes = ejecutar_modulo_etl(es_solo_planilla=True)

    if participantes:
        id_act = input("\nIngresa el ID de la Actividad (o presiona Enter para 'general'): ").strip() or "general"
        generar_planilla_oficial(participantes, id_act, url_actividad="")
        input("\nPresiona Enter para volver al menú principal...")
    else:
        print("⚠️ No se generó la planilla.")
        time.sleep(1.0)

def flujo_formacion(estado_previo: dict = None):
    """Flujo principal de carga y registro de formación en InfoApp."""
    participantes = []
    config = None
    indice_inicio = 0
    participantes_previos = []

    if estado_previo:
        u, c = obtener_credenciales()
        config = {
            "usuario": u,
            "clave": c,
            "url": estado_previo.get("url"),
            "id_actividad": estado_previo.get("id_actividad"),
            "timestamp_str": estado_previo.get("timestamp_str"),
            "archivo_log": estado_previo.get("archivo_log")
        }
        participantes = estado_previo.get("participantes", [])
        indice_inicio = estado_previo.get("indice_ultimo_procesado", 0)
        participantes_previos = participantes[:indice_inicio]
    else:
        # 1. Normalización ETL
        participantes = ejecutar_modulo_etl()
        if not participantes:
            return

        # 2. Configuración inicial de URL y sesión
        limpiar_consola()
        imprimir_banner()
        config = inicializar_sesion_actividad()
        if not config:
            return

    # 3. Pantalla de Confirmación de Pre-Vuelo
    while True:
        accion_prevuelo = prompt_confirmacion_prevuelo(participantes, config)
        if accion_prevuelo == "PROCEED":
            break
        elif accion_prevuelo == "CHANGE_URL":
            from modulos.interfaz_usuario import prompt_url_actividad
            nueva_url = prompt_url_actividad()
            if nueva_url:
                config["url"] = nueva_url
                config["id_actividad"] = extraer_id_actividad(nueva_url)
        elif accion_prevuelo == "CHANGE_FILE":
            nuevos_p = ejecutar_modulo_etl()
            if nuevos_p:
                participantes = nuevos_p
                indice_inicio = 0
                participantes_previos = []
        elif accion_prevuelo == "CANCEL":
            print("\n⚠️ Carga cancelada.")
            time.sleep(1.0)
            return

    # Guardar checkpoint inicial
    guardar_estado_sesion(config, participantes, indice_inicio)

    # 4. Inyección Automatizada en InfoApp
    try:
        nuevos_cargados, fallidos, tiempo_seg = ejecutar_carga_infoapp(
            participantes, config, indice_inicio=indice_inicio
        )

        todos_cargados = participantes_previos + nuevos_cargados
        total_reporte = todos_cargados if todos_cargados else participantes
        total_esperado = len(participantes) - indice_inicio
        carga_completa = len(nuevos_cargados) >= total_esperado

        if carga_completa:
            finalizar_log_exito(config)
        else:
            finalizar_log_incompleto(config, f"Carga parcial: {len(nuevos_cargados)}/{total_esperado} procesados")

        # 5. Generación de Planilla Oficial (.ods)
        generar_planilla_oficial(total_reporte, config['id_actividad'], config['url'])

        # 6. Generación de Reporte Excel de Auditoría (.xlsx)
        ruta_excel_auditoria = generar_reporte_auditoria_excel(config, todos_cargados, fallidos)

        # 7. Balance Final y Menú Post-Carga
        while True:
            limpiar_consola()
            imprimir_banner()
            mostrar_resumen_estadistico(total_reporte, len(participantes), tiempo_seg, len(fallidos))
            post_opc = prompt_menu_post_carga(ruta_excel_auditoria)
            if post_opc == "OPEN_EXCEL":
                abrir_archivo_sistema(ruta_excel_auditoria)
                time.sleep(1)
            elif post_opc == "MENU":
                break
            elif post_opc == "EXIT":
                print("\n👋 ¡Sesión finalizada con éxito!")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️ Proceso pausado por el usuario.")
        if config:
            finalizar_log_incompleto(config, "Interrumpido manualmente")
        time.sleep(1.2)
    except Exception as e:
        print(f"\n❌ Incidencia durante el proceso: {e}")
        if config:
            finalizar_log_incompleto(config, str(e))
        time.sleep(2)

def flujo_servicios(estado_previo: dict = None):
    """Flujo consolidado de atención comunitaria y registro de servicios."""
    personas = []
    config_bot = None
    config_servicio = None
    indice_inicio = 0
    personas_previas = []

    cfg_serv_global = cargar_config_servicios()

    if estado_previo:
        u, c = obtener_credenciales()
        config_bot = {
            "usuario": u,
            "clave": c,
            "timestamp_str": estado_previo.get("timestamp_str"),
            "archivo_log": estado_previo.get("archivo_log")
        }
        config_servicio = estado_previo.get("config_servicio", {})
        personas = estado_previo.get("personas", [])
        indice_inicio = estado_previo.get("indice_ultimo_procesado", 0)
        personas_previas = personas[:indice_inicio]
    else:
        # 1. Normalización de Personas
        personas = normalizar_personas_servicios()
        if not personas:
            return

        # 2. Configuración de Servicio y Fecha
        catalogo = cfg_serv_global.get("catalogo_servicios", [])
        def_serv = cfg_serv_global.get("servicio_por_defecto", "")
        tipo_srv = prompt_tipo_servicio(catalogo, def_serv)
        if tipo_srv == "__CANCEL__":
            return

        fecha_srv = prompt_fecha_servicio()
        if not fecha_srv:
            return

        u, c = gestionar_credenciales()
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        archivo_log = os.path.join(log_dir, f"log_servicios_{ts}.txt")

        with open(archivo_log, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"REGISTRO DE AUDITORÍA — SERVICIOS JsBOT v3.1.0\n")
            f.write(f"Fecha Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Servicio     : {tipo_srv}\n")
            f.write(f"Fecha Reg.   : {fecha_srv}\n")
            f.write(f"Operador     : {u}\n")
            f.write("=" * 80 + "\n\n")

        config_bot = {
            "usuario": u,
            "clave": c,
            "timestamp_str": ts,
            "archivo_log": archivo_log
        }
        config_servicio = {
            "tipo_servicio": tipo_srv,
            "fecha_servicio": fecha_srv,
            "infocentro": cfg_serv_global.get("infocentro", {})
        }

    # 3. Pantalla de Confirmación de Pre-Vuelo
    while True:
        accion = prompt_confirmacion_servicios(personas, config_servicio)
        if accion == "PROCEED":
            break
        elif accion == "CHANGE_TYPE":
            catalogo = cfg_serv_global.get("catalogo_servicios", [])
            nuevo_t = prompt_tipo_servicio(catalogo, config_servicio.get("tipo_servicio"))
            if nuevo_t and nuevo_t != "__CANCEL__":
                config_servicio["tipo_servicio"] = nuevo_t
        elif accion == "CHANGE_DATE":
            nueva_f = prompt_fecha_servicio()
            if nueva_f:
                config_servicio["fecha_servicio"] = nueva_f
        elif accion == "CHANGE_FILE":
            nuevas_p = normalizar_personas_servicios()
            if nuevas_p:
                personas = nuevas_p
                indice_inicio = 0
                personas_previas = []
        elif accion == "CANCEL":
            print("\n⚠️ Carga de servicios cancelada.")
            time.sleep(1.0)
            return

    # Checkpoint inicial
    guardar_estado_sesion_servicios(config_bot, config_servicio, personas, indice_inicio)

    # 4. Inyección Automatizada en InfoApp
    try:
        nuevos_exitosos, fallidos, duracion = ejecutar_carga_servicios_infoapp(
            personas, config_bot, config_servicio,
            indice_inicio=indice_inicio,
            fn_guardar_checkpoint=guardar_estado_sesion_servicios
        )

        todos_exitosos = personas_previas + nuevos_exitosos
        total_esperado = len(personas) - indice_inicio

        if len(nuevos_exitosos) >= total_esperado:
            limpiar_estado_sesion_servicios()

        # 5. Generar reporte Excel de auditoría
        ruta_excel = generar_reporte_auditoria_servicios(config_bot, config_servicio, todos_exitosos, fallidos)

        # 6. Balance Final y Menú Post-Carga
        while True:
            limpiar_consola()
            imprimir_banner()
            mostrar_resumen_estadistico_servicios(todos_exitosos, len(personas), duracion, len(fallidos))
            post_opc = prompt_menu_post_carga(ruta_excel)
            if post_opc == "OPEN_EXCEL":
                abrir_archivo_sistema(ruta_excel)
                time.sleep(1)
            elif post_opc == "MENU":
                break
            elif post_opc == "EXIT":
                print("\n👋 ¡Sesión finalizada con éxito!")
                sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️ Proceso de servicios pausado por el usuario.")
        time.sleep(1.2)
    except Exception as e:
        print(f"\n❌ Incidencia durante servicios: {e}")
        time.sleep(2)

def flujo_consola():
    """Bucle maestro del agente RPA JsBOT v4.0.0 en modo consola interactiva."""
    # PASO 0: Diagnóstico de Integridad y Requisitos de Entorno (Pre-vuelo)
    if not ejecutar_checklist_sistema():
        sys.exit(1)
    time.sleep(1.5)

    while True:
        limpiar_consola()
        imprimir_banner()

        # 0. Detección de sesión interrumpida de Formación
        estado_previo_form = leer_estado_sesion()
        if estado_previo_form:
            decision = prompt_reanudar_sesion(estado_previo_form, tipo="FORMACION")
            if decision == "RESUME":
                flujo_formacion(estado_previo=estado_previo_form)
                continue
            else:
                limpiar_estado_sesion()

        # Detección de sesión interrumpida de Servicios
        estado_previo_serv = leer_estado_sesion_servicios()
        if estado_previo_serv:
            decision = prompt_reanudar_sesion(estado_previo_serv, tipo="SERVICIOS")
            if decision == "RESUME":
                flujo_servicios(estado_previo=estado_previo_serv)
                continue
            else:
                limpiar_estado_sesion_servicios()

        # Menú Principal
        opcion = prompt_menu_principal()

        if opcion == "FORMACION":
            flujo_formacion()
        elif opcion == "SERVICIOS":
            flujo_servicios()
        elif opcion == "PLANILLA":
            flujo_planilla_directa()
        elif opcion == "CONFIG":
            flujo_configuracion()
        elif opcion == "SALIR":
            print("\n👋 ¡Gracias por usar JsBOT! Hasta pronto.\n")
            break

def iniciar_sistema(args: list = None):
    """Punto de entrada bimodal para JsBOT v4.0.0.

    Soporta los flags de línea de comandos:
      --gui, -g: Fuerza el lanzamiento de la interfaz gráfica nativa (CustomTkinter).
      --cli, -c, --consola, --terminal: Fuerza el modo consola interactivo tradicional.

    Sin flags:
      Consulta 'config/settings.json' -> 'app.interfaz_predeterminada' ('gui' o 'cli').

    Fallback seguro:
      Si falla la inicialización de la GUI (ej. librerías faltantes, ausencia de servidor
      gráfico X11/Wayland en Linux/Canaima, o TclError), captura la incidencia, emite
      una advertencia visual e inicia automáticamente el modo consola sin interrumpir
      la operatividad del usuario.
    """
    if args is None:
        args = sys.argv[1:]

    args_lower = [str(a).lower() for a in args]
    forzar_cli = any(flag in args_lower for flag in ["--cli", "-c", "--consola", "--terminal"])
    forzar_gui = any(flag in args_lower for flag in ["--gui", "-g", "--grafica"])

    modo = None
    if forzar_cli:
        modo = "cli"
    elif forzar_gui:
        modo = "gui"
    else:
        try:
            ruta_cfg = os.path.join(BASE_DIR, "config", "settings.json")
            if os.path.exists(ruta_cfg):
                with open(ruta_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    modo = cfg.get("app", {}).get("interfaz_predeterminada", "gui").lower()
            else:
                modo = "gui"
        except Exception:
            modo = "gui"

    if modo == "gui":
        try:
            from modulos.interfaz_grafica import AppGUI
            app = AppGUI()
            app.mainloop()
            return
        except (ImportError, Exception) as e:
            print(f"\n⚠️  [AVISO] No se pudo iniciar la interfaz gráfica: {e}")
            print("🔄 Iniciando automáticamente en modo consola interactiva (CLI)...\n")
            time.sleep(1)
            flujo_consola()
    else:
        flujo_consola()

def main():
    """Punto de entrada maestro y compatibilidad con invocaciones directas."""
    iniciar_sistema()

if __name__ == "__main__":
    main()
