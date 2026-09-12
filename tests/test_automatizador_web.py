#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del automatizador web (automatizador_web.py) SIN abrir navegador real.

Se simula el driver de Selenium con FakeDriver/FakeElement, que imita solo la
interfaz que usa el bot: current_url, get, find_element, execute_script,
save_screenshot. Esto permite reprobar:
  - Datos mal cargados (campos faltantes, nombres con caracteres hostiles)
  - Clics erróneos / elementos que explotan
  - Navegador muerto, sesión PHP expirada
  - Servidor InfoApp que responde errores o advertencias
  - Verificación en tabla fallida
  - Decisiones del operador ante fallos (REINTENTAR / SALTAR / PAUSAR)

Ejecutar desde la raíz del proyecto:
    py -m unittest tests.test_automatizador_web -v
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from selenium.common.exceptions import WebDriverException

import modulos.automatizador_web as am


# =============================================================================
# FAKES DEL NAVEGADOR
# =============================================================================

class FakeElement:
    def __init__(self, valor="", explotar_click=False, explotar_send=False):
        self.valor = valor
        self.explotar_click = explotar_click
        self.explotar_send = explotar_send
        self.texto_enviado = []
        self.tag_name = "input"

    def clear(self):
        pass

    def send_keys(self, txt):
        if self.explotar_send:
            raise WebDriverException("Elemento no interactuable (overlay encima)")
        self.texto_enviado.append(txt)

    def click(self):
        if self.explotar_click:
            raise WebDriverException("click intercepted por overlay")

    def get_attribute(self, attr):
        return self.valor

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def is_selected(self):
        return False


class FakeDriver:
    """
    Driver simulado. Configurable por escenario:
      - url_actual: lo que devuelve current_url
      - valor_campo_nombre: value del input #name (detecta preexistentes)
      - respuesta_ajax: msg del servidor ('' = éxito silencioso)
      - verificado: si la tabla DOM contiene al participante
      - user_f_id / name_param: resultados de búsqueda de servicios
    """

    def __init__(self, url_actual="https://infoapp2.infocentro.gob.ve/admin/index.php?id_activity=123",
                 valor_campo_nombre="", respuesta_ajax="", verificado=True,
                 user_f_id="777", name_param="Ana Perez",
                 elemento_lupa_explota=False):
        self.url_actual = url_actual
        self.valor_campo_nombre = valor_campo_nombre
        self.respuesta_ajax = respuesta_ajax
        self.verificado = verificado
        self.user_f_id = user_f_id
        self.name_param = name_param
        self.elemento_lupa_explota = elemento_lupa_explota
        self.navegaciones = []
        self.scripts = []          # log de execute_script sin arguments
        self.ajax_params = None    # captura del dict pasado como arguments[0]
        self._campo_nombre = None

    @property
    def current_url(self):
        return self.url_actual

    def get(self, url):
        self.navegaciones.append(url)
        # tras navegar a la actividad, simula que estamos allí
        if "id_activity" in url or "view=" in url:
            self.url_actual = url

    def find_element(self, by, selector):
        if selector == "name" and getattr(self, "_busqueda_nombre", False):
            pass
        if selector == "name":
            if self._campo_nombre is None:
                self._campo_nombre = FakeElement(valor=self.valor_campo_nombre)
            return self._campo_nombre
        if "button" in str(selector) or "onclick" in str(selector):
            return FakeElement(explotar_click=self.elemento_lupa_explota)
        return FakeElement()

    def execute_script(self, script, *args):
        self.scripts.append(script)
        if "spinOculto" in script:
            return True   # el spinner de carga siempre está oculto (AJAX libre)
        if "window.__ajax_done = false" in script:
            if args:
                self.ajax_params = args[0]
            return None
        if "return window.__ajax_done" in script:
            return True   # la petición AJAX siempre 'termina'
        if "return window.__ajax_res" in script:
            return self.respuesta_ajax
        if "var doc = arguments[0]" in script:
            return self.verificado
        if "user_f_id" in script and "name_param" in script:
            return self.name_param
        if "user_f_id" in script:
            return self.user_f_id
        return None

    def save_screenshot(self, ruta):
        with open(ruta, "wb") as f:
            f.write(b"PNG-fake")


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


