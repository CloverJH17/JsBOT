#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas nuevas de contratos operativos: configuración, versionado y privacidad.

Estas pruebas no usan red, credenciales reales ni archivos de producción.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modulos import config_manager as cm
from modulos.version import ETIQUETA_VERSION, __version__

BASE_DIR = Path(__file__).resolve().parent.parent


class TestConfiguracionAtomica(unittest.TestCase):
    """Los tres JSON de configuración deben ser tolerantes a cortes de energía."""

    def _ruta(self, directory, name):
        return str(Path(directory) / name)

    def test_settings_usa_os_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = self._ruta(tmp, "settings.json")
            with open(ruta, "w", encoding="utf-8") as handle:
                json.dump({"app": {"version": __version__}}, handle)

            with patch.object(cm.os, "replace", wraps=os.replace) as replace:
                self.assertTrue(cm.guardar_settings({"browser": {"priority": ["chrome"]}}, ruta=ruta))

            replace.assert_called_once()
            self.assertEqual(cm.cargar_settings(ruta)["browser"]["priority"], ["chrome"])

    def test_config_servicios_usa_os_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = self._ruta(tmp, "config_servicios.json")
            with patch.object(cm.os, "replace", wraps=os.replace) as replace:
                self.assertTrue(cm.guardar_config_servicios({"catalogo_servicios": ["Prueba"]}, ruta=ruta))

            replace.assert_called_once()
            self.assertEqual(cm.cargar_config_servicios(ruta)["catalogo_servicios"], ["Prueba"])

    def test_datos_actividad_usa_os_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = self._ruta(tmp, "datos_actividad.json")
            with patch.object(cm.os, "replace", wraps=os.replace) as replace:
                self.assertTrue(cm.guardar_datos_actividad({"modulo": "Prueba"}, ruta=ruta))

            replace.assert_called_once()
            self.assertEqual(cm.cargar_datos_actividad(ruta)["modulo"], "Prueba")


class TestManifestVersionYPrivacidad(unittest.TestCase):
    """El release debe ser coherente y no reintroducir telemetría remota."""

    def test_manifest_principal_conserva_version_unica(self):
        settings = json.loads((BASE_DIR / "config" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["app"]["version"], __version__)
        self.assertEqual(ETIQUETA_VERSION, f"v{__version__}")

        for relative in ("README.md", "docs/PROJECT.md"):
            self.assertIn(
                f"v{__version__}",
                (BASE_DIR / relative).read_text(encoding="utf-8")[:500],
                f"La cabecera de {relative} no refleja la versión actual",
            )

        for relative in ("docs/version.txt", "docs/historial/version.txt"):
            self.assertIn(f"[{ETIQUETA_VERSION}]", (BASE_DIR / relative).read_text(encoding="utf-8"))

    def test_lanzadores_consumen_version_dinamica(self):
        assert_contains = lambda relative, *tokens: self.assertTrue(
            all(token in (BASE_DIR / relative).read_text(encoding="utf-8") for token in tokens),
            f"{relative} debe mantener versión dinámica",
        )
        assert_contains("install.ps1", "ETIQUETA_VERSION")
        assert_contains("install.sh", "APP_VERSION", "ETIQUETA_VERSION")
        assert_contains("scripts/instalar.sh", "VERSION", "ETIQUETA_VERSION")

    def test_no_existe_telemetria_remota_en_superficie_operativa(self):
        self.assertFalse((BASE_DIR / "modulos" / "telemetria.py").exists())
        settings = json.loads((BASE_DIR / "config" / "settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("telemetria", settings)

        for relative in ("main.py", "install.ps1", "install.sh", "uninstall.ps1", "uninstall.sh"):
            text = (BASE_DIR / relative).read_text(encoding="utf-8")
            self.assertNotIn("registrar_evento", text)
            self.assertNotIn("script.google.com", text)

    def test_dependencias_de_pruebas_estan_declaradas(self):
        requirements = (BASE_DIR / "config" / "requirements.txt").read_text(encoding="utf-8")
        self.assertRegex(requirements, r"(?m)^pytest[>=]", "pytest debe estar declarado para la suite")
        self.assertRegex(requirements, r"(?m)^pytest-mock[>=]", "pytest-mock debe estar declarado para la suite")


if __name__ == "__main__":
    unittest.main(verbosity=2)
