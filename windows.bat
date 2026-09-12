@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title JsBOT — Verificador de Entorno
cd /d "%~dp0"

echo [INFO] Verificando interprete de Python...

set PYTHON_CMD=
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    )
)

if "%PYTHON_CMD%"=="" (
    echo.
    echo ========================================================
    echo  [X] ERROR: Python no esta instalado en este equipo.
    echo ========================================================
    echo  Para ejecutar JsBOT necesitas instalar Python 3.10 o superior.
    echo  Descargalo desde: https://www.python.org/downloads/
    echo  IMPORTANTE: Marca la casilla "Add Python to PATH" al instalar.
    echo ========================================================
    echo.
    pause
    exit /b 1
)

%PYTHON_CMD% -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTA] pip no esta disponible. Intentando activar ensurepip...
    %PYTHON_CMD% -m ensurepip --default-pip
)

%PYTHON_CMD% -c "import pandas, customtkinter, selenium" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Configurando dependencias por primera vez...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo.
        echo [X] Error al instalar dependencias. Revisa tu conexion a Internet.
        pause
        exit /b 1
    )
)

cls
%PYTHON_CMD% main.py %*
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] La aplicacion finalizo con codigo de error.
    pause
)
