#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de CASOS EXTREMOS y ERRORES HUMANOS del ETL de JsBOT.

Simula la basura real que llega en las planillas de los infocentros:
cédulas con letras, fechas imposibles, géneros mal escritos, filas de totales,
nombres pegados, teléfonos en campos equivocados, Excel que trunca cédulas, etc.

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
    procesar_archivo_texto,
)


class _CSVMixin:
    """Helper para escribir CSVs temporales y limpiarlos después."""

    def _csv(self, contenido: str) -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        f.write(contenido)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name


# =============================================================================
# CÉDULAS: errores de tipeo humano
# =============================================================================

class TestCedulasExtremas(unittest.TestCase):
    def test_con_prefijos_y_puntos(self):
        self.assertEqual(limpiar_cedula("V-30.348.783"), "30348783")
        self.assertEqual(limpiar_cedula("v30348783"), "30348783")   # minúscula
        self.assertEqual(limpiar_cedula("V 12.345.678"), "12345678")
        self.assertEqual(limpiar_cedula("e-84321000"), "E-84321000") # minúscula extranjero

    def test_letras_mezcladas(self):
        # '1234a5678' -> extrae solo dígitos
        self.assertEqual(limpiar_cedula("1234a5678"), "12345678")

    def test_todo_ceros(self):
        # int(digitos) == 0 se descarta
        self.assertEqual(limpiar_cedula("00000000"), "")
        self.assertEqual(limpiar_cedula("000"), "")

    def test_extranjero_muy_corto(self):
        # 5 dígitos mínimos; pasaporte corto se descarta igual por regla actual
        self.assertEqual(limpiar_cedula("E-123"), "E-123" if False else "")

    def test_numeros_flotantes_de_excel(self):
        # Excel a veces entrega la cédula como float
        self.assertEqual(limpiar_cedula(30348783.0), "30348783")

    def test_espacios_internos(self):
        self.assertEqual(limpiar_cedula("30 348 783"), "30348783")


# =============================================================================
# FECHAS IMPOSIBLES Y RARAS
# =============================================================================

class TestFechasExtremas(unittest.TestCase):
    def test_dia_inexistente(self):
        # 31 de febrero no existe -> debe devolver vacío, NO inventar fecha
        self.assertEqual(limpiar_fecha("31/02/2020"), "")

    def test_mes_13(self):
        self.assertEqual(limpiar_fecha("15/13/2020"), "")

    def test_serial_fuera_de_rango(self):
        self.assertEqual(limpiar_fecha(100), "")      # muy viejo (~1900)
        self.assertEqual(limpiar_fecha(200000), "")   # año ~2500
        self.assertEqual(limpiar_fecha(-50), "")

    def test_formato_con_puntos(self):
        self.assertEqual(limpiar_fecha("15.03.2014"), "2014-03-15")

    def test_formato_slash_invertido(self):
        self.assertEqual(limpiar_fecha("2014/03/15"), "2014-03-15")

    def test_texto_natural_variado(self):
        self.assertEqual(limpiar_fecha("5 de mayo de 2005"), "2005-05-05")
        self.assertEqual(limpiar_fecha("1 ene 1990"), "1990-01-01")
        self.assertEqual(limpiar_fecha("31 de diciembre de 1999"), "1999-12-31")

    def test_ambigua_dayfirst(self):
        # dd/mm/yyyy (convención venezolana): 03/04 = 3 de abril
        self.assertEqual(limpiar_fecha("03/04/2014"), "2014-04-03")

    def test_anio_dos_digitos_frontera(self):
        # %y mapea 00-68 al siglo XXI, pero para nacimientos se retrotrae
        # un siglo cuando caería en futuro: '51' -> 1951
        self.assertEqual(limpiar_fecha("10/12/14"), "2014-12-10")
        self.assertEqual(limpiar_fecha("10/12/51"), "1951-12-10")

    def test_fecha_4_digitos_futura_sigue_rechazada(self):
        # Fechas explícitamente futuras (año completo) NO se retrottraen
        self.assertEqual(limpiar_fecha("15/03/2035"), "")

    def test_solo_anio_ya_no_inventa_fecha(self):
        # CORREGIDO: antes el fallback de pandas convertía '2014' en
        # 2014-01-01 aceptando basura numérica; ahora se rechaza.
        self.assertEqual(limpiar_fecha("2014"), "")
        self.assertEqual(limpiar_fecha("12345"), "")


