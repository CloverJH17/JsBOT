#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas nuevas de seguridad de red, SQL y automatización web."""
import unittest
from unittest.mock import MagicMock, patch

from modulos import automatizador_web
from modulos import web_utils
from modulos.motor_export_auditoria import (
    consultar_actividades_infoapp_export,
    sanitizar_texto_sql,
    validar_codigo_sql,
    validar_fecha_sql,
)
from modulos.verificador_cargas_export import obtener_participantes_existentes_actividad


class FakeLocator:
    def __init__(self):
        self.first = self

    def is_visible(self, *args, **kwargs):
        return False

    def input_value(self, *args, **kwargs):
        return ""


class TestSeguridadRedNueva(unittest.TestCase):
    def test_sanitizador_no_conserva_delimitadores_sql(self):
        resultado = sanitizar_texto_sql("' OR 1=1; -- /*x*/")
        for peligroso in ("'", ";", "--", "/*", "*/"):
            self.assertNotIn(peligroso, resultado)
        self.assertEqual(validar_codigo_sql("ABC-123_45"), "ABC-123_45")
        self.assertEqual(validar_codigo_sql("ABC' OR 1=1--"), "ABCOR11")
        self.assertEqual(validar_fecha_sql("2026-09-24"), "2026-09-24")
        self.assertEqual(validar_fecha_sql("2026-09-24' OR 1=1"), "")

    def test_export_nativo_exige_verificacion_tls(self):
        session = MagicMock()
        response = MagicMock(status_code=500, content=b"")
        session.get.return_value = response
        with patch("modulos.auditor_reportes.consultar_actividades_infoapp_http_crawler", return_value=(0, [])):
            consultar_actividades_infoapp_export(
                session,
                estado="Yaracuy",
                start_at="2026-01-01",
                finish_at="2026-01-01",
            )
        self.assertTrue(session.get.call_args.kwargs.get("verify", False))

    def test_id_actividad_no_numerico_no_llega_al_endpoint(self):
        session = MagicMock()
        resultado = obtener_participantes_existentes_actividad(session, "1 OR 1=1")
        self.assertEqual(resultado, [])
        session.get.assert_not_called()

    def test_login_respeta_url_configurada(self):
        page = MagicMock()
        page.locator.return_value = FakeLocator()
        page.goto = MagicMock()
        url_configurada = "https://ejemplo.interno/admin/index.php"

        resultado = web_utils.realizar_login_infoapp(
            page,
            "usuario",
            "clave",
            url_login=url_configurada,
        )

        self.assertTrue(resultado)  # el mock representa una sesión válida sin formulario de login
        urls = [call.args[0] for call in page.goto.call_args_list]
        self.assertTrue(any(url_configurada in str(url) for url in urls), urls)

    def test_carga_rpa_conserva_perfil_persistente(self):
        contexto = {"pw": None, "context": None, "page": None}
        contexto_mock = MagicMock()
        contexto_mock.new_page.return_value = MagicMock(
            url="https://infoapp2.infocentro.gob.ve/admin/index.php"
        )
        with patch.object(
            automatizador_web,
            "iniciar_contexto_playwright",
            return_value=(MagicMock(), contexto_mock),
        ) as iniciar, patch.object(automatizador_web, "realizar_login"):
            automatizador_web.asegurar_sesion_activa(
                contexto,
                {"usuario": "u", "clave": "c"},
            )

        self.assertEqual(iniciar.call_count, 1)
        self.assertIn("user_data_dir", iniciar.call_args.kwargs)
        self.assertTrue(str(iniciar.call_args.kwargs["user_data_dir"]).endswith("playwright_context"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
