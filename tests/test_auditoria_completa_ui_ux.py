#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SUITE DE AUDITORIA COMPLETA UI/UX -- JsBOT v4.4.0
===============================================================================
Pruebas REALES de GUI: ventana real abierta, botones pulsados con .invoke(),
widgets auditados via winfo_children(), efectos verificados en variables y logs.

Subagentes:
  1. Inspector  - catalogo recursivo de widgets via winfo_children()
  2. Operador   - estimulos reales sobre cada widget interactivo
  3. Oraculo    - certifica mutaciones reales en el estado del sistema
  4. Auditor UX - metricas Fitts, Hick, Doherty, Nielsen cronometradas
  + Resiliencia - infraestructura de checkpoints ante apagones

Ejecucion:
  py -m pytest tests/test_auditoria_completa_ui_ux.py -v

Compatibilidad:
  - Windows (sin DISPLAY)
  - Canaima/Linux: LIBGL_ALWAYS_SOFTWARE=1 forzado si no hay GPU

ARQUITECTURA: singleton de GUI a nivel de modulo.
  Python 3.14 destruye el interprete Tcl al hacer app.destroy(); no se puede
  crear un segundo Tk() en el mismo proceso.  Por eso se crea UNA SOLA instancia
  al inicio del modulo y se comparte entre todas las clases de test.