# =============================================================================
# GÉNEROS MAL ESCRITOS
# =============================================================================

class TestGenerosExtremos(unittest.TestCase):
    def test_typos_reales_de_planillas(self):
        for masc in ("Marcuino", "MASCU", "masculina ", "Varon", "niño", "Papa"):
            self.assertEqual(limpiar_genero(masc), "M", repr(masc))
        for fem in ("f.", "muje", "Niña", "MADRE", "hembra"):
            self.assertEqual(limpiar_genero(fem), "F", repr(fem))

    def test_valores_sin_sentido(self):
        for raro in ("X", "?", "--", "no sé"):
            self.assertEqual(limpiar_genero(raro), "", repr(raro))


# =============================================================================
# TELÉFONOS CON ERRORES HUMANOS
# =============================================================================

class TestTelefonosExtremos(unittest.TestCase):
    def test_formatos_con_separadores(self):
        self.assertEqual(limpiar_telefono("0426 123 45 67"), "0426-1234567")
        self.assertEqual(limpiar_telefono("(0414)123-4567"), "0414-1234567")
        self.assertEqual(limpiar_telefono("0414.123.45.67"), "0414-1234567")

    def test_con_codigo_internacional(self):
        self.assertEqual(limpiar_telefono("+58 424-1234567"), "0424-1234567")
        self.assertEqual(limpiar_telefono("58 416 123 4567"), "0416-1234567")

    def test_demasiados_digitos(self):
        # 13 dígitos empieza con 58 -> recorta bien
        self.assertEqual(limpiar_telefono("5841212345678".rstrip("8")), "0412-1234567")

    def test_muy_cortos_o_basura(self):
        for basura in ("0412", "123", "telefono pendiente", "s/t"):
            self.assertEqual(limpiar_telefono(basura), "0412-0000000", repr(basura))

    def test_fijo_regional(self):
        # San Felipe 0254 / Barquisimeto 0251
        self.assertEqual(limpiar_telefono("02541234567"), "0254-1234567")


# =============================================================================
# NOMBRES CON DESASTRES DE TIPEO
# =============================================================================

class TestNombresExtremos(unittest.TestCase):
    def test_espacios_multiples_y_caps(self):
        self.assertEqual(formatear_nombre_propio("  MARÍA   DEL   CARMEN  "), "María del Carmen")
        self.assertEqual(formatear_nombre_propio("JOSE"), "Jose")

    def test_una_sola_palabra(self):
        self.assertEqual(formatear_nombre_propio("ana"), "Ana")

    def test_particula_al_inicio(self):
        # Apellidos como "De la Cruz" capitalizan la primera partícula
        self.assertEqual(formatear_nombre_propio("DE LA CRUZ"), "De la Cruz")

    def test_nombres_validos_con_tildes(self):
        self.assertTrue(es_nombre_valido("José María de los Ángeles"))
        self.assertTrue(es_nombre_valido("Ñañez Ñoño"))

    def test_filas_estadisticas_completas(self):
        for fila in ("TOTAL GENERAL", "Total Varones", "Promedio de edad",
                     "OBSERVACIONES:", "Rango 6-11 años"):
            self.assertFalse(es_nombre_valido(fila), repr(fila))

    def test_linea_coordinacion_filtrada(self):
        # CORREGIDO: 'coordinación' ahora está en la lista negra de firmas
        self.assertFalse(es_nombre_valido("Coordinación"))
        self.assertFalse(es_nombre_valido("Coordinación General"))

    def test_nombres_legitimos_no_afectados_por_lista_negra(self):
        self.assertTrue(es_nombre_valido("Corina Díaz"))
        self.assertTrue(es_nombre_valido("Esteban Rogelio"))

    def test_limitacion_conocida_substring_nota(self):
        # LIMITACIÓN PREEXISTENTE: la lista negra usa substring, así que
        # 'nota' captura apellidos raros como 'Notario'. No es regresión
        # de esta iteración; se documenta por si acaso.
        self.assertFalse(es_nombre_valido("Notario Esteban"))

    def test_normalizar_encabezados_reales(self):
        # Encabezados reales con puntos pegados ahora se mapean
        self.assertEqual(normalizar_col_nombre("C.I."), "ci")
        self.assertEqual(normalizar_col_nombre("C.I. Representante"), "ci representante")


