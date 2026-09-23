#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SUITE: NORMALIZADOR DE NOMBRES COMBINADOS Y APERTURA ASISTIDA GUI
Valida la extracción precisa de nombres/apellidos en columnas compuestas,
la ausencia de falsos positivos en la auditoría estructural y los controles
de apertura en Excel y recarga en caliente de la interfaz gráfica.
"""
import unittest
import os
import sys
import tempfile
import csv
from unittest.mock import patch, MagicMock

from modulos.normalizador_datos import (
    procesar_archivo_participantes,
    abrir_archivo_asistido,
)


class TestNormalizadorNombresCombinados(unittest.TestCase):
    """Verifica que las columnas de nombres compuestos se separen inteligentemente."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _crear_csv(self, filas):
        ruta = os.path.join(self.temp_dir.name, "test_nombres.csv")
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for r in filas:
                writer.writerow(r)
        return ruta

    def test_columna_nombres_y_apellidos_separacion_4_palabras(self):
        """Verifica que 'Nombres y Apellidos' con 4 palabras se divida en nombre y apellido."""
        filas = [
            ["N°", "Nombres y Apellidos", "Cédula", "Fecha Nac.", "Género", "Teléfono"],
            ["1", "Garrido Tovar Gabriel Alexander", "33108316", "2010-01-15", "M", "0414-3521083"]
        ]
        ruta = self._crear_csv(filas)
        res = procesar_archivo_participantes(ruta)

        self.assertEqual(len(res), 1)
        part = res[0]
        self.assertTrue(bool(part.get("nombre")), "El nombre no debe estar vacío")
        self.assertTrue(bool(part.get("apellido")), "El apellido no debe estar vacío")
        self.assertEqual(part.get("cedula"), "33108316")
        self.assertEqual(part.get("cedulado"), "si")

    def test_columna_nombres_y_apellidos_separacion_2_y_3_palabras(self):
        """Verifica que nombres de 2 y 3 palabras se particionen adecuadamente."""
        filas = [
            ["N°", "Nombres y Apellidos", "Cédula", "Fecha Nac.", "Género", "Teléfono"],
            ["1", "Juan Perez", "12345678", "1990-05-10", "M", "0412-1112233"],
            ["2", "Maria Elena Gomez", "23456789", "1995-08-20", "F", "0414-2223344"],
        ]
        ruta = self._crear_csv(filas)
        res = procesar_archivo_participantes(ruta)

        self.assertEqual(len(res), 2)
        # Juan Perez -> nombre: Juan, apellido: Perez
        self.assertEqual(res[0]["nombre"], "Juan")
        self.assertEqual(res[0]["apellido"], "Perez")
        # Maria Elena Gomez -> nombre: Maria Elena o Maria, apellido: Gomez
        self.assertTrue(bool(res[1]["nombre"]))
        self.assertTrue(bool(res[1]["apellido"]))

    def test_auditoria_estructural_sin_falsas_inconsistencias(self):
        """Valida que un lote con nombres compuestos resulte en 0 inconsistencias."""
        filas = [
            ["Nombres y Apellidos", "Cédula", "Fecha Nac.", "Género", "Teléfono"],
            ["Acosta Escalona Cristian Alexander", "33257083", "2010-03-20", "M", "0424-5108344"],
            ["Verastegui Melendez Sorianny Yulieth", "33277978", "2010-04-09", "F", "0412-7526288"]
        ]
        ruta = self._crear_csv(filas)
        participantes = procesar_archivo_participantes(ruta)

        inconsistencias = 0
        for p in participantes:
            nom_p = str(p.get('nombre', '') or '').strip()
            ape_p = str(p.get('apellido', '') or '').strip()
            tiene_nombre = bool((nom_p and ape_p) or (len(f"{nom_p} {ape_p}".strip()) >= 3 and not p.get('solo_cedula', False)))
            tiene_doc = bool(p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre'))
            if not (tiene_nombre and tiene_doc):
                inconsistencias += 1

        self.assertEqual(inconsistencias, 0)


class TestAperturaAsistidaYRecarga(unittest.TestCase):
    """Valida el comportamiento de abrir_archivo_asistido y métodos de control GUI."""

    def test_abrir_archivo_asistido_retorna_booleano_sin_lanzar_excepcion(self):
        """abrir_archivo_asistido debe retornar bool de forma segura ante rutas válidas o inexistentes."""
        res = abrir_archivo_asistido("archivo_inexistente_de_prueba.xlsx")
        self.assertIsInstance(res, bool)
        self.assertFalse(res)

    @patch("os.startfile", create=True)
    def test_abrir_archivo_asistido_exito_windows(self, mock_startfile):
        """Si os.startfile tiene éxito, la función debe retornar True."""
        mock_startfile.return_value = None
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(b"data")
            tmp_path = tmp.name

        try:
            with patch("sys.platform", "win32"):
                res = abrir_archivo_asistido(tmp_path)
                self.assertTrue(res)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_resolucion_rutas_gui_independientes(self):
        """Verifica que el método auxiliar _obtener_ruta_seccion discrimine por sección."""
        from modulos.interfaz_grafica import JsBotGUI

        class MockApp:
            archivo_actual_ruta = "ruta_general.xlsx"
            archivo_ruta_formacion = "formacion.xlsx"
            archivo_ruta_servicios = "servicios.xlsx"
            archivo_ruta_planillas = "planillas.ods"
            _obtener_ruta_seccion = JsBotGUI._obtener_ruta_seccion

        app = MockApp()
        self.assertEqual(app._obtener_ruta_seccion("Formacion"), "formacion.xlsx")
        self.assertEqual(app._obtener_ruta_seccion("Servicios"), "servicios.xlsx")
        self.assertEqual(app._obtener_ruta_seccion("Planillas"), "planillas.ods")


if __name__ == "__main__":
    unittest.main()