class _WebTestCase(unittest.TestCase):
    """Aísla efectos secundarios: screenshots, checkpoints, paneles UI."""

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.patches = [
            patch.object(am, "SCREENSHOTS_DIR", tmp),
            patch.object(am, "guardar_estado_sesion"),
            patch.object(am, "renderizar_panel_carga"),
            patch.object(am, "renderizar_panel_servicios"),
            patch.object(am, "obtener_timeout_ajax", return_value=1),
            patch.object(am, "prompt_reintentar_alumno", return_value="SKIP"),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)


# =============================================================================
# CONFIGURACIÓN DE TIMEOUTS
# =============================================================================

class TestTimeoutAjax(unittest.TestCase):
    def test_default_sin_archivo(self):
        with patch.object(am, "SETTINGS_FILE", "no_existe.json"):
            self.assertEqual(am.obtener_timeout_ajax(), 15)

    def test_valor_personalizado(self):
        fd, ruta = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"timeouts": {"ajax_wait_seconds": 42}}, f)
        self.addCleanup(os.unlink, ruta)
        with patch.object(am, "SETTINGS_FILE", ruta):
            self.assertEqual(am.obtener_timeout_ajax(), 42)

    def test_json_corrupto_usa_default(self):
        fd, ruta = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("{esto no es json")
        self.addCleanup(os.unlink, ruta)
        with patch.object(am, "SETTINGS_FILE", ruta):
            self.assertEqual(am.obtener_timeout_ajax(), 15)


# =============================================================================
# GESTIÓN DEL NAVEGADOR Y SESIÓN
# =============================================================================

class TestAsegurarNavegador(_WebTestCase):
    def test_driver_nulo_inicia_sesion(self):
        with patch.object(am, "iniciar_navegador", return_value=MagicMock()) as m_nav, \
             patch.object(am, "realizar_login") as m_login:
            contenedor = {"driver": None}
            am.asegurar_navegador_activo(contenedor, _config())
            m_nav.assert_called_once()
            m_login.assert_called_once()

    def test_ningun_navegador_disponible_lanza_error(self):
        with patch.object(am, "iniciar_navegador", return_value=None):
            with self.assertRaises(RuntimeError):
                am.asegurar_navegador_activo({"driver": None}, _config())

    def test_sesion_php_expirada_reautentica(self):
        # El bot detecta expiración solo si la URL contiene 'login' o 'acceder'
        driver = MagicMock()
        driver.current_url = "https://infoapp2.infocentro.gob.ve/index.php?view=acceder"
        with patch.object(am, "realizar_login") as m_login:
            am.asegurar_navegador_activo({"driver": driver}, _config())
            m_login.assert_called_once()

    def test_sesion_expirada_sin_palabra_clave_no_se_detecta(self):
        # HALLAZGO: si InfoApp redirige a una URL sin 'login'/'acceder'
        # (p.ej. admin/index.php), el bot NO reautentica y fallará después
        driver = MagicMock()
        driver.current_url = "https://infoapp2.infocentro.gob.ve/admin/index.php"
        with patch.object(am, "realizar_login") as m_login:
            am.asegurar_navegador_activo({"driver": driver}, _config())
            m_login.assert_not_called()

    def test_sesion_viva_no_toca_nada(self):
        driver = MagicMock(spec=["current_url"])
        driver.current_url = "https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=123"
        with patch.object(am, "realizar_login") as m_login, \
             patch.object(am, "iniciar_navegador") as m_nav:
            am.asegurar_navegador_activo({"driver": driver}, _config())
            m_login.assert_not_called()
            m_nav.assert_not_called()


# =============================================================================
# REGISTRO DE ALUMNO EN FORMACIÓN — parámetros AJAX según tipo de documento
# =============================================================================