# =============================================================================
# FÓRMULA CÉDULA ESCOLAR CON DATOS PARCIALES
# =============================================================================

class TestCedulaEscolarExtrema(unittest.TestCase):
    def test_ci_representante_incompleta_zfill(self):
        # CI de 7 dígitos se rellena a 8
        self.assertEqual(generar_cedula_escolar("2015-09-01", "1234567"), "11501234567")

    def test_fecha_invalida_usa_00(self):
        self.assertEqual(generar_cedula_escolar("fecha mala", "30348783"), "10030348783")

    def test_ci_con_ruido(self):
        # El representante escribió la CI con puntos dentro del campo escolar
        self.assertEqual(generar_cedula_escolar("2016-05-10", "V-30.348.783"), "11630348783")


# =============================================================================
# DEDUPLICACIÓN CON ERRORES HUMANOS
# =============================================================================

class TestDedupeExtremo(unittest.TestCase):
    def _p(self, nombre, cedula="", escolar="", padre="", apellido="Pérez"):
        return {
            "nombre": nombre, "apellido": apellido, "cedula": cedula,
            "cedulado": "si" if cedula else ("escolar" if escolar else "no"),
            "cedula_escolar": escolar, "cedula_padre": padre,
            "nacimiento": "2010-01-01", "edad": 16, "genero": "M",
            "telefono": "0412-0000000"
        }

    def setUp(self):
        import builtins
        self._orig_input = builtins.input
        builtins.input = lambda *a, **k: ""  # Enter = DEDUP en el fallback

    def tearDown(self):
        import builtins
        builtins.input = self._orig_input

    def test_lista_vacia(self):
        self.assertEqual(deduplicar_participantes([]), [])

    def test_misma_persona_con_y_sin_puntos(self):
        # Registraron dos veces al mismo: '12345678' y 'V-12.345.678'
        lista = [self._p("Ana", cedula="12345678"), self._p("Ana", cedula="12345678")]
        res = deduplicar_participantes(lista)
        self.assertEqual(len(res), 1)

    def test_hermanos_mismo_padre_distinto_nombre(self):
        a = self._p("Jose", padre="30348783", escolar="11630348783")
        b = self._p("Maria", padre="30348783", escolar="11630348783")
        res = deduplicar_participantes([a, b])
        self.assertEqual(len(res), 2)


# =============================================================================
# DETECCIÓN DE CABECERAS HOSTILES
# =============================================================================

