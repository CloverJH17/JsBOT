#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: AUTOMATIZADOR WEB PLAYWRIGHT (automatizador_web.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
Motor exclusivo: Playwright (auto-waiting nativo, contexto persistente).
"""

import os
import sys
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, BrowserContext

from modulos.gestor_sesion import (
    registrar_evento_log,
    guardar_estado_sesion,
    registrar_inscrito_historico_db
)
from modulos import config_manager as cm
from modulos.driver_factory import obtener_contexto_playwright
import modulos.entorno as entorno
from modulos.web_utils import (
    limpiar_overlays,
    esperar_desbloqueo_ajax,
    realizar_login_infoapp,
)
from modulos.interfaz_usuario import (
    prompt_reintentar_alumno,
    renderizar_panel_carga,
    renderizar_panel_servicios,
    limpiar_consola,
)

BASE_DIR = str(entorno.RAIZ_PROYECTO)
SCREENSHOTS_DIR = str(entorno.CARPETA_SCREENSHOTS)
CONFIG_DIR = str(entorno.CARPETA_CONFIG)
SETTINGS_FILE = str(entorno.ARCHIVO_SETTINGS)


# =============================================================================
# UTILIDADES INTERNAS
# =============================================================================

def capturar_pantalla_error(page, doc_str: str):
    """Guarda una captura de pantalla ante errores de navegación o carga."""
    if not cm.captura_screenshots_activada():
        return
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_limpio = "".join(c for c in str(doc_str or "SD") if c.isalnum() or c in ('_', '-'))
        ruta = os.path.join(SCREENSHOTS_DIR, f"error_{doc_limpio}_{ts}.png")
        if page:
            page.screenshot(path=ruta)
    except Exception:
        pass


# =============================================================================
# MOTOR PLAYWRIGHT — CONTEXTO PERSISTENTE Y AUTO-WAITING
# =============================================================================

def iniciar_contexto_playwright(user_data_dir: str = None, headless: bool = False, navegador: str = "chromium"):
    """
    Inicia un contexto persistente con Playwright delegando a la factoría central.
    Garantiza compatibilidad con Microsoft Edge nativo, Google Chrome y auto-fallback en cascada.
    """
    return obtener_contexto_playwright(
        headless=headless,
        navegador=navegador,
        user_data_dir=user_data_dir,
    )


def realizar_login(page: Page, config: dict):
    """Ejecuta el inicio de sesión en InfoApp usando Playwright."""
    url_login = cm.obtener_url_login()
    print(f"🔐 Accediendo a InfoApp ({config['usuario']})...")
    realizar_login_infoapp(page, config['usuario'], config['clave'], url_login)
    print("✅ Autenticado con éxito en InfoApp.")


def asegurar_sesion_activa(contexto_contenedor: dict, config: dict):
    """
    Garantiza que el contexto Playwright esté activo y la sesión no haya expirado.
    contexto_contenedor = {'pw': ..., 'context': ..., 'page': ...}
    """
    necesita_reabrir = (
        contexto_contenedor.get('page') is None
        or contexto_contenedor.get('context') is None
    )

    if not necesita_reabrir:
        # Detectar sesión expirada por URL
        try:
            current = contexto_contenedor['page'].url.lower()
            if "login" in current or "acceder" in current:
                print("⚠️ Sesión de InfoApp caducada. Reautenticando...")
                realizar_login(contexto_contenedor['page'], config)
                return
        except Exception:
            necesita_reabrir = True

    if necesita_reabrir:
        print("\n🌐 Iniciando navegador y sesión en InfoApp...")
        # Cerrar contexto anterior si existe
        for key in ('page', 'context', 'pw'):
            try:
                if contexto_contenedor.get(key):
                    contexto_contenedor[key].close() if key != 'pw' else contexto_contenedor[key].stop()
            except Exception:
                pass

        cfg_browser = cm.obtener_browser_cfg()
        nav = cfg_browser["priority"][0] if cfg_browser["priority"] else "chromium"
        pw, context = iniciar_contexto_playwright(navegador=nav)
        page = context.new_page()

        contexto_contenedor['pw'] = pw
        contexto_contenedor['context'] = context
        contexto_contenedor['page'] = page
        realizar_login(page, config)


# =============================================================================
# SECCIÓN 1: AUTOMATIZACIÓN DE ACTIVIDADES FORMATIVAS (PLAYWRIGHT)
# =============================================================================

def registrar_alumno_playwright(page: Page, alumno: dict, config: dict) -> tuple:
    """
    Ejecuta el ciclo de inscripción de un participante con Playwright:
    1. Búsqueda superior por AJAX (document_id, cedula_escolar o parent_ref).
    2. Verificación de existencia previa en base de datos.
    3. Llenado del formulario con validaciones oficiales de InfoApp.
    4. Envío directo AJAX add_participant + confirmación inmediata por respuesta de servidor.
    5. Auditoría y verificación real en la tabla de InfoApp.
    """
    url_actividad = config.get('url', '')
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

    if not page.url or "id_activity" not in page.url:
        page.goto(url_actividad, wait_until="domcontentloaded")
        esperar_desbloqueo_ajax(page)
        limpiar_overlays(page)

    # 1. Búsqueda superior AJAX
    try:
        page.locator("#search_field").select_option(tipo_busqueda)
        page.locator("#q_participante").fill(str(cedula_busqueda))

        lupa_btn = page.locator("button[onclick*='codigoAJAX']").first
        lupa_btn.scroll_into_view_if_needed()
        limpiar_overlays(page)
        lupa_btn.click(force=True)

        esperar_desbloqueo_ajax(page, timeout=6)
        limpiar_overlays(page)
    except Exception as e_busq:
        return False, f"Error al ejecutar búsqueda AJAX: {e_busq}"

    # 2. Verificar si es usuario preexistente
    nombre_detectado = ""
    try:
        nombre_detectado = page.locator("#name").input_value().strip()
    except Exception:
        pass

    es_preexistente = bool(nombre_detectado and nombre_detectado != "")

    # Nombres y Apellidos
    partes_nom = str(alumno.get('nombre', '')).strip().split()
    nom_1 = partes_nom[0] if partes_nom else alumno.get('nombre', '')
    nom_2 = " ".join(partes_nom[1:]) if len(partes_nom) > 1 else ""

    partes_ape = str(alumno.get('apellido', '')).strip().split()
    ape_1 = partes_ape[0] if partes_ape else alumno.get('apellido', '')
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
        try:
            page.locator("#user_nationality").select_option("V")
        except Exception:
            pass

        # Selección de modalidad de cédula
        if cedulado_tipo == "si":
            try:
                page.locator("#user_has_document").select_option("Si")
            except Exception:
                pass
            page.evaluate("if(document.getElementById('document_id_l')) document.getElementById('document_id_l').style.display='block';")
            try:
                page.locator("#document_id").fill(str(alumno.get('cedula', '')))
            except Exception:
                pass
        elif cedulado_tipo == "escolar":
            try:
                page.locator("#user_has_document").select_option(label="Cédula escolar")
            except Exception:
                try:
                    page.locator("#user_has_document").select_option("Cédula escolar")
                except Exception:
                    pass
            page.evaluate("if(document.getElementById('cedula_escolar_l')) document.getElementById('cedula_escolar_l').style.display='block';")
            try:
                page.locator("#cedula_escolar").fill(str(alumno.get('cedula_escolar', '')))
            except Exception:
                pass
        else:
            try:
                page.locator("#user_has_document").select_option(label="No/No escolarizado")
            except Exception:
                try:
                    page.locator("#user_has_document").select_option("No/No escolarizado")
                except Exception:
                    pass
            page.evaluate("if(document.getElementById('parent_dni_div')) document.getElementById('parent_dni_div').style.display='block';")
            page.evaluate("if(document.getElementById('child_number_div')) document.getElementById('child_number_div').style.display='block';")
            try:
                page.locator("#parent_dni").fill(str(alumno.get('cedula_padre', '')))
                page.locator("#child_number").fill("1")
            except Exception:
                pass

        try:
            page.locator("#name").fill(nom_1)
        except Exception:
            page.evaluate("""(val) => {
                const el = document.getElementById('name');
                if (el) el.value = val;
            }""", nom_1)

        if nom_2:
            try:
                page.locator("#name_2").fill(nom_2)
            except Exception:
                page.evaluate("""(val) => {
                    const el = document.getElementById('name_2');
                    if (el) el.value = val;
                }""", nom_2)

        try:
            page.locator("#lastname").fill(ape_1)
        except Exception:
            page.evaluate("""(val) => {
                const el = document.getElementById('lastname');
                if (el) el.value = val;
            }""", ape_1)

        if ape_2:
            try:
                page.locator("#lastname_2").fill(ape_2)
            except Exception:
                page.evaluate("""(val) => {
                    const el = document.getElementById('lastname_2');
                    if (el) el.value = val;
                }""", ape_2)

        # Inyección de Fecha de Nacimiento
        if alumno.get('nacimiento'):
            page.evaluate("""(fn_val) => {
                let fn = document.getElementById('user_f_nacimiento');
                if (fn) {
                    fn.value = fn_val;
                    fn.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", str(alumno['nacimiento']))

        # Teléfono
        try:
            page.locator("#phone").fill(str(alumno.get('telefono', '0412-0000000')))
        except Exception:
            pass

        # Género (Hombre / Mujer)
        texto_gen = "Mujer" if alumno.get('genero') == 'F' else "Hombre"
        try:
            page.locator("#gender").select_option(label=texto_gen)
        except Exception:
            try:
                page.locator("#gender").select_option(texto_gen)
            except Exception:
                pass

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
            try:
                page.locator(f"#{cat_id}").select_option(cat_val)
            except Exception:
                pass

    # 4. Envío directo AJAX con sincronización estricta de campos
    limpiar_overlays(page)

    # Determinar valores exactos según la modalidad de documento
    if cedulado_tipo == "si":
        has_doc_val = "Si"
        doc_id_val = str(alumno.get("cedula", "")).strip()
        ced_esc_val = ""
        parent_dni_val = "No aplica"
        child_num_val = ""
        parent_ref_val = "No aplica"
    elif cedulado_tipo == "escolar":
        has_doc_val = "Cédula escolar"
        doc_id_val = ""
        ced_esc_val = str(alumno.get("cedula_escolar", "")).strip()
        parent_dni_val = "No aplica"
        child_num_val = ""
        parent_ref_val = "No aplica"
    else:
        has_doc_val = "No/No escolarizado"
        doc_id_val = "No escolarizado"
        ced_esc_val = ""
        parent_dni_val = str(alumno.get("cedula_padre", "")).strip()
        child_num_val = "1"
        parent_ref_val = f"{parent_dni_val}1" if parent_dni_val else "No aplica"

    is_new_val = 'false' if es_preexistente else 'true'
    gender_val = "Mujer" if alumno.get("genero") == "F" else "Hombre"

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

    # Ejecución AJAX directa de InfoApp
    page.evaluate("""(p) => {
        window.__ajax_done = false;
        window.__ajax_res = null;

        var domIsNew = document.getElementById('is_new') ? document.getElementById('is_new').value : '';
        var isNew = (domIsNew === 'false') ? 'false' : p.is_new;
        var idFinalUser = (typeof window.jQuery !== 'undefined' && $('#id_final_user').length) ? ($('#id_final_user').val() || '0') : '0';

        if (typeof window.jQuery !== 'undefined') {
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
        } else {
            window.__ajax_done = true;
            window.__ajax_res = 'ERROR: jQuery no disponible en InfoApp';
        }
    }""", ajax_params)

    # Esperar respuesta de la petición AJAX activamente
    resp_servidor = ""
    for _ in range(25):
        try:
            done = page.evaluate("() => Boolean(window.__ajax_done)")
            if done:
                resp_servidor = str(page.evaluate("() => window.__ajax_res || ''")).strip()
                break
        except Exception:
            pass
        page.wait_for_timeout(200)

    # Si InfoApp respondió con error o advertencia explícita
    if resp_servidor.startswith("ERROR:") or "¡AVISO!:" in resp_servidor or "ATENCIÓN" in resp_servidor or "ATENCION" in resp_servidor:
        capturar_pantalla_error(page, str(cedula_busqueda))
        return False, resp_servidor

    # 5. Auditoría y verificación real en la tabla de la actividad en InfoApp
    page.goto(url_actividad, wait_until="domcontentloaded")
    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)

    doc_busc = str(cedula_busqueda).strip()
    nom_busc = str(nom_1).strip().lower()
    ape_busc = str(ape_1).strip().lower()

    esta_verificado = False
    try:
        esta_verificado = page.evaluate("""([doc, nom, ape]) => {
            var filas = document.querySelectorAll('table tbody tr, .card-content table tr');
            for (var i = 0; i < filas.length; i++) {
                var txt = (filas[i].innerText || '').toLowerCase();
                if (doc && doc !== 'no escolarizado' && doc !== 'no aplica' && txt.includes(doc.toLowerCase())) return true;
                if (nom && ape && txt.includes(nom) && txt.includes(ape)) return true;
            }
            return false;
        }""", [doc_busc, nom_busc, ape_busc])
    except Exception:
        esta_verificado = False

    if esta_verificado:
        return True, "Registrado y verificado en la tabla de InfoApp"
    else:
        capturar_pantalla_error(page, str(cedula_busqueda))
        return False, f"El participante {nom_1} {ape_1} ({doc_busc}) no figura en la tabla tras el guardado"


def ejecutar_carga_infoapp(
    participantes: list,
    config: dict,
    indice_inicio: int = 0,
    log_callback=None,
    progreso_callback=None
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

    contexto_contenedor = {'pw': None, 'context': None, 'page': None}
    cargados_exitosos = []
    fallidos = []
    t_inicio = time.time()
    total = len(participantes)

    print("\n" + "=" * 80)
    print(f"   [+] INICIANDO CARGA RPA: {total - indice_inicio} PARTICIPANTES")
    print("=" * 80)
    _emitir_log(f"[INFO] Iniciando automatización web Playwright ({total - indice_inicio} participantes)...")
    _emitir_progreso(indice_inicio, total, "Iniciando navegador...")

    try:
        asegurar_sesion_activa(contexto_contenedor, config)
        _emitir_log(f"[OK] Sesión autenticada en InfoApp con usuario '{config.get('usuario', '')}'.")
        _emitir_log(f"[WEB] Actividad en proceso: ID {config.get('id_actividad', '')}")

        for i in range(indice_inicio, total):
            alumno = participantes[i]
            nom_comp = f"{alumno.get('nombre', '')} {alumno.get('apellido', '')}".strip()
            doc_str = (
                alumno.get('cedula')
                or (f"CE:{alumno.get('cedula_escolar')}" if alumno.get('cedulado') == 'escolar' else None)
                or (f"Rep:{alumno.get('cedula_padre')}" if alumno.get('cedula_padre') else "S/C")
            )

            id_act = config.get('id_actividad', '')
            renderizar_panel_carga(i + 1, total, alumno, len(cargados_exitosos), len(fallidos), t_inicio, "Procesando en InfoApp...", id_actividad=id_act)
            _emitir_progreso(i + 1, total, f"Procesando: {nom_comp}")
            _emitir_log(f"[PROCESANDO] Alumno {i + 1}/{total}: {nom_comp} ({doc_str})...")

            cargado = False
            reintentos = 0

            while not cargado:
                try:
                    asegurar_sesion_activa(contexto_contenedor, config)
                    page = contexto_contenedor['page']

                    exito, detalle = registrar_alumno_playwright(page, alumno, config)

                    if exito:
                        renderizar_panel_carga(i + 1, total, alumno, len(cargados_exitosos) + 1, len(fallidos), t_inicio, "[OK] Verificado", id_actividad=id_act)
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "EXITOSO", detalle)
                        cargados_exitosos.append(alumno)
                        guardar_estado_sesion(config, participantes, i + 1)
                        try:
                            registrar_inscrito_historico_db(
                                id_actividad=str(id_act or "general"),
                                cedula=doc_str,
                                nombre=nom_comp,
                                telefono=str(alumno.get('telefono', ''))
                            )
                        except Exception:
                            pass
                        _emitir_log(f"[OK] Alumno {i + 1}/{total}: {nom_comp} registrado en InfoApp.")
                        _emitir_progreso(i + 1, total, f"[OK] {nom_comp}")
                        cargado = True
                    else:
                        renderizar_panel_carga(i + 1, total, alumno, len(cargados_exitosos), len(fallidos) + 1, t_inicio, f"[ERROR] {detalle}", id_actividad=id_act)
                        print(f"\n[-] INCIDENCIA con '{nom_comp}': {detalle}")
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "FALLIDO", detalle)
                        capturar_pantalla_error(page, doc_str)
                        _emitir_log(f"[ERROR] Incidencia con '{nom_comp}': {detalle}")

                        if config.get('modo_gui'):
                            accion = config.get('accion_defecto_incidencia', 'SKIP')
                            _emitir_log(f"[AVISO] Modo GUI: Omitiendo participante '{nom_comp}'.")
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

                except Exception as ex:
                    capturar_pantalla_error(contexto_contenedor.get('page'), doc_str)
                    reintentos += 1
                    if reintentos > 3:
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "CRITICO", str(ex))
                        fallidos.append({'participante': alumno, 'estado': 'FALLIDO', 'detalle': str(ex)})
                        guardar_estado_sesion(config, participantes, i + 1)
                        cargado = True
                    else:
                        # Reintentar con sesión nueva
                        contexto_contenedor['page'] = None

            # Verificación Post-Carga contra InfoApp por HTTP ultrarrápido
            if cargados_exitosos and id_act:
                try:
                    lista_cedulas_verif = [
                        str(a.get("cedula") or a.get("cedula_escolar") or a.get("dni") or "").strip()
                        for a in cargados_exitosos
                        if (a.get("cedula") or a.get("cedula_escolar") or a.get("dni"))
                    ]
                    if lista_cedulas_verif:
                        _emitir_log(f"[VERIFICACIÓN] Comprobando {len(lista_cedulas_verif)} participantes en servidor InfoApp (Actividad #{id_act})...")
                        import requests
                        from modulos.verificador_cargas_export import verificar_participantes_actividad
                        sess_verif = requests.Session()
                        sess_verif.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        if contexto_contenedor.get('context'):
                            try:
                                for ck in contexto_contenedor['context'].cookies():
                                    sess_verif.cookies.set(ck['name'], ck['value'], domain=ck.get('domain', ''), path=ck.get('path', '/'))
                            except Exception:
                                pass
                        res_v = verificar_participantes_actividad(sess_verif, str(id_act), lista_cedulas_verif)
                        tot_c = res_v.get("confirmados_total", len(lista_cedulas_verif))
                        tot_e = res_v.get("esperados_total", len(lista_cedulas_verif))
                        porc = (tot_c / tot_e * 100.0) if tot_e > 0 else 100.0
                        _emitir_log(f"✅ Verificación InfoApp en Servidor: {tot_c}/{tot_e} confirmados ({porc:.1f}%).")
                except Exception as err_v:
                    _emitir_log(f"[AVISO] Verificación post-carga InfoApp omitida: {err_v}")

    finally:
        for key in ('context', 'pw'):
            try:
                if contexto_contenedor.get(key):
                    contexto_contenedor[key].close() if key == 'context' else contexto_contenedor[key].stop()
            except Exception:
                pass

    return cargados_exitosos, fallidos, time.time() - t_inicio