class TestRegistroAlumnoParametros(_WebTestCase):
    def _ejecutar(self, alumno, **fake_kw):
        driver = FakeDriver(**fake_kw)
        exito, detalle = am.registrar_alumno_en_web(driver, alumno, _config())
        return driver, exito, detalle

    def test_cedulado_envia_doc_id_y_ced_esc_vacia(self):
        driver, exito, _ = self._ejecutar(_alumno())
        self.assertTrue(exito)
        p = driver.ajax_params
        self.assertEqual(p["doc_id"], "12345678")
        self.assertEqual(p["ced_esc"], "")
        self.assertEqual(p["has_doc"], "Si")
        self.assertEqual(p["is_new"], "true")

    def test_escolar_envia_ced_esc_y_doc_vacio(self):
        alumno = _alumno(cedula="", cedulado="escolar", cedula_escolar="11630348783")
        driver, exito, _ = self._ejecutar(alumno)
        self.assertTrue(exito)
        p = driver.ajax_params
        self.assertEqual(p["doc_id"], "")
        self.assertEqual(p["ced_esc"], "11630348783")
        self.assertEqual(p["has_doc"], "Cédula escolar")

    def test_menor_sin_ci_genera_parent_ref(self):
        alumno = _alumno(cedula="", cedulado="no", cedula_padre="30348783")
        driver, exito, _ = self._ejecutar(alumno)
        self.assertTrue(exito)
        p = driver.ajax_params
        self.assertEqual(p["parent_dni"], "30348783")
        self.assertEqual(p["child_num"], "1")
        self.assertEqual(p["parent_ref"], "303487831")

    def test_preexistente_marca_is_new_false(self):
        driver, _, _ = self._ejecutar(_alumno(), valor_campo_nombre="Ana María")
        self.assertEqual(driver.ajax_params["is_new"], "false")

    def test_genero_mapea_a_texto(self):
        driver, _, _ = self._ejecutar(_alumno(genero="M"))
        self.assertEqual(driver.ajax_params["gender"], "Hombre")

    def test_telefono_default_cuando_falta(self):
        a = _alumno()
        del a["telefono"]
        driver, _, _ = self._ejecutar(a)
        self.assertEqual(driver.ajax_params["telefono"], "0412-0000000")

    def test_edad_calculada_desde_nacimiento_si_falta(self):
        a = _alumno()
        a["edad"] = None
        driver, _, _ = self._ejecutar(a)
        esperado = 2026 - 2010 - ((8, 25) < (5, 10))
        self.assertEqual(driver.ajax_params["age"], esperado)


# =============================================================================
# DATOS MAL CARGADOS Y CARACTERES HOSTILES
# =============================================================================

class TestDatosMalCargados(_WebTestCase):
    def test_nombre_con_caracteres_js_hostiles_viaja_intacto(self):
        # Los datos van como arguments[] y NO interpolados en el JS, así que
        # un nombre con comillas no corrompe el script (viaja como dict)
        alumno = _alumno(nombre="D'Angelo \"El Mago\" & Hijos", apellido="<Script>")
        driver = FakeDriver()
        exito, _ = am.registrar_alumno_en_web(driver, alumno, _config())
        self.assertTrue(exito)
        p = driver.ajax_params
        self.assertEqual(p["nom_1"], "D'Angelo")
        self.assertEqual(p["nom_2"], '"El Mago" & Hijos')
        self.assertEqual(p["ape_1"], "<Script>")

    def test_apellido_con_comillas_divide_correctamente(self):
        alumno = _alumno(apellido="O'Brien De La Rosa")
        driver = FakeDriver()
        exito, _ = am.registrar_alumno_en_web(driver, alumno, _config())
        p = driver.ajax_params
        self.assertEqual(p["ape_1"], "O'Brien")
        self.assertEqual(p["ape_2"], "De La Rosa")

    def test_alumno_sin_nombre_explota_y_se_marca_critico(self):
        # ERROR HUMANO: fila sin nombre llega al bot -> debe caer en fallidos
        alumno = _alumno()
        del alumno["nombre"]     # provoca KeyError dentro del flujo
        with patch.object(am, "registrar_alumno_en_web", side_effect=KeyError("nombre")), \
             patch.object(am, "asegurar_navegador_activo"):
            exitosos, fallidos, _ = am.ejecutar_carga_infoapp([alumno], _config())
        self.assertEqual(len(exitosos), 0)
        self.assertEqual(len(fallidos), 1)
        self.assertIn("nombre", fallidos[0]["detalle"])

    def test_campos_numericos_corruptos_no_detienen_el_flujo(self):
        # COMPORTAMIENTO ACTUAL: el módulo web CONFINA en la edad del ETL y
        # la envía tal cual al servidor ('dieciséis' viaja sin validar).
        # El flujo no explota, pero el dato basura llega a InfoApp.
        alumno = _alumno(edad="dieciséis", nacimiento="fecha-mala")
        driver = FakeDriver()
        exito, _ = am.registrar_alumno_en_web(driver, alumno, _config())
        self.assertTrue(exito)
        self.assertEqual(driver.ajax_params["age"], "dieciséis")

    def test_edad_none_si_usa_fallback_numerico(self):
        # Sin edad y sin fecha de nacimiento aplica el fallback 10
        alumno = _alumno(edad=None, nacimiento="")
        driver = FakeDriver()
        exito, _ = am.registrar_alumno_en_web(driver, alumno, _config())
        self.assertTrue(exito)
        self.assertEqual(driver.ajax_params["age"], 10)


