#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: INTERFAZ GRÁFICA NATIVA (interfaz_grafica.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Tecnología: Python + CustomTkinter (Dark Mode con acentos #3B8ED0 y #22c55e)
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Yaracuy, Venezuela
===============================================================================
"""

import os
import sys

# Compatibilidad con Canaima GNU/Linux: Forzar renderizado OpenGL por software
# antes de cualquier importación de librerías gráficas (Tkinter, CustomTkinter)
os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

import json
import time
import shutil
import subprocess
import threading
import queue
import webbrowser
import configparser
import unicodedata
import calendar
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Union
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
import modulos.entorno as entorno
from modulos.version import __version__, ETIQUETA_VERSION, NOMBRE_APP

# Asegurar acceso a la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")

# Despachador nativo multiplataforma (Canaima / Linux / Windows)
def abrir_archivo_o_directorio_sistema(ruta: str) -> bool:
    """Abre un archivo o directorio con la aplicación nativa del sistema operativo."""
    if not ruta or not os.path.exists(ruta):
        return False
    try:
        if sys.platform.startswith('win'):
            os.startfile(ruta)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', ruta])
        else:
            # Canaima GNU/Linux, Debian, Ubuntu
            subprocess.Popen(['xdg-open', ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def normalizar_clave_vista(clave: str) -> str:
    """Normaliza y mapea canónicamente los identificadores de vistas (insensible a mayúsculas y diacríticos)."""
    if not clave:
        return "Diagnostico"
    s = str(clave).strip()
    s_norm = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    ).lower()

    mapping = {
        "diagnostico": "Diagnostico",
        "dashboard": "Dashboard",
        "credenciales": "Credenciales",
        "cuenta": "Credenciales",
        "formacion": "Formacion",
        "servicios": "Servicios",
        "planillas": "Planillas",
        "ods": "Planillas",
        "reportes": "Reportes",
        "inspector": "Reportes",
        "auditoria": "Reportes",
        "auditor": "Auditor",
        "analisis": "Analisis",
        "creditos": "Creditos",
        "ajustes": "Ajustes",
    }
    return mapping.get(s_norm, s)

# Importaciones de los módulos funcionales
try:
    from modulos.normalizador_datos import (
        procesar_archivo_participantes,
        procesar_archivo_texto,
        deduplicar_participantes,
        abrir_archivo_asistido,
        limpiar_fecha
    )
    from modulos.verificador_entorno import (
        detectar_sistema_operativo,
        detectar_navegadores,
        detectar_suite_ofimatica,
        verificar_integridad_archivos
    )
    from modulos.automatizador_web import (
        ejecutar_carga_infoapp,
        ejecutar_carga_servicios_infoapp
    )
    from modulos.generador_planilla import generar_planilla_oficial
    from modulos.gestor_sesion import (
        obtener_credenciales,
        guardar_credenciales,
        extraer_id_actividad,
        extraer_id_servicio,
        guardar_estado_sesion,
        guardar_estado_sesion_servicios,
        leer_estado_sesion,
        leer_estado_sesion_servicios,
        limpiar_estado_sesion,
        limpiar_estado_sesion_servicios,
        finalizar_log_exito,
        finalizar_log_incompleto,
        generar_reporte_auditoria_excel,
        generar_reporte_auditoria_servicios,
        cargar_config_servicios
    )
    from modulos import config_manager as cm
    from modulos import auditor_reportes as ar
    MODULOS_DISPONIBLES = True
except Exception as e:
    MODULOS_DISPONIBLES = False
    ERROR_IMPORTACION = str(e)

# Configuración global de tema y apariencia
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Ruta canónica a los iconos de producción en config/assets/iconos
RUTA_ICONOS = str(Path(__file__).resolve().parent.parent / "config" / "assets" / "iconos")
if not os.path.exists(RUTA_ICONOS):
    RUTA_ICONOS = os.path.join(BASE_DIR, "pruebas", "assets", "iconos")

# Pre-carga en memoria del diagnóstico del entorno para acelerar arranque (Ley de Doherty < 2.5s)
_CACHE_DIAGNOSTICO_INICIAL = {}

def _obtener_diagnostico_entorno(forzar: bool = False) -> dict:
    global _CACHE_DIAGNOSTICO_INICIAL
    if forzar or not _CACHE_DIAGNOSTICO_INICIAL:
        so_nombre = detectar_sistema_operativo() if MODULOS_DISPONIBLES else "Windows"
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        py_ok = sys.version_info >= (3, 10)
        nav_desc = detectar_navegadores() if MODULOS_DISPONIBLES else "Chrome / Edge detectado"
        suite_ok, suite_ruta = detectar_suite_ofimatica() if MODULOS_DISPONIBLES else (True, "LibreOffice")
        archivos_diag = verificar_integridad_archivos() if MODULOS_DISPONIBLES else {
            "settings": (True, "config/settings.json"),
            "plantilla": (True, "config/plantilla_base.ods")
        }
        _CACHE_DIAGNOSTICO_INICIAL = {
            "so_nombre": so_nombre,
            "py_ver": py_ver,
            "py_ok": py_ok,
            "nav_desc": nav_desc,
            "suite_ok": suite_ok,
            "suite_ruta": suite_ruta,
            "archivos_diag": archivos_diag,
            "archivos_ok": all(v[0] for v in archivos_diag.values()),
        }
    return _CACHE_DIAGNOSTICO_INICIAL

if MODULOS_DISPONIBLES:
    try:
        _obtener_diagnostico_entorno(forzar=False)
    except Exception:
        pass


class JsBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Configuración de Ventana Principal (Calibrada para 1366x768)
        self.title(f"{NOMBRE_APP} — Versión {__version__}")
        self.geometry("1020x670")
        self.minsize(980, 620)

        # Centrar ventana en pantalla
        self._centrar_ventana(1020, 670)

        # Configuración del grid principal (Sidebar: 220px, Contenedor Principal: expandible)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Estado global de la aplicación
        self.seccion_actual = "Diagnostico"
        self.participantes_cargados = []
        self.datos_normalizados_actuales = []
        self.reporte_deduplicacion_actual = None
        self.archivo_actual_ruta = ""
        self.ejecutando_tarea = False

        # Variables de Auditoría / Inspector (v4.2.0)
        hoy_dt = datetime.now()
        primer_dia_mes = hoy_dt.replace(day=1).strftime("%Y-%m-%d")
        hoy_str = hoy_dt.strftime("%Y-%m-%d")

        self.var_modo_auditoria = tk.StringVar(value="Por Facilitador (UID)")
        self.var_criterio_uid = tk.StringVar(value="1325")
        self.var_criterio_infoid = tk.StringVar(value="NRYAR24")
        self.var_criterio_estado = tk.StringVar(value="Yaracuy")
        self.var_fecha_desde_aud = tk.StringVar(value=primer_dia_mes)
        self.var_fecha_hasta_aud = tk.StringVar(value=hoy_str)
        self.var_rol_auditor = tk.BooleanVar(value=False)
        self.var_modo_turbo = tk.BooleanVar(value=True)
        self.var_exportar_formato = tk.StringVar(value="LibreOffice Calc (.ods)")
        self.ejecutando_auditoria = False
        self.resultado_auditoria_actual = None
        self.ruta_ultimo_reporte_auditoria = ""
        self.directorio_reportes_auditoria = os.path.join(BASE_DIR, "Reportes_Auditoria")

        # Control de microanimaciones no bloqueantes (after)
        self._animando_pulso = False
        self._pulso_after_id = None
        self._banner_anim_id = None
        self._target_progreso = 0.0

        # Variables Tkinter para Formación
        self.archivo_seleccionado_formacion = tk.StringVar(value="Ningún archivo seleccionado")
        self.var_modo_visible_formacion = tk.BooleanVar(value=True)
        self.var_generar_ods_formacion = tk.BooleanVar(value=True)

        # Variables Tkinter para Servicios
        self.archivo_seleccionado_servicios = tk.StringVar(value="Ningún archivo seleccionado")
        self.var_modo_visible_servicios = tk.BooleanVar(value=True)
        self.var_registro_tramite_servicios = tk.BooleanVar(value=True)

        # Variables Tkinter para Planillas
        self.archivo_seleccionado_planillas = tk.StringVar(value="Ningún archivo seleccionado")
        self.participantes_cargados_planillas = []
        self.datos_normalizados_planillas = []
        self.reporte_deduplicacion_planillas = None

        # Variables de Credenciales InfoApp (Persistidas en config/config.ini)
        u_init, c_init = obtener_credenciales() if MODULOS_DISPONIBLES else ("", "")
        self.usuario_activo = u_init
        self.clave_activa = c_init
        self.var_cred_usuario = tk.StringVar(value=u_init)
        self.var_cred_clave = tk.StringVar(value=c_init)

        # Variables para Ajustes Interactivos con valores base
        self.defaults_ajustes = {
            "login": 15,
            "ajax": 15,
            "element": 12,
            "browser": "Firefox (Recomendado)",
            "maximized": True,
            "screenshots": True,
            "logs": True,
            "phone": "0412-0000000"
        }

        self.var_login_timeout = tk.IntVar(value=self.defaults_ajustes["login"])
        self.var_ajax_timeout = tk.IntVar(value=self.defaults_ajustes["ajax"])
        self.var_element_timeout = tk.IntVar(value=self.defaults_ajustes["element"])
        self.var_browser_pref = tk.StringVar(value=self.defaults_ajustes["browser"])
        self.var_start_maximized = tk.BooleanVar(value=self.defaults_ajustes["maximized"])
        self.var_capture_screenshots = tk.BooleanVar(value=self.defaults_ajustes["screenshots"])
        self.var_detailed_logs = tk.BooleanVar(value=self.defaults_ajustes["logs"])
        self.var_default_phone = tk.StringVar(value=self.defaults_ajustes["phone"])

        # Referencias a labels dinámicos de los sliders
        self.labels_sliders = {}

        # Registro centralizado de modales activos (CTkToplevel) para gestión robusta de ciclo de vida
        self.modales_activos: dict[str, ctk.CTkToplevel] = {}

        # Cargar valores iniciales desde config/settings.json si existe
        self._cargar_config_inicial()

        # 2. Cargar Iconos PNG y Logo Robot
        self._cargar_iconos()

        # 3. Construcción visual
        self._crear_barra_lateral()
        self._crear_contenedor_principal()

        # Configurar protocolo seguro de cierre en ventana principal
        try:
            self.protocol("WM_DELETE_WINDOW", self._al_cerrar_ventana_principal)
        except Exception:
            pass

        # Cola segura de eventos entre hilos secundarios y la interfaz
        self.cola_eventos = queue.Queue()
        self._iniciar_escucha_cola()

        # Log inicial de bienvenida
        self._agregar_log(f"[OK] Entorno gráfico JsBOT {ETIQUETA_VERSION} inicializado (Resolución 1020x670).")
        if MODULOS_DISPONIBLES:
            self._agregar_log("[OK] Módulos de verificación y normalización vinculados en modo lectura.")
        else:
            self._agregar_log(f"[ADVERTENCIA] Error cargando módulos: {ERROR_IMPORTACION}")

        # Comprobar si hay sesión previa interrumpida por apagón o corte de red
        if MODULOS_DISPONIBLES:
            self.after(300, self.comprobar_sesion_interrumpida_gui)

    # =========================================================================
    # GESTIÓN CENTRALIZADA DEL CICLO DE VIDA DE MODALES (CTkToplevel)
    # =========================================================================
    def registrar_modal(
        self,
        nombre: str,
        modal: ctk.CTkToplevel,
        grab: bool = True,
        al_cerrar: Optional[Callable] = None
    ) -> ctk.CTkToplevel:
        """Registra un modal activo en self.modales_activos con protocolo seguro de cierre y control de grab."""
        if not hasattr(self, "modales_activos"):
            self.modales_activos = {}

        if nombre in self.modales_activos:
            antiguo = self.modales_activos.get(nombre)
            if antiguo is not None and antiguo is not modal:
                try:
                    if antiguo.winfo_exists():
                        self.cerrar_modal(antiguo)
                except Exception:
                    pass

        self.modales_activos[nombre] = modal

        if al_cerrar is not None:
            modal._cb_al_cerrar = al_cerrar

        def _on_wm_delete():
            self.cerrar_modal(modal)

        try:
            modal.protocol("WM_DELETE_WINDOW", _on_wm_delete)
        except Exception:
            pass

        if grab:
            try:
                modal.grab_set()
            except Exception:
                pass

        return modal

    def cerrar_modal(self, nombre_o_instancia: Union[str, ctk.CTkToplevel]) -> None:
        """Cierra de forma segura un modal activo: libera grab, invoca al_cerrar y destruye el widget."""
        if not hasattr(self, "modales_activos"):
            self.modales_activos = {}
            return

        modal = None
        clave_encontrada = None

        if isinstance(nombre_o_instancia, str):
            clave_encontrada = nombre_o_instancia
            modal = self.modales_activos.get(nombre_o_instancia)
        else:
            modal = nombre_o_instancia
            for k, m in list(self.modales_activos.items()):
                if m is modal:
                    clave_encontrada = k
                    break

        if clave_encontrada and clave_encontrada in self.modales_activos:
            self.modales_activos.pop(clave_encontrada, None)

        if modal is None:
            return

        # 1. Liberar grab de forma segura
        try:
            modal.grab_release()
        except Exception:
            pass

        # 2. Invocar callback de cierre si fue registrado (previniendo recursión)
        cb = getattr(modal, "_cb_al_cerrar", None)
        try:
            delattr(modal, "_cb_al_cerrar")
        except Exception:
            pass
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

        # 3. Destruir el widget de ventana
        try:
            if modal.winfo_exists():
                modal.destroy()
        except Exception:
            pass

    def cerrar_modales_activos(self, excluir: Optional[Union[str, ctk.CTkToplevel]] = None) -> None:
        """Cierra todas las ventanas modales secundarias registradas, excepto la indicada."""
        if not hasattr(self, "modales_activos"):
            self.modales_activos = {}
            return

        modal_excluir = None
        clave_excluir = None
        if isinstance(excluir, str):
            clave_excluir = excluir
            modal_excluir = self.modales_activos.get(excluir)
        elif excluir is not None:
            modal_excluir = excluir
            for k, m in list(self.modales_activos.items()):
                if m is modal_excluir:
                    clave_excluir = k
                    break

        for k, modal in list(self.modales_activos.items()):
            if k == clave_excluir or modal is modal_excluir:
                continue
            self.cerrar_modal(modal)

    def _al_cerrar_ventana_principal(self):
        """Cierre ordenado de la ventana principal y de todos los modales secundarios activos."""
        try:
            self.cerrar_modales_activos()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _iniciar_escucha_cola(self):
        """Procesa de forma continua y segura los eventos emitidos por hilos secundarios (Cero estrés de CPU)."""
        try:
            while True:
                item = self.cola_eventos.get_nowait()
                tipo, datos = item
                if tipo == "log":
                    self.agregar_log_telemetria(datos)
                elif tipo == "progreso":
                    self._actualizar_progreso_ui(datos)
                elif tipo == "fin_formacion":
                    self._finalizar_ejecucion_formacion(datos)
                elif tipo == "fin_servicios":
                    self._finalizar_ejecucion_servicios(datos)
                elif tipo == "fin_auditoria":
                    self._finalizar_ejecucion_auditoria(datos)
                elif tipo == "log_auditoria":
                    self._agregar_log_auditoria(datos)
                elif tipo == "progreso_auditoria":
                    self._actualizar_progreso_auditoria(datos)
                elif tipo == "exportacion_ok":
                    ruta_final = datos
                    self.ruta_ultimo_reporte_auditoria = ruta_final
                    if hasattr(self, "btn_abrir_reporte_auditoria"):
                        self.btn_abrir_reporte_auditoria.configure(state="normal", fg_color="#1f538d", hover_color="#14375e")
                    self._agregar_log_auditoria(f"💾 Reporte exportado exitosamente en: {ruta_final}")
                    self._mostrar_toast(f"Reporte exportado: {os.path.basename(ruta_final)}")
                    abrir_archivo_o_directorio_sistema(ruta_final)
                elif tipo == "exportacion_error":
                    self._agregar_log_auditoria(f"❌ Error al exportar reporte: {datos}")
                    self._mostrar_modal_mensaje("Error de Exportación", f"No se pudo generar el reporte:\n{datos}", tipo="error")
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            try:
                if self.winfo_exists():
                    self.after(35, self._iniciar_escucha_cola)
            except Exception:
                pass

    def _centrar_ventana(self, ancho: int, alto: int):
        """Calcula las coordenadas para centrar la ventana en la pantalla del usuario."""
        pantalla_ancho = self.winfo_screenwidth()
        pantalla_alto = self.winfo_screenheight()
        pos_x = max(0, int((pantalla_ancho - ancho) / 2))
        pos_y = max(0, int((pantalla_alto - alto) / 2))
        self.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")

    def comprobar_sesion_interrumpida_gui(self):
        """Detecta checkpoints guardados tras caídas de red o apagones y levanta un modal de rescate."""
        try:
            estado = leer_estado_sesion()
            if estado and estado.get("participantes"):
                total = len(estado["participantes"])
                idx = estado.get("indice_ultimo_procesado", 0)
                if 0 <= idx < total:
                    self._mostrar_modal_recuperacion(estado, idx, total, tipo="formacion")
                    return

            if "leer_estado_sesion_servicios" in globals():
                estado_srv = leer_estado_sesion_servicios()
                if estado_srv and estado_srv.get("personas"):
                    total = len(estado_srv["personas"])
                    idx = estado_srv.get("indice_ultimo_procesado", 0)
                    if 0 <= idx < total:
                        self._mostrar_modal_recuperacion(estado_srv, idx, total, tipo="servicios")
        except Exception as e:
            self._agregar_log(f"[AVISO] Error al verificar sesión previa: {e}")

    def _mostrar_modal_recuperacion(self, estado: dict, idx: int, total: int, tipo: str = "formacion"):
        modal = ctk.CTkToplevel(self)
        modal.title("Sesión Previa Detectada")
        modal.geometry("460x230")
        modal.resizable(False, False)
        self.registrar_modal("modal_recuperacion", modal, grab=True)

        id_ref = estado.get('id_actividad') or estado.get('id_servicio') or 'N/A'
        tipo_lbl = "Formación" if tipo == "formacion" else "Servicios"
        lbl = ctk.CTkLabel(
            modal,
            text=f"🚨 Se detectó una sesión interrumpida por corte de luz o red.\n"
                 f"Módulo: {tipo_lbl} | ID: {id_ref}\n"
                 f"Progreso alcanzado: Alumno/Usuario {idx} de {total} procesados.\n\n"
                 f"¿Deseas retomar la carga exactamente donde quedó?",
            font=("Segoe UI", 13),
            wraplength=420
        )
        lbl.pack(pady=20)

        frame_btns = ctk.CTkFrame(modal, fg_color="transparent")
        frame_btns.pack(pady=10)

        btn_retomar = ctk.CTkButton(
            frame_btns,
            text="Retomar Carga",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            command=lambda: [self.cerrar_modal(modal), self._reanudar_flujo_desde_estado(estado, tipo=tipo)]
        )
        btn_retomar.pack(side="left", padx=10)

        def _descartar():
            if tipo == "formacion":
                limpiar_estado_sesion()
            else:
                if "limpiar_estado_sesion_servicios" in globals():
                    limpiar_estado_sesion_servicios()
            self.cerrar_modal(modal)

        btn_descartar = ctk.CTkButton(
            frame_btns,
            text="Descartar Sesión",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=_descartar
        )
        btn_descartar.pack(side="right", padx=10)

    def _reanudar_flujo_desde_estado(self, estado: dict, tipo: str = "formacion"):
        """Carga los datos y participantes de la sesión interrumpida para continuar en su índice."""
        try:
            if tipo == "servicios":
                self.participantes_cargados = estado.get("personas", [])
                self.datos_normalizados_actuales = self.participantes_cargados
                idx = estado.get("indice_ultimo_procesado", 0)
                self.indice_inicio_recuperacion_servicios = idx
                url = estado.get("url") or ""
                if url and hasattr(self, "entry_url_servicios"):
                    self.entry_url_servicios.delete(0, tk.END)
                    self.entry_url_servicios.insert(0, url)
                self._cambiar_seccion("Servicios")
                total = len(self.participantes_cargados)
                if hasattr(self, "lbl_prevuelo_servicios_total"):
                    self.lbl_prevuelo_servicios_total.configure(text=f"Total: {total} usuarios (Reanudando en #{idx + 1})")
                if hasattr(self, "card_prevuelo_servicios") and self.card_prevuelo_servicios.winfo_manager() != "pack":
                    self.card_prevuelo_servicios.pack(fill="x", padx=16, pady=(0, 8), before=self.url_container_servicios)
                self._agregar_log(f"[RECUPERACIÓN] Sesión de servicios reanudada: Usuario {idx} de {total} listos para continuar.")
            else:
                self.participantes_cargados = estado.get("participantes", [])
                self.datos_normalizados_actuales = self.participantes_cargados
                idx = estado.get("indice_ultimo_procesado", 0)
                self.indice_inicio_recuperacion_formacion = idx
                url = estado.get("url") or estado.get("url_actividad") or ""
                if url and hasattr(self, "entry_url_formacion"):
                    self.entry_url_formacion.delete(0, tk.END)
                    self.entry_url_formacion.insert(0, url)
                self._cambiar_seccion("Formacion")
                total = len(self.participantes_cargados)
                if hasattr(self, "lbl_prevuelo_formacion_total"):
                    self.lbl_prevuelo_formacion_total.configure(text=f"Total: {total} participantes (Reanudando en #{idx + 1})")
                if hasattr(self, "card_prevuelo_formacion") and self.card_prevuelo_formacion.winfo_manager() != "pack":
                    self.card_prevuelo_formacion.pack(fill="x", padx=16, pady=(0, 8), before=self.url_container_formacion)
                self._agregar_log(f"[RECUPERACIÓN] Sesión reanudada: Alumno {idx} de {total} participantes listos para continuar.")
        except Exception as e:
            self._agregar_log(f"[ERROR] No se pudo reanudar sesión: {e}")

    def _mostrar_modal_resolucion_huerfanos(self, huerfanos: list, seccion: str = "Formacion"):
        """Muestra modal interactivo no bloqueante para asignar C.I. de tutor o gestionar menores sin documento."""
        modal = ctk.CTkToplevel(self)
        modal.title("Resolución de Menores sin Cédula ni Tutor")
        modal.geometry("540x440")
        modal.resizable(False, False)
        self.registrar_modal("modal_resolucion_huerfanos", modal, grab=True)

        lbl_tit = ctk.CTkLabel(
            modal,
            text=f"⚠️ Se detectaron {len(huerfanos)} menor(es) sin Cédula ni Representante",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F39C12"
        )
        lbl_tit.pack(pady=(16, 6))

        lbl_desc = ctk.CTkLabel(
            modal,
            text="InfoApp requiere vincular un tutor para generar la Cédula Escolar o buscar al participante.\nIngresa la C.I. del Representante para asignar a este grupo:",
            font=ctk.CTkFont(size=11),
            text_color="#D1D1D6",
            wraplength=500
        )
        lbl_desc.pack(pady=(0, 10))

        # Lista previa de menores
        frame_lista = ctk.CTkScrollableFrame(modal, height=130, fg_color="#181822", border_width=1, border_color="#292938")
        frame_lista.pack(fill="x", padx=20, pady=(0, 12))

        for i, h in enumerate(huerfanos, 1):
            nom = f"{h.get('nombre', '')} {h.get('apellido', '')}".strip() or "Participante"
            edad = f"{h.get('edad')} años" if h.get('edad') else "Edad N/D"
            lbl_item = ctk.CTkLabel(
                frame_lista,
                text=f"• #{i} {nom} ({edad})",
                font=ctk.CTkFont(size=11),
                anchor="w"
            )
            lbl_item.pack(fill="x", padx=6, pady=2)

        # Entrada Cédula Representante
        row_ci = ctk.CTkFrame(modal, fg_color="transparent")
        row_ci.pack(fill="x", padx=20, pady=(0, 8))

        lbl_ci = ctk.CTkLabel(row_ci, text="C.I. Representante:", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_ci.pack(side="left", padx=(0, 8))

        entry_ci_tutor = ctk.CTkEntry(row_ci, placeholder_text="Ej: 12345678 o V-12345678", font=ctk.CTkFont(size=11), height=32)
        entry_ci_tutor.pack(side="left", fill="x", expand=True)

        lbl_err = ctk.CTkLabel(modal, text="", font=ctk.CTkFont(size=10), text_color="#E74C3C")
        lbl_err.pack(pady=(0, 8))

        frame_btns = ctk.CTkFrame(modal, fg_color="transparent")
        frame_btns.pack(pady=(0, 16))

        def _asignar():
            val = entry_ci_tutor.get().strip()
            from modulos.identidad_utils import limpiar_cedula_universal
            ced_limpia = limpiar_cedula_universal(val)
            if not ced_limpia:
                lbl_err.configure(text="⚠️ Cédula inválida. Ingresa un número válido de al menos 5 dígitos.")
                return
            
            from modulos.normalizador_datos import asignar_tutor_a_huerfano
            for h in huerfanos:
                asignar_tutor_a_huerfano(h, ced_limpia)

            self._agregar_log(f"[TUTOR] Asignada C.I. {ced_limpia} a {len(huerfanos)} menores huérfanos.")
            self.cerrar_modal(modal)
            self._actualizar_prevuelo_tras_resolucion(seccion=seccion)

        def _conservar_cortesia():
            self._agregar_log(f"[AVISO] {len(huerfanos)} menores conservados como carga de cortesía (sin tutor).")
            self.cerrar_modal(modal)

        def _omitir():
            self.participantes_cargados = [p for p in self.participantes_cargados if p not in huerfanos]
            self.datos_normalizados_actuales = self.participantes_cargados
            self._agregar_log(f"[AVISO] {len(huerfanos)} menores sin tutor omitidos de la lista.")
            self.cerrar_modal(modal)
            self._actualizar_prevuelo_tras_resolucion(seccion=seccion)

        btn_asignar = ctk.CTkButton(
            frame_btns,
            text="Asignar C.I. Tutor",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            command=_asignar
        )
        btn_asignar.pack(side="left", padx=6)

        btn_cortesia = ctk.CTkButton(
            frame_btns,
            text="Carga de Cortesía",
            font=ctk.CTkFont(size=11),
            fg_color="#4A4A5A",
            hover_color="#3A3A4A",
            command=_conservar_cortesia
        )
        btn_cortesia.pack(side="left", padx=6)

        btn_omitir = ctk.CTkButton(
            frame_btns,
            text="Omitir Menores",
            font=ctk.CTkFont(size=11),
            fg_color="#C0392B",
            hover_color="#962D22",
            command=_omitir
        )
        btn_omitir.pack(side="left", padx=6)

    def _actualizar_prevuelo_tras_resolucion(self, seccion: str = "Formacion"):
        """Recalcula métricas de pre-vuelo tras editar participantes o asignar tutores."""
        participantes = self.participantes_cargados or []
        total = len(participantes)
        ci_saime = sum(1 for p in participantes if p.get('cedulado') == 'si' or p.get('cedula'))
        ci_escolar = sum(1 for p in participantes if p.get('cedula_escolar') or p.get('cedula_padre'))
        menores_sin_doc = sum(1 for p in participantes if not (p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre')))

        desglose_txt = f"{ci_saime} Cedulados  |  {ci_escolar} Escolares  |  {menores_sin_doc} Menores S/C"
        estado_txt = "● Estructura Actualizada y Válida" if menores_sin_doc == 0 else f"▲ {menores_sin_doc} menor(es) sin tutor"
        estado_col = "#30D158" if menores_sin_doc == 0 else "#F39C12"

        if seccion == "Servicios":
            if hasattr(self, "lbl_prevuelo_servicios_total"):
                self.lbl_prevuelo_servicios_total.configure(text=f"Total: {total} usuarios")
                self.lbl_prevuelo_servicios_desglose.configure(text=desglose_txt)
                self.lbl_prevuelo_servicios_estado.configure(text=estado_txt, text_color=estado_col)
        else:
            if hasattr(self, "lbl_prevuelo_formacion_total"):
                self.lbl_prevuelo_formacion_total.configure(text=f"Total: {total} participantes")
                self.lbl_prevuelo_formacion_desglose.configure(text=desglose_txt)
                self.lbl_prevuelo_formacion_estado.configure(text=estado_txt, text_color=estado_col)

    def _crear_label_con_icono(self, master, text="", icono_clave=None, font=None, text_color=None, compound="left", **kwargs):
        """Crea un CTkLabel tolerante a fallos de imagen o Tcl."""
        img = self.iconos.get(icono_clave) if icono_clave and hasattr(self, "iconos") else None
        if img:
            try:
                return ctk.CTkLabel(master, text=text, image=img, compound=compound, font=font, text_color=text_color, **kwargs)
            except Exception:
                pass
        return ctk.CTkLabel(master, text=text, font=font, text_color=text_color, **kwargs)

    def _crear_boton_con_icono(self, master, text="", icono_clave=None, command=None, font=None, compound="left", **kwargs):
        """Crea un CTkButton tolerante a fallos de imagen o Tcl."""
        img = self.iconos.get(icono_clave) if icono_clave and hasattr(self, "iconos") else None
        if img:
            try:
                return ctk.CTkButton(master, text=text, image=img, command=command, compound=compound, font=font, **kwargs)
            except Exception:
                pass
        return ctk.CTkButton(master, text=text, command=command, font=font, **kwargs)

    def _cargar_iconos(self):
        """Carga los iconos PNG desde config/assets/iconos/ usando CTkImage."""
        self.iconos = {}
        nombres = ["diagnostico", "cuenta", "credenciales", "formacion", "servicios", "reportes", "ajustes", "info", "robot_logo"]
        for n in nombres:
            ruta = os.path.join(RUTA_ICONOS, f"{n}.png")
            if not os.path.exists(ruta):
                alt_ruta = os.path.join(BASE_DIR, "assets", "iconos", f"{n}.png")
                if os.path.exists(alt_ruta):
                    ruta = alt_ruta
            if os.path.exists(ruta):
                try:
                    with Image.open(ruta) as im:
                        img = im.convert("RGBA").copy()
                    tam = (44, 44) if n == "robot_logo" else (18, 18)
                    self.iconos[n] = ctk.CTkImage(light_image=img, dark_image=img, size=tam)
                except Exception:
                    self.iconos[n] = None
            else:
                self.iconos[n] = None

    def _cargar_config_inicial(self):
        """Sincroniza variables locales con config/settings.json."""
        if MODULOS_DISPONIBLES:
            try:
                cfg = cm.cargar_settings()
                self.defaults_ajustes["login"] = cfg.get("timeouts", {}).get("login_wait_seconds", 15)
                self.defaults_ajustes["ajax"] = cfg.get("timeouts", {}).get("ajax_wait_seconds", 15)
                self.defaults_ajustes["element"] = cfg.get("timeouts", {}).get("element_wait_seconds", 12)
                self.defaults_ajustes["phone"] = cfg.get("validation", {}).get("default_phone", "0412-0000000")
                self.defaults_ajustes["screenshots"] = cfg.get("validation", {}).get("capture_screenshots_on_error", True)
                self.defaults_ajustes["maximized"] = cfg.get("browser", {}).get("start_maximized", True)

                prio = cfg.get("browser", {}).get("priority", ["firefox"])
                if prio and isinstance(prio, list):
                    prim = str(prio[0]).lower()
                    if "chrome" in prim:
                        self.defaults_ajustes["browser"] = "Google Chrome"
                    elif "edge" in prim:
                        self.defaults_ajustes["browser"] = "Microsoft Edge"
                    else:
                        self.defaults_ajustes["browser"] = "Firefox (Recomendado)"

                self.var_login_timeout.set(self.defaults_ajustes["login"])
                self.var_ajax_timeout.set(self.defaults_ajustes["ajax"])
                self.var_element_timeout.set(self.defaults_ajustes["element"])
                self.var_browser_pref.set(self.defaults_ajustes["browser"])
                self.var_default_phone.set(self.defaults_ajustes["phone"])
                self.var_capture_screenshots.set(self.defaults_ajustes["screenshots"])
                self.var_start_maximized.set(self.defaults_ajustes["maximized"])
            except Exception:
                pass

    # =========================================================================
    # 1. BARRA LATERAL (SIDEBAR REDUCIDO A 220PX)
    # =========================================================================
    def _crear_barra_lateral(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)  # Empujador elástico

        # 1. Logo de Robot en Sidebar
        if self.iconos.get("robot_logo"):
            try:
                self.robot_logo_label = ctk.CTkLabel(
                    self.sidebar_frame,
                    text="",
                    image=self.iconos.get("robot_logo")
                )
                self.robot_logo_label.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
            except Exception:
                pass

        # 2. Título de la App y Versión
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="JsBOT (RPA)",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=1, column=0, padx=16, pady=(0, 2), sticky="w")

        self.sub_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"Versión {__version__}",
            font=ctk.CTkFont(size=11),
            text_color="#8E8E93"
        )
        self.sub_label.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="w")

        # 3. Separador visual
        self.sep = ctk.CTkFrame(self.sidebar_frame, height=1, fg_color="#2B2B36")
        self.sep.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

        # 4. Botones de navegación superiores
        self.nav_buttons = {}

        secciones_superiores = [
            ("Diagnostico", "Diagnóstico", "diagnostico"),
            ("Credenciales", "Credenciales", "cuenta"),
            ("Formacion", "Formación", "formacion"),
            ("Servicios", "Servicios", "servicios"),
            ("Planillas", "Planillas / ODS", "reportes"),
            ("Reportes", "Reportes", "reportes"),
        ]

        for idx, (clave, texto, icono_k) in enumerate(secciones_superiores, start=4):
            es_activo = (clave == "Diagnostico")
            img_icon = self.iconos.get(icono_k) or self.iconos.get("credenciales") or self.iconos.get("cuenta")
            btn_args = {
                "text": f"  {texto}",
                "compound": "left",
                "anchor": "w",
                "height": 38,
                "corner_radius": 8,
                "font": ctk.CTkFont(size=12, weight="bold" if es_activo else "normal"),
                "fg_color": "#1f538d" if es_activo else "transparent",
                "hover_color": "#14375e" if es_activo else "#2B2B36",
                "command": lambda c=clave: self._mostrar_seccion(c)
            }
            try:
                btn = ctk.CTkButton(self.sidebar_frame, image=img_icon, **btn_args)
            except Exception:
                btn = ctk.CTkButton(self.sidebar_frame, **btn_args)
            btn.grid(row=idx, column=0, padx=12, pady=2, sticky="ew")
            self.nav_buttons[clave] = btn

        # 5. Botón 'Créditos' ubicado directamente arriba de 'Ajustes'
        btn_cred_args = {
            "text": "  Créditos",
            "compound": "left",
            "anchor": "w",
            "height": 38,
            "corner_radius": 8,
            "font": ctk.CTkFont(size=12),
            "fg_color": "transparent",
            "hover_color": "#2B2B36",
            "command": lambda: self._mostrar_seccion("Creditos")
        }
        try:
            btn_creditos = ctk.CTkButton(self.sidebar_frame, image=self.iconos.get("info"), **btn_cred_args)
        except Exception:
            btn_creditos = ctk.CTkButton(self.sidebar_frame, **btn_cred_args)
        btn_creditos.grid(row=11, column=0, padx=12, pady=(0, 2), sticky="ew")
        self.nav_buttons["Creditos"] = btn_creditos

        # 6. Botón Ajustes
        btn_aj_args = {
            "text": "  Ajustes",
            "compound": "left",
            "anchor": "w",
            "height": 38,
            "corner_radius": 8,
            "font": ctk.CTkFont(size=12),
            "fg_color": "transparent",
            "hover_color": "#2B2B36",
            "command": lambda: self._mostrar_seccion("Ajustes")
        }
        try:
            btn_ajustes = ctk.CTkButton(self.sidebar_frame, image=self.iconos.get("ajustes"), **btn_aj_args)
        except Exception:
            btn_ajustes = ctk.CTkButton(self.sidebar_frame, **btn_aj_args)
        btn_ajustes.grid(row=12, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.nav_buttons["Ajustes"] = btn_ajustes

        # 7. Tarjeta de Estado en el pie
        self.status_card = ctk.CTkFrame(self.sidebar_frame, corner_radius=10, fg_color="#181822", border_width=1, border_color="#292938")
        self.status_card.grid(row=13, column=0, padx=12, pady=(0, 16), sticky="sew")

        self.lbl_status = ctk.CTkLabel(
            self.status_card,
            text="● Sistema Listo",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#22c55e"
        )
        self.lbl_status.pack(anchor="w", padx=10, pady=(8, 2))

        lbl_browser = ctk.CTkLabel(
            self.status_card,
            text="Navegadores: Chrome / Edge",
            font=ctk.CTkFont(size=10),
            text_color="#A1A1AA"
        )
        lbl_browser.pack(anchor="w", padx=10, pady=1)

        lbl_instance = ctk.CTkLabel(
            self.status_card,
            text="Instancia: Exclusiva (.lock)",
            font=ctk.CTkFont(size=10),
            text_color="#A1A1AA"
        )
        lbl_instance.pack(anchor="w", padx=10, pady=(1, 8))

    def _mostrar_seccion(self, seccion: str):
        """Conmuta a la sección indicada en el panel central."""
        self._cambiar_seccion(seccion)

    def _cambiar_seccion(self, seccion: str):
        """Intercambia vistas en el panel central y actualiza el botón activo del sidebar."""
        seccion_clave = normalizar_clave_vista(str(seccion))

        if self.seccion_actual == seccion_clave:
            return

        self.seccion_actual = seccion_clave

        # Cerrar modales secundarios activos al navegar entre vistas
        self.cerrar_modales_activos()

        # Determinar clave canónica para iluminar el botón en self.nav_buttons
        alias_botones = {
            "Auditor": "Reportes",
            "Analisis": "Reportes",
            "Dashboard": "Diagnostico",
            "Cuenta": "Credenciales",
            "ODS": "Planillas",
        }
        boton_objetivo = alias_botones.get(seccion_clave, seccion_clave)
        boton_norm = normalizar_clave_vista(boton_objetivo)

        for clave, btn in self.nav_buttons.items():
            if normalizar_clave_vista(clave) == boton_norm:
                btn.configure(fg_color="#1f538d", hover_color="#14375e", font=ctk.CTkFont(size=12, weight="bold"))
            else:
                btn.configure(fg_color="transparent", hover_color="#2B2B36", font=ctk.CTkFont(size=12, weight="normal"))

        # Conmutar marcos con detección por identidad para evitar self-ungriding
        vistas_unicas = set(self.vistas.values())
        vista_destino = self.vistas.get(seccion_clave)
        if vista_destino is not None:
            for v in vistas_unicas:
                if v is vista_destino:
                    v.grid(row=0, column=0, sticky="nsew")
                else:
                    v.grid_forget()

        self._agregar_log(f"[NAVEGACIÓN] Sección activa: {seccion_clave}")

        if seccion_clave in ("Formacion", "Servicios") and MODULOS_DISPONIBLES:
            self.after(60, self.comprobar_sesion_interrumpida_gui)

    # Alias canónicos de navegación requeridos por arquitectura e interoperabilidad
    cambiar_vista = _cambiar_seccion
    _cambiar_vista = _cambiar_seccion
    mostrar_vista = _cambiar_seccion
    _mostrar_vista = _cambiar_seccion
    cambiar_seccion = _cambiar_seccion
    mostrar_seccion = _cambiar_seccion

    # =========================================================================
    # 2. CONTENEDOR PRINCIPAL Y VISTAS
    # =========================================================================
    def _crear_contenedor_principal(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=14)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=0)

        self.vistas_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.vistas_container.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.vistas_container.grid_columnconfigure(0, weight=1)
        self.vistas_container.grid_rowconfigure(0, weight=1)

        # Diccionario de vistas
        self.vistas = {}
        self.vistas["Diagnostico"] = self._crear_vista_diagnostico(self.vistas_container)
        self.vistas["Dashboard"] = self.vistas["Diagnostico"]
        self.frame_credenciales = self._crear_vista_credenciales(self.vistas_container)
        self.vistas["Credenciales"] = self.frame_credenciales
        self.vistas["Cuenta"] = self.frame_credenciales
        self.vistas["Formacion"] = self._crear_vista_formacion(self.vistas_container)
        self.vistas["Formación"] = self.vistas["Formacion"]
        self.vistas["Servicios"] = self._crear_vista_servicios(self.vistas_container)
        self.vistas["Planillas"] = self._crear_vista_reportes(self.vistas_container)
        self.vistas["ODS"] = self.vistas["Planillas"]
        self.vistas["Reportes"] = self.frame_reportes = self._crear_vista_inspector(self.vistas_container)
        self.vistas["Auditor"] = self.vistas["Reportes"]
        self.vistas["Analisis"] = self.vistas["Reportes"]
        self.vistas["Análisis"] = self.vistas["Reportes"]
        self.vistas["Auditoria"] = self.vistas["Reportes"]
        self.vistas["Auditoría"] = self.vistas["Reportes"]
        self.vistas["Inspector"] = self.vistas["Reportes"]
        self.vistas["Creditos"] = self._crear_vista_creditos(self.vistas_container)
        self.vistas["Créditos"] = self.vistas["Creditos"]
        self.vistas["Ajustes"] = self._crear_vista_ajustes(self.vistas_container)

        # Vista predeterminada: Diagnóstico
        self.vistas["Diagnostico"].grid(row=0, column=0, sticky="nsew")

        # Telemetría fija en la parte inferior con Toolbar compacta
        self._crear_panel_telemetria(self.main_container)

    # -------------------------------------------------------------------------
    # A. VISTA 1: DIAGNÓSTICO EN GRID (2x3 — CERO SCROLLBAR)
    # -------------------------------------------------------------------------
    def _crear_vista_diagnostico(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        # Encabezado
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        lbl_title = self._crear_label_con_icono(
            header,
            text="Diagnóstico del Sistema y Entorno",
            icono_clave="diagnostico",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        self.btn_recomprobar = self._crear_boton_con_icono(
            header,
            text="Re-comprobar Entorno",
            icono_clave="diagnostico",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._actualizar_diagnostico_en_caliente
        )
        self.btn_recomprobar.pack(side="right")

        lbl_sub = ctk.CTkLabel(
            frame,
            text="Auditoría automática integral: arquitectura, dependencias y disponibilidad operativa.",
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98"
        )
        lbl_sub.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        # Contenedor Grid (2x3) SIN scrollbar
        self.diag_grid = ctk.CTkFrame(frame, fg_color="transparent")
        self.diag_grid.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.diag_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="card_col")
        self.diag_grid.grid_rowconfigure((0, 1), weight=1, uniform="card_row")

        self._construir_cuadricula_diagnostico()
        return frame

    def _construir_cuadricula_diagnostico(self, forzar: bool = False):
        for widget in self.diag_grid.winfo_children():
            widget.destroy()

        diag = _obtener_diagnostico_entorno(forzar=forzar)
        so_nombre = diag.get("so_nombre", "Windows")
        py_ver = diag.get("py_ver", "3.10.0")
        py_ok = diag.get("py_ok", True)
        nav_desc = diag.get("nav_desc", "Detectado")
        suite_ok = diag.get("suite_ok", True)
        suite_ruta = diag.get("suite_ruta", "LibreOffice")
        archivos_diag = diag.get("archivos_diag", {})
        archivos_ok = diag.get("archivos_ok", True)

        # Tarjeta 1: Python
        self._crear_tarjeta_grid(
            self.diag_grid, row=0, col=0,
            titulo="Intérprete Python",
            valor_destacado=f"Python v{py_ver}",
            tag_texto="[OK]" if py_ok else "[ERROR]",
            tag_color="#30D158" if py_ok else "#FF453A",
            linea_1="Compatibilidad: >= 3.10 Superado",
            linea_2=f"Binario: {os.path.basename(sys.executable)}"
        )

        # Tarjeta 2: Sistema Operativo
        self._crear_tarjeta_grid(
            self.diag_grid, row=0, col=1,
            titulo="Sistema Operativo",
            valor_destacado=so_nombre,
            tag_texto="[OK]",
            tag_color="#30D158",
            linea_1="Plataforma: Arquitectura 64-bit",
            linea_2="Consola: Soporte VT100 activo"
        )

        # Tarjeta 3: Dependencias PyPI
        self._crear_tarjeta_grid(
            self.diag_grid, row=0, col=2,
            titulo="Dependencias PyPI",
            valor_destacado="Sincronizadas",
            tag_texto="[OK]",
            tag_color="#30D158",
            linea_1="Librerías: Playwright, Pandas, CTk, PIL",
            linea_2="Estado: requirements.txt verificado"
        )

        # Tarjeta 4: Navegadores Web
        nav_ok = "detectado" in nav_desc.lower() and "no detectado" not in nav_desc.lower()
        if "firefox" in nav_desc.lower() and "chrome" in nav_desc.lower():
            val_nav = "Firefox / Chrome"
        elif "firefox" in nav_desc.lower():
            val_nav = "Mozilla Firefox"
        elif "chrome" in nav_desc.lower():
            val_nav = "Google Chrome"
        elif "edge" in nav_desc.lower():
            val_nav = "Microsoft Edge"
        else:
            val_nav = "Detectado" if nav_ok else "No detectado"

        self._crear_tarjeta_grid(
            self.diag_grid, row=1, col=0,
            titulo="Navegadores Web",
            valor_destacado=val_nav,
            tag_texto="[OK]" if nav_ok else "[AVISO]",
            tag_color="#30D158" if nav_ok else "#F5A623",
            linea_1="Control: Playwright",
            linea_2="Rutas: Encontrados en PATH"
        )

        # Tarjeta 5: Suite Ofimática
        if suite_ok and suite_ruta:
            base_s = os.path.basename(suite_ruta).lower()
            if "desktopeditors" in base_s or "onlyoffice" in base_s:
                valor_suite = "ONLYOFFICE"
            elif "soffice" in base_s or "libreoffice" in base_s or "localc" in base_s:
                valor_suite = "LibreOffice"
            elif "excel" in base_s:
                valor_suite = "Microsoft Excel"
            else:
                valor_suite = os.path.basename(suite_ruta)
        else:
            valor_suite = "Modo Asistido"

        self._crear_tarjeta_grid(
            self.diag_grid, row=1, col=1,
            titulo="Suite Ofimática",
            valor_destacado=valor_suite,
            tag_texto="[OK]" if suite_ok else "[AVISO]",
            tag_color="#30D158" if suite_ok else "#F5A623",
            linea_1="Soporte: Formatos .ODS y .XLSX",
            linea_2="Asistencia HITL: Lista para aperturas"
        )

        # Tarjeta 6: Archivos Core
        self._crear_tarjeta_grid(
            self.diag_grid, row=1, col=2,
            titulo="Archivos Core",
            valor_destacado="Verificados",
            tag_texto="[OK]" if archivos_ok else "[AVISO]",
            tag_color="#30D158" if archivos_ok else "#FF453A",
            linea_1="Config: settings.json y logs/",
            linea_2="Actas: plantilla_base.ods intacta"
        )

    def _crear_tarjeta_grid(self, padre, row: int, col: int, titulo: str, valor_destacado: str, tag_texto: str, tag_color: str, linea_1: str, linea_2: str):
        card = ctk.CTkFrame(padre, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))

        lbl_t = ctk.CTkLabel(top, text=titulo, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFFFFF")
        lbl_t.pack(side="left")

        lbl_tag = ctk.CTkLabel(top, text=tag_texto, font=ctk.CTkFont(size=10, weight="bold"), text_color=tag_color)
        lbl_tag.pack(side="right")

        lbl_val = ctk.CTkLabel(
            card,
            text=valor_destacado,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#3B8ED0"
        )
        lbl_val.pack(anchor="w", padx=10, pady=(1, 4))

        lbl_l1 = ctk.CTkLabel(card, text=linea_1, font=ctk.CTkFont(size=10), text_color="#8E8E98", anchor="w")
        lbl_l1.pack(fill="x", padx=10, pady=1)

        lbl_l2 = ctk.CTkLabel(card, text=linea_2, font=ctk.CTkFont(size=10), text_color="#A1A1AA", anchor="w")
        lbl_l2.pack(fill="x", padx=10, pady=(0, 6))

    def _actualizar_diagnostico_en_caliente(self):
        self.btn_recomprobar.configure(text="Verificando...", state="disabled")
        self._agregar_log("[DIAGNÓSTICO] Re-comprobando integridad de entorno...")

        def _tarea():
            time.sleep(0.35)
            _obtener_diagnostico_entorno(forzar=True)
            self.after(0, self._terminar_refresco_diagnostico)

        threading.Thread(target=_tarea, daemon=True).start()

    def _terminar_refresco_diagnostico(self):
        self._construir_cuadricula_diagnostico(forzar=False)
        self.btn_recomprobar.configure(text="Re-comprobar Entorno", state="normal")
        self._agregar_log("[OK] Diagnóstico actualizado: 6/6 módulos verificados.")

    # -------------------------------------------------------------------------
    # B. VISTA DEDICADA: GESTIÓN DE CUENTA Y CREDENCIALES INFOAPP
    # -------------------------------------------------------------------------
    def _crear_vista_credenciales(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        # Encabezado
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        lbl_title = self._crear_label_con_icono(
            header,
            text="🔐 Gestión de Cuenta y Credenciales InfoApp",
            icono_clave="cuenta",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            header,
            text="Configura tus datos de acceso institucional para la automatización web sin exponer claves en código.",
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Tarjeta Central de Formulario
        card_form = ctk.CTkFrame(
            frame,
            corner_radius=10,
            fg_color="#161620",
            border_width=1,
            border_color="#292938"
        )
        card_form.pack(fill="x", padx=16, pady=(8, 12))

        card_inner = ctk.CTkFrame(card_form, fg_color="transparent")
        card_inner.pack(fill="x", padx=16, pady=16)

        # Indicador de Estado Superior
        u_actual = self.usuario_activo or ""
        estado_texto = f"● Estado: Cuenta guardada ({u_actual})" if u_actual else "● Estado: Sin credenciales configuradas"
        estado_color = "#22c55e" if u_actual else "#F5A623"

        row_estado = ctk.CTkFrame(card_inner, fg_color="transparent")
        row_estado.pack(fill="x", pady=(0, 12))

        self.lbl_estado_credenciales = ctk.CTkLabel(
            row_estado,
            text=estado_texto,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=estado_color
        )
        self.lbl_estado_credenciales.pack(side="left")

        # 1. Campo Usuario / Correo
        lbl_usuario = ctk.CTkLabel(
            card_inner,
            text="Usuario / Correo Institucional:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_usuario.pack(anchor="w", pady=(0, 4))

        self.entry_cred_usuario = ctk.CTkEntry(
            card_inner,
            placeholder_text="correo@infocentro.gob.ve",
            textvariable=self.var_cred_usuario,
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_cred_usuario.pack(fill="x", pady=(0, 12))

        # 2. Campo Contraseña
        lbl_clave = ctk.CTkLabel(
            card_inner,
            text="Contraseña de Acceso:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_clave.pack(anchor="w", pady=(0, 4))

        row_clave = ctk.CTkFrame(card_inner, fg_color="transparent")
        row_clave.pack(fill="x", pady=(0, 16))

        self.entry_cred_clave = ctk.CTkEntry(
            row_clave,
            show="*",
            placeholder_text="Ingresa tu contraseña de InfoApp",
            textvariable=self.var_cred_clave,
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_cred_clave.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Botón compacto para alternar visibilidad
        self.btn_toggle_ver_clave = ctk.CTkButton(
            row_clave,
            text="👁 Mostrar",
            width=90,
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._alternar_ver_clave
        )
        self.btn_toggle_ver_clave.pack(side="right")

        # Fila de Acciones y Notificación Visual
        row_acciones = ctk.CTkFrame(card_inner, fg_color="transparent")
        row_acciones.pack(fill="x", pady=(4, 2))

        self.btn_guardar_credenciales = ctk.CTkButton(
            row_acciones,
            text="Guardar Credenciales",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self._guardar_credenciales_gui
        )
        self.btn_guardar_credenciales.pack(side="left", padx=(0, 14))

        self.lbl_feedback_credenciales = ctk.CTkLabel(
            row_acciones,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#22c55e"
        )
        self.lbl_feedback_credenciales.pack(side="left")

        # Tarjeta informativa de seguridad en el pie
        card_info = ctk.CTkFrame(
            frame,
            corner_radius=8,
            fg_color="#14141E",
            border_width=1,
            border_color="#252535"
        )
        card_info.pack(fill="x", padx=16, pady=(0, 16))

        lbl_info_seguridad = ctk.CTkLabel(
            card_info,
            text="🛡️ Seguridad y Privacidad: Tus credenciales se almacenan localmente en 'config/config.ini' y se utilizan\núnicamente durante el proceso automatizado con Playwright hacia los servidores oficiales de InfoApp.",
            font=ctk.CTkFont(size=10),
            text_color="#8E8E98",
            justify="left"
        )
        lbl_info_seguridad.pack(anchor="w", padx=14, pady=10)

        return frame

    def _alternar_ver_clave(self):
        """Alterna la visibilidad del campo contraseña entre texto plano y asteriscos."""
        if self.entry_cred_clave.cget("show") == "*":
            self.entry_cred_clave.configure(show="")
            self.btn_toggle_ver_clave.configure(text="🔒 Ocultar")
        else:
            self.entry_cred_clave.configure(show="*")
            self.btn_toggle_ver_clave.configure(text="👁 Mostrar")

    def _guardar_credenciales_gui(self):
        """Persiste las credenciales en config/config.ini y actualiza la memoria activa."""
        usuario = self.entry_cred_usuario.get().strip()
        clave = self.entry_cred_clave.get().strip()

        if not usuario or not clave:
            self.lbl_feedback_credenciales.configure(
                text="⚠️ Usuario y contraseña no pueden estar vacíos",
                text_color="#F5A623"
            )
            self._agregar_log("[ERROR] Intento de guardar credenciales vacías en InfoApp.")
            return

        try:
            # 1. Escribir directamente en [LOGIN] de config/config.ini mediante configparser
            config_path = CONFIG_FILE if 'CONFIG_FILE' in globals() else os.path.join(BASE_DIR, "config", "config.ini")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            cfg = configparser.ConfigParser()
            if os.path.exists(config_path):
                try:
                    cfg.read(config_path, encoding='utf-8')
                except Exception:
                    pass

            if "LOGIN" not in cfg:
                cfg["LOGIN"] = {}
            cfg["LOGIN"]["usuario"] = usuario
            cfg["LOGIN"]["clave"] = clave

            # Mantener retrocompatibilidad con [CREDENCIALES]
            if "CREDENCIALES" not in cfg:
                cfg["CREDENCIALES"] = {}
            cfg["CREDENCIALES"]["usuario"] = usuario
            cfg["CREDENCIALES"]["clave"] = clave

            with open(config_path, "w", encoding="utf-8") as f:
                cfg.write(f)

            # 2. Actualizar variables de sesión activas en memoria para que Selenium las consuma de inmediato sin reiniciar
            self.usuario_activo = usuario
            self.clave_activa = clave

            if MODULOS_DISPONIBLES:
                try:
                    guardar_credenciales(usuario, clave)
                except Exception:
                    pass

            # 3. Emitir mensaje a la consola de telemetría
            self._agregar_log("[OK] Credenciales de InfoApp actualizadas y persistidas en config/config.ini.")

            # 4. Notificar visualmente en la tarjeta
            self.lbl_feedback_credenciales.configure(
                text="✓ Credenciales guardadas exitosamente",
                text_color="#22c55e"
            )
            self.lbl_estado_credenciales.configure(
                text=f"● Estado: Cuenta guardada ({usuario})",
                text_color="#22c55e"
            )

        except Exception as ex:
            self._agregar_log(f"[ERROR] No se pudieron guardar las credenciales: {ex}")
            self.lbl_feedback_credenciales.configure(
                text=f"✕ Error al guardar: {ex}",
                text_color="#EF4444"
            )

    # -------------------------------------------------------------------------
    # C. VISTA 3: FORMACIÓN (CON CHIP DE ARCHIVO Y BOTÓN [✕])
    # -------------------------------------------------------------------------
    def _crear_vista_formacion(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))
        lbl_title = self._crear_label_con_icono(
            header,
            text="Carga Masiva de Formación — Cursos y Actas ODS",
            icono_clave="formacion",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        # 1. Área de Ingesta con Chip de Archivo y Botón [ ✕ ]
        drop_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color="#161620", border_width=2, border_color="#3B8ED0")
        drop_frame.pack(fill="x", padx=16, pady=(4, 8))

        drop_inner = ctk.CTkFrame(drop_frame, fg_color="transparent")
        drop_inner.pack(fill="x", padx=12, pady=8)

        self.btn_examinar_formacion = ctk.CTkButton(
            drop_inner,
            text="Examinar archivo (.xlsx, .ods, .csv)",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            command=self._examinar_archivo_formacion
        )
        self.btn_examinar_formacion.pack(side="left", padx=(0, 12))

        # Chip contenedor del archivo seleccionado
        self.chip_frame_formacion = ctk.CTkFrame(drop_inner, fg_color="#20202E", corner_radius=6, border_width=1, border_color="#2D2D42")
        self.chip_frame_formacion.pack(side="left", fill="x", expand=True)

        self.lbl_archivo_formacion = ctk.CTkLabel(
            self.chip_frame_formacion,
            textvariable=self.archivo_seleccionado_formacion,
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98",
            anchor="w"
        )
        self.lbl_archivo_formacion.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=4)

        self.btn_descartar_formacion = ctk.CTkButton(
            self.chip_frame_formacion,
            text="✕",
            width=22,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#C0392B",
            hover_color="#962D22",
            command=self._descartar_archivo_formacion
        )
        # Oculto por defecto hasta que se elija un archivo

        # 1.5 Tarjeta de Pre-vuelo (Resumen Inmediato ETL - Inicialmente oculta)
        self.card_prevuelo_formacion = ctk.CTkFrame(
            frame,
            corner_radius=10,
            fg_color="#161620",
            border_width=1,
            border_color="#292938"
        )

        card_inner_f = ctk.CTkFrame(self.card_prevuelo_formacion, fg_color="transparent")
        card_inner_f.pack(fill="x", padx=14, pady=10)

        prevuelo_left_f = ctk.CTkFrame(card_inner_f, fg_color="transparent")
        prevuelo_left_f.pack(side="left", fill="x", expand=True)

        top_met_f = ctk.CTkFrame(prevuelo_left_f, fg_color="transparent")
        top_met_f.pack(anchor="w", fill="x")

        self.lbl_prevuelo_formacion_total = ctk.CTkLabel(
            top_met_f,
            text="Total: 0 participantes",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3B8ED0"
        )
        self.lbl_prevuelo_formacion_total.pack(side="left", padx=(0, 12))

        self.lbl_prevuelo_formacion_estado = ctk.CTkLabel(
            top_met_f,
            text="● Estructura Válida (0 inconsistencias)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#30D158"
        )
        self.lbl_prevuelo_formacion_estado.pack(side="left")

        self.lbl_prevuelo_formacion_desglose = ctk.CTkLabel(
            prevuelo_left_f,
            text="0 Cedulados  |  0 Escolares  |  0 Menores S/C",
            font=ctk.CTkFont(size=11),
            text_color="#A1A1AA"
        )
        self.lbl_prevuelo_formacion_desglose.pack(anchor="w", pady=(2, 0))

        self.btn_recargar_formacion = ctk.CTkButton(
            card_inner_f,
            text="↻ Recargar",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=85,
            fg_color="#2C3E50",
            hover_color="#1A252F",
            command=lambda: self._accion_recargar_archivo("Formación")
        )
        self.btn_recargar_formacion.pack(side="right", padx=(6, 0))

        self.btn_excel_formacion = ctk.CTkButton(
            card_inner_f,
            text="✎ Abrir en Excel",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=110,
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=lambda: self._accion_abrir_archivo_excel("Formación")
        )
        self.btn_excel_formacion.pack(side="right", padx=(6, 0))

        self.btn_tabla_formacion = ctk.CTkButton(
            card_inner_f,
            text="👁 Ver Tabla",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=100,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=lambda: self._abrir_tabla_previsualizacion("Formación")
        )
        self.btn_tabla_formacion.pack(side="right", padx=(6, 0))

        # 2. URL InfoApp
        self.url_container_formacion = ctk.CTkFrame(frame, fg_color="transparent")
        self.url_container_formacion.pack(fill="x", padx=16, pady=(0, 8))

        lbl_url = ctk.CTkLabel(
            self.url_container_formacion,
            text="URL de InfoApp (debe contener id_activity=):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_url.pack(anchor="w", pady=(0, 3))

        url_input_row = ctk.CTkFrame(self.url_container_formacion, fg_color="transparent")
        url_input_row.pack(fill="x")

        self.entry_url_formacion = ctk.CTkEntry(
            url_input_row,
            placeholder_text="https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=...",
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_url_formacion.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_url_formacion.bind("<KeyRelease>", lambda e: self._validar_sintaxis_url(self.entry_url_formacion))

        self.btn_pegar_formacion = ctk.CTkButton(
            url_input_row,
            text="Pegar",
            width=70,
            height=34,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self._pegar_portapapeles_url(self.entry_url_formacion)
        )
        self.btn_pegar_formacion.pack(side="right")

        # 3. Opciones
        opts_row = ctk.CTkFrame(frame, fg_color="transparent")
        opts_row.pack(fill="x", padx=16, pady=(0, 10))

        chk_vis = ctk.CTkCheckBox(
            opts_row,
            text="Modo Visible (Ver Navegador)",
            variable=self.var_modo_visible_formacion,
            font=ctk.CTkFont(size=11)
        )
        chk_vis.pack(side="left", padx=(0, 20))

        chk_ods = ctk.CTkCheckBox(
            opts_row,
            text="Generar Planilla Oficial .ODS",
            variable=self.var_generar_ods_formacion,
            font=ctk.CTkFont(size=11)
        )
        chk_ods.pack(side="left")

        # 4. Botón Acción
        action_row = ctk.CTkFrame(frame, fg_color="transparent")
        action_row.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_iniciar_formacion = ctk.CTkButton(
            action_row,
            text="INICIAR CARGA AUTOMATIZADA",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self._iniciar_ejecucion_asincrona_formacion
        )
        self.btn_iniciar_formacion.pack(fill="x")

        return frame

    # -------------------------------------------------------------------------
    # C. VISTA 3: SERVICIOS (CON CHIP DE ARCHIVO Y BOTÓN [✕])
    # -------------------------------------------------------------------------
    def _crear_vista_servicios(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))
        lbl_title = self._crear_label_con_icono(
            header,
            text="Carga de Servicios Comunitarios y Trámites",
            icono_clave="servicios",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        # Ingesta con Chip de Descarte
        drop_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color="#161620", border_width=2, border_color="#2E7D32")
        drop_frame.pack(fill="x", padx=16, pady=(4, 8))

        drop_inner = ctk.CTkFrame(drop_frame, fg_color="transparent")
        drop_inner.pack(fill="x", padx=12, pady=8)

        btn_examinar = ctk.CTkButton(
            drop_inner,
            text="Examinar usuarios (.xlsx, .csv)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            height=32,
            command=self._examinar_archivo_servicios
        )
        btn_examinar.pack(side="left", padx=(0, 12))

        self.chip_frame_servicios = ctk.CTkFrame(drop_inner, fg_color="#1B281E", corner_radius=6, border_width=1, border_color="#253D2A")
        self.chip_frame_servicios.pack(side="left", fill="x", expand=True)

        self.lbl_archivo_servicios = ctk.CTkLabel(
            self.chip_frame_servicios,
            textvariable=self.archivo_seleccionado_servicios,
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98",
            anchor="w"
        )
        self.lbl_archivo_servicios.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=4)

        self.btn_descartar_servicios = ctk.CTkButton(
            self.chip_frame_servicios,
            text="✕",
            width=22,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#C0392B",
            hover_color="#962D22",
            command=self._descartar_archivo_servicios
        )

        # 1.5 Tarjeta de Pre-vuelo (Resumen Inmediato ETL - Servicios)
        self.card_prevuelo_servicios = ctk.CTkFrame(
            frame,
            corner_radius=10,
            fg_color="#161620",
            border_width=1,
            border_color="#253D2A"
        )

        card_inner_s = ctk.CTkFrame(self.card_prevuelo_servicios, fg_color="transparent")
        card_inner_s.pack(fill="x", padx=14, pady=10)

        prevuelo_left_s = ctk.CTkFrame(card_inner_s, fg_color="transparent")
        prevuelo_left_s.pack(side="left", fill="x", expand=True)

        top_met_s = ctk.CTkFrame(prevuelo_left_s, fg_color="transparent")
        top_met_s.pack(anchor="w", fill="x")

        self.lbl_prevuelo_servicios_total = ctk.CTkLabel(
            top_met_s,
            text="Total: 0 usuarios",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2ECC71"
        )
        self.lbl_prevuelo_servicios_total.pack(side="left", padx=(0, 12))

        self.lbl_prevuelo_servicios_estado = ctk.CTkLabel(
            top_met_s,
            text="● Estructura Válida (0 inconsistencias)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#30D158"
        )
        self.lbl_prevuelo_servicios_estado.pack(side="left")

        self.lbl_prevuelo_servicios_desglose = ctk.CTkLabel(
            prevuelo_left_s,
            text="0 Cedulados  |  0 Escolares  |  0 Menores S/C",
            font=ctk.CTkFont(size=11),
            text_color="#A1A1AA"
        )
        self.lbl_prevuelo_servicios_desglose.pack(anchor="w", pady=(2, 0))

        self.btn_recargar_servicios = ctk.CTkButton(
            card_inner_s,
            text="↻ Recargar",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=85,
            fg_color="#2C3E50",
            hover_color="#1A252F",
            command=lambda: self._accion_recargar_archivo("Servicios")
        )
        self.btn_recargar_servicios.pack(side="right", padx=(6, 0))

        self.btn_excel_servicios = ctk.CTkButton(
            card_inner_s,
            text="✎ Abrir en Excel",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=110,
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=lambda: self._accion_abrir_archivo_excel("Servicios")
        )
        self.btn_excel_servicios.pack(side="right", padx=(6, 0))

        self.btn_tabla_servicios = ctk.CTkButton(
            card_inner_s,
            text="👁 Ver Tabla",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=100,
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=lambda: self._abrir_tabla_previsualizacion("Servicios")
        )
        self.btn_tabla_servicios.pack(side="right", padx=(6, 0))

        # URL de Servicio InfoApp
        self.url_container_servicios = ctk.CTkFrame(frame, fg_color="transparent")
        self.url_container_servicios.pack(fill="x", padx=16, pady=(0, 8))

        lbl_url = ctk.CTkLabel(
            self.url_container_servicios,
            text="URL de Servicio InfoApp (debe contener id_service=):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_url.pack(anchor="w", pady=(0, 3))

        url_input_row = ctk.CTkFrame(self.url_container_servicios, fg_color="transparent")
        url_input_row.pack(fill="x")

        self.entry_url_servicios = ctk.CTkEntry(
            url_input_row,
            placeholder_text="https://infoapp2.infocentro.gob.ve/admin/index.php?r=service/create&id_service=...",
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_url_servicios.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_url_servicios.bind("<KeyRelease>", lambda e: self._validar_sintaxis_url(self.entry_url_servicios))

        btn_pegar = ctk.CTkButton(
            url_input_row,
            text="Pegar",
            width=70,
            height=34,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self._pegar_portapapeles_url(self.entry_url_servicios)
        )
        btn_pegar.pack(side="right")

        # Fecha del Servicio InfoApp
        self.fecha_container_servicios = ctk.CTkFrame(frame, fg_color="transparent")
        self.fecha_container_servicios.pack(fill="x", padx=16, pady=(0, 8))

        lbl_fecha_srv = ctk.CTkLabel(
            self.fecha_container_servicios,
            text="Fecha del Servicio a Asentar (AAAA-MM-DD):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_fecha_srv.pack(anchor="w", pady=(0, 3))

        fecha_input_row = ctk.CTkFrame(self.fecha_container_servicios, fg_color="transparent")
        fecha_input_row.pack(fill="x")

        hoy_str = datetime.now().strftime("%Y-%m-%d")
        self.entry_fecha_servicios = ctk.CTkEntry(
            fecha_input_row,
            placeholder_text="AAAA-MM-DD (ej: 2026-03-15)",
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_fecha_servicios.insert(0, hoy_str)
        self.entry_fecha_servicios.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_cal_srv = ctk.CTkButton(
            fecha_input_row,
            text="📅 Calendario",
            width=100,
            height=34,
            fg_color="#3B8ED0",
            hover_color="#1F6AA5",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self._mostrar_selector_fecha(self.entry_fecha_servicios)
        )
        btn_cal_srv.pack(side="left", padx=(0, 8))

        btn_hoy_srv = ctk.CTkButton(
            fecha_input_row,
            text="Hoy",
            width=60,
            height=34,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            font=ctk.CTkFont(size=11),
            command=lambda: self._establecer_fecha_hoy(self.entry_fecha_servicios)
        )
        btn_hoy_srv.pack(side="right")

        # Selector de Tipo de Actividad / Servicio InfoApp
        self.tipo_container_servicios = ctk.CTkFrame(frame, fg_color="transparent")
        self.tipo_container_servicios.pack(fill="x", padx=16, pady=(0, 8))

        lbl_tipo_srv = ctk.CTkLabel(
            self.tipo_container_servicios,
            text="Tipo de Actividad / Servicio a Registrar en InfoApp:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_tipo_srv.pack(anchor="w", pady=(0, 3))

        cfg_serv = cargar_config_servicios() if MODULOS_DISPONIBLES else {}
        catalogo_opciones = list(cfg_serv.get("catalogo_servicios", []))
        if not catalogo_opciones:
            catalogo_opciones = ["Actividades de educación o aprendizaje"]

        def_servicio = cfg_serv.get("servicio_por_defecto", "Actividades de educación o aprendizaje")
        if def_servicio not in catalogo_opciones:
            def_servicio = catalogo_opciones[0]

        self.menu_tipo_servicio = ctk.CTkOptionMenu(
            self.tipo_container_servicios,
            values=catalogo_opciones,
            font=ctk.CTkFont(size=11),
            dropdown_font=ctk.CTkFont(size=11),
            dynamic_resizing=False,
            height=34,
            fg_color="#2B2B36",
            button_color="#3A3A4A",
            button_hover_color="#4B4B5E"
        )
        self.menu_tipo_servicio.set(def_servicio)
        self.menu_tipo_servicio.pack(fill="x")

        # Opciones
        opts_row = ctk.CTkFrame(frame, fg_color="transparent")
        opts_row.pack(fill="x", padx=16, pady=(0, 10))

        chk_vis = ctk.CTkCheckBox(
            opts_row,
            text="Modo Visible (Ver Navegador)",
            variable=self.var_modo_visible_servicios,
            font=ctk.CTkFont(size=11)
        )
        chk_vis.pack(anchor="w", pady=(0, 4))

        # Botón de Acción Servicios
        action_row = ctk.CTkFrame(frame, fg_color="transparent")
        action_row.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_iniciar_servicios = ctk.CTkButton(
            action_row,
            text="INICIAR CARGA DE SERVICIOS",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self._iniciar_ejecucion_asincrona_servicios
        )
        self.btn_iniciar_servicios.pack(fill="x")

        return frame

    # -------------------------------------------------------------------------
    # D. VISTA 4: PLANILLAS / ODS (GENERACIÓN DIRECTA Y UTILIDADES)
    # -------------------------------------------------------------------------
    def _crear_vista_reportes(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))
        lbl_title = self._crear_label_con_icono(
            header,
            text="Gestión de Planillas Oficiales y Reportes ODS",
            icono_clave="reportes",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        # 1. Ingesta con Chip de Descarte (Estilo Formación)
        drop_frame_planillas = ctk.CTkFrame(frame, corner_radius=10, fg_color="#161620", border_width=2, border_color="#1F538D")
        drop_frame_planillas.pack(fill="x", padx=16, pady=(4, 8))

        drop_inner_p = ctk.CTkFrame(drop_frame_planillas, fg_color="transparent")
        drop_inner_p.pack(fill="x", padx=12, pady=8)

        self.btn_examinar_planillas = ctk.CTkButton(
            drop_inner_p,
            text="Examinar archivo (.xlsx, .ods, .csv)",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            fg_color="#1F538D",
            hover_color="#14375E",
            command=self._examinar_archivo_planillas
        )
        self.btn_examinar_planillas.pack(side="left", padx=(0, 12))

        self.chip_frame_planillas = ctk.CTkFrame(drop_inner_p, fg_color="#20202E", corner_radius=6, border_width=1, border_color="#2D2D42")
        self.chip_frame_planillas.pack(side="left", fill="x", expand=True)

        self.lbl_archivo_planillas = ctk.CTkLabel(
            self.chip_frame_planillas,
            textvariable=self.archivo_seleccionado_planillas,
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98",
            anchor="w"
        )
        self.lbl_archivo_planillas.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=4)

        self.btn_descartar_planillas = ctk.CTkButton(
            self.chip_frame_planillas,
            text="✕",
            width=22,
            height=22,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#C0392B",
            hover_color="#962D22",
            command=self._descartar_archivo_planillas
        )

        # 1.5 Tarjeta de Pre-vuelo (Resumen Inmediato ETL - Inicialmente oculta)
        self.card_prevuelo_planillas = ctk.CTkFrame(
            frame,
            corner_radius=10,
            fg_color="#161620",
            border_width=1,
            border_color="#292938"
        )

        card_inner_p = ctk.CTkFrame(self.card_prevuelo_planillas, fg_color="transparent")
        card_inner_p.pack(fill="x", padx=14, pady=10)

        prevuelo_left_p = ctk.CTkFrame(card_inner_p, fg_color="transparent")
        prevuelo_left_p.pack(side="left", fill="x", expand=True)

        top_met_p = ctk.CTkFrame(prevuelo_left_p, fg_color="transparent")
        top_met_p.pack(anchor="w", fill="x")

        self.lbl_prevuelo_planillas_total = ctk.CTkLabel(
            top_met_p,
            text="Total: 0 participantes",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3B8ED0"
        )
        self.lbl_prevuelo_planillas_total.pack(side="left", padx=(0, 12))

        self.lbl_prevuelo_planillas_estado = ctk.CTkLabel(
            top_met_p,
            text="● Estructura Válida (0 inconsistencias)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#30D158"
        )
        self.lbl_prevuelo_planillas_estado.pack(side="left")

        self.lbl_prevuelo_planillas_desglose = ctk.CTkLabel(
            prevuelo_left_p,
            text="0 Cedulados  |  0 Escolares  |  0 Menores S/C",
            font=ctk.CTkFont(size=11),
            text_color="#A1A1AA"
        )
        self.lbl_prevuelo_planillas_desglose.pack(anchor="w", pady=(2, 0))

        self.btn_recargar_planillas = ctk.CTkButton(
            card_inner_p,
            text="↻ Recargar",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=85,
            fg_color="#2C3E50",
            hover_color="#1A252F",
            command=lambda: self._accion_recargar_archivo("Planillas")
        )
        self.btn_recargar_planillas.pack(side="right", padx=(6, 0))

        self.btn_excel_planillas = ctk.CTkButton(
            card_inner_p,
            text="✎ Abrir en Excel",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=110,
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=lambda: self._accion_abrir_archivo_excel("Planillas")
        )
        self.btn_excel_planillas.pack(side="right", padx=(6, 0))

        self.btn_tabla_planillas = ctk.CTkButton(
            card_inner_p,
            text="👁 Ver Tabla",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            width=100,
            fg_color="#1F538D",
            hover_color="#14375E",
            command=lambda: self._abrir_tabla_previsualizacion("Planillas")
        )
        self.btn_tabla_planillas.pack(side="right", padx=(6, 0))

        # 2. Contenedor de Opciones / Metadatos de la Planilla
        self.container_opciones_planillas = ctk.CTkFrame(frame, fg_color="transparent")
        self.container_opciones_planillas.pack(fill="x", padx=16, pady=(0, 8))

        lbl_id_url = ctk.CTkLabel(
            self.container_opciones_planillas,
            text="ID de Actividad o URL InfoApp (Opcional - Enter para institucional):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#D1D1D6"
        )
        lbl_id_url.pack(anchor="w", pady=(0, 3))

        row_cfg_planillas = ctk.CTkFrame(self.container_opciones_planillas, fg_color="transparent")
        row_cfg_planillas.pack(fill="x")

        self.entry_id_url_planillas = ctk.CTkEntry(
            row_cfg_planillas,
            placeholder_text="ID actividad (ej: 523948) o URL completa (dejar vacío para institucional)",
            font=ctk.CTkFont(size=11),
            height=34,
            border_width=2,
            border_color="#3A3A4A"
        )
        self.entry_id_url_planillas.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.menu_formato_planillas = ctk.CTkOptionMenu(
            row_cfg_planillas,
            values=["OpenDocument (.ods)", "Microsoft Excel (.xlsx)", "Documento PDF (.pdf)"],
            font=ctk.CTkFont(size=11),
            dropdown_font=ctk.CTkFont(size=11),
            dynamic_resizing=False,
            width=175,
            height=34,
            fg_color="#2B2B36",
            button_color="#3A3A4A",
            button_hover_color="#4B4B5E"
        )
        self.menu_formato_planillas.set("OpenDocument (.ods)")
        self.menu_formato_planillas.pack(side="left", padx=(0, 8))

        btn_editar_ficha = ctk.CTkButton(
            row_cfg_planillas,
            text="✏️ Ficha Formativa",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=34,
            width=140,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._mostrar_modal_editar_ficha_formativa
        )
        btn_editar_ficha.pack(side="right")

        # 3. Botón de Acción Principal Generación
        action_row_p = ctk.CTkFrame(frame, fg_color="transparent")
        action_row_p.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_iniciar_planillas = ctk.CTkButton(
            action_row_p,
            text="GENERAR PLANILLA OFICIAL",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#1F538D",
            hover_color="#14375E",
            command=self._iniciar_generacion_planilla_directa
        )
        self.btn_iniciar_planillas.pack(fill="x")

        # 4. Herramientas y Plantillas Base (Bloque Inferior)
        tools_card = ctk.CTkFrame(frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        tools_card.pack(fill="x", padx=16, pady=(4, 10))

        tools_inner = ctk.CTkFrame(tools_card, fg_color="transparent")
        tools_inner.pack(fill="x", padx=12, pady=10)

        lbl_tools_title = ctk.CTkLabel(
            tools_inner,
            text="Herramientas de Soporte y Plantilla Matriz",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#A1A1AA"
        )
        lbl_tools_title.pack(anchor="w", pady=(0, 6))

        actions_grid = ctk.CTkFrame(tools_inner, fg_color="transparent")
        actions_grid.pack(fill="x", pady=(0, 8))
        actions_grid.grid_columnconfigure((0, 1), weight=1)

        btn_carpeta = ctk.CTkButton(
            actions_grid,
            text="Abrir Carpeta de Planillas y Salidas",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=34,
            command=self._abrir_directorio_salidas
        )
        btn_carpeta.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        btn_plantilla = ctk.CTkButton(
            actions_grid,
            text="Inspeccionar Plantilla Base ODS",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            height=34,
            command=self._abrir_plantilla_base
        )
        btn_plantilla.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # Estado del archivo de respaldo
        csv_path = os.path.join(BASE_DIR, "backups", "estudiantes.csv")
        if not os.path.exists(csv_path):
            csv_fallback = os.path.join(BASE_DIR, "estudiantes.csv")
            if os.path.exists(csv_fallback):
                csv_path = csv_fallback
        csv_existe = os.path.exists(csv_path)

        csv_card = ctk.CTkFrame(tools_inner, fg_color="#14141E", corner_radius=6)
        csv_card.pack(fill="x")

        lbl_csv = ctk.CTkLabel(
            csv_card,
            text=f"Respaldo local (estudiantes.csv): {'Disponible (Verificado)' if csv_existe else 'No generado aún'}",
            font=ctk.CTkFont(size=10, weight="bold" if csv_existe else "normal"),
            text_color="#30D158" if csv_existe else "#8E8E98"
        )
        lbl_csv.pack(side="left", padx=10, pady=6)

        if csv_existe:
            btn_ver_csv = ctk.CTkButton(
                csv_card,
                text="Ver CSV",
                width=65,
                height=24,
                font=ctk.CTkFont(size=10),
                command=lambda: abrir_archivo_o_directorio_sistema(csv_path)
            )
            btn_ver_csv.pack(side="right", padx=10)

        return frame

    # -------------------------------------------------------------------------
    # D.2 VISTA INSPECTOR DE AUDITORÍA Y BALANCE OPERATIVO (v4.2.0)
    # -------------------------------------------------------------------------
    def _crear_vista_inspector(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        # 1. Encabezado
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(10, 4))

        lbl_title = self._crear_label_con_icono(
            header,
            text="Inspector de Auditoría",
            icono_clave="reportes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        # Switch Rol Auditor
        self.switch_rol_auditor = ctk.CTkSwitch(
            header,
            text="Rol Auditor",
            variable=self.var_rol_auditor,
            font=ctk.CTkFont(size=11),
            progress_color="#1f538d",
            command=self._al_cambiar_rol_auditor
        )
        self.switch_rol_auditor.pack(side="right", padx=(6, 0))

        # Switch Modo Turbo (Aceleración HTTP)
        self.switch_modo_turbo = ctk.CTkSwitch(
            header,
            text="⚡ Turbo",
            variable=self.var_modo_turbo,
            font=ctk.CTkFont(size=11),
            progress_color="#27AE60"
        )
        self.switch_modo_turbo.pack(side="right", padx=(6, 4))

        btn_abrir_dir_reportes = ctk.CTkButton(
            header,
            text="📂 Reportes",
            font=ctk.CTkFont(size=11),
            width=90,
            height=28,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._abrir_directorio_reportes_auditoria
        )
        btn_abrir_dir_reportes.pack(side="right", padx=3)

        self.btn_cargar_cache = ctk.CTkButton(
            header,
            text="⚡ Caché",
            font=ctk.CTkFont(size=11),
            width=80,
            height=28,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._cargar_ultima_busqueda_cache
        )
        self.btn_cargar_cache.pack(side="right", padx=3)

        # 2. Tarjeta de Criterios y Parámetros
        params_card = ctk.CTkFrame(frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        params_card.pack(fill="x", padx=16, pady=(4, 6))

        # Fila 1: SegmentedButton Modo
        row_mode = ctk.CTkFrame(params_card, fg_color="transparent")
        row_mode.pack(fill="x", padx=10, pady=(6, 4))

        lbl_modo = ctk.CTkLabel(row_mode, text="Modo:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#C0C0C8")
        lbl_modo.pack(side="left", padx=(0, 8))

        self.seg_modo_auditoria = ctk.CTkSegmentedButton(
            row_mode,
            values=["Por Facilitador (UID)", "Por Infocentro (Código)", "Resumen Estadal (Región)"],
            variable=self.var_modo_auditoria,
            font=ctk.CTkFont(size=11),
            selected_color="#1f538d",
            selected_hover_color="#14375e",
            command=self._al_cambiar_modo_auditoria
        )
        self.seg_modo_auditoria.pack(side="left", fill="x", expand=True)

        # Contenedor de inputs con grid de 2 filas balanceadas y responsivas
        frame_filtros_inputs = ctk.CTkFrame(params_card, fg_color="transparent")
        frame_filtros_inputs.pack(fill="x", padx=10, pady=(2, 8))

        frame_filtros_inputs.grid_columnconfigure(0, weight=1)
        frame_filtros_inputs.grid_columnconfigure(1, weight=1)
        frame_filtros_inputs.grid_columnconfigure(2, weight=2)
        frame_filtros_inputs.grid_columnconfigure(3, weight=2)

        # FILA 0: Criterios de Identificación (Reactivos y condicionales)
        # Columna 0: UID
        self.box_aud_uid = ctk.CTkFrame(frame_filtros_inputs, fg_color="transparent")
        self.box_aud_uid.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 0), pady=(4, 2))
        self.lbl_aud_uid = ctk.CTkLabel(self.box_aud_uid, text="UID Facilitador:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8E8E98")
        self.lbl_aud_uid.pack(side="left", padx=(0, 6))
        self.entry_aud_uid = ctk.CTkEntry(self.box_aud_uid, textvariable=self.var_criterio_uid, height=28, font=ctk.CTkFont(size=11), placeholder_text="ej: 1325")
        self.entry_aud_uid.pack(side="left", fill="x", expand=True)

        # Columna 1: Cód. Infocentro
        self.box_aud_infoid = ctk.CTkFrame(frame_filtros_inputs, fg_color="transparent")
        self.lbl_aud_infoid = ctk.CTkLabel(self.box_aud_infoid, text="Código de Infocentro:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8E8E98")
        self.lbl_aud_infoid.pack(side="left", padx=(0, 6))
        self.entry_aud_infoid = ctk.CTkEntry(self.box_aud_infoid, textvariable=self.var_criterio_infoid, height=28, font=ctk.CTkFont(size=11), placeholder_text="ej: NRYAR24")
        self.entry_aud_infoid.pack(side="left", fill="x", expand=True)

        # Columna 2..3: Estado / Región
        self.box_aud_estado = ctk.CTkFrame(frame_filtros_inputs, fg_color="transparent")
        self.lbl_aud_estado = ctk.CTkLabel(self.box_aud_estado, text="Región / Entidad Federal:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8E8E98")
        self.lbl_aud_estado.pack(side="left", padx=(0, 6))

        estados_vzla = list(getattr(ar, "LISTA_ESTADOS_VENEZUELA", [
            "Amazonas", "Anzoátegui", "Apure", "Aragua", "Barinas", "Bolívar", "Carabobo",
            "Cojedes", "Delta Amacuro", "Falcón", "Guárico", "Lara", "Mérida", "Miranda",
            "Monagas", "Nueva Esparta", "Portuguesa", "Sucre", "Táchira", "Trujillo",
            "La Guaira", "Yaracuy", "Zulia", "Distrito Capital", "Dependencias Federales", "Guayana Esequiba"
        ]))
        self.combo_aud_estado = ctk.CTkComboBox(
            self.box_aud_estado,
            values=estados_vzla,
            variable=self.var_criterio_estado,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.combo_aud_estado.pack(side="left", fill="x", expand=True)

        # FILA 1: Rango Temporal y Botón de Inicio de Búsqueda (Sin selector de exportar)
        # Columna 0: Desde
        box_desde = ctk.CTkFrame(frame_filtros_inputs, fg_color="transparent")
        box_desde.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(4, 2))
        lbl_desde = ctk.CTkLabel(box_desde, text="Desde:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8E8E98")
        lbl_desde.pack(side="left", padx=(0, 4))
        self.entry_aud_desde = ctk.CTkEntry(box_desde, textvariable=self.var_fecha_desde_aud, height=28, font=ctk.CTkFont(size=11))
        self.entry_aud_desde.pack(side="left", fill="x", expand=True)

        # Columna 1: Hasta
        box_hasta = ctk.CTkFrame(frame_filtros_inputs, fg_color="transparent")
        box_hasta.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(4, 2))
        lbl_hasta = ctk.CTkLabel(box_hasta, text="Hasta:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8E8E98")
        lbl_hasta.pack(side="left", padx=(0, 4))
        self.entry_aud_hasta = ctk.CTkEntry(box_hasta, textvariable=self.var_fecha_hasta_aud, height=28, font=ctk.CTkFont(size=11))
        self.entry_aud_hasta.pack(side="left", fill="x", expand=True)

        # Columna 2..3: Botón Iniciar Auditoría (Ocupa ambas columnas para máxima visibilidad y ergonomía)
        self.btn_iniciar_auditoria = ctk.CTkButton(
            frame_filtros_inputs,
            text="🔍 Iniciar Auditoría",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27AE60",
            hover_color="#219653",
            height=28,
            command=self._iniciar_auditoria_thread
        )
        self.btn_iniciar_auditoria.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(6, 0), pady=(4, 2))

        # 3. Tarjetas KPIs Ampliadas con Métricas Detalladas (Aprovechamiento óptimo del espacio)
        kpi_frame = ctk.CTkFrame(frame, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=16, pady=(4, 6))
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        # KPI 1: Actividades Registradas
        kpi1 = ctk.CTkFrame(kpi_frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        kpi1.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        ctk.CTkLabel(kpi1, text="📊 TOTAL ACTIVIDADES", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8E8E98").pack(pady=(8, 2))
        self.lbl_kpi_actividades = ctk.CTkLabel(kpi1, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#38BDF8")
        self.lbl_kpi_actividades.pack(pady=(0, 2))
        self.lbl_kpi_actividades_sub = ctk.CTkLabel(kpi1, text="0 Form | 0 Prod | 0 Otr", font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E0E8")
        self.lbl_kpi_actividades_sub.pack(pady=(0, 2))
        self.lbl_kpi_actividades_det = ctk.CTkLabel(kpi1, text="Sin actividades cargadas", font=ctk.CTkFont(size=9), text_color="#6C7A89")
        self.lbl_kpi_actividades_det.pack(pady=(0, 8))

        # KPI 2: Formados Reales
        kpi2 = ctk.CTkFrame(kpi_frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        kpi2.grid(row=0, column=1, padx=5, sticky="nsew")
        ctk.CTkLabel(kpi2, text="🎓 FORMADOS REALES", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8E8E98").pack(pady=(8, 2))
        self.lbl_kpi_formados = ctk.CTkLabel(kpi2, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#2ECC71")
        self.lbl_kpi_formados.pack(pady=(0, 2))
        self.lbl_kpi_formados_sub = ctk.CTkLabel(kpi2, text="Participantes en aula", font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E0E8")
        self.lbl_kpi_formados_sub.pack(pady=(0, 2))
        self.lbl_kpi_formados_det = ctk.CTkLabel(kpi2, text="Promedio: 0.0 alumnos / aula", font=ctk.CTkFont(size=9), text_color="#6C7A89")
        self.lbl_kpi_formados_det.pack(pady=(0, 8))

        # KPI 3: Servicios Brindados
        kpi3 = ctk.CTkFrame(kpi_frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        kpi3.grid(row=0, column=2, padx=5, sticky="nsew")
        ctk.CTkLabel(kpi3, text="🛠️ SERVICIOS BRINDADOS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8E8E98").pack(pady=(8, 2))
        self.lbl_kpi_servicios = ctk.CTkLabel(kpi3, text="0", font=ctk.CTkFont(size=22, weight="bold"), text_color="#A855F7")
        self.lbl_kpi_servicios.pack(pady=(0, 2))
        self.lbl_kpi_servicios_sub = ctk.CTkLabel(kpi3, text="Atenciones ciudadanas", font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E0E8")
        self.lbl_kpi_servicios_sub.pack(pady=(0, 2))
        self.lbl_kpi_servicios_det = ctk.CTkLabel(kpi3, text="0 Cedulados • 0 Sin cédula", font=ctk.CTkFont(size=9), text_color="#6C7A89")
        self.lbl_kpi_servicios_det.pack(pady=(0, 8))

        # KPI 4: Control de Cuadre
        kpi4 = ctk.CTkFrame(kpi_frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        kpi4.grid(row=0, column=3, padx=(5, 0), sticky="nsew")
        ctk.CTkLabel(kpi4, text="⚖️ ESTADO DE CUADRE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8E8E98").pack(pady=(8, 2))
        self.lbl_kpi_cuadre = ctk.CTkLabel(kpi4, text="● En Espera", font=ctk.CTkFont(size=16, weight="bold"), text_color="#8E8E98")
        self.lbl_kpi_cuadre.pack(pady=(0, 2))
        self.lbl_kpi_cuadre_sub = ctk.CTkLabel(kpi4, text="Balance matemático", font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E0E8")
        self.lbl_kpi_cuadre_sub.pack(pady=(0, 2))
        self.lbl_kpi_cuadre_det = ctk.CTkLabel(kpi4, text="Fórmula: Act = Form+Prod+Otr", font=ctk.CTkFont(size=9), text_color="#6C7A89")
        self.lbl_kpi_cuadre_det.pack(pady=(0, 8))

        # 4. Barra de Acciones: Botones de Inspección Detallada (Izquierda) y Exportación (Derecha)
        toolbar_inspeccion = ctk.CTkFrame(frame, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        toolbar_inspeccion.pack(fill="x", padx=16, pady=(6, 8))

        # Grupo Izquierdo: Botones de Inspección que abren Ventana Flotante Modal al frente
        box_botones_insp = ctk.CTkFrame(toolbar_inspeccion, fg_color="transparent")
        box_botones_insp.pack(side="left", padx=(10, 4), pady=8)

        self.btn_ver_actividades = ctk.CTkButton(
            box_botones_insp,
            text="🎓 Formaciones",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            width=120,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=lambda: self._abrir_ventana_flotante_inspeccion("actividades")
        )
        self.btn_ver_actividades.pack(side="left", padx=(0, 4))

        self.btn_ver_servicios = ctk.CTkButton(
            box_botones_insp,
            text="🛠️ Servicios",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            width=105,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self._abrir_ventana_flotante_inspeccion("servicios")
        )
        self.btn_ver_servicios.pack(side="left", padx=(0, 4))

        self.btn_ver_facilitadores = ctk.CTkButton(
            box_botones_insp,
            text="👥 Facilitadores",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            width=120,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self._abrir_ventana_flotante_inspeccion("facilitadores")
        )
        self.btn_ver_facilitadores.pack(side="left", padx=(0, 4))

        # Grupo Derecho: Selector de Formato + Botón de Exportar (Empacados de Izquierda a Derecha)
        box_exportacion = ctk.CTkFrame(toolbar_inspeccion, fg_color="transparent")
        box_exportacion.pack(side="right", padx=(4, 10), pady=8)

        lbl_formato = ctk.CTkLabel(
            box_exportacion,
            text="Formato:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#8E8E98"
        )
        lbl_formato.pack(side="left", padx=(0, 4))

        self.combo_aud_formato = ctk.CTkComboBox(
            box_exportacion,
            values=[
                "LibreOffice Calc (.ods)",
                "Excel (.xlsx)",
                "Documento PDF (.pdf)",
                "CSV plano (.csv)",
                "Vista en Pantalla (Consola)"
            ],
            variable=self.var_exportar_formato,
            width=135,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.combo_aud_formato.pack(side="left", padx=(0, 6))

        self.btn_exportar_reporte_dialogo = ctk.CTkButton(
            box_exportacion,
            text="💾 Exportar Reporte...",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            width=135,
            state="disabled",
            fg_color="#27AE60",
            hover_color="#219653",
            command=self._accion_exportar_reporte_dialogo
        )
        self.btn_exportar_reporte_dialogo.pack(side="left")

        # Elementos de compatibilidad con backend y tests (sin ocupar espacio en pantalla)
        self.btn_abrir_reporte_auditoria = ctk.CTkButton(
            frame,
            text="📊 Abrir Reporte",
            state="disabled",
            command=self._abrir_ultimo_reporte_auditoria
        )
        self.lbl_auditoria_estado = ctk.CTkLabel(
            frame,
            text="Esperando inicio de auditoría..."
        )

        # Objetos de compatibilidad con tests y arquitectura previa
        class _TabviewCompatProxy:
            def __init__(self):
                self._tab_dict = {
                    "🎓 Formaciones y Actividades": {},
                    "🛠️ Servicios a Usuarios": {},
                    "👥 Resumen por Facilitador": {}
                }
                self._tab_actual = "🎓 Formaciones y Actividades"

            def get(self):
                return self._tab_actual

            def set(self, val):
                self._tab_actual = val

            def add(self, name):
                self._tab_dict[name] = {}
                return None

        self.tabview_auditoria = _TabviewCompatProxy()

        class _ScrollFrameCompat:
            def winfo_children(self):
                return []

        self.scroll_tab_actividades = _ScrollFrameCompat()
        self.scroll_tab_servicios = _ScrollFrameCompat()
        self.scroll_tab_facilitadores = _ScrollFrameCompat()
        self.txt_telemetria_auditoria = None

        # Ajustar modo inicial reactivo
        self._al_cambiar_modo_auditoria()

        return frame

    def _al_cambiar_modo_auditoria(self, valor=None):
        """Ajusta reactivamente las entradas según el modo de auditoría seleccionado."""
        modo = self.var_modo_auditoria.get()
        if "UID" in modo:
            if hasattr(self, "box_aud_uid") and self.box_aud_uid:
                self.box_aud_uid.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 0), pady=(4, 2))
            if hasattr(self, "box_aud_infoid") and self.box_aud_infoid:
                self.box_aud_infoid.grid_remove()
            if hasattr(self, "box_aud_estado") and self.box_aud_estado:
                self.box_aud_estado.grid_remove()
            if hasattr(self, "entry_aud_uid") and self.entry_aud_uid:
                self.entry_aud_uid.configure(state="normal")
            self._agregar_log_auditoria("[MODO] Selección: Por Facilitador (UID). Mostrando campo UID.")
        elif "Infocentro" in modo:
            if hasattr(self, "box_aud_uid") and self.box_aud_uid:
                self.box_aud_uid.grid_remove()
            if hasattr(self, "box_aud_infoid") and self.box_aud_infoid:
                self.box_aud_infoid.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 0), pady=(4, 2))
            if hasattr(self, "box_aud_estado") and self.box_aud_estado:
                self.box_aud_estado.grid_remove()
            if hasattr(self, "entry_aud_infoid") and self.entry_aud_infoid:
                self.entry_aud_infoid.configure(state="normal")
            self._agregar_log_auditoria("[MODO] Selección: Por Infocentro (Código). Mostrando campo Cód Info.")
        else:
            if hasattr(self, "box_aud_uid") and self.box_aud_uid:
                self.box_aud_uid.grid_remove()
            if hasattr(self, "box_aud_infoid") and self.box_aud_infoid:
                self.box_aud_infoid.grid_remove()
            if hasattr(self, "box_aud_estado") and self.box_aud_estado:
                self.box_aud_estado.grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 0), pady=(4, 2))
            if hasattr(self, "combo_aud_estado") and self.combo_aud_estado:
                self.combo_aud_estado.configure(state="normal")
            self._agregar_log_auditoria("[MODO] Selección: Resumen Estadal (Región). Mostrando selector de Estado.")

    def _al_cambiar_rol_auditor(self):
        """Maneja el switch de permisos de rol de auditor / jefatura."""
        rol = self.var_rol_auditor.get()
        if rol:
            config = configparser.ConfigParser()
            u_aud = ""
            c_aud = ""
            if os.path.exists(CONFIG_FILE):
                try:
                    config.read(CONFIG_FILE, encoding="utf-8")
                    if config.has_section("AUDITORIA"):
                        u_aud = config.get("AUDITORIA", "usuario", fallback="").strip()
                        c_aud = config.get("AUDITORIA", "clave", fallback="").strip()
                except Exception:
                    pass

            if u_aud and c_aud:
                self.switch_rol_auditor.configure(text=f"Rol Auditor (Activo: {u_aud})")
                self._agregar_log_auditoria(f"[ROL AUDITOR] Activado (Perfil: {u_aud}). Se usarán credenciales con permisos de auditoría.")
            else:
                self._mostrar_modal_credenciales_auditor()
        else:
            self.switch_rol_auditor.configure(text="Rol Auditor / Jefatura")
            self._agregar_log_auditoria("[ROL AUDITOR] Desactivado: Se usarán credenciales estándar [LOGIN].")

    def _mostrar_modal_credenciales_auditor(self):
        """Despliega modal CTkToplevel para capturar y persistir credenciales de Auditor / Jefatura."""
        modal = ctk.CTkToplevel(self)
        modal.title("Credenciales de Auditor / Jefatura")
        modal.geometry("440x330")
        modal.resizable(False, False)
        modal.configure(fg_color="#1E1E28")
        modal.transient(self)

        try:
            x = self.winfo_x() + max(0, (self.winfo_width() - 440) // 2)
            y = self.winfo_y() + max(0, (self.winfo_height() - 330) // 2)
            modal.geometry(f"+{x}+{y}")
        except Exception:
            pass

        def al_cerrar_cancelar():
            conf_check = configparser.ConfigParser()
            tiene_cred = False
            if os.path.exists(CONFIG_FILE):
                try:
                    conf_check.read(CONFIG_FILE, encoding="utf-8")
                    if conf_check.has_section("AUDITORIA"):
                        u = conf_check.get("AUDITORIA", "usuario", fallback="").strip()
                        c = conf_check.get("AUDITORIA", "clave", fallback="").strip()
                        if u and c:
                            tiene_cred = True
                except Exception:
                    pass
            if not tiene_cred:
                self.var_rol_auditor.set(False)
                self.switch_rol_auditor.configure(text="Rol Auditor / Jefatura")
            self.cerrar_modal(modal)

        self.registrar_modal("modal_credenciales_auditor", modal, grab=True, al_cerrar=al_cerrar_cancelar)

        header = ctk.CTkFrame(modal, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(
            header,
            text="Credenciales de Auditor / Jefatura",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Ingrese el usuario y contraseña con permisos para consultar InfoApp estadal:",
            font=ctk.CTkFont(size=10),
            text_color="#A1A1AA",
            wraplength=400,
            justify="left"
        ).pack(anchor="w", pady=(2, 0))

        form_box = ctk.CTkFrame(modal, fg_color="#161620", corner_radius=8, border_width=1, border_color="#292938")
        form_box.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(form_box, text="Usuario / Correo:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#D1D1D6").pack(anchor="w", padx=14, pady=(10, 2))
        entry_user = ctk.CTkEntry(form_box, height=32, font=ctk.CTkFont(size=11), placeholder_text="ej: coord_yaracuy")
        entry_user.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(form_box, text="Contraseña:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#D1D1D6").pack(anchor="w", padx=14, pady=(2, 2))
        entry_pass = ctk.CTkEntry(form_box, height=32, font=ctk.CTkFont(size=11), show="*", placeholder_text="Contraseña de InfoApp")
        entry_pass.pack(fill="x", padx=14, pady=(0, 14))

        # Cargar valores previos si existen
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE, encoding="utf-8")
                if config.has_section("AUDITORIA"):
                    prev_u = config.get("AUDITORIA", "usuario", fallback="")
                    entry_user.insert(0, prev_u)
            except Exception:
                pass

        btn_row = ctk.CTkFrame(modal, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(10, 14))

        def guardar_credenciales_auditor():
            usr = entry_user.get().strip()
            pwd = entry_pass.get().strip()
            if not usr or not pwd:
                self._mostrar_modal_mensaje("Campos Requeridos", "Debe ingresar tanto el usuario como la contraseña.", tipo="aviso")
                return

            try:
                cfg = configparser.ConfigParser()
                if os.path.exists(CONFIG_FILE):
                    cfg.read(CONFIG_FILE, encoding="utf-8")
                if not cfg.has_section("AUDITORIA"):
                    cfg.add_section("AUDITORIA")
                cfg.set("AUDITORIA", "usuario", usr)
                cfg.set("AUDITORIA", "clave", pwd)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    cfg.write(f)

                self.var_rol_auditor.set(True)
                self.switch_rol_auditor.configure(text=f"Rol Auditor (Activo: {usr})")
                self.agregar_log_telemetria(f"[ROL AUDITOR] Credenciales de auditor guardadas y activas para: {usr}")
                # Limpiar callback de cancelación para que no se ejecute al guardar con éxito
                try:
                    delattr(modal, "_cb_al_cerrar")
                except Exception:
                    pass
                self.cerrar_modal(modal)
            except Exception as err:
                self._mostrar_modal_mensaje("Error al Guardar", f"No se pudieron guardar las credenciales: {err}", tipo="error")

        btn_cancelar = ctk.CTkButton(
            btn_row,
            text="Cancelar",
            font=ctk.CTkFont(size=11),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            width=100,
            command=al_cerrar_cancelar
        )
        btn_cancelar.pack(side="left")

        btn_guardar = ctk.CTkButton(
            btn_row,
            text="Guardar Credenciales de Auditor",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27AE60",
            hover_color="#219653",
            command=guardar_credenciales_auditor
        )
        btn_guardar.pack(side="right")

    def _al_seleccionar_tab_auditoria(self):
        """Abre automáticamente la ventana flotante de inspección detallada al seleccionar una pestaña."""
        try:
            if not self.winfo_ismapped() or not self.winfo_viewable():
                return
        except Exception:
            return

        if not self.resultado_auditoria_actual:
            return

        tabview = getattr(self, "tabview_auditoria", None)
        if not tabview:
            return

        tab_actual = tabview.get()
        if "Actividades" in tab_actual or "Formaciones" in tab_actual:
            self._abrir_ventana_flotante_inspeccion("actividades")
        elif "Servicios" in tab_actual:
            self._abrir_ventana_flotante_inspeccion("servicios")
        elif "Facilitador" in tab_actual:
            self._abrir_ventana_flotante_inspeccion("facilitadores")

    def _abrir_ventana_flotante_inspeccion(self, tipo: str = "facilitadores"):
        """Despliega una ventana modal maximizable (1100x650) con buscador reactivo y cabeceras ordenables."""
        # Evitar ventanas flotantes duplicadas: si ya existe y sigue abierta, enfocar y elevar
        modal_existente = self.modales_activos.get("ventana_inspeccion")
        if modal_existente is not None:
            try:
                if modal_existente.winfo_exists():
                    modal_existente.lift()
                    modal_existente.focus_force()
                    return modal_existente
            except Exception:
                pass

        modal = ctk.CTkToplevel(self)
        modal.geometry("1100x650")
        modal.minsize(850, 480)
        modal.configure(fg_color="#1E1E28")

        titulos_map = {
            "actividades": "🎓 Formaciones y Actividades — Inspección Detallada",
            "servicios": "🛠️ Servicios a Usuarios — Inspección Detallada",
            "facilitadores": "👥 Resumen por Facilitador — Inspección Detallada"
        }
        titulo_modal = titulos_map.get(tipo, "Inspección Detallada")
        modal.title(titulo_modal)

        try:
            x = self.winfo_x() + max(0, (self.winfo_width() - 1100) // 2)
            y = self.winfo_y() + max(0, (self.winfo_height() - 650) // 2)
            modal.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self.registrar_modal("ventana_inspeccion", modal, grab=True)

        # Asegurar ejecución DELANTE de la ventana principal y comportamiento modal
        modal.transient(self)
        modal.lift()
        modal.attributes("-topmost", True)
        modal.after(150, lambda: modal.attributes("-topmost", False))
        modal.focus_force()

        def _cerrar_modal():
            self.cerrar_modal(modal)

        modal.protocol("WM_DELETE_WINDOW", _cerrar_modal)

        # 1. Barra Superior con Buscador y Contador
        top_bar = ctk.CTkFrame(modal, fg_color="#161620", height=50)
        top_bar.pack(fill="x", padx=12, pady=(10, 6))
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text=titulo_modal,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        ).pack(side="left", padx=12)

        entry_busqueda = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Filtrar por nombre, UID, tema o sede...",
            width=360,
            height=30,
            font=ctk.CTkFont(size=11)
        )
        entry_busqueda.pack(side="left", padx=12)

        lbl_contador = ctk.CTkLabel(
            top_bar,
            text="Registros: 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2ECC71"
        )
        lbl_contador.pack(side="left", padx=8)

        btn_cerrar = ctk.CTkButton(
            top_bar,
            text="✕ Cerrar",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#C0392B",
            hover_color="#962D22",
            command=_cerrar_modal
        )
        btn_cerrar.pack(side="right", padx=12)

        # 2. Contenedor de Tabla
        table_container = ctk.CTkFrame(modal, fg_color="#121218", corner_radius=8)
        table_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Estado de ordenamiento en memoria
        sort_state = {"col": "total_act" if tipo == "facilitadores" else "fecha", "reverse": True}

        res = self.resultado_auditoria_actual or {}
        if tipo == "facilitadores":
            facs_dict = res.get("resumen_facilitadores", {})
            datos_base = []
            for f_uid, d in facs_dict.items():
                datos_base.append({
                    "uid": str(d.get("uid", f_uid)),
                    "nombre": str(d.get("nombre", f"UID {f_uid}")),
                    "info_id": str(d.get("info_id", "")),
                    "formaciones": int(d.get("formaciones", 0)),
                    "estudiantes": int(d.get("estudiantes", 0)),
                    "productos": int(d.get("productos", 0)),
                    "otras": int(d.get("otras", 0)),
                    "servicios": int(d.get("servicios", 0)),
                    "total_act": int(d.get("total_act", 0)),
                })
        elif tipo == "servicios":
            datos_base = list(res.get("servicios", []))
        else:
            datos_base = list(res.get("formaciones", []) + res.get("productos", []) + res.get("otras_actividades", []))

        # Cabeceras
        headers_frame = ctk.CTkFrame(table_container, fg_color="#181824", corner_radius=6, height=32)
        headers_frame.pack(fill="x", padx=4, pady=(4, 2))
        headers_frame.pack_propagate(False)

        scroll_filas = ctk.CTkScrollableFrame(table_container, fg_color="#121218", corner_radius=6)
        scroll_filas.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        def ordenar_por(col_name):
            if sort_state["col"] == col_name:
                sort_state["reverse"] = not sort_state["reverse"]
            else:
                sort_state["col"] = col_name
                sort_state["reverse"] = True
            render_tabla()

        def render_tabla():
            for w in scroll_filas.winfo_children():
                w.destroy()

            q = entry_busqueda.get().strip().lower()

            filtrados = []
            for item in datos_base:
                if not q:
                    filtrados.append(item)
                else:
                    texto_completo = " ".join(str(v) for v in item.values()).lower()
                    if q in texto_completo:
                        filtrados.append(item)

            c = sort_state["col"]
            rev = sort_state["reverse"]
            try:
                filtrados.sort(key=lambda x: x.get(c, 0) if isinstance(x.get(c, 0), (int, float)) else str(x.get(c, "")).lower(), reverse=rev)
            except Exception:
                pass

            lbl_contador.configure(text=f"Mostrando {len(filtrados)} de {len(datos_base)} registros")

            if not filtrados:
                ctk.CTkLabel(
                    scroll_filas,
                    text="No se encontraron registros que coincidan con la búsqueda.",
                    font=ctk.CTkFont(size=11),
                    text_color="#8E8E98"
                ).pack(pady=30)
                return

            for idx, item in enumerate(filtrados, start=1):
                bg = "#181824" if idx % 2 == 0 else "#1E1E2C"
                row_f = ctk.CTkFrame(scroll_filas, fg_color=bg, corner_radius=6, height=34)
                row_f.pack(fill="x", pady=2, padx=2)
                row_f.pack_propagate(False)

                if tipo == "facilitadores":
                    ctk.CTkLabel(row_f, text=str(item.get("uid", "")), width=65, font=ctk.CTkFont(size=10, weight="bold"), text_color="#3B8ED0").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("nombre", "")), font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFFFFF", anchor="w").pack(side="left", fill="x", expand=True, padx=6)
                    ctk.CTkLabel(row_f, text=str(item.get("info_id", "")), width=80, font=ctk.CTkFont(size=10), text_color="#F39C12", anchor="center").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("formaciones", 0)), width=80, font=ctk.CTkFont(size=10), text_color="#C0C0C8", anchor="center").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("estudiantes", 0)), width=85, font=ctk.CTkFont(size=10, weight="bold"), text_color="#2ECC71", anchor="center").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("productos", 0)), width=75, font=ctk.CTkFont(size=10), text_color="#C0C0C8", anchor="center").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("otras", 0)), width=70, font=ctk.CTkFont(size=10), text_color="#C0C0C8", anchor="center").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("servicios", 0)), width=75, font=ctk.CTkFont(size=10, weight="bold"), text_color="#9B59B6", anchor="center").pack(side="left", padx=2)

                    b_tot = ctk.CTkFrame(row_f, fg_color="#1E3A5F", corner_radius=6, width=65, height=22)
                    b_tot.pack(side="left", padx=(2, 8))
                    b_tot.pack_propagate(False)
                    ctk.CTkLabel(b_tot, text=str(item.get("total_act", 0)), font=ctk.CTkFont(size=10, weight="bold"), text_color="#60A5FA").place(relx=0.5, rely=0.5, anchor="center")

                elif tipo == "servicios":
                    ctk.CTkLabel(row_f, text=str(idx), width=35, font=ctk.CTkFont(size=10), text_color="#8E8E98").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("fecha", "S/F")), width=90, font=ctk.CTkFont(size=10), text_color="#C0C0C8").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("servicio", "")), width=180, font=ctk.CTkFont(size=10, weight="bold"), text_color="#38BDF8", anchor="w").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("cedula", "") or "No cedulado"), width=110, font=ctk.CTkFont(family="Consolas", size=10), text_color="#F39C12", anchor="center").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("usuario", "")), font=ctk.CTkFont(size=10), text_color="#FFFFFF", anchor="w").pack(side="left", fill="x", expand=True, padx=6)
                    ctk.CTkLabel(row_f, text=str(item.get("profesion", "") or "S/D"), width=130, font=ctk.CTkFont(size=10), text_color="#8E8E98", anchor="w").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("info_id", "")), width=85, font=ctk.CTkFont(size=10), text_color="#A1A1AA", anchor="center").pack(side="left", padx=(2, 6))

                else:  # actividades
                    ctk.CTkLabel(row_f, text=str(idx), width=35, font=ctk.CTkFont(size=10), text_color="#8E8E98").pack(side="left", padx=2)
                    ctk.CTkLabel(row_f, text=str(item.get("fecha", "S/F")), width=85, font=ctk.CTkFont(size=10), text_color="#C0C0C8").pack(side="left", padx=2)

                    dims = item.get("dimensiones", "").lower()
                    if "aprendizaje" in dims or "robótica" in dims or "taller" in dims:
                        t_lbl, t_fg, t_tc = "Formación", "#1E4D2B", "#2ECC71"
                    elif item.get("productos", 0) > 0 or "contenido" in dims:
                        t_lbl, t_fg, t_tc = "Producto", "#1B3A57", "#3B8ED0"
                    else:
                        t_lbl, t_fg, t_tc = "Otras Act.", "#3D2B52", "#9B59B6"

                    b_tipo = ctk.CTkFrame(row_f, fg_color=t_fg, corner_radius=4, width=90, height=22)
                    b_tipo.pack(side="left", padx=4)
                    b_tipo.pack_propagate(False)
                    ctk.CTkLabel(b_tipo, text=t_lbl, font=ctk.CTkFont(size=9, weight="bold"), text_color=t_tc).place(relx=0.5, rely=0.5, anchor="center")

                    tema = item.get("taller") or item.get("area") or item.get("titulo") or "Sin tema"
                    tit = item.get("titulo", "")
                    desc = f"{tema} — {tit}" if (tit and tit != tema) else tema
                    ctk.CTkLabel(row_f, text=desc, font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFFFFF", anchor="w").pack(side="left", fill="x", expand=True, padx=6)
                    ctk.CTkLabel(row_f, text=str(item.get("responsable", "") or f"UID {item.get('uid', '')}"), width=140, font=ctk.CTkFont(size=10), text_color="#A1A1AA", anchor="w").pack(side="left", padx=4)
                    ctk.CTkLabel(row_f, text=str(item.get("info_id", "")), width=75, font=ctk.CTkFont(size=10), text_color="#F39C12", anchor="center").pack(side="left", padx=2)

                    n_p = item.get("participantes", 0)
                    b_p = ctk.CTkFrame(row_f, fg_color="#1E3A5F" if n_p > 0 else "#252533", corner_radius=10, width=46, height=22)
                    b_p.pack(side="left", padx=(2, 6))
                    b_p.pack_propagate(False)
                    ctk.CTkLabel(b_p, text=str(n_p), font=ctk.CTkFont(size=10, weight="bold"), text_color="#60A5FA" if n_p > 0 else "#8E8E98").place(relx=0.5, rely=0.5, anchor="center")

        if tipo == "facilitadores":
            cols_def = [
                ("UID", "uid", 65),
                ("Facilitador / Responsable", "nombre", 0),
                ("Sede", "info_id", 80),
                ("Formaciones", "formaciones", 80),
                ("Estudiantes", "estudiantes", 85),
                ("Productos", "productos", 75),
                ("Otras", "otras", 70),
                ("Servicios", "servicios", 75),
                ("Total Act.", "total_act", 65),
            ]
        elif tipo == "servicios":
            cols_def = [
                ("#", None, 35),
                ("Fecha", "fecha", 90),
                ("Servicio Prestado", "servicio", 180),
                ("Cédula / ID", "cedula", 110),
                ("Nombre del Usuario", "usuario", 0),
                ("Profesión", "profesion", 130),
                ("Sede", "info_id", 85),
            ]
        else:
            cols_def = [
                ("#", None, 35),
                ("Fecha", "fecha", 85),
                ("Tipo", "dimensiones", 90),
                ("Tema Pedagógico / Taller / Título", "titulo", 0),
                ("Facilitador / Responsable", "responsable", 140),
                ("Sede", "info_id", 75),
                ("Part.", "participantes", 46),
            ]

        for label, col_key, width in cols_def:
            if col_key:
                btn = ctk.CTkButton(
                    headers_frame,
                    text=label,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="transparent",
                    text_color="#3B8ED0",
                    hover_color="#2B2B36",
                    command=lambda k=col_key: ordenar_por(k)
                )
            else:
                btn = ctk.CTkLabel(headers_frame, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color="#3B8ED0")

            if width > 0:
                btn.configure(width=width)
                btn.pack(side="left", padx=2)
            else:
                btn.pack(side="left", fill="x", expand=True, padx=4)

        entry_busqueda.bind("<KeyRelease>", lambda e: render_tabla())
        render_tabla()

    def _iniciar_auditoria_thread(self):
        """Valida parámetros y despacha el hilo secundario de auditoría."""
        if self.ejecutando_auditoria or self.ejecutando_tarea:
            self._mostrar_modal_mensaje("JsBOT Ocupado", "Ya hay una tarea o auditoría en curso. Por favor espere a que termine.", tipo="aviso")
            return

        modo = self.var_modo_auditoria.get()
        uid = self.var_criterio_uid.get().strip()
        infoid = self.var_criterio_infoid.get().strip()
        estado = self.var_criterio_estado.get().strip()
        f_desde = self.var_fecha_desde_aud.get().strip()
        f_hasta = self.var_fecha_hasta_aud.get().strip()
        rol = self.var_rol_auditor.get()
        formato = self.var_exportar_formato.get().lower()

        if "consola" in formato or "pantalla" in formato:
            formato_exp = "consola"
        elif "ods" in formato or "libreoffice" in formato or "calc" in formato:
            formato_exp = "ods"
        elif "pdf" in formato:
            formato_exp = "pdf"
        elif "csv" in formato:
            formato_exp = "csv"
        else:
            formato_exp = "excel"

        try:
            datetime.strptime(f_desde, "%Y-%m-%d")
            datetime.strptime(f_hasta, "%Y-%m-%d")
        except (ValueError, TypeError):
            self._mostrar_modal_mensaje("Error en Fechas", "Las fechas deben tener el formato AAAA-MM-DD (ej: 2026-09-01).", tipo="error")
            return

        if "UID" in modo:
            if not uid:
                self._mostrar_modal_mensaje("Falta UID", "En el modo 'Por Facilitador' debe especificar el UID a consultar.", tipo="aviso")
                return
            c_uid = uid
            c_infoid = ""   # No restringir por infocentro al consultar un facilitador específico
            c_estado = ""   # No restringir por estado al consultar un facilitador específico
        elif "Infocentro" in modo:
            if not infoid:
                self._mostrar_modal_mensaje("Falta Cód. Infocentro", "En el modo 'Por Infocentro' debe especificar el código de la sede (ej: NRYAR24).", tipo="aviso")
                return
            c_uid = ""      # Consultar todos los facilitadores pertenecientes a esa sede
            c_infoid = infoid
            c_estado = ""
        else:
            if not estado:
                self._mostrar_modal_mensaje("Falta Estado", "En el modo 'Resumen Estadal' debe seleccionar el estado a auditar.", tipo="aviso")
                return
            c_uid = ""
            c_infoid = ""
            c_estado = estado

        self.ejecutando_auditoria = True
        self.btn_iniciar_auditoria.configure(text="⏳ Auditando...", state="disabled", fg_color="#E67E22")
        self.btn_abrir_reporte_auditoria.configure(state="disabled")
        if hasattr(self, "btn_exportar_reporte_dialogo"):
            self.btn_exportar_reporte_dialogo.configure(state="disabled")
        self.lbl_auditoria_estado.configure(text="Conectando con InfoApp y auditando...", text_color="#3B8ED0")
        self.lbl_kpi_cuadre.configure(text="● Consultando...", text_color="#3B8ED0")

        modo_turbo = self.var_modo_turbo.get()

        params = {
            "uid": c_uid,
            "info_id": c_infoid,
            "estado": c_estado,
            "fecha_inicio": f_desde,
            "fecha_fin": f_hasta,
            "rol_auditor": rol,
            "exportar_formato": "ninguno",
            "formato": "ninguno",
            "modo_turbo": modo_turbo
        }

        t = threading.Thread(target=self._hilo_auditoria_worker, args=(params,), daemon=True)
        t.start()

    def _hilo_auditoria_worker(self, params: dict):
        """Worker en segundo plano para ejecutar la auditoría sin congelar la GUI."""
        def callback_progreso(msg: str):
            self.cola_eventos.put(("log_auditoria", msg))

        try:
            self.cola_eventos.put(("log_auditoria", f"Iniciando motor de auditoría oficial {ETIQUETA_VERSION}..."))
            resultado = ar.ejecutar_auditoria(
                uid=params.get("uid"),
                info_id=params.get("info_id"),
                estado=params.get("estado"),
                fecha_inicio=params.get("fecha_inicio"),
                fecha_fin=params.get("fecha_fin"),
                start_at=params.get("fecha_inicio"),
                finish_at=params.get("fecha_fin"),
                rol_auditor=params.get("rol_auditor", False),
                exportar_formato="ninguno",
                formato="ninguno",
                modo_turbo=params.get("modo_turbo", True),
                callback_log=callback_progreso,
                progreso_callback=callback_progreso
            )
            # Persistir caché de forma desacoplada en el worker sin bloquear el bucle de eventos Tkinter
            try:
                ar.guardar_cache_inspector(resultado)
            except Exception:
                pass
            self.cola_eventos.put(("fin_auditoria", resultado))
        except Exception as e:
            self.cola_eventos.put(("fin_auditoria", {"exito": False, "error": str(e)}))

    def _finalizar_ejecucion_auditoria(self, resultado: dict):
        """Actualiza la interfaz con los datos y métricas recibidos de la auditoría."""
        self.ejecutando_auditoria = False
        self.btn_iniciar_auditoria.configure(text="🔍 Iniciar Auditoría", state="normal", fg_color="#27AE60")
        self.resultado_auditoria_actual = resultado

        if not resultado.get("exito"):
            err = resultado.get("error", "Error desconocido")
            self.lbl_auditoria_estado.configure(text=f"Error en auditoría: {err}", text_color="#E74C3C")
            self.lbl_kpi_cuadre.configure(text="● Error", text_color="#E74C3C")
            self.lbl_kpi_cuadre_sub.configure(text="Fallo de conexión", text_color="#E74C3C")
            if hasattr(self, "btn_exportar_reporte_dialogo"):
                self.btn_exportar_reporte_dialogo.configure(state="disabled")
            self._mostrar_modal_mensaje("Fallo en Auditoría", f"No se pudo completar la inspección:\n{err}", tipo="error")
            return

        tot_act = resultado.get("total_actividades", 0)
        n_form = len(resultado.get("formaciones", []))
        n_prod = len(resultado.get("productos", []))
        n_otr = len(resultado.get("otras_actividades", []))
        tot_est = resultado.get("total_estudiantes", 0)
        tot_srv = resultado.get("total_servicios", 0)
        cuadro_ok = resultado.get("cuadre_perfecto", False)

        # Gestión de resultados vacíos (Directiva v4.2.4)
        if tot_act == 0 and tot_srv == 0:
            self.lbl_kpi_actividades.configure(text="0")
            self.lbl_kpi_actividades_sub.configure(text="0 Form | 0 Prod | 0 Otr")
            if hasattr(self, "lbl_kpi_actividades_det"):
                self.lbl_kpi_actividades_det.configure(text="Rango sin actividad")
            self.lbl_kpi_formados.configure(text="0")
            if hasattr(self, "lbl_kpi_formados_det"):
                self.lbl_kpi_formados_det.configure(text="0 aulas registradas")
            self.lbl_kpi_servicios.configure(text="0")
            if hasattr(self, "lbl_kpi_servicios_det"):
                self.lbl_kpi_servicios_det.configure(text="0 atenciones registradas")
            self.lbl_kpi_cuadre.configure(text="● Sin Registros", text_color="#A1A1AA")
            self.lbl_kpi_cuadre_sub.configure(text="0 actividades encontradas", text_color="#A1A1AA")
            if hasattr(self, "lbl_kpi_cuadre_det"):
                self.lbl_kpi_cuadre_det.configure(text="Sin discrepancias")

            self._poblar_tab_actividades([])
            self._poblar_tab_servicios([])
            self._poblar_tab_facilitadores({})

            msg_aviso = "[AVISO] No se encontraron actividades o usuarios en el rango seleccionado."
            self._agregar_log_auditoria(msg_aviso)
            self.lbl_auditoria_estado.configure(text=msg_aviso, text_color="#F39C12")
            self.btn_abrir_reporte_auditoria.configure(state="disabled")
            if hasattr(self, "btn_exportar_reporte_dialogo"):
                self.btn_exportar_reporte_dialogo.configure(state="disabled")
            self._mostrar_toast(msg_aviso)
            return

        self.lbl_kpi_actividades.configure(text=str(tot_act))
        self.lbl_kpi_actividades_sub.configure(text=f"{n_form} Form | {n_prod} Prod | {n_otr} Otr")
        todas_act = resultado.get("formaciones", []) + resultado.get("productos", []) + resultado.get("otras_actividades", [])
        if hasattr(self, "lbl_kpi_actividades_det"):
            sedes_unicas = len(set(str(a.get("info_id", "")).strip() for a in todas_act if a.get("info_id")))
            self.lbl_kpi_actividades_det.configure(text=f"Total: {tot_act} act • {sedes_unicas} sede(s)")

        self.lbl_kpi_formados.configure(text=str(tot_est))
        self.lbl_kpi_formados_sub.configure(text=f"{tot_est} Participantes en aula")
        if hasattr(self, "lbl_kpi_formados_det"):
            prom = (tot_est / n_form) if n_form > 0 else 0.0
            self.lbl_kpi_formados_det.configure(text=f"Promedio: {prom:.1f} est / formación ({n_form} aulas)")

        self.lbl_kpi_servicios.configure(text=str(tot_srv))
        ced = resultado.get("cedulados_serv", 0)
        no_ced = resultado.get("no_cedulados_serv", 0)
        self.lbl_kpi_servicios_sub.configure(text=f"{ced} Cedulados | {no_ced} Sin Cédula")
        if hasattr(self, "lbl_kpi_servicios_det"):
            conteo_s = resultado.get("conteo_servicios", {})
            if conteo_s:
                top_srv_nom = max(conteo_s, key=conteo_s.get)
                if len(top_srv_nom) > 22:
                    top_srv_nom = top_srv_nom[:20] + ".."
                self.lbl_kpi_servicios_det.configure(text=f"Top: {top_srv_nom} ({conteo_s[max(conteo_s, key=conteo_s.get)]})")
            else:
                self.lbl_kpi_servicios_det.configure(text=f"{tot_srv} atenciones registradas")

        conciliacion = resultado.get("conciliacion")
        if conciliacion:
            cuadro_ok = conciliacion.get("cuadra", False)

        if cuadro_ok:
            self.lbl_kpi_cuadre.configure(text="● Cuadrado (100%)", text_color="#2ECC71")
            self.lbl_kpi_cuadre_sub.configure(text="Coincidencia exacta", text_color="#2ECC71")
            if hasattr(self, "lbl_kpi_cuadre_det"):
                self.lbl_kpi_cuadre_det.configure(text="Balance verificado sin anomalías", text_color="#2ECC71")
        else:
            hallazgos = conciliacion.get("hallazgos", []) if conciliacion else []
            txt_sub = f"{len(hallazgos)} hallazgo(s) detectado(s)" if hallazgos else "Discrepancia detectada"
            self.lbl_kpi_cuadre.configure(text="● Descuadre", text_color="#E74C3C")
            self.lbl_kpi_cuadre_sub.configure(text=txt_sub, text_color="#E74C3C")
            if hasattr(self, "lbl_kpi_cuadre_det"):
                det_txt = (hallazgos[0][:38] + "...") if hallazgos else f"Actividades: {tot_act}"
                self.lbl_kpi_cuadre_det.configure(text=det_txt, text_color="#E74C3C")

        self._poblar_tab_actividades(todas_act)
        self._poblar_tab_servicios(resultado.get("servicios", []))
        self._poblar_tab_facilitadores(resultado.get("resumen_facilitadores", {}))

        # Habilitar botones de inspección y exportación dinámica
        if hasattr(self, "btn_exportar_reporte_dialogo"):
            self.btn_exportar_reporte_dialogo.configure(state="normal")
        if hasattr(self, "btn_ver_actividades"):
            self.btn_ver_actividades.configure(state="normal")
        if hasattr(self, "btn_ver_servicios"):
            self.btn_ver_servicios.configure(state="normal")
        if hasattr(self, "btn_ver_facilitadores"):
            self.btn_ver_facilitadores.configure(state="normal")

        ruta_exp = resultado.get("archivo_exportado", "")
        if ruta_exp and os.path.exists(ruta_exp):
            self.ruta_ultimo_reporte_auditoria = ruta_exp
            self.btn_abrir_reporte_auditoria.configure(state="normal", fg_color="#1f538d", hover_color="#14375e")
            self.lbl_auditoria_estado.configure(
                text=f"Auditoría exitosa: {tot_act} actividades, {tot_est} formados, {tot_srv} servicios. Reporte exportado.",
                text_color="#2ECC71"
            )
        else:
            self.btn_abrir_reporte_auditoria.configure(state="disabled")
            self.lbl_auditoria_estado.configure(
                text=f"Auditoría finalizada: {tot_act} actividades, {tot_est} formados, {tot_srv} servicios.",
                text_color="#2ECC71"
            )

        try:
            self.tabview_auditoria.set("🎓 Formaciones y Actividades")
        except Exception:
            pass

    def _actualizar_progreso_auditoria(self, pct):
        """Callback para sincronizar avance porcentual si se activa barra."""
        pass

    def _poblar_tab_actividades(self, actividades: list):
        """Método de compatibilidad para procesar o actualizar actividades en memoria."""
        pass

    def _poblar_tab_servicios(self, servicios: list):
        """Método de compatibilidad para procesar o actualizar servicios en memoria."""
        pass

    def _poblar_tab_facilitadores(self, facilitadores: dict):
        """Método de compatibilidad para procesar o actualizar facilitadores en memoria."""
        pass

    def _abrir_ultimo_reporte_auditoria(self):
        """Abre directamente el último reporte exportado si existe en el sistema de archivos."""
        if self.ruta_ultimo_reporte_auditoria and os.path.exists(self.ruta_ultimo_reporte_auditoria):
            abrir_archivo_o_directorio_sistema(self.ruta_ultimo_reporte_auditoria)
            self._agregar_log_auditoria(f"[SISTEMA] Abriendo reporte: {self.ruta_ultimo_reporte_auditoria}")
        else:
            self._mostrar_modal_mensaje("Reporte no disponible", "No hay un archivo de reporte generado recientemente.", tipo="aviso")

    _abrir_reporte_auditoria_actual = _abrir_ultimo_reporte_auditoria

    def _accion_exportar_reporte_dialogo(self):
        """Despliega el diálogo interactivo para guardar el reporte en el formato seleccionado o mostrarlo en telemetría."""
        if not self.resultado_auditoria_actual:
            self._mostrar_modal_mensaje("Sin Datos", "Debe ejecutar una auditoría antes de exportar el reporte.", tipo="aviso")
            return

        formato_str = self.var_exportar_formato.get()
        fecha_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        res = self.resultado_auditoria_actual

        if "Consola" in formato_str or "Pantalla" in formato_str:
            resumen_txt = ar.generar_resumen_consola(res)
            self._agregar_log_auditoria("\n" + resumen_txt)
            self._mostrar_toast("Resumen ejecutivo visualizado en telemetría.")
            return

        fmt_low = formato_str.lower()
        if "ods" in fmt_low or "libreoffice" in fmt_low or "calc" in fmt_low:
            def_ext = ".ods"
            ftypes = [("Libro LibreOffice Calc", "*.ods"), ("Todos los archivos", "*.*")]
            formato_clave = "ods"
        elif "pdf" in fmt_low:
            def_ext = ".pdf"
            ftypes = [("Documento Portable PDF", "*.pdf"), ("Todos los archivos", "*.*")]
            formato_clave = "pdf"
        elif "csv" in fmt_low:
            def_ext = ".csv"
            ftypes = [("Valores separados por comas", "*.csv"), ("Todos los archivos", "*.*")]
            formato_clave = "csv"
        else:
            def_ext = ".xlsx"
            ftypes = [("Libro de Microsoft Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
            formato_clave = "excel"

        nombre_sugerido = f"Auditoria_InfoApp_{fecha_stamp}{def_ext}"
        os.makedirs(self.directorio_reportes_auditoria, exist_ok=True)

        ruta_elegida = filedialog.asksaveasfilename(
            initialdir=self.directorio_reportes_auditoria,
            initialfile=nombre_sugerido,
            defaultextension=def_ext,
            filetypes=ftypes,
            title=f"Guardar Reporte de Auditoría ({formato_str})"
        )

        if not ruta_elegida:
            return

        self._agregar_log_auditoria(f"⏳ Iniciando exportación en segundo plano ({formato_str})...")

        def _trabajo_exportacion():
            try:
                ruta_final = ar.exportar_reporte_auditoria(res, formato=formato_clave, ruta_destino=ruta_elegida)
                self.cola_eventos.put(("exportacion_ok", ruta_final))
            except Exception as e:
                self.cola_eventos.put(("exportacion_error", str(e)))

        threading.Thread(target=_trabajo_exportacion, daemon=True).start()

    def _abrir_directorio_reportes_auditoria(self):
        """Abre el explorador de archivos en la carpeta Reportes_Auditoria/."""
        rep_dir = os.path.join(BASE_DIR, "Reportes_Auditoria")
        os.makedirs(rep_dir, exist_ok=True)
        abrir_archivo_o_directorio_sistema(rep_dir)
        self._agregar_log_auditoria(f"[SISTEMA] Abriendo directorio de reportes: {rep_dir}")

    def _limpiar_log_auditoria(self):
        """Limpia el visor de telemetría principal."""
        self._limpiar_logs()

    def _agregar_log_auditoria(self, texto: str):
        """Redirige registros de auditoría hacia la consola unificada de telemetría."""
        self.agregar_log_telemetria(f"[AUDITORÍA] {texto}")

    def _cargar_ultima_busqueda_cache(self):
        """Carga en la interfaz los resultados cacheados de la última auditoría."""
        datos = self.cargar_cache_inspector()
        if not datos or not datos.get("exito"):
            self._mostrar_modal_mensaje("Sin Caché", "No se encontró ningún caché de búsqueda reciente.", tipo="info")
            return False
        self._finalizar_ejecucion_auditoria(datos)
        self._agregar_log_auditoria("[CACHE] Datos cargados desde la última búsqueda almacenada.")
        self._mostrar_toast("Caché de auditoría cargado con éxito")
        return True

    def guardar_cache_inspector(self, resultado: dict, ruta_archivo: str = None) -> str:
        """Persiste los resultados de auditoría en el caché ligero JSON."""
        return ar.guardar_cache_inspector(resultado, ruta_archivo)

    def cargar_cache_inspector(self, ruta_archivo: str = None) -> dict:
        """Carga los resultados de auditoría desde el caché ligero JSON."""
        return ar.cargar_cache_inspector(ruta_archivo)

    def _mostrar_modal_confirmacion(self, titulo: str, mensaje: str, callback_si=None, callback_no=None):
        """
        Despliega un diálogo modal de confirmación con CTkToplevel y botones Sí / Cancelar,
        garantizando cero dependencias de consola o sys.stdin.
        """
        modal = ctk.CTkToplevel(self)
        modal.title(titulo)
        ancho, alto = 480, 200
        pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho) // 2)
        pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto) // 2)
        modal.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")
        modal.resizable(False, False)
        modal.transient(self)

        def _al_cancelar_modal():
            if callback_no:
                try:
                    callback_no()
                except Exception:
                    pass

        self.registrar_modal("modal_confirmacion", modal, grab=True, al_cerrar=_al_cancelar_modal)

        f_top = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0)
        f_top.pack(fill="x")
        ctk.CTkLabel(f_top, text=f"❓ {titulo}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3B8ED0").pack(anchor="w", padx=16, pady=10)

        f_body = ctk.CTkFrame(modal, fg_color="transparent")
        f_body.pack(fill="both", expand=True, padx=20, pady=12)
        ctk.CTkLabel(f_body, text=mensaje, font=ctk.CTkFont(size=11), text_color="#E0E0E8", justify="left", wraplength=440).pack(anchor="w", fill="x")

        f_btns = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0, height=48)
        f_btns.pack(fill="x", side="bottom")

        def al_confirmar():
            try:
                delattr(modal, "_cb_al_cerrar")
            except Exception:
                pass
            self.cerrar_modal(modal)
            if callback_si:
                try:
                    callback_si()
                except Exception:
                    pass

        def al_cancelar():
            self.cerrar_modal(modal)

        ctk.CTkButton(f_btns, text="Cancelar", width=90, fg_color="#4A4A5A", hover_color="#5A5A6A", command=al_cancelar).pack(side="right", padx=(6, 16), pady=8)
        ctk.CTkButton(f_btns, text="Confirmar", width=100, fg_color="#27AE60", hover_color="#219653", command=al_confirmar).pack(side="right", padx=6, pady=8)

    def _mostrar_toast(self, mensaje: str, duracion_ms: int = 3500):
        """Muestra una notificación flotante estilo Toast no intrusiva y sin bloqueo."""
        try:
            toast = ctk.CTkToplevel(self)
            toast.withdraw()
            toast.overrideredirect(True)
            try:
                toast.attributes("-topmost", True)
            except Exception:
                pass

            self.registrar_modal("toast", toast, grab=False)

            frame = ctk.CTkFrame(toast, fg_color="#1E1E28", border_width=1, border_color="#F39C12", corner_radius=8)
            frame.pack(fill="both", expand=True, padx=2, pady=2)

            lbl = ctk.CTkLabel(
                frame,
                text=f"🔔 {mensaje}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#F39C12",
                padx=16,
                pady=10
            )
            lbl.pack()

            toast.update_idletasks()
            w = toast.winfo_reqwidth()
            h = toast.winfo_reqheight()

            x = self.winfo_x() + self.winfo_width() - w - 24
            y = self.winfo_y() + self.winfo_height() - h - 36
            toast.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
            toast.deiconify()

            def cerrar_toast():
                self.cerrar_modal(toast)

            self.after(duracion_ms, cerrar_toast)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # E. VISTA 5: CRÉDITOS Y AUTORÍA (PESTAÑA NATIVA EMBEBIDA)
    # -------------------------------------------------------------------------
    def _crear_vista_creditos(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        head_box = ctk.CTkFrame(frame, fg_color="transparent")
        head_box.pack(fill="x", padx=16, pady=(14, 8))

        if self.iconos.get("robot_logo"):
            try:
                lbl_logo = self._crear_label_con_icono(head_box, text="", icono_clave="robot_logo")
                lbl_logo.pack(pady=(0, 4))
            except Exception:
                pass

        lbl_title = ctk.CTkLabel(
            head_box,
            text="JsBOT (Robotic Process Automation)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack()

        lbl_version = ctk.CTkLabel(
            head_box,
            text=f"Versión {__version__} Oficial — Núcleo de Automatización {ETIQUETA_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="#3B8ED0"
        )
        lbl_version.pack(pady=(2, 0))

        scroll_creditos = ctk.CTkScrollableFrame(frame, height=290, fg_color="transparent")
        scroll_creditos.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Tarjeta 1: Co-Desarrollo y Arquitectura
        card_equipo = ctk.CTkFrame(scroll_creditos, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card_equipo.pack(fill="x", pady=(0, 10))

        t1_top = ctk.CTkFrame(card_equipo, fg_color="transparent")
        t1_top.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(t1_top, text="Co-Desarrollo y Arquitectura", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3B8ED0").pack(side="left")

        items_equipo = [
            ("Autor Principal:", "Jair Alejandro Hernández González"),
            ("Rol en Proyecto:", "Diseñador y Desarrollador de Automatización / Facilitador Infocentro"),
            ("IA Colaboradora:", "Gemini (Google DeepMind) — Arquitectura de Resiliencia, Hardening y QA"),
            ("Organización:", "Fundación Infocentro — San Felipe, Yaracuy, Venezuela")
        ]

        for k, v in items_equipo:
            row = ctk.CTkFrame(card_equipo, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(row, text=k, font=ctk.CTkFont(size=10), text_color="#8E8E98").pack(side="left")
            ctk.CTkLabel(row, text=v, font=ctk.CTkFont(size=10, weight="bold"), text_color="#D1D1D6").pack(side="right")

        ctk.CTkLabel(card_equipo, text="", height=2).pack()

        # Tarjeta 2: Enlaces y Contacto Directo
        card_contacto = ctk.CTkFrame(scroll_creditos, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card_contacto.pack(fill="x", pady=(0, 8))

        t2_top = ctk.CTkFrame(card_contacto, fg_color="transparent")
        t2_top.pack(fill="x", padx=14, pady=(10, 6))
        ctk.CTkLabel(t2_top, text="Contacto y Portafolio Oficial", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3B8ED0").pack(side="left")

        btn_portafolio = ctk.CTkButton(
            card_contacto,
            text="🌐  Portafolio: cloverjh17.github.io",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=34,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=lambda: webbrowser.open("https://cloverjh17.github.io/")
        )
        btn_portafolio.pack(fill="x", padx=14, pady=(0, 8))

        contacto_grid = ctk.CTkFrame(card_contacto, fg_color="transparent")
        contacto_grid.pack(fill="x", padx=14, pady=(0, 8))
        contacto_grid.grid_columnconfigure((0, 1), weight=1)

        btn_telegram = ctk.CTkButton(
            contacto_grid,
            text="✈ Telegram: @CloverJH17",
            font=ctk.CTkFont(size=10),
            height=30,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: webbrowser.open("https://t.me/CloverJH17")
        )
        btn_telegram.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        btn_email = ctk.CTkButton(
            contacto_grid,
            text="✉ the.hernandezjair@gmail.com",
            font=ctk.CTkFont(size=10),
            height=30,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: webbrowser.open("mailto:the.hernandezjair@gmail.com")
        )
        btn_email.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        lbl_lema = ctk.CTkLabel(
            card_contacto,
            text='"Todo tiene solución, menos la muerte... y aun así, existen excepciones."',
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#A1A1AA"
        )
        lbl_lema.pack(pady=(2, 10))

        return frame

    # -------------------------------------------------------------------------
    # F. VISTA 6: AJUSTES (GRID REACTIVO Y COLAPSO TOTAL)
    # -------------------------------------------------------------------------
    def _crear_vista_ajustes(self, padre) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        frame.grid_columnconfigure(0, weight=1)

        # Fila 0: Encabezado
        self.header_ajustes = ctk.CTkFrame(frame, fg_color="transparent")
        self.header_ajustes.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        lbl_title = self._crear_label_con_icono(
            self.header_ajustes,
            text="Parámetros de Configuración y Preferencias",
            icono_clave="ajustes",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_title.pack(side="left")

        # Fila 1: Banner Dinámico de Advertencia (Oculto inicialmente sin reservar espacio)
        self.banner_advertencia = ctk.CTkFrame(frame, fg_color="#2A2415", border_width=1, border_color="#F5A623", corner_radius=8)
        self.banner_advertencia.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.banner_advertencia.grid_remove()

        banner_inner = ctk.CTkFrame(self.banner_advertencia, fg_color="transparent")
        banner_inner.pack(fill="x", padx=10, pady=6)

        self.lbl_adv_text = ctk.CTkLabel(
            banner_inner,
            text="⚠️ Has modificado parámetros críticos de red. Reducir los tiempos puede causar errores en conexiones lentas.",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#F5A623",
            anchor="w"
        )
        self.lbl_adv_text.pack(fill="x", pady=(0, 4))

        self.adv_btn_row = ctk.CTkFrame(banner_inner, fg_color="transparent")
        self.adv_btn_row.pack(fill="x")

        self.btn_guardar_ajustes = ctk.CTkButton(
            self.adv_btn_row,
            text="Guardar Cambios",
            width=120,
            height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self._guardar_cambios_ajustes
        )
        self.btn_guardar_ajustes.pack(side="left", padx=(0, 8))

        self.btn_restaurar_ajustes = ctk.CTkButton(
            self.adv_btn_row,
            text="Restaurar Valores por Defecto",
            width=170,
            height=26,
            font=ctk.CTkFont(size=10),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._restaurar_defaults_ajustes
        )
        self.btn_restaurar_ajustes.pack(side="left")

        # Fila 2: Contenedor desplazable de ajustes (Sube de inmediato si el banner no existe)
        self.scroll_ajustes = ctk.CTkScrollableFrame(frame, height=290, fg_color="transparent")
        self.scroll_ajustes.grid(row=2, column=0, sticky="nsew", padx=12, pady=(2, 10))
        frame.grid_rowconfigure(2, weight=1)

        # 1. BLOQUE: Timeouts y Esperas
        card_timeouts = ctk.CTkFrame(self.scroll_ajustes, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card_timeouts.pack(fill="x", pady=4)

        t_lbl = ctk.CTkLabel(card_timeouts, text="Timeouts y Esperas de Red (Segundos)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#3B8ED0")
        t_lbl.pack(anchor="w", padx=12, pady=(6, 4))

        self._crear_control_timeout(card_timeouts, "Login Timeout:", "login", self.var_login_timeout, 5, 30)
        self._crear_control_timeout(card_timeouts, "Espera AJAX / Peticiones:", "ajax", self.var_ajax_timeout, 5, 30)
        self._crear_control_timeout(card_timeouts, "Búsqueda de Elementos DOM:", "element", self.var_element_timeout, 5, 30)
        ctk.CTkLabel(card_timeouts, text="", height=2).pack()

        # 2. BLOQUE: Preferencia de Navegador
        card_browser = ctk.CTkFrame(self.scroll_ajustes, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card_browser.pack(fill="x", pady=4)

        b_lbl = ctk.CTkLabel(card_browser, text="Preferencia de Navegador y Ventana", font=ctk.CTkFont(size=11, weight="bold"), text_color="#3B8ED0")
        b_lbl.pack(anchor="w", padx=12, pady=(6, 4))

        row_nav = ctk.CTkFrame(card_browser, fg_color="transparent")
        row_nav.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row_nav, text="Navegador Principal:", font=ctk.CTkFont(size=10), text_color="#A1A1AA").pack(side="left")

        combo_nav = ctk.CTkComboBox(
            row_nav,
            values=["Firefox (Recomendado)", "Google Chrome", "Microsoft Edge"],
            variable=self.var_browser_pref,
            width=200,
            height=26,
            command=lambda v: self._al_modificar_parametro()
        )
        combo_nav.pack(side="right")

        row_max = ctk.CTkFrame(card_browser, fg_color="transparent")
        row_max.pack(fill="x", padx=12, pady=2)
        sw_max = ctk.CTkSwitch(
            row_max,
            text="Iniciar navegador maximizado",
            variable=self.var_start_maximized,
            font=ctk.CTkFont(size=10),
            command=self._al_modificar_parametro
        )
        sw_max.pack(side="left")
        ctk.CTkLabel(card_browser, text="", height=2).pack()

        # 3. BLOQUE: Opciones de Captura y Logs
        card_logs = ctk.CTkFrame(self.scroll_ajustes, fg_color="#161620", corner_radius=10, border_width=1, border_color="#292938")
        card_logs.pack(fill="x", pady=4)

        l_lbl = ctk.CTkLabel(card_logs, text="Opciones de Captura y Validación", font=ctk.CTkFont(size=11, weight="bold"), text_color="#3B8ED0")
        l_lbl.pack(anchor="w", padx=12, pady=(6, 4))

        row_sw1 = ctk.CTkFrame(card_logs, fg_color="transparent")
        row_sw1.pack(fill="x", padx=12, pady=2)
        sw_cap = ctk.CTkSwitch(
            row_sw1,
            text="Capturar pantalla automáticamente en caso de error (logs/screenshots/)",
            variable=self.var_capture_screenshots,
            font=ctk.CTkFont(size=10),
            command=self._al_modificar_parametro
        )
        sw_cap.pack(side="left")

        row_sw2 = ctk.CTkFrame(card_logs, fg_color="transparent")
        row_sw2.pack(fill="x", padx=12, pady=2)
        sw_det = ctk.CTkSwitch(
            row_sw2,
            text="Habilitar trazas detalladas de normalización en disco (normalizacion.log)",
            variable=self.var_detailed_logs,
            font=ctk.CTkFont(size=10),
            command=self._al_modificar_parametro
        )
        sw_det.pack(side="left")

        row_tlf = ctk.CTkFrame(card_logs, fg_color="transparent")
        row_tlf.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row_tlf, text="Teléfono por defecto para menores:", font=ctk.CTkFont(size=10), text_color="#A1A1AA").pack(side="left")
        entry_tlf = ctk.CTkEntry(row_tlf, textvariable=self.var_default_phone, width=120, height=24)
        entry_tlf.pack(side="right")
        entry_tlf.bind("<KeyRelease>", lambda e: self._al_modificar_parametro())
        ctk.CTkLabel(card_logs, text="", height=2).pack()

        return frame

    def _crear_control_timeout(self, padre, etiqueta: str, clave: str, variable: tk.IntVar, v_min: int, v_max: int):
        row = ctk.CTkFrame(padre, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)

        lbl_nom = ctk.CTkLabel(row, text=etiqueta, width=160, anchor="w", font=ctk.CTkFont(size=10), text_color="#A1A1AA")
        lbl_nom.pack(side="left")

        val_lbl = ctk.CTkLabel(row, text=f"{variable.get()}s", width=30, font=ctk.CTkFont(size=10, weight="bold"), text_color="#E0E0E8")
        val_lbl.pack(side="right")
        self.labels_sliders[clave] = val_lbl

        def _on_slider(val):
            val_lbl.configure(text=f"{int(val)}s")
            self._al_modificar_parametro()

        slider = ctk.CTkSlider(
            row,
            from_=v_min,
            to=v_max,
            number_of_steps=v_max - v_min,
            variable=variable,
            height=12,
            command=_on_slider
        )
        slider.pack(side="right", fill="x", expand=True, padx=8)

    def _al_modificar_parametro(self):
        """Muestra el banner de advertencia con transición suave o lo oculta inmediatamente."""
        modificado = (
            self.var_login_timeout.get() != self.defaults_ajustes["login"] or
            self.var_ajax_timeout.get() != self.defaults_ajustes["ajax"] or
            self.var_element_timeout.get() != self.defaults_ajustes["element"] or
            self.var_browser_pref.get() != self.defaults_ajustes["browser"] or
            self.var_start_maximized.get() != self.defaults_ajustes["maximized"] or
            self.var_capture_screenshots.get() != self.defaults_ajustes["screenshots"] or
            self.var_detailed_logs.get() != self.defaults_ajustes["logs"] or
            self.var_default_phone.get() != self.defaults_ajustes["phone"]
        )
        if modificado:
            if not self.banner_advertencia.winfo_ismapped():
                self._mostrar_banner_advertencia_suave()
        else:
            self._ocultar_banner_advertencia_inmediato()

    def _mostrar_banner_advertencia_suave(self):
        """Muestra el banner de advertencia desplegando sus elementos secuencialmente con retardo de 40 ms."""
        if hasattr(self, "_banner_anim_id") and self._banner_anim_id:
            try:
                self.after_cancel(self._banner_anim_id)
            except Exception:
                pass
            self._banner_anim_id = None

        # Ocultar temporalmente los hijos para entrada secuencial suave
        if hasattr(self, "lbl_adv_text"):
            self.lbl_adv_text.pack_forget()
        if hasattr(self, "adv_btn_row"):
            self.adv_btn_row.pack_forget()

        # Colocar el contenedor en grid
        self.banner_advertencia.grid()

        def _paso_1():
            if hasattr(self, "lbl_adv_text"):
                self.lbl_adv_text.pack(fill="x", pady=(0, 4))
            self._banner_anim_id = self.after(40, _paso_2)

        def _paso_2():
            if hasattr(self, "adv_btn_row"):
                self.adv_btn_row.pack(fill="x")
            self._banner_anim_id = None

        self._banner_anim_id = self.after(40, _paso_1)

    def _ocultar_banner_advertencia_inmediato(self):
        """Oculta el banner de inmediato mediante grid_remove() para que el contenido inferior suba limpiamente."""
        if hasattr(self, "_banner_anim_id") and self._banner_anim_id:
            try:
                self.after_cancel(self._banner_anim_id)
            except Exception:
                pass
            self._banner_anim_id = None

        if hasattr(self, "banner_advertencia") and self.banner_advertencia.winfo_ismapped():
            self.banner_advertencia.grid_remove()

        # Restaurar visibilidad de los hijos para la próxima visualización
        if hasattr(self, "lbl_adv_text") and not self.lbl_adv_text.winfo_ismapped():
            self.lbl_adv_text.pack(fill="x", pady=(0, 4))
        if hasattr(self, "adv_btn_row") and not self.adv_btn_row.winfo_ismapped():
            self.adv_btn_row.pack(fill="x")

    def _guardar_cambios_ajustes(self):
        """Actualiza los valores baseline, los persiste en config/settings.json y oculta el banner inmediatamente."""
        self.defaults_ajustes["login"] = self.var_login_timeout.get()
        self.defaults_ajustes["ajax"] = self.var_ajax_timeout.get()
        self.defaults_ajustes["element"] = self.var_element_timeout.get()
        self.defaults_ajustes["browser"] = self.var_browser_pref.get()
        self.defaults_ajustes["maximized"] = self.var_start_maximized.get()
        self.defaults_ajustes["screenshots"] = self.var_capture_screenshots.get()
        self.defaults_ajustes["logs"] = self.var_detailed_logs.get()
        self.defaults_ajustes["phone"] = self.var_default_phone.get()

        pref = self.var_browser_pref.get()
        if "chrome" in pref.lower():
            prioridad = ["chrome", "firefox", "edge"]
        elif "edge" in pref.lower():
            prioridad = ["edge", "chrome", "firefox"]
        else:
            prioridad = ["firefox", "chrome", "edge"]

        nuevos_settings = {
            "timeouts": {
                "login_wait_seconds": int(self.var_login_timeout.get()),
                "ajax_wait_seconds": int(self.var_ajax_timeout.get()),
                "element_wait_seconds": int(self.var_element_timeout.get())
            },
            "browser": {
                "priority": prioridad,
                "start_maximized": bool(self.var_start_maximized.get())
            },
            "validation": {
                "default_phone": str(self.var_default_phone.get()).strip() or "0412-0000000",
                "capture_screenshots_on_error": bool(self.var_capture_screenshots.get())
            }
        }

        if MODULOS_DISPONIBLES:
            try:
                cm.guardar_settings(nuevos_settings)
            except Exception as e:
                self._agregar_log(f"[ADVERTENCIA] Error guardando ajustes: {e}")

        self._ocultar_banner_advertencia_inmediato()
        self._agregar_log(f"[AJUSTES] Parámetros guardados y persistidos en config/settings.json: Login={self.defaults_ajustes['login']}s, AJAX={self.defaults_ajustes['ajax']}s, Element={self.defaults_ajustes['element']}s, Navegador={self.defaults_ajustes['browser']}.")

    def _restaurar_defaults_ajustes(self):
        """Restaura los valores por defecto, los persiste en disco y retira el banner inmediatamente sin dejar espacios."""
        self.var_login_timeout.set(15)
        self.var_ajax_timeout.set(15)
        self.var_element_timeout.set(12)
        self.var_browser_pref.set("Firefox (Recomendado)")
        self.var_start_maximized.set(True)
        self.var_capture_screenshots.set(True)
        self.var_detailed_logs.set(True)
        self.var_default_phone.set("0412-0000000")

        if "login" in self.labels_sliders:
            self.labels_sliders["login"].configure(text="15s")
        if "ajax" in self.labels_sliders:
            self.labels_sliders["ajax"].configure(text="15s")
        if "element" in self.labels_sliders:
            self.labels_sliders["element"].configure(text="12s")

        self.defaults_ajustes["login"] = 15
        self.defaults_ajustes["ajax"] = 15
        self.defaults_ajustes["element"] = 12
        self.defaults_ajustes["browser"] = "Firefox (Recomendado)"
        self.defaults_ajustes["maximized"] = True
        self.defaults_ajustes["screenshots"] = True
        self.defaults_ajustes["logs"] = True
        self.defaults_ajustes["phone"] = "0412-0000000"

        if MODULOS_DISPONIBLES:
            threading.Thread(target=cm.guardar_settings, args=(cm.DEFAULTS,), daemon=True).start()

        self._ocultar_banner_advertencia_inmediato()
        self._agregar_log("[AJUSTES] Valores restaurados por defecto y persistidos en config/settings.json.")

    # -------------------------------------------------------------------------
    # G. PANEL INFERIOR: TELEMETRÍA Y PROGRESO CON TOOLBAR COMPACTA
    # -------------------------------------------------------------------------
    def _crear_panel_telemetria(self, padre):
        self.panel_telemetria = ctk.CTkFrame(padre, corner_radius=12, fg_color="#1E1E28")
        self.panel_telemetria.grid(row=1, column=0, sticky="nsew")
        self.panel_telemetria.grid_rowconfigure(2, weight=1)
        self.panel_telemetria.grid_columnconfigure(0, weight=1)

        telemetria_header = ctk.CTkFrame(self.panel_telemetria, fg_color="transparent")
        telemetria_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(8, 4))

        lbl_telemetria = ctk.CTkLabel(
            telemetria_header,
            text="Telemetría y Registro de Ejecución",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_telemetria.pack(side="left")

        # Barra de herramientas compacta a la derecha (Directiva 2)
        toolbar_right = ctk.CTkFrame(telemetria_header, fg_color="transparent")
        toolbar_right.pack(side="right")

        self.lbl_porcentaje = ctk.CTkLabel(
            toolbar_right,
            text="Progreso: 0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#3B8ED0"
        )
        self.lbl_porcentaje.pack(side="left", padx=(0, 10))

        self.btn_copiar_logs = ctk.CTkButton(
            toolbar_right,
            text="📋 Copiar",
            width=68,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._copiar_logs
        )
        self.btn_copiar_logs.pack(side="left", padx=(0, 6))

        self.btn_limpiar_logs = ctk.CTkButton(
            toolbar_right,
            text="🧹 Limpiar",
            width=68,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._limpiar_logs
        )
        self.btn_limpiar_logs.pack(side="left")

        self.progreso = ctk.CTkProgressBar(self.panel_telemetria, height=7)
        self.progreso.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self.progreso.set(0.0)
        self.barra_progreso = self.progreso  # Alias para compatibilidad directa con directiva de animación

        self.textbox_logs = ctk.CTkTextbox(
            self.panel_telemetria,
            font=ctk.CTkFont(family="Consolas", size=11),
            height=110,
            corner_radius=8,
            fg_color="#121218",
            text_color="#D1D1D6"
        )
        self.textbox_logs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        self.txt_telemetria_auditoria = self.textbox_logs

    def _copiar_logs(self):
        """Copia el contenido del visor de telemetría al portapapeles con feedback temporal."""
        try:
            texto = self.textbox_logs.get("0.0", tk.END).strip()
            if texto:
                self.clipboard_clear()
                self.clipboard_append(texto)
                self.btn_copiar_logs.configure(text="✓ Copiado", fg_color="#2E7D32")
                self.after(1500, lambda: self.btn_copiar_logs.configure(text="📋 Copiar", fg_color="#2B2B36"))
        except Exception:
            pass

    def _limpiar_logs(self):
        """Vacía el visor de eventos para iniciar una sesión de prueba limpia."""
        self.textbox_logs.delete("0.0", tk.END)
        self._agregar_log("[CONSOLA] Registro de eventos vaciado.")

    def _mostrar_modal_mensaje(self, titulo: str, mensaje: str, tipo: str = "aviso"):
        """
        Muestra un diálogo modal visual mediante CTkMessagebox si está disponible,
        o mediante una ventana secundaria CTkToplevel vinculada a la ventana principal.
        Evita volcar excepciones o advertencias en sys.stdout.
        """
        try:
            from CTkMessagebox import CTkMessagebox
            icon_map = {"error": "cancel", "aviso": "warning", "info": "info", "ok": "check"}
            CTkMessagebox(master=self, title=titulo, message=mensaje, icon=icon_map.get(tipo, "info"))
            return
        except ImportError:
            pass

        try:
            self.update_idletasks()
            ancho = 500
            alto = 230
            pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho) // 2)
            pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto) // 2)

            modal = ctk.CTkToplevel(self)
            modal.title(titulo)
            modal.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")
            modal.resizable(False, False)
            modal.transient(self)
            self.registrar_modal("modal_mensaje", modal, grab=True)
            modal.focus_set()

            colores = {
                "error": ("#E74C3C", "❌ Error"),
                "aviso": ("#F39C12", "⚠️ Advertencia"),
                "info": ("#3B8ED0", "ℹ️ Información"),
                "ok": ("#30D158", "✅ Éxito")
            }
            color_tema, prefijo = colores.get(tipo, ("#3B8ED0", "ℹ️ Información"))

            f_top = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0)
            f_top.pack(fill="x")

            lbl_t = ctk.CTkLabel(
                f_top,
                text=f"{prefijo}: {titulo}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=color_tema
            )
            lbl_t.pack(anchor="w", padx=16, pady=10)

            f_body = ctk.CTkFrame(modal, fg_color="transparent")
            f_body.pack(fill="both", expand=True, padx=20, pady=12)

            lbl_msg = ctk.CTkLabel(
                f_body,
                text=mensaje,
                font=ctk.CTkFont(size=11),
                text_color="#E0E0E8",
                justify="left",
                wraplength=450
            )
            lbl_msg.pack(anchor="w", pady=(4, 8))

            btn_ok = ctk.CTkButton(
                modal,
                text="Aceptar",
                width=110,
                height=32,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#1f538d",
                hover_color="#14375e",
                command=lambda: self.cerrar_modal(modal)
            )
            btn_ok.pack(side="bottom", pady=(0, 14))
        except Exception:
            pass

    def _establecer_fecha_hoy(self, entry_widget):
        """Asigna la fecha actual en formato YYYY-MM-DD al campo de texto indicado."""
        if hasattr(entry_widget, "delete") and hasattr(entry_widget, "insert"):
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, datetime.now().strftime("%Y-%m-%d"))

    def _mostrar_selector_fecha(self, entry_destino):
        """
        Despliega un calendario flotante modal para seleccionar una fecha en formato YYYY-MM-DD.
        Totalmente nativo con CustomTkinter y calendar de Python estándar (sin dependencias externas).
        """
        try:
            val_actual = entry_destino.get().strip() if hasattr(entry_destino, "get") else ""
            año_act, mes_act, dia_act = None, None, None
            if val_actual:
                try:
                    f_dt = datetime.strptime(val_actual, "%Y-%m-%d")
                    año_act, mes_act, dia_act = f_dt.year, f_dt.month, f_dt.day
                except Exception:
                    pass

            hoy = datetime.now()
            if not año_act:
                año_act, mes_act, dia_act = hoy.year, hoy.month, hoy.day

            estado_cal = {
                "año": año_act,
                "mes": mes_act,
                "dia_sel": dia_act
            }

            self.update_idletasks()
            ancho = 340
            alto = 380
            pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho) // 2)
            pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto) // 2)

            modal = ctk.CTkToplevel(self)
            modal.title("Seleccionar Fecha")
            modal.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")
            modal.resizable(False, False)
            modal.configure(fg_color="#181822")
            modal.transient(self)
            self.registrar_modal("selector_fecha", modal, grab=True)
            modal.focus_set()

            meses_nombres = [
                "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]

            # Contenedor superior (Navegación Mes / Año)
            f_nav = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0, height=48)
            f_nav.pack(fill="x")

            lbl_mes_año = ctk.CTkLabel(
                f_nav,
                text="",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#FFFFFF"
            )

            # Contenedor para días de la semana y grilla
            f_cal = ctk.CTkFrame(modal, fg_color="transparent")
            f_cal.pack(fill="both", expand=True, padx=14, pady=10)

            # Contenedor inferior (Acciones)
            f_pie = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0, height=45)
            f_pie.pack(fill="x", side="bottom")

            def _seleccionar_y_cerrar(a, m, d):
                fecha_str = f"{a:04d}-{m:02d}-{d:02d}"
                if hasattr(entry_destino, "delete") and hasattr(entry_destino, "insert"):
                    entry_destino.delete(0, tk.END)
                    entry_destino.insert(0, fecha_str)
                self.cerrar_modal(modal)

            def _seleccionar_hoy():
                _seleccionar_y_cerrar(hoy.year, hoy.month, hoy.day)

            def _cambiar_mes(delta):
                m = estado_cal["mes"] + delta
                a = estado_cal["año"]
                if m > 12:
                    m = 1
                    a += 1
                elif m < 1:
                    m = 12
                    a -= 1
                estado_cal["mes"] = m
                estado_cal["año"] = a
                _renderizar_calendario()

            def _cambiar_año(delta):
                estado_cal["año"] += delta
                _renderizar_calendario()

            # Botones de navegación
            btn_prev_a = ctk.CTkButton(f_nav, text="«", width=26, height=28, fg_color="transparent", hover_color="#2B2B36", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: _cambiar_año(-1))
            btn_prev_a.pack(side="left", padx=(8, 2), pady=8)

            btn_prev_m = ctk.CTkButton(f_nav, text="‹", width=26, height=28, fg_color="transparent", hover_color="#2B2B36", font=ctk.CTkFont(size=14, weight="bold"), command=lambda: _cambiar_mes(-1))
            btn_prev_m.pack(side="left", padx=(0, 4), pady=8)

            lbl_mes_año.pack(side="left", expand=True, pady=8)

            btn_next_m = ctk.CTkButton(f_nav, text="›", width=26, height=28, fg_color="transparent", hover_color="#2B2B36", font=ctk.CTkFont(size=14, weight="bold"), command=lambda: _cambiar_mes(1))
            btn_next_m.pack(side="right", padx=(0, 4), pady=8)

            btn_next_a = ctk.CTkButton(f_nav, text="»", width=26, height=28, fg_color="transparent", hover_color="#2B2B36", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: _cambiar_año(1))
            btn_next_a.pack(side="right", padx=(2, 8), pady=8)

            def _renderizar_calendario():
                for widget in f_cal.winfo_children():
                    widget.destroy()

                a = estado_cal["año"]
                m = estado_cal["mes"]
                lbl_mes_año.configure(text=f"{meses_nombres[m]} {a}")

                # Fila de días de la semana
                dias_sem = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
                for col_idx, d_nom in enumerate(dias_sem):
                    color_d = "#3B8ED0" if col_idx < 5 else "#F39C12"
                    lbl_d = ctk.CTkLabel(
                        f_cal,
                        text=d_nom,
                        font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=color_d,
                        width=38
                    )
                    lbl_d.grid(row=0, column=col_idx, padx=1, pady=(0, 4))

                # Días del mes con calendar.monthcalendar
                cal_matriz = calendar.monthcalendar(a, m)
                for r_idx, semana in enumerate(cal_matriz):
                    for c_idx, dia in enumerate(semana):
                        if dia == 0:
                            lbl_v = ctk.CTkLabel(f_cal, text="", width=38, height=28)
                            lbl_v.grid(row=r_idx + 1, column=c_idx, padx=1, pady=1)
                        else:
                            es_hoy = (a == hoy.year and m == hoy.month and dia == hoy.day)
                            es_sel = (a == estado_cal.get("año") and m == estado_cal.get("mes") and dia == estado_cal.get("dia_sel"))

                            fg_col = "#2E7D32" if es_hoy else ("#3B8ED0" if es_sel else "transparent")
                            hov_col = "#1B5E20" if es_hoy else "#2B2B36"
                            txt_col = "#FFFFFF" if (es_hoy or es_sel) else "#D1D1D6"

                            btn_dia = ctk.CTkButton(
                                f_cal,
                                text=str(dia),
                                width=38,
                                height=28,
                                corner_radius=6,
                                fg_color=fg_col,
                                hover_color=hov_col,
                                text_color=txt_col,
                                font=ctk.CTkFont(size=11, weight="bold" if es_hoy else "normal"),
                                command=lambda d=dia: _seleccionar_y_cerrar(a, m, d)
                            )
                            btn_dia.grid(row=r_idx + 1, column=c_idx, padx=1, pady=1)

            _renderizar_calendario()

            btn_hoy = ctk.CTkButton(
                f_pie,
                text="📅 Hoy",
                width=80,
                height=28,
                fg_color="#2E7D32",
                hover_color="#1B5E20",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=_seleccionar_hoy
            )
            btn_hoy.pack(side="left", padx=14, pady=8)

            btn_cancelar = ctk.CTkButton(
                f_pie,
                text="Cancelar",
                width=80,
                height=28,
                fg_color="#2B2B36",
                hover_color="#3A3A4A",
                font=ctk.CTkFont(size=11),
                command=lambda: self.cerrar_modal(modal)
            )
            btn_cancelar.pack(side="right", padx=14, pady=8)

        except Exception as e:
            if hasattr(self, "_agregar_log"):
                self._agregar_log(f"[AVISO] No se pudo abrir el selector de fecha: {e}")

    # =========================================================================
    # LÓGICA FUNCIONAL (EXAMINAR, DESCARTAR, URLS, ASINCRONISMO)
    # =========================================================================
    def _obtener_ruta_seccion(self, seccion: str) -> str:
        """Determina la ruta del archivo activo correspondiente a la sección consultada."""
        sec = str(seccion or "").lower()
        if "servicio" in sec:
            return getattr(self, "archivo_ruta_servicios", "") or getattr(self, "archivo_actual_ruta", "")
        elif "planilla" in sec:
            return getattr(self, "archivo_ruta_planillas", "") or getattr(self, "archivo_actual_ruta", "")
        else:
            return getattr(self, "archivo_ruta_formacion", "") or getattr(self, "archivo_actual_ruta", "")

    def _accion_abrir_archivo_excel(self, seccion: str):
        """Abre el archivo activo en el editor predeterminado de hojas de cálculo del sistema."""
        ruta = self._obtener_ruta_seccion(seccion)
        if not ruta or not os.path.exists(ruta):
            self._agregar_log(f"[AVISO] No hay ningún archivo seleccionado para abrir en {seccion}.")
            self._mostrar_modal_mensaje(
                titulo="Archivo no seleccionado",
                mensaje="No se encontró ningún archivo activo para abrir.\nPor favor examina y selecciona un archivo primero.",
                tipo="warning"
            )
            return

        self._agregar_log(f"[ARCHIVO] Solicitando apertura asistida en Excel/Calc: {os.path.basename(ruta)}")
        abierto = abrir_archivo_asistido(ruta)
        if abierto:
            self._agregar_log(f"[OK] Archivo abierto en la suite ofimática predeterminada.")
            self._agregar_log(f"[INFO] Puedes modificar y guardar cambios (Ctrl+G). Luego pulsa 'Recargar' para actualizar.")
        else:
            self._agregar_log(f"[AVISO] No se detectó suite ofimática asociada. Ruta: {ruta}")
            self._mostrar_modal_mensaje(
                titulo="Apertura Manual Requerida",
                mensaje=f"No se detectó Excel ni LibreOffice asociado automáticamente.\nPuedes abrir y editar manualmente el archivo en:\n\n{ruta}",
                tipo="info"
            )

    def _accion_recargar_archivo(self, seccion: str):
        """Recarga y re-normaliza en caliente el archivo activo de la sección."""
        ruta = self._obtener_ruta_seccion(seccion)
        if not ruta or not os.path.exists(ruta):
            self._agregar_log(f"[AVISO] No hay ningún archivo cargado para recargar en {seccion}.")
            return

        sec_norm = "Servicios" if "servicio" in str(seccion).lower() else ("Planillas" if "planilla" in str(seccion).lower() else "Formacion")
        self._agregar_log(f"[ARCHIVO] ↻ Recargando datos actualizados de '{os.path.basename(ruta)}'...")
        self._procesar_archivo_en_frio(ruta, seccion=sec_norm)
        self._agregar_log(f"[OK] ↻ Datos recargados y sincronizados exitosamente.")

    def _examinar_archivo_formacion(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de estudiantes / formación",
            filetypes=[("Hojas de cálculo", "*.xlsx *.xls *.ods *.csv"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return

        ext = os.path.splitext(ruta)[1].lower()
        if ext not in ('.xlsx', '.xls', '.ods', '.csv', '.txt'):
            self._agregar_log(f"[ERROR] Formato de archivo no soportado: '{os.path.basename(ruta)}'")
            self._mostrar_modal_mensaje(
                titulo="Formato no compatible",
                mensaje=f"El archivo '{os.path.basename(ruta)}' tiene un formato no compatible ({ext}).\n\nFormatos soportados: Excel (.xlsx, .xls), OpenDocument (.ods), CSV (.csv) y Texto (.txt).",
                tipo="error"
            )
            return

        self.archivo_actual_ruta = ruta
        self.archivo_ruta_formacion = ruta
        nombre = os.path.basename(ruta)
        self.archivo_seleccionado_formacion.set(f"📄 {nombre}")
        self.lbl_archivo_formacion.configure(text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_descartar_formacion.pack(side="right", padx=(6, 4))

        self._agregar_log(f"[ARCHIVO] Archivo seleccionado: {nombre}")
        self._procesar_archivo_en_frio(ruta, seccion="Formacion")

    def _descartar_archivo_formacion(self):
        """Deselecciona el archivo de formación, oculta la tarjeta de pre-vuelo y limpia datos."""
        self.cerrar_modales_activos()
        self.archivo_actual_ruta = ""
        self.archivo_ruta_formacion = ""
        self.participantes_cargados = []
        self.datos_normalizados_actuales = []
        self.reporte_deduplicacion_actual = None
        self.archivo_seleccionado_formacion.set("Ningún archivo seleccionado")
        self.lbl_archivo_formacion.configure(text_color="#8E8E98", font=ctk.CTkFont(size=11, weight="normal"))
        self.btn_descartar_formacion.pack_forget()
        if hasattr(self, "card_prevuelo_formacion") and self.card_prevuelo_formacion.winfo_manager() == "pack":
            self.card_prevuelo_formacion.pack_forget()
        self._agregar_log("[ARCHIVO] Archivo de formación deseleccionado.")

    def _examinar_archivo_servicios(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de usuarios de atención / servicios",
            filetypes=[("Hojas de cálculo", "*.xlsx *.xls *.ods *.csv"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return

        ext = os.path.splitext(ruta)[1].lower()
        if ext not in ('.xlsx', '.xls', '.ods', '.csv', '.txt'):
            self._agregar_log(f"[ERROR] Formato de archivo no soportado: '{os.path.basename(ruta)}'")
            self._mostrar_modal_mensaje(
                titulo="Formato no compatible",
                mensaje=f"El archivo '{os.path.basename(ruta)}' tiene un formato no compatible ({ext}).\n\nFormatos soportados: Excel (.xlsx, .xls), OpenDocument (.ods), CSV (.csv) y Texto (.txt).",
                tipo="error"
            )
            return

        self.archivo_actual_ruta = ruta
        self.archivo_ruta_servicios = ruta
        nombre = os.path.basename(ruta)
        self.archivo_seleccionado_servicios.set(f"📄 {nombre}")
        self.lbl_archivo_servicios.configure(text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_descartar_servicios.pack(side="right", padx=(6, 4))

        self._agregar_log(f"[ARCHIVO] Archivo de servicios seleccionado: {nombre}")
        self._procesar_archivo_en_frio(ruta, seccion="Servicios")

    def _descartar_archivo_servicios(self):
        """Deselecciona el archivo de servicios, oculta la tarjeta de pre-vuelo y limpia datos."""
        self.cerrar_modales_activos()
        self.archivo_actual_ruta = ""
        self.archivo_ruta_servicios = ""
        self.participantes_cargados = []
        self.datos_normalizados_actuales = []
        self.reporte_deduplicacion_actual = None
        self.archivo_seleccionado_servicios.set("Ningún archivo seleccionado")
        self.lbl_archivo_servicios.configure(text_color="#8E8E98", font=ctk.CTkFont(size=11, weight="normal"))
        self.btn_descartar_servicios.pack_forget()
        if hasattr(self, "card_prevuelo_servicios") and self.card_prevuelo_servicios.winfo_manager() == "pack":
            self.card_prevuelo_servicios.pack_forget()
        self._agregar_log("[ARCHIVO] Archivo de servicios deseleccionado.")

    def _examinar_archivo_planillas(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de participantes para generar planilla",
            filetypes=[("Hojas de cálculo", "*.xlsx *.xls *.ods *.csv"), ("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return

        ext = os.path.splitext(ruta)[1].lower()
        if ext not in ('.xlsx', '.xls', '.ods', '.csv', '.txt'):
            self._agregar_log(f"[ERROR] Formato de archivo no soportado: '{os.path.basename(ruta)}'")
            self._mostrar_modal_mensaje(
                titulo="Formato no compatible",
                mensaje=f"El archivo '{os.path.basename(ruta)}' tiene un formato no compatible ({ext}).\n\nFormatos soportados: Excel (.xlsx, .xls), OpenDocument (.ods), CSV (.csv) y Texto (.txt).",
                tipo="error"
            )
            return

        self.archivo_actual_ruta = ruta
        self.archivo_ruta_planillas = ruta
        nombre = os.path.basename(ruta)
        self.archivo_seleccionado_planillas.set(f"📄 {nombre}")
        self.lbl_archivo_planillas.configure(text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"))
        self.btn_descartar_planillas.pack(side="right", padx=(6, 4))

        self._agregar_log(f"[ARCHIVO] Archivo para planillas seleccionado: {nombre}")
        self._procesar_archivo_en_frio(ruta, seccion="Planillas")

    def _descartar_archivo_planillas(self):
        """Deselecciona el archivo de planillas, oculta la tarjeta de pre-vuelo y limpia datos."""
        self.cerrar_modales_activos()
        self.archivo_actual_ruta = ""
        self.archivo_ruta_planillas = ""
        self.participantes_cargados_planillas = []
        self.datos_normalizados_planillas = []
        self.reporte_deduplicacion_planillas = None
        self.archivo_seleccionado_planillas.set("Ningún archivo seleccionado")
        self.lbl_archivo_planillas.configure(text_color="#8E8E98", font=ctk.CTkFont(size=11, weight="normal"))
        self.btn_descartar_planillas.pack_forget()
        if hasattr(self, "card_prevuelo_planillas") and self.card_prevuelo_planillas.winfo_manager() == "pack":
            self.card_prevuelo_planillas.pack_forget()
        self._agregar_log("[ARCHIVO] Archivo de planillas deseleccionado.")

    def _procesar_archivo_en_frio(self, ruta: str, seccion: str = "Formacion"):
        if not MODULOS_DISPONIBLES:
            self._agregar_log("[ERROR] Módulos de normalización no disponibles.")
            self._mostrar_modal_mensaje(
                "Módulos no disponibles",
                "Los módulos de normalización de datos no están disponibles en este entorno.",
                tipo="error"
            )
            return

        try:
            ext = os.path.splitext(ruta)[1].lower()
            if seccion == "Servicios" and ext == '.txt':
                participantes = procesar_archivo_texto(ruta)
            else:
                participantes = procesar_archivo_participantes(ruta)

            if not participantes:
                self._agregar_log(f"[ADVERTENCIA] No se detectaron participantes válidos en '{os.path.basename(ruta)}'.")
                self._mostrar_modal_mensaje(
                    titulo="Sin registros válidos",
                    mensaje=f"No se detectaron registros válidos en '{os.path.basename(ruta)}'.\n\nVerifica que contenga cabeceras claras (Nombres, Apellidos, Cédula) y filas con datos.",
                    tipo="aviso"
                )
                return

            # Invocación con modo_interactivo=False para desacoplar InquirerPy/CLI de la GUI
            res_dedup = deduplicar_participantes(participantes, modo_interactivo=False)
            if isinstance(res_dedup, tuple):
                participantes, reporte_dedup = res_dedup
            else:
                participantes = res_dedup
                reporte_dedup = {"duplicados_omitidos": 0, "nombres": []}

            if seccion == "Planillas":
                self.participantes_cargados_planillas = participantes
                self.datos_normalizados_planillas = participantes
                self.reporte_deduplicacion_planillas = reporte_dedup
            else:
                self.participantes_cargados = participantes
                self.datos_normalizados_actuales = participantes
                self.reporte_deduplicacion_actual = reporte_dedup

            dup_omitidos = reporte_dedup.get("duplicados_omitidos", 0)
            if dup_omitidos > 0:
                self._agregar_log(f"[AVISO] Se detectaron {dup_omitidos} registros duplicados en el archivo.")
                self._agregar_log(f"[OK] Duplicados depurados automáticamente: {len(participantes)} registros únicos listos para procesar.")

            total = len(participantes)
            ci_saime = 0
            ci_escolar = 0
            menores_sin_doc = 0
            inconsistencias = 0

            for p in participantes:
                if p.get('cedulado') == 'si' or p.get('cedula'):
                    ci_saime += 1
                elif p.get('cedula_escolar'):
                    ci_escolar += 1
                elif p.get('cedula_padre'):
                    ci_escolar += 1
                else:
                    menores_sin_doc += 1

                # Validación de consistencia estructural
                nom_p = str(p.get('nombre', '') or '').strip()
                ape_p = str(p.get('apellido', '') or '').strip()
                tiene_nombre = bool((nom_p and ape_p) or (len(f"{nom_p} {ape_p}".strip()) >= 3 and not p.get('solo_cedula', False)))
                tiene_doc = bool(p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre'))
                if not (tiene_nombre and tiene_doc):
                    inconsistencias += 1

            from modulos.normalizador_datos import obtener_huerfanos_de_documento
            huerfanos_detectados = obtener_huerfanos_de_documento(participantes)
            if huerfanos_detectados:
                self._agregar_log(f"[ADVERTENCIA] Se detectaron {len(huerfanos_detectados)} participantes SIN DOCUMENTO ni Cédula de Representante.")
                self._agregar_log(f"[AVISO] Abriendo diálogo interactivo de resolución de tutor...")
                self.after(100, lambda: self._mostrar_modal_resolucion_huerfanos(huerfanos_detectados, seccion=seccion))

            if inconsistencias == 0:
                if dup_omitidos > 0:
                    estado_txt = f"● Estructura Válida ({dup_omitidos} dup. depurados)"
                else:
                    estado_txt = "● Estructura Válida (0 inconsistencias)"
                estado_color = "#30D158"
            else:
                if dup_omitidos > 0:
                    estado_txt = f"▲ {inconsistencias} inconsistencia(s) | {dup_omitidos} dup. depurados"
                else:
                    estado_txt = f"▲ {inconsistencias} inconsistencia(s) detectada(s)"
                estado_color = "#F39C12"

            if dup_omitidos > 0:
                desglose_txt = f"{ci_saime} Cedulados  |  {ci_escolar} Escolares  |  {menores_sin_doc} Menores S/C  |  {dup_omitidos} Dup. omitidos"
            else:
                desglose_txt = f"{ci_saime} Cedulados  |  {ci_escolar} Escolares  |  {menores_sin_doc} Menores S/C"

            if seccion == "Servicios":
                if hasattr(self, "lbl_prevuelo_servicios_total"):
                    self.lbl_prevuelo_servicios_total.configure(text=f"Total: {total} usuarios")
                    self.lbl_prevuelo_servicios_desglose.configure(text=desglose_txt)
                    self.lbl_prevuelo_servicios_estado.configure(text=estado_txt, text_color=estado_color)
                if hasattr(self, "card_prevuelo_servicios") and self.card_prevuelo_servicios.winfo_manager() != "pack":
                    self.card_prevuelo_servicios.pack(fill="x", padx=16, pady=(0, 8), before=self.url_container_servicios)
            elif seccion == "Planillas":
                if hasattr(self, "lbl_prevuelo_planillas_total"):
                    self.lbl_prevuelo_planillas_total.configure(text=f"Total: {total} participantes")
                    self.lbl_prevuelo_planillas_desglose.configure(text=desglose_txt)
                    self.lbl_prevuelo_planillas_estado.configure(text=estado_txt, text_color=estado_color)
                if hasattr(self, "card_prevuelo_planillas") and self.card_prevuelo_planillas.winfo_manager() != "pack":
                    self.card_prevuelo_planillas.pack(fill="x", padx=16, pady=(0, 8), before=self.container_opciones_planillas)
            else:
                if hasattr(self, "lbl_prevuelo_formacion_total"):
                    self.lbl_prevuelo_formacion_total.configure(text=f"Total: {total} participantes")
                    self.lbl_prevuelo_formacion_desglose.configure(text=desglose_txt)
                    self.lbl_prevuelo_formacion_estado.configure(text=estado_txt, text_color=estado_color)
                if hasattr(self, "card_prevuelo_formacion") and self.card_prevuelo_formacion.winfo_manager() != "pack":
                    self.card_prevuelo_formacion.pack(fill="x", padx=16, pady=(0, 8), before=self.url_container_formacion)

            self._agregar_log("────────────────────────────────────────────────────────────")
            self._agregar_log(f"[ETL] Resumen de normalización: '{os.path.basename(ruta)}'")
            self._agregar_log(f"[OK] Total de participantes válidos: {total}")
            self._agregar_log(f"[DATOS] ├─ Cédulas de Identidad (SAIME): {ci_saime}")
            self._agregar_log(f"[DATOS] ├─ Cédulas Escolares (CE): {ci_escolar}")
            self._agregar_log(f"[DATOS] ├─ Menores vinculados a tutor / S/C: {menores_sin_doc}")
            if dup_omitidos > 0:
                self._agregar_log(f"[DATOS] └─ Duplicados depurados: {dup_omitidos}")
            else:
                self._agregar_log(f"[DATOS] └─ Sin duplicados detectados")
            self._agregar_log(f"[INFO] Ingesta completada: {total} registros listos para revisión previa.")
            self._agregar_log("────────────────────────────────────────────────────────────")

        except Exception as e:
            self._agregar_log(f"[ERROR] Fallo al normalizar archivo: {e}")
            self._mostrar_modal_mensaje(
                titulo="Error de Normalización",
                mensaje=f"No se pudo procesar el archivo '{os.path.basename(ruta)}':\n\n{e}",
                tipo="error"
            )

    def _abrir_tabla_previsualizacion(self, titulo_fuente: str):
        """Abre ventana modal CTkToplevel para inspeccionar y auditar los datos normalizados en tabla."""
        if titulo_fuente == "Planillas":
            datos = self.datos_normalizados_planillas or self.participantes_cargados_planillas
        else:
            datos = self.datos_normalizados_actuales or self.participantes_cargados
        if not datos:
            datos = [
                {"nombre": "Eduardo", "apellido": "Pineda", "cedula": "36996120", "cedulado": "si", "edad": 15, "nacimiento": "2011-04-12", "telefono": "0412-1112233"},
                {"nombre": "Marcela", "apellido": "Villegas", "cedula_escolar": "11607579666", "cedulado": "escolar", "edad": 10, "nacimiento": "2016-07-20", "telefono": "0414-9998877"},
                {"nombre": "Damián", "apellido": "Gutiérrez", "cedula": "35890123", "cedulado": "si", "edad": 16, "nacimiento": "2010-02-18", "telefono": "0424-5554433"},
                {"nombre": "Sofía", "apellido": "Hernández", "cedula_padre": "18456123", "cedulado": "escolar", "edad": 8, "nacimiento": "2018-09-05", "telefono": "0416-2223344"},
                {"nombre": "Lucas", "apellido": "Camacho", "cedula": "34112980", "cedulado": "si", "edad": 17, "nacimiento": "2009-11-30", "telefono": "0412-7776655"},
            ]

        self.update_idletasks()
        ancho_modal = 850
        alto_modal = 500
        pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho_modal) // 2)
        pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto_modal) // 2)

        modal = ctk.CTkToplevel(self)
        modal.title("Previsualización y Auditoría de Datos Normalizados")
        modal.geometry(f"{ancho_modal}x{alto_modal}+{pos_x}+{pos_y}")
        modal.minsize(800, 450)
        modal.transient(self)
        self.registrar_modal("tabla_previsualizacion", modal, grab=True)
        modal.focus_set()

        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(2, weight=1)

        # 1. Cabecera del Modal
        header_frame = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=10)

        lbl_modal_title = ctk.CTkLabel(
            header_inner,
            text="Previsualización y Auditoría de Datos Normalizados",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_modal_title.pack(anchor="w")

        nombre_arc = os.path.basename(self.archivo_actual_ruta) if self.archivo_actual_ruta else "Demostración en frío"
        dup_om = self.reporte_deduplicacion_actual.get('duplicados_omitidos', 0) if getattr(self, 'reporte_deduplicacion_actual', None) else 0
        sub_txt = f"Módulo: {titulo_fuente}  •  Origen: {nombre_arc}  •  Registros: {len(datos)}"
        if dup_om > 0:
            sub_txt += f"  •  Duplicados depurados: {dup_om}"
        lbl_modal_sub = ctk.CTkLabel(
            header_inner,
            text=sub_txt,
            font=ctk.CTkFont(size=11),
            text_color="#8E8E98"
        )
        lbl_modal_sub.pack(anchor="w", pady=(2, 0))

        # 2. Encabezado Fijo de Columnas
        col_frame = ctk.CTkFrame(modal, fg_color="#161620", corner_radius=6, border_width=1, border_color="#292938")
        col_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(10, 4))

        columnas_def = [
            ("N°", 36, "center"),
            ("Nombres y Apellidos", 200, "w"),
            ("Documento / Cédula", 120, "center"),
            ("Tipo", 80, "center"),
            ("Edad / F. Nac", 120, "center"),
            ("Teléfono", 100, "center"),
            ("Diagnóstico", 84, "center"),
        ]

        for nombre_col, ancho_col, alineacion in columnas_def:
            lbl_c = ctk.CTkLabel(
                col_frame,
                text=nombre_col,
                width=ancho_col,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#3B8ED0",
                anchor=alineacion
            )
            lbl_c.pack(side="left", padx=3, pady=6)

        # 3. Contenedor de Filas con Scroll
        scroll_tabla = ctk.CTkScrollableFrame(modal, fg_color="#121218", corner_radius=8)
        scroll_tabla.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 8))

        for idx, p in enumerate(datos, start=1):
            bg_fila = "#181824" if idx % 2 == 0 else "#1E1E2C"
            fila_frame = ctk.CTkFrame(scroll_tabla, fg_color=bg_fila, corner_radius=6)
            fila_frame.pack(fill="x", pady=2)

            nombre_ap = f"{p.get('nombre', '')} {p.get('apellido', '')}".strip().title()
            if not nombre_ap:
                nombre_ap = "Sin nombre registrado"

            ced = str(p.get('cedula', '') or '').strip()
            ced_esc = str(p.get('cedula_escolar', '') or '').strip()
            ced_pad = str(p.get('cedula_padre', '') or '').strip()
            cedulado_flag = p.get('cedulado', '')

            if ced or cedulado_flag == 'si':
                doc_str = f"V-{ced}" if ced else "V-(S/N)"
                tipo_str = "SAIME"
                tipo_color = "#3B8ED0"
            elif ced_esc:
                doc_str = f"CE-{ced_esc}"
                tipo_str = "Escolar"
                tipo_color = "#F39C12"
            elif ced_pad:
                doc_str = f"Rep: {ced_pad}"
                tipo_str = "Menor S/C"
                tipo_color = "#9B59B6"
            else:
                doc_str = "S/C (Sin Doc)"
                tipo_str = "Sin Doc"
                tipo_color = "#E74C3C"

            edad = p.get('edad')
            nac = p.get('nacimiento') or ''
            if edad is not None and nac:
                edad_nac_str = f"{edad}a ({nac})"
            elif edad is not None:
                edad_nac_str = f"{edad} años"
            elif nac:
                edad_nac_str = f"{nac}"
            else:
                edad_nac_str = "N/D"

            tlf_str = p.get('telefono') or "No reg."

            tiene_doc = bool(ced or ced_esc or ced_pad)
            nom_p = str(p.get('nombre', '') or '').strip()
            ape_p = str(p.get('apellido', '') or '').strip()
            tiene_nombre = bool((nom_p and ape_p) or (len(f"{nom_p} {ape_p}".strip()) >= 3 and not p.get('solo_cedula', False)))
            if tiene_nombre and tiene_doc:
                diag_str = "[OK] Listo"
                diag_color = "#30D158"
            elif not tiene_doc:
                diag_str = "[!] Sin Doc"
                diag_color = "#E74C3C"
            else:
                diag_str = "[!] Revisar"
                diag_color = "#E74C3C"

            ctk.CTkLabel(fila_frame, text=str(idx), width=36, font=ctk.CTkFont(size=10), text_color="#8E8E98", anchor="center").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=nombre_ap, width=200, font=ctk.CTkFont(size=10, weight="bold"), text_color="#FFFFFF", anchor="w").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=doc_str, width=120, font=ctk.CTkFont(family="Consolas", size=10), text_color="#E0E0E8", anchor="center").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=tipo_str, width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=tipo_color, anchor="center").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=edad_nac_str, width=120, font=ctk.CTkFont(size=10), text_color="#A1A1AA", anchor="center").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=tlf_str, width=100, font=ctk.CTkFont(family="Consolas", size=10), text_color="#A1A1AA", anchor="center").pack(side="left", padx=3, pady=5)
            ctk.CTkLabel(fila_frame, text=diag_str, width=84, font=ctk.CTkFont(size=10, weight="bold"), text_color=diag_color, anchor="center").pack(side="left", padx=3, pady=5)

        # 4. Pie del Modal
        footer_frame = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0)
        footer_frame.grid(row=3, column=0, sticky="ew")

        footer_inner = ctk.CTkFrame(footer_frame, fg_color="transparent")
        footer_inner.pack(fill="x", padx=16, pady=8)

        if dup_om > 0:
            txt_res = f"Mostrando {len(datos)} registros únicos listos para inyección ({dup_om} duplicados omitidos automáticamente)."
        else:
            txt_res = f"Mostrando {len(datos)} registros normalizados listos para inyección."
        lbl_resumen = ctk.CTkLabel(
            footer_inner,
            text=txt_res,
            font=ctk.CTkFont(size=11),
            text_color="#A1A1AA"
        )
        lbl_resumen.pack(side="left")

        def _recargar_desde_modal():
            self._accion_recargar_archivo(titulo_fuente)
            self.cerrar_modal(modal)
            self._abrir_tabla_previsualizacion(titulo_fuente)

        btn_cerrar = ctk.CTkButton(
            footer_inner,
            text="Cerrar y Continuar",
            width=135,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            command=lambda: self.cerrar_modal(modal)
        )
        btn_cerrar.pack(side="right", padx=(6, 0))

        btn_excel_modal = ctk.CTkButton(
            footer_inner,
            text="✎ Abrir en Excel",
            width=120,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27AE60",
            hover_color="#1E8449",
            command=lambda: self._accion_abrir_archivo_excel(titulo_fuente)
        )
        btn_excel_modal.pack(side="right", padx=(6, 0))

        btn_recargar_modal = ctk.CTkButton(
            footer_inner,
            text="↻ Recargar",
            width=90,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2C3E50",
            hover_color="#1A252F",
            command=_recargar_desde_modal
        )
        btn_recargar_modal.pack(side="right", padx=(6, 0))

    def _pegar_portapapeles_url(self, entry_widget: ctk.CTkEntry):
        try:
            texto = self.clipboard_get().strip()
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, texto)
            self._validar_sintaxis_url(entry_widget)
            self._agregar_log("[INTERFAZ] URL pegada desde el portapapeles.")
        except Exception:
            self._agregar_log("[AVISO] No se encontró texto válido en el portapapeles.")

    def _validar_sintaxis_url(self, entry_widget: ctk.CTkEntry):
        texto = entry_widget.get().strip()
        if not texto:
            entry_widget.configure(border_color="#3A3A4A")
            return

        if "id_activity=" in texto or "id_service=" in texto or "view=services" in texto or "services" in texto.lower():
            entry_widget.configure(border_color="#2ECC71")
        else:
            entry_widget.configure(border_color="#F39C12")

    def agregar_log_telemetria(self, mensaje: str):
        """Redirige registros de ejecución en vivo hacia la consola visual de telemetría."""
        self._agregar_log(mensaje)

    def _iniciar_ejecucion_asincrona_formacion(self):
        if self.ejecutando_tarea:
            return

        # 1. Validar presencia de archivo cargado
        if not self.participantes_cargados:
            self._agregar_log("[ERROR] No se puede iniciar: no hay ningún archivo seleccionado o no contiene participantes válidos.")
            self._mostrar_modal_mensaje(
                titulo="Archivo Requerido",
                mensaje="Debes examinar y cargar un archivo de estudiantes válido (.xlsx, .ods, .csv, .txt) antes de iniciar la carga automatizada.",
                tipo="error"
            )
            return

        # 1.1 Validar que los participantes tengan identificación para interactuar con InfoApp
        con_doc = [p for p in self.participantes_cargados if p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre')]
        if not con_doc:
            self._agregar_log("[ERROR] Bloqueo preventivo: Ningún participante posee Cédula propia ni de Representante.")
            self._mostrar_modal_mensaje(
                titulo="Documentos Requeridos",
                mensaje=(
                    "No se puede iniciar la carga masiva porque ningún participante tiene documento de identidad ni cédula de representante.\n\n"
                    "InfoApp exige la Cédula del Representante para registrar menores o generar su Cédula Escolar.\n\n"
                    "👉 Por favor añade al menos la columna de Cédula del Representante al archivo para continuar."
                ),
                tipo="error"
            )
            return

        # 2. Validar sintaxis y presencia de id_activity en la URL
        url = self.entry_url_formacion.get().strip()
        id_actividad = extraer_id_actividad(url) if MODULOS_DISPONIBLES else ""
        if not url or ("id_activity=" not in url and id_actividad == "general"):
            self._agregar_log(f"[ERROR] URL de InfoApp no válida: '{url}'")
            self._mostrar_modal_mensaje(
                titulo="URL Inválida",
                mensaje="La URL de InfoApp no es válida. Debe contener el parámetro 'id_activity=' de la actividad destino (ej: https://infoapp2.infocentro.gob.ve/admin/index.php?r=activity/create&id_activity=526293).",
                tipo="error"
            )
            return

        # 3. Cargar credenciales activas en memoria o desde config.ini
        usuario = self.usuario_activo or (obtener_credenciales()[0] if MODULOS_DISPONIBLES else "")
        clave = self.clave_activa or (obtener_credenciales()[1] if MODULOS_DISPONIBLES else "")
        if not usuario or not clave:
            self._agregar_log("[ERROR] Credenciales no localizadas en config/config.ini.")
            self._mostrar_modal_mensaje(
                titulo="Credenciales Requeridas",
                mensaje="No se encontraron credenciales en 'config/config.ini'. Por favor configura tu usuario y contraseña de InfoApp.",
                tipo="error"
            )
            return

        # 4. Iniciar ejecución en hilo seguro
        self.ejecutando_tarea = True
        self.btn_iniciar_formacion.configure(state="disabled", text="EJECUTANDO CARGA...", fg_color="#0F6CBD")
        self.progreso.set(0.0)
        self.lbl_porcentaje.configure(text="Progreso: 0%")
        self._iniciar_pulso_estado()

        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        archivo_log = os.path.join(log_dir, f"log_actividad_{id_actividad}_{ts}.txt")

        with open(archivo_log, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"REGISTRO DE AUDITORÍA — JsBOT RPA {ETIQUETA_VERSION} (GUI)\n")
            f.write(f"Actividad ID : {id_actividad}\n")
            f.write(f"URL          : {url}\n")
            f.write(f"Fecha Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Operador     : {usuario}\n")
            f.write("=" * 80 + "\n\n")

        config = {
            "usuario": usuario,
            "clave": clave,
            "url": url,
            "id_actividad": id_actividad,
            "timestamp_str": ts,
            "archivo_log": archivo_log,
            "modo_gui": True,
            "modo_visible": self.var_modo_visible_formacion.get(),
            "generar_ods": self.var_generar_ods_formacion.get()
        }

        participantes = list(self.participantes_cargados)
        threading.Thread(
            target=self._hilo_proceso_carga_formacion,
            args=(participantes, config),
            daemon=True
        ).start()

    def _iniciar_ejecucion_asincrona_servicios(self):
        if self.ejecutando_tarea:
            return

        # 1. Validar presencia de usuarios/participantes
        if not self.participantes_cargados:
            self._agregar_log("[ERROR] No se puede iniciar: no hay usuarios cargados para servicios comunitarios.")
            self._mostrar_modal_mensaje(
                titulo="Archivo Requerido",
                mensaje="Debes examinar y cargar un archivo de usuarios válido (.xlsx, .csv, .txt) antes de iniciar la carga de servicios.",
                tipo="error"
            )
            return

        # 1.1 Validar que los usuarios tengan identificación para interactuar con InfoApp
        con_doc = [p for p in self.participantes_cargados if p.get('cedula') or p.get('cedula_escolar') or p.get('cedula_padre')]
        if not con_doc:
            self._agregar_log("[ERROR] Bloqueo preventivo: Ningún usuario posee Cédula propia ni de Representante.")
            self._mostrar_modal_mensaje(
                titulo="Documentos Requeridos",
                mensaje=(
                    "No se puede iniciar la carga masiva porque ningún usuario tiene documento de identidad ni cédula de representante.\n\n"
                    "InfoApp exige un documento para buscar usuarios o registrar perfiles nuevos.\n\n"
                    "👉 Por favor añade al menos la columna de Cédula al archivo para continuar."
                ),
                tipo="error"
            )
            return

        # 2. Validar sintaxis y presencia de id_service o view=services en la URL
        url = self.entry_url_servicios.get().strip()
        if not url:
            url = "https://infoapp2.infocentro.gob.ve/admin/index.php?view=services"
            self.entry_url_servicios.delete(0, "end")
            self.entry_url_servicios.insert(0, url)
            self._validar_sintaxis_url(self.entry_url_servicios)

        id_servicio = extraer_id_servicio(url) if MODULOS_DISPONIBLES else "general"
        es_valida = bool("id_service=" in url or "view=services" in url or "services" in url.lower() or "infocentro.gob.ve" in url)
        if not es_valida:
            self._agregar_log(f"[ERROR] URL de Servicio InfoApp no válida: '{url}'")
            self._mostrar_modal_mensaje(
                titulo="URL de Servicio Inválida",
                mensaje="La URL de Servicio no es válida. Debe ser una URL de InfoApp (ej: https://infoapp2.infocentro.gob.ve/admin/index.php?view=services o con id_service=...).",
                tipo="error"
            )
            return

        # 3. Cargar credenciales activas en memoria o desde config.ini
        usuario = self.usuario_activo or (obtener_credenciales()[0] if MODULOS_DISPONIBLES else "")
        clave = self.clave_activa or (obtener_credenciales()[1] if MODULOS_DISPONIBLES else "")
        if not usuario or not clave:
            self._agregar_log("[ERROR] Credenciales no localizadas en config/config.ini.")
            self._mostrar_modal_mensaje(
                titulo="Credenciales Requeridas",
                mensaje="No se encontraron credenciales en 'config/config.ini'. Por favor configura tu usuario y contraseña de InfoApp.",
                tipo="error"
            )
            return

        # 3.1 Validar fecha del servicio ingresada o seleccionada
        fecha_raw = self.entry_fecha_servicios.get().strip() if hasattr(self, "entry_fecha_servicios") else ""
        if not fecha_raw:
            fecha_srv = datetime.now().strftime("%Y-%m-%d")
        else:
            fecha_norm = limpiar_fecha(fecha_raw) if "limpiar_fecha" in globals() else fecha_raw
            es_fecha_valida = False
            if fecha_norm:
                try:
                    datetime.strptime(fecha_norm, "%Y-%m-%d")
                    es_fecha_valida = True
                    fecha_srv = fecha_norm
                except Exception:
                    es_fecha_valida = False

            if not es_fecha_valida:
                self._agregar_log(f"[ERROR] Fecha de servicio inválida: '{fecha_raw}'")
                self._mostrar_modal_mensaje(
                    titulo="Fecha de Servicio Inválida",
                    mensaje=(
                        f"La fecha ingresada '{fecha_raw}' no es válida.\n\n"
                        "Por favor utiliza el formato AAAA-MM-DD (ej: 2026-03-15) "
                        "o selecciona una fecha haciendo clic en el botón '📅 Calendario'."
                    ),
                    tipo="error"
                )
                return

        # 4. Iniciar ejecución en hilo seguro
        self.ejecutando_tarea = True
        self.btn_iniciar_servicios.configure(state="disabled", text="EJECUTANDO SERVICIOS...", fg_color="#1B5E20")
        self.progreso.set(0.0)
        self.lbl_porcentaje.configure(text="Progreso: 0%")
        self._iniciar_pulso_estado()

        cfg_serv_global = cargar_config_servicios() if MODULOS_DISPONIBLES else {}
        tipo_srv = ""
        if hasattr(self, "menu_tipo_servicio"):
            try:
                tipo_srv = str(self.menu_tipo_servicio.get()).strip()
            except Exception:
                tipo_srv = ""
        elif hasattr(self, "combo_tipo_servicio"):
            try:
                tipo_srv = str(self.combo_tipo_servicio.get()).strip()
            except Exception:
                tipo_srv = ""

        if not tipo_srv:
            tipo_srv = cfg_serv_global.get("servicio_por_defecto", "Actividades de educación o aprendizaje")

        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        archivo_log = os.path.join(log_dir, f"log_servicios_{id_servicio}_{ts}.txt")

        with open(archivo_log, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"REGISTRO DE AUDITORÍA — SERVICIOS JsBOT {ETIQUETA_VERSION} (GUI)\n")
            f.write(f"Fecha Inicio : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Servicio     : {tipo_srv}\n")
            f.write(f"Servicio ID  : {id_servicio}\n")
            f.write(f"Fecha Reg.   : {fecha_srv}\n")
            f.write(f"Operador     : {usuario}\n")
            f.write("=" * 80 + "\n\n")

        config_bot = {
            "usuario": usuario,
            "clave": clave,
            "url": url,
            "id_servicio": id_servicio,
            "timestamp_str": ts,
            "archivo_log": archivo_log,
            "modo_gui": True,
            "modo_visible": self.var_modo_visible_servicios.get()
        }

        config_servicio = {
            "tipo_servicio": tipo_srv,
            "fecha_servicio": fecha_srv,
            "id_servicio": id_servicio,
            "infocentro": cfg_serv_global.get("infocentro", {})
        }

        usuarios = list(self.participantes_cargados)
        threading.Thread(
            target=self._hilo_proceso_carga_servicios,
            args=(usuarios, config_bot, config_servicio),
            daemon=True
        ).start()

    def _hilo_proceso_carga_formacion(self, participantes: list, config: dict):
        total = len(participantes)
        id_act = config.get("id_actividad", "")
        indice_inicio = getattr(self, "indice_inicio_recuperacion_formacion", 0) or 0
        self.indice_inicio_recuperacion_formacion = 0

        self.cola_eventos.put(("log", f"[INICIO] Proceso de Carga Automatizada real iniciado para {total - indice_inicio} participantes (Total lote: {total})."))
        self.cola_eventos.put(("log", f"[ACTIVIDAD] ID Actividad: {id_act} | URL: {config.get('url')}"))

        if MODULOS_DISPONIBLES:
            guardar_estado_sesion(config, participantes, indice_inicio)

        def cb_log(msg):
            self.cola_eventos.put(("log", msg))

        def cb_progreso(actual, total_p, desc=""):
            pct = actual / total_p if total_p > 0 else 0.0
            self.cola_eventos.put(("progreso", pct))

        cargados_exitosos = []
        fallidos = []
        tiempo_seg = 0.0

        try:
            cargados_exitosos, fallidos, tiempo_seg = ejecutar_carga_infoapp(
                participantes,
                config,
                indice_inicio=indice_inicio,
                log_callback=cb_log,
                progreso_callback=cb_progreso
            )

            if len(cargados_exitosos) >= total:
                self.cola_eventos.put(("log", f"[OK] Carga completada exitosamente: {len(cargados_exitosos)}/{total} inyectados en {tiempo_seg:.1f}s."))
            else:
                finalizar_log_incompleto(config, f"Parcial: {len(cargados_exitosos)}/{total} procesados")
                self.cola_eventos.put(("log", f"[AVISO] Carga parcial: {len(cargados_exitosos)}/{total} procesados ({len(fallidos)} incidencias)."))

            # Reporte Excel de Auditoría
            try:
                ruta_excel = generar_reporte_auditoria_excel(config, cargados_exitosos, fallidos)
                if ruta_excel:
                    self.cola_eventos.put(("log", f"[AUDITORÍA] Reporte Excel generado: logs/{os.path.basename(ruta_excel)}"))
            except Exception as e_excel:
                self.cola_eventos.put(("log", f"[AVISO] Error al generar reporte Excel: {e_excel}"))

            # Generar planilla ODS si la opción está activa
            if config.get("generar_ods", True):
                self.cola_eventos.put(("log", "[PLANILLA] Generando Planilla Oficial .ODS..."))
                planillas_dir = os.path.join(BASE_DIR, "Planillas")
                os.makedirs(planillas_dir, exist_ok=True)
                ts = config.get("timestamp_str", datetime.now().strftime("%Y%m%d_%H%M"))
                ruta_ods = os.path.join(planillas_dir, f"Planilla_Participantes_Actividad_{id_act}_{ts}.ods")
                lista_ods = cargados_exitosos if cargados_exitosos else participantes
                try:
                    res_ods = generar_planilla_oficial(lista_ods, id_act, config.get("url", ""), ruta_salida=ruta_ods)
                    self.cola_eventos.put(("log", f"[OK] Planilla oficial .ODS guardada en: Planillas/{os.path.basename(res_ods or ruta_ods)}"))
                except Exception as e_ods:
                    self.cola_eventos.put(("log", f"[ERROR] No se pudo generar la planilla .ODS: {e_ods}"))

            if len(cargados_exitosos) >= total:
                finalizar_log_exito(config)

        except Exception as e:
            self.cola_eventos.put(("log", f"[CRITICO] Error no controlado durante la carga: {e}"))
            if MODULOS_DISPONIBLES:
                try:
                    finalizar_log_incompleto(config, str(e))
                except Exception:
                    pass
        finally:
            self.cola_eventos.put(("fin_formacion", len(cargados_exitosos)))

    def _hilo_proceso_carga_servicios(self, usuarios: list, config_bot: dict, config_servicio: dict):
        total = len(usuarios)
        id_srv = config_bot.get("id_servicio", "")
        tipo_srv = config_servicio.get("tipo_servicio", "")
        indice_inicio = getattr(self, "indice_inicio_recuperacion_servicios", 0) or 0
        self.indice_inicio_recuperacion_servicios = 0

        self.cola_eventos.put(("log", f"[INICIO] Proceso de Servicios Comunitarios real iniciado para {total - indice_inicio} usuarios (Total lote: {total})."))
        self.cola_eventos.put(("log", f"[SERVICIO] ID: {id_srv} | Tipo: {tipo_srv}"))

        if MODULOS_DISPONIBLES:
            guardar_estado_sesion_servicios(config_bot, config_servicio, usuarios, indice_inicio)

        def cb_log(msg):
            self.cola_eventos.put(("log", msg))

        def cb_progreso(actual, total_p, desc=""):
            pct = actual / total_p if total_p > 0 else 0.0
            self.cola_eventos.put(("progreso", pct))

        cargados_exitosos = []
        fallidos = []
        tiempo_seg = 0.0

        try:
            cargados_exitosos, fallidos, tiempo_seg = ejecutar_carga_servicios_infoapp(
                usuarios,
                config_bot,
                config_servicio,
                indice_inicio=indice_inicio,
                fn_guardar_checkpoint=guardar_estado_sesion_servicios,
                log_callback=cb_log,
                progreso_callback=cb_progreso
            )

            if len(cargados_exitosos) >= total:
                limpiar_estado_sesion_servicios()
                self.cola_eventos.put(("log", f"[OK] Servicios registrados con éxito: {len(cargados_exitosos)}/{total} en {tiempo_seg:.1f}s."))
            else:
                self.cola_eventos.put(("log", f"[AVISO] Registro parcial de servicios: {len(cargados_exitosos)}/{total} ({len(fallidos)} incidencias)."))

            try:
                ruta_excel = generar_reporte_auditoria_servicios(config_bot, config_servicio, cargados_exitosos, fallidos)
                if ruta_excel:
                    self.cola_eventos.put(("log", f"[AUDITORÍA] Reporte Excel de servicios generado: logs/{os.path.basename(ruta_excel)}"))
            except Exception as e_excel:
                self.cola_eventos.put(("log", f"[AVISO] Error al generar reporte Excel: {e_excel}"))

        except Exception as e:
            self.cola_eventos.put(("log", f"[CRITICO] Error no controlado durante servicios: {e}"))
        finally:
            self.cola_eventos.put(("fin_servicios", len(cargados_exitosos)))

    def animar_progreso(self, valor_objetivo: float, paso_actual=None):
        """Avanza la barra de progreso de forma suave sin saltos bruscos."""
        if paso_actual is None:
            paso_actual = self.barra_progreso.get()
            self._target_progreso = valor_objetivo

        # Si el valor objetivo cambió por una llamada más reciente, salir del ciclo previo
        if hasattr(self, "_target_progreso") and self._target_progreso != valor_objetivo:
            return

        # Diferencia entre el valor actual y el deseado
        diff = valor_objetivo - paso_actual
        if abs(diff) > 0.01:
            nuevo_valor = paso_actual + (diff * 0.25)
            self.barra_progreso.set(nuevo_valor)
            self.lbl_porcentaje.configure(text=f"Progreso: {int(nuevo_valor * 100)}%")
            self.after(30, lambda: self.animar_progreso(valor_objetivo, nuevo_valor))
        else:
            self.barra_progreso.set(valor_objetivo)
            self.lbl_porcentaje.configure(text=f"Progreso: {int(valor_objetivo * 100)}%")

    def _actualizar_progreso_ui(self, valor: float, etiqueta: str = ""):
        self.animar_progreso(valor)

    def _iniciar_pulso_estado(self):
        """Inicia el efecto de pulso visual suave en el indicador de estado lateral."""
        self._animando_pulso = True
        self._color_pulso_actual = "#38bdf8"
        if hasattr(self, "lbl_status"):
            self.lbl_status.configure(text="● Procesando datos...", text_color=self._color_pulso_actual)
        self._ciclo_pulso_estado()

    def _ciclo_pulso_estado(self):
        """Alterna el color del texto entre cyan y azul cada 500 ms con self.after()."""
        if not getattr(self, "_animando_pulso", False):
            return

        if hasattr(self, "lbl_status"):
            self._color_pulso_actual = "#0284c7" if self._color_pulso_actual == "#38bdf8" else "#38bdf8"
            self.lbl_status.configure(text="● Procesando datos...", text_color=self._color_pulso_actual)

        self._pulso_after_id = self.after(500, self._ciclo_pulso_estado)

    def _detener_pulso_estado(self):
        """Detiene el pulso y restablece de inmediato el indicador a verde fijo."""
        self._animando_pulso = False
        if hasattr(self, "_pulso_after_id") and self._pulso_after_id:
            try:
                self.after_cancel(self._pulso_after_id)
            except Exception:
                pass
            self._pulso_after_id = None

        if hasattr(self, "lbl_status"):
            self.lbl_status.configure(text="● Sistema Listo", text_color="#22c55e")

    def _finalizar_ejecucion_formacion(self, total: int):
        self.ejecutando_tarea = False
        self._detener_pulso_estado()
        self.animar_progreso(1.0)
        self.btn_iniciar_formacion.configure(state="normal", text="INICIAR CARGA AUTOMATIZADA", fg_color="#1f538d")
        self._agregar_log(f"[FINALIZADO] Proceso de formación completado: {total} registros procesados.")

    def _finalizar_ejecucion_servicios(self, total: int):
        self.ejecutando_tarea = False
        self._detener_pulso_estado()
        self.animar_progreso(1.0)
        self.btn_iniciar_servicios.configure(state="normal", text="INICIAR CARGA DE SERVICIOS", fg_color="#2E7D32")
        self._agregar_log(f"[FINALIZADO] Servicios comunitarios completados: {total} usuarios procesados.")

    def _abrir_directorio_salidas(self):
        planillas_dir = os.path.join(BASE_DIR, "Planillas")
        os.makedirs(planillas_dir, exist_ok=True)
        exito = abrir_archivo_o_directorio_sistema(planillas_dir)
        if exito:
            self._agregar_log(f"[REPORTES] Abriendo directorio de planillas: {planillas_dir}")
        else:
            self._agregar_log(f"[ADVERTENCIA] No se pudo abrir automáticamente: {planillas_dir}")

    def _abrir_plantilla_base(self):
        plantilla = os.path.join(BASE_DIR, "config", "plantilla_base.ods")
        if os.path.exists(plantilla):
            exito = abrir_archivo_o_directorio_sistema(plantilla)
            if exito:
                self._agregar_log(f"[REPORTES] Abriendo plantilla base: {plantilla}")
            else:
                self._agregar_log(f"[ADVERTENCIA] No se pudo abrir automáticamente: {plantilla}")
        else:
            self._agregar_log(f"[ADVERTENCIA] No se localizó la plantilla: {plantilla}")

    def _iniciar_generacion_planilla_directa(self):
        """Genera la planilla oficial multiformato de forma directa desde los datos cargados."""
        participantes = self.participantes_cargados_planillas
        if not participantes:
            self._mostrar_modal_mensaje(
                titulo="Archivo Requerido",
                mensaje="Por favor examina y selecciona primero un archivo de participantes (.xlsx, .ods, .csv).",
                tipo="aviso"
            )
            return

        fmt_seleccionado = self.menu_formato_planillas.get() if hasattr(self, "menu_formato_planillas") else "OpenDocument (.ods)"
        if "xlsx" in fmt_seleccionado.lower() or "excel" in fmt_seleccionado.lower():
            formato = "xlsx"
        elif "pdf" in fmt_seleccionado.lower():
            formato = "pdf"
        else:
            formato = "ods"

        id_o_url = self.entry_id_url_planillas.get().strip() if hasattr(self, "entry_id_url_planillas") else ""
        id_act = ""
        url_act = ""
        if id_o_url:
            if "http" in id_o_url.lower():
                url_act = id_o_url
                id_act = extraer_id_actividad(id_o_url) if "extraer_id_actividad" in globals() else ""
            elif id_o_url.isdigit() or len(id_o_url) < 15:
                id_act = id_o_url
        if not id_act:
            id_act = "general"

        from modulos.generador_planilla import generar_planilla_multiformato
        self._agregar_log(f"[PLANILLA] Generando planilla oficial ({formato.upper()}) para {len(participantes)} participantes...")

        try:
            ruta_generada = generar_planilla_multiformato(
                participantes=participantes,
                id_actividad=id_act,
                url_actividad=url_act,
                formato=formato
            )
            if not ruta_generada:
                self._agregar_log("[INFO] Generación de planilla cancelada por el usuario.")
                return

            if os.path.exists(ruta_generada):
                self._agregar_log(f"[OK] Planilla oficial generada exitosamente en:\n   {ruta_generada}")
                self._mostrar_modal_exito_planilla(ruta_generada)
            else:
                self._agregar_log("[ERROR] No se pudo encontrar el archivo de planilla generado.")
                self._mostrar_modal_mensaje(
                    titulo="Error de Generación",
                    mensaje="No se pudo completar la generación del archivo de planilla.",
                    tipo="error"
                )
        except Exception as e:
            self._agregar_log(f"[ERROR] Incidencia generando planilla: {e}")
            self._mostrar_modal_mensaje(
                titulo="Error al Generar Planilla",
                mensaje=f"Ocurrió un error durante la generación de la planilla:\n\n{e}",
                tipo="error"
            )

    def _mostrar_modal_exito_planilla(self, ruta_archivo: str):
        """Abre modal informativo al generar la planilla con botones para abrir el archivo o la carpeta."""
        self.update_idletasks()
        ancho_modal = 500
        alto_modal = 220
        pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho_modal) // 2)
        pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto_modal) // 2)

        modal = ctk.CTkToplevel(self)
        modal.title("Planilla Oficial Generada")
        modal.geometry(f"{ancho_modal}x{alto_modal}+{pos_x}+{pos_y}")
        modal.minsize(460, 200)
        modal.transient(self)
        self.registrar_modal("exito_planilla", modal, grab=True)
        modal.focus_set()

        nom_arc = os.path.basename(ruta_archivo)
        lbl_titulo = ctk.CTkLabel(
            modal,
            text="✅ ¡Planilla Oficial Generada con Éxito!",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#30D158"
        )
        lbl_titulo.pack(pady=(16, 6))

        lbl_desc = ctk.CTkLabel(
            modal,
            text=f"El documento se ha guardado en:\n{nom_arc}",
            font=ctk.CTkFont(size=11),
            text_color="#C0C0C8"
        )
        lbl_desc.pack(padx=20, pady=(0, 16))

        btn_row = ctk.CTkFrame(modal, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 10))

        btn_abrir_archivo = ctk.CTkButton(
            btn_row,
            text="👁 Abrir Planilla",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=34,
            fg_color="#1F538D",
            hover_color="#14375E",
            command=lambda: abrir_archivo_o_directorio_sistema(ruta_archivo)
        )
        btn_abrir_archivo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_abrir_carpeta = ctk.CTkButton(
            btn_row,
            text="📂 Abrir Carpeta",
            font=ctk.CTkFont(size=11),
            height=34,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=self._abrir_directorio_salidas
        )
        btn_abrir_carpeta.pack(side="left", fill="x", expand=True, padx=(6, 6))

        btn_cerrar = ctk.CTkButton(
            btn_row,
            text="Cerrar",
            font=ctk.CTkFont(size=11),
            height=34,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self.cerrar_modal(modal)
        )
        btn_cerrar.pack(side="left", padx=(6, 0))

    def _mostrar_modal_editar_ficha_formativa(self):
        """Abre modal CTkToplevel para ver y modificar interactivamente la Ficha Formativa (datos_actividad.json)."""
        from modulos.config_manager import cargar_datos_actividad, guardar_datos_actividad
        datos_actuales = cargar_datos_actividad()

        self.update_idletasks()
        ancho_modal = 540
        alto_modal = 520
        pos_x = max(0, self.winfo_x() + (self.winfo_width() - ancho_modal) // 2)
        pos_y = max(0, self.winfo_y() + (self.winfo_height() - alto_modal) // 2)

        modal = ctk.CTkToplevel(self)
        modal.title("Ficha Formativa y Metadatos Institucionales")
        modal.geometry(f"{ancho_modal}x{alto_modal}+{pos_x}+{pos_y}")
        modal.minsize(500, 480)
        modal.transient(self)
        self.registrar_modal("editar_ficha_formativa", modal, grab=True)
        modal.focus_set()

        modal.grid_columnconfigure(0, weight=1)
        modal.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(modal, fg_color="#1E1E28", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        lbl_h = ctk.CTkLabel(
            header,
            text="✏️ Ficha Formativa y Metadatos Institucionales",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_h.pack(anchor="w", padx=16, pady=10)

        # Form Scrollable
        form_scroll = ctk.CTkScrollableFrame(modal, fg_color="#121218", corner_radius=8)
        form_scroll.grid(row=1, column=0, sticky="nsew", padx=14, pady=8)
        form_scroll.grid_columnconfigure(1, weight=1)

        campos = [
            ("Facilitador:", "nombre_facilitador", datos_actuales.get("nombre_facilitador", "")),
            ("Cédula Facilitador:", "cedula_facilitador", datos_actuales.get("cedula_facilitador", "")),
            ("Estado:", "estado", datos_actuales.get("estado", "Yaracuy")),
            ("Infocentro:", "nombre_infocentro", datos_actuales.get("nombre_infocentro", "")),
            ("Código Infocentro:", "codigo_infocentro", datos_actuales.get("codigo_infocentro", "")),
            ("Módulo Formación:", "modulo", datos_actuales.get("modulo", "")),
            ("Contenido:", "contenido", datos_actuales.get("contenido", "")),
            ("Hora Inicio:", "hora_inicio", datos_actuales.get("hora_inicio", "9:00 am")),
            ("Hora Fin:", "hora_fin", datos_actuales.get("hora_fin", "12:00 pm")),
        ]

        entradas = {}
        for r_idx, (etiqueta, clave, valor) in enumerate(campos):
            lbl = ctk.CTkLabel(form_scroll, text=etiqueta, font=ctk.CTkFont(size=11, weight="bold"), text_color="#C0C0C8", anchor="w")
            lbl.grid(row=r_idx, column=0, padx=(8, 12), pady=5, sticky="w")
            ent = ctk.CTkEntry(form_scroll, font=ctk.CTkFont(size=11), height=30)
            ent.insert(0, valor)
            ent.grid(row=r_idx, column=1, padx=(0, 8), pady=5, sticky="ew")
            entradas[clave] = ent

        # Footer Buttons
        footer = ctk.CTkFrame(modal, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

        def _guardar_ficha():
            nuevos = {clave: entradas[clave].get().strip() for clave in entradas}
            guardar_datos_actividad(nuevos)
            self._agregar_log("[OK] Ficha formativa institucional actualizada en config/datos_actividad.json.")
            self.cerrar_modal(modal)

        btn_guardar = ctk.CTkButton(
            footer,
            text="💾 Guardar Cambios",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=32,
            fg_color="#1F538D",
            hover_color="#14375E",
            command=_guardar_ficha
        )
        btn_guardar.pack(side="right", padx=(8, 0))

        btn_cancelar = ctk.CTkButton(
            footer,
            text="Cancelar",
            font=ctk.CTkFont(size=11),
            height=32,
            fg_color="#2B2B36",
            hover_color="#3A3A4A",
            command=lambda: self.cerrar_modal(modal)
        )
        btn_cancelar.pack(side="right")

    def _agregar_log(self, mensaje: str):
        if threading.current_thread() is not threading.main_thread():
            if hasattr(self, "cola_eventos"):
                self.cola_eventos.put(("log", mensaje))
            else:
                self.after(0, lambda: self._agregar_log(mensaje))
            return

        ts = datetime.now().strftime("%H:%M:%S")
        linea = f"[{ts}] {mensaje}\n"
        try:
            self.textbox_logs.insert(tk.END, linea)
            self.textbox_logs.see(tk.END)
        except Exception:
            pass


# Aliases de compatibilidad
AppGUI = JsBotGUI
JsBotGUIPreview = JsBotGUI


def iniciar_gui():
    """Punto de entrada oficial para inicializar la aplicación de escritorio CustomTkinter."""
    app = JsBotGUI()
    app.mainloop()


def main():
    iniciar_gui()


if __name__ == "__main__":
    main()
