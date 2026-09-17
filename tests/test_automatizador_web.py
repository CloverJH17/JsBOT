#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del automatizador web (automatizador_web.py) SIN abrir navegador real.

Se simula la Page de Playwright con MagicMock, que imita la interfaz que usa
el bot: page.url, page.goto, page.locator, page.evaluate, page.screenshot.
Esto permite probar:
  - Participantes sin documento son rechazados correctamente
  - Lógica de la función asegurar_sesion_activa
  - Captura de screenshots (flag activado/desactivado)
  - Flujos de carga masiva (exitosos, fallidos, pausa)
  - Servicios: búsqueda, perfil nuevo, verificación en tabla

Ejecutar desde la raíz del proyecto:
    py -m unittest tests.test_automatizador_web -v
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.automatizador_web as am


# =============================================================================
# HELPERS
# =============================================================================

def _make_page(url="https://infoapp2.infocentro.gob.ve/admin/index.php?id_activity=123"):
    """Crea un MagicMock de Playwright Page preconfigurado."""
    page = MagicMock()
    page.url = url
    # locator().input_value() devuelve "" por defecto (usuario nuevo)
    page.locator.return_value.input_value.return_value = ""
    page.locator.return_value.wait_for.return_value = None
    page.locator.return_value.first = page.locator.return_value
    page.evaluate.return_value = None
    return page


def _config(archivo_log=None):
    return {
        "usuario": "op@test", "clave": "secreto",
        "url": "https://infoapp2.infocentro.gob.ve/admin/index.php?view=participants_list&id_activity=123",
        "id_actividad": "123", "timestamp_str": "2026-08-25_1200",
        "archivo_log": archivo_log,
    }


def _alumno(**kw):
    base = {
        "nombre": "Ana", "apellido": "Pérez", "cedula": "12345678",
        "cedulado": "si", "cedula_escolar": "", "cedula_padre": "",
        "nacimiento": "2010-05-10", "edad": 16, "genero": "F",
        "telefono": "0412-1234567"
    }
    base.update(kw)
    return base


def _persona(**kw):
    base = {
        "nombre": "Ana", "apellido": "Pérez", "cedula": "12345678",
        "cedulado": "si", "cedula_escolar": "", "cedula_padre": "",
        "nacimiento": "1990-01-01", "edad": 36, "genero": "F",
        "telefono": "0412-1234567"
    }
    base.update(kw)
    return base


