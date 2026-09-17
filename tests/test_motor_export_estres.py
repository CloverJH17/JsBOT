#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TESTS: PRUEBAS DE ESTRÉS Y VALIDACIÓN DEL MOTOR DE EXPORTACIÓN NATIVA (test_motor_export_estres.py)
===============================================================================
"""

import unittest
from unittest.mock import MagicMock, patch
from modulos.motor_export_auditoria import (
    limpiar_campo_csv,
    clasificar_actividad_datos,
    parsear_csv_actividades_infoapp,
    parsear_csv_servicios_infoapp
)
from modulos.verificador_cargas_export import (
    verificar_servicios_cargados_hoy,
    verificar_actividad_cargada
)

class TestMotorExportEstres(unittest.TestCase):
    
    def test_01_limpiar_campo_csv(self):
        self.assertEqual(limpiar_campo_csv("'Hola Mundo'"), "Hola Mundo")
        self.assertEqual(limpiar_campo_csv('"Texto con comillas"'), "Texto con comillas")
        self.assertEqual(limpiar_campo_csv("   Normal   "), "Normal")
        self.assertEqual(limpiar_campo_csv(None), "")
        self.assertEqual(limpiar_campo_csv(""), "")

    def test_02_clasificacion_actividades(self):
        # 1. Formación
        t1 = clasificar_actividad_datos("Comunidades de aprendizaje", "Formación en TIC", "Taller Tinkercad", "Montaje", 0)
        self.assertEqual(t1, "formacion")
        
        t2 = clasificar_actividad_datos("Comunidades de participación", "Robótica", "", "Clase 1", 0)
        self.assertEqual(t2, "formacion")
        
        # 2. Producto
        t3 = clasificar_actividad_datos("Comunidades de participación digital", "Contenido", "", "Diseño de Flyer", 1)
        self.assertEqual(t3, "producto")
        
        # 3. Otra actividad
        t4 = clasificar_actividad_datos("Comunidades de participación digital", "Reunión", "", "Encuentro de trabajo", 0)
        self.assertEqual(t4, "otra")

    def test_03_parsear_csv_actividades_datos_sinteticos_y_casos_borde(self):
        header = (
            "id|info_id|is_active|status_activity|code_info|user_id|line_action|report_type|specific_action|"
            "training_type|training_level|estate|municipality|parish|city|address|activity_title|date_pub|"
            "date_ini|date_end|hour_activity|developed_content|training_modality|duration_days|duration_hour|"
            "person_fe|person_ma|responsible_name|responsible_phone|responsible_type|responsible_dni|"
            "responsible_email|personal_type|organized_by_info|institutions|name_os|observations|notific|"
            "image|file|datetime|total_products|tipo_taller|profile_image|institucion_formacion|id_institucion|"
            "isnt_type|circuito_comunal|servicio_tecnologico"
        )
        # Fila 1: Formacion normal
        r1 = ["500001", "1", "1", "1", "NRYAR24", "1325", "Comunidades de aprendizaje", "Formación TIC", "", "", "", "Yaracuy", "San Felipe", "San Felipe", "San Felipe", "Urb", "Curso Robótica Básica", "2026-09-10", "2026-09-10", "2026-09-10", "1", "Contenido", "Presencial", "1", "2", "10", "15", "Jair H", "0412", "Fac", "12345", "a@b.com", "Fijo", "1", "Inst", "Linux", "Obs", "1", "", "", "2026-09-10 10:00:00", "0", "Taller Robótica", "", "", "", "", "", ""]
        # Fila 2: Producto con comillas y caracteres especiales (ñ, á)
        r2 = ["500002", "1", "1", "1", "NRYAR24", "1325", "Comunicación y medios", "Contenido", "", "", "", "Yaracuy", "San Felipe", "San Felipe", "San Felipe", "Urb", "'Diseño de infografía en Cañadón'", "2026-09-11", "2026-09-11", "2026-09-11", "1", "Contenido", "Presencial", "1", "2", "0", "0", "Jair H", "0412", "Fac", "12345", "a@b.com", "Fijo", "1", "Inst", "Linux", "Obs", "1", "", "", "2026-09-11 10:00:00", "5", "", "", "", "", "", "", ""]
        # Fila 3: Registro vacío / corrupto
        r3 = ["500003"]
        
        csv_text = header + "\n" + "|".join(r1) + "\n" + "|".join(r2) + "\n" + "|".join(r3)
        acts = parsear_csv_actividades_infoapp(csv_text.encode("utf-8"))
        
        self.assertEqual(len(acts), 2)
        self.assertEqual(acts[0]["id"], "500001")
        self.assertEqual(acts[0]["participantes"], 25)
        self.assertEqual(acts[0]["tipo_clasificacion"], "formacion")
        self.assertEqual(acts[0]["fecha"], "10/09/2026")
        
        self.assertEqual(acts[1]["id"], "500002")
        self.assertEqual(acts[1]["participantes"], 0)
        self.assertEqual(acts[1]["productos"], 5)
        self.assertEqual(acts[1]["tipo_clasificacion"], "producto")
        self.assertEqual(acts[1]["titulo"], "Diseño de infografía en Cañadón")

    def test_04_parsear_csv_servicios_datos_sinteticos(self):
        # CSV simulado con 30 columnas
        header = (
            "id|user_id|info_id|user_info_cod|user_nombres|user_apellidos|user_dni|user_correo|user_telefono|"
            "user_genero|user_comunity_type|user_pertenece_organizacion|disability_type|user_etnia|user_f_nacimiento|"
            "user_edad|user_nivel_academ|user_profesion|user_ocupacion|user_empleado|user_institucion|user_estado|"
            "user_municipio|user_direccion|user_tipo_servicio|user_fecha_servicio|user_name_os|user_fecha_reg|"
            "user_f_id|user_espacio_visitado"
        )
        # Fila 1: Cedulado
        r1 = ["300001", "1325", "634", "NRYAR24", "'Juan'", "'Perez'", "12345678", "j@p.com", "0412", "M", "Comunidad", "No", "Ninguna", "No", "1990-01-01", "36", "Universitario", "Ing", "Empleado", "Si", "Infocentro", "Yaracuy", "San Felipe", "Dir", "Asesoría TIC", "2026-09-12", "Linux", "2026-09-12", "1", "1"]
        # Fila 2: No cedulado
        r2 = ["300002", "1325", "634", "NRYAR24", "'Ana'", "'Gomez'", "0", "", "", "F", "Comunidad", "No", "Ninguna", "No", "2018-01-01", "8", "Primaria", "Estudiante", "No", "No", "Escuela", "Yaracuy", "San Felipe", "Dir", "Navegación", "2026-09-12", "Linux", "2026-09-12", "1", "1"]
        
        csv_text = header + "\n" + "|".join(r1) + "\n" + "|".join(r2)
        srvs = parsear_csv_servicios_infoapp(csv_text.encode("utf-8"))
        
        self.assertEqual(len(srvs), 2)
        self.assertEqual(srvs[0]["id"], "300001")
        self.assertTrue(srvs[0]["cedulado"])
        self.assertEqual(srvs[0]["usuario_nombre"], "Juan Perez")
        self.assertEqual(srvs[0]["fecha"], "12/09/2026")
        
        self.assertEqual(srvs[1]["id"], "300002")
        self.assertFalse(srvs[1]["cedulado"])
        self.assertEqual(srvs[1]["usuario_nombre"], "Ana Gomez")

    def test_05_csv_vacio_o_invalido(self):
        self.assertEqual(parsear_csv_actividades_infoapp(b""), [])
        self.assertEqual(parsear_csv_actividades_infoapp(b"header|only"), [])
        self.assertEqual(parsear_csv_servicios_infoapp(b""), [])
        self.assertEqual(parsear_csv_servicios_infoapp(b"header|only"), [])

    @patch("modulos.verificador_cargas_export.consultar_servicios_infoapp_export")
    def test_06_verificar_servicios_cargados_hoy(self, mock_srv):
        mock_srv.return_value = (2, [
            {"id": "101", "dni": "20111222", "usuario_nombre": "Carlos M"},
            {"id": "102", "dni": "25333444", "usuario_nombre": "Maria L"}
        ])
        session = MagicMock()
        
        # Caso 1: Todos presentes
        res = verificar_servicios_cargados_hoy(session, "1325", ["20111222", "25333444"])
        self.assertTrue(res["exito_completo"])
        self.assertEqual(res["confirmados_total"], 2)
        self.assertEqual(len(res["faltantes"]), 0)
        
        # Caso 2: Cédula faltante
        res2 = verificar_servicios_cargados_hoy(session, "1325", ["20111222", "99999999"])
        self.assertFalse(res2["exito_completo"])
        self.assertEqual(res2["confirmados_total"], 1)
        self.assertIn("99999999", res2["faltantes"])

    @patch("modulos.verificador_cargas_export.consultar_actividades_infoapp_export")
    def test_07_verificar_actividad_cargada(self, mock_act):
        mock_act.return_value = (1, [
            {"id": "528449", "titulo": "Taller de Robótica", "participantes": 62}
        ])
        session = MagicMock()
        
        # Encontrada por ID
        r1 = verificar_actividad_cargada(session, "1325", "528449")
        self.assertTrue(r1["encontrada"])
        self.assertEqual(r1["id"], "528449")
        
        # Encontrada por Título parcial
        r2 = verificar_actividad_cargada(session, "1325", "robótica")
        self.assertTrue(r2["encontrada"])
        
        # No encontrada
        r3 = verificar_actividad_cargada(session, "1325", "Tinkercad Inexistente")
        self.assertFalse(r3["encontrada"])

if __name__ == "__main__":
    unittest.main()
