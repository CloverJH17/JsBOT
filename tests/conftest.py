#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aislamiento de recursos para la suite local."""
import os

# Evita que várias importaciones de NumPy/OpenBLAS agoten la memoria durante
# la recolección de pruebas en equipos pequeños.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["MALLOC_ARENA_MAX"] = "2"