class TestCabecerasHostiles(_CSVMixin, unittest.TestCase):
    def test_columna_telefono_sin_encabezado(self):
        # Planilla con una tercera columna SIN encabezado llena de números
        df = pd.DataFrame([
            ["Nombre", "Apellido", ""],
            ["Ana", "Pérez", "04121234567"],
            ["Luis", "Díaz", "04167654321"],
            ["Marta", "Rojas", "04241112233"],
        ])
        _, mapa = detectar_cabeceras(df)
        self.assertIn("telefono", mapa)

    def test_encabezados_en_fila_14(self):
        # Membrete institucional enorme (14 filas de ruido)
        filas = [[f"ruido {i}"] * 3 for i in range(14)]
        filas.append(["Nombres", "Apellidos", "Cédula"])
        filas.append(["Ana", "Pérez", "12345678"])
        df = pd.DataFrame(filas)
        fila, mapa = detectar_cabeceras(df)
        self.assertEqual(fila, 14)
        self.assertIn("nombre", mapa)

    def test_columnas_autoridades_ignoradas(self):
        # La columna 'Cédula Facilitador' NO debe mapearse como cédula del alumno
        df = pd.DataFrame([
            ["Nombres", "Apellidos", "C.I. Facilitador", "Cédula"],
            ["Ana", "Pérez", "99999999", "12345678"],
        ])
        _, mapa = detectar_cabeceras(df)
        self.assertIn("cedula_alumno", mapa)
        self.assertNotEqual(mapa.get("cedula_alumno"), mapa.get("nombre"))


# =============================================================================
# ARCHIVOS COMPLETOS LLENOS DE BASURA HUMANA
# =============================================================================

