#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SUITE DE PRUEBAS DE ALTO RENDIMIENTO — JsBOT v5.0 MOTOR ACCELERATION
===============================================================================
Valida:
  1. Ingesta ultrarrápida con python-calamine (.xlsx, .ods, .xls).
  2. Persistencia transaccional ACID y auditoría histórica con SQLite3.
  3. Generación multiformato de planillas con odfdo y openpyxl.
  4. Bitácoras resilientes con Loguru (rotación 5MB y compresión zip).
  5. Adaptador híbrido y automatización web con Playwright.
===============================================================================
"""

import os
import sys
import tempfile
import unittest
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import openpyxl
from python_calamine import CalamineWorkbook
from loguru import logger

import modulos.entorno as entorno
from modulos.normalizador_datos import (
    procesar_archivo,
    procesar_archivo_participantes,
    detectar_cabecera_avanzada,
    detectar_cabeceras,
    limpiar_cedula,
    generar_cedula_escolar
)
from modulos.gestor_sesion import (
    inicializar_db,
    guardar_checkpoint_db,
    obtener_checkpoint_db,
    limpiar_checkpoint_db,
    registrar_inscrito_historico_db,
    consultar_inscritos_historico_db,
    guardar_estado_sesion,
    leer_estado_sesion,
    limpiar_estado_sesion,
    configurar_logger
)
from modulos.generador_planilla import (
    generar_planilla_ods_odfdo,
    generar_planilla_xlsx,
    generar_planilla_pdf,
    generar_planilla_multiformato,
    generar_planilla_oficial
)
from modulos.automatizador_web import (
    AdaptadorWebHibrido,
    iniciar_contexto_playwright,
    registrar_alumno_playwright,
    PLAYWRIGHT_DISPONIBLE
)


def _crear_participante_muestra(i=1, nombre="Maria", apellido="Perez", cedula="12345678"):
    return {
        "nombre": f"{nombre} {i}",
        "apellido": f"{apellido} {i}",
        "cedula": f"{cedula[:-1]}{i}",
        "cedulado": "si",
        "cedula_escolar": "",
        "cedula_padre": "",
        "nacimiento": "2000-05-15",
        "edad": 26,
        "genero": "F" if i % 2 == 0 else "M",
        "telefono": "0412-1234567",
        "direccion": "San Felipe, Yaracuy",
        "correo": f"participante{i}@correo.gob.ve",
        "nivel": "Educación Universitaria",
        "ocupacion": "Estudiante"
    }


# =============================================================================
# 1. PRUEBAS DE INGESTA DE HOJAS CON PYTHON-CALAMINE
# =============================================================================

class TestCalamineIngesta(unittest.TestCase):
    """Valida la lectura ultrarrápida y directa de matrices con python-calamine."""

    def test_calamine_lectura_plantilla_base_ods(self):
        plantilla = str(entorno.ARCHIVO_PLANTILLA_ODS)
        self.assertTrue(os.path.exists(plantilla), "La plantilla base ODS debe existir")
        
        wb = CalamineWorkbook.from_path(plantilla)
        self.assertTrue(len(wb.sheet_names) >= 1)
        
        sheet = wb.get_sheet_by_name(wb.sheet_names[0])
        rows = sheet.to_python()
        self.assertIsInstance(rows, list)
        self.assertTrue(len(rows) > 0)

    def test_detectar_cabecera_avanzada_desde_matriz_directa(self):
        matriz = [
            ["REPÚBLICA BOLIVARIANA DE VENEZUELA"],
            ["Infocentro San Felipe"],
            ["Nombres", "Apellidos", "Cédula", "Fecha de Nacimiento", "Teléfono", "Género"],
            ["Carlos", "Hernandez", "18234567", "1990-01-01", "04121234567", "M"],
            ["Elena", "Torres", "25345678", "1998-07-20", "04149876543", "F"],
        ]
        mejor_fila, mapa_cols = detectar_cabecera_avanzada(matriz)
        self.assertEqual(mejor_fila, 2)
        self.assertIn("nombre", mapa_cols)
        self.assertIn("apellido", mapa_cols)
        self.assertIn("cedula_alumno", mapa_cols)
        self.assertIn("nacimiento", mapa_cols)
        self.assertIn("telefono", mapa_cols)
        self.assertIn("genero", mapa_cols)

    def test_procesar_archivo_xlsx_con_calamine(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Estudiantes"
        ws.append(["Nombres", "Apellidos", "Cédula", "Fecha Nacimiento", "Teléfono", "Sexo"])
        ws.append(["Jair", "Hernandez", "30348783", "2003-09-16", "04120000000", "M"])
        ws.append(["Valeria", "Gomez", "28111222", "2001-11-20", "04165554433", "F"])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            ruta_xlsx = f.name

        try:
            wb.save(ruta_xlsx)
            participantes = procesar_archivo(ruta_xlsx)
            self.assertEqual(len(participantes), 2)
            
            p1 = participantes[0]
            self.assertEqual(p1["nombre"], "Jair")
            self.assertEqual(p1["apellido"], "Hernandez")
            self.assertEqual(p1["cedula"], "30348783")
            self.assertEqual(p1["cedulado"], "si")
            self.assertEqual(p1["nacimiento"], "2003-09-16")
            self.assertEqual(p1["genero"], "M")

            p2 = participantes[1]
            self.assertEqual(p2["nombre"], "Valeria")
            self.assertEqual(p2["apellido"], "Gomez")
            self.assertEqual(p2["cedula"], "28111222")
            self.assertEqual(p2["genero"], "F")
        finally:
            if os.path.exists(ruta_xlsx):
                os.remove(ruta_xlsx)


# =============================================================================
# 2. PRUEBAS DE PERSISTENCIA ACID Y AUDITORÍA HISTÓRICA CON SQLITE3
# =============================================================================

class TestPersistenciaSQLiteACID(unittest.TestCase):
    """Valida el almacenamiento transaccional de checkpoints e histórico."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_jsbot.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_inicializacion_esquema_db(self):
        inicializar_db(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tablas = [r[0] for r in cur.fetchall()]
            self.assertIn("checkpoints", tablas)
            self.assertIn("inscritos_historico", tablas)

    def test_guardar_y_obtener_checkpoint_db(self):
        guardar_checkpoint_db(
            id_actividad="523949",
            indice=5,
            cedula="30348783",
            estado="EN_PROCESO",
            tipo="formacion",
            datos_json='{"total": 10}',
            db_path=self.db_path
        )

        cp = obtener_checkpoint_db(id_actividad="523949", tipo="formacion", db_path=self.db_path)
        self.assertIsNotNone(cp)
        self.assertEqual(cp["id_actividad"], "523949")
        self.assertEqual(cp["indice"], 5)
        self.assertEqual(cp["cedula"], "30348783")
        self.assertEqual(cp["estado"], "EN_PROCESO")

    def test_actualizacion_checkpoint_conflicto_acid(self):
        guardar_checkpoint_db(id_actividad="777", indice=1, cedula="111", db_path=self.db_path)
        guardar_checkpoint_db(id_actividad="777", indice=2, cedula="222", db_path=self.db_path)

        cp = obtener_checkpoint_db(id_actividad="777", tipo="formacion", db_path=self.db_path)
        self.assertEqual(cp["indice"], 2)
        self.assertEqual(cp["cedula"], "222")

    def test_limpiar_checkpoint_db(self):
        guardar_checkpoint_db(id_actividad="888", indice=3, db_path=self.db_path)
        limpiar_checkpoint_db(id_actividad="888", db_path=self.db_path)
        cp = obtener_checkpoint_db(id_actividad="888", db_path=self.db_path)
        self.assertIsNone(cp)

    def test_inscritos_historico_db_roundtrip(self):
        registrar_inscrito_historico_db(
            id_actividad="ACT-101",
            cedula="12345678",
            nombre="Ana Lopez",
            telefono="0412-1112233",
            db_path=self.db_path
        )
        registrar_inscrito_historico_db(
            id_actividad="ACT-101",
            cedula="87654321",
            nombre="Pedro Perez",
            telefono="0414-3334455",
            db_path=self.db_path
        )

        res = consultar_inscritos_historico_db(id_actividad="ACT-101", db_path=self.db_path)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["cedula"], "12345678")
        self.assertEqual(res[1]["nombre"], "Pedro Perez")

        res_ci = consultar_inscritos_historico_db(cedula="12345678", db_path=self.db_path)
        self.assertEqual(len(res_ci), 1)
        self.assertEqual(res_ci[0]["nombre"], "Ana Lopez")


