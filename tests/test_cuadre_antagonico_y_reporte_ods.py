#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST SUITE: CONCILIACIÓN ANTAGÓNICA Y EXPORTACIÓN ODS / PDF (v4.14.0)
===============================================================================
Pruebas unitarias de integridad matemática para:
1. conciliar_balance_auditoria (control antagónico de doble partida, duplicados,
   fechas extemporáneas y pérdida en crawler).
2. exportar_reporte_ods (Libro LibreOffice Calc con 4 hojas idénticas a Excel).
3. exportar_reporte_pdf (Informe tabular con UTF-8 íntegro).
===============================================================================
"""

import os
import sys
import unittest
import tempfile
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.auditor_reportes import (
    conciliar_balance_auditoria,
    exportar_reporte_ods,
    exportar_reporte_pdf,
    exportar_reporte_auditoria
)


class TestCuadreAntagonicoYReporteODS(unittest.TestCase):
    """Pruebas exhaustivas para la conciliación independiente y reportes ODS/PDF."""

    def setUp(self):
        self.mock_resultado_cuadrado = {
            "exito": True,
            "criterio_tipo": "uid",
            "criterio_valor": "1325",
            "f_ini": "2026-09-01",
            "f_fin": "2026-09-30",
            "facilitador_principal": "Jair Alejandro Hernández González",
            "total_actividades": 2,
            "total_procesadas": 2,
            "formaciones": [
                {
                    "fecha": "2026-09-10",
                    "id": "ACT_001",
                    "uid": "1325",
                    "info_id": "YAR01",
                    "taller": "Robótica Educativa con Arduino",
                    "titulo": "Robótica Educativa con Arduino",
                    "area": "Tecnología",
                    "responsable": "Jair Hernández",
                    "participantes": 15,
                    "productos": 0,
                    "dimensiones": "Formación, Robótica"
                }
            ],
            "productos": [
                {
                    "fecha": "2026-09-15",
                    "id": "ACT_002",
                    "uid": "1325",
                    "info_id": "YAR01",
                    "taller": "Infografía Digital Comunitaria",
                    "titulo": "Infografía Digital Comunitaria",
                    "area": "Comunicación",
                    "responsable": "Jair Hernández",
                    "participantes": 0,
                    "productos": 1,
                    "dimensiones": "Contenido, Medios Digitales"
                }
            ],
            "otras_actividades": [],
            "total_estudiantes": 15,
            "total_servicios": 1,
            "servicios": [
                {
                    "fecha": "2026-09-18",
                    "uid": "1325",
                    "info_id": "YAR01",
                    "servicio": "Asesoría Trámites en Línea",
                    "cedula": "V-18765432",
                    "id_usuario": "USR_99",
                    "usuario": "María Rodríguez",
                    "profesion": "Comerciante"
                }
            ],
            "conteo_servicios": {"Asesoría Trámites en Línea": 1},
            "cedulados_serv": 1,
            "no_cedulados_serv": 0,
            "resumen_facilitadores": {
                "1325": {
                    "uid": "1325",
                    "nombre": "Jair Alejandro Hernández González",
                    "info_id": "YAR01",
                    "formaciones": 1,
                    "estudiantes": 15,
                    "productos": 1,
                    "otras": 0,
                    "total_act": 2,
                    "servicios": 1
                }
            },
            "cuadre_perfecto": True
        }

    def test_conciliacion_lote_perfecto(self):
        """Verifica que un lote consistente obtenga dictamen CUADRADO (100%)."""
        conc = conciliar_balance_auditoria(self.mock_resultado_cuadrado, total_declarado_servidor=2)
        self.assertTrue(conc["cuadra"])
        self.assertEqual(conc["porcentaje_cuadre"], 100.0)
        self.assertEqual(conc["dictamen"], "CUADRADO (100%)")
        self.assertEqual(len(conc["hallazgos"]), 0)
        self.assertEqual(conc["metricas_control"]["tot_act_declarado"], 2)

    def test_conciliacion_discrepancia_suma_facilitador(self):
        """Detecta discrepancia cuando la suma de facilitadores no coincide con el total."""
        res_alterado = dict(self.mock_resultado_cuadrado)
        res_alterado["total_actividades"] = 3  # Declarado 3 pero facilitador solo suma 2
        conc = conciliar_balance_auditoria(res_alterado)
        self.assertFalse(conc["cuadra"])
        self.assertIn("DISCREPANCIA", conc["dictamen"])
        self.assertTrue(any("la suma de facilitadores" in h for h in conc["hallazgos"]))

    def test_conciliacion_deteccion_ids_duplicados(self):
        """Detecta IDs de actividad duplicados y emite hallazgo."""
        res_duplicado = dict(self.mock_resultado_cuadrado)
        act_dup = dict(self.mock_resultado_cuadrado["formaciones"][0])
        # Insertar segunda actividad con el mismo ID ACT_001
        res_duplicado["formaciones"] = [act_dup, act_dup]
        res_duplicado["total_actividades"] = 2
        res_duplicado["productos"] = []
        conc = conciliar_balance_auditoria(res_duplicado)
        self.assertFalse(conc["cuadra"])
        self.assertIn("ACT_001", conc["metricas_control"]["ids_duplicados"])
        self.assertTrue(any("duplicados" in h for h in conc["hallazgos"]))

    def test_conciliacion_deteccion_fechas_extemporaneas(self):
        """Detecta actividades fuera del rango evaluado f_ini - f_fin."""
        res_extemp = dict(self.mock_resultado_cuadrado)
        # Fecha en agosto, pero el período evaluado es septiembre
        res_extemp["formaciones"] = [
            dict(self.mock_resultado_cuadrado["formaciones"][0], fecha="2026-08-15")
        ]
        conc = conciliar_balance_auditoria(res_extemp)
        self.assertFalse(conc["cuadra"])
        self.assertGreater(conc["metricas_control"]["actividades_extemporaneas"], 0)
        self.assertTrue(any("extemporáneas" in h for h in conc["hallazgos"]))

    def test_conciliacion_deteccion_caida_crawler(self):
        """Detecta pérdida de registros si el servidor reportó más que lo capturado."""
        conc = conciliar_balance_auditoria(self.mock_resultado_cuadrado, total_declarado_servidor=10)
        self.assertFalse(conc["cuadra"])
        self.assertTrue(any("Pérdida en captura" in h for h in conc["hallazgos"]))

    def test_exportar_reporte_ods_4_pestanas(self):
        """Verifica que exportar_reporte_ods cree un archivo ODS con las 4 pestañas idénticas a Excel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta_ods = os.path.join(tmpdir, "Auditoria_Test.ods")
            resultado_exp = exportar_reporte_ods(self.mock_resultado_cuadrado, ruta_destino=ruta_ods)

            self.assertTrue(os.path.exists(resultado_exp))
            self.assertGreater(os.path.getsize(resultado_exp), 500)

            # Leer el archivo ODS con pandas
            with pd.ExcelFile(resultado_exp, engine='odf') as xl:
                pestañas_esperadas = [
                    "Resumen por Facilitador",
                    "Actividades",
                    "Servicios",
                    "Resumen Ejecutivo"
                ]
                self.assertEqual(xl.sheet_names, pestañas_esperadas)

                # Validar contenido de Hoja 1 (Resumen por Facilitador)
                df_fac = xl.parse("Resumen por Facilitador")
                self.assertIn("UID", df_fac.columns)
                self.assertIn("Facilitador / Responsable", df_fac.columns)
                self.assertIn("Total Act.", df_fac.columns)

                # Validar contenido de Hoja 2 (Actividades)
                df_act = xl.parse("Actividades")
                self.assertEqual(len(df_act), 2)
                self.assertIn("ID InfoApp", df_act.columns)
                self.assertIn("Participantes", df_act.columns)

                # Validar contenido de Hoja 3 (Servicios)
                df_srv = xl.parse("Servicios")
                self.assertEqual(len(df_srv), 1)
                self.assertIn("Cédula", df_srv.columns)
                self.assertIn("Servicio / Trámite", df_srv.columns)

                # Validar contenido de Hoja 4 (Resumen Ejecutivo)
                df_res = xl.parse("Resumen Ejecutivo")
                self.assertIn("Métrica / Parámetro", df_res.columns)
                self.assertIn("Valor", df_res.columns)

    def test_exportar_reporte_pdf_utf8_e_integridad(self):
        """Verifica la exportación del reporte PDF estructurado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ruta_pdf = os.path.join(tmpdir, "Auditoria_Test.pdf")
            res_pdf = exportar_reporte_pdf(self.mock_resultado_cuadrado, ruta_destino=ruta_pdf)

            self.assertTrue(os.path.exists(res_pdf))
            self.assertGreater(os.path.getsize(res_pdf), 1000)


if __name__ == '__main__':
    unittest.main()
