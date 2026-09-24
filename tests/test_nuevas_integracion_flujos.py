#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de integración entre ETL, RPA, checkpoints y verificación."""
import importlib
import unittest
from unittest.mock import MagicMock, patch

from modulos import automatizador_web


class TestIntegracionFlujosNueva(unittest.TestCase):
    def _participante(self, cedula):
        return {
            "nombre": "Ana",
            "apellido": "Pérez",
            "cedula": cedula,
            "cedulado": "si",
            "cedula_escolar": "",
            "cedula_padre": "",
            "nacimiento": "1995-04-03",
            "edad": 31,
            "genero": "F",
            "telefono": "04121234567",
        }

    def _config(self):
        return {
            "usuario": "test",
            "clave": "test",
            "url": "https://example.test/admin/index.php?id_activity=123",
            "id_actividad": "123",
            "timestamp_str": "20260924_0100",
            "archivo_log": None,
        }

    def _preparar_web(self, contenedor, config):
        contenedor["page"] = MagicMock()
        contenedor["context"] = MagicMock()
        contenedor["context"].cookies.return_value = []
        contenedor["pw"] = MagicMock()

    def test_carga_formacion_actualiza_checkpoint_historico_y_verifica(self):
        participantes = [self._participante("25123456"), self._participante("26123457")]
        config = self._config()
        logs = []
        config["log_callback"] = logs.append

        with patch.object(automatizador_web, "asegurar_sesion_activa", side_effect=self._preparar_web), \
             patch.object(automatizador_web, "registrar_alumno_playwright", return_value=(True, "verificado")), \
             patch.object(automatizador_web, "guardar_estado_sesion") as guardar_checkpoint, \
             patch.object(automatizador_web, "registrar_inscrito_historico_db") as historico, \
             patch.object(automatizador_web, "registrar_evento_log"), \
             patch.object(automatizador_web, "renderizar_panel_carga"), \
             patch("modulos.verificador_cargas_export.verificar_participantes_actividad", return_value={"confirmados_total": 2, "esperados_total": 2, "exito_completo": True}):
            exitosos, fallidos, _ = automatizador_web.ejecutar_carga_infoapp(participantes, config)

        self.assertEqual(len(exitosos), 2)
        self.assertEqual(fallidos, [])
        self.assertEqual(guardar_checkpoint.call_count, 2)
        self.assertEqual(historico.call_count, 2)
        self.assertTrue(any("confirmados" in message for message in logs))

    def test_verificacion_parcial_queda_visible_en_bitacora(self):
        participantes = [self._participante("25123456"), self._participante("26123457")]
        config = self._config()
        logs = []
        config["log_callback"] = logs.append

        with patch.object(automatizador_web, "asegurar_sesion_activa", side_effect=self._preparar_web), \
             patch.object(automatizador_web, "registrar_alumno_playwright", return_value=(True, "verificado")), \
             patch.object(automatizador_web, "guardar_estado_sesion"), \
             patch.object(automatizador_web, "registrar_inscrito_historico_db"), \
             patch.object(automatizador_web, "registrar_evento_log"), \
             patch.object(automatizador_web, "renderizar_panel_carga"), \
             patch("modulos.verificador_cargas_export.verificar_participantes_actividad", return_value={"confirmados_total": 1, "esperados_total": 2, "exito_completo": False, "faltantes": ["26123457"]}):
            exitosos, fallidos, _ = automatizador_web.ejecutar_carga_infoapp(participantes, config)

        self.assertEqual(len(exitosos), 2)
        self.assertEqual(fallidos, [])
        self.assertTrue(any("50.0%" in message for message in logs))

    def test_importacion_de_modulos_no_telemetria(self):
        modules = [
            "main",
            "modulos.entorno",
            "modulos.config_manager",
            "modulos.normalizador_datos",
            "modulos.automatizador_web",
            "modulos.driver_factory",
            "modulos.auditor_reportes",
            "modulos.motor_export_auditoria",
            "modulos.generador_planilla",
            "modulos.gestor_sesion",
            "modulos.verificador_cargas_export",
            "modulos.diagnostico_facilitador",
            "modulos.verificador_entorno",
            "modulos.web_utils",
            "modulos.orquestador",
        ]
        for module in modules:
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))

    def test_registro_perfil_rechaza_menor_sin_representante(self):
        page = MagicMock()
        persona = {"nombre": "Niño", "apellido": "Prueba", "cedulado": "sin_documento", "cedula": "", "cedula_padre": ""}
        exito, detalle = automatizador_web.registrar_nuevo_usuario_perfil(page, persona, {})
        self.assertFalse(exito)
        self.assertIn("documento", detalle.lower())
        page.goto.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
