"""
SUITE DE PRUEBAS PARA GENERACIÓN DIRECTA DE PLANILLAS Y FICHA FORMATIVA (GUI & CORE) — JsBOT
Valida la carga y edición de datos de actividad, la inyección en generador_planilla,
y el flujo de la interfaz gráfica sin requerir automatización web.
"""
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import entorno
from modulos import config_manager as cm
from modulos import generador_planilla as gp
from modulos.interfaz_grafica import JsBotGUI


class TestGeneracionDirectaPlanillasGUI(unittest.TestCase):

    def test_01_constante_archivo_datos_actividad(self):
        """Verifica que entorno.py defina ARCHIVO_DATOS_ACTIVIDAD y apunte al JSON correspondiente."""
        self.assertTrue(hasattr(entorno, "ARCHIVO_DATOS_ACTIVIDAD"))
        self.assertTrue(str(entorno.ARCHIVO_DATOS_ACTIVIDAD).endswith("datos_actividad.json"))

    def test_02_config_manager_cargar_y_guardar_datos_actividad(self):
        """Verifica que config_manager cargue y guarde la ficha de datos de actividad correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_json = os.path.join(tmpdir, "datos_actividad_test.json")
            datos_test = {
                "nombre_facilitador": "Facilitador de Prueba",
                "cedula_facilitador": "V-99999999",
                "nombre_infocentro": "Infocentro Experimental",
                "codigo_infocentro": "TEST01",
                "modulo": "Automatización Python",
                "contenido": "Pruebas de Software",
                "hora_inicio": "08:00 am",
                "hora_fin": "12:00 pm"
            }
            with patch.object(entorno, "ARCHIVO_DATOS_ACTIVIDAD", tmp_json):
                ok = cm.guardar_datos_actividad(datos_test)
                self.assertTrue(ok)
                self.assertTrue(os.path.exists(tmp_json))

                recuperado = cm.cargar_datos_actividad()
                self.assertEqual(recuperado["nombre_facilitador"], "Facilitador de Prueba")
                self.assertEqual(recuperado["codigo_infocentro"], "TEST01")
                self.assertEqual(recuperado["contenido"], "Pruebas de Software")

    def test_03_parsear_metadatos_url_con_datos_actividad(self):
        """Verifica que parsear_metadatos_url use los datos de actividad por defecto cuando no vienen en la URL."""
        metadatos_falsos = {
            "nombre_facilitador": "Docente Mock",
            "cedula_facilitador": "V-11111111",
            "nombre_infocentro": "Infocentro Mock",
            "codigo_infocentro": "MOCK01",
            "modulo": "Módulo Mock",
            "contenido": "Contenido Mock",
            "hora_inicio": "09:00 am",
            "hora_fin": "01:00 pm"
        }
        with patch("modulos.config_manager.cargar_datos_actividad", return_value=metadatos_falsos):
            url = "https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=555"
            meta = gp.parsear_metadatos_url(url)
            self.assertEqual(meta["id_actividad"], "555")
            self.assertEqual(meta["nombre_facilitador"], "Docente Mock")
            self.assertEqual(meta["codigo_infocentro"], "MOCK01")
            self.assertEqual(meta["modulo"], "Módulo Mock")

    def test_04_gui_descartar_archivo_planillas(self):
        """Verifica que _descartar_archivo_planillas limpie el estado en memoria y la UI."""
        gui = MagicMock()
        gui.archivo_seleccionado_planillas = MagicMock()
        gui.participantes_cargados_planillas = [{"nombre": "Juan"}]
        gui.datos_normalizados_planillas = MagicMock()
        gui.reporte_deduplicacion_planillas = {"total": 1}
        gui.btn_descartar_planillas = MagicMock()
        gui.card_prevuelo_planillas = MagicMock()
        gui.card_prevuelo_planillas.winfo_manager.return_value = "pack"

        with patch("customtkinter.CTkFont"):
            # Ejecutar el método real
            JsBotGUI._descartar_archivo_planillas(gui)

        self.assertEqual(gui.participantes_cargados_planillas, [])
        self.assertEqual(gui.datos_normalizados_planillas, [])
        self.assertIsNone(gui.reporte_deduplicacion_planillas)
        gui.archivo_seleccionado_planillas.set.assert_called_with("Ningún archivo seleccionado")
        gui.btn_descartar_planillas.pack_forget.assert_called_once()
        gui.card_prevuelo_planillas.pack_forget.assert_called_once()

    def test_05_gui_iniciar_generacion_sin_participantes(self):
        """Verifica que _iniciar_generacion_planilla_directa muestre advertencia si no hay archivo cargado."""
        gui = MagicMock()
        gui.participantes_cargados_planillas = []
        gui._mostrar_modal_mensaje = MagicMock()

        JsBotGUI._iniciar_generacion_planilla_directa(gui)

        gui._mostrar_modal_mensaje.assert_called_once()
        self.assertEqual(gui._mostrar_modal_mensaje.call_args[1]["titulo"], "Archivo Requerido")

    def test_06_gui_iniciar_generacion_directa_ejecuta_generador(self):
        """Verifica que _iniciar_generacion_planilla_directa invoque generar_planilla_multiformato con los parámetros correctos."""
        gui = MagicMock()
        gui.participantes_cargados_planillas = [{"nombre": "Ana", "apellido": "Perez", "cedula": "12345678"}]
        gui.entry_id_url_planillas = MagicMock()
        gui.entry_id_url_planillas.get.return_value = "777"
        gui.menu_formato_planillas = MagicMock()
        gui.menu_formato_planillas.get.return_value = "Microsoft Excel (.xlsx)"
        gui._mostrar_modal_exito_planilla = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("modulos.generador_planilla.generar_planilla_multiformato", return_value=tmp_path) as mock_gen:
                JsBotGUI._iniciar_generacion_planilla_directa(gui)

                mock_gen.assert_called_once_with(
                    participantes=gui.participantes_cargados_planillas,
                    id_actividad="777",
                    url_actividad="",
                    formato="xlsx"
                )
                gui._mostrar_modal_exito_planilla.assert_called_once_with(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