# =============================================================================
# SECCIÓN 2: AUTOMATIZACIÓN DE ATENCIÓN AL USUARIO Y SERVICIOS (PLAYWRIGHT)
# =============================================================================

def registrar_nuevo_usuario_perfil(page: Page, persona: dict, config_servicio: dict) -> tuple:
    """Registra a un usuario nuevo en 'userform_new' cuando no existe previamente."""
    url_new = "https://infoapp2.infocentro.gob.ve/index.php?view=userform_new&new=1"
    page.goto(url_new, wait_until="domcontentloaded")
    esperar_desbloqueo_ajax(page)
    page.locator("#userdata").wait_for(state="attached")

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
        return False, "Menor sin documento propio ni cédula de representante válida"

    telefono = persona.get('telefono', '0412-0000000')
    genero_str = "Mujer" if persona.get('genero') == 'F' else "Hombre"
    f_nac = persona.get('nacimiento', '2000-01-01')

    info_cfg = config_servicio.get('infocentro', {})
    estado_id = info_cfg.get('estado_id', '22')
    direccion_def = info_cfg.get('direccion', 'Av. principal El Jovito, Antigua Sede Del Inan')

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
        nivel_academico = 'Educación primaria'

    situacion_laboral = 'No trabaja' if edad_num < 18 else 'Trabajo independiente'

    payload_usuario = {
        "nacionalidad": str(nacionalidad),
        "has_doc_val": str(has_doc_val),
        "cedula_num": str(cedula_num),
        "parent_dni_val": str(parent_dni_val),
        "child_num_val": str(child_num_val),
        "nom_1": str(nom_1),
        "nom_2": str(nom_2),
        "ape_1": str(ape_1),
        "ape_2": str(ape_2),
        "telefono": str(telefono),
        "correo_unico": str(correo_unico),
        "genero_str": str(genero_str),
        "f_nac": str(f_nac),
        "estado_id": str(estado_id),
        "direccion_def": str(direccion_def),
        "nivel_academico": str(nivel_academico),
        "situacion_laboral": str(situacion_laboral)
    }

    page.evaluate("""(d) => {
        if (document.getElementById('user_nationality')) document.getElementById('user_nationality').value = d.nacionalidad;
        if (document.getElementById('user_has_document')) {
            document.getElementById('user_has_document').value = d.has_doc_val;
            document.getElementById('user_has_document').dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (d.has_doc_val === 'Si') {
            if (document.getElementById('user_dni')) document.getElementById('user_dni').value = d.cedula_num;
        } else {
            if (document.getElementById('parent_dni')) document.getElementById('parent_dni').value = d.parent_dni_val;
            if (document.getElementById('child_number')) document.getElementById('child_number').value = d.child_num_val;
            if (document.getElementById('parent_ref')) document.getElementById('parent_ref').value = d.parent_dni_val + d.child_num_val;
        }
        if (document.getElementById('user_nombres')) document.getElementById('user_nombres').value = d.nom_1;
        let n2 = document.querySelector("input[name='user_nombre_2']");
        if (n2) n2.value = d.nom_2;
        let ap1 = document.querySelector("input[name='user_apellidos']");
        if (ap1) ap1.value = d.ape_1;
        let ap2 = document.querySelector("input[name='user_apellido_2']");
        if (ap2) ap2.value = d.ape_2;
        if (document.getElementById('user_telefono')) document.getElementById('user_telefono').value = d.telefono;
        if (document.getElementById('user_correo')) document.getElementById('user_correo').value = d.correo_unico;
        if (document.getElementById('user_genero')) document.getElementById('user_genero').value = d.genero_str;
        if (document.getElementById('user_f_nacimiento')) document.getElementById('user_f_nacimiento').value = d.f_nac;
        if (document.getElementById('user_comunity_type')) document.getElementById('user_comunity_type').value = 'No aplica';
        if (document.getElementById('user_etnia')) document.getElementById('user_etnia').value = 'No aplica';
        if (document.getElementById('disability_type')) document.getElementById('disability_type').value = 'No aplica';
        let org = document.querySelector("select[name='user_pertenece_organizacion']");
        if (org) org.value = 'No aplica';
        if (document.getElementById('estados')) {
            document.getElementById('estados').value = d.estado_id;
            document.getElementById('estados').dispatchEvent(new Event('change', { bubbles: true }));
        }
        let dir = document.querySelector("input[name='user_direccion']");
        if (dir) dir.value = d.direccion_def;
        if (document.getElementById('user_nivel_academ')) document.getElementById('user_nivel_academ').value = d.nivel_academico;
        if (document.getElementById('user_profesion')) document.getElementById('user_profesion').value = 'Sin títulos universitarios';
        if (document.getElementById('user_ocupacion')) document.getElementById('user_ocupacion').value = 'Estudiante';
        if (document.getElementById('user_empleado')) document.getElementById('user_empleado').value = d.situacion_laboral;
    }""", payload_usuario)

    esperar_desbloqueo_ajax(page)

    try:
        page.evaluate("""
            let mun = document.getElementById('municipios_1');
            if (mun && mun.options.length > 1) {
                mun.selectedIndex = 1;
                mun.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)
    except Exception:
        pass

    page.evaluate("""
        let form = document.getElementById('userdata');
        if (form) { form.submit(); }
    """)

    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)
    return True, "Perfil creado"


def registrar_servicio_persona(page: Page, persona: dict, config_servicio: dict) -> tuple:
    """Ejecuta el ciclo de registro de un servicio para una persona en InfoApp."""
    url_servicios = config_servicio.get('url') or "https://infoapp2.infocentro.gob.ve/admin/index.php?view=services"

    if not page.url or "view=services" not in page.url:
        page.goto(url_servicios, wait_until="domcontentloaded")
        esperar_desbloqueo_ajax(page)
        limpiar_overlays(page)

    # 1. Abrir Modal de Registro de Servicio
    page.evaluate("""() => {
        if (typeof window.jQuery !== 'undefined') {
            $('#image_preview').modal('show');
        }
    }""")
    page.wait_for_timeout(600)

    # 2. Configurar búsqueda
    es_cedulado = (persona.get('cedulado') == 'si' and bool(persona.get('cedula')))
    parent_ci_clean = re.sub(r'\D', '', str(persona.get('cedula_padre', '')))

    if es_cedulado:
        cedula_busc = str(persona.get('cedula', '')).replace("E-", "").replace("V-", "").strip()
        doc_tipo = "Si"
    else:
        cedula_busc = f"{parent_ci_clean}1" if parent_ci_clean else (persona.get('cedula_escolar') or f"{persona.get('nombre', '')} {persona.get('apellido', '')}").strip()
        doc_tipo = "No"

    try:
        page.locator("#user_has_document").select_option(doc_tipo)
    except Exception:
        page.evaluate("""(v) => { if(document.getElementById('user_has_document')) document.getElementById('user_has_document').value = v; }""", str(doc_tipo))

    try:
        page.locator("#q_participante").fill(str(cedula_busc))
    except Exception:
        page.evaluate("""(v) => { if(document.getElementById('q_participante')) document.getElementById('q_participante').value = v; }""", str(cedula_busc))

    page.evaluate("() => { if (typeof codigoAJAX === 'function') codigoAJAX(); }")
    esperar_desbloqueo_ajax(page, timeout=8)
    page.wait_for_timeout(1000)

    # 3. Comprobar si el usuario existe
    try:
        user_f_id = page.evaluate("() => document.getElementById('user_f_id') ? document.getElementById('user_f_id').value.trim() : ''")
        name_param = page.evaluate("() => document.getElementById('name_param') ? document.getElementById('name_param').value.trim() : ''")
    except Exception:
        user_f_id = ""
        name_param = ""
    usuario_encontrado = bool(user_f_id and user_f_id != "" and name_param != "No existe este usuario")

    if not usuario_encontrado:
        if persona.get('nombre'):
            page.evaluate("() => { if(typeof window.jQuery !== 'undefined') $('#image_preview').modal('hide'); }")
            registrar_nuevo_usuario_perfil(page, persona, config_servicio)

            page.goto(url_servicios, wait_until="domcontentloaded")
            esperar_desbloqueo_ajax(page)
            limpiar_overlays(page)

            page.evaluate("() => { if(typeof window.jQuery !== 'undefined') $('#image_preview').modal('show'); }")
            page.wait_for_timeout(600)

            try:
                page.locator("#user_has_document").select_option(doc_tipo)
            except Exception:
                page.evaluate("""(v) => { if(document.getElementById('user_has_document')) document.getElementById('user_has_document').value = v; }""", str(doc_tipo))

            try:
                page.locator("#q_participante").fill(str(cedula_busc))
            except Exception:
                page.evaluate("""(v) => { if(document.getElementById('q_participante')) document.getElementById('q_participante').value = v; }""", str(cedula_busc))

            page.evaluate("() => { if (typeof codigoAJAX === 'function') codigoAJAX(); }")
            esperar_desbloqueo_ajax(page, timeout=8)
            page.wait_for_timeout(1000)

            try:
                user_f_id = page.evaluate("() => document.getElementById('user_f_id') ? document.getElementById('user_f_id').value.trim() : ''")
            except Exception:
                user_f_id = ""
            usuario_encontrado = bool(user_f_id and user_f_id != "")

        if not usuario_encontrado:
            capturar_pantalla_error(page, str(cedula_busc))
            page.evaluate("() => { if(typeof window.jQuery !== 'undefined') $('#image_preview').modal('hide'); }")
            return False, "Usuario no existe en InfoApp (requiere registro previo de perfil)"

    # 4. Asignar Servicio y Fecha
    tipo_srv = config_servicio.get('tipo_servicio', 'Gestión en el Sistema de Protección Social Patria')
    fecha_srv = config_servicio.get('fecha_servicio', datetime.now().strftime("%Y-%m-%d"))

    page.evaluate("""([srv, f_srv]) => {
        if (document.getElementById('user_tipo_servicio')) document.getElementById('user_tipo_servicio').value = srv;
        if (document.getElementById('tipo_servicio')) document.getElementById('tipo_servicio').value = srv;
        let f_inp = document.getElementById('user_fecha_servicio');
        if (f_inp) {
            f_inp.type = 'date';
            f_inp.value = f_srv;
            f_inp.dispatchEvent(new Event('change', { bubbles: true }));
            f_inp.dispatchEvent(new Event('input', { bubbles: true }));
        }
        let f_alt = document.querySelector("input[name='user_fecha_servicio']");
        if (f_alt && f_alt !== f_inp) { f_alt.value = f_srv; }
    }""", [str(tipo_srv), str(fecha_srv)])

    # 5. Enviar formulario del servicio
    limpiar_overlays(page)
    page.evaluate("""() => {
        var form = document.getElementById('form');
        var user_f_id = document.getElementById('user_f_id') ? document.getElementById('user_f_id').value : '';
        var user_email = document.getElementById('user_correo_update') ? document.getElementById('user_correo_update').value : '';
        if (typeof window.jQuery !== 'undefined') {
            $.ajax({
                type: "POST",
                url: "./?action=services_users",
                data: { function: "get_repeated_email", id: user_f_id, email: user_email }
            }).always(function() {
                if (document.getElementById('cover-spin')) $('#cover-spin').show(0);
                if (form) form.submit();
            });
        } else if (form) {
            form.submit();
        }
    }""")

    page.wait_for_timeout(2000)
    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)

    # 6. Verificación en la tabla DOM de servicios
    page.goto(url_servicios, wait_until="domcontentloaded")
    esperar_desbloqueo_ajax(page)
    limpiar_overlays(page)

    nom_busc = str(persona.get('nombre', '')).strip().split()[0].lower() if persona.get('nombre') else ""
    ape_busc = str(persona.get('apellido', '')).strip().split()[0].lower() if persona.get('apellido') else ""
    uid_busc = str(user_f_id).strip()
    doc_busc = str(cedula_busc).strip().lower()

    verificado = page.evaluate("""([doc, uid, nom, ape]) => {
        var filas = document.querySelectorAll('table tbody tr, .card-content table tr');
        for (var i = 0; i < Math.min(filas.length, 15); i++) {
            var txt = (filas[i].innerText || '').toLowerCase();
            if (uid && uid.length >= 2 && txt.indexOf(uid.toLowerCase()) !== -1) return true;
            if (nom && ape && txt.indexOf(nom) !== -1 && txt.indexOf(ape) !== -1) return true;
            if (doc && doc.length >= 3 && txt.indexOf(doc) !== -1) return true;
        }
        return false;
    }""", [doc_busc, uid_busc, nom_busc, ape_busc])

    if verificado:
        return True, f"Servicio registrado y verificado en tabla (ID: {user_f_id})"
    else:
        capturar_pantalla_error(page, str(cedula_busc))
        return False, f"El servicio para la cédula {cedula_busc} no aparece en la tabla de InfoApp"


def ejecutar_carga_servicios_infoapp(
    personas: list,
    config: dict,
    config_servicio: dict,
    indice_inicio: int = 0,
    fn_guardar_checkpoint=None,
    log_callback=None,
    progreso_callback=None
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

    contexto_contenedor = {'pw': None, 'context': None, 'page': None}
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
            indice_inicio + 1, total, personas[indice_inicio],
            len(cargados_exitosos), len(fallidos), t_inicio, tipo_srv, fecha_srv, "Iniciando navegador y sesión..."
        )
        asegurar_sesion_activa(contexto_contenedor, config)
        _emitir_log(f"[OK] Sesión autenticada en InfoApp con usuario '{config.get('usuario', '')}'.")

        for i in range(indice_inicio, total):
            persona = personas[i]
            nom_comp = f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip() or f"Usuario C.I. {persona.get('cedula', '')}"
            doc_str = (
                persona.get('cedula')
                or (f"CE:{persona.get('cedula_escolar')}" if persona.get('cedula_escolar') else None)
                or f"Rep:{persona.get('cedula_padre', '')}"
            )

            renderizar_panel_servicios(
                i + 1, total, persona, len(cargados_exitosos), len(fallidos),
                t_inicio, tipo_srv, fecha_srv, "Procesando en InfoApp..."
            )
            _emitir_progreso(i + 1, total, f"Procesando: {nom_comp}")
            _emitir_log(f"[PROCESANDO] Servicio {i + 1}/{total}: {nom_comp} ({doc_str})...")

            cargado = False
            reintentos = 0

            while not cargado:
                try:
                    asegurar_sesion_activa(contexto_contenedor, config)
                    page = contexto_contenedor['page']

                    exito, detalle = registrar_servicio_persona(page, persona, config_servicio)

                    if exito:
                        renderizar_panel_servicios(
                            i + 1, total, persona, len(cargados_exitosos) + 1, len(fallidos),
                            t_inicio, tipo_srv, fecha_srv, f"[OK] {detalle}"
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
                            i + 1, total, persona, len(cargados_exitosos), len(fallidos) + 1,
                            t_inicio, tipo_srv, fecha_srv, f"[ERROR] {detalle}"
                        )
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "FALLIDO", detalle)
                        capturar_pantalla_error(page, doc_str)
                        _emitir_log(f"[ERROR] Incidencia con servicio de '{nom_comp}': {detalle}")

                        if config.get('modo_gui'):
                            accion = config.get('accion_defecto_incidencia', 'SKIP')
                            _emitir_log(f"[AVISO] Modo GUI: Omitiendo usuario '{nom_comp}'.")
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

                except Exception as ex:
                    capturar_pantalla_error(contexto_contenedor.get('page'), doc_str)
                    reintentos += 1
                    if reintentos > 3:
                        registrar_evento_log(config['archivo_log'], doc_str, nom_comp, "CRITICO", str(ex))
                        fallidos.append({'participante': persona, 'estado': 'FALLIDO', 'detalle': str(ex)})
                        if fn_guardar_checkpoint:
                            fn_guardar_checkpoint(config, config_servicio, personas, i + 1)
                        cargado = True
                    else:
                        contexto_contenedor['page'] = None

    finally:
        for key in ('context', 'pw'):
            try:
                if contexto_contenedor.get(key):
                    contexto_contenedor[key].close() if key == 'context' else contexto_contenedor[key].stop()
            except Exception:
                pass

    return cargados_exitosos, fallidos, time.time() - t_inicio


# =============================================================================
# CLASE ADAPTADOR (compatibilidad con código que la importa)
# =============================================================================

class AdaptadorWebHibrido:
    """
    Adaptador Playwright unificado.
    Mantiene la interfaz pública del antiguo adaptador híbrido.
    """
    def __init__(self, motor: str = "playwright", user_data_dir: str = None, headless: bool = False):
        self.motor_activo = "playwright"
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.pw = None
        self.context = None
        self.page = None

    def iniciar(self):
        cfg_browser = cm.obtener_browser_cfg()
        nav = cfg_browser["priority"][0] if cfg_browser["priority"] else "chromium"
        self.pw, self.context = obtener_contexto_playwright(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            navegador=nav
        )
        self.page = self.context.new_page()
        return self

    def registrar_alumno(self, alumno: dict, config: dict) -> tuple:
        return registrar_alumno_playwright(self.page, alumno, config)

    def cerrar(self):
        for obj, method in [(self.context, 'close'), (self.pw, 'stop')]:
            try:
                if obj:
                    getattr(obj, method)()
            except Exception:
                pass
