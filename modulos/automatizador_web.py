#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: AUTOMATIZADOR WEB SELENIUM CONSOLIDADO (automatizador_web.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — v3.5.2
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchWindowException
)

from modulos.gestor_sesion import registrar_evento_log, guardar_estado_sesion
from modulos import config_manager as cm
from modulos.driver_factory import obtener_driver_resiliente
from modulos.web_utils import (
    limpiar_overlays as core_limpiar_overlays,
    esperar_desbloqueo_ajax as core_esperar_desbloqueo_ajax,
    escribir_input_nativo_js
)
from modulos.interfaz_usuario import (
    prompt_reintentar_alumno,
    renderizar_panel_carga,
    renderizar_panel_servicios,
    limpiar_consola
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "logs", "screenshots")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

def obtener_timeout_ajax() -> int:
    """Obtiene el timeout de espera AJAX configurado en settings.json (por defecto 15s)."""
    try:
        return int(cm.cargar_settings(SETTINGS_FILE)["timeouts"].get("ajax_wait_seconds", 15))
    except Exception:
        pass
    return 15

def capturar_pantalla_error(driver, doc_str: str):
    """Guarda una captura de pantalla ante errores de navegación o carga."""
    if not cm.captura_screenshots_activada():
        return
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_limpio = "".join(c for c in str(doc_str or "SD") if c.isalnum() or c in ('_', '-'))
        ruta = os.path.join(SCREENSHOTS_DIR, f"error_{doc_limpio}_{ts}.png")
        if driver:
            driver.save_screenshot(ruta)
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Fábricas de navegadores (registradas en un diccionario para que la cascada
# respete browser.priority de settings.json y sea testeable con mocks).
# -----------------------------------------------------------------------------

def _iniciar_firefox(maximizado: bool):
    """Delega el arranque a la factoría centralizada de WebDriver."""
    driver = obtener_driver_resiliente(headless=False)
    if driver and maximizado:
        try:
            driver.maximize_window()
        except Exception:
            pass
    return driver

def _iniciar_chrome(maximizado: bool):
    """Delega el arranque a la factoría centralizada de WebDriver."""
    return obtener_driver_resiliente(headless=False)

def _iniciar_edge(maximizado: bool):
    """Delega el arranque a la factoría centralizada de WebDriver."""
    return obtener_driver_resiliente(headless=False)

FABRICAS_NAVEGADOR = {
    "firefox": _iniciar_firefox,
    "chrome": _iniciar_chrome,
    "edge": _iniciar_edge
}

def iniciar_navegador():
    """Inicia el primer navegador disponible según la prioridad de settings.json."""
    cfg_browser = cm.obtener_browser_cfg()
    for nombre in cfg_browser["priority"]:
        fabrica = FABRICAS_NAVEGADOR.get(nombre)
        if not fabrica:
            continue
        driver = fabrica(cfg_browser["start_maximized"])
        if driver:
            return driver

    print("\n❌ ERROR: No se encontró ningún navegador compatible (Firefox, Chrome o Edge).")
    return None

def limpiar_overlays(driver):
    """Elimina toastify, alertas flotantes y modales delegando a modulos.web_utils."""
    core_limpiar_overlays(driver)

def esperar_desbloqueo_ajax(driver, timeout=None):
    """Espera activamente que desaparezca el indicador de carga delegando a modulos.web_utils."""
    if timeout is None:
        timeout = obtener_timeout_ajax()
    core_esperar_desbloqueo_ajax(driver, timeout=timeout)

def realizar_login(driver, config: dict):
    """Ejecuta el inicio de sesión en InfoApp."""
    wait = WebDriverWait(driver, cm.obtener_timeout("login_wait_seconds", 15))
    url_login = cm.obtener_url_login()
    
    print(f"🔐 Accediendo a InfoApp ({config['usuario']})...")
    driver.get(url_login)
    esperar_desbloqueo_ajax(driver)

    campo_user = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
    campo_user.clear()
    campo_user.send_keys(config['usuario'])

    campo_pass = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    campo_pass.clear()
    campo_pass.send_keys(config['clave'])

    btn_ingresar = None
    selectores = [
        "//input[@type='submit']",
        "//input[contains(@value, 'Iniciar')]",
        "//button[@type='submit']",
        "//button[contains(text(), 'Iniciar')]"
    ]
    for sel in selectores:
        try:
            elem = driver.find_element(By.XPATH, sel)
            if elem.is_displayed():
                btn_ingresar = elem
                break
        except Exception:
            pass

    if btn_ingresar:
        try:
            btn_ingresar.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn_ingresar)
    else:
        driver.execute_script("if(document.forms.length > 0) document.forms[0].submit();")

    wait.until(EC.url_changes(url_login))
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)
    print("✅ Autenticado con éxito en InfoApp.")

def asegurar_navegador_activo(driver_contenedor: dict, config: dict):
    """Garantiza que el navegador esté activo y la sesión en PHP no haya expirado."""
    necesita_reabrir = False
    if driver_contenedor.get('driver') is None:
        necesita_reabrir = True
    else:
        try:
            _ = driver_contenedor['driver'].current_url
        except Exception:
            necesita_reabrir = True

    if necesita_reabrir:
        print("\n🌐 Iniciando navegador y sesión en InfoApp...")
        try:
            if driver_contenedor.get('driver'):
                driver_contenedor['driver'].quit()
        except Exception:
            pass

        nuevo_driver = iniciar_navegador()
        if not nuevo_driver:
            raise RuntimeError("No se pudo iniciar ningún navegador compatible.")

        driver_contenedor['driver'] = nuevo_driver
        realizar_login(nuevo_driver, config)
    else:
        # Detección y recuperación ante sesión PHP expirada
        try:
            driver = driver_contenedor['driver']
            current = driver.current_url.lower()
            if "login" in current or "acceder" in current:
                print("⚠️ Sesión de InfoApp caducada en el servidor. Reautenticando...")
                realizar_login(driver, config)
        except Exception:
            pass