===============================================================================
"""

import os
import sys
import time
import json
import queue
import threading
import unittest
import configparser
from datetime import datetime

# -- Compatibilidad Linux headless
if sys.platform.startswith("linux"):
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"

# -- Raiz del proyecto en path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.interfaz_grafica import JsBotGUI, AppGUI


# ===========================================================================
# SINGLETON DE GUI A NIVEL DE MODULO
# ===========================================================================
#
# Se crea UNA SOLA vez para todos los tests de este archivo.
# Python 3.14 no permite reinstanciar Tk() una vez que se llamo .destroy()
# en el mismo proceso (el interprete Tcl se desmonta y no se recarga).
#
_t0_arranque = time.monotonic()
_APP = JsBotGUI()
_APP.withdraw()
_APP.update_idletasks()
_ARRANQUE_S = time.monotonic() - _t0_arranque


# ===========================================================================
# HELPERS COMPARTIDOS
# ===========================================================================

def _flush(app, ms=80):
    deadline = time.monotonic() + ms / 1000.0
    while time.monotonic() < deadline:
        try:
            app.update_idletasks()
        except Exception:
            break


def _log_content(app):
    try:
        return app.textbox_logs.get("0.0", "end")
    except Exception:
        return ""


def _collect_all_widgets(widget, result=None):
    """Subagente 1 - Inspector: catalogo recursivo via winfo_children()."""
    if result is None:
        result = []
    try:
        children = widget.winfo_children()
    except Exception:
        return result
    for child in children:
        result.append(child)
        _collect_all_widgets(child, result)
    return result


# ===========================================================================
# CLASE BASE: APUNTA AL SINGLETON; NUNCA CREA NI DESTRUYE LA VENTANA
# ===========================================================================

class _GuiTestBase(unittest.TestCase):
    """Clase base que expone el singleton como self.app."""
    app = _APP
    _arranque_s = _ARRANQUE_S

    def setUp(self):
        for w in list(self.app.winfo_children()):
            if w.__class__.__name__ == "CTkToplevel":
                try:
                    w.destroy()
                except Exception:
                    pass
        try:
            self.app.update_idletasks()
        except Exception:
            pass


# ===========================================================================
# SUBAGENTE 1 -- INSPECTOR
# ===========================================================================

class TestInspectorWidgets(_GuiTestBase):

    def test_01_sidebar_navigation_buttons(self):
        expected = {"Diagnostico", "Credenciales", "Formacion", "Servicios",
                    "Planillas", "Reportes", "Creditos", "Ajustes"}
        actual = set(self.app.nav_buttons.keys())
        self.assertTrue(expected.issubset(actual),
                        f"Botones faltantes: {expected - actual}")

    def test_02_todas_las_vistas_registradas(self):
        vistas_req = {"Diagnostico", "Credenciales", "Formacion", "Servicios",
                      "Planillas", "Reportes", "Creditos", "Ajustes"}
        actual = set(self.app.vistas.keys())
        self.assertTrue(vistas_req.issubset(actual),
                        f"Vistas faltantes: {vistas_req - actual}")

    def test_03_botones_accion_principales(self):
        botones = [
            "btn_recomprobar", "btn_examinar_formacion", "btn_descartar_formacion",
            "btn_pegar_formacion", "btn_iniciar_formacion", "btn_iniciar_servicios",
            "btn_descartar_servicios", "btn_tabla_formacion", "btn_tabla_servicios",
            "btn_guardar_credenciales", "btn_toggle_ver_clave",
            "btn_iniciar_auditoria", "btn_abrir_reporte_auditoria",
            "btn_guardar_ajustes", "btn_restaurar_ajustes",
            "btn_copiar_logs", "btn_limpiar_logs",
        ]
        for nombre in botones:
            with self.subTest(boton=nombre):
                self.assertTrue(hasattr(self.app, nombre),
                                f"Boton critico ausente: {nombre}")

    def test_04_entries_existen(self):
        entries = [
            "entry_cred_usuario", "entry_cred_clave",
            "entry_url_formacion", "entry_url_servicios",
            "entry_aud_uid", "entry_aud_infoid",
            "entry_aud_desde", "entry_aud_hasta",
        ]
        for e in entries:
            with self.subTest(entry=e):
                self.assertTrue(hasattr(self.app, e), f"Entry ausente: {e}")

    def test_05_variables_tkinter(self):
        import tkinter as tk
        vars_esperadas = [
            ("var_modo_auditoria", tk.StringVar),
            ("var_criterio_uid", tk.StringVar),
            ("var_rol_auditor", tk.BooleanVar),
            ("var_modo_turbo", tk.BooleanVar),
            ("var_modo_visible_formacion", tk.BooleanVar),
            ("var_generar_ods_formacion", tk.BooleanVar),
            ("var_modo_visible_servicios", tk.BooleanVar),
            ("var_registro_tramite_servicios", tk.BooleanVar),
            ("var_login_timeout", tk.IntVar),
            ("var_ajax_timeout", tk.IntVar),
            ("var_element_timeout", tk.IntVar),
            ("var_browser_pref", tk.StringVar),
            ("var_start_maximized", tk.BooleanVar),
            ("var_capture_screenshots", tk.BooleanVar),
            ("var_detailed_logs", tk.BooleanVar),
            ("var_default_phone", tk.StringVar),
        ]
        for nombre, tipo in vars_esperadas:
            with self.subTest(var=nombre):
                self.assertTrue(hasattr(self.app, nombre), f"Var Tkinter ausente: {nombre}")
                self.assertIsInstance(getattr(self.app, nombre), tipo)

    def test_06_textbox_y_progreso(self):
        self.assertTrue(hasattr(self.app, "textbox_logs"))
        self.assertTrue(hasattr(self.app, "progreso"))
        self.assertTrue(hasattr(self.app, "lbl_porcentaje"))
        self.assertIsInstance(_log_content(self.app), str)

    def test_07_kpis_auditoria(self):
        kpis = [
            "lbl_kpi_actividades", "lbl_kpi_actividades_det",
            "lbl_kpi_formados", "lbl_kpi_formados_det",
            "lbl_kpi_servicios", "lbl_kpi_servicios_det",
            "lbl_kpi_cuadre", "lbl_kpi_cuadre_det",
        ]
        for k in kpis:
            with self.subTest(kpi=k):
                self.assertTrue(hasattr(self.app, k), f"KPI label ausente: {k}")

    def test_08_recursivo_mas_de_100_widgets(self):
        todos = _collect_all_widgets(self.app)
        self.assertGreater(len(todos), 100,
                           f"Se esperaban >100 widgets; encontrados: {len(todos)}")

    def test_09_cola_eventos_funcional(self):
        self.assertTrue(hasattr(self.app, "cola_eventos"))
        self.assertIsInstance(self.app.cola_eventos, queue.Queue)

    def test_10_status_card_sidebar(self):
        self.assertTrue(hasattr(self.app, "lbl_status"))
        self.assertIn("Sistema", self.app.lbl_status.cget("text"))

    def test_11_switches_auditoria_existen(self):
        self.assertTrue(hasattr(self.app, "switch_modo_turbo"))
        self.assertTrue(hasattr(self.app, "switch_rol_auditor"))
        self.assertTrue(hasattr(self.app, "tabview_auditoria"))

    def test_12_botones_inspeccion_auditoria(self):
        botones = ["btn_ver_actividades", "btn_ver_servicios",
                   "btn_ver_facilitadores", "combo_aud_formato",
                   "btn_exportar_reporte_dialogo"]
        for b in botones:
            with self.subTest(boton=b):
                self.assertTrue(hasattr(self.app, b), f"Widget auditoria ausente: {b}")

    def test_13_prevuelo_labels_formacion(self):
        for lbl in ["lbl_prevuelo_formacion_total", "lbl_prevuelo_formacion_estado",
                    "lbl_prevuelo_formacion_desglose"]:
            with self.subTest(label=lbl):
                self.assertTrue(hasattr(self.app, lbl))

    def test_14_prevuelo_labels_servicios(self):
        for lbl in ["lbl_prevuelo_servicios_total", "lbl_prevuelo_servicios_estado",
                    "lbl_prevuelo_servicios_desglose"]:
            with self.subTest(label=lbl):
                self.assertTrue(hasattr(self.app, lbl))

    def test_15_alias_appgui(self):
        self.assertIs(AppGUI, JsBotGUI)


# ===========================================================================
# SUBAGENTE 2 -- OPERADOR
# ===========================================================================

class TestOperadorEstimulos(_GuiTestBase):

    def test_21_nav_diagnostico(self):
        self.app.seccion_actual = "Formacion"
        self.app.nav_buttons["Diagnostico"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Diagnostico")

    def test_22_nav_credenciales(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Credenciales"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Credenciales")

    def test_23_nav_formacion(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Formacion"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Formacion")

    def test_24_nav_servicios(self):
        self.app.seccion_actual = "Formacion"
        self.app.nav_buttons["Servicios"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Servicios")

    def test_25_nav_planillas(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Planillas"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Planillas")

    def test_26_nav_reportes(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Reportes"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Reportes")

    def test_27_nav_ajustes(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Ajustes"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Ajustes")

    def test_28_nav_creditos(self):
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Creditos"].invoke()
        _flush(self.app, 150)
        self.assertEqual(self.app.seccion_actual, "Creditos")

    def test_29_toggle_clave_alterna_show(self):
        self.app.entry_cred_clave.configure(show="*")
        self.app.btn_toggle_ver_clave.invoke()
        _flush(self.app, 80)
        self.assertEqual(self.app.entry_cred_clave.cget("show"), "")
        self.app.btn_toggle_ver_clave.invoke()
        _flush(self.app, 80)
        self.assertEqual(self.app.entry_cred_clave.cget("show"), "*")

    def test_30_limpiar_logs(self):
        self.app._agregar_log("[TEST] Linea de prueba.")
        _flush(self.app, 80)
        self.app.btn_limpiar_logs.invoke()
        _flush(self.app, 80)
        self.assertIn("vaciado", _log_content(self.app).lower())

    def test_31_copiar_logs_no_lanza_excepcion(self):
        self.app._agregar_log("[TEST] Texto para copiar.")
        _flush(self.app, 80)
        try:
            self.app.btn_copiar_logs.invoke()
            _flush(self.app, 80)
        except Exception as e:
            self.fail(f"btn_copiar_logs lanzo excepcion: {e}")

    def test_32_entry_url_formacion(self):
        url = "https://infoapp2.infocentro.gob.ve/?r=activity/create&id_activity=12345"
        self.app.entry_url_formacion.delete(0, "end")
        self.app.entry_url_formacion.insert(0, url)
        _flush(self.app, 80)
        self.assertEqual(self.app.entry_url_formacion.get(), url)

    def test_33_entry_url_servicios(self):
        url = "https://infoapp2.infocentro.gob.ve/?r=service/create&id_service=9999"
        self.app.entry_url_servicios.delete(0, "end")
        self.app.entry_url_servicios.insert(0, url)
        _flush(self.app, 80)
        self.assertEqual(self.app.entry_url_servicios.get(), url)

    def test_34_entry_cred_usuario_refleja_variable(self):
        self.app.entry_cred_usuario.delete(0, "end")
        self.app.entry_cred_usuario.insert(0, "facilitador_test")
        _flush(self.app, 80)
        self.assertEqual(self.app.var_cred_usuario.get(), "facilitador_test")

    def test_35_modo_auditoria_uid(self):
        self.app.var_modo_auditoria.set("Por Facilitador (UID)")
        self.app._al_cambiar_modo_auditoria()
        _flush(self.app, 100)
        self.assertTrue(bool(self.app.box_aud_uid.grid_info()))
        self.assertFalse(bool(self.app.box_aud_infoid.grid_info()))

    def test_36_modo_auditoria_infocentro(self):
        self.app.var_modo_auditoria.set("Por Infocentro (Codigo)")
        self.app._al_cambiar_modo_auditoria()
        _flush(self.app, 100)
        self.assertFalse(bool(self.app.box_aud_uid.grid_info()))
        self.assertTrue(bool(self.app.box_aud_infoid.grid_info()))

    def test_37_modo_auditoria_estadal(self):
        self.app.var_modo_auditoria.set("Resumen Estadal (Region)")
        self.app._al_cambiar_modo_auditoria()
        _flush(self.app, 100)
        self.assertFalse(bool(self.app.box_aud_uid.grid_info()))
        self.assertTrue(bool(self.app.box_aud_estado.grid_info()))

    def test_38_descartar_formacion(self):
        self.app.archivo_seleccionado_formacion.set("test.xlsx")
        self.app.participantes_cargados = [{"cedula": "1"}]
        self.app._descartar_archivo_formacion()
        _flush(self.app, 100)
        texto = self.app.archivo_seleccionado_formacion.get()
        self.assertIn("Ning", texto)

    def test_39_descartar_servicios(self):
        self.app.archivo_seleccionado_servicios.set("usuarios.csv")
        self.app._descartar_archivo_servicios()
        _flush(self.app, 100)
        self.assertIn("Ning", self.app.archivo_seleccionado_servicios.get())

    def test_40_poblar_tabs_vacias_sin_error(self):
        try:
            self.app._poblar_tab_actividades([])
            self.app._poblar_tab_servicios([])
            self.app._poblar_tab_facilitadores({})
        except Exception as e:
            self.fail(f"Poblar tabs vacias lanzo: {e}")


# ===========================================================================
# SUBAGENTE 3 -- ORACULO
# ===========================================================================

class TestOraculoEstadoBackend(_GuiTestBase):

    def test_41_log_registra_navegacion(self):
        self.app.btn_limpiar_logs.invoke()
        _flush(self.app, 80)
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Credenciales"].invoke()
        _flush(self.app, 150)
        self.assertIn("Credenciales", _log_content(self.app))

    def test_42_guardar_credenciales_escribe_config(self):
        config_path = os.path.join(BASE_DIR, "config", "config.ini")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        contenido_previo = None
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                contenido_previo = f.read()
        try:
            usuario_test = f"test_user_{int(time.time())}"
            self.app.entry_cred_usuario.delete(0, "end")
            self.app.entry_cred_usuario.insert(0, usuario_test)
            self.app.entry_cred_clave.delete(0, "end")
            self.app.entry_cred_clave.insert(0, "clave_test_1234")
            _flush(self.app, 80)
            self.app.btn_guardar_credenciales.invoke()
            _flush(self.app, 200)
            self.assertTrue(os.path.exists(config_path))
            cfg = configparser.ConfigParser()
            cfg.read(config_path, encoding="utf-8")
            encontrado = any(
                cfg.has_section(s) and cfg.get(s, "usuario", fallback="") == usuario_test
                for s in ("LOGIN", "CREDENCIALES")
            )
            self.assertTrue(encontrado, f"Usuario '{usuario_test}' no en config.ini")
        finally:
            if contenido_previo is not None:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(contenido_previo)

    def test_43_limpiar_logs_muta_textbox(self):
        self.app._agregar_log("[ORACULO] Linea de referencia.")
        _flush(self.app, 80)
        antes = _log_content(self.app)
        self.app.btn_limpiar_logs.invoke()
        _flush(self.app, 100)
        self.assertNotEqual(antes, _log_content(self.app))

    def test_44_seccion_actual_muta_al_navegar(self):
        for boton, esperado in [("Planillas", "Planillas"), ("Ajustes", "Ajustes")]:
            with self.subTest(seccion=boton):
                self.app.seccion_actual = "Credenciales"
                self.app.nav_buttons[boton].invoke()
                _flush(self.app, 150)
                self.assertEqual(self.app.seccion_actual, esperado)

    def test_45_prevuelo_formacion_actualiza_labels(self):
        self.app.participantes_cargados = [
            {"nombre": "Ana", "cedula": "10000001", "cedulado": "si"},
            {"nombre": "Luis", "cedula": "20000002", "cedulado": "si"},
            {"nombre": "Nino", "cedulado": "sin_documento"},
        ]
        self.app._actualizar_prevuelo_tras_resolucion(seccion="Formacion")
        _flush(self.app, 80)
        self.assertIn("3", self.app.lbl_prevuelo_formacion_total.cget("text"))

    def test_46_prevuelo_servicios_actualiza_labels(self):
        self.app.participantes_cargados = [
            {"nombre": "Pedro", "cedula": "30000003", "cedulado": "si"},
        ]
        self.app._actualizar_prevuelo_tras_resolucion(seccion="Servicios")
        _flush(self.app, 80)
        self.assertIn("1", self.app.lbl_prevuelo_servicios_total.cget("text"))

    def test_47_restaurar_ajustes_resetea_variables(self):
        self.app.var_login_timeout.set(5)
        self.app.var_ajax_timeout.set(5)
        self.app.var_element_timeout.set(5)
        _flush(self.app, 80)
        self.app.btn_restaurar_ajustes.invoke()
        _flush(self.app, 200)
        self.assertEqual(self.app.var_login_timeout.get(), 15)
        self.assertEqual(self.app.var_ajax_timeout.get(), 15)
        self.assertEqual(self.app.var_element_timeout.get(), 12)

    def test_48_guardar_ajustes_persiste_settings(self):
        settings_path = os.path.join(BASE_DIR, "config", "settings.json")
        self.app.var_login_timeout.set(20)
        self.app.var_ajax_timeout.set(18)
        _flush(self.app, 80)
        self.app.btn_guardar_ajustes.invoke()
        _flush(self.app, 200)
        if os.path.exists(settings_path):
            with open(settings_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("timeouts", {}).get("login_wait_seconds"), 20)
        else:
            self.assertEqual(self.app.defaults_ajustes["login"], 20)

    def test_49_finalizar_auditoria_kpis(self):
        resultado_mock = {
            "exito": True, "total_actividades": 3, "total_procesadas": 3,
            "formaciones": [
                {"id": "1", "participantes": 25, "dimensiones": "IA", "info_id": "NR"},
                {"id": "2", "participantes": 30, "dimensiones": "Web", "info_id": "NR"},
                {"id": "3", "participantes": 15, "dimensiones": "RPA", "info_id": "NR"},
            ],
            "productos": [], "otras_actividades": [], "total_estudiantes": 70,
            "total_servicios": 1,
            "servicios": [{"servicio": "Tramite", "cedula": "12345678"}],
            "conteo_servicios": {"Tramite": 1},
            "cedulados_serv": 1, "no_cedulados_serv": 0, "cuadre_perfecto": True,
        }
        self.app._finalizar_ejecucion_auditoria(resultado_mock)
        _flush(self.app, 150)
        self.assertIn("3", self.app.lbl_kpi_actividades.cget("text"))
        self.assertIn("Cuadrado", self.app.lbl_kpi_cuadre.cget("text"))

    def test_50_reanudacion_preserva_indice(self):
        estado = {
            "participantes": [
                {"nombre": "P1", "cedula": "11111111"},
                {"nombre": "P2", "cedula": "22222222"},
                {"nombre": "P3", "cedula": "33333333"},
                {"nombre": "P4", "cedula": "44444444"},
            ],
            "indice_ultimo_procesado": 3,
            "url": "https://infoapp2.infocentro.gob.ve/?id_activity=777",
        }
        self.app._reanudar_flujo_desde_estado(estado, tipo="formacion")
        _flush(self.app, 100)
        self.assertEqual(getattr(self.app, "indice_inicio_recuperacion_formacion", -1), 3)
        self.assertEqual(len(self.app.participantes_cargados), 4)


# ===========================================================================
# SUBAGENTE 4 -- AUDITOR UX (METRICAS HCI)
# ===========================================================================

class TestAuditorUXMetricasHCI(_GuiTestBase):

    def test_51_doherty_arranque_menos_2500ms(self):
        self.assertLess(self._arranque_s, 2.5,
                        f"Arranque supera Doherty: {self._arranque_s:.3f}s")

    def test_52_doherty_cambio_seccion_menos_100ms(self):
        secciones = ["Credenciales", "Formacion", "Servicios", "Reportes", "Ajustes", "Diagnostico"]
        for s in secciones:
            self.app.seccion_actual = "FORZADO"
            t0 = time.monotonic()
            self.app._cambiar_seccion(s)
            self.app.update_idletasks()
            ms = (time.monotonic() - t0) * 1000
            with self.subTest(seccion=s):
                self.assertLess(ms, 100, f"{s}: {ms:.1f}ms (limite Doherty: 100ms)")
            _flush(self.app, 30)

    def test_53_fitts_botones_criticos_height_38px(self):
        for nombre in ("btn_iniciar_formacion", "btn_iniciar_servicios"):
            with self.subTest(boton=nombre):
                btn = getattr(self.app, nombre)
                try:
                    self.app.update_idletasks()
                    alto = btn.winfo_height()
                    if alto < 10:
                        alto = btn.cget("height")
                except Exception:
                    alto = btn.cget("height")
                self.assertGreaterEqual(int(alto), 38,
                                        f"{nombre}: height={alto}px (minimo Fitts: 38px)")

    def test_54_fitts_botones_nav_sidebar_38px(self):
        for nombre, btn in self.app.nav_buttons.items():
            with self.subTest(boton=nombre):
                self.assertGreaterEqual(int(btn.cget("height")), 38,
                                        f"Nav {nombre}: height < 38px")

    def test_55_hick_sidebar_max_8_secciones(self):
        n = len(self.app.nav_buttons)
        self.assertLessEqual(n, 8, f"Sidebar tiene {n} botones (limite Hick: 8)")

    def test_56_nielsen_h1_feedback_en_log(self):
        self.app.btn_limpiar_logs.invoke()
        _flush(self.app, 100)
        self.app.seccion_actual = "Diagnostico"
        self.app.nav_buttons["Formacion"].invoke()
        _flush(self.app, 150)
        self.assertTrue(len(_log_content(self.app).strip()) > 0,
                        "No hay feedback de log tras navegacion (Nielsen H1)")

    def test_57_nielsen_h4_banner_solo_con_cambios(self):
        # Restaurar primero para garantir estado limpio
        self.app.btn_restaurar_ajustes.invoke()
        # Procesar callbacks after() pendientes de la animacion de cierre
        for _ in range(10):
            self.app.update()
        self.assertFalse(self.app.banner_advertencia.winfo_ismapped(),
                         "Banner visible sin cambios (violacion Nielsen H4)")

        # Modificar y verificar que el banner se muestra
        self.app.var_login_timeout.set(5)
        self.app._al_modificar_parametro()
        # update() procesa los callbacks after(40ms) de la animacion
        for _ in range(15):
            self.app.update()
        # Verificar via grid_info (no depende de visibilidad de pantalla)
        banner_en_grid = bool(self.app.banner_advertencia.grid_info())
        self.assertTrue(banner_en_grid,
                        "Banner no aparece en grid tras modificar parametro (violacion Nielsen H4)")

        # Restaurar estado para no contaminar tests siguientes
        self.app.btn_restaurar_ajustes.invoke()
        for _ in range(10):
            self.app.update()


    def test_58_nielsen_h4_modo_auditoria_valores(self):
        opciones = [
            "Por Facilitador (UID)",
            "Por Infocentro (Codigo)",
            "Resumen Estadal (Region)",
        ]
        for op in opciones:
            self.app.var_modo_auditoria.set(op)
            _flush(self.app, 50)
            self.assertEqual(self.app.var_modo_auditoria.get(), op)

    def test_59_nielsen_h6_switch_rol_texto_descriptivo(self):
        texto = self.app.switch_rol_auditor.cget("text")
        self.assertGreater(len(texto), 3,
                           f"Texto de switch_rol_auditor muy corto: {texto!r}")

    def test_60_nielsen_h4_telemetria_alias_unificado(self):
        self.assertIs(self.app.txt_telemetria_auditoria, self.app.textbox_logs,
                      "txt_telemetria_auditoria y textbox_logs son objetos distintos")


# ===========================================================================
# RESILIENCIA ANTE APAGONES
# ===========================================================================

class TestResilienciaApagones(_GuiTestBase):

    def test_61_metodos_de_rescate_existen(self):
        metodos = [
            "comprobar_sesion_interrumpida_gui",
            "_mostrar_modal_recuperacion",
            "_reanudar_flujo_desde_estado",
            "_mostrar_modal_resolucion_huerfanos",
            "_actualizar_prevuelo_tras_resolucion",
        ]
        for m in metodos:
            with self.subTest(metodo=m):
                self.assertTrue(
                    hasattr(self.app, m) and callable(getattr(self.app, m)),
                    f"Metodo de rescate ausente: {m}"
                )

    def test_62_directorio_logs_existe(self):
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "logs")))

    def test_63_directorio_reportes_auditoria(self):
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "Reportes_Auditoria")))

    def test_64_cola_eventos_inter_hilos(self):
        resultado = []

        def _hilo():
            self.app.cola_eventos.put(("log", "[HILO] Mensaje de prueba."))
            resultado.append("ok")

        t = threading.Thread(target=_hilo, daemon=True)
        t.start()
        t.join(timeout=2.0)
        self.assertEqual(resultado, ["ok"])
        try:
            item = self.app.cola_eventos.get_nowait()
            self.assertEqual(item[0], "log")
            self.assertIn("HILO", item[1])
        except queue.Empty:
            self.fail("Mensaje del hilo no llego a la cola")

    def test_65_modal_recuperacion_sin_error(self):
        estado_sim = {
            "participantes": [{"nombre": "A", "cedula": "10000001"},
                              {"nombre": "B", "cedula": "20000002"}],
            "indice_ultimo_procesado": 1,
            "id_actividad": "TEST_999",
        }
        try:
            self.app._mostrar_modal_recuperacion(
                estado_sim, idx=1, total=2, tipo="formacion"
            )
            _flush(self.app, 200)
            modales = [w for w in self.app.winfo_children()
                       if w.__class__.__name__ == "CTkToplevel"]
            self.assertGreater(len(modales), 0)
            for m in modales:
                m.destroy()
        except Exception as e:
            self.fail(f"Modal de recuperacion lanzo excepcion: {e}")

    def test_66_agregar_log_desde_hilo(self):
        exc = []

        def _log():
            try:
                self.app._agregar_log("[HILO] Prueba de resiliencia.")
            except Exception as e:
                exc.append(str(e))

        t = threading.Thread(target=_log, daemon=True)
        t.start()
        t.join(timeout=2.0)
        self.assertEqual(exc, [])

    def test_67_directorio_config_existe(self):
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "config")))

    def test_68_directorio_planillas_existe(self):
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "Planillas")))

    def test_69_ejecutando_tarea_flag_inicialmente_falso(self):
        self.assertFalse(self.app.ejecutando_tarea)

    def test_70_seccion_actual_es_string_no_vacio(self):
        self.assertIsInstance(self.app.seccion_actual, str)
        self.assertGreater(len(self.app.seccion_actual), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
