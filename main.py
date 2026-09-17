#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PUNTO DE ENTRADA MAESTRO — JsBOT v4.3.0
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — Versión 4.3.0
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

from modulos.orquestador import iniciar_sistema

if __name__ == "__main__":
    iniciar_sistema(sys.argv[1:])
