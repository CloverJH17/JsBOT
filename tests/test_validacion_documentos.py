#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas unitarias de validación estricta de documentos, eliminación de C.E. apócrifas
y auditoría de integridad en JsBOT v4.2.1.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.normalizador_datos import (
    procesar_archivo_participantes,
    auditar_integridad_lote,
    generar_cedula_escolar
)
from modulos.automatizador_web import (
    registrar_alumno_playwright,
    registrar_nuevo_usuario_perfil
)


class TestValidacionDocumentos(unittest.TestCase):

    def test_archivo_sin_cedulas_no_genera_falsa_ce(self):
        """Verifica que un archivo sin cédulas no invente C.E. ficticias (11111111)."""
        ruta_archivo = os.path.join(r"C:\Users\thehe\Downloads", "Lista_Nombres_Fechas_Nacimiento.xlsx")
        if not os.path.exists(ruta_archivo):
            self.skipTest("Archivo de prueba no encontrado en Descargas")

        participantes = procesar_archivo_participantes(ruta_archivo)
        self.assertGreater(len(participantes), 0)

        for p in participantes:
            # Nunca debe inventarse la cédula escolar 11811111111
            self.assertEqual(p['cedula'], "")
            self.assertEqual(p['cedula_padre'], "")
            self.assertEqual(p['cedula_escolar'], "")
            self.assertEqual(p['cedulado'], "sin_documento")
            self.assertNotIn("11111111", str(p.get('cedula_escolar', '')))

    def test_auditar_integridad_lote_detecta_bloqueo(self):
        """Verifica que la auditoría marque bloqueante_registro cuando faltan documentos."""
        participantes = [
            {"nombre": "Isaac", "apellido": "Ávila", "cedula": "", "cedula_escolar": "", "cedula_padre": ""},
            {"nombre": "José", "apellido": "Giménez", "cedula": "", "cedula_escolar": "", "cedula_padre": ""}
        ]
        audit = auditar_integridad_lote(participantes)
        self.assertEqual(audit["total"], 2)
        self.assertEqual(audit["sin_documento"], 2)
        self.assertTrue(audit["requiere_atencion"])
        self.assertTrue(audit["bloqueante_registro"])

    def test_participante_con_tutor_genera_ce_legitima(self):
        """Verifica que cuando sí existe cédula de tutor, se genere la CE legítima."""
        ce = generar_cedula_escolar("2018-02-11", "21302079", "1")
        self.assertEqual(ce, "11821302079")

    def test_automatizador_rechaza_participante_sin_documento(self):
        """Verifica que el automatizador web no intente inyectar a alumnos sin documento."""
        mock_page = MagicMock()
        mock_page.url = "https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=100"

        alumno_sin_doc = {
            "nombre": "Isaac",
            "apellido": "Ávila",
            "cedula": "",
            "cedula_escolar": "",
            "cedula_padre": "",
            "cedulado": "sin_documento"
        }
        config = {"url": "https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=100"}

        ok, msg = registrar_alumno_playwright(mock_page, alumno_sin_doc, config)
        self.assertFalse(ok)
        self.assertIn("sin documento", msg.lower())

    def test_automatizador_servicios_rechaza_menor_sin_tutor(self):
        """Verifica que servicios rechace registrar perfiles de menores sin tutor."""
        mock_page = MagicMock()
        persona_sin_doc = {
            "nombre": "Isaac",
            "apellido": "Ávila",
            "cedula": "",
            "cedula_padre": "",
            "cedulado": "sin_documento"
        }
        ok, msg = registrar_nuevo_usuario_perfil(mock_page, persona_sin_doc, {})
        self.assertFalse(ok)
        self.assertIn("sin documento", msg.lower())


if __name__ == "__main__":
    unittest.main()
