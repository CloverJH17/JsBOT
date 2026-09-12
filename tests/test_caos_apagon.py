#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST DE CAOS: CORTE ELÉCTRICO Y RESURRECCIÓN (test_caos_apagon.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — Suite Pre-v4.0
Objetivo  : Simular fallos críticos por apagón repentino durante la persistencia
            atómica de estado (.tmp), verificar que session_state.json nunca quede
            a 0 bytes o corrupto, validar la recuperación exacta del índice y
            confirmar la fusión sin pérdidas de registros previos y nuevos.
===============================================================================
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.gestor_sesion as gs


def _generar_participante(idx: int) -> dict:
    """Genera un participante sintético determinista."""
    return {
        "nombre": f"Participante_{idx:02d}",
        "apellido": f"Apellido_{idx:02d}",
        "cedula": f"{20000000 + idx}",
        "cedulado": "si",
        "cedula_escolar": "",
        "cedula_padre": "",
        "nacimiento": "2000-01-01",
        "edad": 24,
        "genero": "M" if idx % 2 == 0 else "F",
        "telefono": f"0412-{idx:07d}",
        "correo": f"user{idx}@ejemplo.com",
        "direccion": "San Felipe, Yaracuy",
        "ocupacion": "Estudiante",
        "nivel": "Educación Media General"
    }


