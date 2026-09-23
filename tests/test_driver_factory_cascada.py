#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUITE DE PRUEBAS UNITARIAS: CASCADA RESILIENTE DE NAVEGADORES (PLAYWRIGHT FACTORY)
JsBOT v4.10.1 — Garantiza que el orden de cascada y la conmutación automática ante fallos
funcionen de forma transparente y protejan contra regresiones.
"""
import unittest
from unittest.mock import patch, MagicMock

from modulos.driver_factory import (
    _construir_cascada,
    _resolver_config_navegador,
    obtener_contexto_playwright,
)
from modulos.automatizador_web import iniciar_contexto_playwright


class TestDriverFactoryCascada(unittest.TestCase):
    """Pruebas del algoritmo de cascada y resolución de navegadores."""

    def test_construir_cascada_orden_preferido_firefox(self):
        """Si el preferido es firefox, el orden debe ser: firefox -> chrome -> chromium -> edge."""
        cascada = _construir_cascada("firefox")
        self.assertEqual(cascada, ["firefox", "chrome", "chromium", "edge"])

    def test_construir_cascada_orden_preferido_edge(self):
        """Si el preferido es edge, el orden debe ser: edge -> chrome -> firefox -> chromium."""
        cascada = _construir_cascada("edge")
        self.assertEqual(cascada, ["edge", "chrome", "firefox", "chromium"])

    def test_construir_cascada_normalizacion_alias(self):
        """Alias como 'Google Chrome' o 'Microsoft Edge' deben normalizarse a sus claves internas."""
        self.assertEqual(_construir_cascada("Google Chrome"), ["chrome", "firefox", "chromium", "edge"])
        self.assertEqual(_construir_cascada("Microsoft Edge"), ["edge", "chrome", "firefox", "chromium"])
        self.assertEqual(_construir_cascada("Mozilla Firefox"), ["firefox", "chrome", "chromium", "edge"])

    def test_construir_cascada_sin_preferencia(self):
        """Sin preferencia debe retornar el orden base estándar."""
        self.assertEqual(_construir_cascada(None), ["chrome", "firefox", "chromium", "edge"])
        self.assertEqual(_construir_cascada(""), ["chrome", "firefox", "chromium", "edge"])

    def test_resolver_config_navegador(self):
        """Mapeo correcto a instancias Playwright, canales nativos y subcarpetas."""
        mock_pw = MagicMock()
        mock_pw.firefox = "PW_FIREFOX"
        mock_pw.chromium = "PW_CHROMIUM"
        mock_pw.webkit = "PW_WEBKIT"

        # Firefox
        b_type, channel, subf = _resolver_config_navegador(mock_pw, "firefox")
        self.assertEqual(b_type, "PW_FIREFOX")
        self.assertIsNone(channel)
        self.assertEqual(subf, "firefox")

        # Chrome
        b_type, channel, subf = _resolver_config_navegador(mock_pw, "chrome")
        self.assertEqual(b_type, "PW_CHROMIUM")
        self.assertEqual(channel, "chrome")
        self.assertEqual(subf, "chromium")

        # Edge
        b_type, channel, subf = _resolver_config_navegador(mock_pw, "msedge")
        self.assertEqual(b_type, "PW_CHROMIUM")
        self.assertEqual(channel, "msedge")
        self.assertEqual(subf, "chromium")

        # Chromium puro
        b_type, channel, subf = _resolver_config_navegador(mock_pw, "chromium")
        self.assertEqual(b_type, "PW_CHROMIUM")
        self.assertIsNone(channel)
        self.assertEqual(subf, "chromium")


class TestDriverFactoryConmutacion(unittest.TestCase):
    """Pruebas de conmutación y tolerancia a fallos en tiempo de ejecución."""

    @patch("modulos.driver_factory.sync_playwright")
    def test_conmutacion_automatica_cuando_falla_preferido(self, mock_sync_pw):
        """
        Si el preferido (ej: firefox) falla con 'Executable doesn't exist',
        el factory debe conmutar automáticamente al siguiente (chrome) sin lanzar excepción.
        """
        mock_pw = MagicMock()
        mock_sync_pw.return_value.start.return_value = mock_pw

        # Simular que Firefox no tiene binarios instalados
        mock_pw.firefox.launch_persistent_context.side_effect = Exception(
            "BrowserType.launch: Executable doesn't exist at C:\\path\\firefox.exe"
        )

        # Simular que Chrome sí arranca exitosamente
        mock_context_chrome = MagicMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context_chrome

        import tempfile
        import shutil
        tmp_dir = tempfile.mkdtemp()
        try:
            pw, ctx = obtener_contexto_playwright(
                headless=True,
                navegador="firefox",
                user_data_dir=tmp_dir
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # Debe haber intentado Firefox y luego haber conmutado a Chrome
        self.assertEqual(ctx, mock_context_chrome)
        mock_pw.firefox.launch_persistent_context.assert_called_once()
        self.assertTrue(mock_pw.chromium.launch_persistent_context.called)

    @patch("modulos.driver_factory.sync_playwright")
    def test_falla_todos_los_navegadores_eleva_runtime_error(self, mock_sync_pw):
        """Si todos los navegadores de la cascada fallan, debe elevar RuntimeError con la cascada."""
        mock_pw = MagicMock()
        mock_sync_pw.return_value.start.return_value = mock_pw

        mock_pw.firefox.launch.side_effect = Exception("Fallo Firefox")
        mock_pw.chromium.launch.side_effect = Exception("Fallo Chromium/Chrome")

        with self.assertRaises(RuntimeError) as ctx:
            obtener_contexto_playwright(headless=True, navegador="firefox")

        self.assertIn("No se pudo iniciar ningún navegador de la cascada", str(ctx.exception))


class TestAutomatizadorWebUnificacion(unittest.TestCase):
    """Prueba que el automatizador web delega en la factoría central."""

    @patch("modulos.automatizador_web.obtener_contexto_playwright")
    def test_iniciar_contexto_playwright_delega_en_factoria(self, mock_obtener):
        """iniciar_contexto_playwright debe llamar a obtener_contexto_playwright de driver_factory."""
        mock_pw = MagicMock()
        mock_context = MagicMock()
        mock_obtener.return_value = (mock_pw, mock_context)

        pw, context = iniciar_contexto_playwright(
            user_data_dir="ruta_data",
            headless=True,
            navegador="edge"
        )

        mock_obtener.assert_called_once_with(
            headless=True,
            navegador="edge",
            user_data_dir="ruta_data"
        )
        self.assertEqual(pw, mock_pw)
        self.assertEqual(context, mock_context)


class TestWindowsBatSintaxis(unittest.TestCase):
    """Verifica que el script windows.bat no contenga errores sintácticos de parsing en cmd.exe."""

    def test_windows_bat_sin_parentesis_peligrosos_en_bloques(self):
        """windows.bat no debe tener paréntesis sin escapar que rompan bloques if de cmd.exe."""
        import os
        ruta_bat = os.path.join(os.path.dirname(__file__), "..", "windows.bat")
        with open(ruta_bat, "r", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()

        # Verificar que no exista el error de eco con paréntesis que rompa bloques
        self.assertNotIn("(sin limite de tiempo)...", contenido)
        # Verificar que el salto lineal a deps_ready esté presente
        self.assertIn("goto :deps_ready", contenido)
        # Verificar CRLF estricto
        raw = open(ruta_bat, "rb").read()
        self.assertIn(b"\r\n", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


if __name__ == "__main__":
    unittest.main()
