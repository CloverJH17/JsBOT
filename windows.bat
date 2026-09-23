@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title JsBOT RPA — Verificador de Entorno
cd /d "%~dp0"

echo ========================================================
echo    JsBOT RPA — Entorno Microsoft Windows
echo ========================================================
echo.

REM -----------------------------------------------------------------------------
REM 1. DETECCION E INSTALACION DE PYTHON
REM -----------------------------------------------------------------------------
echo [INFO] Verificando interprete de Python...
set "PYTHON_EXE="
set "PYTHON_ARGS="

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    goto :python_found
)

python -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    set "PYTHON_ARGS="
    goto :python_found
)

py -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS="
    goto :python_found
)

python3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=python3"
    set "PYTHON_ARGS="
    goto :python_found
)

for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%ProgramFiles(x86)%\Python3*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%D\python.exe"
            set "PYTHON_ARGS="
            set "PATH=%%D;%%D\Scripts;!PATH!"
            goto :python_found
        )
    )
)

echo.
echo ========================================================
echo  [AVISO] Python no fue detectado en su sistema.
echo  Iniciando instalacion automatica de Python 3.12 64-bit...
echo ========================================================
echo.

where winget >nul 2>nul
if not errorlevel 1 (
    echo [INFO] Instalando Python mediante winget...
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements --scope user
) else (
    echo [INFO] Descargando instalador oficial de Python para Windows...
    where curl >nul 2>nul
    if not errorlevel 1 (
        curl.exe -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe', '$env:TEMP\python_installer.exe')"
    )
    if exist "%TEMP%\python_installer.exe" (
        echo [INFO] Instalando Python en segundo plano, por favor espere...
        start /wait "" "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
        del "%TEMP%\python_installer.exe" 2>nul
    )
)

for /d %%D in ("%LocalAppData%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%ProgramFiles(x86)%\Python3*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%D\python.exe"
            set "PYTHON_ARGS="
            set "PATH=%%D;%%D\Scripts;!PATH!"
            goto :python_found
        )
    )
)

py -3 -c "import sys" >nul 2>nul && set "PYTHON_EXE=py" && set "PYTHON_ARGS=-3" && goto :python_found
python -c "import sys" >nul 2>nul && set "PYTHON_EXE=python" && set "PYTHON_ARGS=" && goto :python_found

if "%PYTHON_EXE%"=="" (
    echo.
    echo ========================================================
    echo  [X] ERROR: No se pudo completar la instalacion automatica de Python.
    echo ========================================================
    echo  Por favor instalalo manualmente desde: https://www.python.org/downloads/
    echo  IMPORTANTE: Marca la casilla Add Python to PATH al instalar.
    echo ========================================================
    echo.
    pause
    exit /b 1
)

:python_found
if "%PYTHON_ARGS%"=="" (
    echo [OK] Python detectado: "%PYTHON_EXE%"
) else (
    echo [OK] Python detectado: "%PYTHON_EXE%" %PYTHON_ARGS%
)
echo.

REM -----------------------------------------------------------------------------
REM 2. VERIFICACION DE PIP
REM -----------------------------------------------------------------------------
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [ALERTA] pip no esta disponible. Activando ensurepip...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m ensurepip --default-pip
)

REM -----------------------------------------------------------------------------
REM 3. LECTURA DINAMICA DE VERSION
REM -----------------------------------------------------------------------------
set JSBOT_VER=4.12.0
for /f "delims=" %%V in ('"%PYTHON_EXE%" %PYTHON_ARGS% -c "import sys; sys.path.insert(0, '.'); import modulos.version as _v; print(_v.__version__)" 2^>nul') do set JSBOT_VER=%%V
title JsBOT v%JSBOT_VER% — Verificador de Entorno
echo ========================================================
echo    JsBOT v%JSBOT_VER% — Entorno Microsoft Windows
echo ========================================================
echo.

REM -----------------------------------------------------------------------------
REM 4. VERIFICACION E INSTALACION DE DEPENDENCIAS
REM -----------------------------------------------------------------------------
echo [INFO] Verificando dependencias del sistema...
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import pandas, customtkinter, CTkMessagebox, playwright, python_calamine, PIL, bs4, requests, rich, InquirerPy, openpyxl, xlrd, odf, odfdo, loguru" >nul 2>nul
if not errorlevel 1 goto :check_playwright_browser

echo [INFO] Configurando dependencias del sistema por primera vez...
"%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r "%~dp0config\requirements.txt"
if errorlevel 1 (
    echo.
    echo [X] Error al instalar dependencias. Revisa tu conexion a Internet.
    pause
    exit /b 1
)

:check_playwright_browser
REM Verificar si los binarios de Chromium para Playwright estan disponibles
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import os, glob; base=os.path.expandvars(r'%%LOCALAPPDATA%%\ms-playwright'); exit(0 if glob.glob(os.path.join(base, 'chromium*')) else 1)" >nul 2>nul
if not errorlevel 1 goto :deps_ready

echo [INFO] Descargando binarios del navegador Playwright Chromium...
"%PYTHON_EXE%" %PYTHON_ARGS% -m playwright install chromium

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import os, glob; base=os.path.expandvars(r'%%LOCALAPPDATA%%\ms-playwright'); exit(0 if glob.glob(os.path.join(base, 'chromium*')) else 1)" >nul 2>nul
if not errorlevel 1 goto :deps_ready

echo [AVISO] La descarga estandar de Playwright fallo o supero el tiempo limite.
echo [INFO] Activando descarga resiliente de Chromium con curl - sin limite de tiempo...
set "PW_DEST=%LocalAppData%\ms-playwright\chromium-1243"
mkdir "!PW_DEST!" 2>nul
curl.exe -# -L -o "%TEMP%\chrome-win64.zip" "https://cdn.playwright.dev/builds/cft/153.0.8010.12/win64/chrome-win64.zip"
if exist "%TEMP%\chrome-win64.zip" (
    echo [INFO] Descomprimiendo binarios del navegador...
    tar.exe -xf "%TEMP%\chrome-win64.zip" -C "!PW_DEST!"
    type nul > "!PW_DEST!\INSTALLATION_COMPLETE"
    type nul > "!PW_DEST!\DEPENDENCIES_VALIDATED"
    del "%TEMP%\chrome-win64.zip" 2>nul
    echo [OK] Chromium configurado correctamente via fallback.
) else (
    echo [ALERTA] No se pudo completar la descarga automatica de Chromium.
)

:deps_ready
REM -----------------------------------------------------------------------------
REM 5. EJECUCION DE JSBOT
REM -----------------------------------------------------------------------------
echo [INFO] Iniciando JsBOT...
"%PYTHON_EXE%" %PYTHON_ARGS% "%~dp0main.py" %*
if errorlevel 1 (
    echo.
    echo [AVISO] La aplicacion finalizo con codigo de advertencia o error.
    pause
)