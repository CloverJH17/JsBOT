#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de contratos GUI que no requieren servidor gráfico."""
import queue
import threading
import unittest
from unittest.mock import MagicMock

from modulos.interfaz_grafica import JsBotGUI, normalizar_clave_vista


class FakeModal:
    def __init__(self):
        self.grab_set_calls = 0
        self.grab_release_calls = 0
        self.destroyed = False
        self.protocols = {}
        self.exists = True

    def grab_set(self):
        self.grab_set_calls += 1

    def grab_release(self):
        self.grab_release_calls += 1

    def protocol(self, name, callback):
        self.protocols[name] = callback

    def winfo_exists(self):
        return self.exists and not self.destroyed

    def destroy(self):
        self.destroyed = True


class TestGUIContractsNueva(unittest.TestCase):
    def test_normalizacion_de_vistas_acepta_aliases(self):
        self.assertEqual(normalizar_clave_vista("Diagnóstico"), "Diagnostico")
        self.assertEqual(normalizar_clave_vista("  créditos  "), "Creditos")
        self.assertEqual(normalizar_clave_vista("auditoria"), "Reportes")
        self.assertEqual(normalizar_clave_vista("planillas"), "Planillas")

    def test_registro_y_cierre_de_modal_liberan_grab_y_callback(self):
        app = JsBotGUI.__new__(JsBotGUI)
        app.modales_activos = {}
        modal = FakeModal()
        cerrado = []

        JsBotGUI.registrar_modal(app, "prueba", modal, grab=True, al_cerrar=lambda: cerrado.append(True))
        self.assertIn("prueba", app.modales_activos)
        self.assertEqual(modal.grab_set_calls, 1)
        self.assertIn("WM_DELETE_WINDOW", modal.protocols)

        modal.protocols["WM_DELETE_WINDOW"]()
        self.assertEqual(modal.grab_release_calls, 1)
        self.assertEqual(cerrado, [True])
        self.assertNotIn("prueba", app.modales_activos)
        self.assertTrue(modal.destroyed)

    def test_log_desde_hilo_se_envia_a_cola(self):
        app = JsBotGUI.__new__(JsBotGUI)
        app.cola_eventos = queue.Queue()

        worker = threading.Thread(target=JsBotGUI._agregar_log, args=(app, "evento de hilo"))
        worker.start()
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(app.cola_eventos.get_nowait(), ("log", "evento de hilo"))

    def test_cierra_varios_modales_sin_duplicados(self):
        app = JsBotGUI.__new__(JsBotGUI)
        app.modales_activos = {"a": FakeModal(), "b": FakeModal()}
        JsBotGUI.cerrar_modales_activos(app)
        self.assertEqual(app.modales_activos, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