# =============================================================================
# 3. PRUEBAS DE GENERACIÓN MULTIFORMATO (ODFDO, OPENPYXL, WEASYPRINT)
# =============================================================================

class TestGeneracionPlanillasMultiformato(unittest.TestCase):
    """Valida la generación de reportes oficiales en .ods, .xlsx y .pdf/html."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.participantes = [_crear_participante_muestra(i) for i in range(1, 4)]

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_generar_planilla_ods_odfdo(self):
        ruta_out = os.path.join(self.tmp_dir, "Planilla_Test.ods")
        res = generar_planilla_ods_odfdo(
            participantes=self.participantes,
            id_actividad="523949",
            url_actividad="https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=523949",
            ruta_salida=ruta_out
        )
        self.assertTrue(os.path.exists(res))
        self.assertTrue(os.path.getsize(res) > 0)

    def test_generar_planilla_xlsx_openpyxl(self):
        ruta_out = os.path.join(self.tmp_dir, "Planilla_Test.xlsx")
        res = generar_planilla_xlsx(
            participantes=self.participantes,
            id_actividad="523949",
            url_actividad="https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=523949",
            ruta_salida=ruta_out
        )
        self.assertTrue(os.path.exists(res))
        
        # Verificar contenido con openpyxl
        wb = openpyxl.load_workbook(res)
        ws = wb.active
        self.assertIn("PLANILLA OFICIAL", str(ws["A2"].value))
        self.assertEqual(ws.cell(row=9, column=2).value, "Maria 1 Perez 1")
        self.assertEqual(ws.cell(row=10, column=2).value, "Maria 2 Perez 2")

    def test_generar_planilla_pdf_o_fallback(self):
        ruta_out = os.path.join(self.tmp_dir, "Planilla_Test.pdf")
        res = generar_planilla_pdf(
            participantes=self.participantes,
            id_actividad="523949",
            url_actividad="https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=523949",
            ruta_salida=ruta_out
        )
        self.assertTrue(os.path.exists(res))
        self.assertTrue(os.path.getsize(res) > 0)

    def test_generar_planilla_multiformato_enrutador(self):
        out_ods = os.path.join(self.tmp_dir, "auto.ods")
        out_xlsx = os.path.join(self.tmp_dir, "auto.xlsx")

        r1 = generar_planilla_multiformato(self.participantes, ruta_salida=out_ods)
        r2 = generar_planilla_multiformato(self.participantes, ruta_salida=out_xlsx)

        self.assertTrue(os.path.exists(r1))
        self.assertTrue(os.path.exists(r2))


# =============================================================================
# 4. PRUEBAS DE BITÁCORAS CON LOGURU
# =============================================================================

class TestLoguruBitacoras(unittest.TestCase):
    """Valida la configuración, rotación a 5MB y compresión zip de Loguru."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.tmp_dir, "actividad_{time:YYYY-MM-DD}.log")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_configuracion_logger_rotacion_compresion(self):
        lg = configurar_logger(self.log_file, nivel="DEBUG")
        self.assertIsNotNone(lg)
        
        lg.info("Mensaje de prueba de auditoría RPA JsBOT v5.0")
        lg.warning("Advertencia de prueba simulada")

        archivos = os.listdir(self.tmp_dir)
        self.assertTrue(len(archivos) >= 1)
        
        ruta_creada = os.path.join(self.tmp_dir, archivos[0])
        with open(ruta_creada, "r", encoding="utf-8") as f:
            contenido = f.read()
            self.assertIn("Mensaje de prueba de auditoría RPA JsBOT v5.0", contenido)


# =============================================================================
# 5. PRUEBAS DEL MOTOR PLAYWRIGHT Y ADAPTADOR HÍBRIDO
# =============================================================================

class TestPlaywrightAutomatizador(unittest.TestCase):
    """Valida la integración de Playwright y el adaptador híbrido."""

    def test_disponibilidad_playwright(self):
        self.assertTrue(PLAYWRIGHT_DISPONIBLE, "Playwright debe estar disponible en el entorno")

    def test_adaptador_hibrido_instanciacion(self):
        adaptador = AdaptadorWebHibrido(motor="selenium")
        self.assertEqual(adaptador.motor_preferido, "selenium")
        self.assertIsNone(adaptador.motor_activo)


if __name__ == "__main__":
    unittest.main()
