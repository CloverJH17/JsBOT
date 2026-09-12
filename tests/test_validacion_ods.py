#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST DE INTEGRIDAD Y REGLAS XML DE PLANILLAS ODS (test_validacion_ods.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — Suite Pre-v4.0
Objetivo  : Validar la generación oficial de planillas ODS inyectadas sobre la
            plantilla base oficial (config/plantilla_base.ods), analizando el
            árbol XML de content.xml con xml.etree.ElementTree.
            Verifica:
              - Ausencia total de caracteres de control inválidos (ASCII 0x00 a 0x1F)
              - Estructura exacta de 12 columnas visibles + celda de cierre repetida
              - Preservación intacta del pie de firmas (footer_rows)
              - Confirmación de exportación XML nativa sin caída en fallback plano
===============================================================================
"""

import os
import sys
import re
import zipfile
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.generador_planilla as gp
from modulos.generador_planilla import generar_planilla_oficial, TEMPLATE_PATH

NS = {
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
}


def _construir_lote_60_sinteticos() -> list:
    """
    Construye un lote heterogéneo de 60 participantes:
      - 20 con Cédula Normal (V-...)
      - 20 con Cédula Escolar calculada (CE...)
      - 20 Menores no escolarizados sin cédula (S/C con representante)
    Incluye caracteres sucios intencionales para certificar la sanitización XML.
    """
    participantes = []

    # Grupo 1: 20 Cédulas normales (incluyendo casos con acentos, comillas y caracteres de control)
    for i in range(1, 21):
        # Inyectar deliberadamente caracteres de control en algunos registros para auditar la sanitización
        control_chars = "\x00\x08\x0b\x1f" if i % 5 == 0 else ""
        participantes.append({
            "nombre": f"Participante{control_chars} Normal {i}",
            "apellido": f"Pérez & Co {i}",
            "cedula": f"{15000000 + i}",
            "cedulado": "si",
            "cedula_escolar": "",
            "cedula_padre": "",
            "nacimiento": f"199{i % 10}-0{1 + (i % 9)}-15 00:00:00",
            "edad": 25,
            "genero": "M" if i % 2 == 0 else "F",
            "telefono": f"0412-111{i:04d}",
            "correo": f"normal_{i}@correo.gob.ve",
            "direccion": f"Av. Caracas Calle {i}, San Felipe",
            "ocupacion": "Empleado Público",
            "nivel": "Educación Universitaria"
        })

    # Grupo 2: 20 Cédulas Escolares calculadas
    for i in range(1, 21):
        ce_calculada = f"115000000{i:02d}"
        participantes.append({
            "nombre": f"Estudiante Escolar {i}",
            "apellido": f"González {i}",
            "cedula": "",
            "cedulado": "escolar",
            "cedula_escolar": ce_calculada,
            "cedula_padre": f"{12000000 + i}",
            "nacimiento": f"2015-0{1 + (i % 9)}-10T12:30",
            "edad": 9,
            "genero": "F" if i % 2 == 0 else "M",
            "telefono": f"0414-222{i:04d}",
            "correo": "",
            "direccion": "Sector Higuerón, San Felipe",
            "ocupacion": "Estudiante",
            "nivel": "Educación Básica"
        })

    # Grupo 3: 20 Menores no escolarizados sin cédula
    for i in range(1, 21):
        ced_rep = f"{18000000 + i}"
        participantes.append({
            "nombre": f"Menor Sin Cedula {i}",
            "apellido": f"Reyes {i}",
            "cedula": "",
            "cedulado": "no",
            "cedula_escolar": "",
            "cedula_padre": ced_rep,
            "nacimiento": f"2021-0{1 + (i % 9)}-01",
            "edad": 3,
            "genero": "M" if i % 2 == 0 else "F",
            "telefono": f"0416-333{i:04d}",
            "correo": None,
            "direccion": "Albarico, San Felipe",
            "ocupacion": "",
            "nivel": ""
        })

    return participantes


@unittest.skipUnless(os.path.exists(TEMPLATE_PATH), f"No existe la plantilla base oficial: {TEMPLATE_PATH}")
class TestValidacionPlanillaOdsXml(unittest.TestCase):
    """
    Suite de validación profunda de reglas de formato y consistencia XML
    para las planillas oficiales OpenDocument Spreadsheet (.ods).
    """

    def setUp(self):
        """Genera una planilla oficial sintética con 60 participantes en un archivo temporal."""
        self.tmp_fd, self.ruta_ods = tempfile.mkstemp(prefix="jsbot_valida_ods_", suffix=".ods")
        os.close(self.tmp_fd)

        self.participantes = _construir_lote_60_sinteticos()
        self.id_actividad = "777888"
        self.url_actividad = (
            "https://infoapp2.infocentro.gob.ve/index.php?view=participants_list"
            "&id_activity=777888&activity=Alfabetizaci%C3%B3n+Digital+Comunitaria"
            "&estate=Yaracuy&code_info=YAR24&line_action=Apropiaci%C3%B3n+Social"
            "&date_activity=01-09-2026/10-09-2026"
        )

        # Mockear seleccionar_ubicacion_guardado para garantizar guardado automático en el archivo temporal
        with patch.object(gp, 'seleccionar_ubicacion_guardado', return_value=self.ruta_ods):
            generar_planilla_oficial(
                self.participantes,
                id_actividad=self.id_actividad,
                url_actividad=self.url_actividad
            )

        # Leer archivo ODS con zipfile y obtener content.xml
        self.assertTrue(os.path.exists(self.ruta_ods), "El archivo .ods generado debe existir en disco.")
        with zipfile.ZipFile(self.ruta_ods, 'r') as z:
            self.archivos_ods = z.namelist()
            self.content_xml_bytes = z.read('content.xml')

        self.content_xml_texto = self.content_xml_bytes.decode('utf-8')
        self.root = ET.fromstring(self.content_xml_bytes)

        # Localizar la tabla principal
        self.table = self.root.find('.//table:table', NS)
        self.assertIsNotNone(self.table, "No se encontró el elemento <table:table> en content.xml.")
        self.rows = list(self.table.findall(f"{{{NS['table']}}}table-row"))

    def tearDown(self):
        """Elimina el archivo temporal .ods."""
        if os.path.exists(self.ruta_ods):
            try:
                os.remove(self.ruta_ods)
            except Exception:
                pass

    def test_01_confirmar_ausencia_total_de_caracteres_de_control_invalidos(self):
        """
        REGLA XML 1:
        Confirma que en ningún nodo de content.xml existan caracteres de control
        inválidos para XML 1.0 (rango ASCII 0x00 a 0x1F, excluyendo tabulador 0x09
        y salto de línea 0x0A / retorno 0x0D).
        """
        # Expresión regular para caracteres de control prohibidos en XML
        regex_control = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')
        coincidencias = regex_control.findall(self.content_xml_texto)

        self.assertEqual(len(coincidencias), 0,
                         f"Se detectaron caracteres de control prohibidos en content.xml: {coincidencias}")

        # Comprobar específicamente que el byte nulo \x00 no exista
        self.assertNotIn("\x00", self.content_xml_texto, "El byte nulo \\x00 corrompe catastróficamente XML.")

    def test_02_estructura_filas_inyectadas_12_columnas_visibles_mas_cierre_repetido(self):
        """
        REGLA XML 2:
        Verifica que exactamente 60 filas hayan sido inyectadas y que cada una
        tenga la estructura geométrica estricta de la plantilla oficial:
          - 12 columnas visibles representadas en celdas XML:
            0: Correlativo N° (float, ce1)
            1: Nombre y Apellido (string, ce2, span 2 cols)
            2: covered-table-cell (ce8)
            3: Documento / Cédula / Escolar / S/C (string, ce1)
            4: Fecha de Nacimiento (string, ce11)
            5: Sexo (string, ce1)
            6: Dirección (string, ce1)
            7: Correo (string, ce1)
            8: Teléfono (string, ce1)
            9: Nivel (string, ce1)
            10: Ocupación (string, ce1)
            11: Firma (string, ce1)
          - Celdas de cierre repetidas:
            12: Celda ce14 con number-columns-repeated="2"
            13: Celda de cierre de tabla con number-columns-repeated="1010"
        """
        # Encabezados: 8 filas (0 a 7)
        # Inyectados: 60 filas (8 a 67)
        # Pie de firmas: 5 filas (68 a 72)
        total_esperado_filas = 8 + 60 + 5
        self.assertEqual(len(self.rows), total_esperado_filas,
                         f"El total de filas debe ser 73 (8 cabecera + 60 datos + 5 pie). Encontrado: {len(self.rows)}")

        filas_inyectadas = self.rows[8:68]
        self.assertEqual(len(filas_inyectadas), 60, "Deben existir exactamente 60 filas de datos inyectados.")

        table_ns = NS['table']
        office_ns = NS['office']
        text_ns = NS['text']

        for idx, row in enumerate(filas_inyectadas, 1):
            hijos = list(row)
            self.assertEqual(len(hijos), 14,
                             f"La fila inyectada {idx} debe contener exactamente 14 elementos XML.")

            # Celda 0: Correlativo
            c0 = hijos[0]
            self.assertEqual(c0.tag, f"{{{table_ns}}}table-cell")
            self.assertEqual(c0.attrib.get(f"{{{table_ns}}}style-name"), "ce1")
            self.assertEqual(c0.attrib.get(f"{{{office_ns}}}value-type"), "float")
            self.assertEqual(c0.attrib.get(f"{{{office_ns}}}value"), str(idx))
            self.assertEqual(c0.find(f"{{{text_ns}}}p").text, str(idx))

            # Celda 1: Nombre (spanned 2 columnas)
            c1 = hijos[1]
            self.assertEqual(c1.tag, f"{{{table_ns}}}table-cell")
            self.assertEqual(c1.attrib.get(f"{{{table_ns}}}style-name"), "ce2")
            self.assertEqual(c1.attrib.get(f"{{{table_ns}}}number-columns-spanned"), "2")
            self.assertEqual(c1.attrib.get(f"{{{table_ns}}}number-rows-spanned"), "1")
            self.assertTrue(bool(c1.find(f"{{{text_ns}}}p").text))

            # Celda 2: Celda cubierta por el span
            c2 = hijos[2]
            self.assertEqual(c2.tag, f"{{{table_ns}}}covered-table-cell")
            self.assertEqual(c2.attrib.get(f"{{{table_ns}}}style-name"), "ce8")

            # Celda 3: Documento de Identidad según modalidad
            c3 = hijos[3]
            self.assertEqual(c3.tag, f"{{{table_ns}}}table-cell")
            self.assertEqual(c3.attrib.get(f"{{{table_ns}}}style-name"), "ce1")
            doc_texto = c3.find(f"{{{text_ns}}}p").text or ""
            if idx <= 20:
                # Cédula normal
                self.assertRegex(doc_texto, r'^\d+$', f"Fila {idx} debe tener cédula normal.")
            elif idx <= 40:
                # Cédula escolar
                self.assertTrue(doc_texto.startswith("CE"), f"Fila {idx} debe iniciar con 'CE'.")
            else:
                # Menor no escolarizado
                self.assertTrue(doc_texto.startswith("S/C"), f"Fila {idx} debe ser 'S/C' o 'S/C (Rep: ...)'.")

            # Celda 4: Fecha de nacimiento YYYY-MM-DD
            c4 = hijos[4]
            self.assertEqual(c4.tag, f"{{{table_ns}}}table-cell")
            self.assertEqual(c4.attrib.get(f"{{{table_ns}}}style-name"), "ce11")
            f_texto = c4.find(f"{{{text_ns}}}p").text or ""
            self.assertRegex(f_texto, r'^\d{4}-\d{2}-\d{2}$',
                             f"Fila {idx}: La fecha '{f_texto}' debe tener formato ISO YYYY-MM-DD.")

            # Celda 5: Sexo
            c5 = hijos[5]
            self.assertIn(c5.find(f"{{{text_ns}}}p").text, ["M", "F"])

            # Celda 6: Dirección
            c6 = hijos[6]
            self.assertIn("San Felipe", c6.find(f"{{{text_ns}}}p").text)

            # Celda 7: Correo
            c7 = hijos[7]
            self.assertIsNotNone(c7.find(f"{{{text_ns}}}p"))

            # Celda 8: Teléfono
            c8 = hijos[8]
            self.assertRegex(c8.find(f"{{{text_ns}}}p").text, r'^\d{4}-\d{7}$')

            # Celda 9: Nivel
            c9 = hijos[9]
            self.assertIsNotNone(c9.find(f"{{{text_ns}}}p"))

            # Celda 10: Ocupación
            c10 = hijos[10]
            self.assertIsNotNone(c10.find(f"{{{text_ns}}}p"))

            # Celda 11: Firma (vacía para firmar manualmente)
            c11 = hijos[11]
            firma_p = c11.find(f"{{{text_ns}}}p")
            self.assertTrue(firma_p is None or firma_p.text is None or firma_p.text == "")

            # Celda 12: Celdas repetidas adyacentes ce14 (number-columns-repeated="2")
            c12 = hijos[12]
            self.assertEqual(c12.attrib.get(f"{{{table_ns}}}style-name"), "ce14")
            self.assertEqual(c12.attrib.get(f"{{{table_ns}}}number-columns-repeated"), "2")

            # Celda 13: Celda de cierre de fila ODS (number-columns-repeated="1010")
            c13 = hijos[13]
            self.assertEqual(c13.attrib.get(f"{{{table_ns}}}number-columns-repeated"), "1010")

    def test_03_preservacion_intacta_pie_de_pagina_y_firmas(self):
        """
        REGLA XML 3:
        Confirma que las filas del pie de página (footer_rows) conserven íntegramente
        los textos institucionales oficiales y las áreas destinadas a firmas:
          - 'Nota: Para ser llenado con letra Imprenta, sin enmiendas ni tachaduras'
          - 'Documento soporte que debe reposar en los archivos del Infocentro'
        """
        filas_pie = self.rows[68:]
        self.assertEqual(len(filas_pie), 5, "Deben preservarse exactamente 5 filas de pie de página.")

        texto_pie_completo = " ".join("".join(f.itertext()) for f in filas_pie)

        self.assertIn("Para ser llenado con letra Imprenta", texto_pie_completo,
                      "La nota oficial de llenado debe estar presente en el pie.")
        self.assertIn("sin enmiendas ni tachaduras", texto_pie_completo)
        self.assertIn("Documento soporte que debe reposar en los archivos del Infocentro", texto_pie_completo,
                      "La cláusula legal de custodia documental debe preservarse intacta.")

    def test_04_exportacion_nativa_xml_vs_no_caida_en_fallback_pandas(self):
        """
        REGLA XML 4:
        Confirma que la exportación haya sido 100% nativa XML y que NO haya
        recurrido al fallback plano de Pandas:
          - El contenedor ODS incluye 'styles.xml' y estilos de la plantilla base.
          - El XML contiene estilos nativos 'ro1', 'ce1', 'ce2', 'ce8', 'ce11'.
          - Si cayera en fallback Pandas, no existirían los 8 rows de encabezados
            oficiales ni los 5 de firmas ni los spans de columnas.
        """
        # 1. Comprobar que en el zip existen los artefactos de la plantilla oficial
        self.assertIn('styles.xml', self.archivos_ods, "styles.xml debe estar presente en el paquete ODS.")
        self.assertIn('META-INF/manifest.xml', self.archivos_ods)

        # 2. Comprobar que los atributos nativos de la plantilla oficial existen
        self.assertIn('table:style-name="ce1"', self.content_xml_texto)
        self.assertIn('table:style-name="ce2"', self.content_xml_texto)
        self.assertIn('table:style-name="ro1"', self.content_xml_texto)

        # 3. Comprobar que la cabecera oficial de 8 filas contiene los metadatos inyectados
        filas_cabecera = self.rows[:8]
        texto_cabecera = " ".join("".join(r.itertext()) for r in filas_cabecera)
        self.assertIn("Estado:", texto_cabecera)
        self.assertIn("Nombre del Infocentro:", texto_cabecera)
        self.assertIn("Nombres y apellidos del facilitador", texto_cabecera)
        self.assertIn("Modulo de formación:", texto_cabecera)

        # 4. Probar que si no hubiera plantilla (fallback), la estructura sería totalmente distinta
        # (Esto garantiza que el test detecta la diferencia entre exportación nativa y fallback)
        fd_fb, ruta_fb = tempfile.mkstemp(prefix="jsbot_fallback_", suffix=".ods")
        os.close(fd_fb)
        self.addCleanup(lambda: os.path.exists(ruta_fb) and os.remove(ruta_fb))

        with patch.object(gp, 'TEMPLATE_PATH', "no_existe_plantilla.ods"), \
             patch.object(gp, 'seleccionar_ubicacion_guardado', return_value=ruta_fb):
            generar_planilla_oficial(self.participantes[:5], id_actividad="1", url_actividad="")

        with zipfile.ZipFile(ruta_fb, 'r') as z_fb:
            xml_fb = z_fb.read('content.xml').decode('utf-8')

        # El fallback plano de pandas/odf NO tiene la cabecera de 8 filas ni ce14 ni 1010 columnas repetidas
        self.assertNotIn('number-columns-repeated="1010"', xml_fb,
                         "El fallback de Pandas no genera las celdas de cierre repetidas de la plantilla oficial.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
