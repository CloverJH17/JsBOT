#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests del generador de planillas ODS (generador_planilla.py).

Incluye un test EXTREMO-A-EXTREMO que usa la plantilla real
config/plantilla_base.ods, inyecta participantes y relee el archivo
resultante para verificar que el XML quedó válido y con los datos.

Ejecutar desde la raíz del proyecto:
    py -m unittest discover -s tests -v
"""

import os
import sys
import io
import zipfile
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd
from unittest.mock import patch

import modulos.generador_planilla as gp
from modulos.generador_planilla import (
    limpiar_xml_texto,
    limpiar_fecha_ods,
    sanitizar_nombre_archivo,
    parsear_metadatos_url,
    generar_planilla_oficial,
)

TEMPLATE_REAL = os.path.join(BASE_DIR, "config", "plantilla_base.ods")
NS = {
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
}

def _participante(nombre="Ana", apellido="Pérez", cedula="12345678",
                  nacimiento="2010-05-10", genero="F", telefono="0412-1234567"):
    return {
        "nombre": nombre, "apellido": apellido, "cedula": cedula,
        "cedulado": "si" if cedula else "escolar", "cedula_escolar": "",
        "cedula_padre": "", "nacimiento": nacimiento, "edad": 16,
        "genero": genero, "telefono": telefono
    }


# =============================================================================
# FUNCIONES PURAS
# =============================================================================

class TestLimpiarXmlTexto(unittest.TestCase):
    def test_none_y_nan(self):
        self.assertEqual(limpiar_xml_texto(None), "")
        self.assertEqual(limpiar_xml_texto(float("nan")), "")

    def test_caracteres_de_control_eliminados(self):
        # Caracteres que rompen el parser XML si llegan de una celda sucia
        sucio = "Ana\x00\x08\x0bMaría\x1f"
        self.assertEqual(limpiar_xml_texto(sucio), "AnaMaría")

    def test_preserva_saltos_validos(self):
        self.assertIn("\n", limpiar_xml_texto("línea1\nlínea2"))
        self.assertIn("\t", limpiar_xml_texto("a\tb"))

    def test_caras_especiales_xml_se_conservan(self):
        # El escapado lo hace ET al serializar; aquí solo deben sobrevivir
        self.assertEqual(limpiar_xml_texto("Rojas & Pérez <S.A.>"), "Rojas & Pérez <S.A.>")


class TestLimpiarFechaOds(unittest.TestCase):
    def test_corta_timestamp(self):
        self.assertEqual(limpiar_fecha_ods("2014-03-15 14:30:00"), "2014-03-15")
        self.assertEqual(limpiar_fecha_ods("2014-03-15T14:30"), "2014-03-15")

    def test_vacios(self):
        self.assertEqual(limpiar_fecha_ods(""), "")
        self.assertEqual(limpiar_fecha_ods(None), "")


class TestSanitizarNombreArchivo(unittest.TestCase):
    def test_caracteres_prohibidos_windows(self):
        self.assertEqual(sanitizar_nombre_archivo('Actividad: "Formación"/1?'), "Actividad_Formación1")

    def test_largo_maximo(self):
        self.assertEqual(len(sanitizar_nombre_archivo("x" * 500)), 60)

    def test_vacio(self):
        self.assertEqual(sanitizar_nombre_archivo(""), "Actividad")


class TestParsearMetadatosUrl(unittest.TestCase):
    def test_defaults_sin_url(self):
        d = parsear_metadatos_url("")
        self.assertEqual(d['nombre_actividad'], 'Actividad Formativa')
        self.assertEqual(d['estado'], 'Yaracuy')

    def test_url_completa_real(self):
        params = {
            'id_activity': '523948',
            'activity': 'Formación en Robótica',
            'estate': 'Yaracuy',
            'code_info': 'NRYAR24',
            'line_action': 'Comunidades digitales',
            'date_activity': '2026-08-20/2026-08-25',
        }
        url = "https://infoapp2.infocentro.gob.ve/index.php?" + urllib.parse.urlencode(params)
        d = parsear_metadatos_url(url)
        self.assertEqual(d['id_actividad'], '523948')
        self.assertEqual(d['nombre_actividad'], 'Formación en Robótica')
        self.assertEqual(d['contenido'], 'Formación en Robótica')
        self.assertEqual(d['codigo_infocentro'], 'NRYAR24')
        self.assertEqual(d['fecha_desde'], '2026/08/20')
        self.assertEqual(d['fecha_hasta'], '2026/08/25')

    def test_url_malformada_no_explota(self):
        d = parsear_metadatos_url("http://%%%no-es-url&&&")
        self.assertIn('nombre_actividad', d)


# =============================================================================
# TEST EXTREMO-A-EXTREMO CON LA PLANTILLA REAL
# =============================================================================

@unittest.skipUnless(os.path.exists(TEMPLATE_REAL), "No existe config/plantilla_base.ods")
class TestGeneracionPlanillaReal(unittest.TestCase):

    def _generar(self, participantes):
        """Genera la planilla en un temporal sin diálogos tkinter."""
        fd, ruta = tempfile.mkstemp(suffix=".ods")
        os.close(fd)
        os.unlink(ruta)
        self.addCleanup(lambda: os.path.exists(ruta) and os.unlink(ruta))
        with patch.object(gp, 'seleccionar_ubicacion_guardado', return_value=ruta):
            generar_planilla_oficial(participantes, id_actividad="523948", url_actividad="")
        return ruta

    def _leer_filas(self, ruta):
        with zipfile.ZipFile(ruta) as z:
            root = ET.fromstring(z.read('content.xml'))
        tabla = root.find('.//table:table', NS)
        filas = tabla.findall(f"{{{NS['table']}}}table-row")
        textos = []
        for f in filas:
            celdas = []
            for c in f.iter(f"{{{NS['text']}}}p"):
                celdas.append(c.text or "")
            textos.append(" | ".join(celdas))
        return filas, textos

    def test_inyeccion_y_relectura_valida(self):
        partes = [
            _participante("Ana", "Pérez", "11111111"),
            _participante("Beto", "Rojas", "22222222"),
            _participante("Carla", "Díaz", "33333333"),
        ]
        ruta = self._generar(partes)
        self.assertTrue(os.path.exists(ruta))

        filas, textos = self._leer_filas(ruta)
        todo = "\n".join(textos)
        self.assertIn("Ana Pérez", todo)
        self.assertIn("Beto Rojas", todo)
        self.assertIn("Carla Díaz", todo)
        self.assertIn("11111111", todo)

    def test_pandas_puede_releer_el_ods(self):
        # Validación dura: si el XML quedó roto, read_excel lanza excepción
        ruta = self._generar([_participante(), _participante("Luis", "Márquez")])
        df = pd.read_excel(ruta, engine='odf', header=None)
        plano = df.astype(str).to_string()
        self.assertIn("Ana Pérez", plano)
        self.assertIn("Luis Márquez", plano)

    def test_cabecera_oficial_se_preserva(self):
        ruta = self._generar([_participante()])
        _, textos = self._leer_filas(ruta)
        todo = "\n".join(textos)
        self.assertIn("Estado:", todo)
        self.assertIn("facilitador", todo.lower())

    def test_caracteres_especiales_no_rompen_xml(self):
        # Nombre con &, < y comillas: el caso clásico que corrompe el ODS
        partes = [
            _participante("Ana<>&\"'", "O'Brien & Co"),
            _participante("Xavier", "100% Ñandú"),
        ]
        ruta = self._generar(partes)   # fallaría si el XML se corrompe
        df = pd.read_excel(ruta, engine='odf', header=None)
        self.assertGreaterEqual(len(df), 8)

    def test_caracteres_de_control_de_celda_sucia(self):
        p = _participante()
        p["nombre"] = "An\x00a\x1f"
        ruta = self._generar([p])
        df = pd.read_excel(ruta, engine='odf', header=None)
        plano = df.astype(str).to_string()
        self.assertNotIn("\x00", plano)

    def test_lista_grande_200_participantes(self):
        partes = [
            _participante(f"Persona{i:03d}", f"Apellido{i % 7}", str(10000000 + i))
            for i in range(200)
        ]
        ruta = self._generar(partes)
        filas, textos = self._leer_filas(ruta)
        todo = "\n".join(textos)
        self.assertIn("Persona000 Apellido0", todo)
        self.assertIn("Persona199 Apellido3", todo)  # 199 % 7 = 3

    def test_participante_campos_faltantes(self):
        # Registro mínimo: solo nombre (errores humanos en el ETL previo)
        minimo = {"nombre": "SinDatos", "apellido": "", "cedula": "",
                  "cedulado": "escolar", "cedula_escolar": "", "cedula_padre": "",
                  "nacimiento": "", "edad": None, "genero": "", "telefono": ""}
        ruta = self._generar([minimo])
        _, textos = self._leer_filas(ruta)
        todo = "\n".join(textos)
        self.assertIn("SinDatos", todo)
        # COMPORTAMIENTO DEL MÓDULO: escolar sin CE imprime 'CE' a secas
        # (candidato a mejora futura: 'S/C' o la CE calculada)
        self.assertIn(" | CE | ", todo)
        self.assertIn("---", todo)          # correo placeholder

    def test_sin_participantes_no_genera_nada(self):
        fd, ruta = tempfile.mkstemp(suffix=".ods")
        os.close(fd)
        os.unlink(ruta)
        self.addCleanup(lambda: os.path.exists(ruta) and os.unlink(ruta))
        with patch.object(gp, 'seleccionar_ubicacion_guardado', return_value=ruta):
            generar_planilla_oficial([], id_actividad="1", url_actividad="")
        self.assertFalse(os.path.exists(ruta))


@unittest.skipUnless(os.path.exists(TEMPLATE_REAL), "No existe config/plantilla_base.ods")
class TestFallbackSinPlantilla(unittest.TestCase):
    def test_fallback_pandas_cuando_no_hay_plantilla(self):
        fd, ruta = tempfile.mkstemp(suffix=".ods")
        os.close(fd)
        os.unlink(ruta)
        self.addCleanup(lambda: os.path.exists(ruta) and os.unlink(ruta))
        with patch.object(gp, 'TEMPLATE_PATH', "no_existe_plantilla.ods"), \
             patch.object(gp, 'seleccionar_ubicacion_guardado', return_value=ruta):
            generar_planilla_oficial([_participante()], id_actividad="1", url_actividad="")
        self.assertTrue(os.path.exists(ruta))
        df = pd.read_excel(ruta, engine='odf')
        self.assertIn("Nombres y Apellidos", df.columns)


if __name__ == "__main__":
    unittest.main(verbosity=2)
