#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SUITE: BLINDAJE TÉCNICO Y REFACTORIZACIÓN v5.1.0
Valida:
1. Sanitización de constructores SQL contra inyección.
2. Centralización de clasificación institucional de actividades.
3. Desacoplamiento y existencia de crawlers de auditoría (sin ciclos circulares).
4. Recuperación resiliente de checkpoints desde SQLite ante JSON corrupto.
"""

import unittest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

from modulos.motor_export_auditoria import (
    sanitizar_texto_sql,
    validar_codigo_sql,
    validar_fecha_sql,
    clasificar_actividad_datos
)
from modulos.auditor_reportes import (
    obtener_tipo_clasificacion_actividad,
    consultar_actividades_infoapp_http_crawler,
    consultar_servicios_infoapp_http_crawler
)
import modulos.gestor_sesion as gs


class TestSanitizacionSQL(unittest.TestCase):
    def test_sanitizar_texto_sql_comillas_y_comentarios(self):
        resultado = sanitizar_texto_sql("Yaracuy' OR '1'='1")
        self.assertEqual(resultado, "Yaracuy OR 11")
        self.assertNotIn("'", resultado)
        self.assertNotIn(";", resultado)
        self.assertNotIn("--", resultado)
        self.assertEqual(sanitizar_texto_sql("Lara; DROP TABLE reports;--"), "Lara DROP TABLE reports")
        self.assertEqual(sanitizar_texto_sql(""), "")
        self.assertEqual(sanitizar_texto_sql(None), "")

    def test_validar_codigo_sql(self):
        self.assertEqual(validar_codigo_sql("YAR01' OR 1=1--"), "YAR01OR11")
        self.assertEqual(validar_codigo_sql("INF-123_45"), "INF-123_45")
        self.assertEqual(validar_codigo_sql(""), "")

    def test_validar_fecha_sql(self):
        self.assertEqual(validar_fecha_sql("2026-09-23"), "2026-09-23")
        self.assertEqual(validar_fecha_sql("2026-09-23' OR 1=1"), "")
        self.assertEqual(validar_fecha_sql("mal_formato"), "")


class TestClasificacionCentralizada(unittest.TestCase):
    def test_formaciones(self):
        act = {
            "dimensiones": "Comunidades de aprendizaje y robótica básica",
            "taller": "Robótica Educativa",
            "productos": 0
        }
        self.assertEqual(obtener_tipo_clasificacion_actividad(act), "formacion")
        self.assertEqual(act.get("tipo_clasificacion"), "formacion")

    def test_productos(self):
        act = {
            "dimensiones": "Producción de contenido digital",
            "taller": "Diseño Gráfico",
            "productos": 2
        }
        self.assertEqual(obtener_tipo_clasificacion_actividad(act), "producto")
        self.assertEqual(act.get("tipo_clasificacion"), "producto")

    def test_otras_actividades(self):
        act = {
            "dimensiones": "Reunión de coordinación comunitaria",
            "taller": "Encuentro de voceros",
            "productos": 0
        }
        self.assertEqual(obtener_tipo_clasificacion_actividad(act), "otra")
        self.assertEqual(act.get("tipo_clasificacion"), "otra")


class TestDesacoplamientoCrawlers(unittest.TestCase):
    def test_crawlers_existen_y_son_invocables(self):
        self.assertTrue(callable(consultar_actividades_infoapp_http_crawler))
        self.assertTrue(callable(consultar_servicios_infoapp_http_crawler))

    def test_export_fallback_invoca_crawler_sin_import_error(self):
        from modulos.motor_export_auditoria import consultar_actividades_infoapp_export
        fake_session = MagicMock()
        fake_resp = MagicMock()
        fake_resp.status_code = 500
        fake_session.get.return_value = fake_resp

        with patch("modulos.auditor_reportes.consultar_actividades_infoapp_http_crawler", return_value=(0, [])) as mock_crawler:
            total, acts = consultar_actividades_infoapp_export(fake_session, info_id="TEST", uid="100", estado="YAR")
            self.assertEqual(total, 0)
            self.assertEqual(acts, [])
            mock_crawler.assert_called_once()


class TestRecuperacionCheckpointsResiliente(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_checkpoints.db")
        self.json_form = os.path.join(self.tmpdir, "estado_sesion.json")
        self.json_serv = os.path.join(self.tmpdir, "estado_sesion_servicios.json")

    def tearDown(self):
        for f in (self.db_path, self.json_form, self.json_serv):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass

    def test_recupera_de_sqlite_cuando_json_falta(self):
        # Asegurar que el archivo JSON no exista
        if os.path.exists(self.json_form):
            os.remove(self.json_form)

        # Guardar en SQLite un checkpoint válido
        datos_validos = {
            "id_actividad": "ACT-123",
            "indice_ultimo_procesado": 1,
            "participantes": [{"nombre": "Ana"}, {"nombre": "Luis"}]
        }
        gs.guardar_checkpoint_db(
            id_actividad="ACT-123",
            indice=1,
            cedula="V123",
            estado="EN_PROCESO",
            tipo="formacion",
            datos_json=json.dumps(datos_validos),
            db_path=self.db_path
        )

        with patch.object(gs, "SESSION_STATE_FILE", self.json_form), \
             patch.object(gs, "DB_FILE", self.db_path):
            recuperado = gs.leer_estado_sesion()
            self.assertIsNotNone(recuperado)
            self.assertEqual(recuperado.get("id_actividad"), "ACT-123")
            self.assertEqual(recuperado.get("indice_ultimo_procesado"), 1)
            self.assertEqual(len(recuperado.get("participantes")), 2)


if __name__ == "__main__":
    unittest.main()
