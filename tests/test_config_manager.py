#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del gestor central de configuración (config_manager.py) y de su
integración con automatizador_web (motor Playwright).

Ejecutar desde la raíz del proyecto:
    py -m unittest tests.test_config_manager -v
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import config_manager as cm
import modulos.automatizador_web as am


def _escribir_settings(datos: dict) -> str:
    fd, ruta = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    return ruta


class TestCargarSettings(unittest.TestCase):
    def test_archivo_inexistente_devuelve_defaults(self):
        cfg = cm.cargar_settings("no_existe_abc123.json")
        self.assertEqual(cfg, cm.DEFAULTS)

    def test_json_corrupto_devuelve_defaults(self):
        fd, ruta = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("{esto no es json")
        self.addCleanup(os.unlink, ruta)
        self.assertEqual(cm.cargar_settings(ruta), cm.DEFAULTS)

    def test_raiz_no_dict_devuelve_defaults(self):
        ruta = _escribir_settings(["no", "soy", "dict"])
        self.addCleanup(os.unlink, ruta)
        self.assertEqual(cm.cargar_settings(ruta), cm.DEFAULTS)

    def test_fusion_profunda_no_destruye_secciones(self):
        ruta = _escribir_settings({"browser": {"start_maximized": False}})
        self.addCleanup(os.unlink, ruta)
        cfg = cm.cargar_settings(ruta)
        self.assertFalse(cfg["browser"]["start_maximized"])
        # La prioridad default sigue intacta pese al override puntual
        self.assertEqual(
            cfg["browser"]["priority"], cm.DEFAULTS["browser"]["priority"]
        )


class TestHelpersConfig(unittest.TestCase):
    def test_obtener_url_login(self):
        url = cm.obtener_url_login()
        self.assertTrue(url.startswith("https://infoapp2.infocentro.gob.ve"))

    def test_browser_cfg_normaliza_prioridad(self):
        ruta = _escribir_settings({"browser": {"priority": [" CHROMIUM ", "Firefox"]}})
        self.addCleanup(os.unlink, ruta)
        original = cm.SETTINGS_PATH
        cm.SETTINGS_PATH = ruta
        try:
            cfg = cm.obtener_browser_cfg()
        finally:
            cm.SETTINGS_PATH = original
        self.assertEqual(cfg["priority"], ["chromium", "firefox"])

    def test_browser_cfg_priority_por_defecto_es_lista(self):
        cfg = cm.obtener_browser_cfg()
        self.assertIsInstance(cfg["priority"], list)
        self.assertGreater(len(cfg["priority"]), 0)

    def test_telefono_por_defecto_configurable(self):
        self.assertRegex(cm.telefono_por_defecto(), r"^04\d{2}-\d{7}$")

    def test_flag_capturas_on_por_defecto(self):
        self.assertTrue(cm.captura_screenshots_activada())

    def test_no_hay_seccion_timeouts_en_defaults(self):
        """Playwright usa auto-waiting, no hay timeouts Selenium en DEFAULTS."""
        self.assertNotIn("timeouts", cm.DEFAULTS)

    def test_no_existe_obtener_timeout(self):
        """La función obtener_timeout fue eliminada junto con Selenium."""
        self.assertFalse(hasattr(cm, "obtener_timeout"))


class TestFlagCapturasPantalla(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_flag_apagado_no_genera_archivo(self):
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp), \
             patch.object(am.cm, "captura_screenshots_activada", return_value=False):
            am.capturar_pantalla_error(MagicMock(), "12345678")
        self.assertEqual(os.listdir(self.tmp), [])

    def test_flag_encendido_llama_screenshot_en_page(self):
        """Con Playwright, se llama page.screenshot(path=...) en vez de driver.save_screenshot."""
        fake_page = MagicMock()
        fake_page.screenshot.side_effect = (
            lambda path: open(path, "wb").write(b"\x89PNG simulado")
        )
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp), \
             patch.object(am.cm, "captura_screenshots_activada", return_value=True):
            am.capturar_pantalla_error(fake_page, "12345678")
        self.assertEqual(len(os.listdir(self.tmp)), 1)
        fake_page.screenshot.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
