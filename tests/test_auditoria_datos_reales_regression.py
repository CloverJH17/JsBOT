#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE REGRESIÓN DE AUDITORÍA Y CUADRE MATEMÁTICO CON DATOS OFICIALES — JsBOT
Valida que el motor de exportación nativa parseé correctamente el esquema completo
de 49 columnas de reports y 30 columnas de services_users, extrayendo estudiantes
reales, dimensiones, facilitadores y cuadre al 100%.
"""

import unittest
from modulos.motor_export_auditoria import (
    parsear_csv_actividades_infoapp,
    parsear_csv_servicios_infoapp,
    clasificar_actividad_datos
)

class TestAuditoriaDatosRealesRegression(unittest.TestCase):

    def test_parseo_esquema_49_columnas_reports(self):
        """Verifica que se mapeen person_fe, person_ma, tipo_taller, etc. dinámicamente."""
        cols_rep = [
            "id", "info_id", "is_active", "status_activity", "code_info", "user_id", "line_action", "report_type",
            "specific_action", "training_type", "training_level", "estate", "municipality", "parish", "city",
            "address", "activity_title", "date_pub", "date_ini", "date_end", "hour_activity", "developed_content",
            "training_modality", "duration_days", "duration_hour", "person_fe", "person_ma", "responsible_name",
            "responsible_phone", "responsible_type", "responsible_dni", "responsible_email", "personal_type",
            "organized_by_info", "institutions", "name_os", "observations", "notific", "image", "file", "datetime",
            "total_products", "tipo_taller", "profile_image", "institucion_formacion", "id_institucion", "isnt_type",
            "circuito_comunal", "servicio_tecnologico"
        ]
        row_rep = [""] * len(cols_rep)
        row_rep[0] = "528449"
        row_rep[1] = "100"
        row_rep[4] = "NRYAR24"
        row_rep[5] = "1325"
        row_rep[6] = "Formación y Aprendizaje"
        row_rep[7] = "Comunidades de Aprendizaje"
        row_rep[11] = "Yaracuy"
        row_rep[12] = "San Felipe"
        row_rep[13] = "San Javier"
        row_rep[16] = "Curso de Robótica Educativa"
        row_rep[18] = "2026-09-10"
        row_rep[19] = "2026-09-12"
        row_rep[25] = "32"
        row_rep[26] = "30"
        row_rep[27] = "Jair Hernandez"
        row_rep[30] = "V12345678"
        row_rep[41] = "0"
        row_rep[42] = "Robótica Básica"

        csv_sample = ("|".join(cols_rep) + "\n" + "|".join(row_rep) + "\n").encode("utf-8")

        actividades = parsear_csv_actividades_infoapp(csv_sample)
        self.assertEqual(len(actividades), 1)
        act = actividades[0]

        self.assertEqual(act["id"], "528449")
        self.assertEqual(act["uid"], "1325")
        self.assertEqual(act["info_id"], "NRYAR24")
        self.assertEqual(act["participantes"], 62)
        self.assertEqual(act["part_fe"], 32)
        self.assertEqual(act["part_ma"], 30)
        self.assertEqual(act["responsable"], "Jair Hernandez")
        self.assertEqual(act["tipo_clasificacion"], "formacion")
        self.assertIn("Robótica Básica", act["dimensiones"])

    def test_parseo_esquema_30_columnas_services(self):
        """Verifica que los servicios tengan todas las claves esperadas por la GUI e inspector."""
        csv_sample = (
            "id|user_id|info_id|user_info_cod|user_nombres|user_apellidos|user_dni|user_correo|user_telefono|"
            "user_genero|user_comunity_type|user_pertenece_organizacion|disability_type|user_etnia|user_f_nacimiento|"
            "user_edad|user_nivel_academ|user_profesion|user_ocupacion|user_empleado|user_institucion|user_estado|"
            "user_municipio|user_direccion|user_tipo_servicio|user_fecha_servicio|user_name_os|user_fecha_reg|"
            "user_f_id|user_espacio_visitado\n"
            "9901|1325|100|NRYAR24|Carlos|Perez|15678901|||Masculino|||||2000-01-01|26|Universitario|Ingeniero||||Yaracuy|"
            "San Felipe||Asesoría Técnica|2026-09-15||2026-09-15||1\n"
        ).encode("utf-8")

        servicios = parsear_csv_servicios_infoapp(csv_sample)
        self.assertEqual(len(servicios), 1)
        srv = servicios[0]

        self.assertEqual(srv["id"], "9901")
        self.assertEqual(srv["servicio"], "Asesoría Técnica")
        self.assertEqual(srv["cedula"], "15678901")
        self.assertEqual(srv["usuario"], "Carlos Perez")
        self.assertEqual(srv["profesion"], "Ingeniero")
        self.assertTrue(srv["cedulado"])

if __name__ == "__main__":
    unittest.main()
