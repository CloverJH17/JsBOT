"""
SUITE DE PRUEBAS PARA SELECTOR DE ACTIVIDAD / SERVICIO (GUI & CONFIG) — JsBOT
Valida la centralización de configuración en config_manager, entorno.py y el selector desplegable en la GUI.
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import tkinter as tk
import customtkinter as ctk

from modulos import entorno
from modulos import config_manager as cm
from modulos import gestor_sesion as gs
from modulos.interfaz_grafica import JsBotGUI


class TestServiciosSelectorActividad(unittest.TestCase):

    def test_01_ruta_canonica_en_entorno(self):
        """Verifica que entorno.py defina ARCHIVO_CONFIG_SERVICIOS."""
        self.assertTrue(hasattr(entorno, "ARCHIVO_CONFIG_SERVICIOS"))
        self.assertTrue(str(entorno.ARCHIVO_CONFIG_SERVICIOS).endswith("config_servicios.json"))
        self.assertTrue(os.path.exists(entorno.ARCHIVO_CONFIG_SERVICIOS))

    def test_02_config_manager_cargar_servicios(self):
        """Verifica que config_manager.cargar_config_servicios devuelva el catálogo y el valor por defecto correcto."""
        cfg = cm.cargar_config_servicios()
        self.assertIn("catalogo_servicios", cfg)
        self.assertIn("servicio_por_defecto", cfg)
        self.assertEqual(cfg["servicio_por_defecto"], "Actividades de educación o aprendizaje")
        self.assertIn("Actividades de educación o aprendizaje", cfg["catalogo_servicios"])
        self.assertIn("Gestión en el Sistema de Protección Social Patria", cfg["catalogo_servicios"])

    def test_03_gestor_sesion_delegacion(self):
        """Verifica que gestor_sesion delegue en config_manager sin fallos."""
        cfg = gs.cargar_config_servicios()
        self.assertEqual(cfg["servicio_por_defecto"], "Actividades de educación o aprendizaje")
        self.assertIsInstance(cfg["catalogo_servicios"], list)
        self.assertGreater(len(cfg["catalogo_servicios"]), 10)

    def test_04_extraccion_tipo_servicio_en_iniciar_servicios(self):
        """Verifica que _iniciar_ejecucion_asincrona_servicios extraiga el valor directamente desde el selector."""
        gui = MagicMock()
        gui.ejecutando_tarea = False
        gui.participantes_cargados = [{"cedula": "12345678", "nombre": "Test", "apellido": "User", "cedulado": "si"}]
        gui.entry_url_servicios = MagicMock()
        gui.entry_url_servicios.get.return_value = "https://infoapp2.infocentro.gob.ve/admin/index.php?r=service/create&id_service=77"
        gui.usuario_activo = "operador"
        gui.clave_activa = "secret"
        gui.entry_fecha_servicios = MagicMock()
        gui.entry_fecha_servicios.get.return_value = "2026-09-19"
        gui.var_modo_visible_servicios = MagicMock()
        gui.var_modo_visible_servicios.get.return_value = True

        # Simular el OptionMenu con una selección específica
        gui.menu_tipo_servicio = MagicMock()
        gui.menu_tipo_servicio.get.return_value = "Operaciones bancarias por Internet"

        with patch("threading.Thread") as mock_thread, \
             patch("builtins.open", unittest.mock.mock_open()):
            JsBotGUI._iniciar_ejecucion_asincrona_servicios(gui)
            mock_thread.assert_called_once()
            # Inspeccionar config_servicio pasado como argumento al hilo
            _, kwargs = mock_thread.call_args
            args = mock_thread.call_args[1].get("args") or mock_thread.call_args[0]
            # args: (usuarios, config_bot, config_servicio)
            config_servicio = mock_thread.call_args[1].get("args", (None, None, None))[2]
            self.assertEqual(config_servicio["tipo_servicio"], "Operaciones bancarias por Internet")
            self.assertEqual(config_servicio["fecha_servicio"], "2026-09-19")
            self.assertEqual(config_servicio["id_servicio"], "77")


if __name__ == "__main__":
    unittest.main()
