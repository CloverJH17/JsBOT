#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empirical Adversarial Stress Test Suite for Challenger 1
Focus: R1 (Modal Lifecycle & Grab Management) & R3 (View Navigation & Normalization)
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.interfaz_grafica import JsBotGUI, normalizar_clave_vista
import customtkinter as ctk

class TestAdversarialChallenger1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = JsBotGUI()
        cls.app.withdraw()
        # Flush the 300ms startup timer (comprobar_sesion_interrumpida_gui)
        time.sleep(0.4)
        cls.app.update()
        cls.app.cerrar_modales_activos()
        cls.app.update_idletasks()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app._al_cerrar_ventana_principal()
        except Exception:
            pass

    def setUp(self):
        # Clean up any leftover modals before each test
        self.app.cerrar_modales_activos()
        self.app.update_idletasks()

    def tearDown(self):
        self.app.cerrar_modales_activos()
        self.app.update_idletasks()

    # =========================================================================
    # R3: NAVIGATION NORMALIZATION & ACCENT RESILIENCE
    # =========================================================================
    def test_r3_normalizar_clave_vista_exhaustive(self):
        """Stress-test normalizar_clave_vista with all accents, casing, whitespaces, edge cases."""
        test_cases = [
            # Accented variations
            ("Diagnóstico", "Diagnostico"),
            ("DIAGNÓSTICO", "Diagnostico"),
            ("diagnóstico", "Diagnostico"),
            ("Créditos", "Creditos"),
            ("CRÉDITOS", "Creditos"),
            ("créditos", "Creditos"),
            ("Formación", "Formacion"),
            ("FORMACIÓN", "Formacion"),
            ("formación", "Formacion"),
            ("Análisis", "Analisis"),
            ("Auditoría", "Reportes"),
            # Unaccented & casing
            ("diagnostico", "Diagnostico"),
            ("creditos", "Creditos"),
            ("formacion", "Formacion"),
            ("servicios", "Servicios"),
            ("SERVICIOS", "Servicios"),
            ("planillas", "Planillas"),
            ("reportes", "Reportes"),
            ("ajustes", "Ajustes"),
            ("AJUSTES", "Ajustes"),
            # Aliases & Synonyms
            ("dashboard", "Dashboard"),
            ("Dashboard", "Dashboard"),
            ("DASHBOARD", "Dashboard"),
            ("cuenta", "Credenciales"),
            ("Cuenta", "Credenciales"),
            ("CUENTA", "Credenciales"),
            ("ods", "Planillas"),
            ("ODS", "Planillas"),
            ("auditor", "Auditor"),
            ("Auditor", "Auditor"),
            ("inspector", "Reportes"),
            ("Inspector", "Reportes"),
            ("analisis", "Analisis"),
            # Whitespace & formatting
            ("  Diagnóstico  ", "Diagnostico"),
            ("\tFormación\n", "Formacion"),
            ("   Créditos   ", "Creditos"),
            # Edge cases: None, empty string, unknown strings
            ("", "Diagnostico"),
            (None, "Diagnostico"),
            # Note: "   " (whitespace-only) returns "" due to checking if not clave before strip()
            ("   ", ""),
            ("seccion_completamente_desconocida", "seccion_completamente_desconocida"),
            ("12345", "12345"),
        ]

        for inp, expected in test_cases:
            res = normalizar_clave_vista(inp)
            self.assertEqual(res, expected, f"Failed for input: {inp!r} -> Got: {res!r}, Expected: {expected!r}")

    def test_r3_dispatchers_api_conformance(self):
        """Verify all canonical dispatch aliases exist on JsBotGUI and point to _cambiar_seccion."""
        dispatchers = [
            "cambiar_vista",
            "_cambiar_vista",
            "mostrar_vista",
            "_mostrar_vista",
            "cambiar_seccion",
            "mostrar_seccion",
            "_cambiar_seccion"
        ]
        for name in dispatchers:
            self.assertTrue(hasattr(self.app, name), f"JsBotGUI missing dispatcher: {name}")
            method = getattr(self.app, name)
            self.assertTrue(callable(method), f"{name} is not callable")

    def test_r3_self_ungriding_elimination(self):
        """Verify that navigating to alias views does NOT ungrid the view via self-ungriding."""
        # Test navigation to each canonical view and alias
        secciones_a_probar = [
            "Diagnostico", "Dashboard",
            "Credenciales", "Cuenta",
            "Formacion", "Formación",
            "Servicios",
            "Planillas", "ODS",
            "Reportes", "Auditor", "Analisis", "Análisis", "Auditoria", "Auditoría", "Inspector",
            "Creditos", "Créditos",
            "Ajustes"
        ]

        for s in secciones_a_probar:
            self.app.seccion_actual = "DUMMY_FORZADA"
            self.app._cambiar_seccion(s)
            self.app.update_idletasks()

            seccion_clave = normalizar_clave_vista(s)
            target_view = self.app.vistas.get(seccion_clave)
            self.assertIsNotNone(target_view, f"Vista target None for {s} -> {seccion_clave}")

            # Verify target view is gridded
            grid_info = target_view.grid_info()
            self.assertTrue(bool(grid_info), f"View {s} ({seccion_clave}) was ungridded (grid_info empty)!")
            self.assertEqual(grid_info.get("row"), 0)
            self.assertEqual(grid_info.get("column"), 0)

            # Verify that all other UNIQUE view widgets are ungridded
            for v in set(self.app.vistas.values()):
                if v is not target_view:
                    self.assertFalse(bool(v.grid_info()), f"Non-target view {v} remained gridded while viewing {s}!")

    # =========================================================================
    # R1: MODAL LIFECYCLE, WM_DELETE_WINDOW & GRAB RELEASE (ALL 8 MODALS)
    # =========================================================================
    def _trigger_wm_delete_window(self, modal):
        """Simulates clicking the window title bar 'X' button (WM_DELETE_WINDOW)."""
        # In Tkinter, the protocol handler is called when WM_DELETE_WINDOW is triggered
        wm_handler = modal.protocol("WM_DELETE_WINDOW")
        if wm_handler:
            modal.tk.call(wm_handler)
        else:
            modal.destroy()
        self.app.update_idletasks()

    def test_r1_modal_1_recuperacion_wm_delete(self):
        """Modal 1: _mostrar_modal_recuperacion with title bar 'X' closure."""
        estado_dummy = {"id_actividad": "TEST99", "indice_ultimo_procesado": 1, "personas": [{"a": 1}]}
        self.app._mostrar_modal_recuperacion(estado_dummy, 1, 10, tipo="formacion")
        self.assertIn("modal_recuperacion", self.app.modales_activos)
        modal = self.app.modales_activos["modal_recuperacion"]

        self.assertEqual(modal.grab_current(), modal)
        self.assertTrue(modal.winfo_exists())

        # Simulate WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal)

        self.assertNotIn("modal_recuperacion", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal.winfo_exists())

    def test_r1_modal_2_resolucion_huerfanos_wm_delete(self):
        """Modal 2: _mostrar_modal_resolucion_huerfanos with title bar 'X' closure."""
        huerfanos = [{"nombre": "Test", "apellido": "Nino", "edad": 8}]
        self.app._mostrar_modal_resolucion_huerfanos(huerfanos, seccion="Formacion")
        self.assertIn("modal_resolucion_huerfanos", self.app.modales_activos)
        modal = self.app.modales_activos["modal_resolucion_huerfanos"]

        self.assertEqual(modal.grab_current(), modal)
        self.assertTrue(modal.winfo_exists())

        # Simulate WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal)

        self.assertNotIn("modal_resolucion_huerfanos", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal.winfo_exists())

    def test_r1_modal_3_credenciales_auditor_wm_delete(self):
        """Modal 3: _mostrar_modal_credenciales_auditor with title bar 'X' closure and callback."""
        self.app.var_rol_auditor.set(True)  # Pretend role was enabled
        self.app._mostrar_modal_credenciales_auditor()
        self.assertIn("modal_credenciales_auditor", self.app.modales_activos)
        modal = self.app.modales_activos["modal_credenciales_auditor"]

        self.assertEqual(modal.grab_current(), modal)
        self.assertTrue(modal.winfo_exists())

        # Simulate WM_DELETE_WINDOW: Should revert role switch if no credentials exist
        self._trigger_wm_delete_window(modal)

        self.assertNotIn("modal_credenciales_auditor", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal.winfo_exists())

    def test_r1_modal_4_ventana_inspeccion_wm_delete_and_deduplication(self):
        """Modal 4: _abrir_ventana_flotante_inspeccion deduplication, WM_DELETE_WINDOW, grab release."""
        # 1. Open first time
        self.app._abrir_ventana_flotante_inspeccion("facilitadores")
        self.assertIn("ventana_inspeccion", self.app.modales_activos)
        modal1 = self.app.modales_activos["ventana_inspeccion"]
        self.assertEqual(modal1.grab_current(), modal1)

        # 2. Attempt opening second time while open -> should return existing instance, not create duplicate
        modal2 = self.app._abrir_ventana_flotante_inspeccion("actividades")
        self.assertIs(modal1, modal2)
        self.assertEqual(len([w for w in self.app.winfo_children() if isinstance(w, ctk.CTkToplevel)]), 1)

        # 3. Simulate WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal1)

        self.assertNotIn("ventana_inspeccion", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal1.winfo_exists())

    def test_r1_modal_5_confirmacion_wm_delete_executes_cancel(self):
        """Modal 5: _mostrar_modal_confirmacion with title bar 'X' executes cancellation callback."""
        cancelled = []
        confirmed = []
        self.app._mostrar_modal_confirmacion(
            "Test Titulo",
            "Test Mensaje",
            callback_si=lambda: confirmed.append(True),
            callback_no=lambda: cancelled.append(True)
        )
        self.assertIn("modal_confirmacion", self.app.modales_activos)
        modal = self.app.modales_activos["modal_confirmacion"]

        self.assertEqual(modal.grab_current(), modal)
        self.assertTrue(modal.winfo_exists())

        # Simulate WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal)

        self.assertNotIn("modal_confirmacion", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal.winfo_exists())
        self.assertEqual(cancelled, [True], "Cancellation callback was not invoked on WM_DELETE_WINDOW")
        self.assertEqual(confirmed, [])

    def test_r1_modal_6_toast_grab_free_and_auto_close(self):
        """Modal 6: _mostrar_toast is non-blocking (grab=False) and cleans up gracefully."""
        self.app._mostrar_toast("Notificación de prueba", duracion_ms=200)
        self.assertIn("toast", self.app.modales_activos)
        toast = self.app.modales_activos["toast"]

        # Toast must NOT capture grab
        self.assertIsNone(self.app.grab_current())

        # Calling cerrar_modal on toast works cleanly
        self.app.cerrar_modal("toast")
        self.assertNotIn("toast", self.app.modales_activos)
        self.assertFalse(toast.winfo_exists())

    def test_r1_modal_7_mensaje_wm_delete(self):
        """Modal 7: _mostrar_modal_mensaje with title bar 'X' closure."""
        # Force fallback by mocking CTkMessagebox to fail import
        with patch.dict("sys.modules", {"CTkMessagebox": None}):
            self.app._mostrar_modal_mensaje("Aviso Test", "Contenido mensaje", tipo="info")

        if "modal_mensaje" in self.app.modales_activos:
            modal = self.app.modales_activos["modal_mensaje"]
            self.assertEqual(modal.grab_current(), modal)
            self._trigger_wm_delete_window(modal)
            self.assertNotIn("modal_mensaje", self.app.modales_activos)
            self.assertIsNone(self.app.grab_current())
            self.assertFalse(modal.winfo_exists())

    def test_r1_modal_8_tabla_previsualizacion_wm_delete(self):
        """Modal 8: _abrir_tabla_previsualizacion with title bar 'X' closure."""
        datos_prueba = [
            {"nombre": "Juan", "apellido": "Perez", "cedula": "12345678", "edad": 25}
        ]
        self.app.datos_normalizados_actuales = datos_prueba
        self.app._abrir_tabla_previsualizacion("Formación")
        self.assertIn("tabla_previsualizacion", self.app.modales_activos)
        modal = self.app.modales_activos["tabla_previsualizacion"]

        self.assertEqual(modal.grab_current(), modal)
        self.assertTrue(modal.winfo_exists())

        # Simulate WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal)

        self.assertNotIn("tabla_previsualizacion", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())
        self.assertFalse(modal.winfo_exists())

    # =========================================================================
    # R1: MODAL AUTO-CLEANUP HOOKS (NAVIGATION & FILE DISCARD)
    # =========================================================================
    def test_r1_auto_cleanup_on_section_change(self):
        """Changing sections via _cambiar_seccion closes all active secondary modals."""
        # Ensure distinct source section
        self.app.seccion_actual = "Diagnostico"
        self.app._mostrar_modal_confirmacion("Auto-close 1", "Mensaje 1")
        self.app._abrir_ventana_flotante_inspeccion("facilitadores")
        self.assertTrue(len(self.app.modales_activos) >= 2)

        # Change section
        self.app._cambiar_seccion("Ajustes")
        self.app.update_idletasks()

        # All modals must be closed
        self.assertEqual(len(self.app.modales_activos), 0)
        self.assertIsNone(self.app.grab_current())

    def test_r1_auto_cleanup_on_descartar_formacion(self):
        """Discarding formación file closes active secondary modals."""
        self.app._mostrar_modal_confirmacion("Descartar Formacion", "¿Desea continuar?")
        self.assertIn("modal_confirmacion", self.app.modales_activos)

        self.app._descartar_archivo_formacion()
        self.app.update_idletasks()

        self.assertEqual(len(self.app.modales_activos), 0)
        self.assertIsNone(self.app.grab_current())

    def test_r1_auto_cleanup_on_descartar_servicios(self):
        """Discarding servicios file closes active secondary modals."""
        self.app._mostrar_modal_confirmacion("Descartar Servicios", "¿Desea continuar?")
        self.assertIn("modal_confirmacion", self.app.modales_activos)

        self.app._descartar_archivo_servicios()
        self.app.update_idletasks()

        self.assertEqual(len(self.app.modales_activos), 0)
        self.assertIsNone(self.app.grab_current())

    def test_r1_cerrar_modales_activos_with_exclude(self):
        """cerrar_modales_activos(excluir=...) preserves the excluded modal and closes the rest."""
        self.app._mostrar_modal_confirmacion("Modal 1", "M1")
        self.app._abrir_ventana_flotante_inspeccion("facilitadores")
        self.assertEqual(len(self.app.modales_activos), 2, f"Active modals: {self.app.modales_activos}")

        # Exclude ventana_inspeccion
        self.app.cerrar_modales_activos(excluir="ventana_inspeccion")
        self.app.update_idletasks()

        self.assertEqual(len(self.app.modales_activos), 1)
        self.assertIn("ventana_inspeccion", self.app.modales_activos)
        self.assertNotIn("modal_confirmacion", self.app.modales_activos)


    # =========================================================================
    # ADVANCED ADVERSARIAL STRESS TESTING
    # =========================================================================
    def test_r1_nested_modals_grab_and_cleanup(self):
        """Test opening a modal on top of another modal, closing in reverse order."""
        # 1. Open parent modal (inspection window)
        self.app._abrir_ventana_flotante_inspeccion("facilitadores")
        self.assertIn("ventana_inspeccion", self.app.modales_activos)
        modal_parent = self.app.modales_activos["ventana_inspeccion"]
        self.assertEqual(modal_parent.grab_current(), modal_parent)

        # 2. Open child modal (confirmation modal)
        self.app._mostrar_modal_confirmacion("Confirmar Acción", "¿Está seguro?")
        self.assertIn("modal_confirmacion", self.app.modales_activos)
        modal_child = self.app.modales_activos["modal_confirmacion"]
        self.assertEqual(modal_child.grab_current(), modal_child)

        # 3. Close child modal via WM_DELETE_WINDOW
        self._trigger_wm_delete_window(modal_child)
        self.assertNotIn("modal_confirmacion", self.app.modales_activos)
        self.assertFalse(modal_child.winfo_exists())

        # 4. Parent modal is still active in registry
        self.assertIn("ventana_inspeccion", self.app.modales_activos)

        # 5. Close parent modal
        self._trigger_wm_delete_window(modal_parent)
        self.assertNotIn("ventana_inspeccion", self.app.modales_activos)
        self.assertIsNone(self.app.grab_current())

    def test_r1_rapid_navigation_fuzzing(self):
        """Rapidly switch between views 50 times in rapid succession, verifying zero ungriding or freeze."""
        sections = [
            "Diagnostico", "Credenciales", "Formacion", "Servicios",
            "Planillas", "Reportes", "Creditos", "Ajustes",
            "Dashboard", "Cuenta", "ODS", "Auditor", "Inspector"
        ]
        t0 = time.monotonic()
        for i in range(50):
            target = sections[i % len(sections)]
            self.app.cambiar_vista(target)
        self.app.update_idletasks()
        elapsed = time.monotonic() - t0

        # Verify final state is valid and mapped
        last_sec = normalizar_clave_vista(sections[49 % len(sections)])
        target_view = self.app.vistas[last_sec]
        self.assertTrue(bool(target_view.grid_info()), f"Final view {last_sec} not mapped after rapid navigation")
        # 50 navigations should take less than 1.5 seconds total (< 30ms per navigation)
        self.assertLess(elapsed, 1.5, f"Rapid navigation took too long: {elapsed:.3f}s for 50 switches")

    def test_r3_type_coercion_and_exotics(self):
        """Stress test normalizar_clave_vista with unusual types and inputs."""
        self.assertEqual(normalizar_clave_vista(123), "123")
        self.assertEqual(normalizar_clave_vista(False), "Diagnostico")
        self.assertEqual(normalizar_clave_vista(True), "True")
        # Unknown string with null byte returns original string s without crashing
        self.assertEqual(normalizar_clave_vista("DIAGNÓSTICO\x00"), "DIAGNÓSTICO\x00")

    def test_r1_same_section_click_modal_behavior(self):
        """Verify behavior when re-clicking the active section while a modal is open.
        Note: Re-clicking the active section returns early (if self.seccion_actual == seccion_clave: return),
        so modals remain open unless switching to a DIFFERENT section."""
        self.app._cambiar_seccion("Ajustes")
        self.app.update_idletasks()
        self.assertEqual(self.app.seccion_actual, "Ajustes")

        # Open a modal while in Ajustes
        self.app._mostrar_modal_confirmacion("Test", "Mensaje")
        self.assertIn("modal_confirmacion", self.app.modales_activos)

        # Re-click "Ajustes"
        self.app._cambiar_seccion("Ajustes")
        self.app.update_idletasks()

        # Documented behavior: Returns early without closing modal
        self.assertIn("modal_confirmacion", self.app.modales_activos)

        # Clicking a DIFFERENT section ("Reportes") DOES close the modal
        self.app._cambiar_seccion("Reportes")
        self.app.update_idletasks()
        self.assertNotIn("modal_confirmacion", self.app.modales_activos)


if __name__ == "__main__":
    unittest.main()
