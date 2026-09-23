#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TESTS: SUITE DE VALIDACIÓN INTEGRAL JSBOT v4.8.0 (test_suite_v480.py)
===============================================================================
"""

import unittest
import json
import io
import openpyxl
from unittest.mock import MagicMock, patch
from pathlib import Path
import modulos.version as ver
import modulos.entorno as entorno
from modulos.verificador_cargas_export import (
    obtener_participantes_existentes_actividad,
    verificar_participantes_actividad,
    verificar_servicios_cargados_hoy,
    verificar_actividad_cargada
)
from modulos.diagnostico_facilitador import diagnosticar_actividades_facilitador
from modulos.generador_planilla import generar_planilla_desde_actividad_infoapp

class TestSuiteV480(unittest.TestCase):

    def test_01_consistencia_version_v480(self):
        """Verifica que la versión 4.10.0 esté perfectamente sincronizada."""
        current_v = ver.__version__
        self.assertEqual(ver.ETIQUETA_VERSION, f"v{current_v}")
        
        # settings.json
        settings_path = str(entorno.ARCHIVO_SETTINGS)
        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("app", {}).get("version"), current_v)
        
        # version.txt
        version_txt_path = Path(entorno.RAIZ_PROYECTO) / "docs" / "version.txt"
        with open(version_txt_path, "r", encoding="utf-8") as f:
            txt = f.read()
        self.assertIn(f"[v{current_v}]", txt)

    @patch("requests.Session.get")
    def test_02_obtener_participantes_existentes_actividad(self, mock_get):
        """Valida la extracción de participantes desde exportxlsx_2.php."""
        wb = openpyxl.Workbook()
        ws = wb.active
        # Fila 1: Cabecera
        ws.append(["id", "id_user_final", "uid_fac", "id_activity", "col4", "col5", "col6", "col7", "col8", "col9", "col10", "name", "name_2", "lastname", "lastname_2", "col15", "col16", "document_id", "col18", "col19", "col20", "user_f_nacimiento", "age", "gender", "col24", "col25", "phone", "email"])
        # Fila 2: Datos
        ws.append(["2001", "101", "1325", "528449", "", "", "", "", "", "", "", "Pedro", "Antonio", "Perez", "Gomez", "V", "Si", "12345678", "No aplica", 0, 100, "2005-01-01", 21, "Hombre", "No", "No", "0412-1112233", "p@g.com"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = buf.getvalue()
        mock_get.return_value = mock_resp
        
        session = MagicMock()
        session.get = mock_get
        
        parts = obtener_participantes_existentes_actividad(session, "528449")
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["dni"], "12345678")
        self.assertEqual(parts[0]["nombre"], "Pedro Antonio")
        self.assertEqual(parts[0]["apellido"], "Perez Gomez")
        self.assertEqual(parts[0]["telefono"], "0412-1112233")

    @patch("modulos.verificador_cargas_export.obtener_participantes_existentes_actividad")
    def test_03_verificar_participantes_actividad(self, mock_parts):
        mock_parts.return_value = [
            {"dni": "11111111", "nombre": "Carlos", "apellido": "R"},
            {"dni": "22222222", "nombre": "Ana", "apellido": "M"}
        ]
        session = MagicMock()
        
        # Caso completo
        res = verificar_participantes_actividad(session, "5001", ["11111111", "22222222"])
        self.assertTrue(res["exito_completo"])
        self.assertEqual(res["confirmados_total"], 2)
        
        # Caso faltante
        res2 = verificar_participantes_actividad(session, "5001", ["11111111", "33333333"])
        self.assertFalse(res2["exito_completo"])
        self.assertIn("33333333", res2["faltantes"])

    @patch("modulos.diagnostico_facilitador.consultar_actividades_infoapp_export")
    def test_04_diagnostico_facilitador(self, mock_acts):
        mock_acts.return_value = (3, [
            {"id": "1", "titulo": "Taller 1", "participantes": 15, "tipo_clasificacion": "formacion"},
            {"id": "2", "titulo": "Diseño", "participantes": 0, "tipo_clasificacion": "producto"},
            {"id": "3", "titulo": "Borrador Incompleto", "participantes": 0, "tipo_clasificacion": "formacion"}
        ])
        session = MagicMock()
        
        diag = diagnosticar_actividades_facilitador(session, "1325", "2026-09-01", "2026-09-17")
        self.assertEqual(diag["total_actividades"], 3)
        self.assertEqual(diag["conteo_sin_participantes"], 1)
        self.assertEqual(diag["sin_participantes"][0]["id"], "3")
        self.assertEqual(diag["salud_reporte"], "atencion_requerida")

    @patch("modulos.verificador_cargas_export.obtener_participantes_existentes_actividad")
    @patch("modulos.generador_planilla.generar_planilla_multiformato")
    def test_05_generar_planilla_desde_actividad_infoapp(self, mock_gen, mock_obt):
        mock_obt.return_value = [
            {"dni": "12345", "nombre": "Jose", "apellido": "Perez", "telefono": "0412"}
        ]
        mock_gen.return_value = "Planilla_Test.ods"
        
        session = MagicMock()
        res = generar_planilla_desde_actividad_infoapp(session, "528449", formato="ods")
        self.assertEqual(res, "Planilla_Test.ods")
        self.assertTrue(mock_gen.called)

if __name__ == "__main__":
    unittest.main()