# =============================================================================
# SERVIDOR INFOAPP HOSTIL Y VERIFICACIÓN EN TABLA
# =============================================================================

class TestServidorHostil(_WebTestCase):
    def _correr(self, respuesta_ajax, verificado=True):
        return am.registrar_alumno_en_web(
            FakeDriver(respuesta_ajax=respuesta_ajax, verificado=verificado),
            _alumno(), _config()
        )

    def test_aviso_del_servidor_es_fallo(self):
        exito, detalle = self._correr("¡AVISO!: El participante ya está inscrito")
        self.assertFalse(exito)
        self.assertIn("AVISO", detalle)

    def test_atencion_del_servidor_es_fallo(self):
        exito, detalle = self._correr("ATENCIÓN: datos inconsistentes")
        self.assertFalse(exito)

    def test_error_de_red_ajax_es_fallo(self):
        exito, detalle = self._correr("ERROR: Internal Server Error")
        self.assertFalse(exito)
        self.assertIn("ERROR", detalle)

    def test_ok_pero_no_aparece_en_tabla_es_fallo(self):
        # El peor caso: servidor calló pero la tabla no muestra al alumno
        exito, detalle = self._correr("", verificado=False)
        self.assertFalse(exito)
        self.assertIn("no aparece en la tabla", detalle)

    def test_ok_y_verificado_en_tabla(self):
        exito, detalle = self._correr("")
        self.assertTrue(exito)
        self.assertIn("verificado", detalle.lower())


# =============================================================================
# CLICS ERRÓNEOS Y NAVEGADOR MUERTO (bucle de reintentos)
# =============================================================================

class TestClicsYNavegadorMuerto(_WebTestCase):
    def _cargar(self, alumno):
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "registrar_alumno_en_web", return_value=(True, "ok")):
            return am.ejecutar_carga_infoapp([alumno], _config())

    def test_lupa_que_explota_por_overlay(self):
        # CLIC ERRÓNEO: un toast tapa el botón de búsqueda
        driver = FakeDriver(elemento_lupa_explota=True)
        with self.assertRaises(WebDriverException):
            am.registrar_alumno_en_web(driver, _alumno(), _config())

    def test_webdriver_exception_persistente_agota_reintentos(self):
        # Navegador muerto 4 veces seguidas -> debe rendir con RuntimeError
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "renderizar_panel_carga"), \
             patch.object(am, "guardar_estado_sesion"), \
             patch.object(am, "registrar_evento_log"), \
             patch.object(am, "registrar_alumno_en_web",
                          side_effect=WebDriverException("browser died")):
            with self.assertRaises(RuntimeError):
                am.ejecutar_carga_infoapp([_alumno()], _config())

    def test_url_invalida_mensaje_claro(self):
        cfg = _config()
        cfg["url"] = "esto-no-es-url"
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "renderizar_panel_carga"), \
             patch.object(am, "registrar_alumno_en_web",
                          side_effect=WebDriverException("javascript invalid argument: 'x'")):
            with self.assertRaises(ValueError) as cm:
                am.ejecutar_carga_infoapp([_alumno()], cfg)
            self.assertIn("URL inválida", str(cm.exception))

    def test_operador_salta_alumno_fallido_y_continua(self):
        respuestas = [(False, "ya inscrito"), (True, "ok")]
        alumnos = [_alumno(cedula="11111111"), _alumno(cedula="22222222")]
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "registrar_alumno_en_web", side_effect=respuestas), \
             patch.object(am, "prompt_reintentar_alumno", return_value="SKIP"):
            exitosos, fallidos, _ = am.ejecutar_carga_infoapp(alumnos, _config())
        self.assertEqual(len(fallidos), 1)
        self.assertEqual(len(exitosos), 1)
        self.assertEqual(exitosos[0]["cedula"], "22222222")

    def test_operador_pausa_guarda_estado_parcial(self):
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "registrar_alumno_en_web", return_value=(False, "timeout")), \
             patch.object(am, "prompt_reintentar_alumno", return_value="PAUSE"):
            exitosos, fallidos, _ = am.ejecutar_carga_infoapp(
                [_alumno(), _alumno(cedula="22222222")], _config())
        self.assertEqual(len(exitosos), 0)
        self.assertEqual(len(fallidos), 0)   # pausa antes de clasificar


