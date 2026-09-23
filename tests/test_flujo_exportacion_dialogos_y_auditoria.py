#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST DE FLUJO DE EXPORTACIÓN: DIÁLOGOS EN PLANILLAS Y AUDITORÍA A DEMANDA
(test_flujo_exportacion_dialogos_y_auditoria.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation)
Objetivo  : Validar que:
            1. seleccionar_ubicacion_guardado configure extensiones y filtros
               consistentes para ODS, XLSX y PDF.
            2. La cancelación del diálogo retorne cadena vacía sin generar archivos.
            3. generar_planilla_xlsx y generar_planilla_pdf invoquen el diálogo
               cuando no se suministre ruta de salida.
            4. ejecutar_auditoria con exportar_formato="ninguno" no genere
               archivos físicos en Reportes_Auditoria/.
            5. El formato predeterminado de auditoría sea LibreOffice (.odt).
===============================================================================
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.generador_planilla as gp
import modulos.auditor_reportes as ar


class TestFlujoExportacionDialogosYAuditoria(unittest.TestCase):

    def test_seleccionar_ubicacion_guardado_filtros_multiformato(self):
        """Verifica que seleccionar_ubicacion_guardado adapte extensiones y filtros para ods, xlsx y pdf."""
        formatos_esperados = {
            "ods": (".ods", "*.ods"),
            "xlsx": (".xlsx", "*.xlsx"),
            "pdf": (".pdf", "*.pdf")
        }

        for fmt, (ext_esperada, filtro_esperado) in formatos_esperados.items():
            with patch("tkinter.filedialog.asksaveasfilename", return_value=f"C:/test/salida{ext_esperada}") as mock_dialog:
                ruta = gp.seleccionar_ubicacion_guardado(id_actividad="123", formato=fmt)
                self.assertEqual(ruta, f"C:/test/salida{ext_esperada}")
                mock_dialog.assert_called_once()
                kwargs = mock_dialog.call_args[1]
                self.assertEqual(kwargs.get("defaultextension"), ext_esperada)
                self.assertIn(ext_esperada, kwargs.get("initialfile"))
                # Comprobar que en los filetypes figure el filtro
                tipos = [ft[1] for ft in kwargs.get("filetypes", [])]
                self.assertIn(filtro_esperado, tipos)

    def test_seleccionar_ubicacion_guardado_cancelacion_retorna_vacio(self):
        """Verifica que si el usuario presiona Cancelar en el diálogo, se retorne cadena vacía."""
        with patch("tkinter.filedialog.asksaveasfilename", return_value=""):
            ruta = gp.seleccionar_ubicacion_guardado(id_actividad="123", formato="xlsx")
            self.assertEqual(ruta, "")

    def test_generador_xlsx_cancela_limpiamente_si_dialogo_se_cancela(self):
        """Verifica que generar_planilla_xlsx aborte sin crear archivo si el diálogo retorna vacío."""
        with patch.object(gp, "seleccionar_ubicacion_guardado", return_value=""):
            participantes = [{"nombre": "Juan", "apellido": "Pérez", "cedula": "12345"}]
            resultado = gp.generar_planilla_xlsx(participantes, id_actividad="123", ruta_salida="")
            self.assertEqual(resultado, "")

    def test_generador_pdf_cancela_limpiamente_si_dialogo_se_cancela(self):
        """Verifica que generar_planilla_pdf aborte sin crear archivo si el diálogo retorna vacío."""
        with patch.object(gp, "seleccionar_ubicacion_guardado", return_value=""):
            participantes = [{"nombre": "Juan", "apellido": "Pérez", "cedula": "12345"}]
            resultado = gp.generar_planilla_pdf(participantes, id_actividad="123", ruta_salida="")
            self.assertEqual(resultado, "")

    def test_generador_ods_cancela_limpiamente_si_dialogo_se_cancela(self):
        """Verifica que generar_planilla_ods_odfdo aborte sin crear archivo si el diálogo retorna vacío."""
        with patch.object(gp, "seleccionar_ubicacion_guardado", return_value=""):
            participantes = [{"nombre": "Juan", "apellido": "Pérez", "cedula": "12345"}]
            resultado = gp.generar_planilla_ods_odfdo(participantes, id_actividad="123", ruta_salida="")
            self.assertEqual(resultado, "")

    def test_auditoria_exportar_formato_ninguno_no_genera_archivos(self):
        """Verifica que al ejecutar auditoría con exportar_formato='ninguno' no se genere archivo en disco."""
        with patch("modulos.auditor_reportes.cargar_credenciales_auditoria", return_value=("usr", "pwd")), \
             patch("modulos.auditor_reportes.iniciar_driver_auditoria") as mock_driver, \
             patch("modulos.auditor_reportes.autenticar_infoapp", return_value=True), \
             patch("modulos.auditor_reportes.consultar_actividades_infoapp", return_value=(0, [])), \
             patch("modulos.auditor_reportes.consultar_servicios_infoapp", return_value=(0, [])), \
             patch("modulos.auditor_reportes.guardar_cache_inspector"):

            mock_driver_instance = MagicMock()
            mock_driver_instance.get_cookies.return_value = []
            mock_driver.return_value = mock_driver_instance

            res = ar.ejecutar_auditoria(
                uid="1325",
                exportar_formato="ninguno",
                modo_turbo=True
            )

            self.assertTrue(res.get("exito"))
            self.assertEqual(res.get("archivo_exportado"), "")

    def test_auditoria_formato_predeterminado_es_odt(self):
        """Verifica que el formato por defecto en auditor_reportes sea 'odt'."""
        with patch("modulos.auditor_reportes.exportar_reporte_odt", return_value="C:/Reportes_Auditoria/reporte.odt") as mock_odt:
            resultado_simulado = {
                "exito": True,
                "criterio_tipo": "uid",
                "criterio_valor": "1325",
                "total_actividades": 0,
                "total_servicios": 0
            }
            # Al no especificar formato, debe delegar en exportar_reporte_odt
            ruta = ar.exportar_reporte_auditoria(resultado_simulado)
            self.assertEqual(ruta, "C:/Reportes_Auditoria/reporte.odt")
            mock_odt.assert_called_once()


if __name__ == '__main__':
    unittest.main()
