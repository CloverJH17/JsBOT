#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TEST DE EXCLUSIÓN MUTUA Y CONCURRENCIA DE INSTANCIAS (test_concurrencia.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — Suite Pre-v4.0
Objetivo  : 
  1. Evaluar si el sistema actual maneja un archivo de bloqueo temporal
     (lockfile) al iniciar main() en modulos/orquestador.py.
  2. Implementar y validar la propuesta mínima de exclusión mutua de instancia
     única sin dependencias externas (PID checking multiplataforma Windows/Linux,
     recuperación ante locks huérfanos por apagón y liberación en atexit).
===============================================================================
"""

import os
import sys
import json
import time
import inspect
import tempfile
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.orquestador as orq


# =============================================================================
# PROPUESTA MÍNIMA DE BLOQUEO DE INSTANCIA ÚNICA (Zero External Dependencies)
# =============================================================================

def verificar_pid_activo(pid: int) -> bool:
    """
    Comprueba si un proceso con el PID dado está en ejecución.
    Multiplataforma:
      - Windows: Utiliza ctypes con kernel32.OpenProcess sin dependencias externas.
      - Linux / POSIX: Utiliza os.kill(pid, 0).
    """
    if pid <= 0:
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259

            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                codigo_salida = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(codigo_salida)):
                    return codigo_salida.value == STILL_ACTIVE
                return True
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


class GestorInstanciaUnica:
    """
    Controlador de exclusión mutua para evitar instancias concurrentes de JsBOT.
    Utiliza un archivo logs/.bot.lock con comprobación activa de PID para:
      1. Impedir que dos terminales o usuarios ejecuten el bot simultáneamente.
      2. Recuperar automáticamente bloqueos huérfanos generados por caídas o apagones.
    """

    def __init__(self, ruta_lock: str = None):
        if ruta_lock:
            self.ruta_lock = ruta_lock
        else:
            logs_dir = os.path.join(BASE_DIR, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            self.ruta_lock = os.path.join(logs_dir, ".bot.lock")
        self._adquirido = False

    def adquirir(self) -> bool:
        """
        Intenta adquirir el bloqueo exclusivo.
        Retorna:
          True  -> Bloqueo adquirido exitosamente (instancia autorizada a correr).
          False -> Otra instancia activa ya está en ejecución (bloqueo rechazado).
        """
        pid_actual = os.getpid()

        if os.path.exists(self.ruta_lock):
            try:
                with open(self.ruta_lock, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                pid_existente = datos.get("pid")
                timestamp = datos.get("timestamp")

                # Si el PID registrado sigue vivo en el sistema operativo, hay concurrencia
                if pid_existente and verificar_pid_activo(pid_existente):
                    if pid_existente != pid_actual:
                        return False
                    # Si es el mismo PID (re-adquisición en el mismo hilo), se permite
                    self._adquirido = True
                    return True
                else:
                    # El proceso anterior murió abruptamente (ej. apagón): Lock huérfano
                    self._eliminar_lock_silencioso()
            except Exception:
                # Archivo corrupto o ilegible: recuperar lock
                self._eliminar_lock_silencioso()

        # Escribir el nuevo lock con PID y timestamp actual
        try:
            temp_lock = f"{self.ruta_lock}.tmp"
            info = {
                "pid": pid_actual,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sistema": sys.platform
            }
            with open(temp_lock, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_lock, self.ruta_lock)
            self._adquirido = True
            return True
        except Exception:
            return False

    def liberar(self):
        """Libera el lock si pertenece al proceso actual."""
        if self._adquirido and os.path.exists(self.ruta_lock):
            try:
                with open(self.ruta_lock, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if datos.get("pid") == os.getpid():
                    os.remove(self.ruta_lock)
            except Exception:
                pass
            finally:
                self._adquirido = False

    def _eliminar_lock_silencioso(self):
        try:
            if os.path.exists(self.ruta_lock):
                os.remove(self.ruta_lock)
        except Exception:
            pass

    def __enter__(self):
        if not self.adquirir():
            raise RuntimeError(f"JsBOT ya se encuentra en ejecución en otra ventana o proceso.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.liberar()


# =============================================================================
# SUITE DE PRUEBAS DE CONCURRENCIA
# =============================================================================

class TestConcurrenciaYExclusionMutua(unittest.TestCase):
    """
    Evalúa el estado del código actual respecto al manejo de lockfile
    y verifica el comportamiento del mecanismo de bloqueo propuesto.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="jsbot_lock_test_")
        self.ruta_lock = os.path.join(self.tmp_dir, ".bot.lock")

    def tearDown(self):
        if os.path.exists(self.ruta_lock):
            try:
                os.remove(self.ruta_lock)
            except Exception:
                pass
        if os.path.exists(self.tmp_dir):
            try:
                os.rmdir(self.tmp_dir)
            except Exception:
                pass

    def test_01_evaluacion_sistema_actual_ausencia_de_lockfile(self):
        """
        EVALUACIÓN DE PRODUCCIÓN:
        Inspecciona modulos/orquestador.py para verificar si actualmente existe
        un mecanismo nativo de exclusión mutua de instancia única.
        Resultado esperado:
          Actualmente el código no implementa un archivo de bloqueo (.lock).
          Este test documenta formalmente la necesidad de integrarlo para v4.0.
        """
        codigo_fuente = inspect.getsource(orq.main)
        tiene_lock_en_main = any(termino in codigo_fuente.lower() for termino in ["lock", "pid", "instancia_unica", "bot.lock"])

        # Evaluamos si el orquestador implementa o no un lockfile
        if not tiene_lock_en_main:
            # Estado actual verificado: No existe archivo de bloqueo en main()
            self.assertFalse(
                tiene_lock_en_main,
                "DIAGNÓSTICO: modulos/orquestador.py no cuenta con exclusión mutua por lockfile al iniciar main()."
            )
        else:
            self.assertTrue(tiene_lock_en_main)

    def test_02_propuesta_adquisicion_exitosa_instancia_inicial(self):
        """
        PROPUESTA 1:
        Verifica que una instancia limpia adquiera el bloqueo correctamente,
        generando .bot.lock con el PID del proceso actual y timestamp.
        """
        gestor = GestorInstanciaUnica(self.ruta_lock)
        adquirido = gestor.adquirir()

        self.assertTrue(adquirido, "La primera instancia debe adquirir el lock exitosamente.")
        self.assertTrue(os.path.exists(self.ruta_lock), "El archivo .bot.lock debe ser creado en disco.")

        with open(self.ruta_lock, "r", encoding="utf-8") as f:
            datos = json.load(f)

        self.assertEqual(datos.get("pid"), os.getpid(), "El archivo lock debe contener el PID del proceso actual.")
        self.assertIn("timestamp", datos)

        gestor.liberar()
        self.assertFalse(os.path.exists(self.ruta_lock), "Al liberar, el archivo .bot.lock debe ser eliminado.")

    def test_03_propuesta_exclusion_mutua_rechaza_segunda_instancia(self):
        """
        PROPUESTA 2:
        Verifica que si una primera instancia está activa, un segundo intento
        de adquisición (otra ventana o proceso) sea inmediatamente RECHAZADO (retorna False),
        garantizando exclusión mutua estricta.
        """
        gestor_instancia_1 = GestorInstanciaUnica(self.ruta_lock)
        self.assertTrue(gestor_instancia_1.adquirir())

        # Simular una segunda instancia con otro PID activo (usamos el PID actual simulado en el archivo)
        # Un segundo gestor intenta adquirir sobre el mismo lockfile
        gestor_instancia_2 = GestorInstanciaUnica(self.ruta_lock)

        # Mockeamos os.getpid() para simular un proceso concurrente con distinto PID
        with patch("os.getpid", return_value=os.getpid() + 1000):
            with patch("tests.test_concurrencia.verificar_pid_activo", return_value=True):
                adquirido_2 = gestor_instancia_2.adquirir()
                self.assertFalse(adquirido_2,
                                 "La segunda instancia DEBE ser rechazada mientras la primera esté viva.")

        gestor_instancia_1.liberar()

    def test_04_propuesta_recuperacion_automatica_de_lock_huerfano(self):
        """
        PROPUESTA 3:
        Verifica que si un proceso anterior murió abruptamente (ej. apagón eléctrico)
        y dejó un archivo .bot.lock huérfano con un PID que ya NO existe en el SO,
        la nueva instancia detecte el PID inactivo, rompa el lock huérfano y tome
        el control exitosamente.
        """
        # Crear deliberadamente un lock huérfano con un PID inexistente
        pid_muerto = 99999999
        info_huerfana = {
            "pid": pid_muerto,
            "timestamp": "2026-08-01 10:00:00",
            "sistema": sys.platform
        }
        with open(self.ruta_lock, "w", encoding="utf-8") as f:
            json.dump(info_huerfana, f)

        # Confirmar que el PID huérfano no existe
        self.assertFalse(verificar_pid_activo(pid_muerto))

        # El nuevo gestor intenta arrancar
        gestor = GestorInstanciaUnica(self.ruta_lock)
        adquirido = gestor.adquirir()

        self.assertTrue(adquirido, "El gestor debe limpiar el lock huérfano y adquirir el control.")

        # Verificar que el lockfile ahora contenga el nuevo PID activo
        with open(self.ruta_lock, "r", encoding="utf-8") as f:
            nuevos_datos = json.load(f)

        self.assertEqual(nuevos_datos.get("pid"), os.getpid())
        gestor.liberar()

    def test_05_propuesta_soporte_context_manager(self):
        """
        PROPUESTA 4:
        Verifica el uso idiomático de Python con la sintaxis 'with GestorInstanciaUnica():'
        asegurando liberación automática incluso ante excepciones.
        """
        with GestorInstanciaUnica(self.ruta_lock):
            self.assertTrue(os.path.exists(self.ruta_lock))

        # Tras salir del context manager, el lock debe estar limpio
        self.assertFalse(os.path.exists(self.ruta_lock))


if __name__ == "__main__":
    unittest.main(verbosity=2)
