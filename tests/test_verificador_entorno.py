#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo verificador_entorno.py y abstracción multiplataforma.
JsBOT v3.6.0
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import verificador_entorno as ve
from modulos.normalizador_datos import abrir_archivo_asistido


class TestVerificadorEntorno(unittest.TestCase):

    def test_detectar_sistema_operativo(self):
        so = ve.detectar_sistema_operativo()
        self.assertIsInstance(so, str)
        self.assertTrue(len(so) > 0)
        if sys.platform.startswith("win"):
            self.assertEqual(so, "Windows")

    def test_detectar_navegadores(self):
        navs = ve.detectar_navegadores()
        self.assertIsInstance(navs, str)
        self.assertTrue("detectado" in navs.lower() or "no detectado" in navs.lower())

    def test_detectar_suite_ofimatica(self):
        tiene, ruta = ve.detectar_suite_ofimatica()
        self.assertIsInstance(tiene, bool)
        if tiene:
            self.assertIsNotNone(ruta)

    def test_verificar_integridad_archivos(self):
        estado = ve.verificar_integridad_archivos()
        self.assertIn("settings", estado)
        self.assertIn("plantilla", estado)
        self.assertIn("logs", estado)
        # settings and plantilla must exist in repo
        self.assertTrue(estado["settings"][0])
        self.assertTrue(estado["plantilla"][0])
        self.assertTrue(estado["logs"][0])

    def test_abrir_archivo_asistido_invocable(self):
        self.assertTrue(callable(abrir_archivo_asistido))

    def test_ejecutar_checklist_sistema_exito(self):
        resultado = ve.ejecutar_checklist_sistema()
        self.assertTrue(resultado)


if __name__ == "__main__":
    unittest.main()
