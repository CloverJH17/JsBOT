#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SUITE DE PRUEBAS DEL MÓDULO INSPECTOR DE AUDITORÍA (v4.2.4)
===============================================================================
Pruebas unitarias aisladas para verificar:
1. Parsing ante tablas vacías y emisión del aviso correspondiente en GUI/telemetría.
2. Persistencia y lectura del caché JSON temporal (logs/ultima_busqueda_inspector.json).
3. Robustez de parámetros ante valores de UID y fechas nulas, incompletas o inválidas.
===============================================================================
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.auditor_reportes import (
    parsear_pagina_actividades_bs4,
    parsear_pagina_servicios_bs4,
    guardar_cache_inspector,
    cargar_cache_inspector,
    ejecutar_auditoria,
    exportar_reporte_auditoria,
    generar_resumen_consola,
    exportar_reporte_ods,
    exportar_reporte_pdf,
    CACHE_INSPECTOR_PATH
)
from modulos.interfaz_grafica import AppGUI


class TestInspectorSuite(unittest.TestCase):
    """Suite integral y aislada para el módulo de Inspección y Auditoría."""

    @classmethod
    def setUpClass(cls):
        """Inicializa una instancia única de AppGUI para pruebas de interfaz."""
        cls.app = AppGUI()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        """Destruye la instancia gráfica de prueba."""
        try:
            cls.app.destroy()
        except Exception:
            pass

    def setUp(self):
        """Limpia modales y restaura estados entre tests."""
        for w in self.app.winfo_children():
            if w.__class__.__name__ == "CTkToplevel":
                try:
                    w.destroy()
                except Exception:
                    pass
        try:
            self.app.update_idletasks()
        except Exception:
            pass

    # =========================================================================
    # 1. PARSING ANTE TABLAS VACÍAS Y GESTIÓN DE CERO RESULTADOS
    # =========================================================================

    def test_parsing_actividades_tabla_vacia(self):
        """Verifica que el parser de actividades maneje HTML vacío o sin filas sin fallar."""
        # HTML completamente vacío
        res1 = parsear_pagina_actividades_bs4("")
        self.assertEqual(res1, [])

        # HTML con tabla vacía o aviso de sin registros
        html_vacio = """
        <html>
            <body>
                <table class="table table-hover">
                    <thead><tr><th>Fecha</th><th>Dimensiones</th></tr></thead>
                    <tbody>
                        <tr><td colspan="5">No se encontraron actividades registradas.</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        res2 = parsear_pagina_actividades_bs4(html_vacio)
        self.assertEqual(res2, [])

    def test_parsing_servicios_tabla_vacia(self):
        """Verifica que el parser de servicios maneje HTML vacío o incompleto sin fallar."""
        # HTML vacío
        res1 = parsear_pagina_servicios_bs4("")
        self.assertEqual(res1, [])

        # HTML con filas insuficientes (< 10 columnas requeridas para servicios)
        html_incompleto = """
        <html>
            <body>
                <table class="table-bordered">
                    <tbody>
                        <tr><td>UID</td><td>Fecha</td><td>Sin Datos</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        res2 = parsear_pagina_servicios_bs4(html_incompleto)
        self.assertEqual(res2, [])

    def test_aviso_cero_resultados_en_gui_y_telemetria(self):
        """
        Verifica que al recibir 0 actividades y 0 servicios:
        1. Las KPIs se reseteen a '0'.
        2. El KPI de cuadre muestre '● Sin Registros'.
        3. Se registre en telemetría el aviso exacto:
           '[AVISO] No se encontraron actividades o usuarios en el rango seleccionado.'
        """
        resultado_vacio = {
            "exito": True,
            "criterio_tipo": "uid",
            "criterio_valor": "99999",
            "f_ini": "2026-08-01",
            "f_fin": "2026-08-31",
            "facilitador_principal": "Criterio UID: 99999",
            "total_actividades": 0,
            "total_procesadas": 0,
            "formaciones": [],
            "productos": [],
            "otras_actividades": [],
            "total_estudiantes": 0,
            "total_servicios": 0,
            "servicios": [],
            "conteo_servicios": {},
            "cedulados_serv": 0,
            "no_cedulados_serv": 0,
            "resumen_facilitadores": {},
            "cuadre_perfecto": True,
            "archivo_exportado": ""
        }

        self.app._finalizar_ejecucion_auditoria(resultado_vacio)

        # 1. Verificación de KPIs
        self.assertEqual(self.app.lbl_kpi_actividades.cget("text"), "0")
        self.assertEqual(self.app.lbl_kpi_formados.cget("text"), "0")
        self.assertEqual(self.app.lbl_kpi_servicios.cget("text"), "0")
        self.assertEqual(self.app.lbl_kpi_cuadre.cget("text"), "● Sin Registros")

        # 2. Verificación de aviso en telemetría y estado
        texto_telemetria = self.app.textbox_logs.get("0.0", "end")
        self.assertIn("[AVISO] No se encontraron actividades o usuarios en el rango seleccionado.", texto_telemetria)
        texto_estado = self.app.lbl_auditoria_estado.cget("text")
        self.assertIn("[AVISO] No se encontraron actividades o usuarios en el rango seleccionado.", texto_estado)

        # 3. Botón de abrir reporte deshabilitado
        self.assertEqual(self.app.btn_abrir_reporte_auditoria.cget("state"), "disabled")

    # =========================================================================
    # 2. PERSISTENCIA Y LECTURA DEL CACHÉ JSON TEMPORAL
    # =========================================================================

    def test_persistencia_y_lectura_cache_json(self):
        """Verifica que guardar_cache_inspector y cargar_cache_inspector preserven la estructura completa."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ruta_cache_tmp = os.path.join(tmp_dir, "test_cache.json")

            datos_prueba = {
                "exito": True,
                "criterio_tipo": "uid",
                "criterio_valor": "1325",
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-08-31",
                "facilitador_principal": "Facilitador Test",
                "total_actividades": 3,
                "total_procesadas": 3,
                "formaciones": [
                    {"id": "101", "titulo": "Taller Scratch", "participantes": 15, "dimensiones": "TIC % Robótica"}
                ],
                "productos": [
                    {"id": "102", "titulo": "Infografía Digital", "productos": 2, "dimensiones": "Medios Digitales"}
                ],
                "otras_actividades": [
                    {"id": "103", "titulo": "Mantenimiento Preventivo", "productos": 0, "dimensiones": "Comunidad"}
                ],
                "total_estudiantes": 15,
                "total_servicios": 1,
                "servicios": [
                    {"uid": "1325", "servicio": "Trámite Carnet", "cedula": "12345678", "usuario": "Juan Pérez"}
                ],
                "conteo_servicios": Counter({"Trámite Carnet": 1}),
                "cedulados_serv": 1,
                "no_cedulados_serv": 0,
                "resumen_facilitadores": {
                    "1325": {"nombre": "Facilitador Test", "formaciones": 1, "estudiantes": 15, "total_act": 3, "servicios": 1}
                },
                "cuadre_perfecto": True,
                "archivo_exportado": "Reportes_Auditoria/test.xlsx"
            }

            # Guardar
            guardado = guardar_cache_inspector(datos_prueba, ruta_archivo=ruta_cache_tmp)
            self.assertTrue(os.path.exists(guardado))

            # Validar sintaxis JSON en disco
            with open(guardado, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
            self.assertEqual(raw_json["total_actividades"], 3)
            self.assertEqual(raw_json["conteo_servicios"], {"Trámite Carnet": 1})

            # Cargar mediante función oficial
            cargado = cargar_cache_inspector(ruta_archivo=ruta_cache_tmp)
            self.assertTrue(cargado.get("exito"))
            self.assertEqual(cargado.get("total_actividades"), 3)
            self.assertEqual(cargado.get("total_estudiantes"), 15)
            self.assertEqual(len(cargado.get("formaciones")), 1)
            self.assertEqual(len(cargado.get("servicios")), 1)
            self.assertEqual(cargado.get("criterio_valor"), "1325")

    def test_cargar_cache_inexistente_o_corrupto(self):
        """Verifica que el cargador de caché retorne diccionario vacío ante fallos sin explotar."""
        # Archivo que no existe
        res1 = cargar_cache_inspector("/ruta/totalmente/falsa/inexistente.json")
        self.assertEqual(res1, {})

        # Archivo corrupto (no JSON)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp:
            tmp.write("{json roto sin cerrar: 123,")
            ruta_rota = tmp.name

        try:
            res2 = cargar_cache_inspector(ruta_rota)
            self.assertEqual(res2, {})
        finally:
            if os.path.exists(ruta_rota):
                os.remove(ruta_rota)

    def test_gui_cargar_ultima_busqueda_cache(self):
        """Verifica la carga interactiva desde la GUI mediante _cargar_ultima_busqueda_cache."""
        with patch("modulos.auditor_reportes.cargar_cache_inspector") as mock_cargar:
            # Caso sin caché
            mock_cargar.return_value = {}
            exito_falso = self.app._cargar_ultima_busqueda_cache()
            self.assertFalse(exito_falso)

            # Caso con caché válido
            mock_cargar.return_value = {
                "exito": True,
                "criterio_tipo": "uid",
                "criterio_valor": "1325",
                "total_actividades": 2,
                "total_procesadas": 2,
                "formaciones": [{"id": "1", "participantes": 10, "dimensiones": "Robótica"}],
                "productos": [],
                "otras_actividades": [{"id": "2", "productos": 0, "dimensiones": "Comunidad"}],
                "total_estudiantes": 10,
                "total_servicios": 0,
                "servicios": [],
                "resumen_facilitadores": {},
                "cuadre_perfecto": True
            }
            exito_verdadero = self.app._cargar_ultima_busqueda_cache()
            self.assertTrue(exito_verdadero)
            self.assertEqual(self.app.lbl_kpi_actividades.cget("text"), "2")
            self.assertEqual(self.app.lbl_kpi_formados.cget("text"), "10")

    # =========================================================================
    # 3. ROBUSTEZ DE PARÁMETROS NULOS, INCOMPLETOS O INVÁLIDOS
    # =========================================================================

    def test_ejecutar_auditoria_parametros_nulos_o_incompletos(self):
        """Verifica que ejecutar_auditoria resuelva criterios y fechas por defecto si se pasan Nones."""
        with patch("modulos.auditor_reportes.cargar_credenciales_auditoria", return_value=("user_test", "pass_test")), \
             patch("modulos.auditor_reportes.iniciar_driver_auditoria") as mock_driver, \
             patch("modulos.auditor_reportes.autenticar_infoapp", return_value=True), \
             patch("modulos.auditor_reportes.consultar_actividades_infoapp", return_value=(0, [])), \
             patch("modulos.auditor_reportes.consultar_servicios_infoapp", return_value=(0, [])):

            mock_driver_instance = MagicMock()
            mock_driver_instance.get_cookies.return_value = []
            mock_driver.return_value = mock_driver_instance

            # Invocar con parámetros completamente nulos
            resultado = ejecutar_auditoria(
                uid=None,
                info_id=None,
                estado=None,
                start_at=None,
                finish_at=None,
                fecha_inicio=None,
                fecha_fin=None,
                exportar_formato="ninguno"
            )

            self.assertTrue(resultado.get("exito"))
            self.assertEqual(resultado.get("criterio_tipo"), "uid")
            self.assertEqual(resultado.get("criterio_valor"), "1325")
            self.assertTrue(len(resultado.get("f_ini")) > 0)
            self.assertTrue(len(resultado.get("f_fin")) > 0)
            self.assertEqual(resultado.get("total_actividades"), 0)
            self.assertEqual(resultado.get("total_servicios"), 0)

    def test_gui_validacion_fechas_invalidas_bloquea_ejecucion(self):
        """Verifica que fechas con formato inválido muestren aviso y aborten sin ejecutar hilo."""
        self.app.ejecutando_auditoria = False
        self.app.var_fecha_desde_aud.set("2026/09/01")  # Slash en lugar de guion
        self.app.var_fecha_hasta_aud.set("2026-09-30")

        with patch.object(self.app, "_mostrar_modal_mensaje") as mock_modal:
            self.app._iniciar_auditoria_thread()
            self.assertFalse(self.app.ejecutando_auditoria)
            mock_modal.assert_called_once()
            args, kwargs = mock_modal.call_args
            self.assertIn("Error en Fechas", args)

        # Restaurar fechas válidas
        self.app.var_fecha_desde_aud.set("2026-08-01")
        self.app.var_fecha_hasta_aud.set("2026-08-31")

    def test_gui_validacion_uid_vacio_en_modo_uid(self):
        """Verifica que en modo UID no se permita iniciar si el UID está en blanco."""
        self.app.ejecutando_auditoria = False
        self.app.var_modo_auditoria.set("Por Facilitador (UID)")
        self.app.var_criterio_uid.set("   ")  # Solo espacios en blanco

        with patch.object(self.app, "_mostrar_modal_mensaje") as mock_modal:
            self.app._iniciar_auditoria_thread()
            self.assertFalse(self.app.ejecutando_auditoria)
            mock_modal.assert_called_once()
            args, kwargs = mock_modal.call_args
            self.assertIn("Falta UID", args)

        # Restaurar
        self.app.var_criterio_uid.set("1325")

    def test_gui_modal_confirmacion_limpio_sin_bloqueo(self):
        """Verifica que _mostrar_modal_confirmacion cree un CTkToplevel interactivo sin tocar stdin."""
        callback_llamado = [False]

        def mi_callback():
            callback_llamado[0] = True

        self.app._mostrar_modal_confirmacion(
            titulo="Confirmar Operación",
            mensaje="¿Desea continuar con el proceso de inspección?",
            callback_si=mi_callback
        )

        # Buscar el modal creado en los hijos de la ventana
        modales = [w for w in self.app.winfo_children() if w.__class__.__name__ == "CTkToplevel"]
        self.assertTrue(len(modales) > 0)
        # Destruir modal para limpiar
        for m in modales:
            m.destroy()

    # =========================================================================
    # 4. DOM FALLBACK, MODO TURBO Y EXPORTACIÓN MULTIFORMATO (v4.2.5)
    # =========================================================================

    def test_parsing_actividades_dom_fallback(self):
        """Verifica que el parser extraiga datos desde celdas <td> cuando faltan etiquetas <p> ocultas."""
        html_sin_parrafos = """
        <html>
            <body>
                <table class="table table-hover">
                    <thead><tr><th>Fecha</th><th>Dimensiones</th><th>Infocentro</th><th>Facilitador</th><th>Part.</th><th>Prod.</th></tr></thead>
                    <tbody>
                        <tr id="row_991">
                            <td><span>2026-08-20</span></td>
                            <td>Comunidades de aprendizaje % Robótica Educativa % Taller De Scratch</td>
                            <td>NRYAR24</td>
                            <td>1325 - Jair Hernandez</td>
                            <td><a class="btn-info btn-sm">22</a></td>
                            <td><a class="btn-danger btn-sm">0</a></td>
                        </tr>
                        <tr id="row_992">
                            <td><span>2026-08-21</span></td>
                            <td>Mantenimiento Preventivo de Servidores</td>
                            <td>NRYAR01</td>
                            <td>Ana Lopez</td>
                            <td><span class="badge">10</span></td>
                            <td><span class="badge">1</span></td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        acts = parsear_pagina_actividades_bs4(html_sin_parrafos, default_info_id="DEF_INFO", default_uid="DEF_UID")
        self.assertEqual(len(acts), 2)

        # Fila 1
        a1 = acts[0]
        self.assertEqual(a1["fecha"], "2026-08-20")
        self.assertEqual(a1["participantes"], 22)
        self.assertEqual(a1["uid"], "1325")
        self.assertEqual(a1["responsable"], "Jair Hernandez")
        self.assertEqual(a1["info_id"], "NRYAR24")
        self.assertIn("Scratch", a1["taller"])
        self.assertEqual(a1["area"], "Robótica Educativa")

        # Fila 2 (sin UID explícito en texto, toma default_uid)
        a2 = acts[1]
        self.assertEqual(a2["fecha"], "2026-08-21")
        self.assertEqual(a2["info_id"], "NRYAR01")
        self.assertEqual(a2["responsable"], "Ana Lopez")
        self.assertEqual(a2["uid"], "DEF_UID")
        self.assertTrue(a2["id"].startswith("ACT_") or a2["id"] == "row_992")

    def test_exportar_reporte_multiformato(self):
        """Verifica la exportación en los 5 formatos: Excel, ODS, PDF, CSV y Consola."""
        mock_resultado = {
            "exito": True,
            "criterio_tipo": "uid",
            "criterio_valor": "1325",
            "f_ini": "2026-08-01",
            "f_fin": "2026-08-31",
            "facilitador_principal": "Jair Hernandez",
            "total_actividades": 2,
            "total_procesadas": 2,
            "formaciones": [
                {
                    "id": "1",
                    "fecha": "2026-08-10",
                    "titulo": "Robótica con Arduino",
                    "area": "Robótica Educativa",
                    "taller": "Arduino Básico",
                    "participantes": 15,
                    "productos": 0,
                    "responsable": "Jair Hernandez",
                    "uid": "1325",
                    "info_id": "NRYAR24",
                    "dimensiones": "Comunidades % Robótica % Arduino"
                }
            ],
            "productos": [],
            "otras_actividades": [
                {
                    "id": "2",
                    "fecha": "2026-08-12",
                    "titulo": "Reunión Comunitaria",
                    "area": "Comunidad",
                    "taller": "Organización",
                    "participantes": 0,
                    "productos": 0,
                    "responsable": "Jair Hernandez",
                    "uid": "1325",
                    "info_id": "NRYAR24",
                    "dimensiones": "Comunidades % Organización"
                }
            ],
            "total_estudiantes": 15,
            "total_servicios": 1,
            "servicios": [
                {
                    "id": "101",
                    "fecha": "2026-08-14",
                    "servicio": "Asesoría en Trámites Patria",
                    "usuario": "Carlos Perez",
                    "cedula": "V-12345678",
                    "profesion": "Estudiante",
                    "sexo": "M",
                    "edad": 22,
                    "discapacidad": "No",
                    "comunidad": "Centro",
                    "organizacion": "Ninguna",
                    "info_id": "NRYAR24",
                    "uid": "1325"
                }
            ],
            "conteo_servicios": Counter({"Asesoría en Trámites Patria": 1}),
            "cedulados_serv": 1,
            "no_cedulados_serv": 0,
            "resumen_facilitadores": {
                "1325": {
                    "nombre": "Jair Hernandez",
                    "info_id": "NRYAR24",
                    "formaciones": 1,
                    "estudiantes": 15,
                    "productos": 0,
                    "otras": 1,
                    "total_act": 2,
                    "servicios": 1
                }
            },
            "cuadre_perfecto": True
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Excel (.xlsx)
            ruta_xlsx = os.path.join(tmpdir, "test.xlsx")
            res_xlsx = exportar_reporte_auditoria(mock_resultado, formato="excel", ruta_destino=ruta_xlsx)
            self.assertTrue(os.path.exists(res_xlsx))
            self.assertTrue(os.path.getsize(res_xlsx) > 100)

            # 2. LibreOffice (.ods)
            ruta_ods = os.path.join(tmpdir, "test.ods")
            res_ods = exportar_reporte_auditoria(mock_resultado, formato="ods", ruta_destino=ruta_ods)
            self.assertTrue(os.path.exists(res_ods))
            self.assertTrue(os.path.getsize(res_ods) > 100)

            # 3. Documento PDF (.pdf)
            ruta_pdf = os.path.join(tmpdir, "test.pdf")
            res_pdf = exportar_reporte_auditoria(mock_resultado, formato="pdf", ruta_destino=ruta_pdf)
            self.assertTrue(os.path.exists(res_pdf))
            self.assertTrue(os.path.getsize(res_pdf) > 100)

            # 4. CSV (.csv)
            ruta_csv = os.path.join(tmpdir, "test.csv")
            res_csv = exportar_reporte_auditoria(mock_resultado, formato="csv", ruta_destino=ruta_csv)
            self.assertTrue(os.path.exists(res_csv))
            self.assertTrue(os.path.getsize(res_csv) > 50)

            # 5. Vista en Pantalla (Consola)
            res_consola = exportar_reporte_auditoria(mock_resultado, formato="consola")
            self.assertIn("INFORME", res_consola)
            self.assertIn("Jair Hernandez", res_consola)
            self.assertIn("Robótica con Arduino", res_consola)

    def test_gui_componentes_v425(self):
        """Verifica la existencia del switch turbo, botón de exportar diálogo y los 5 formatos en ComboBox."""
        # Switch Modo Turbo
        self.assertTrue(hasattr(self.app, "switch_modo_turbo"))
        self.assertTrue(hasattr(self.app, "var_modo_turbo"))
        self.assertTrue(self.app.var_modo_turbo.get())

        # Botón Exportar Diálogo
        self.assertTrue(hasattr(self.app, "btn_exportar_reporte_dialogo"))
        self.assertIn(self.app.btn_exportar_reporte_dialogo.cget("state"), ["normal", "disabled"])
        self.assertEqual(self.app.btn_exportar_reporte_dialogo.cget("text"), "💾 Exportar Reporte...")

        # ComboBox 5 formatos
        valores_combo = self.app.combo_aud_formato.cget("values")
        formatos_esperados = [
            "LibreOffice Calc (.ods)",
            "Excel (.xlsx)",
            "Documento PDF (.pdf)",
            "CSV plano (.csv)",
            "Vista en Pantalla (Consola)"
        ]
        for f in formatos_esperados:
            self.assertIn(f, valores_combo)

    def test_gui_al_seleccionar_tab_auditoria(self):
        """Verifica que _al_seleccionar_tab_auditoria no abra ventana sin datos pero responda con datos."""
        # Sin datos: debe salir silenciosamente
        self.app.resultado_auditoria_actual = None
        self.app._al_seleccionar_tab_auditoria()
        # Verificar que no hay modales abiertos
        modales = [w for w in self.app.winfo_children() if w.__class__.__name__ == "CTkToplevel"]
        self.assertEqual(len(modales), 0)

        # Invocación directa del despachador de ventana flotante
        self.app._abrir_ventana_flotante_inspeccion("actividades")
        modales_act = [w for w in self.app.winfo_children() if w.__class__.__name__ == "CTkToplevel"]
        self.assertTrue(len(modales_act) >= 1)
        for m in modales_act:
            m.destroy()
        self.app.update_idletasks()

    def test_excel_autofilter_primera_pestana(self):
        """Verifica que la primera pestaña ('Resumen por Facilitador') del Excel tenga auto_filter activo."""
        import openpyxl
        mock_resultado = {
            "exito": True,
            "criterio_tipo": "uid",
            "criterio_valor": "1325",
            "f_ini": "2026-09-01",
            "f_fin": "2026-09-13",
            "facilitador_principal": "Jair Hernández",
            "total_actividades": 1,
            "total_procesadas": 1,
            "formaciones": [
                {
                    "fecha": "2026-09-05", "id": "1001", "uid": "1325", "info_id": "NRYAR24",
                    "dimensiones": "Robótica", "area": "Robótica", "taller": "Arduino",
                    "titulo": "Robótica con Arduino", "responsable": "Jair Hernández",
                    "participantes": 25, "productos": 0
                }
            ],
            "productos": [],
            "otras_actividades": [],
            "total_estudiantes": 25,
            "total_servicios": 1,
            "servicios": [
                {
                    "fecha": "2026-09-05", "uid": "1325", "info_id": "NRYAR24",
                    "servicio": "Trámite", "cedula": "12345", "id_usuario": "U1",
                    "usuario": "Juan Pérez", "profesion": "Estudiante"
                }
            ],
            "conteo_servicios": {"Trámite": 1},
            "cedulados_serv": 1,
            "no_cedulados_serv": 0,
            "resumen_facilitadores": {
                "1325": {
                    "nombre": "Jair Hernández", "info_id": "NRYAR24",
                    "formaciones": 1, "estudiantes": 25, "productos": 0,
                    "otras": 0, "servicios": 1, "total_act": 1
                }
            },
            "cuadre_perfecto": True
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ruta_xlsx = os.path.join(tmpdir, "reporte_test.xlsx")
            exportar_reporte_auditoria(mock_resultado, formato="excel", ruta_destino=ruta_xlsx)
            self.assertTrue(os.path.exists(ruta_xlsx))

            wb = openpyxl.load_workbook(ruta_xlsx)
            ws_fac = wb["Resumen por Facilitador"]
            self.assertIsNotNone(ws_fac.auto_filter.ref, "La primera hoja debe tener auto_filter.ref configurado")
            self.assertTrue(ws_fac.auto_filter.ref.startswith("A1:H"), f"El auto_filter debe cubrir columnas A1:H: {ws_fac.auto_filter.ref}")

    def test_aislamiento_criterio_busqueda_uid(self):
        """Verifica que al buscar por UID, no se restrinja por infocentro ni estado en InfoApp."""
        with patch("modulos.auditor_reportes.cargar_credenciales_auditoria", return_value=("usr", "pwd")), \
             patch("modulos.auditor_reportes.iniciar_driver_auditoria") as mock_init_driver, \
             patch("modulos.auditor_reportes.autenticar_infoapp") as mock_auth, \
             patch("modulos.auditor_reportes.consultar_actividades_infoapp") as mock_acts, \
             patch("modulos.auditor_reportes.consultar_servicios_infoapp") as mock_servs:

            mock_acts.return_value = (0, [])
            mock_servs.return_value = (0, [])

            # Si el usuario pasa UID '749' y residualmente info_id='NRYAR24'
            res = ejecutar_auditoria(uid="749", info_id="NRYAR24", modo_turbo=False, exportar_formato="consola")

            self.assertTrue(res.get("exito"))
            # Verificar que consultar_actividades_infoapp fue llamado con uid='749' e info_id=''
            mock_acts.assert_called_once()
            _, kwargs_acts = mock_acts.call_args
            self.assertEqual(kwargs_acts.get("uid"), "749")
            self.assertEqual(kwargs_acts.get("info_id"), "")
            self.assertEqual(kwargs_acts.get("estado"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
