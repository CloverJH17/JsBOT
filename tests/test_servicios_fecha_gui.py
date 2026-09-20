"""
SUITE DE PRUEBAS PARA SELECTOR DE FECHA Y VALIDACIÓN EN SERVICIOS (GUI) — JsBOT
Valida que el selector de calendario nativo, atajo 'Hoy' y validación estricta de fecha funcionen adecuadamente.
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import tkinter as tk

from modulos.normalizador_datos import limpiar_fecha
from modulos.interfaz_grafica import JsBotGUI

class TestServiciosFechaGUI(unittest.TestCase):

    def test_01_limpiar_y_normalizar_fechas_servicios(self):
        """Verifica que diversos formatos de fecha sean normalizados a ISO YYYY-MM-DD."""
        self.assertEqual(limpiar_fecha("2026-03-15"), "2026-03-15")
        self.assertEqual(limpiar_fecha("15/03/2026"), "2026-03-15")
        self.assertEqual(limpiar_fecha("15-03-2026"), "2026-03-15")
        self.assertEqual(limpiar_fecha("01/01/2025"), "2025-01-01")

    def test_02_establecer_fecha_hoy(self):
        """Verifica que el método helper _establecer_fecha_hoy asigne la fecha actual en YYYY-MM-DD."""
        gui = MagicMock(spec=JsBotGUI)
        entry_mock = MagicMock()
        
        # Ejecutar método real unbound
        JsBotGUI._establecer_fecha_hoy(gui, entry_mock)
        
        entry_mock.delete.assert_called_once_with(0, tk.END)
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        entry_mock.insert.assert_called_once_with(0, hoy_str)

    def test_03_validacion_fecha_en_iniciar_servicios_fecha_invalida(self):
        """Verifica que una fecha inválida muestre modal de error y detenga el flujo."""
        gui = MagicMock(spec=JsBotGUI)
        gui.ejecutando_tarea = False
        gui.participantes_cargados = [{"cedula": "12345678", "nombre": "Test", "apellido": "User"}]
        gui.entry_url_servicios = MagicMock()
        gui.entry_url_servicios.get.return_value = "https://infoapp2.infocentro.gob.ve/admin/index.php?r=service/create&id_service=99"
        gui.usuario_activo = "admin"
        gui.clave_activa = "secret"
        gui.entry_fecha_servicios = MagicMock()
        gui.entry_fecha_servicios.get.return_value = "32/13/2026" # Fecha inválida

        # Ejecutar método real
        JsBotGUI._iniciar_ejecucion_asincrona_servicios(gui)

        # Debe registrar error y mostrar modal de error
        gui._mostrar_modal_mensaje.assert_called_once()
        call_args = gui._mostrar_modal_mensaje.call_args
        self.assertEqual(call_args.kwargs.get("tipo"), "error")
        self.assertIn("Fecha de Servicio Inválida", call_args.kwargs.get("titulo"))
        self.assertFalse(gui.ejecutando_tarea)

if __name__ == "__main__":
    unittest.main()
