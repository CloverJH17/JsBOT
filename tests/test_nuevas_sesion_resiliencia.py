#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de persistencia, recuperación y resiliencia de SQLite."""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modulos import gestor_sesion as gs


class TestSesionResilienciaNueva(unittest.TestCase):
    def test_esquema_sqlite_tiene_indices_esperados(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "jsbot.db")
            gs.inicializar_db(db)
            conn = sqlite3.connect(db)
            try:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                indexes = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            finally:
                conn.close()
            self.assertTrue({"checkpoints", "inscritos_historico", "app_logs"}.issubset(tables))
            self.assertIn("idx_checkpoints_actividad", indexes)
            self.assertIn("idx_historico_cedula", indexes)
            self.assertIn("idx_app_logs_ts", indexes)

    def test_checkpoint_json_corrupto_recurre_a_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = str(root / "jsbot.db")
            json_path = root / "session_state.json"
            json_path.write_text("{no es json", encoding="utf-8")
            datos = {
                "id_actividad": "123",
                "indice_ultimo_procesado": 1,
                "participantes": [{"nombre": "Ana"}, {"nombre": "Luis"}],
            }
            gs.guardar_checkpoint_db(
                id_actividad="123",
                indice=1,
                tipo="formacion",
                datos_json=json.dumps(datos),
                db_path=db,
            )

            with patch.object(gs, "DB_FILE", db), patch.object(gs, "SESSION_STATE_FILE", str(json_path)):
                recuperado = gs.leer_estado_sesion()

            self.assertIsNotNone(recuperado)
            self.assertEqual(recuperado["id_actividad"], "123")
            self.assertEqual(recuperado["indice_ultimo_procesado"], 1)

    def test_checkpoint_json_se_escribe_atomically_y_no_deja_temporal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = str(root / "jsbot.db")
            json_path = root / "session_state.json"
            config = {"id_actividad": "456", "usuario": "test", "url": "https://example.test"}
            participantes = [{"nombre": "Ana", "cedula": "25123456"}, {"nombre": "Luis", "cedula": "26123457"}]

            with patch.object(gs, "DB_FILE", db), patch.object(gs, "SESSION_STATE_FILE", str(json_path)):
                gs.guardar_estado_sesion(config, participantes, 1)
                self.assertTrue(json_path.exists())
                self.assertFalse((root / "session_state.json.tmp").exists())
                self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["indice_ultimo_procesado"], 1)

    def test_historico_filtra_por_actividad_y_cedula(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "jsbot.db")
            gs.registrar_inscrito_historico_db("A1", "11111111", "Ana", "04120000000", db_path=db)
            gs.registrar_inscrito_historico_db("A2", "22222222", "Luis", "04120000001", db_path=db)
            por_actividad = gs.consultar_inscritos_historico_db(id_actividad="A1", db_path=db)
            por_cedula = gs.consultar_inscritos_historico_db(cedula="22222222", db_path=db)
            self.assertEqual(len(por_actividad), 1)
            self.assertEqual(por_actividad[0]["cedula"], "11111111")
            self.assertEqual(len(por_cedula), 1)
            self.assertEqual(por_cedula[0]["id_actividad"], "A2")

    def test_purga_respeta_retencion_y_tope(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "jsbot.db")
            gs.inicializar_db(db)
            conn = sqlite3.connect(db)
            try:
                conn.execute("INSERT INTO app_logs(timestamp,nivel,origen,mensaje) VALUES (datetime('now','-45 days'),'INFO','test','viejo')")
                for index in range(4):
                    conn.execute("INSERT INTO app_logs(timestamp,nivel,origen,mensaje) VALUES (datetime('now'),'INFO','test',?)", (f"nuevo-{index}",))
                conn.commit()
            finally:
                conn.close()
            eliminados = gs.purgar_logs_antiguos_db(dias_retencion=30, max_registros=3, db_path=db)
            restantes = gs.consultar_logs_db(limite=10, db_path=db)
            self.assertGreaterEqual(eliminados, 2)
            self.assertEqual(len(restantes), 3)
            self.assertNotIn("viejo", [row["mensaje"] for row in restantes])


if __name__ == "__main__":
    unittest.main(verbosity=2)