def seleccionar_dropdown(driver, select_id: str, valor: str):
    """Selecciona una opción en un <select> por valor o texto mediante JS y Selenium."""
    try:
        driver.execute_script(f"""
            let s = document.getElementById('{select_id}');
            if (s) {{
                let valBusq = "{valor}".trim().toLowerCase();
                for (let i = 0; i < s.options.length; i++) {{
                    let optVal = (s.options[i].value || "").trim().toLowerCase();
                    let optTxt = (s.options[i].text || "").trim().toLowerCase();
                    if (optVal === valBusq || optTxt === valBusq || optTxt.includes(valBusq)) {{
                        s.selectedIndex = i;
                        s.value = s.options[i].value;
                        s.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        break;
                    }}
                }}
            }}
        """)
    except Exception:
        pass

    try:
        elem = driver.find_element(By.ID, select_id)
        if elem:
            s_obj = Select(elem)
            try:
                s_obj.select_by_visible_text(valor)
            except Exception:
                try:
                    s_obj.select_by_value(valor)
                except Exception:
                    pass
    except Exception:
        pass

# =============================================================================
# SECCIÓN 1: AUTOMATIZACIÓN DE ACTIVIDADES FORMATIVAS
# =============================================================================

def registrar_alumno_en_web(driver, alumno: dict, config: dict) -> tuple:
    """
    Ejecuta el ciclo de inscripción de un participante:
    1. Búsqueda superior por AJAX (document_id, cedula_escolar o parent_ref).
    2. Verificación de existencia previa en base de datos.
    3. Llenado del formulario con validaciones oficiales de InfoApp.
    4. Envío directo AJAX + confirmación inmediata por respuesta de servidor.
    """
    wait = WebDriverWait(driver, cm.obtener_timeout("element_wait_seconds", 12))
    url_actividad = config['url']

    cedulado_tipo = alumno.get('cedulado', 'si')
    if cedulado_tipo == "si" and alumno.get('cedula'):
        cedula_busqueda = alumno['cedula']
        tipo_busqueda = "document_id"
    elif cedulado_tipo == "escolar" and alumno.get('cedula_escolar'):
        cedula_busqueda = alumno['cedula_escolar']
        tipo_busqueda = "cedula_escolar"
    elif alumno.get('cedula_padre'):
        cedula_busqueda = alumno.get('cedula_padre', '')
        tipo_busqueda = "parent_ref"
    else:
        return False, "Participante sin documento propio ni de representante (imposible registrar o buscar en InfoApp)"

    # Navegar a la actividad solo si no estamos en ella
    if not driver.current_url or "id_activity" not in driver.current_url:
        driver.get(url_actividad)
        esperar_desbloqueo_ajax(driver)
        limpiar_overlays(driver)

    # 1. Búsqueda superior AJAX
    seleccionar_dropdown(driver, "search_field", tipo_busqueda)
    campo_q = wait.until(EC.visibility_of_element_located((By.ID, "q_participante")))
    campo_q.clear()
    campo_q.send_keys(cedula_busqueda)

    btn_lupa = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@onclick, 'codigoAJAX')]")))
    btn_lupa.click()
    esperar_desbloqueo_ajax(driver, timeout=6)
    limpiar_overlays(driver)

    # 2. Verificar si es usuario preexistente
    campo_nombre = wait.until(EC.presence_of_element_located((By.ID, "name")))
    nombre_detectado = campo_nombre.get_attribute("value")
    es_preexistente = bool(nombre_detectado and nombre_detectado.strip() != "")

    # Nombres y Apellidos
    partes_nom = alumno['nombre'].split()
    nom_1 = partes_nom[0] if partes_nom else alumno['nombre']
    nom_2 = " ".join(partes_nom[1:]) if len(partes_nom) > 1 else ""

    partes_ape = alumno['apellido'].split()
    ape_1 = partes_ape[0] if partes_ape else alumno['apellido']
    ape_2 = " ".join(partes_ape[1:]) if len(partes_ape) > 1 else ""

    # Calcular edad
    edad_num = alumno.get('edad')
    if edad_num is None and alumno.get('nacimiento'):
        try:
            fn = datetime.strptime(alumno['nacimiento'], "%Y-%m-%d")
            hoy = datetime.now()
            edad_num = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
        except Exception:
            edad_num = 10

    if not es_preexistente:
        # 3. Llenado de formulario para usuario nuevo
        seleccionar_dropdown(driver, "user_nationality", "V")
        
        # Selección de modalidad de cédula
        if cedulado_tipo == "si":
            seleccionar_dropdown(driver, "user_has_document", "Si")
            driver.execute_script("if(document.getElementById('document_id_l')) document.getElementById('document_id_l').style.display='block';")
            campo_doc = wait.until(EC.visibility_of_element_located((By.ID, "document_id")))
            campo_doc.clear()
            campo_doc.send_keys(alumno['cedula'])
        elif cedulado_tipo == "escolar":
            seleccionar_dropdown(driver, "user_has_document", "Cédula escolar")
            driver.execute_script("if(document.getElementById('cedula_escolar_l')) document.getElementById('cedula_escolar_l').style.display='block';")
            campo_esc = wait.until(EC.visibility_of_element_located((By.ID, "cedula_escolar")))
            campo_esc.clear()
            campo_esc.send_keys(alumno['cedula_escolar'])
        else:
            seleccionar_dropdown(driver, "user_has_document", "No/No escolarizado")
            driver.execute_script("if(document.getElementById('parent_dni_div')) document.getElementById('parent_dni_div').style.display='block';")
            driver.execute_script("if(document.getElementById('child_number_div')) document.getElementById('child_number_div').style.display='block';")
            campo_p = wait.until(EC.visibility_of_element_located((By.ID, "parent_dni")))
            campo_p.clear()
            campo_p.send_keys(alumno.get('cedula_padre', ''))
            
            campo_h = wait.until(EC.visibility_of_element_located((By.ID, "child_number")))
            campo_h.clear()
            campo_h.send_keys("1")

        driver.find_element(By.ID, "name").clear()
        driver.find_element(By.ID, "name").send_keys(nom_1)
        if nom_2:
            driver.find_element(By.ID, "name_2").clear()
            driver.find_element(By.ID, "name_2").send_keys(nom_2)

        driver.find_element(By.ID, "lastname").clear()
        driver.find_element(By.ID, "lastname").send_keys(ape_1)
        if ape_2:
            driver.find_element(By.ID, "lastname_2").clear()
            driver.find_element(By.ID, "lastname_2").send_keys(ape_2)

        # Inyección de Fecha de Nacimiento
        if alumno.get('nacimiento'):
            driver.execute_script(f"""
                let fn = document.getElementById('user_f_nacimiento');
                if (fn) {{
                    fn.value = '{alumno['nacimiento']}';
                    fn.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """)

        # Teléfono
        campo_tlf = driver.find_element(By.ID, "phone")
        campo_tlf.clear()
        campo_tlf.send_keys(alumno.get('telefono', '0412-0000000'))

        # Género (Hombre / Mujer)
        texto_gen = "Mujer" if alumno.get('genero') == 'F' else "Hombre"
        seleccionar_dropdown(driver, "gender", texto_gen)

        # Catálogos obligatorios
        catalogos = [
            ("user_comunity_type", "No aplica"),
            ("user_pertenece_organizacion", "No aplica"),
            ("user_etnia", "No aplica"),
            ("disability_type", "No aplica"),
            ("user_profesion", "Estudiante"),
            ("user_ocupacion", "Estudiante")
        ]
        for cat_id, cat_val in catalogos:
            seleccionar_dropdown(driver, cat_id, cat_val)

    # 4. Envío directo AJAX con sincronización estricta de campos
    limpiar_overlays(driver)
    
    # Determinar valores exactos según la modalidad de documento (reglas oficiales de InfoApp)
    if cedulado_tipo == "si":
        has_doc_val = "Si"
        doc_id_val = str(alumno.get("cedula", "")).strip()
        ced_esc_val = ""  # OBLIGATORIO: cadena vacía para cedulados (NUNCA "No aplica")
        parent_dni_val = "No aplica"
        child_num_val = ""
        parent_ref_val = "No aplica"
    elif cedulado_tipo == "escolar":
        has_doc_val = "Cédula escolar"
        doc_id_val = ""   # OBLIGATORIO: cadena vacía para cédula escolar
        ced_esc_val = str(alumno.get("cedula_escolar", "")).strip()
        parent_dni_val = "No aplica"
        child_num_val = ""
        parent_ref_val = "No aplica"
    else:
        has_doc_val = "No/No escolarizado"
        doc_id_val = "No escolarizado"
        ced_esc_val = ""  # OBLIGATORIO: cadena vacía para no escolarizados
        parent_dni_val = str(alumno.get("cedula_padre", "")).strip()
        child_num_val = "1"
        parent_ref_val = f"{parent_dni_val}1" if parent_dni_val else "No aplica"

    is_new_val = 'false' if es_preexistente else 'true'
    gender_val = "Mujer" if alumno.get("genero") == "F" else "Hombre"

    # Parámetros seguros pasados como arguments[] de Selenium
    ajax_params = {
        "doc_id": doc_id_val,
        "ced_esc": ced_esc_val,
        "parent_dni": parent_dni_val,
        "child_num": child_num_val,
        "parent_ref": parent_ref_val,
        "has_doc": has_doc_val,
        "nom_1": nom_1,
        "nom_2": nom_2,
        "ape_1": ape_1,
        "ape_2": ape_2,
        "nacimiento": alumno.get("nacimiento", ""),
        "gender": gender_val,
        "telefono": alumno.get("telefono", "0412-0000000"),
        "is_new": is_new_val,
        "age": edad_num or 10
    }

    # Ejecución AJAX directa de InfoApp con sincronización y paso seguro de parámetros
    driver.execute_script("""
        var p = arguments[0];
        window.__ajax_done = false;
        window.__ajax_res = null;

        var domIsNew = document.getElementById('is_new') ? document.getElementById('is_new').value : '';
        var isNew = (domIsNew === 'false') ? 'false' : p.is_new;
        var idFinalUser = $('#id_final_user').val() || '0';

        // Sincronizar inputs del formulario para evitar que InfoApp conserve 'No aplica' en cédula escolar
        $('#user_has_document').val(p.has_doc);
        $('#document_id').val(p.doc_id);
        $('#cedula_escolar').val(p.ced_esc);
        $('#parent_dni').val(p.parent_dni);
        $('#child_number').val(p.child_num);
        $('#parent_ref').val(p.parent_ref);

        $.ajax({
            type: 'POST',
            url: './?action=ajax',
            data: {
                function: 'add_participant',
                is_new: isNew,
                id_activity: $('#id_activity').val() || '',
                id_final_user: idFinalUser,
                activity: $('#activity').val() || '',
                date_activity: $('#date_activity').val() || '',
                estate: $('#estate').val() || '',
                code_info: $('#code_info').val() || '',
                name: $('#name').val() || p.nom_1,
                name_2: $('#name_2').val() || p.nom_2,
                lastname: $('#lastname').val() || p.ape_1,
                lastname_2: $('#lastname_2').val() || p.ape_2,
                user_nationality: $('#user_nationality').val() || 'V',
                user_has_document: p.has_doc,
                document_id: p.doc_id,
                cedula_escolar: p.ced_esc,
                parent_dni: p.parent_dni,
                child_number: p.child_num,
                user_f_nacimiento: $('#user_f_nacimiento').val() || p.nacimiento,
                gender: $('#gender').val() || p.gender,
                user_comunity_type: $('#user_comunity_type').val() || 'No aplica',
                user_pertenece_organizacion: $('#user_pertenece_organizacion').val() || 'No aplica',
                phone: $('#phone').val() || p.telefono,
                email: $('#email').val() || '',
                etnia: $('#user_etnia').val() || 'No aplica',
                line_action: $('#line_action').val() || '',
                report_type: $('#report_type').val() || '',
                disability_type: $('#disability_type').val() || 'No aplica',
                uid_fac: $('#uid_fac').val() || '',
                parent_ref: p.parent_ref,
                user_profesion: $('#user_profesion').val() || 'Estudiante',
                user_ocupacion: $('#user_ocupacion').val() || 'Estudiante',
                equipo_sala_comunal: $('#equipo_sala_comunal').val() || '',
                age: p.age
            }
        }).done(function(msg) {
            window.__ajax_done = true;
            window.__ajax_res = msg;
        }).fail(function(err) {
            window.__ajax_done = true;
            window.__ajax_res = 'ERROR: ' + (err.statusText || 'Error de comunicación AJAX');
        });
    """, ajax_params)

    # Esperar respuesta de la petición AJAX activamente
    resp_servidor = ""
    for _ in range(20):
        done = driver.execute_script("return window.__ajax_done;")
        if done:
            resp_servidor = str(driver.execute_script("return window.__ajax_res;") or "").strip()
            break
        time.sleep(0.2)

    # Si InfoApp respondió con error o advertencia explícita
    if resp_servidor.startswith("ERROR:") or "¡AVISO!:" in resp_servidor or "ATENCIÓN" in resp_servidor or "ATENCION" in resp_servidor:
        capturar_pantalla_error(driver, cedula_busqueda)
        return False, resp_servidor

    # 5. AUDITORÍA Y VERIFICACIÓN REAL EN LA TABLA DE INFOAPP (RECARGA Y VERIFICACIÓN OBLIGATORIA)
    driver.get(url_actividad)
    esperar_desbloqueo_ajax(driver)
    time.sleep(1.5)
    limpiar_overlays(driver)

    doc_busc = str(cedula_busqueda).strip()
    nom_busc = str(nom_1).strip().lower()
    ape_busc = str(ape_1).strip().lower()

    # Verificación estricta en el DOM de la tabla de la actividad
    esta_verificado = driver.execute_script("""
        var doc = arguments[0];
        var nom = arguments[1];
        var ape = arguments[2];
        var filas = document.querySelectorAll('table tbody tr, .card-content table tr');
        for (var i = 0; i < filas.length; i++) {
            var txt = (filas[i].innerText || '').toLowerCase();
            if (doc && doc !== 'no escolarizado' && doc !== 'no aplica' && txt.includes(doc.toLowerCase())) return true;
            if (nom && ape && txt.includes(nom) && txt.includes(ape)) return true;
        }
        return false;
    """, doc_busc, nom_busc, ape_busc)

    if esta_verificado:
        return True, "Registrado y verificado en la tabla de InfoApp"
    else:
        capturar_pantalla_error(driver, cedula_busqueda)
        detalle_err = resp_servidor if resp_servidor else "El participante no aparece en la tabla de InfoApp (no se guardó)"
        return False, detalle_err

