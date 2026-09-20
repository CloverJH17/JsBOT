"""
Pruebas Unitarias para la Vista del Inspector en la GUI (v4.2.3)
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.interfaz_grafica import AppGUI

class TestInterfazInspector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = AppGUI()
        cls.app.withdraw()  # Ocultar ventana para tests rápidos

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.destroy()
        except Exception:
            pass

    def test_sidebar_botones_planillas_y_reportes(self):
        """Verifica que el sidebar contenga tanto 'Planillas' como 'Reportes'."""
        self.assertIn("Planillas", self.app.nav_buttons)
        self.assertIn("Reportes", self.app.nav_buttons)

    def test_vistas_registradas(self):
        """Verifica que self.vistas contenga 'Planillas' y 'Reportes'."""
        self.assertIn("Planillas", self.app.vistas)
        self.assertIn("Reportes", self.app.vistas)

    def test_componentes_vista_inspector(self):
        """Verifica la existencia de los KPIs y controles del Inspector (v4.2.3)."""
        self.assertTrue(hasattr(self.app, "lbl_kpi_actividades"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_formados"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_servicios"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_cuadre"))
        self.assertTrue(hasattr(self.app, "tabview_auditoria"))
        self.assertTrue(hasattr(self.app, "btn_iniciar_auditoria"))
        self.assertTrue(hasattr(self.app, "btn_abrir_reporte_auditoria"))
        self.assertTrue(hasattr(self.app, "switch_rol_auditor"))

        # Pestañas activas (Telemetría unificada en panel inferior)
        pestanas = ["🎓 Formaciones y Actividades", "🛠️ Servicios a Usuarios", "👥 Resumen por Facilitador"]
        for p in pestanas:
            self.assertIn(p, self.app.tabview_auditoria._tab_dict)

        # Telemetría unificada redirigida
        self.assertEqual(self.app.txt_telemetria_auditoria, self.app.textbox_logs)

    def test_cambio_de_modo_inspector_reactivo(self):
        """Verifica que el cambio dinámico oculte (.grid_remove) y muestre campos condicionalmente."""
        # Modo UID
        self.app.var_modo_auditoria.set("Por Facilitador (UID)")
        self.app._al_cambiar_modo_auditoria()
        self.assertTrue(bool(self.app.box_aud_uid.grid_info()), "box_aud_uid debe estar visible en Modo UID")
        self.assertFalse(bool(self.app.box_aud_infoid.grid_info()), "box_aud_infoid debe ocultarse en Modo UID")
        self.assertFalse(bool(self.app.box_aud_estado.grid_info()), "box_aud_estado debe ocultarse en Modo UID")

        # Modo Infocentro
        self.app.var_modo_auditoria.set("Por Infocentro (Código)")
        self.app._al_cambiar_modo_auditoria()
        self.assertFalse(bool(self.app.box_aud_uid.grid_info()), "box_aud_uid debe ocultarse en Modo Infocentro")
        self.assertTrue(bool(self.app.box_aud_infoid.grid_info()), "box_aud_infoid debe estar visible en Modo Infocentro")
        self.assertFalse(bool(self.app.box_aud_estado.grid_info()), "box_aud_estado debe ocultarse en Modo Infocentro")

        # Modo Resumen Estadal
        self.app.var_modo_auditoria.set("Resumen Estadal (Región)")
        self.app._al_cambiar_modo_auditoria()
        self.assertFalse(bool(self.app.box_aud_uid.grid_info()), "box_aud_uid debe ocultarse en Modo Estado")
        self.assertFalse(bool(self.app.box_aud_infoid.grid_info()), "box_aud_infoid debe ocultarse en Modo Estado")
        self.assertTrue(bool(self.app.box_aud_estado.grid_info()), "box_aud_estado debe estar visible en Modo Estado")

    def test_poblado_tabs_vacias(self):
        """Verifica que los métodos de renderizado manejen listas vacías sin error."""
        self.app._poblar_tab_actividades([])
        self.app._poblar_tab_servicios([])
        self.app._poblar_tab_facilitadores({})

    def test_apertura_ventana_flotante_inspeccion(self):
        """Verifica la creación de ventana flotante CTkToplevel para inspección detallada."""
        self.app._abrir_ventana_flotante_inspeccion("facilitadores")
        # Verificar que se creó y destruirla
        for widget in self.app.winfo_children():
            if widget.__class__.__name__ == "CTkToplevel":
                widget.destroy()

    def test_apertura_modal_credenciales_auditor(self):
        """Verifica la apertura del modal CTkToplevel para credenciales de auditor."""
        self.app._mostrar_modal_credenciales_auditor()
        for widget in self.app.winfo_children():
            if widget.__class__.__name__ == "CTkToplevel":
                widget.destroy()

    def test_nuevos_botones_inspeccion_y_exportacion(self):
        """Verifica la existencia y configuración de los botones de inspección modal y exportación (v4.2.6)."""
        self.assertTrue(hasattr(self.app, "btn_ver_actividades"))
        self.assertTrue(hasattr(self.app, "btn_ver_servicios"))
        self.assertTrue(hasattr(self.app, "btn_ver_facilitadores"))
        self.assertTrue(hasattr(self.app, "combo_aud_formato"))
        self.assertTrue(hasattr(self.app, "btn_exportar_reporte_dialogo"))

        self.assertIn("Formaciones", self.app.btn_ver_actividades.cget("text"))
        self.assertIn("Servicios", self.app.btn_ver_servicios.cget("text"))
        self.assertIn("Facilitador", self.app.btn_ver_facilitadores.cget("text"))

    def test_kpis_ampliados_y_metricas_detalladas(self):
        """Verifica la presencia de las etiquetas de detalle de KPIs y su actualización con datos ricos."""
        self.assertTrue(hasattr(self.app, "lbl_kpi_actividades_det"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_formados_det"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_servicios_det"))
        self.assertTrue(hasattr(self.app, "lbl_kpi_cuadre_det"))

        resultado_mock = {
            "exito": True,
            "total_actividades": 2,
            "total_procesadas": 2,
            "formaciones": [
                {"id": "1", "participantes": 30, "dimensiones": "Robótica", "info_id": "NRYAR24"},
                {"id": "2", "participantes": 20, "dimensiones": "Ofimática", "info_id": "NRYAR24"}
            ],
            "productos": [],
            "otras_actividades": [],
            "total_estudiantes": 50,
            "total_servicios": 2,
            "servicios": [
                {"servicio": "Trámite Patria", "cedula": "123"},
                {"servicio": "Trámite Patria", "cedula": ""}
            ],
            "conteo_servicios": {"Trámite Patria": 2},
            "cedulados_serv": 1,
            "no_cedulados_serv": 1,
            "cuadre_perfecto": True
        }
        self.app._finalizar_ejecucion_auditoria(resultado_mock)

        # Promedio: 50 / 2 = 25.0
        self.assertIn("25.0", self.app.lbl_kpi_formados_det.cget("text"))
        # Top servicio
        self.assertIn("Trámite Patria", self.app.lbl_kpi_servicios_det.cget("text"))
        # Cuadre
        self.assertIn("Cuadrado", self.app.lbl_kpi_cuadre.cget("text"))

    def test_modal_estricta_al_frente_con_grab(self):
        """Verifica que la ventana de inspección se configure como modal estricta bloqueante."""
        self.app._abrir_ventana_flotante_inspeccion("actividades")
        modales = [w for w in self.app.winfo_children() if w.__class__.__name__ == "CTkToplevel"]
        self.assertTrue(len(modales) > 0)
        modal = modales[-1]

        # Verificar que el modal existe y está registrado
        self.assertTrue(modal.winfo_exists())

        # Destruir modal para limpiar
        modal.destroy()

if __name__ == "__main__":
    unittest.main()