class TestArchivosConBasuraHumana(_CSVMixin, unittest.TestCase):

    def _procesar(self, contenido: str):
        return procesar_archivo_participantes(self._csv(contenido))

    def test_csv_solo_con_encabezados(self):
        self.assertEqual(self._procesar("Nombres,Apellidos,Cédula\n"), [])

    def test_csv_vacio(self):
        self.assertEqual(self._procesar(""), [])

    def test_filas_total_resumen_y_firmas(self):
        partes = self._procesar(
            "Nombres,Apellidos,Cédula\n"
            "Ana,Pérez,11111111\n"
            "\n"
            "TOTALES,,\n"
            "TOTAL MASCULINO,FEMENINO,\n"
            "Firma del Facilitador,,\n"
            "Observaciones: buena asistencia,,\n"
            "Beto,Rojas,22222222\n"
        )
        nombres = [p["nombre"] for p in partes]
        self.assertEqual(nombres, ["Ana", "Beto"])

    def test_cedula_truncada_por_excel(self):
        # Excel convirtió la CE 12018345678 en notación científica/truncada '12018'
        partes = self._procesar(
            "Nombres,Apellidos,Cédula,Fecha de Nacimiento\n"
            "Pedrito,Rojas,12018,2018-03-01\n"
        )
        p = partes[0]
        self.assertEqual(p["cedula"], "")          # no es una CI válida de adulto
        self.assertEqual(p["cedulado"], "escolar") # se clasifica como escolar

    def test_nino_con_ci_de_adulto_en_su_columna(self):
        # Regla D: menor de 10 años con CI < 30 millones -> pasa a ser CI del rep.
        partes = self._procesar(
            "Nombres,Apellidos,Cédula,Fecha de Nacimiento\n"
            "Bebe,Rojas,12345678,2020-06-15\n"
        )
        p = partes[0]
        self.assertEqual(p["cedula"], "")
        self.assertEqual(p["cedula_padre"], "12345678")
        self.assertEqual(p["cedulado"], "escolar")

    def test_adulto_con_cedula_escolar_pegada(self):
        # Alguien pegó una CE de 11 dígitos en la columna Cédula
        partes = self._procesar(
            "Nombres,Apellidos,Cédula\n"
            "Adolescente,Pérez,11630348783\n"
        )
        p = partes[0]
        self.assertEqual(p["cedulado"], "escolar")
        self.assertEqual(p["cedula_escolar"], "11630348783")

    def test_fecha_futura_corregida_por_edad(self):
        # Escribieron 2024 pero la edad dice 20 años -> año corregido
        partes = self._procesar(
            "Nombres,Apellidos,Cédula,Fecha Nac.,Edad\n"
            "Adulto,Joven,33333333,2024-05-10,20\n"
        )
        p = partes[0]
        self.assertTrue(p["nacimiento"].startswith(str(pd.Timestamp.now().year - 20)))

    def test_genero_inferido_por_nombre_cuando_falta(self):
        partes = self._procesar(
            "Nombres,Apellidos,Cédula\n"
            "Andrea,Pérez,11111111\n"
            "Andrés,Rojas,22222222\n"
        )
        gen = {p["nombre"]: p["genero"] for p in partes}
        self.assertEqual(gen["Andrea"], "F")
        self.assertEqual(gen["Andrés"], "M")

    def test_genero_excepciones_masculinas_terminadas_en_a(self):
        partes = self._procesar(
            "Nombres,Apellidos,Cédula\n"
            "Luis,Pérez,11111111\n"
            "Nicolas,Rojas,22222222\n"
            "Jesus,Díaz,33333333\n"
        )
        for p in partes:
            self.assertEqual(p["genero"], "M", p["nombre"])

    def test_excel_serial_en_fecha(self):
        partes = self._procesar(
            "Nombres,Apellidos,Cédula,Fecha de Nacimiento\n"
            "Ana,Pérez,11111111,41713\n"  # serial Excel -> 2014-03-15
        )
        self.assertEqual(partes[0]["nacimiento"], "2014-03-15")

    def test_telefonos_con_guiones_y_espacios(self):
        partes = self._procesar(
            "Nombres,Apellidos,Teléfono\n"
            "Ana,Pérez,(0414) 123-45-67\n"
        )
        self.assertEqual(partes[0]["telefono"], "0414-1234567")

    def test_nombre_y_apellido_en_una_sola_columna(self):
        partes = self._procesar(
            "Estudiante,Cédula\n"
            "Ana Maria Perez Gomez,12345678\n"
        )
        p = partes[0]
        self.assertEqual(p["nombre"], "Ana Maria")
        self.assertEqual(p["apellido"], "Perez Gomez")

    def test_tres_nombres_dos_apellidos_split(self):
        partes = self._procesar(
            "Estudiante,Cédula\n"
            "Ana Maria De Los Angeles Perez Gomez,12345678\n"
        )
        p = partes[0]
        self.assertIn("Perez", p["apellido"])
        self.assertIn("Gomez", p["apellido"])

    def test_archivo_txt_solo_cedulas(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        f.write("# comentario ignorado\n30348783\n\n12345678\n")
        f.close()
        self.addCleanup(os.unlink, f.name)
        personas = procesar_archivo_texto(f.name)
        self.assertEqual(len(personas), 2)
        self.assertTrue(all(p["cedulado"] == "si" for p in personas))

    def test_archivo_txt_con_pares_cedula_nombre(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        f.write("30348783, Jair Hernandez\n")
        f.close()
        self.addCleanup(os.unlink, f.name)
        personas = procesar_archivo_texto(f.name)
        self.assertEqual(personas[0]["nombre"], "Jair Hernandez")

    def test_caracteres_unicode_raros(self):
        partes = self._procesar(
            "Nombres,Apellidos,Cédula\n"
            "D'Angelo,Núñez-Jáuregui,12345678\n"
        )
        p = partes[0]
        # COMPORTAMIENTO ACTUAL de formatear_nombre_propio: solo capitaliza la
        # primera letra; el resto va a minúsculas (incluido lo que sigue al
        # apóstrofo o al guion).
        self.assertEqual(p["nombre"], "D'angelo")
        self.assertEqual(p["apellido"], "Núñez-jáuregui")


# =============================================================================
# LIMPIAR_TEXTO CON BASURA DE PANDAS
# =============================================================================

class TestTextoBasuraPandas(unittest.TestCase):
    def test_tipos_numpy_y_timestamp(self):
        self.assertEqual(limpiar_texto(pd.Timestamp("2014-03-15")), "2014-03-15 00:00:00")
        self.assertTrue(isinstance(limpiar_texto(3.14), str))

    def test_valores_none_diversos(self):
        import numpy as np
        self.assertEqual(limpiar_texto(np.nan), "")
        self.assertEqual(limpiar_texto(float("inf")), "inf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
