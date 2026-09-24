#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST SUITE: INSTALADORES AUTÓNOMOS Y VERIFICACIÓN DE PRIVACIDAD / SEMVER
===============================================================================
Pruebas unitarias para:
1. Coherencia SemVer dinámica entre modulos/version.py, settings.json y docs.
2. Integridad de los instaladores autónomos y desinstaladores (Windows y Linux).
3. Verificación de privacidad: ausencia total de módulos o hooks de telemetría remota.
===============================================================================
"""

import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.version import __version__, ETIQUETA_VERSION


class TestInstaladoresYVersion(unittest.TestCase):

    def test_coherencia_version_dinamica(self):
        """Valida la coherencia estricta de versión entre version.py, settings.json y docs."""
        self.assertTrue(__version__, "La versión no debe estar vacía")
        self.assertEqual(ETIQUETA_VERSION, f"v{__version__}")

        # 1. settings.json
        settings_path = os.path.join(BASE_DIR, "config", "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertEqual(settings["app"]["version"], __version__)

        # 2. docs/version.txt
        docs_path = os.path.join(BASE_DIR, "docs", "version.txt")
        with open(docs_path, "r", encoding="utf-8") as f:
            docs_content = f.read()
        self.assertIn(f"[{ETIQUETA_VERSION}]", docs_content)

    def test_archivos_instaladores_existencia_y_estructura(self):
        """Valida la presencia y estructura esencial de los instaladores y desinstaladores."""
        # 1. install.ps1
        ps1_path = os.path.join(BASE_DIR, "install.ps1")
        self.assertTrue(os.path.exists(ps1_path))
        with open(ps1_path, "r", encoding="utf-8") as f:
            ps1_content = f.read()
        self.assertIn("$InstallDir", ps1_content)
        self.assertIn("JsBOT.lnk", ps1_content)
        self.assertIn("jsbot.cmd", ps1_content)

        # 2. install.sh
        sh_path = os.path.join(BASE_DIR, "install.sh")
        self.assertTrue(os.path.exists(sh_path))
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertIn("INSTALL_DIR", sh_content)
        self.assertIn("jsbot.desktop", sh_content)
        self.assertIn("~/.local/bin/jsbot", sh_content)

        # 3. scripts/instalar.sh
        instalar_sh_path = os.path.join(BASE_DIR, "scripts", "instalar.sh")
        self.assertTrue(os.path.exists(instalar_sh_path))
        with open(instalar_sh_path, "r", encoding="utf-8") as f:
            instalar_content = f.read()
        self.assertIn("ETIQUETA_VERSION", instalar_content)

        # 4. uninstall.ps1 & uninstall.sh
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "uninstall.ps1")))
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "uninstall.sh")))

    def test_ausencia_total_telemetria_remota(self):
        """Valida que la telemetría remota esté completamente eliminada por privacidad y seguridad."""
        # 1. El módulo telemetria.py no debe existir
        telemetria_py = os.path.join(BASE_DIR, "modulos", "telemetria.py")
        self.assertFalse(os.path.exists(telemetria_py), "modulos/telemetria.py debe haber sido eliminado")

        # 2. settings.json no debe tener sección de telemetría
        settings_path = os.path.join(BASE_DIR, "config", "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertNotIn("telemetria", settings, "settings.json no debe contener sección telemetria")

        # 3. Ni install ni uninstall deben invocar telemetria
        for fname in ["install.ps1", "install.sh", "uninstall.ps1", "uninstall.sh", "main.py"]:
            fpath = os.path.join(BASE_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("from modulos.telemetria", content, f"{fname} no debe importar telemetria")
            self.assertNotIn("registrar_evento", content, f"{fname} no debe invocar eventos de telemetria")


if __name__ == "__main__":
    unittest.main()
