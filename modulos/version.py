#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FUENTE UNICA DE VERSION — JsBOT RPA
===============================================================================
Sistema   : JsBOT (Robotic Process Automation)
Autor     : Jair Alejandro Hernandez Gonzalez
Ubicacion : San Felipe, Estado Yaracuy, Republica Bolivariana de Venezuela

Unica ubicacion del proyecto donde se declara el numero de version.
Toda la UI, la CLI, los reportes y los lanzadores consumen estas constantes.
Para publicar un nuevo release: actualizar aqui, espejar el valor en
config/settings.json (app.version) y registrar el cambio en
docs/version.txt y docs/historial/version.txt.
===============================================================================
"""

__version__ = "4.8.0"
__author__ = "Jair Alejandro Hernandez Gonzalez"
NOMBRE_APP = "JsBOT (Robotic Process Automation)"
ETIQUETA_VERSION = f"v{__version__}"


def banner_texto(descripcion: str = "GESTION MASIVA DE ACTIVIDADES Y SERVICIOS INFOCENTRO") -> str:
    """Compone la linea central del banner CLI con ancho fijo de 78 columnas."""
    return f"JsBOT {ETIQUETA_VERSION} — {descripcion}"
