#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST SUITE: INSTALADORES ONE-LINE Y TELEMETRÍA CLOUD (JsBOT v5.1.0)
===============================================================================
Pruebas unitarias para:
1. Recolección de metadatos de sistema e identificación de máquina.
2. Tolerancia a fallos offline y resiliencia asíncrona de telemetría.
3. Coherencia SemVer triple (version.py, settings.json, docs/version.txt).
4. Integridad de los instaladores autónomos y desinstaladores (Windows y Linux).
===============================================================================
"""

import os
import sys
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.version import __version__
from modulos.telemetria import (
    obtener_identificador_maquina,
    obtener_metadatos_sistema,
    despachar_evento_asincrono,
    registrar_evento_instalacion,
    registrar_evento_inicio,
    registrar_evento_desinstalacion
)

class TestInstaladoresYTelemetria(unittest.TestCase):
    
    def test_metadatos_sistema_completitud(self):
        """Valida que la recolección de metadatos del sistema sea completa y segura."""
        meta = obtener_metadatos_sistema()
        
        campos_requeridos = [
            "marca_temporal",
            "id_maquina",
            "equipo",
            "usuario",
            "sistema_operativo",
            "version_jsbot",
            "python_version"
        ]
        for campo in campos_requeridos:
            self.assertIn(campo, meta, f"El campo {campo} debe estar presente en los metadatos")
            self.assertIsNotNone(meta[campo], f"El campo {campo} no puede ser nulo")
        
        self.assertEqual(meta["version_jsbot"], "v5.2.0")

    def test_identificador_maquina_estabilidad(self):
        """Valida que el identificador anónimo de máquina sea consistente y tenga formato hash."""
        id1 = obtener_identificador_maquina()
        id2 = obtener_identificador_maquina()
        self.assertEqual(id1, id2)
        self.assertGreaterEqual(len(id1), 8)

    def test_telemetria_tolerancia_fallos_offline(self):
        """Valida que el envío de eventos sea 100% tolerante a fallos de red sin excepciones."""
        try:
            despachar_evento_asincrono("TEST_OFFLINE", "Simulación sin internet", url_override="http://127.0.0.1:59999/dummy")
            registrar_evento_instalacion(url_override="http://127.0.0.1:59999/dummy")
            registrar_evento_inicio(modo="TEST")
            registrar_evento_desinstalacion(url_override="http://127.0.0.1:59999/dummy")
        except Exception as e:
            self.fail(f"La telemetría no debe arrojar excepciones ante fallas de red: {e}")

    def test_coherencia_version_triple_v5(self):
        """Valida la coherencia estricta de versión v5.2.0 entre version.py, settings.json y docs."""
        # 1. version.py
        self.assertEqual(__version__, "5.2.0")
        
        # 2. settings.json
        settings_path = os.path.join(BASE_DIR, "config", "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        self.assertEqual(settings["app"]["version"], "5.2.0")
        self.assertIn("telemetria", settings)
        self.assertTrue(settings["telemetria"]["activa"])
        
        # 3. docs/version.txt
        docs_path = os.path.join(BASE_DIR, "docs", "version.txt")
        with open(docs_path, "r", encoding="utf-8") as f:
            docs_content = f.read()
        self.assertIn("[v5.2.0]", docs_content)

    def test_archivos_instaladores_existencia_y_estructura(self):
        """Valida la presencia y estructura esencial de los instaladores y desinstaladores."""
        # 1. install.ps1
        ps1_path = os.path.join(BASE_DIR, "install.ps1")
        self.assertTrue(os.path.exists(ps1_path))
        with open(ps1_path, "r", encoding="utf-8") as f:
            ps1_content = f.read()
        self.assertIn("JsBOT RPA v5.2.0", ps1_content)
        self.assertIn("$InstallDir", ps1_content)
        self.assertIn("JsBOT.lnk", ps1_content)
        self.assertIn("jsbot.cmd", ps1_content)
        
        # 2. install.sh
        sh_path = os.path.join(BASE_DIR, "install.sh")
        self.assertTrue(os.path.exists(sh_path))
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertIn("JsBOT RPA v5.2.0", sh_content)
        self.assertIn("INSTALL_DIR", sh_content)
        self.assertIn("jsbot.desktop", sh_content)
        self.assertIn("~/.local/bin/jsbot", sh_content)
        
        # 3. uninstall.ps1 & uninstall.sh
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "uninstall.ps1")))
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "uninstall.sh")))
        
        # 4. docs/telemetria_google_sheets.md
        self.assertTrue(os.path.exists(os.path.join(BASE_DIR, "docs", "telemetria_google_sheets.md")))

if __name__ == "__main__":
    unittest.main()