class TestCaosApagonYResurreccion(unittest.TestCase):
    """
    Suite de simulación de corte eléctrico abrupto, integridad atómica
    y resurrección sin pérdida de participantes.
    """

    def setUp(self):
        """Aísla el entorno de logs y configuración en un directorio temporal."""
        self.tmp_dir = tempfile.mkdtemp(prefix="jsbot_caos_apagon_")
        self.session_file = os.path.join(self.tmp_dir, "session_state.json")
        self.session_tmp = f"{self.session_file}.tmp"
        self.session_serv_file = os.path.join(self.tmp_dir, "session_state_servicios.json")
        self.session_serv_tmp = f"{self.session_serv_file}.tmp"
        self.log_file = os.path.join(self.tmp_dir, "log_actividad_sim.txt")

        self.patches = [
            patch.object(gs, "LOGS_DIR", self.tmp_dir),
            patch.object(gs, "SESSION_STATE_FILE", self.session_file),
            patch.object(gs, "SESSION_STATE_SERV_FILE", self.session_serv_file),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

        self.config_base = {
            "id_actividad": "999888",
            "url": "https://infoapp2.infocentro.gob.ve/index.php?view=participants_list&id_activity=999888",
            "usuario": "facilitador_yaracuy",
            "clave": "secreto123",
            "timestamp_str": "2026-09-10_2200",
            "archivo_log": self.log_file
        }

        # Generar lote de 30 participantes sintéticos
        self.total_participantes = 30
        self.lote_30 = [_generar_participante(i) for i in range(self.total_participantes)]

    def tearDown(self):
        """Limpia los archivos temporales creados."""
        for f in [self.session_file, self.session_tmp, self.session_serv_file, self.session_serv_tmp, self.log_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        if os.path.exists(self.tmp_dir):
            try:
                os.rmdir(self.tmp_dir)
            except Exception:
                pass

    def test_01_simulacion_apagon_abrupto_preserva_archivo_y_evita_cero_bytes(self):
        """
        SIMULACIÓN 1:
        1. Guarda un estado intermedio válido en el participante 15 de 30.
        2. Simula una interrupción violenta de energía (power cut) durante el
           guardado del participante 16 antes del reemplazo atómico.
        3. Assertions:
           - session_state.json no queda en 0 bytes.
           - session_state.json contiene JSON válido e íntegro.
           - El estado no fue corrompido por el .tmp incompleto.
        """
        # Paso 1: Estado intermedio a mitad de carga (15 de 30 participantes)
        gs.guardar_estado_sesion(self.config_base, self.lote_30, indice_ultimo=15)

        self.assertTrue(os.path.exists(self.session_file), "El checkpoint de sesión debe existir.")
        tam_inicial = os.path.getsize(self.session_file)
        self.assertGreater(tam_inicial, 0, "session_state.json no debe estar vacío tras el guardado.")

        # Paso 2: Simulación de apagón abrupto a nivel de sistema operativo
        # Se genera un archivo .tmp trunco/incompleto de 0 bytes o corrupto que simula
        # que el suministro eléctrico colapsó en pleno dump antes de os.replace()
        with open(self.session_tmp, "w", encoding="utf-8") as f_tmp:
            f_tmp.write('{"id_actividad": "999888", "url": "incompleto_')  # JSON truncado por apagón

        # Intentar simular una excepción crítica durante un guardado interrumpido
        with patch("os.replace", side_effect=OSError("CORTE ELÉCTRICO: Dispositivo I/O no disponible")):
            with self.assertRaises(OSError):
                gs.guardar_estado_sesion(self.config_base, self.lote_30, indice_ultimo=16)

        # Paso 3: Verificaciones de Integridad Atómica
        self.assertTrue(os.path.exists(self.session_file), "session_state.json DEBE sobrevivir al apagón.")
        tam_final = os.path.getsize(self.session_file)
        self.assertGreater(tam_final, 0, "session_state.json NUNCA debe quedar en 0 bytes tras un fallo de escritura.")
        self.assertEqual(tam_final, tam_inicial, "El tamaño del archivo consolidado debe permanecer intacto.")

        # Verificar que el contenido siga siendo un JSON válido
        with open(self.session_file, "r", encoding="utf-8") as f_leido:
            datos = json.load(f_leido)

        self.assertEqual(datos.get("indice_ultimo_procesado"), 15,
                         "El checkpoint debe conservar el último índice exitoso (15).")
        self.assertEqual(len(datos.get("participantes", [])), 30,
                         "La estructura de participantes debe permanecer íntegra con 30 registros.")

    def test_02_resurreccion_recupera_indice_exacto_y_datos_previos(self):
        """
        SIMULACIÓN 2:
        Verifica que leer_estado_sesion() recupere con precisión milimétrica:
        - El índice exacto donde ocurrió el corte (15).
        - La totalidad de datos de los 15 participantes previamente cargados.
        - La configuración de URL y metadatos de la sesión.
        """
        # Guardar estado en el participante 15
        gs.guardar_estado_sesion(self.config_base, self.lote_30, indice_ultimo=15)

        # Invocar la función de resurrección oficial
        estado_resucitado = gs.leer_estado_sesion()

        self.assertIsNotNone(estado_resucitado, "leer_estado_sesion() debe detectar y resucitar la sesión pausada.")
        self.assertEqual(estado_resucitado["indice_ultimo_procesado"], 15,
                         "El índice resucitado debe ser exactamente 15.")
        self.assertEqual(estado_resucitado["id_actividad"], "999888")
        self.assertEqual(estado_resucitado["usuario"], "facilitador_yaracuy")

        participantes_resucitados = estado_resucitado["participantes"]
        self.assertEqual(len(participantes_resucitados), 30)

        # Validar los datos de cada uno de los 15 participantes procesados
        for i in range(15):
            esperado = self.lote_30[i]
            recuperado = participantes_resucitados[i]
            self.assertEqual(recuperado["cedula"], esperado["cedula"],
                             f"La cédula del participante {i} debe coincidir con los datos previos.")
            self.assertEqual(recuperado["nombre"], esperado["nombre"])
            self.assertEqual(recuperado["telefono"], esperado["telefono"])

    def test_03_unificacion_final_sin_descartar_registros_previos(self):
        """
        SIMULACIÓN 3:
        Simula el flujo completo de resurrección (similar a flujo_formacion en orquestador.py):
        1. Carga interrumpida en el participante 15.
        2. Resurrección: se extraen participantes_previos = participantes[:15].
        3. Se procesan los participantes restantes: nuevos_cargados = participantes[15:].
        4. Se unifican: todos_cargados = participantes_previos + nuevos_cargados.
        5. Assertions:
           - Total resultante es exactamente 30 participantes.
           - Los primeros 15 registros no sufrieron descarte, duplicación ni corrupción.
           - La lista resultante contiene todos los 30 registros en el orden original.
        """
        # Establecer el estado previo a la interrupción
        gs.guardar_estado_sesion(self.config_base, self.lote_30, indice_ultimo=15)

        # Proceso de resurrección
        estado_previo = gs.leer_estado_sesion()
        self.assertIsNotNone(estado_previo)

        indice_inicio = estado_previo.get("indice_ultimo_procesado", 0)
        self.assertEqual(indice_inicio, 15)

        # Segmentar según la lógica de orquestador.py
        participantes_completos = estado_previo.get("participantes", [])
        participantes_previos = participantes_completos[:indice_inicio]
        participantes_pendientes = participantes_completos[indice_inicio:]

        self.assertEqual(len(participantes_previos), 15, "Deben existir exactamente 15 registros previos.")
        self.assertEqual(len(participantes_pendientes), 15, "Deben existir exactamente 15 registros pendientes.")

        # Simular procesamiento exitoso del lote pendiente (15 a 29)
        nuevos_cargados = []
        for p in participantes_pendientes:
            # Simulación de éxito de carga individual en InfoApp
            nuevos_cargados.append(p)

        # Fusión oficial según orquestador.py: todos_cargados = participantes_previos + nuevos_cargados
        todos_cargados = participantes_previos + nuevos_cargados

        # Assertions de unificación
        self.assertEqual(len(todos_cargados), 30,
                         "El lote final unificado debe contener exactamente 30 participantes.")

        # Verificar que los primeros 15 sean idénticos al lote original (no descartados)
        self.assertEqual(todos_cargados[:15], self.lote_30[:15],
                         "Los 15 participantes iniciales deben preservarse intactos sin descarte.")

        # Verificar que los últimos 15 correspondan al lote nuevo completado
        self.assertEqual(todos_cargados[15:], self.lote_30[15:],
                         "Los 15 participantes procesados tras la resurrección deben integrarse correctamente.")

        # Comprobar que no haya duplicados en cédulas
        cedulas_totales = [p["cedula"] for p in todos_cargados]
        self.assertEqual(len(cedulas_totales), len(set(cedulas_totales)),
                         "No debe existir duplicidad de cédulas tras la unificación.")

    def test_04_tmp_corrupto_o_cero_bytes_es_ignorado_por_lector(self):
        """
        SIMULACIÓN 4:
        Si un apagón abrupto dejó un session_state.json.tmp con 0 bytes en disco,
        leer_estado_sesion() ignora el residuo y lee session_state.json intacto.
        """
        # Checkpoint válido
        gs.guardar_estado_sesion(self.config_base, self.lote_30, indice_ultimo=10)

        # Archivo .tmp residual dejado por apagón en un guardado posterior
        with open(self.session_tmp, "wb") as f_tmp:
            f_tmp.write(b"")  # 0 bytes huérfano

        self.assertEqual(os.path.getsize(self.session_tmp), 0)

        # Lector no debe fallar ni leer el .tmp de 0 bytes
        estado = gs.leer_estado_sesion()
        self.assertIsNotNone(estado)
        self.assertEqual(estado["indice_ultimo_procesado"], 10)
        self.assertEqual(len(estado["participantes"]), 30)

    def test_05_caos_apagon_en_servicios_comunitarios(self):
        """
        SIMULACIÓN 5:
        Verifica el mismo blindaje atómico en la atención y servicios comunitarios
        (guardar_estado_sesion_servicios y leer_estado_sesion_servicios).
        """
        cfg_bot = {
            "usuario": "facilitador_yaracuy",
            "archivo_log": self.log_file,
            "timestamp_str": "2026-09-10_2200"
        }
        cfg_srv = {
            "tipo_servicio": "Gestión en el Sistema de Protección Social Patria",
            "fecha_servicio": "2026-09-10"
        }

        # Guardar estado a mitad de camino (15 de 30 personas atendidas)
        gs.guardar_estado_sesion_servicios(cfg_bot, cfg_srv, self.lote_30, indice_ultimo=15)

        self.assertTrue(os.path.exists(self.session_serv_file))
        self.assertGreater(os.path.getsize(self.session_serv_file), 0)

        # Inyectar .tmp huérfano simulando corte eléctrico
        with open(self.session_serv_tmp, "w", encoding="utf-8") as f_tmp:
            f_tmp.write("JSON corrupto por corte súbito...")

        # Resurrección de servicios
        estado_srv = gs.leer_estado_sesion_servicios()
        self.assertIsNotNone(estado_srv)
        self.assertEqual(estado_srv["indice_ultimo_procesado"], 15)
        self.assertEqual(len(estado_srv["personas"]), 30)
        self.assertEqual(estado_srv["config_servicio"]["tipo_servicio"],
                         "Gestión en el Sistema de Protección Social Patria")

        # Fusión de personas atendidas previas y nuevas
        personas_previas = estado_srv["personas"][:15]
        personas_nuevas = estado_srv["personas"][15:]
        total_atendidos = personas_previas + personas_nuevas

        self.assertEqual(len(total_atendidos), 30)
        self.assertEqual(total_atendidos[0]["cedula"], self.lote_30[0]["cedula"])
        self.assertEqual(total_atendidos[29]["cedula"], self.lote_30[29]["cedula"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
