#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de instaladores, lanzadores, AST y documentación."""
import ast
import re
import unittest
from pathlib import Path

from modulos.version import ETIQUETA_VERSION, __version__

BASE_DIR = Path(__file__).resolve().parent.parent


class TestInstaladoresDocumentacionNueva(unittest.TestCase):
    def test_todos_los_modulos_python_compilan_ast(self):
        for path in sorted((BASE_DIR / "modulos").glob("*.py")):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        ast.parse((BASE_DIR / "main.py").read_text(encoding="utf-8"), filename="main.py")

    def test_no_se_reintroducen_hooks_de_telemetria(self):
        for path in [BASE_DIR / "main.py", *sorted((BASE_DIR / "modulos").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path.relative_to(BASE_DIR))):
                self.assertNotIn("from modulos.telemetria", text)
                self.assertNotIn("registrar_evento_inicio", text)
                self.assertNotIn("registrar_evento_instalacion", text)

    def test_tls_no_se_desactiva_en_superficie_operativa(self):
        for path in [BASE_DIR / "main.py", *sorted((BASE_DIR / "modulos").glob("*.py"))]:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("verify=False", text)
                self.assertNotIn("disable_warnings", text)

    def test_instaladores_conservan_estructura_y_version_dinamica(self):
        powershell = (BASE_DIR / "install.ps1").read_text(encoding="utf-8")
        shell = (BASE_DIR / "install.sh").read_text(encoding="utf-8")
        script = (BASE_DIR / "scripts" / "instalar.sh").read_text(encoding="utf-8")
        self.assertIn("$InstallDir", powershell)
        self.assertIn("jsbot.cmd", powershell)
        self.assertIn("INSTALL_DIR", shell)
        self.assertIn("jsbot.desktop", shell)
        self.assertIn("ETIQUETA_VERSION", script)
        self.assertNotIn("v5.2.0", powershell + shell + script)

    def test_documentacion_actual_tiene_version_corriente(self):
        self.assertIn(f"v{__version__}", (BASE_DIR / "README.md").read_text(encoding="utf-8")[:300])
        self.assertIn(f"v{__version__}", (BASE_DIR / "docs" / "PROJECT.md").read_text(encoding="utf-8")[:300])
        self.assertIn(f"[{ETIQUETA_VERSION}]", (BASE_DIR / "docs" / "version.txt").read_text(encoding="utf-8"))
        self.assertIn(f"[{ETIQUETA_VERSION}]", (BASE_DIR / "docs" / "historial" / "version.txt").read_text(encoding="utf-8"))

    def test_requirements_declaran_herramientas_de_test(self):
        text = (BASE_DIR / "config" / "requirements.txt").read_text(encoding="utf-8")
        for package in ("pytest", "pytest-mock"):
            self.assertRegex(text, rf"(?m)^{re.escape(package)}[>=]")

    def test_no_hay_referencias_operativas_a_telemetria_remota(self):
        operational = [
            BASE_DIR / "main.py",
            BASE_DIR / "install.ps1",
            BASE_DIR / "install.sh",
            BASE_DIR / "uninstall.ps1",
            BASE_DIR / "uninstall.sh",
            BASE_DIR / "config" / "settings.json",
        ]
        for path in operational:
            with self.subTest(path=path.name):
                self.assertNotIn("script.google.com", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
