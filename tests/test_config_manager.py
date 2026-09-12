#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del gestor central de configuración (config_manager.py) y de su
integración con automatizador_web (cascada de navegadores y flag de capturas).

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
    def test_archivo_valido_pisa_defaults(self):
        ruta = _escribir_settings({"timeouts": {"ajax_wait_seconds": 42}})
        self.addCleanup(os.unlink, ruta)
        cfg = cm.cargar_settings(ruta)
        self.assertEqual(cfg["timeouts"]["ajax_wait_seconds"], 42)
        # Las claves ausentes conservan el default
        self.assertEqual(cfg["timeouts"]["element_wait_seconds"], 12)

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
    def test_obtener_timeout_conocido(self):
        self.assertEqual(cm.obtener_timeout("ajax_wait_seconds"), 15)

    def test_obtener_timeout_inexistente_usa_default(self):
        self.assertEqual(cm.obtener_timeout("campo_raro_xyz", 9), 9)

    def test_obtener_url_login(self):
        url = cm.obtener_url_login()
        self.assertTrue(url.startswith("https://infoapp2.infocentro.gob.ve"))

    def test_browser_cfg_normaliza_prioridad(self):
        ruta = _escribir_settings({"browser": {"priority": [" EDGE ", "Firefox"]}})
        self.addCleanup(os.unlink, ruta)
        original = cm.SETTINGS_PATH
        cm.SETTINGS_PATH = ruta
        try:
            cfg = cm.obtener_browser_cfg()
        finally:
            cm.SETTINGS_PATH = original
        self.assertEqual(cfg["priority"], ["edge", "firefox"])

    def test_telefono_por_defecto_configurable(self):
        self.assertRegex(cm.telefono_por_defecto(), r"^04\d{2}-\d{7}$")

    def test_flag_capturas_on_por_defecto(self):
        self.assertTrue(cm.captura_screenshots_activada())


class TestCascadaNavegadores(unittest.TestCase):
    """La cascada debe respetar browser.priority sin abrir navegadores reales."""

    def _fabrica(self, nombre, resultado):
        llamadas = []

        def fabrica(maximizado):
            llamadas.append((nombre, maximizado))
            return resultado

        fabrica.llamadas = llamadas
        return fabrica

    def test_respeta_priority_y_salta_fallidos(self):
        f_firefox = self._fabrica("firefox", None)          # falla
        f_chrome = self._fabrica("chrome", "DRIVER_CHROME")  # funciona
        f_edge = self._fabrica("edge", "DRIVER_EDGE")
        originales = dict(am.FABRICAS_NAVEGADOR)
        am.FABRICAS_NAVEGADOR = {
            "firefox": f_firefox, "chrome": f_chrome, "edge": f_edge
        }
        try:
            with patch.object(
                am.cm, "obtener_browser_cfg",
                return_value={"priority": ["firefox", "chrome", "edge"],
                              "start_maximized": True}
            ):
                driver = am.iniciar_navegador()
        finally:
            am.FABRICAS_NAVEGADOR = originales

        self.assertEqual(driver, "DRIVER_CHROME")
        self.assertEqual(len(f_firefox.llamadas), 1)
        self.assertEqual(f_edge.llamadas, [])  # nunca se llega a Edge

    def test_nombres_desconocidos_se_saltan(self):
        f_chrome = self._fabrica("chrome", "DRIVER_OK")
        originales = dict(am.FABRICAS_NAVEGADOR)
        am.FABRICAS_NAVEGADOR = {"chrome": f_chrome}
        try:
            with patch.object(
                am.cm, "obtener_browser_cfg",
                return_value={"priority": ["safari", "opera", "chrome"],
                              "start_maximized": False}
            ):
                driver = am.iniciar_navegador()
        finally:
            am.FABRICAS_NAVEGADOR = originales

        self.assertEqual(driver, "DRIVER_OK")

    def test_sin_navegadores_devuelve_none(self):
        originales = dict(am.FABRICAS_NAVEGADOR)
        am.FABRICAS_NAVEGADOR = {}
        try:
            self.assertIsNone(am.iniciar_navegador())
        finally:
            am.FABRICAS_NAVEGADOR = originales


class TestFlagCapturasPantalla(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_flag_apagado_no_genera_archivo(self):
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp), \
             patch.object(am.cm, "captura_screenshots_activada", return_value=False):
            am.capturar_pantalla_error(MagicMock(), "12345678")
        self.assertEqual(os.listdir(self.tmp), [])

    def test_flag_encendido_genera_archivo(self):
        fake_driver = MagicMock()
        # save_screenshot debe escribir el archivo realmente (como Selenium)
        fake_driver.save_screenshot.side_effect = (
            lambda ruta: open(ruta, "wb").write(b"\x89PNG simulado")
        )
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp):
            am.capturar_pantalla_error(fake_driver, "12345678")
        self.assertEqual(len(os.listdir(self.tmp)), 1)
        fake_driver.save_screenshot.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
