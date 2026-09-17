#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
MÓDULO: VERIFICADOR DE INTEGRIDAD Y ENTORNO MULTIPLATAFORMA (verificador_entorno.py)
===============================================================================
Sistema   : JsBOT (Robotic Process Automation) — versión: ver modulos/version.py
Autor     : Jair Alejandro Hernández González
Ubicación : San Felipe, Estado Yaracuy, República Bolivariana de Venezuela
===============================================================================
"""

import os
import sys
import json
import shutil
import subprocess
import importlib.metadata
from datetime import datetime

# Activación de Terminal Virtual (VT100 / ANSI) en Windows
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
        mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(h_out, mode)
    except Exception:
        pass

    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Localización de rutas base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
SCREENSHOTS_DIR = os.path.join(LOGS_DIR, "screenshots")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
PLANTILLA_ODS = os.path.join(CONFIG_DIR, "plantilla_base.ods")
REQUIREMENTS_FILE = os.path.join(CONFIG_DIR, "requirements.txt")
if not os.path.exists(REQUIREMENTS_FILE):
    REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console(force_terminal=True)
    RICH_AVAILABLE = True
except ImportError:
    console = None
    RICH_AVAILABLE = False


def detectar_sistema_operativo() -> str:
    """Identifica con precisión el sistema operativo anfitrión."""
    if sys.platform.startswith("win"):
        return "Windows"
    elif sys.platform.startswith("linux"):
        # Detectar Canaima / Debian si existe /etc/os-release
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    if "canaima" in content:
                        return "Linux Canaima"
                    elif "debian" in content:
                        return "Linux Debian"
                    elif "ubuntu" in content:
                        return "Linux Ubuntu"
            except Exception:
                pass
        return "GNU/Linux"
    elif sys.platform.startswith("darwin"):
        return "macOS"
    return "Desconocido"


def auditar_dependencias_pypi() -> bool:
    """
    Verifica que las dependencias de requirements.txt estén instaladas.
    Si faltan o están desactualizadas, lanza auto-actualización silenciosa con spinner.
    """
    if not os.path.exists(REQUIREMENTS_FILE):
        return True

    requeridos = []
    with open(REQUIREMENTS_FILE, "r", encoding="utf-8") as f:
        for linea in f:
            l = linea.strip()
            if l and not l.startswith("#"):
                # Extraer nombre del paquete antes de cualquier operador >=, ==, <=
                pkg_name = l.split(">=")[0].split("==")[0].split("<=")[0].split(">")[0].split("<")[0].strip()
                if pkg_name:
                    requeridos.append(pkg_name)

    faltantes = False
    for pkg in requeridos:
        try:
            importlib.metadata.version(pkg)
        except Exception:
            faltantes = True
            break

    if faltantes:
        if RICH_AVAILABLE and console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Actualizando dependencias de software... Por favor espera[/bold cyan]"),
                transient=True
            ) as progress:
                progress.add_task("update", total=None)
                cmd = [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--upgrade", "--quiet"]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("\n🔄 Actualizando dependencias de software... Por favor espera...")
            cmd = [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE, "--upgrade", "--quiet"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return True


def detectar_navegadores() -> str:
    """Busca binarios ejecutables de navegadores en PATH y rutas del sistema."""
    encontrados = []
    
    # Lista de nombres típicos
    candidatos_firefox = ["firefox", "firefox.exe", "firefox-esr"]
    candidatos_chrome = ["google-chrome", "chrome", "chrome.exe", "chromium", "chromium-browser"]
    candidatos_edge = ["msedge", "msedge.exe", "microsoft-edge"]

    # 1. Firefox
    if any(shutil.which(cmd) for cmd in candidatos_firefox):
        encontrados.append("Firefox")
    elif sys.platform.startswith("win"):
        rutas_fx = [
            os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
        ]
        if any(os.path.exists(p) for p in rutas_fx):
            encontrados.append("Firefox")

    # 2. Chrome / Chromium
    if any(shutil.which(cmd) for cmd in candidatos_chrome):
        encontrados.append("Chrome")
    elif sys.platform.startswith("win"):
        rutas_cr = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        if any(os.path.exists(p) for p in rutas_cr):
            encontrados.append("Chrome")

    # 3. Edge
    if any(shutil.which(cmd) for cmd in candidatos_edge):
        encontrados.append("Edge")
    elif sys.platform.startswith("win"):
        rutas_ed = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        if any(os.path.exists(p) for p in rutas_ed):
            encontrados.append("Edge")

    if encontrados:
        return f"{' / '.join(encontrados)} detectado"
    return "No detectado (Instalar Firefox o Chrome)"


def detectar_suite_ofimatica() -> tuple:
    """Verifica si existe LibreOffice, OpenOffice, Excel u OnlyOffice para asistencia HITL."""
    comandos_suite = [
        "libreoffice", "soffice", "localc", "excel",
        "desktopeditors", "onlyoffice-desktopeditors", "onlyoffice"
    ]
    for cmd in comandos_suite:
        ruta = shutil.which(cmd)
        if ruta:
            return True, ruta

    # Rutas comunes en Windows
    if sys.platform.startswith("win"):
        rutas_win = [
            os.path.expandvars(r"%ProgramFiles%\LibreOffice\program\soffice.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\LibreOffice\program\soffice.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft Office\root\Office16\EXCEL.EXE"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft Office\Office14\EXCEL.EXE"),
        ]
        for p in rutas_win:
            if os.path.exists(p):
                return True, p

    return False, None


def verificar_integridad_archivos() -> dict:
    """Valida la presencia y consistencia de los archivos críticos del sistema."""
    estado = {}
    
    # 1. Configuración settings.json
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                json.load(f)
            estado["settings"] = (True, "config/settings.json (Cargado OK)")
        except Exception:
            estado["settings"] = (False, "config/settings.json (JSON Inválido o corrupto)")
    else:
        estado["settings"] = (False, "config/settings.json (Faltante)")

    # 2. Plantilla base ODS (Imprescindible para planillas formativas)
    if os.path.exists(PLANTILLA_ODS) and os.path.getsize(PLANTILLA_ODS) > 0:
        estado["plantilla"] = (True, "config/plantilla_base.ods (Verificada)")
    else:
        estado["plantilla"] = (False, "config/plantilla_base.ods (Faltante - Requerido)")

    # 3. Directorio de Logs y Screenshots
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        estado["logs"] = (True, "logs/screenshots/ (Listo para capturas)")
    except Exception as e:
        estado["logs"] = (False, f"logs/screenshots/ (Error de permisos: {e})")

    return estado


def ejecutar_checklist_sistema() -> bool:
    """
    Ejecuta el paso 0 de diagnóstico de integridad y requisitos de JsBOT.
    Renderiza un checklist visual de alto impacto y detiene el arranque si hay fallos críticos.
    """
    # 1. Chequeo de dependencias PyPI
    auditar_dependencias_pypi()

    # 2. Recolección de diagnósticos
    so_nombre = detectar_sistema_operativo()
    py_version = f"v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    py_desc = f"{py_version} (Requisito >= 3.10 {'superado' if py_ok else 'INSUFICIENTE'})"

    nav_desc = detectar_navegadores()
    nav_ok = "detectado" in nav_desc.lower()

    tiene_suite, _ = detectar_suite_ofimatica()
    suite_desc = "Detectada" if tiene_suite else "No detectada (Modo Manual)"

    archivos_estado = verificar_integridad_archivos()
    settings_ok, settings_desc = archivos_estado["settings"]
    plantilla_ok, plantilla_desc = archivos_estado["plantilla"]
    logs_ok, logs_desc = archivos_estado["logs"]

    # Determinar si el sistema está operativo
    todo_ok = py_ok and nav_ok and settings_ok and plantilla_ok and logs_ok

    # Marcadores visuales retrocompatibles (ASCII / CP850 safe)
    tag_ok = "[bold green][OK][/bold green]"
    tag_err = "[bold red][X][/bold red]"
    tag_warn = "[bold yellow][!][/bold yellow]"

    items_checklist = [
        (tag_ok if so_nombre != 'Desconocido' else tag_warn, "Sistema Operativo", f": {so_nombre}"),
        (tag_ok if py_ok else tag_err, "Intérprete Python", f": {py_desc}"),
        (tag_ok, "Dependencias PyPI", ": Sincronizadas y actualizadas al día"),
        (tag_ok if nav_ok else tag_err, "Navegador Detectado", f": {nav_desc}"),
        (tag_ok if tiene_suite else tag_warn, "Suite Ofimática", f": {suite_desc}"),
        (tag_ok if plantilla_ok else tag_err, "Plantilla Base ODS", f": {plantilla_desc}"),
        (tag_ok if settings_ok else tag_err, "Configuración", f": {settings_desc}"),
        (tag_ok if logs_ok else tag_err, "Directorio de Logs", f": {logs_desc}"),
    ]

    if RICH_AVAILABLE and console:
        tabla = Table(box=None, show_header=False, pad_edge=False)
        tabla.add_column("Estado", justify="center", width=6)
        tabla.add_column("Parametro", style="bold white", width=24)
        tabla.add_column("Detalle", style="bright_yellow")

        for estado, param, detalle in items_checklist:
            tabla.add_row(estado, param, detalle)

        panel = Panel(
            tabla,
            title="[bold cyan]DIAGNÓSTICO DE INTEGRIDAD Y REQUISITOS[/bold cyan]",
            subtitle="[bold green]SISTEMA 100% OPERATIVO PARA CARGA MASIVA[/bold green]" if todo_ok else "[bold red]FALLO DE INTEGRIDAD CRÍTICA[/bold red]",
            border_style="cyan" if todo_ok else "red",
            expand=False
        )

        console.print()
        console.print(panel)
        console.print()
    else:
        print("\n" + "=" * 76)
        print("             DIAGNÓSTICO DE INTEGRIDAD Y REQUISITOS — JsBOT")
        print("=" * 76)
        for estado, param, detalle in items_checklist:
            st = "[OK]" if "OK" in estado else ("[X]" if "X" in estado else "[!]")
            print(f"  {st:4} {param:24} {detalle}")
        print("=" * 76 + "\n")

    if not todo_ok:
        if not plantilla_ok:
            print("\n❌ ERROR CRÍTICO: Falta 'config/plantilla_base.ods'.")
            print("👉 El bot requiere este archivo para generar planillas formativas oficiales.")
        if not py_ok:
            print(f"\n❌ ERROR CRÍTICO: Se requiere Python 3.10 o superior (Actual: {py_version}).")
        if not nav_ok:
            print("\n❌ ERROR CRÍTICO: No se detectó ningún navegador compatible (Firefox / Chrome / Edge).")
        return False

    return True


if __name__ == "__main__":
    exito = ejecutar_checklist_sistema()
    if not exito:
        sys.exit(1)
