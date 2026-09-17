"""
SUITE DE REGRESIÓN INTEGRAL, CONTRATOS API Y COMPORTAMIENTO DE GUI — JsBOT
"""
import unittest
from unittest.mock import MagicMock, patch
import modulos.entorno as entorno
from modulos.identidad_utils import limpiar_cedula_universal, formatear_telefono_venezolano, formatear_nombre_institucional
from modulos.driver_factory import obtener_driver_resiliente
from modulos.interfaz_grafica import JsBotGUI
from modulos.web_utils import limpiar_overlays, esperar_desbloqueo_ajax
from modulos.normalizador_datos import (
    resolver_huerfanos_de_documento,
    resolver_fechas_faltantes,
    resolver_telefonos_faltantes
)

class TestCentralizacionEcosistema(unittest.TestCase):

    def test_01_rutas_entorno_universales(self):
        """Certifica que las rutas universales existan físicamente en el entorno."""
        self.assertTrue(entorno.RAIZ_PROYECTO.exists())
        self.assertTrue(entorno.CARPETA_CONFIG.exists())
        self.assertTrue(entorno.CARPETA_LOGS.exists())

    def test_02_contrato_identidad_institucional(self):
        """Valida que el saneamiento de datos cumpla con las reglas institucionales."""
        self.assertEqual(limpiar_cedula_universal(" 26.123.456 "), "V-26123456")
        self.assertEqual(limpiar_cedula_universal("E-84.999.111"), "E-84999111")
        self.assertEqual(formatear_telefono_venezolano("04121234567"), "0412-1234567")
        self.assertEqual(formatear_telefono_venezolano("", default="0412-0000000"), "0412-0000000")
        self.assertEqual(formatear_nombre_institucional("juan de la rosa"), "Juan de la Rosa")

    def test_03_driver_factory_devuelve_tupla_playwright(self):
        """Verifica que obtener_driver_resiliente devuelve (pw, context) con Playwright."""
        mock_pw = MagicMock()
        mock_context = MagicMock()
        with patch("modulos.driver_factory.sync_playwright") as mock_sp:
            mock_sp.return_value.__enter__ = lambda s: mock_pw
            mock_sp.return_value.__exit__ = MagicMock(return_value=False)
            mock_pw.chromium.launch_persistent_context.return_value = mock_context
            resultado = obtener_driver_resiliente(headless=True)
        self.assertIsInstance(resultado, tuple)
        self.assertEqual(len(resultado), 2)

    def test_04_gui_render_y_comportamiento_desacoplado(self):
        """Comprueba que la interfaz gráfica instancie sus componentes sin congelar el hilo."""
        try:
            app = JsBotGUI()
            app.withdraw()  # Ocultar ventana física durante el test automatizado

            # Verificar existencia de vistas desacopladas
            self.assertIn("Reportes", app.vistas)
            self.assertIn("Formación", app.vistas)

            app.destroy()
        except Exception as e:
            self.fail(f"La interfaz gráfica colapsó al instanciarse: {e}")

    def test_05_casos_borde_identidad(self):
        """Prueba casos borde: entradas vacías, minúsculas, flotantes de Excel y prefijos extranjeros inválidos."""
        self.assertEqual(limpiar_cedula_universal(""), "")
        self.assertEqual(limpiar_cedula_universal(None), "")
        self.assertEqual(limpiar_cedula_universal("v-12.345.678"), "V-12345678")
        self.assertEqual(limpiar_cedula_universal("e-84.321.000"), "E-84321000")
        self.assertEqual(limpiar_cedula_universal(30348783.0), "V-30348783")
        self.assertEqual(limpiar_cedula_universal("00000000"), "")
        self.assertEqual(limpiar_cedula_universal("123"), "")
        self.assertEqual(limpiar_cedula_universal("SD"), "")
        self.assertEqual(formatear_telefono_venezolano("+58 424 1234567"), "0424-1234567")
        self.assertEqual(formatear_telefono_venezolano("4161234567"), "0416-1234567")
        self.assertEqual(formatear_telefono_venezolano(4121234567.0), "0412-1234567")
        # Números extranjeros no venezolanos deben retornar el default
        self.assertEqual(formatear_telefono_venezolano("+1 555-1234567"), "0412-0000000")
        self.assertEqual(formatear_telefono_venezolano("12345678901"), "0412-0000000")
        self.assertEqual(formatear_nombre_institucional(""), "")
        self.assertEqual(formatear_nombre_institucional("MARIA DE LOS ANGELES"), "Maria de los Angeles")

    def test_06_compuertas_etl_no_bloqueantes(self):
        """Verifica que las funciones de resolución de huerfanos, fechas y teléfonos no bloqueen."""
        participantes = [
            {"nombre": "Carlos", "apellido": "Perez", "cedulado": "sin_documento", "edad": 25, "nacimiento": "", "telefono": ""},
            {"nombre": "Ana", "apellido": "Gomez", "cedula": "12345678", "cedulado": "si", "edad": None, "nacimiento": "2000-05-10", "telefono": "0414-1112233"}
        ]
        # Modo no interactivo (GUI)
        res_doc = resolver_huerfanos_de_documento(participantes, modo_interactivo=False)
        self.assertEqual(len(res_doc), 2)

        res_fechas = resolver_fechas_faltantes(participantes, modo_interactivo=False, anio_referencia=2026)
        self.assertEqual(res_fechas[0]["nacimiento"], "2001-01-01")

        res_tlf = resolver_telefonos_faltantes(participantes, modo_interactivo=False)
        self.assertEqual(res_tlf[0]["telefono"], "0412-0000000")

    def test_07_web_utils_tolerancia_fallos(self):
        """Verifica que limpiar_overlays y esperar_desbloqueo_ajax no lancen excepciones si la page falla."""
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = Exception("Página desconectada")
        mock_page.wait_for_function.side_effect = Exception("Timeout de AJAX")
        try:
            limpiar_overlays(mock_page)
            esperar_desbloqueo_ajax(mock_page, timeout=1)
        except Exception as e:
            self.fail(f"web_utils no atrapó la excepción: {e}")

    def test_08_driver_factory_navegador_por_defecto_es_chromium(self):
        """Verifica que la prioridad de navegadores por defecto empiece con chromium."""
        from modulos import config_manager as _cm
        self.assertIn("chromium", _cm.DEFAULTS["browser"]["priority"])
        self.assertEqual(_cm.DEFAULTS["browser"]["priority"][0], "chromium")

    def test_09_gui_resurreccion_reanudacion_indice(self):
        """Verifica que el diálogo de resurrección preserve el índice_inicio para no reiniciar en cero."""
        try:
            app = JsBotGUI()
            app.withdraw()
            estado_simulado = {
                "participantes": [
                    {"nombre": "P1", "cedula": "11111111"},
                    {"nombre": "P2", "cedula": "22222222"},
                    {"nombre": "P3", "cedula": "33333333"}
                ],
                "indice_ultimo_procesado": 2,
                "url": "https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=999"
            }
            app._reanudar_flujo_desde_estado(estado_simulado, tipo="formacion")
            self.assertEqual(getattr(app, "indice_inicio_recuperacion_formacion", 0), 2)
            self.assertEqual(len(app.participantes_cargados), 3)
            app.destroy()
        except Exception as e:
            if "Tcl" in type(e).__name__ or "tk" in str(e).lower():
                self.skipTest(f"Entorno Tkinter no disponible para prueba GUI aislada: {e}")
            else:
                self.fail(f"Fallo en la reanudación de sesión: {e}")

if __name__ == "__main__":
    unittest.main()
