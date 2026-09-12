#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de tests unitarios del ETL de JsBOT (normalizador_datos.py)
y del extractor de IDs (gestor_sesion.extraer_id_actividad).

Ejecutar desde la raíz del proyecto:
    py -m unittest discover -s tests -v
"""

import os
import sys
import unittest
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd

from modulos.normalizador_datos import (
    limpiar_texto,
    formatear_nombre_propio,
    es_nombre_valido,
    normalizar_col_nombre,
    limpiar_cedula,
    generar_cedula_escolar,
    limpiar_telefono,
    limpiar_genero,
    limpiar_fecha,
    deduplicar_participantes,
    detectar_cabeceras,
    procesar_archivo_participantes,
)
from modulos.gestor_sesion import extraer_id_actividad


class TestLimpiarTexto(unittest.TestCase):
    def test_none_y_nan(self):
        self.assertEqual(limpiar_texto(None), "")
        self.assertEqual(limpiar_texto(float("nan")), "")
        self.assertEqual(limpiar_texto(pd.NA), "")

    def test_strings_ruido(self):
        for ruido in ("nan", "NONE", "NaT", "null"):
            self.assertEqual(limpiar_texto(ruido), "")

    def test_float_entero(self):
        self.assertEqual(limpiar_texto(30348783.0), "30348783")

    def test_string_normal(self):
        self.assertEqual(limpiar_texto("  Hola  "), "Hola")


class TestFormatearNombrePropio(unittest.TestCase):
    def test_capitalize_basico(self):
        self.assertEqual(formatear_nombre_propio("jair alejandro"), "Jair Alejandro")

    def test_particulas_minusculas(self):
        self.assertEqual(
            formatear_nombre_propio("maria de los angeles"),
            "Maria de los Angeles"
        )
        self.assertEqual(
            formatear_nombre_propio("carlos del valle"),
            "Carlos del Valle"
        )

    def test_vacio(self):
        self.assertEqual(formatear_nombre_propio(""), "")
        self.assertEqual(formatear_nombre_propio(None), "")

    def test_primera_palabra_siempre_capitalizada(self):
        # 'de' al inicio NO debe quedar en minúscula
        self.assertEqual(formatear_nombre_propio("de la cruz"), "De la Cruz")


class TestEsNombreValido(unittest.TestCase):
    def test_nombres_validos(self):
        self.assertTrue(es_nombre_valido("jair hernandez"))
        self.assertTrue(es_nombre_valido("María Pérez"))

    def test_filas_basura(self):
        for basura in ("TOTAL", "masculino femenino", "rango de edad",
                       "estadistica", "firma", "12", "ab"):
            self.assertFalse(es_nombre_valido(basura), basura)

    def test_vacios(self):
        self.assertFalse(es_nombre_valido(""))
        self.assertFalse(es_nombre_valido(None))
        self.assertFalse(es_nombre_valido("12345"))


class TestNormalizarColNombre(unittest.TestCase):
    def test_tildes_y_signos(self):
        self.assertEqual(normalizar_col_nombre("Cédula:*"), "cedula")
        self.assertEqual(normalizar_col_nombre("Teléfono/Móvil"), "telefono movil")

    def test_no_string(self):
        self.assertEqual(normalizar_col_nombre(None), "")
        self.assertEqual(normalizar_col_nombre(123), "")


class TestLimpiarCedula(unittest.TestCase):
    def test_cedula_limpia(self):
        self.assertEqual(limpiar_cedula("30.348.783"), "30348783")
        self.assertEqual(limpiar_cedula(" V-12345678 "), "12345678")

    def test_extranjero(self):
        self.assertEqual(limpiar_cedula("E-84321000"), "E-84321000")
        self.assertEqual(limpiar_cedula("E84321000"), "E-84321000")

    def test_valores_invalidos(self):
        for invalido in ("", "0", "S/D", "NO APLICA", None, "abc"):
            self.assertEqual(limpiar_cedula(invalido), "", repr(invalido))

    def test_muy_corta(self):
        # menos de 5 dígitos se descarta
        self.assertEqual(limpiar_cedula("123"), "")


class TestGenerarCedulaEscolar(unittest.TestCase):
    def test_formula_oficial(self):
        # '1' + aa + CI a 8 dígitos
        self.assertEqual(generar_cedula_escolar("2016-05-10", "30348783"), "11630348783")

    def test_extranjero_zfill(self):
        self.assertEqual(generar_cedula_escolar("2016-05-10", "E-84321000"), "11684321000")

    def test_sin_padre(self):
        self.assertEqual(generar_cedula_escolar("2016-05-10", ""), "")
        self.assertEqual(generar_cedula_escolar("", "30348783"), "10030348783")


class TestLimpiarTelefono(unittest.TestCase):
    def test_formato_estandar(self):
        self.assertEqual(limpiar_telefono("0412-1234567"), "0412-1234567")
        self.assertEqual(limpiar_telefono("04121234567"), "0412-1234567")

    def test_internacional_58(self):
        self.assertEqual(limpiar_telefono("+584121234567"), "0412-1234567")
        self.assertEqual(limpiar_telefono("584141234567"), "0414-1234567")

    def test_diez_digitos_sin_cero(self):
        self.assertEqual(limpiar_telefono("4121234567"), "0412-1234567")
        self.assertEqual(limpiar_telefono("2541234567"), "0254-1234567")

    def test_default(self):
        self.assertEqual(limpiar_telefono(""), "0412-0000000")
        self.assertEqual(limpiar_telefono("abc"), "0412-0000000")


class TestLimpiarGenero(unittest.TestCase):
    def test_femenino_prioritario(self):
        # 'M' inicial no debe capturar antes que fragmentos femeninos
        self.assertEqual(limpiar_genero("F"), "F")
        self.assertEqual(limpiar_genero("MUJER"), "F")
        self.assertEqual(limpiar_genero("Femenino"), "F")

    def test_masculino_typos(self):
        self.assertEqual(limpiar_genero("MARCULINO"), "M")
        self.assertEqual(limpiar_genero("Varón"), "M")
        self.assertEqual(limpiar_genero("HOMBRE"), "M")
        self.assertEqual(limpiar_genero("Masculino"), "M")

    def test_vacio(self):
        self.assertEqual(limpiar_genero(""), "")
        self.assertEqual(limpiar_genero(None), "")


class TestLimpiarFecha(unittest.TestCase):
    def test_serial_excel(self):
        self.assertEqual(limpiar_fecha(41713), "2014-03-15")

    def test_datetime_y_timestamp(self):
        self.assertEqual(limpiar_fecha(pd.Timestamp("2014-03-15")), "2014-03-15")
        self.assertEqual(limpiar_fecha("2014-03-15 14:30:00"), "2014-03-15")
        self.assertEqual(limpiar_fecha("2014-03-15T14:30:00"), "2014-03-15")

    def test_texto_espanol(self):
        self.assertEqual(limpiar_fecha("15 de marzo de 2014"), "2014-03-15")
        self.assertEqual(limpiar_fecha("15-mar-2014"), "2014-03-15")

    def test_formatos_numericos(self):
        self.assertEqual(limpiar_fecha("15/03/2014"), "2014-03-15")
        self.assertEqual(limpiar_fecha("15-03-2014"), "2014-03-15")

    def test_dos_digitos_anio(self):
        self.assertEqual(limpiar_fecha("15/03/14"), "2014-03-15")

    def test_invalida(self):
        self.assertEqual(limpiar_fecha(""), "")
        self.assertEqual(limpiar_fecha("no es fecha"), "")
        self.assertEqual(limpiar_fecha(None), "")


class TestDeduplicarParticipantes(unittest.TestCase):
    def _p(self, nombre, cedula="", escolar="", padre=""):
        return {
            "nombre": nombre, "apellido": "Pérez", "cedula": cedula,
            "cedulado": "si" if cedula else ("escolar" if escolar else "no"),
            "cedula_escolar": escolar, "cedula_padre": padre,
            "nacimiento": "2010-01-01", "edad": 16, "genero": "M",
            "telefono": "0412-0000000"
        }

    def test_sin_duplicados_devuelve_todo(self):
        lista = [self._p("Ana", cedula="111"), self._p("Beto", cedula="222")]
        res = deduplicar_participantes(lista)
        self.assertEqual(len(res), 2)

    def test_duplicado_por_ci_se_elimina(self):
        # En modo no interactivo (stdin no tty) el fallback input() no aplica;
        # InquirerPy está instalado pero stdin no es TTY en tests -> usamos monkeypatch de input.
        lista = [self._p("Ana", cedula="111"), self._p("Ana", cedula="111")]
        import builtins
        original_input = builtins.input
        builtins.input = lambda *a, **k: ""
        try:
            res = deduplicar_participantes(lista)
        finally:
            builtins.input = original_input
        # Enter = Sí (DEDUP) según el fallback
        self.assertEqual(len(res), 1)

    def test_gemelos_no_se_deducen(self):
        # Misma CE y representante pero distinto nombre -> claves distintas
        a = self._p("Jose", escolar="11630348783", padre="30348783")
        b = self._p("Juan", escolar="11630348783", padre="30348783")
        import builtins
        original_input = builtins.input
        builtins.input = lambda *a, **k: ""
        try:
            res = deduplicar_participantes([a, b])
        finally:
            builtins.input = original_input
        self.assertEqual(len(res), 2)


class TestDetectarCabeceras(unittest.TestCase):
    def _df(self, filas):
        return pd.DataFrame(filas)

    def test_cabecera_simple(self):
        df = self._df([
            ["Nombres", "Apellidos", "Cédula", "Fecha Nac."],
            ["Ana", "Pérez", "12345678", "2000-05-10"],
        ])
        fila, mapa = detectar_cabeceras(df)
        self.assertEqual(fila, 0)
        self.assertIn("nombre", mapa)
        self.assertIn("apellido", mapa)
        self.assertIn("cedula_alumno", mapa)

    def test_membrete_institucional(self):
        df = self._df([
            ["REPÚBLICA BOLIVARIANA DE VENEZUELA"],
            ["Infocentro Felix Pifano"],
            [],
            ["Nombres", "Apellidos", "C.I."],
            ["Ana", "Pérez", "12345678"],
        ])
        fila, mapa = detectar_cabeceras(df)
        self.assertEqual(fila, 3)
        self.assertIn("nombre", mapa)

    def test_columna_representante_detectada(self):
        df = self._df([
            ["Nombre", "Apellido", "CI Representante"],
            ["Ana", "Pérez", "30348783"],
        ])
        _, mapa = detectar_cabeceras(df)
        self.assertIn("cedula_padre", mapa)

    def test_ci_con_puntos_representante(self):
        df = self._df([
            ["Nombre", "Apellido", "C.I. Representante"],
            ["Pedro", "Rojas", "30348783"],
        ])
        _, mapa = detectar_cabeceras(df)
        self.assertIn("cedula_padre", mapa)


class TestProcesarArchivoParticipantes(unittest.TestCase):
    def test_csv_basico(self):
        contenido = (
            "Nombres,Apellidos,Cédula,Fecha de Nacimiento,Teléfono,Género\n"
            "ana maria,perez gomez,12345678,15/03/2014,04121234567,F\n"
            "juan carlos,diaz rojas,E-84321000,2010-08-20,04161234567,M\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(contenido)
            ruta = f.name
        try:
            partes = procesar_archivo_participantes(ruta)
            self.assertEqual(len(partes), 2)

            p1 = partes[0]
            self.assertEqual(p1["nombre"], "Ana Maria")
            self.assertEqual(p1["apellido"], "Perez Gomez")
            self.assertEqual(p1["cedula"], "12345678")
            self.assertEqual(p1["cedulado"], "si")
            self.assertEqual(p1["nacimiento"], "2014-03-15")
            self.assertEqual(p1["genero"], "F")
            self.assertEqual(p1["telefono"], "0412-1234567")

            p2 = partes[1]
            self.assertEqual(p2["cedula"], "E-84321000")
            self.assertEqual(p2["genero"], "M")
        finally:
            os.unlink(ruta)

    def test_fila_total_descartada(self):
        contenido = (
            "Nombres,Apellidos,Cédula\n"
            "Ana,Pérez,12345678\n"
            "TOTALES,,\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(contenido)
            ruta = f.name
        try:
            partes = procesar_archivo_participantes(ruta)
            self.assertEqual(len(partes), 1)
            self.assertEqual(partes[0]["nombre"], "Ana")
        finally:
            os.unlink(ruta)

    def test_telefono_en_campo_cedula(self):
        contenido = (
            "Nombres,Apellidos,Cédula\n"
            "Luis,Díaz,04121234567\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(contenido)
            ruta = f.name
        try:
            partes = procesar_archivo_participantes(ruta)
            self.assertEqual(len(partes), 1)
            p = partes[0]
            self.assertEqual(p["cedula"], "")          # cédula descartada
            self.assertNotEqual(p["telefono"], "0412-0000000")  # rescatada como teléfono
        finally:
            os.unlink(ruta)

    def test_menor_sin_ci_genera_cedula_escolar(self):
        contenido = (
            "Nombres,Apellidos,CI Representante,Fecha de Nacimiento\n"
            "Pedro,Rojas,30348783,2016-05-10\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(contenido)
            ruta = f.name
        try:
            partes = procesar_archivo_participantes(ruta)
            self.assertEqual(len(partes), 1)
            p = partes[0]
            self.assertEqual(p["cedulado"], "escolar")
            self.assertEqual(p["cedula_escolar"], "11630348783")
            self.assertEqual(p["cedula_padre"], "30348783")
        finally:
            os.unlink(ruta)

    def test_archivo_inexistente(self):
        self.assertEqual(procesar_archivo_participantes("no_existe.csv"), [])


class TestExtraerIdActividad(unittest.TestCase):
    def test_parametro_estandar(self):
        url = "https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=523948"
        self.assertEqual(extraer_id_actividad(url), "523948")

    def test_sin_id(self):
        self.assertEqual(extraer_id_actividad("https://infoapp2.infocentro.gob.ve/admin/"), "general")
        self.assertEqual(extraer_id_actividad(""), "general")


if __name__ == "__main__":
    unittest.main(verbosity=2)
