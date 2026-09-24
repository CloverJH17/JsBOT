#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de extremo a extremo para la ingesta ETL."""
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from modulos import normalizador_datos as nd
from modulos.identidad_utils import formatear_telefono_venezolano, limpiar_cedula_universal


class TestETLNuevaSuite(unittest.TestCase):
    def test_csv_con_membretes_y_cabeceras_se_procesa(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "participantes.csv"
            with ruta.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["PLAN DE CAPACITACIÓN"])
                writer.writerow(["Nombres", "Apellidos", "Cédula", "Fecha de Nacimiento", "Teléfono", "Sexo"])
                writer.writerow(["ana", "pérez", "25123456", "1995-04-03", "04121234567", "Femenino"])
                writer.writerow(["luis", "gómez", "26123457", "1997-08-09", "04161234567", "Masculino"])

            with patch.object(nd, "log_etl"):
                resultado = nd.procesar_archivo_participantes(str(ruta))

            self.assertEqual(len(resultado), 2)
            self.assertEqual(resultado[0]["nombre"], "Ana")
            self.assertEqual(resultado[0]["apellido"], "Pérez")
            self.assertEqual(resultado[0]["cedula"], "25123456")
            self.assertEqual(resultado[0]["nacimiento"], "1995-04-03")
            self.assertEqual(resultado[0]["genero"], "F")

    def test_xlsx_numerado_detecta_espacios_y_acentos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "numerado.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["1.N°", "2.Nombre de la Institución", "3.Nombres", "4.Apellidos", "5.Cédula de Identidad (si aplica)", "6.Edad", "7.Sexo (Masculino o Femenino)", "8.Grado que cursa", "Teléfono celular"])
            sheet.append(["1", "ESCUELA", "MARÍA", "ROJAS", "27123456", "12", "Femenino", "5", "04241234567"])
            workbook.save(ruta)

            with patch.object(nd, "log_etl"):
                resultado = nd.procesar_archivo_participantes(str(ruta))

            self.assertEqual(len(resultado), 1)
            self.assertEqual(resultado[0]["nombre"], "María")
            self.assertEqual(resultado[0]["apellido"], "Rojas")
            self.assertEqual(resultado[0]["cedula"], "27123456")
            self.assertEqual(resultado[0]["telefono"], "0424-1234567")

    def test_deduplicacion_conserva_hermanos_con_mismo_representante(self):
        participantes = [
            {"nombre": "Ana", "apellido": "Pérez", "cedula": "", "cedula_escolar": "11630348783", "cedula_padre": "30348783", "cedulado": "escolar"},
            {"nombre": "Luis", "apellido": "Pérez", "cedula": "", "cedula_escolar": "11630348783", "cedula_padre": "30348783", "cedulado": "escolar"},
            {"nombre": "Ana", "apellido": "Pérez", "cedula": "25123456", "cedulado": "si"},
        ]
        unicos, reporte = nd.deduplicar_participantes(participantes, modo_interactivo=False, retornar_reporte=True)
        self.assertEqual(len(unicos), 3)
        self.assertEqual(reporte["duplicados_omitidos"], 0)

    def test_normalizadores_rechazan_valores_no_utiles(self):
        self.assertEqual(limpiar_cedula_universal("00000000"), "")
        self.assertEqual(limpiar_cedula_universal("S/D"), "")
        self.assertEqual(formatear_telefono_venezolano("+1 555 1234567"), "0412-0000000")
        self.assertEqual(nd.normalizar_col_nombre("(12) Cédula de Identidad"), "cedula de identidad")

    def test_archivo_solo_con_ruido_no_produce_participantes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "ruido.csv"
            ruta.write_text("TOTAL,ESTADISTICA,RESUMEN\n30,20,10\n", encoding="utf-8")
            with patch.object(nd, "log_etl"):
                resultado = nd.procesar_archivo_participantes(str(ruta))
            self.assertEqual(resultado, [])

    def test_cedula_escolar_se_calcula_desde_representante_y_nacimiento(self):
        resultado = nd.generar_cedula_escolar("2016-05-10", "30348783")
        self.assertEqual(resultado, "11630348783")
        self.assertEqual(len(resultado), 11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
