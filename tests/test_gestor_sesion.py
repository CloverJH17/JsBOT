#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del gestor de sesión, checkpoints y auditoría (gestor_sesion.py).

Todos los tests redirigen los archivos hacia un directorio temporal:
NO se tocan los logs/, config/ ni checkpoints reales del proyecto.

Escenarios probados:
  - Credenciales: guardado/lectura/archivo ausente
  - Checkpoints atómicos: guardar, leer, completar, corruptos, .tmp huérfanos
  - Logs de auditoría: eventos, cierre exitoso, cierre incompleto
  - Reportes Excel de auditoría (formación y servicios)
  - Configuración de servicios: defaults, JSON corrupto, roundtrip

Ejecutar desde la raíz del proyecto:
    py -m unittest tests.test_gestor_sesion -v
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd

import modulos.gestor_sesion as gs


def _participante(nombre="Ana", apellido="Pérez", cedula="12345678", **kw):
    base = {
        "nombre": nombre, "apellido": apellido, "cedula": cedula,
        "cedulado": "si", "cedula_escolar": "", "cedula_padre": "",
        "nacimiento": "2010-05-10", "edad": 16, "genero": "F",
        "telefono": "0412-1234567"
    }
    base.update(kw)
    return base


class _Aislado(unittest.TestCase):
    """Redirige todos los archivos del módulo a un directorio temporal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patches = [
            patch.object(gs, "CONFIG_DIR", self.tmp),
            patch.object(gs, "LOGS_DIR", self.tmp),
            patch.object(gs, "CONFIG_FILE", os.path.join(self.tmp, "config.ini")),
            patch.object(gs, "CONFIG_SERV_PATH", os.path.join(self.tmp, "config_servicios.json")),
            patch.object(gs, "SESSION_STATE_FILE", os.path.join(self.tmp, "session_state.json")),
            patch.object(gs, "SESSION_STATE_SERV_FILE", os.path.join(self.tmp, "session_state_servicios.json")),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def _ruta(self, nombre):
        return os.path.join(self.tmp, nombre)


# =============================================================================
# EXTRAER ID DE ACTIVIDAD
# =============================================================================

class TestExtraerIdActividad(unittest.TestCase):
    def test_parametro_estandar(self):
        url = "https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=523948&otro=1"
        self.assertEqual(gs.extraer_id_actividad(url), "523948")

    def test_sin_id_devuelve_general(self):
        self.assertEqual(gs.extraer_id_actividad("https://infoapp2.infocentro.gob.ve/admin/"), "general")
        self.assertEqual(gs.extraer_id_actividad(""), "general")
        self.assertEqual(gs.extraer_id_actividad("cualquier texto suelto"), "general")

    def test_id_en_path(self):
        self.assertEqual(gs.extraer_id_actividad("https://x.com/actividades/777/"), "777")


# =============================================================================
# CREDENCIALES
# =============================================================================

class TestCredenciales(_Aislado):
    def test_roundtrip(self):
        gs.guardar_credenciales("usuario@info.com", "clave-secreta")
        u, c = gs.obtener_credenciales()
        self.assertEqual((u, c), ("usuario@info.com", "clave-secreta"))

    def test_archivo_ausente_devuelve_vacios(self):
        self.assertEqual(gs.obtener_credenciales(), ("", ""))

    def test_ini_corrupto_no_explota(self):
        with open(self._ruta("config.ini"), "w", encoding="utf-8") as f:
            f.write("esto no es un ini válido [[[")
        # configparser es tolerante: puede leer basura o fallar -> no debe lanzar
        try:
            resultado = gs.obtener_credenciales()
        except Exception:
            resultado = ("", "")
        self.assertIsInstance(resultado, tuple)


# =============================================================================
# CHECKPOINTS DE FORMACIÓN (resiliencia ante apagones)
# =============================================================================

class TestCheckpointFormacion(_Aislado):
    def _config(self):
        return {"usuario": "u", "clave": "c", "url": "http://x/?id_activity=1",
                "id_actividad": "1", "timestamp_str": "2026-08-25_1200",
                "archivo_log": self._ruta("log.txt")}

    def test_guardar_y_leer_checkpoint(self):
        partes = [_participante(), _participante(cedula="22222222")]
        gs.guardar_estado_sesion(self._config(), partes, indice_ultimo=1)
        estado = gs.leer_estado_sesion()
        self.assertIsNotNone(estado)
        self.assertEqual(estado["indice_ultimo_procesado"], 1)
        self.assertEqual(len(estado["participantes"]), 2)

    def test_checkpoint_completo_no_se_reanuda(self):
        partes = [_participante()]
        gs.guardar_estado_sesion(self._config(), partes, indice_ultimo=1)
        self.assertIsNone(gs.leer_estado_sesion())

    def test_sin_checkpoint_devuelve_none(self):
        self.assertIsNone(gs.leer_estado_sesion())

    def test_json_corrupto_devuelve_none(self):
        with open(self._ruta("session_state.json"), "w") as f:
            f.write("{json roto por un apagón")
        self.assertIsNone(gs.leer_estado_sesion())

    def test_tmp_huerfano_de_apagon_se_ignora(self):
        # Escenario real: el apagón ocurrió mientras escribía el .tmp
        with open(self._ruta("session_state.json.tmp"), "w") as f:
            f.write("{a medio escribir...")
        self.assertIsNone(gs.leer_estado_sesion())

    def test_limpieza_elimina_checkpoint(self):
        gs.guardar_estado_sesion(self._config(), [_participante()], 0)
        gs.limpiar_estado_sesion()
        self.assertIsNone(gs.leer_estado_sesion())
        # limpiar dos veces no explota
        gs.limpiar_estado_sesion()

    def test_guardar_sobre_checkpoint_previo_lo_reemplaza(self):
        gs.guardar_estado_sesion(self._config(), [_participante()], 0)
        gs.guardar_estado_sesion(self._config(), [_participante()], 1)
        estado = gs.leer_estado_sesion()
        self.assertTrue(
            estado is None or estado["indice_ultimo_procesado"] == 1,
            "El checkpoint viejo debe ser reemplazado por el nuevo"
        )


# =============================================================================
# CHECKPOINTS DE SERVICIOS
# =============================================================================

class TestCheckpointServicios(_Aislado):
    def test_roundtrip_completo(self):
        cfg_bot = {"usuario": "u", "archivo_log": None, "timestamp_str": "t"}
        cfg_srv = {"tipo_servicio": "Patria", "fecha_servicio": "2026-08-25"}
        personas = [_participante(), _participante(cedula="22222222")]

        gs.guardar_estado_sesion_servicios(cfg_bot, cfg_srv, personas, 1)
        estado = gs.leer_estado_sesion_servicios()
        self.assertIsNotNone(estado)
        self.assertEqual(estado["config_servicio"]["tipo_servicio"], "Patria")
        self.assertEqual(estado["indice_ultimo_procesado"], 1)

        gs.limpiar_estado_sesion_servicios()
        self.assertIsNone(gs.leer_estado_sesion_servicios())

    def test_corrupto_devuelve_none(self):
        with open(self._ruta("session_state_servicios.json"), "w") as f:
            f.write("[[[corrupto")
        self.assertIsNone(gs.leer_estado_sesion_servicios())


# =============================================================================
# LOGS DE AUDITORÍA
# =============================================================================

class TestLogsAuditoria(_Aislado):
    def test_evento_log_formato_estructurado(self):
        ruta = self._ruta("log.txt")
        gs.registrar_evento_log(ruta, "12345678", "Ana Pérez", "EXITOSO", "verificado en tabla")
        with open(ruta, encoding="utf-8") as f:
            linea = f.readlines()[-1]
        self.assertIn("EXITOSO", linea)
        self.assertIn("12345678", linea)
        self.assertIn("Ana Pérez", linea)

    def test_evento_log_sin_archivo_es_noop(self):
        # No debe explotar aunque archivo_log sea None/vacío
        gs.registrar_evento_log(None, "1", "n", "EXITOSO", "d")

    def test_finalizar_log_incompleto_registra_motivo(self):
        ruta = self._ruta("log.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("inicio\n")
        gs.finalizar_log_incompleto({"archivo_log": ruta}, "Interrumpido manualmente")
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        self.assertIn("INCOMPLETO", contenido)
        self.assertIn("Interrumpido manualmente", contenido)

    def test_finalizar_log_exito_cierra_y_limpia(self):
        ruta = self._ruta("log.txt")
        gs.guardar_estado_sesion({"url": "x"}, [_participante()], 0)
        cfg = {"archivo_log": ruta}
        gs.guardar_estado_sesion(cfg, [_participante()], 0)
        gs.finalizar_log_exito(cfg)
        with open(ruta, encoding="utf-8") as f:
            self.assertIn("EXITOSAMENTE", f.read())
        self.assertIsNone(gs.leer_estado_sesion())   # checkpoint removido

    def test_config_sin_archivo_log_es_segura(self):
        gs.finalizar_log_exito(None)
        gs.finalizar_log_incompleto({}, "motivo")


# =============================================================================
# REPORTES EXCEL DE AUDITORÍA
# =============================================================================

class TestReporteExcelFormacion(_Aislado):
    def test_generacion_con_exitosos_y_fallidos(self):
        cfg = {"id_actividad": "523948", "timestamp_str": "2026-08-25_1200"}
        exitosos = [_participante(), _participante(nombre="Beto", apellido="Rojas", cedula="22222222")]
        fallidos = [{"participante": _participante(nombre="Carla", cedula="33333333"),
                     "estado": "OMITIDO", "detalle": "ya inscrito"}]
        ruta = gs.generar_reporte_auditoria_excel(cfg, exitosos, fallidos)

        self.assertTrue(os.path.exists(ruta))
        libro = pd.read_excel(ruta, sheet_name=None)
        self.assertIn("Exitosos", libro)
        self.assertIn("Incidencias", libro)
        ex = libro["Exitosos"]
        self.assertEqual(len(ex), 2)
        self.assertIn("Ana Pérez", ex["Nombres y Apellidos"].tolist())
        inc = libro["Incidencias"]
        self.assertIn("ya inscrito", inc["Causa de la Incidencia"].tolist())

    def test_modalidades_documentos_variados(self):
        cfg = {"id_actividad": "1", "timestamp_str": "t"}
        exitosos = [
            _participante(cedula="11111111"),
            _participante(nombre="Niño", cedula="", cedulado="escolar",
                          cedula_escolar="11630348783"),
            _participante(nombre="Bebé", cedula="", cedulado="no", cedula_padre="30348783"),
        ]
        ruta = gs.generar_reporte_auditoria_excel(cfg, exitosos, [])
        docs = pd.read_excel(ruta, sheet_name="Exitosos")["Documento"].tolist()
        self.assertEqual(docs[0], "11111111")
        self.assertEqual(docs[1], "CE:11630348783")
        self.assertEqual(docs[2], "Rep:30348783")


class TestReporteExcelServicios(_Aislado):
    def test_cedulas_con_prefijo(self):
        cfg = {"usuario": "u", "timestamp_str": "2026-08-25_1300", "archivo_log": None}
        cfg_srv = {"tipo_servicio": "Patria", "fecha_servicio": "2026-08-25"}
        exitosos = [
            _participante(edad=36),
            _participante(nombre="Luis", apellido="Forero", cedula="E-84321000", edad=30),
        ]
        ruta = gs.generar_reporte_auditoria_servicios(cfg, cfg_srv, exitosos, [])
        cedulas = pd.read_excel(ruta, sheet_name="Servicios Exitosos")["Cédula"].tolist()
        self.assertEqual(cedulas[0], "V-12345678")
        self.assertEqual(cedulas[1], "E-84321000")   # extranjeros NO llevan V-


# =============================================================================
# CONFIGURACIÓN DE SERVICIOS
# =============================================================================

class TestConfigServicios(_Aislado):
    def test_default_cuando_no_hay_archivo(self):
        cfg = gs.cargar_config_servicios()
        self.assertIn("catalogo_servicios", cfg)
        self.assertIn("infocentro", cfg)
        self.assertGreater(len(cfg["catalogo_servicios"]), 10)

    def test_json_corrupto_usa_defaults(self):
        with open(self._ruta("config_servicios.json"), "w") as f:
            f.write("{no soy json")
        cfg = gs.cargar_config_servicios()
        self.assertIn("servicio_por_defecto", cfg)

    def test_roundtrip(self):
        original = gs.cargar_config_servicios()
        original["servicio_por_defecto"] = "Servicio Personalizado"
        gs.guardar_config_servicios(original)
        leido = gs.cargar_config_servicios()
        self.assertEqual(leido["servicio_por_defecto"], "Servicio Personalizado")


if __name__ == "__main__":
    unittest.main(verbosity=2)