def ejecutar_carga_infoapp(
    participantes: list,
    config: dict,
    indice_inicio: int = 0,
    log_callback = None,
    progreso_callback = None
) -> tuple:
    """Orquesta la inyección masiva de participantes en actividades formativas."""
    if log_callback is None:
        log_callback = config.get('log_callback')
    if progreso_callback is None:
        progreso_callback = config.get('progreso_callback')

    def _emitir_log(mensaje: str):
        if log_callback:
            try:
                log_callback(mensaje)
            except Exception:
                pass

    def _emitir_progreso(actual: int, total_p: int, desc: str = ""):
        if progreso_callback:
            try:
                progreso_callback(actual, total_p, desc)
            except Exception:
                pass

    driver_contenedor = {'driver': None}
    cargados_exitosos = []
    fallidos = []
    t_inicio = time.time()
    total = len(participantes)

    print("\n" + "=" * 80)
    print(f"   [+] INICIANDO CARGA RPA: {total - indice_inicio} PARTICIPANTES")
    print("================================================================================")
    _emitir_log(f"[INFO] Iniciando automatización web Selenium ({total - indice_inicio} participantes)...")
    _emitir_progreso(indice_inicio, total, "Iniciando navegador...")

    try:
        asegurar_navegador_activo(driver_contenedor, config)
        _emitir_log(f"[OK] Sesión autenticada en InfoApp con usuario '{config.get('usuario', '')}'.")
        _emitir_log(f"[WEB] Actividad en proceso: ID {config.get('id_actividad', '')}")

        for i in range(indice_inicio, total):
            alumno = participantes[i]
            nom_comp = f"{alumno.get('nombre','')} {alumno.get('apellido','')}".strip()
            doc_str = alumno.get('cedula') or (f"CE:{alumno.get('cedula_escolar')}" if alumno.get('cedulado') == 'escolar' else (f"Rep:{alumno.get('cedula_padre')}" if alumno.get('cedula_padre') else "S/C"))

            id_act = config.get('id_actividad', '')
            renderizar_panel_carga(
                i + 1, total, alumno, len(cargados_exitosos), len(fallidos), t_inicio, "Procesando en InfoApp...", id_actividad=id_act
            )
            _emitir_progreso(i + 1, total, f"Procesando: {nom_comp}")
            _emitir_log(f"[PROCESANDO] Alumno {i + 1}/{total}: {nom_comp} ({doc_str})...")

            cargado = False
            reintentos = 0

            while not cargado:
                try:
                    asegurar_navegador_activo(driver_contenedor, config)
                    driver = driver_contenedor['driver']

                    exito, detalle = registrar_alumno_en_web(driver, alumno, config)

                    if exito:
                        renderizar_panel_carga(
                            i + 1, total, alumno, len(cargados_exitosos) + 1, len(fallidos), t_inicio, f"[OK] Verificado en tabla", id_actividad=id_act
                        )
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "EXITOSO", detalle)
                        cargados_exitosos.append(alumno)
                        guardar_estado_sesion(config, participantes, i + 1)
                        _emitir_log(f"[OK] Alumno {i + 1}/{total}: {nom_comp} verificado en InfoApp.")
                        _emitir_progreso(i + 1, total, f"[OK] {nom_comp}")
                        cargado = True
                    else:
                        renderizar_panel_carga(
                            i + 1, total, alumno, len(cargados_exitosos), len(fallidos) + 1, t_inicio, f"[ERROR] {detalle}", id_actividad=id_act
                        )
                        print(f"\n[-] INCIDENCIA con '{nom_comp}': {detalle}")
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "FALLIDO", detalle)
                        capturar_pantalla_error(driver, doc_str)
                        _emitir_log(f"[ERROR] Incidencia con '{nom_comp}': {detalle}")

                        if config.get('modo_gui'):
                            accion = config.get('accion_defecto_incidencia', 'SKIP')
                            _emitir_log(f"[AVISO] Modo GUI: Omitiendo participante '{nom_comp}' tras registrar evidencia.")
                        else:
                            accion = prompt_reintentar_alumno(nom_comp, detalle)

                        if accion == "SKIP":
                            fallidos.append({'participante': alumno, 'estado': 'OMITIDO', 'detalle': detalle})
                            guardar_estado_sesion(config, participantes, i + 1)
                            cargado = True
                        elif accion == "PAUSE":
                            print("💾 Sesión pausada y guardada en disco.")
                            _emitir_log("[PAUSA] Sesión pausada por el usuario.")
                            return cargados_exitosos, fallidos, time.time() - t_inicio

                except (NoSuchWindowException, WebDriverException) as we:
                    capturar_pantalla_error(driver_contenedor.get('driver'), doc_str)
                    if "invalid argument" in str(we).lower():
                        raise ValueError(f"URL inválida: '{config.get('url')}'. Ingresa una URL completa de InfoApp.")
                    reintentos += 1
                    if reintentos > 3:
                        raise RuntimeError(f"Fallo crítico persistente con el navegador: {we}")
                    time.sleep(1)
                except Exception as ex:
                    capturar_pantalla_error(driver_contenedor.get('driver'), doc_str)
                    registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "CRITICO", str(ex))
                    fallidos.append({'participante': alumno, 'estado': 'FALLIDO', 'detalle': str(ex)})
                    guardar_estado_sesion(config, participantes, i + 1)
                    cargado = True

    finally:
        if driver_contenedor.get('driver'):
            try:
                driver_contenedor['driver'].quit()
            except Exception:
                pass

    return cargados_exitosos, fallidos, time.time() - t_inicio

