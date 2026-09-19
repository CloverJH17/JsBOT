@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title JsBOT RPA — Verificador de Entorno
cd /d "%~dp0"

echo ========================================================
echo   JsBOT RPA — Entorno Microsoft Windows
echo ========================================================
echo.

REM -----------------------------------------------------------------------------
REM 1. DETECCIÓN E INSTALACIÓN PRIORITARIA DE PYTHON
REM -----------------------------------------------------------------------------
echo [INFO] Verificando intérprete de Python...

set PYTHON_CMD=

REM Probar ejecución real de comandos para evitar alias rotos de la Tienda de Windows
py -3 -c "import sys" >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    python -c "import sys" >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        py -c "import sys" >nul 2>nul
        if %errorlevel% equ 0 (
            set "PYTHON_CMD=py"
        ) else (
            python3 -c "import sys" >nul 2>nul
            if %errorlevel% equ 0 (
                set "PYTHON_CMD=python3"
            )
        )
    )
)

REM Si no está en PATH, buscar rutas estándar de instalación
if "%PYTHON_CMD%"=="" (
    for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%ProgramFiles(x86)%\Python3*") do (
        if exist "%%D\python.exe" (
            "%%D\python.exe" -c "import sys" >nul 2>nul
            if !errorlevel! equ 0 (
                set "PYTHON_CMD=%%D\python.exe"
                set "PATH=%%D;%%D\Scripts;!PATH!"
            )
        )
    )
)

REM Si Python NO está instalado, proceder con la instalación automática
if "%PYTHON_CMD%"=="" (
    echo.
    echo ========================================================
    echo  [AVISO] Python no fue detectado en su sistema.
    echo  Iniciando instalación automática de Python 3...
    echo ========================================================
    echo.

    where winget >nul 2>nul
    if %errorlevel% equ 0 (
        echo [INFO] Descargando e instalando Python oficial mediante Windows Package Manager (winget)...
        winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements --scope user
    ) else (
        echo [INFO] Descargando instalador oficial de Python para Windows...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe', '$env:TEMP\python_installer.exe')"
        if exist "%TEMP%\python_installer.exe" (
            echo [INFO] Ejecutando instalación silenciosa de Python con soporte PATH...
            "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
            del "%TEMP%\python_installer.exe" 2>nul
        )
    )

    REM Refrescar búsqueda tras la instalación
    for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "%ProgramFiles%\Python3*") do (
        if exist "%%D\python.exe" (
            set "PYTHON_CMD=%%D\python.exe"
            set "PATH=%%D;%%D\Scripts;!PATH!"
        )
    )

    if "%PYTHON_CMD%"=="" (
        py -3 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3"
        python -c "import sys" >nul 2>nul && set "PYTHON_CMD=python"
    )
)

REM Verificación final de Python
if "%PYTHON_CMD%"=="" (
    echo.
    echo ========================================================
    echo  [X] ERROR: No se pudo completar la instalación de Python.
    echo ========================================================
    echo  Por favor instálalo manualmente desde: https://www.python.org/downloads/
    echo  IMPORTANTE: Marca la casilla "Add Python to PATH" al instalar.
    echo ========================================================
    echo.
    pause
    exit /b 1
)

REM -----------------------------------------------------------------------------
REM 2. VERIFICACIÓN DE PIP
REM -----------------------------------------------------------------------------
%PYTHON_CMD% -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ALERTA] pip no está disponible. Activando ensurepip...
    %PYTHON_CMD% -m ensurepip --default-pip
)

REM -----------------------------------------------------------------------------
REM 3. LECTURA DINÁMICA DE VERSIÓN
REM -----------------------------------------------------------------------------
set JSBOT_VER=4.8.0
for /f "delims=" %%V in ('%PYTHON_CMD% -c "import sys; sys.path.insert(0, '.'); import modulos.version as _v; print(_v.__version__)" 2^>nul') do set JSBOT_VER=%%V
title JsBOT v%JSBOT_VER% — Verificador de Entorno
echo ========================================================
echo   JsBOT v%JSBOT_VER% — Entorno Microsoft Windows
echo ========================================================
echo.

REM -----------------------------------------------------------------------------
REM 4. VERIFICACIÓN E INSTALACIÓN DE DEPENDENCIAS
REM -----------------------------------------------------------------------------
%PYTHON_CMD% -c "import pandas, customtkinter, playwright, python_calamine, PIL, bs4, requests, rich, openpyxl, xlrd, odf" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Configurando dependencias del sistema por primera vez...
    %PYTHON_CMD% -m pip install -r config\requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [X] Error al instalar dependencias. Revisa tu conexión a Internet.
        pause
        exit /b 1
    )
    echo [INFO] Verificando binarios del navegador Playwright (Chromium)...
    %PYTHON_CMD% -m playwright install chromium
)

REM -----------------------------------------------------------------------------
REM 5. EJECUCIÓN DE JSBOT
REM -----------------------------------------------------------------------------
cls
%PYTHON_CMD% main.py %*
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] La aplicación finalizó con código de error.
    pause
)
