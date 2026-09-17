#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de regresión del refactor de calidad (v3.5.1):
- Constante única PALABRAS_INVALIDAS_NOMBRE usada por todos los filtros.
- Prefijos telefónicos derivados de PREFIJOS_VALIDOS_TLF (sin duplicados).
- Clave de deduplicación unificada generar_clave_dedup() compartida por
  Formación y Servicios.
- Banner alineado y qmark="" conforme a REGLAS_IA.md.

Ejecutar desde la raíz del proyecto:
    py -m unittest discover -s tests -v
"""

import os
import sys
import re
import unittest
import inspect

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import normalizador_datos as nd
from modulos.normalizador_datos import (
    PALABRAS_INVALIDAS_NOMBRE,
    CABECERAS_IGNORADAS,
    PREFIJOS_VALIDOS_TLF,
    PREFIJOS_SIN_CERO,
    PREFIJOS_MOVILES_SIN_CERO,
    es_nombre_valido,
    limpiar_telefono,
    limpiar_cedula,
    detectar_cabeceras,
    deduplicar_participantes,
    generar_clave_dedup,
)
from modulos.interfaz_usuario import imprimir_banner, prompt_tipo_servicio


class TestConstantesUnificadas(unittest.TestCase):
    def test_lista_palabras_basura_activa(self):
        # La constante debe existir, ser un set no vacío y contener los casos críticos
        self.assertIsInstance(PALABRAS_INVALIDAS_NOMBRE, (set, frozenset))
        self.assertTrue(len(PALABRAS_INVALIDAS_NOMBRE) > 0)
        for critica in ('total', 'masculino', 'femenino', 'firma', 'coordinac'):
            self.assertIn(critica, PALABRAS_INVALIDAS_NOMBRE)

    def test_es_nombre_valido_usa_la_constante(self):
        for palabra in PALABRAS_INVALIDAS_NOMBRE:
            self.assertFalse(
                es_nombre_valido(f"X {palabra} y"),
                f"'{palabra}' debería filtrar la fila"
            )

    def test_cabeceras_ignoradas_definidas(self):
        self.assertTrue(len(CABECERAS_IGNORADAS) > 0)
        for cab in CABECERAS_IGNORADAS:
            self.assertNotIn(" ", cab)


class TestPrefijosTelefonicosUnificados(unittest.TestCase):
    def test_derivaciones_consistentes(self):
        self.assertEqual(len(PREFIJOS_SIN_CERO), len(PREFIJOS_VALIDOS_TLF))
        for con_cero, sin_cero in zip(PREFIJOS_VALIDOS_TLF, PREFIJOS_SIN_CERO):
            self.assertTrue(con_cero.startswith('0'))
            self.assertEqual(con_cero[1:], sin_cero)
        self.assertEqual(
            PREFIJOS_MOVILES_SIN_CERO,
            tuple(p[1:] for p in PREFIJOS_VALIDOS_TLF[:5])
        )

    def test_limpiar_telefono_acepta_todos_los_prefijos(self):
        for pref in PREFIJOS_VALIDOS_TLF:
            esperado = f"{pref}-1234567"
            self.assertEqual(limpiar_telefono(pref + "1234567"), esperado)
            self.assertEqual(limpiar_telefono(pref[1:] + "1234567"), esperado)

    def test_regresion_telefonos(self):
        self.assertEqual(limpiar_telefono("+584121234567"), "0412-1234567")
        self.assertEqual(limpiar_telefono(""), "0412-0000000")
        self.assertEqual(limpiar_telefono("abc"), "0412-0000000")

    def test_prefijo_en_campo_cedula_detectado_como_tlf(self):
        # Un móvil en el campo cédula debe moverse a teléfono y vaciar la cédula
        df = __import__("pandas").DataFrame([
            ["Nombres", "Apellidos", "Cédula"],
            ["Luis", "Díaz", "04261234567"],
        ])
        from modulos.normalizador_datos import procesar_archivo_participantes
        import tempfile
        ruta_csv = df.to_csv(index=False, header=False)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(ruta_csv)
            ruta = f.name
        try:
            partes = procesar_archivo_participantes(ruta)
            self.assertEqual(len(partes), 1)
            self.assertEqual(partes[0]["cedula"], "")
            self.assertTrue(partes[0]["telefono"].startswith("0426-"))
        finally:
            os.unlink(ruta)


class TestClaveDedupUnificada(unittest.TestCase):
    def _persona(self, **kw):
        base = {
            'nombre': '', 'apellido': '', 'cedula': '', 'cedulado': 'no',
            'cedula_padre': '', 'cedula_escolar': '',
            'nacimiento': '', 'edad': None, 'genero': '', 'telefono': ''
        }
        base.update(kw)
        return base

    def test_prioridad_ci_sobre_todo(self):
        # Si tiene CI propia, la clave ignora CE/REP (comportamiento de Formación)
        p = self._persona(nombre="Ana", cedula="111",
                          cedula_escolar="11630348783", cedula_padre="999")
        self.assertEqual(generar_clave_dedup(p), "CI:111")

    def test_claves_ce_y_rep_incluyen_primer_nombre(self):
        gemelo1 = self._persona(nombre="Jose", apellido="Perez",
                                cedula_escolar="11630348783", cedula_padre="30348783")
        gemelo2 = self._persona(nombre="Juan", apellido="Perez",
                                cedula_escolar="11630348783", cedula_padre="30348783")
        self.assertNotEqual(generar_clave_dedup(gemelo1), generar_clave_dedup(gemelo2))

    def test_mismos_datos_misma_clave(self):
        a = self._persona(nombre="Ana", apellido="Perez", cedula_padre="123")
        b = self._persona(nombre="Ana", apellido="Perez", cedula_padre="123")
        self.assertEqual(generar_clave_dedup(a), generar_clave_dedup(b))

    def test_deduplicar_participantes_usa_la_clave(self):
        fuente = inspect.getsource(deduplicar_participantes)
        self.assertIn("generar_clave_dedup", fuente)

    def test_servicios_comparte_la_misma_logica(self):
        src = inspect.getsource(nd.normalizar_personas_servicios)
        self.assertIn("generar_clave_dedup", src)

    def test_dedup_formacion_y_servicios_equivalentes(self):
        lista = [
            self._persona(nombre="Ana", cedula="111"),
            self._persona(nombre="Ana", cedula="111"),
            self._persona(nombre="Jose", cedula_escolar="CE1", cedula_padre="55"),
            self._persona(nombre="Jose", cedula_escolar="CE1", cedula_padre="55"),
            self._persona(nombre="Beto", nacimiento="2010-01-01"),
        ]
        import builtins
        original_input = builtins.input
        builtins.input = lambda *a, **k: ""
        try:
            res = deduplicar_participantes(lista)
        finally:
            builtins.input = original_input
        claves_res = [generar_clave_dedup(p) for p in res]
        self.assertEqual(len(claves_res), len(set(claves_res)))
        self.assertEqual(len(res), 3)


class TestBannerYEstiloUI(unittest.TestCase):
    def _capturar_banner(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            imprimir_banner()
        lineas = [l for l in buf.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lineas), 3, "El banner debe tener 3 líneas (borde, título, borde)")
        return lineas

    def test_banner_alineado(self):
        lineas = self._capturar_banner()
        anchos = {len(l) for l in lineas}
        self.assertEqual(len(anchos), 1,
                         "El banner quedó desalineado: anchos=%s" % sorted(anchos))
        self.assertTrue(lineas[0].startswith("╔") and lineas[1].startswith("║")
                        and lineas[2].startswith("╚"))

    def test_banner_version_actualizada(self):
        # Guarda anti-drift: banner == modulos/version.py == config/settings.json
        from modulos.version import __version__
        linea_titulo = self._capturar_banner()[1]
        self.assertIn(f"v{__version__}", linea_titulo)
        import json as _json
        cfg = _json.load(open(
            os.path.join(BASE_DIR, "config", "settings.json"), encoding="utf-8"
        ))
        self.assertEqual(cfg["app"]["version"], __version__,
                         "settings.json desincronizado respecto a modulos/version.py")

    def test_prompt_tipo_servicio_qmark_vacio(self):
        src = inspect.getsource(prompt_tipo_servicio)
        self.assertIn('qmark=""', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
