#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PUNTO DE ENTRADA MAESTRO — JsBOT RPA
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
Punto de acceso raíz con soporte bimodal:
  - Modo gráfico predeterminado (CustomTkinter)
  - Modo consola interactivo tradicional (Rich + InquirerPy)
  - Argumentos admitidos: --gui, -g, --cli, -c, --consola, --terminal
===============================================================================
"""

import os
import sys

# Compatibilidad con Canaima GNU/Linux: Forzar aceleración por software OpenGL
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

# Asegurar que la raíz del proyecto esté en el path de módulos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from modulos.orquestador import iniciar_sistema

if __name__ == "__main__":
    try:
        from modulos.telemetria import registrar_evento_inicio
        modo = "CLI" if any(arg in sys.argv[1:] for arg in ("--cli", "-c", "--consola", "--terminal")) else "GUI"
        registrar_evento_inicio(modo)
    except Exception:
        pass

    iniciar_sistema(sys.argv[1:])