class _WebTestCase(unittest.TestCase):
    """Aísla efectos secundarios: screenshots, checkpoints, paneles UI."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patches = [
            patch.object(am, "SCREENSHOTS_DIR", self.tmp),
            patch.object(am, "guardar_estado_sesion"),
            patch.object(am, "renderizar_panel_carga"),
            patch.object(am, "renderizar_panel_servicios"),
            patch.object(am, "prompt_reintentar_alumno", return_value="SKIP"),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)


# =============================================================================
# VALIDACIÓN DE PARTICIPANTES SIN DOCUMENTO
# =============================================================================

class TestRegistroSinDocumento(unittest.TestCase):
    def test_rechaza_participante_sin_documento(self):
        """registrar_alumno_playwright rechaza alumnos sin ningún tipo de documento."""
        page = _make_page()
        alumno = _alumno(cedula="", cedula_escolar="", cedula_padre="", cedulado="sin_documento")
        ok, msg = am.registrar_alumno_playwright(page, alumno, _config())
        self.assertFalse(ok)
        self.assertIn("sin documento", msg.lower())
        # No debe haber navegado a ninguna URL
        page.goto.assert_not_called()

    def test_rechaza_perfil_menor_sin_tutor(self):
        """registrar_nuevo_usuario_perfil rechaza menores sin cédula de representante."""
        page = _make_page()
        persona = _persona(cedula="", cedula_padre="", cedulado="sin_documento")
        ok, msg = am.registrar_nuevo_usuario_perfil(page, persona, {})
        self.assertFalse(ok)
        self.assertIn("sin documento", msg.lower())


# =============================================================================
# DETALLES DE REGISTRO EN FORMACIÓN PLAYWRIGHT
# =============================================================================

class TestRegistrarAlumnoPlaywrightDetallado(unittest.TestCase):
    def test_registro_exitoso_verificado_en_tabla(self):
        """Verifica que registrar_alumno_playwright ejecute búsqueda, AJAX y verificación en tabla."""
        page = _make_page()
        # Mock de evaluate: primera llamada (búsqueda/inputs), luego done=True, luego tabla=True
        page.evaluate.side_effect = lambda script, *args: (
            True if "window.__ajax_done" in str(script)
            else ("OK" if "window.__ajax_res" in str(script)
            else (True if "esta_verificado" in str(script) or "querySelectorAll" in str(script)
            else None))
        )
        alumno = _alumno(cedula="28123456", nombre="Carlos", apellido="Gomez")
        ok, msg = am.registrar_alumno_playwright(page, alumno, _config())
        self.assertTrue(ok)
        self.assertIn("verificado", msg.lower())

    def test_registro_rechazado_por_aviso_servidor(self):
        """Verifica que una respuesta de advertencia de InfoApp sea capturada como fallo."""
        page = _make_page()
        page.evaluate.side_effect = lambda script, *args: (
            True if "window.__ajax_done" in str(script)
            else ("¡AVISO!: El participante ya está registrado en la actividad." if "window.__ajax_res" in str(script)
            else None)
        )
        alumno = _alumno(cedula="28123456")
        ok, msg = am.registrar_alumno_playwright(page, alumno, _config())
        self.assertFalse(ok)
        self.assertIn("aviso", msg.lower())


# =============================================================================
# CAPTURAS DE PANTALLA
# =============================================================================

class TestCapturasPantalla(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_flag_apagado_no_genera_archivo(self):
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp), \
             patch.object(am.cm, "captura_screenshots_activada", return_value=False):
            am.capturar_pantalla_error(MagicMock(), "12345678")
        self.assertEqual(os.listdir(self.tmp), [])

    def test_flag_encendido_llama_page_screenshot(self):
        """Con Playwright, se llama page.screenshot(path=...) en vez de save_screenshot."""
        fake_page = MagicMock()
        fake_page.screenshot.side_effect = (
            lambda path: open(path, "wb").write(b"\x89PNG simulado")
        )
        with patch.object(am, "SCREENSHOTS_DIR", self.tmp), \
             patch.object(am.cm, "captura_screenshots_activada", return_value=True):
            am.capturar_pantalla_error(fake_page, "12345678")
        self.assertEqual(len(os.listdir(self.tmp)), 1)
        fake_page.screenshot.assert_called_once()


# =============================================================================
# SESIÓN ACTIVA
# =============================================================================

class TestAsegurarSesion(_WebTestCase):
    def test_sesion_php_expirada_reautentica(self):
        page = _make_page(url="https://infoapp2.infocentro.gob.ve/index.php?view=acceder")
        contenedor = {'pw': MagicMock(), 'context': MagicMock(), 'page': page}
        with patch.object(am, "realizar_login") as m_login:
            am.asegurar_sesion_activa(contenedor, _config())
            m_login.assert_called_once()

    def test_sesion_viva_no_reautentica(self):
        page = _make_page(url="https://infoapp2.infocentro.gob.ve/admin/index.php?id_activity=123")
        contenedor = {'pw': MagicMock(), 'context': MagicMock(), 'page': page}
        with patch.object(am, "realizar_login") as m_login, \
             patch.object(am, "iniciar_contexto_playwright") as m_nav:
            am.asegurar_sesion_activa(contenedor, _config())
            m_login.assert_not_called()
            m_nav.assert_not_called()

    def test_page_nulo_abre_contexto_nuevo(self):
        contenedor = {'pw': None, 'context': None, 'page': None}
        mock_pw = MagicMock()
        mock_context = MagicMock()
        mock_page = _make_page()
        mock_context.new_page.return_value = mock_page
        with patch.object(am, "iniciar_contexto_playwright", return_value=(mock_pw, mock_context)), \
             patch.object(am, "realizar_login") as m_login:
            am.asegurar_sesion_activa(contenedor, _config())
            m_login.assert_called_once()
        self.assertEqual(contenedor['page'], mock_page)


# =============================================================================
# FLUJOS MASIVOS — ACTIVIDADES FORMATIVAS
# =============================================================================

class TestEjecutarCargaInfApp(_WebTestCase):
    def test_registro_exitoso_cuenta_correctamente(self):
        alumnos = [_alumno(), _alumno(cedula="22222222")]
        with patch.object(am, "asegurar_sesion_activa"), \
             patch.object(am, "registrar_alumno_playwright", return_value=(True, "OK")), \
             patch.object(am, "registrar_evento_log"):
            # Proveer page en el contenedor
            with patch.object(am, "asegurar_sesion_activa",
                              side_effect=lambda c, cfg: c.update({'page': _make_page()})):
                exitosos, fallidos, _ = am.ejecutar_carga_infoapp(alumnos, _config())
        self.assertEqual(len(exitosos), 2)
        self.assertEqual(len(fallidos), 0)

    def test_operador_salta_alumno_fallido_y_continua(self):
        alumnos = [_alumno(cedula="11111111"), _alumno(cedula="22222222")]
        respuestas = [(False, "ya inscrito"), (True, "ok")]
        with patch.object(am, "asegurar_sesion_activa",
                          side_effect=lambda c, cfg: c.update({'page': _make_page()})), \
             patch.object(am, "registrar_alumno_playwright", side_effect=respuestas), \
             patch.object(am, "registrar_evento_log"), \
             patch.object(am, "prompt_reintentar_alumno", return_value="SKIP"):
            exitosos, fallidos, _ = am.ejecutar_carga_infoapp(alumnos, _config())
        self.assertEqual(len(fallidos), 1)
        self.assertEqual(len(exitosos), 1)
        self.assertEqual(exitosos[0]["cedula"], "22222222")

    def test_operador_pausa_detiene_flujo(self):
        alumnos = [_alumno(), _alumno(cedula="22222222")]
        with patch.object(am, "asegurar_sesion_activa",
                          side_effect=lambda c, cfg: c.update({'page': _make_page()})), \
             patch.object(am, "registrar_alumno_playwright", return_value=(False, "timeout")), \
             patch.object(am, "registrar_evento_log"), \
             patch.object(am, "prompt_reintentar_alumno", return_value="PAUSE"):
            exitosos, fallidos, _ = am.ejecutar_carga_infoapp(alumnos, _config())
        # Se detiene antes de procesar el segundo alumno
        self.assertEqual(len(exitosos), 0)
        self.assertEqual(len(fallidos), 0)


# =============================================================================
# FLUJOS MASIVOS — SERVICIOS COMUNITARIOS
# =============================================================================

class TestEjecutarCargaServicios(_WebTestCase):
    def _config_servicio(self):
        return {
            "tipo_servicio": "Gestión en el Sistema de Protección Social Patria",
            "fecha_servicio": "2026-08-25",
            "infocentro": {"estado_id": "22", "direccion": "Av. principal El Jovito"}
        }

    def test_bucle_masivo_con_fallidos_intercalados(self):
        personas = [_persona(cedula=f"1000000{i}") for i in range(3)]
        resultados = [(True, "ok"), (False, "¡AVISO!: duplicado"), (True, "ok")]
        with patch.object(am, "asegurar_sesion_activa",
                          side_effect=lambda c, cfg: c.update({'page': _make_page()})), \
             patch.object(am, "registrar_servicio_persona", side_effect=resultados), \
             patch.object(am, "registrar_evento_log"), \
             patch.object(am, "prompt_reintentar_alumno", return_value="SKIP"):
            exitosos, fallidos, _ = am.ejecutar_carga_servicios_infoapp(
                personas, _config(), self._config_servicio(),
                fn_guardar_checkpoint=lambda *a, **k: None
            )
        self.assertEqual(len(exitosos), 2)
        self.assertEqual(len(fallidos), 1)
        self.assertEqual(fallidos[0]["estado"], "OMITIDO")

    def test_servicio_exitoso_cuenta_correctamente(self):
        personas = [_persona()]
        with patch.object(am, "asegurar_sesion_activa",
                          side_effect=lambda c, cfg: c.update({'page': _make_page()})), \
             patch.object(am, "registrar_servicio_persona", return_value=(True, "ok ID:777")), \
             patch.object(am, "registrar_evento_log"):
            exitosos, fallidos, _ = am.ejecutar_carga_servicios_infoapp(
                personas, _config(), self._config_servicio()
            )
        self.assertEqual(len(exitosos), 1)
        self.assertEqual(len(fallidos), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