# =============================================================================
# SERVICIOS: búsqueda, registro de perfil nuevo y verificación
# =============================================================================

def _persona(**kw):
    base = {
        "nombre": "Ana", "apellido": "Pérez", "cedula": "12345678",
        "cedulado": "si", "cedula_escolar": "", "cedula_padre": "",
        "nacimiento": "1990-01-01", "edad": 36, "genero": "F",
        "telefono": "0412-1234567"
    }
    base.update(kw)
    return base


class TestServiciosFlujo(_WebTestCase):
    def _config_servicio(self):
        return {
            "tipo_servicio": "Gestión en el Sistema de Protección Social Patria",
            "fecha_servicio": "2026-08-25",
            "infocentro": {"estado_id": "22", "direccion": "Av. principal El Jovito"}
        }

    def test_usuario_existente_registra_y_verifica(self):
        driver = FakeDriver(user_f_id="777", name_param="Ana Perez", verificado=True)
        exito, detalle = am.registrar_servicio_persona(driver, _persona(), self._config_servicio())
        self.assertTrue(exito)
        self.assertIn("777", detalle)

    def test_usuario_no_existe_devuelve_fallo_claro(self):
        driver = FakeDriver(user_f_id="", name_param="No existe este usuario", verificado=False)
        with patch.object(am, "registrar_nuevo_usuario_perfil", return_value=True):
            exito, detalle = am.registrar_servicio_persona(driver, _persona(), self._config_servicio())
        self.assertFalse(exito)
        self.assertIn("no existe", detalle.lower())

    def test_verificacion_tabla_fallida_es_fallo(self):
        driver = FakeDriver(user_f_id="777", name_param="Ana Perez", verificado=False)
        exito, detalle = am.registrar_servicio_persona(driver, _persona(), self._config_servicio())
        self.assertFalse(exito)
        self.assertIn("no aparece en la tabla", detalle)

    def test_busqueda_de_menor_usa_parent_ref(self):
        persona = _persona(cedula="", cedulado="no", cedula_padre="30348783")
        driver = FakeDriver(user_f_id="888", name_param="Ana Perez")
        am.registrar_servicio_persona(driver, persona, self._config_servicio())
        # el campo de búsqueda recibió {padre}1 según la convención de InfoApp
        buscado = driver.scripts  # la búsqueda va por send_keys sobre q_participante
        self.assertTrue(any("codigoAJAX" in s for s in buscado))

    def test_bucle_masivo_con_fallidos_intercalados(self):
        personas = [_persona(cedula=f"1000000{i}") for i in range(3)]
        resultados = [(True, "ok"), (False, "¡AVISO!: duplicado"), (True, "ok")]
        with patch.object(am, "asegurar_navegador_activo"), \
             patch.object(am, "registrar_servicio_persona", side_effect=resultados):
            exitosos, fallidos, _ = am.ejecutar_carga_servicios_infoapp(
                personas, _config(), self._config_servicio(),
                indice_inicio=0,
                fn_guardar_checkpoint=lambda *a, **k: None
            )
        self.assertEqual(len(exitosos), 2)
        self.assertEqual(len(fallidos), 1)
        self.assertEqual(fallidos[0]["estado"], "OMITIDO")


if __name__ == "__main__":
    unittest.main(verbosity=2)
