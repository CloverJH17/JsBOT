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

    @patch("selenium.webdriver.Chrome")
    def test_03_driver_factory_timeouts_y_resiliencia(self, mock_chrome):
        """Verifica que la factoría configure los timeouts de socket obligatorios."""
        instancia_mock = MagicMock()
        mock_chrome.return_value = instancia_mock
        
        driver = obtener_driver_resiliente(headless=True)
        self.assertIsNotNone(driver)
        instancia_mock.set_page_load_timeout.assert_called_with(30)
        instancia_mock.set_script_timeout.assert_called_with(20)

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
        """Verifica que limpiar_overlays y esperar_desbloqueo_ajax no lancen excepciones si el driver falla."""
        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = Exception("Driver desconectado")
        try:
            limpiar_overlays(mock_driver)
            esperar_desbloqueo_ajax(mock_driver, timeout=1)
        except Exception as e:
            self.fail(f"web_utils no atrapó la excepción: {e}")

    @patch("selenium.webdriver.Firefox")
    def test_08_driver_factory_preferencia_navegador(self, mock_firefox):
        """Verifica que si se especifica navegador preferido, se intente primero."""
        instancia_mock = MagicMock()
        mock_firefox.return_value = instancia_mock
        driver = obtener_driver_resiliente(headless=True, navegador_preferido="firefox")
        self.assertIsNotNone(driver)
        mock_firefox.assert_called_once()

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
            self.fail(f"Fallo en la reanudación de sesión: {e}")

if __name__ == "__main__":
    unittest.main()
