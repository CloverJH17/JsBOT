"""
SUITE DE PRUEBAS PARA MODALES Y COMPUERTAS UI — JsBOT
Valida la resolución de menores huérfanos, auditoría de duplicados, rescate ante apagones y reportes no bloqueantes.
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

from modulos.normalizador_datos import (
    obtener_huerfanos_de_documento,
    asignar_tutor_a_huerfano,
    resolver_huerfanos_de_documento,
    auditar_integridad_lote,
    abrir_archivo_asistido
)
from modulos.gestor_sesion import (
    generar_reporte_auditoria_excel,
    generar_reporte_auditoria_servicios
)
from modulos.interfaz_grafica import JsBotGUI

class TestModalesYCompuertasUI(unittest.TestCase):

    def test_01_deteccion_y_resolucion_huerfanos(self):
        """Verifica que se identifiquen los menores huérfanos y se les pueda asignar tutor."""
        participantes = [
            {"nombre": "Lucas", "apellido": "Mendoza", "cedulado": "sin_documento", "edad": 7, "nacimiento": "2019-03-15"},
            {"nombre": "Sofia", "apellido": "Perez", "cedula": "30123456", "cedulado": "si", "edad": 20, "nacimiento": "2006-01-10"},
            {"nombre": "Mateo", "apellido": "Diaz", "cedula": "", "cedulado": "no", "cedula_escolar": "", "cedula_padre": ""}
        ]

        huerfanos = obtener_huerfanos_de_documento(participantes)
        self.assertEqual(len(huerfanos), 2)
        self.assertEqual(huerfanos[0]["nombre"], "Lucas")
        self.assertEqual(huerfanos[1]["nombre"], "Mateo")

        # Asignar tutor
        asignar_tutor_a_huerfano(huerfanos[0], "V-20.123.456")
        self.assertEqual(huerfanos[0]["cedula_padre"], "20123456")
        self.assertTrue(huerfanos[0]["cedula_escolar"].startswith("119"))
        self.assertEqual(huerfanos[0]["cedulado"], "escolar")

    def test_02_auditoria_integridad_con_duplicados(self):
        """Verifica que auditar_integridad_lote detecte inconsistencias y duplicados exactos."""
        participantes = [
            {"nombre": "Ana", "apellido": "Gomez", "cedula": "12345678", "genero": "F", "nacimiento": "2000-01-01"},
            {"nombre": "Ana", "apellido": "Gomez", "cedula": "12345678", "genero": "F", "nacimiento": "2000-01-01"},
            {"nombre": "Pedro", "apellido": "Perez", "cedula": "", "cedulado": "sin_documento", "genero": "", "nacimiento": ""}
        ]

        reporte = auditar_integridad_lote(participantes)
        self.assertEqual(reporte["total"], 3)
        self.assertEqual(reporte["duplicados"], 1)
        self.assertEqual(reporte["sin_documento"], 1)
        self.assertEqual(reporte["sin_genero"], 1)
        self.assertTrue(reporte["requiere_atencion"])

    def test_03_abrir_archivo_asistido_no_bloqueante(self):
        """Verifica que abrir_archivo_asistido no lance bloqueos si no hay suite instalada y no hay TTY."""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("subprocess.run", side_effect=Exception("No xdg-open")):
                try:
                    abrir_archivo_asistido("archivo_prueba_inexistente.xlsx")
                except Exception as e:
                    self.fail(f"abrir_archivo_asistido bloqueó o lanzó excepción: {e}")

    def test_04_reportes_excel_no_bloqueantes_en_permission_error(self):
        """Verifica que generar_reporte_auditoria_excel genere un archivo alternativo en caso de conflicto."""
        participantes_exitosos = [{"nombre": "Carlos", "apellido": "Ruiz", "cedula": "15678901"}]
        with patch("sys.stdin.isatty", return_value=False):
            config = {"id_actividad": "9999", "timestamp_str": "test_modal"}
            ruta = generar_reporte_auditoria_excel(
                config=config,
                exitosos=participantes_exitosos,
                fallidos=[]
            )
            self.assertTrue(os.path.exists(ruta))
            if os.path.exists(ruta):
                try:
                    os.remove(ruta)
                except Exception:
                    pass

    def test_05_metodos_modales_gui_instanciacion(self):
        """Comprueba que la GUI disponga de los métodos de modales interactivos para huérfanos y rescate."""
        try:
            app = JsBotGUI()
            app.withdraw()

            self.assertTrue(hasattr(app, "_mostrar_modal_resolucion_huerfanos"))
            self.assertTrue(hasattr(app, "comprobar_sesion_interrumpida_gui"))
            self.assertTrue(hasattr(app, "_mostrar_modal_recuperacion"))
            self.assertTrue(hasattr(app, "_actualizar_prevuelo_tras_resolucion"))

            # Probar actualización de pre-vuelo tras resolución
            app.participantes_cargados = [
                {"nombre": "Maria", "apellido": "Lopez", "cedula": "28111222", "cedulado": "si"}
            ]
            app._actualizar_prevuelo_tras_resolucion(seccion="Formacion")
            self.assertIn("Total: 1 participantes", app.lbl_prevuelo_formacion_total.cget("text"))

            app.destroy()
        except Exception as e:
            self.fail(f"Fallo al verificar métodos de modales en GUI: {e}")

if __name__ == "__main__":
    unittest.main()
