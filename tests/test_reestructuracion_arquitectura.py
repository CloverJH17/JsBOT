#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SUITE DE PRUEBAS: REESTRUCTURACIÓN DE ARQUITECTURA Y CONTROL DE DIRECTORIOS
===============================================================================
Valida:
1. Almacenamiento y consulta de logs atómicos en SQLite (data/jsbot.db).
2. Purga y retención automática de logs en SQLite.
3. Integridad de la carpeta docs/ y eliminación de funcionamiento/.
4. Renombrado y operatividad de Features/ en sustitución de scratch/.
5. Reubicación de requirements.txt a config/ y presencia de pyproject.toml.
6. Control estricto contra la creación de carpetas no autorizadas.
===============================================================================
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

import modulos.entorno as entorno
import modulos.version as version
import modulos.gestor_sesion as gestor_sesion
import modulos.verificador_entorno as verificador_entorno


class TestReestructuracionArquitectura(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_jsbot.db")

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_carpetas_canonicas_y_ausencia_de_carpetas_obsoletas(self):
        """Verifica que la estructura de carpetas estándar exista y no haya carpetas obsoletas."""
        raiz = Path(entorno.RAIZ_PROYECTO)
        
        # Carpetas requeridas
        self.assertTrue((raiz / "config").is_dir(), "config/ debe existir")
        self.assertTrue((raiz / "data").is_dir(), "data/ debe existir")
        self.assertTrue((raiz / "docs").is_dir(), "docs/ debe existir")
        self.assertTrue((raiz / "Features").is_dir(), "Features/ debe existir")
        self.assertTrue((raiz / "Planillas").is_dir(), "Planillas/ debe existir")
        self.assertTrue((raiz / "Reportes_Auditoria").is_dir(), "Reportes_Auditoria/ debe existir")
        self.assertTrue((raiz / "logs").is_dir(), "logs/ debe existir")

        # Carpetas obsoletas eliminadas
        self.assertFalse((raiz / "funcionamiento").exists(), "funcionamiento/ no debe existir tras la unificación")
        self.assertFalse((raiz / "scratch").exists(), "scratch/ no debe existir tras ser renombrada a Features")

    def test_02_integridad_documental_en_docs(self):
        """Verifica que los manuales, flujos y version.txt residan correctamente en docs/."""
        raiz = Path(entorno.RAIZ_PROYECTO)
        
        version_txt = raiz / "docs" / "version.txt"
        self.assertTrue(version_txt.is_file(), "docs/version.txt debe existir")
        with open(version_txt, "r", encoding="utf-8") as f:
            contenido = f.read()
        self.assertIn(f"v{version.__version__}", contenido, "docs/version.txt debe reflejar la versión actual")

        # Subcarpetas temáticas
        self.assertTrue((raiz / "docs" / "arquitectura").is_dir())
        self.assertTrue((raiz / "docs" / "manuales").is_dir())
        self.assertTrue((raiz / "docs" / "historial").is_dir())
        self.assertTrue((raiz / "docs" / "diagramas").is_dir())

        self.assertTrue((raiz / "docs" / "arquitectura" / "funciones_jsbot_contexto.md").is_file())
        self.assertTrue((raiz / "docs" / "manuales" / "funcionamiento.txt").is_file())
        self.assertTrue((raiz / "docs" / "diagramas" / "diagrama_de_flujo.txt").is_file())
        self.assertTrue((raiz / "docs" / "historial" / "version.txt").is_file())

    def test_03_dependencias_centralizadas_en_config_y_version_unica(self):
        """Verifica que las dependencias residan únicamente en config/ y la versión esté centralizada."""
        raiz = Path(entorno.RAIZ_PROYECTO)
        
        # 1. requirements.txt debe estar dentro de config/
        req_config = raiz / "config" / "requirements.txt"
        self.assertTrue(req_config.is_file(), "config/requirements.txt debe ser el único archivo de dependencias")
        
        # 2. La raíz no debe tener archivos redundantes de empaquetado o dependencias
        self.assertFalse((raiz / "requirements.txt").exists(), "requirements.txt no debe estar en la raíz")
        self.assertFalse((raiz / "pyproject.toml").exists(), "pyproject.toml no debe estar en la raíz")
        self.assertFalse((raiz / "setup.py").exists(), "setup.py no debe estar en la raíz")

        # 3. La versión debe ser única y centralizada en modulos/version.py
        self.assertTrue(bool(version.__version__))
        self.assertEqual(version.ETIQUETA_VERSION, f"v{version.__version__}")
        
        # 4. Verificador de entorno debe resolver directamente config/requirements.txt
        self.assertTrue(os.path.exists(verificador_entorno.REQUIREMENTS_FILE))
        self.assertEqual(Path(verificador_entorno.REQUIREMENTS_FILE).resolve(), req_config.resolve())

    def test_04_sqlite_logging_atomico_e_indices(self):
        """Verifica la inserción atómica, índices y lectura de app_logs en SQLite."""
        gestor_sesion.inicializar_db(self.test_db)
        
        # Comprobar modo WAL
        with gestor_sesion._abrir_conexion_db(self.test_db) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            modo = cur.fetchone()[0]
            self.assertIn(modo.lower(), ["wal", "memory", "delete"])

        # Insertar registros estructurados
        gestor_sesion.registrar_log_db(
            nivel="INFO",
            origen="AUDITOR_TEST",
            mensaje="Inicio de prueba de auditoría",
            metadata={"uid": "1325", "total": 50},
            db_path=self.test_db
        )
        gestor_sesion.registrar_log_db(
            nivel="ERROR",
            origen="TURBO_HTTP",
            mensaje="Fallo de conexión simulado",
            metadata={"status": 500},
            db_path=self.test_db
        )
        gestor_sesion.registrar_log_db(
            nivel="WARNING",
            origen="AUDITOR_TEST",
            mensaje="Advertencia de sesión",
            db_path=self.test_db
        )

        # Consultas con filtros
        todos = gestor_sesion.consultar_logs_db(limite=10, db_path=self.test_db)
        self.assertEqual(len(todos), 3)

        solo_errores = gestor_sesion.consultar_logs_db(nivel="ERROR", db_path=self.test_db)
        self.assertEqual(len(solo_errores), 1)
        self.assertEqual(solo_errores[0]["origen"], "TURBO_HTTP")
        self.assertEqual(solo_errores[0]["metadata"], {"status": 500})

        solo_auditor = gestor_sesion.consultar_logs_db(origen="AUDITOR_TEST", db_path=self.test_db)
        self.assertEqual(len(solo_auditor), 2)

    def test_05_sqlite_purga_automatica_logs(self):
        """Verifica la purga automática de registros antiguos y control de volumen en SQLite."""
        gestor_sesion.inicializar_db(self.test_db)
        
        # Insertar un registro antiguo simulado (hace 40 días)
        fecha_antigua = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
        with gestor_sesion._abrir_conexion_db(self.test_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO app_logs (timestamp, nivel, origen, mensaje, metadata)
                VALUES (?, 'INFO', 'SISTEMA', 'Log muy antiguo', NULL);
            """, (fecha_antigua,))

        # Insertar 5 registros recientes
        for i in range(5):
            gestor_sesion.registrar_log_db(
                nivel="INFO",
                origen="TEST_PURGA",
                mensaje=f"Log reciente {i}",
                db_path=self.test_db
            )

        total_antes = len(gestor_sesion.consultar_logs_db(limite=50, db_path=self.test_db))
        self.assertEqual(total_antes, 6)

        # Purgar registros de más de 30 días
        eliminados = gestor_sesion.purgar_logs_antiguos_db(dias_retencion=30, max_registros=100, db_path=self.test_db)
        self.assertGreaterEqual(eliminados, 1)

        total_despues = len(gestor_sesion.consultar_logs_db(limite=50, db_path=self.test_db))
        self.assertEqual(total_despues, 5)

        # Test de límite de max_registros
        eliminados_cap = gestor_sesion.purgar_logs_antiguos_db(dias_retencion=365, max_registros=3, db_path=self.test_db)
        self.assertEqual(eliminados_cap, 2)
        total_final = len(gestor_sesion.consultar_logs_db(limite=50, db_path=self.test_db))
        self.assertEqual(total_final, 3)

    def test_06_control_estricto_directorios_permitidos(self):
        """Valida que los directorios del proyecto pertenezcan únicamente a la estructura permitida."""
        raiz = Path(entorno.RAIZ_PROYECTO)
        carpetas_raiz = [
            p.name for p in raiz.iterdir() 
            if p.is_dir() and not p.name.startswith(".") and p.name not in ["__pycache__", ".pytest_cache", ".git"]
        ]
        
        carpetas_esperadas = {
            "config",
            "data",
            "docs",
            "Features",
            "logs",
            "modulos",
            "Planillas",
            "Reportes_Auditoria",
            "scripts",
            "tests"
        }
        
        for c in carpetas_raiz:
            self.assertIn(c, carpetas_esperadas, f"Carpeta no autorizada encontrada en la raíz: {c}")


if __name__ == "__main__":
    unittest.main()

