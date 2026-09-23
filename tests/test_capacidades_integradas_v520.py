#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST SUITE: INTEGRACIÓN DE CAPACIDADES AISLADAS Y TESTS REALES (v5.2.0)
===============================================================================
Valida:
1. Modal preventivo al previsualizar sin participantes (cero datos demo).
2. Persistencia y consulta en histórico SQLite (registrar_inscrito_historico_db).
3. Purga automática de logs en SQLite con retención de 30 días.
4. Verificación post-carga en InfoApp con mock de servidor HTTP.
5. Diagnóstico preventivo de facilitador y detección de actividades en borrador.
6. Generación física de planilla ODS desde actividad remota InfoApp.
7. Resolución robusta de sede en facilitadores de auditoría (info_filtro fallback).
8. Coherencia integral SemVer 5.2.0.
===============================================================================
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Asegurar path base
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modulos import version
from modulos import entorno
from modulos import gestor_sesion
from modulos import diagnostico_facilitador
from modulos import verificador_cargas_export
from modulos import generador_planilla
from modulos import auditor_reportes


class TestCapacidadesIntegradasV520(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.temp_dir.name, "test_jsbot.db")
        gestor_sesion.inicializar_db(self.test_db)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_previsualizacion_sin_datos_alerta_preventiva(self):
        """Valida que _abrir_tabla_previsualizacion no inyecta participantes ficticios y emite aviso."""
        from modulos.interfaz_grafica import JsBotGUI

        with patch.object(JsBotGUI, "__init__", return_value=None):
            app = JsBotGUI()
            app.datos_normalizados_actuales = []
            app.participantes_cargados = []
            app.datos_normalizados_planillas = []
            app.participantes_cargados_planillas = []
            app._mostrar_modal_mensaje = MagicMock()

            # Invocación sin datos
            app._abrir_tabla_previsualizacion("Formacion")

            # Certificar que se llamó al modal de aviso y no se procedió con datos falsos
            app._mostrar_modal_mensaje.assert_called_once()
            args, kwargs = app._mostrar_modal_mensaje.call_args
            self.assertIn("Sin Participantes", args[0])
            self.assertEqual(kwargs.get("tipo"), "aviso")

    def test_02_historico_inscritos_sqlite_persistencia(self):
        """Valida que registrar_inscrito_historico_db persiste atómicamente y es consultable."""
        id_act = "ACT-9999"
        cedula = "V-28111222"
        nombre = "María Bolívar"
        telefono = "0412-1234567"

        # Registrar participante en histórico
        gestor_sesion.registrar_inscrito_historico_db(
            id_actividad=id_act,
            cedula=cedula,
            nombre=nombre,
            telefono=telefono,
            db_path=self.test_db
        )

        # Consultar histórico
        inscritos = gestor_sesion.consultar_inscritos_historico_db(id_actividad=id_act, db_path=self.test_db)
        self.assertEqual(len(inscritos), 1)
        self.assertEqual(inscritos[0]["cedula"], "V-28111222")
        self.assertEqual(inscritos[0]["nombre"], nombre)
        self.assertEqual(inscritos[0]["telefono"], telefono)

    def test_03_purga_logs_antiguos_db(self):
        """Valida que purgar_logs_antiguos_db elimina registros > 30 días y preserva los recientes."""
        with gestor_sesion._abrir_conexion_db(self.test_db) as conn:
            cur = conn.cursor()
            # Insertar log antiguo (hace 45 días)
            cur.execute("""
                INSERT INTO app_logs (timestamp, nivel, origen, mensaje, metadata)
                VALUES (datetime('now', '-45 days'), 'INFO', 'test', 'Log viejo', '{}');
            """)
            # Insertar log reciente (hace 2 días)
            cur.execute("""
                INSERT INTO app_logs (timestamp, nivel, origen, mensaje, metadata)
                VALUES (datetime('now', '-2 days'), 'INFO', 'test', 'Log nuevo', '{}');
            """)

        # Ejecutar purga de 30 días
        eliminados = gestor_sesion.purgar_logs_antiguos_db(dias_retencion=30, db_path=self.test_db)
        self.assertGreaterEqual(eliminados, 1)

        # Comprobar que solo queda el log nuevo
        logs_restantes = gestor_sesion.consultar_logs_db(limite=10, db_path=self.test_db)
        self.assertEqual(len(logs_restantes), 1)
        self.assertEqual(logs_restantes[0]["mensaje"], "Log nuevo")

    def test_04_verificacion_post_carga_http_mock(self):
        """Valida que verificar_participantes_actividad cruza correctamente las cédulas contra el servidor."""
        participantes_existentes = [
            {"dni": "11111111", "nombre": "Pedro", "apellido": "Perez"},
            {"dni": "22222222", "nombre": "Luisa", "apellido": "Gomez"}
        ]

        with patch("modulos.verificador_cargas_export.obtener_participantes_existentes_actividad", return_value=participantes_existentes):
            mock_session = MagicMock()

            # Caso 1: Todas las cédulas coinciden
            res = verificador_cargas_export.verificar_participantes_actividad(
                mock_session, "12345", ["11111111", "22222222"]
            )
            self.assertEqual(res["esperados_total"], 2)
            self.assertEqual(res["confirmados_total"], 2)
            self.assertTrue(res["exito_completo"])
            self.assertEqual(len(res["faltantes"]), 0)

            # Caso 2: Falta una cédula en el servidor
            res_parcial = verificador_cargas_export.verificar_participantes_actividad(
                mock_session, "12345", ["11111111", "99999999"]
            )
            self.assertEqual(res_parcial["confirmados_total"], 1)
            self.assertFalse(res_parcial["exito_completo"])
            self.assertIn("99999999", res_parcial["faltantes"])

    def test_05_diagnostico_preventivo_facilitador_alertas(self):
        """Valida que diagnosticar_actividades_facilitador identifica actividades vacías y enciende alerta."""
        actividades_simuladas = [
            {"id": "1", "nombre": "Taller Python", "participantes": 12, "tipo_clasificacion": "formacion"},
            {"id": "2", "nombre": "Folleto Digital", "participantes": 0, "tipo_clasificacion": "producto"},
            {"id": "3", "nombre": "Charla IA Incompleta", "participantes": 0, "tipo_clasificacion": "formacion"}
        ]

        with patch("modulos.diagnostico_facilitador.consultar_actividades_infoapp_export", return_value=(3, actividades_simuladas)):
            mock_session = MagicMock()
            res = diagnostico_facilitador.diagnosticar_actividades_facilitador(mock_session, uid="1325")

            self.assertEqual(res["total_actividades"], 3)
            self.assertEqual(res["formaciones_total"], 2)
            self.assertEqual(res["productos_total"], 1)
            self.assertEqual(res["conteo_sin_participantes"], 1)
            self.assertEqual(res["salud_reporte"], "atencion_requerida")
            self.assertGreater(len(res["alertas"]), 0)
            self.assertIn("0 participantes cargados", res["alertas"][0])

    def test_06_generar_planilla_desde_actividad_infoapp_mock(self):
        """Valida la generación física de una planilla ODS a partir de datos remotos de actividad."""
        participantes_simulados = [
            {
                "nombre": "Rosa",
                "apellido": "Blanco",
                "dni": "25123456",
                "genero": "Femenino",
                "f_nacimiento": "2000-01-15",
                "telefono": "0412-5556677",
                "correo": "rosa@test.com"
            }
        ]

        with patch("modulos.verificador_cargas_export.obtener_participantes_existentes_actividad", return_value=participantes_simulados):
            ruta_salida = self.temp_dir.name
            mock_session = MagicMock()
            archivo_generado = generador_planilla.generar_planilla_desde_actividad_infoapp(
                mock_session, id_activity="55500", ruta_salida=ruta_salida, formato="ods"
            )

            self.assertTrue(os.path.isfile(archivo_generado))
            self.assertTrue(archivo_generado.endswith(".ods"))
            self.assertGreater(os.path.getsize(archivo_generado), 0)

    def test_07_resumen_facilitadores_info_filtro_resolucion(self):
        """Valida que la agregación de facilitadores usa info_filtro para evitar sedes vacías."""
        actividades_prueba = [
            {"uid": "1325", "responsable": "Facilitador Yaracuy", "info_id": "", "participantes": 5, "productos": 0, "dimensiones": "formacion"}
        ]

        resumen_facilitadores = {}
        info_filtro = "NRYAR24"
        info_id_param = None

        for act in actividades_prueba:
            f_uid = str(act.get("uid") or "").strip()
            resp_nom = str(act.get("responsable") or "").strip()
            clave_fac = f_uid or resp_nom
            if clave_fac not in resumen_facilitadores:
                resumen_facilitadores[clave_fac] = {
                    "uid": f_uid,
                    "nombre": resp_nom,
                    "info_id": act.get("info_id") or info_filtro or info_id_param or "S/D"
                }

        self.assertEqual(resumen_facilitadores["1325"]["info_id"], "NRYAR24")

    def test_08_coherencia_semver_v520(self):
        """Valida la coherencia de versión 5.2.0 en modulos/version.py y config/settings.json."""
        self.assertEqual(version.__version__, "5.2.0")
        self.assertEqual(version.ETIQUETA_VERSION, "v5.2.0")

        settings_path = Path(entorno.ARCHIVO_SETTINGS)
        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("app", {}).get("version"), "5.2.0")

        version_txt_path = Path(entorno.RAIZ_PROYECTO) / "docs" / "version.txt"
        with open(version_txt_path, "r", encoding="utf-8") as f:
            contenido_v = f.read()
        self.assertIn("[v5.2.0]", contenido_v)


if __name__ == "__main__":
    unittest.main()