# =============================================================================
# SECCIÓN 2: AUTOMATIZACIÓN DE ATENCIÓN AL USUARIO Y SERVICIOS
# =============================================================================

def registrar_nuevo_usuario_perfil(driver, persona: dict, config_servicio: dict) -> bool:
    """Registra a un usuario nuevo en 'userform_new' cuando no existe previamente."""
    url_new = "https://infoapp2.infocentro.gob.ve/index.php?view=userform_new&new=1"
    driver.get(url_new)
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)
    time.sleep(1.0)

    wait = WebDriverWait(driver, cm.obtener_timeout("element_wait_seconds", 10))
    wait.until(EC.presence_of_element_located((By.ID, "userdata")))

    partes_nom = str(persona.get('nombre', '')).strip().split()
    nom_1 = partes_nom[0] if partes_nom else "Usuario"
    nom_2 = " ".join(partes_nom[1:]) if len(partes_nom) > 1 else ""

    partes_ape = str(persona.get('apellido', '')).strip().split()
    ape_1 = partes_ape[0] if partes_ape else "Infocentro"
    ape_2 = " ".join(partes_ape[1:]) if len(partes_ape) > 1 else ""

    es_cedulado = (persona.get('cedulado') == 'si' and bool(persona.get('cedula')))
    cedula_padre_num = re.sub(r'\D', '', str(persona.get('cedula_padre', '')))

    if es_cedulado:
        cedula_raw = str(persona.get('cedula', '')).strip()
        es_ext = cedula_raw.startswith("E-")
        cedula_num = cedula_raw.replace("E-", "").replace("V-", "")
        nacionalidad = "E" if es_ext else "V"
        has_doc_val = "Si"
        parent_dni_val = "No aplica"
        child_num_val = "0"
        correo_unico = f"ci{cedula_num}@infocentro.gob.ve"
    elif cedula_padre_num and len(cedula_padre_num) >= 5:
        cedula_num = ""
        nacionalidad = "V"
        has_doc_val = "No/Menor de edad"
        parent_dni_val = cedula_padre_num
        child_num_val = "1"
        correo_unico = f"ci{cedula_padre_num}_hijo1@infocentro.gob.ve"
    else:
        return False, "Menor sin documento propio ni cédula de representante válida (imposible registrar perfil en InfoApp)"

    telefono = persona.get('telefono', '0412-0000000')
    genero_str = "Mujer" if persona.get('genero') == 'F' else "Hombre"
    f_nac = persona.get('nacimiento', '2000-01-01')

    info_cfg = config_servicio.get('infocentro', {})
    estado_id = info_cfg.get('estado_id', '22')
    direccion_def = info_cfg.get('direccion', 'Av. principal El Jovito, Antigua Sede Del Inan')

    # Calcular nivel académico basado en la edad
    try:
        edad_num = int(persona.get('edad', 0))
    except (ValueError, TypeError):
        edad_num = 0

    if edad_num <= 5:
        nivel_academico = 'Educación preescolar'
    elif edad_num <= 11:
        nivel_academico = 'Educación primaria'
    elif edad_num <= 14:
        nivel_academico = 'Primer ciclo de secundaria'
    elif edad_num <= 17:
        nivel_academico = 'Segundo ciclo de secundaria'
    else:
        nivel_academico = 'Educación primaria' # Base por defecto para adultos

    situacion_laboral = 'No trabaja' if edad_num < 18 else 'Trabajo independiente'

    driver.execute_script(f"""
        if (document.getElementById('user_nationality')) document.getElementById('user_nationality').value = '{nacionalidad}';
        if (document.getElementById('user_has_document')) {{
            document.getElementById('user_has_document').value = '{has_doc_val}';
            document.getElementById('user_has_document').dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        if ('{has_doc_val}' === 'Si') {{
            if (document.getElementById('user_dni')) document.getElementById('user_dni').value = '{cedula_num}';
        }} else {{
            if (document.getElementById('parent_dni')) document.getElementById('parent_dni').value = '{parent_dni_val}';
            if (document.getElementById('child_number')) document.getElementById('child_number').value = '{child_num_val}';
            if (document.getElementById('parent_ref')) document.getElementById('parent_ref').value = '{parent_dni_val}{child_num_val}';
        }}

        if (document.getElementById('user_nombres')) document.getElementById('user_nombres').value = '{nom_1}';
        let n2 = document.querySelector("input[name='user_nombre_2']");
        if (n2) n2.value = '{nom_2}';

        let ap1 = document.querySelector("input[name='user_apellidos']");
        if (ap1) ap1.value = '{ape_1}';
        let ap2 = document.querySelector("input[name='user_apellido_2']");
        if (ap2) ap2.value = '{ape_2}';

        if (document.getElementById('user_telefono')) document.getElementById('user_telefono').value = '{telefono}';
        if (document.getElementById('user_correo')) document.getElementById('user_correo').value = '{correo_unico}';

        if (document.getElementById('user_genero')) document.getElementById('user_genero').value = '{genero_str}';
        if (document.getElementById('user_f_nacimiento')) document.getElementById('user_f_nacimiento').value = '{f_nac}';

        if (document.getElementById('user_comunity_type')) document.getElementById('user_comunity_type').value = 'No aplica';
        if (document.getElementById('user_etnia')) document.getElementById('user_etnia').value = 'No aplica';
        if (document.getElementById('disability_type')) document.getElementById('disability_type').value = 'No aplica';
        let org = document.querySelector("select[name='user_pertenece_organizacion']");
        if (org) org.value = 'No aplica';

        if (document.getElementById('estados')) {{
            document.getElementById('estados').value = '{estado_id}';
            document.getElementById('estados').dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        let dir = document.querySelector("input[name='user_direccion']");
        if (dir) dir.value = '{direccion_def}';

        if (document.getElementById('user_nivel_academ')) document.getElementById('user_nivel_academ').value = '{nivel_academico}';
        if (document.getElementById('user_profesion')) document.getElementById('user_profesion').value = 'Sin títulos universitarios';
        if (document.getElementById('user_ocupacion')) document.getElementById('user_ocupacion').value = 'Estudiante';
        if (document.getElementById('user_empleado')) document.getElementById('user_empleado').value = '{situacion_laboral}';
    """)

    time.sleep(1.5)
    esperar_desbloqueo_ajax(driver)

    try:
        driver.execute_script("""
            let mun = document.getElementById('municipios_1');
            if (mun && mun.options.length > 1) {
                mun.selectedIndex = 1;
                mun.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)
    except Exception:
        pass

    driver.execute_script("""
        let form = document.getElementById('userdata');
        if (form) {
            form.submit();
        }
    """)

    time.sleep(2.0)
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)
    return True

def registrar_servicio_persona(driver, persona: dict, config_servicio: dict) -> tuple:
    """Ejecuta el ciclo de registro de un servicio para una persona en InfoApp."""
    url_servicios = "https://infoapp2.infocentro.gob.ve/admin/index.php?view=services"
    wait = WebDriverWait(driver, cm.obtener_timeout("element_wait_seconds", 10))

    if not driver.current_url or "view=services" not in driver.current_url:
        driver.get(url_servicios)
        esperar_desbloqueo_ajax(driver)
        limpiar_overlays(driver)

    # 1. Abrir Modal de Registro de Servicio
    driver.execute_script("$('#image_preview').modal('show');")
    time.sleep(0.6)

    # 2. Configurar búsqueda
    es_cedulado = (persona.get('cedulado') == 'si' and bool(persona.get('cedula')))
    parent_ci_clean = re.sub(r'\D', '', str(persona.get('cedula_padre', '')))

    if es_cedulado:
        cedula_busc = str(persona.get('cedula', '')).replace("E-", "").replace("V-", "").strip()
        doc_tipo = "Si"
    else:
        # En InfoApp, los menores no cedulados se buscan bajo parent_ref ({padre}1) o nombre
        cedula_busc = f"{parent_ci_clean}1" if parent_ci_clean else f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip()
        doc_tipo = "No"

    seleccionar_dropdown(driver, "user_has_document", doc_tipo)

    campo_q = wait.until(EC.visibility_of_element_located((By.ID, "q_participante")))
    campo_q.clear()
    campo_q.send_keys(cedula_busc)

    driver.execute_script("codigoAJAX();")
    esperar_desbloqueo_ajax(driver, timeout=6)
    time.sleep(1.0)

    # 3. Comprobar si el usuario existe
    user_f_id = driver.execute_script("return (document.getElementById('user_f_id') ? document.getElementById('user_f_id').value : '');")
    name_param = driver.execute_script("return (document.getElementById('name_param') ? document.getElementById('name_param').value : '');")

    usuario_encontrado = bool(user_f_id and user_f_id.strip() != "" and name_param != "No existe este usuario")

    # Si no existe en InfoApp
    if not usuario_encontrado:
        if persona.get('nombre'):
            driver.execute_script("$('#image_preview').modal('hide');")
            time.sleep(0.5)
            registrar_nuevo_usuario_perfil(driver, persona, config_servicio)

            driver.get(url_servicios)
            esperar_desbloqueo_ajax(driver)
            limpiar_overlays(driver)

            driver.execute_script("$('#image_preview').modal('show');")
            time.sleep(0.6)

            seleccionar_dropdown(driver, "user_has_document", doc_tipo)
            campo_q = wait.until(EC.visibility_of_element_located((By.ID, "q_participante")))
            campo_q.clear()
            campo_q.send_keys(cedula_busc)
            driver.execute_script("codigoAJAX();")
            esperar_desbloqueo_ajax(driver, timeout=6)
            time.sleep(1.0)

            user_f_id = driver.execute_script("return (document.getElementById('user_f_id') ? document.getElementById('user_f_id').value : '');")
            usuario_encontrado = bool(user_f_id and user_f_id.strip() != "")

        if not usuario_encontrado:
            capturar_pantalla_error(driver, cedula_busc)
            driver.execute_script("$('#image_preview').modal('hide');")
            return False, "Usuario no existe en InfoApp (requiere registro previo de perfil)"

    # 4. Asignar Servicio y Fecha
    tipo_srv = config_servicio.get('tipo_servicio', 'Gestión en el Sistema de Protección Social Patria')
    fecha_srv = config_servicio.get('fecha_servicio', datetime.now().strftime("%Y-%m-%d"))

    seleccionar_dropdown(driver, "tipo_servicio", tipo_srv)

    driver.execute_script(f"""
        if (document.getElementById('user_tipo_servicio')) {{
            document.getElementById('user_tipo_servicio').value = "{tipo_srv}";
        }}
        if (document.getElementById('tipo_servicio')) {{
            document.getElementById('tipo_servicio').value = "{tipo_srv}";
        }}

        let f_inp = document.getElementById('user_fecha_servicio');
        if (f_inp) {{
            f_inp.type = 'date';
            f_inp.value = '{fecha_srv}';
            f_inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            f_inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        let f_alt = document.querySelector("input[name='user_fecha_servicio']");
        if (f_alt && f_alt !== f_inp) {{
            f_alt.value = '{fecha_srv}';
        }}
    """)

    # 5. Enviar el formulario del servicio
    limpiar_overlays(driver)
    driver.execute_script("""
        var form = document.getElementById('form');
        var user_f_id = document.getElementById('user_f_id') ? document.getElementById('user_f_id').value : '';
        var user_email = document.getElementById('user_correo_update') ? document.getElementById('user_correo_update').value : '';

        $.ajax({
            type: "POST",
            url: "./?action=services_users",
            data: {
                function: "get_repeated_email",
                id: user_f_id,
                email: user_email
            }
        }).always(function() {
            $('#cover-spin').show(0);
            form.submit();
        });
    """)

    time.sleep(2.0)
    esperar_desbloqueo_ajax(driver)
    limpiar_overlays(driver)

    # 6. VERIFICACIÓN EN LA TABLA DOM DE SERVICIOS
    driver.get(url_servicios)
    esperar_desbloqueo_ajax(driver)
    time.sleep(1.2)
    limpiar_overlays(driver)

    nom_busc = str(persona.get('nombre', '')).strip().split()[0].lower() if persona.get('nombre') else ""
    ape_busc = str(persona.get('apellido', '')).strip().split()[0].lower() if persona.get('apellido') else ""
    uid_busc = str(user_f_id).strip()
    doc_busc = str(cedula_busc).strip().lower()

    verificado = driver.execute_script("""
        var doc = arguments[0];
        var uid = arguments[1];
        var nom = arguments[2];
        var ape = arguments[3];
        var filas = document.querySelectorAll('table tbody tr');
        for (var i = 0; i < Math.min(filas.length, 10); i++) {
            var txt = (filas[i].innerText || '').toLowerCase();
            if (uid && uid.length >= 2 && txt.indexOf(uid.toLowerCase()) !== -1) return true;
            if (nom && ape && txt.indexOf(nom) !== -1 && txt.indexOf(ape) !== -1) return true;
            if (doc && doc.length >= 3 && txt.indexOf(doc) !== -1) return true;
        }
        return false;
    """, doc_busc, uid_busc, nom_busc, ape_busc)

    if verificado:
        return True, f"Servicio registrado y verificado en tabla (ID: {user_f_id})"
    else:
        capturar_pantalla_error(driver, cedula_busc)
        return False, f"El servicio para la cédula {cedula_busc} no aparece en la tabla de InfoApp (no se guardó)"

def ejecutar_carga_servicios_infoapp(
    personas: list,
    config: dict,
    config_servicio: dict,
    indice_inicio: int = 0,
    fn_guardar_checkpoint = None,
    log_callback = None,
    progreso_callback = None
) -> tuple:
    """Orquesta la inyección masiva de servicios al usuario en InfoApp."""
    if log_callback is None:
        log_callback = config.get('log_callback')
    if progreso_callback is None:
        progreso_callback = config.get('progreso_callback')

    def _emitir_log(mensaje: str):
        if log_callback:
            try:
                log_callback(mensaje)
            except Exception:
                pass

    def _emitir_progreso(actual: int, total_p: int, desc: str = ""):
        if progreso_callback:
            try:
                progreso_callback(actual, total_p, desc)
            except Exception:
                pass

    driver_contenedor = {'driver': None}
    cargados_exitosos = []
    fallidos = []
    t_inicio = time.time()
    total = len(personas)

    tipo_srv = config_servicio.get('tipo_servicio', 'Gestión en el Sistema de Protección Social Patria')
    fecha_srv = config_servicio.get('fecha_servicio', datetime.now().strftime("%Y-%m-%d"))

    _emitir_log(f"[INFO] Iniciando automatización de servicios comunitarios ({total - indice_inicio} usuarios)...")
    _emitir_log(f"[INFO] Servicio: {tipo_srv} | Fecha: {fecha_srv}")
    _emitir_progreso(indice_inicio, total, "Iniciando navegador...")

    try:
        renderizar_panel_servicios(
            indice_inicio + 1, total, personas[indice_inicio], len(cargados_exitosos), len(fallidos), t_inicio, tipo_srv, fecha_srv, "Iniciando navegador y sesión..."
        )
        asegurar_navegador_activo(driver_contenedor, config)
        _emitir_log(f"[OK] Sesión autenticada en InfoApp con usuario '{config.get('usuario', '')}'.")

        for i in range(indice_inicio, total):
            persona = personas[i]
            nom_comp = f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip() or f"Usuario C.I. {persona.get('cedula', '')}"
            doc_str = persona.get('cedula') or (f"CE:{persona.get('cedula_escolar')}" if persona.get('cedula_escolar') else f"Rep:{persona.get('cedula_padre', '')}")

            renderizar_panel_servicios(
                i + 1, total, persona, len(cargados_exitosos), len(fallidos), t_inicio, tipo_srv, fecha_srv, "Procesando en InfoApp..."
            )
            _emitir_progreso(i + 1, total, f"Procesando: {nom_comp}")
            _emitir_log(f"[PROCESANDO] Servicio {i + 1}/{total}: {nom_comp} ({doc_str})...")

            cargado = False
            reintentos = 0

            while not cargado:
                try:
                    asegurar_navegador_activo(driver_contenedor, config)
                    driver = driver_contenedor['driver']

                    exito, detalle = registrar_servicio_persona(driver, persona, config_servicio)

                    if exito:
                        renderizar_panel_servicios(
                            i + 1, total, persona, len(cargados_exitosos) + 1, len(fallidos), t_inicio, tipo_srv, fecha_srv, f"[OK] {detalle}"
                        )
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "EXITOSO", detalle)
                        cargados_exitosos.append(persona)
                        
                        if fn_guardar_checkpoint:
                            fn_guardar_checkpoint(config, config_servicio, personas, i + 1)
                            
                        _emitir_log(f"[OK] Servicio {i + 1}/{total}: {nom_comp} registrado exitosamente.")
                        _emitir_progreso(i + 1, total, f"[OK] {nom_comp}")
                        cargado = True
                    else:
                        renderizar_panel_servicios(
                            i + 1, total, persona, len(cargados_exitosos), len(fallidos) + 1, t_inicio, tipo_srv, fecha_srv, f"[ERROR] {detalle}"
                        )
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "FALLIDO", detalle)
                        capturar_pantalla_error(driver, doc_str)
                        _emitir_log(f"[ERROR] Incidencia con servicio de '{nom_comp}': {detalle}")

                        if config.get('modo_gui'):
                            accion = config.get('accion_defecto_incidencia', 'SKIP')
                            _emitir_log(f"[AVISO] Modo GUI: Omitiendo usuario '{nom_comp}' tras registrar evidencia.")
                        else:
                            accion = prompt_reintentar_alumno(nom_comp, detalle)

                        if accion == "SKIP":
                            fallidos.append({'participante': persona, 'estado': 'OMITIDO', 'detalle': detalle})
                            if fn_guardar_checkpoint:
                                fn_guardar_checkpoint(config, config_servicio, personas, i + 1)
                            cargado = True
                        elif accion == "PAUSE":
                            print("\n[PAUSA] Sesión pausada por el usuario.")
                            _emitir_log("[PAUSA] Sesión de servicios pausada por el usuario.")
                            return cargados_exitosos, fallidos, time.time() - t_inicio

                except (NoSuchWindowException, WebDriverException) as we:
                    capturar_pantalla_error(driver_contenedor.get('driver'), doc_str)
                    reintentos += 1
                    if reintentos > 3:
                        raise RuntimeError(f"Error persistente con el navegador: {we}")
                    time.sleep(1)
                except Exception as ex:
                    capturar_pantalla_error(driver_contenedor.get('driver'), doc_str)
                    registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "CRITICO", str(ex))
                    fallidos.append({'participante': persona, 'estado': 'FALLIDO', 'detalle': str(ex)})
                    if fn_guardar_checkpoint:
                        fn_guardar_checkpoint(config, config_servicio, personas, i + 1)
                    cargado = True

    finally:
        if driver_contenedor.get('driver'):
            try:
                driver_contenedor['driver'].quit()
            except Exception:
                pass

    return cargados_exitosos, fallidos, time.time() - t_inicio
