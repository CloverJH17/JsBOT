#Requires -Version 5.1
<#
===============================================================================
INSTALADOR EXPRESS ONE-LINE — JsBOT RPA v5.0.0 (Microsoft Windows)
===============================================================================
Uso en PowerShell (1 sola línea):
irm https://raw.githubusercontent.com/CloverJH17/JsBOT/main/install.ps1 | iex
===============================================================================
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   JsBOT RPA v5.0.0 — Instalador Express Autónomo" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$RepoUrl = "https://github.com/CloverJH17/JsBOT.git"
$ZipUrl  = "https://github.com/CloverJH17/JsBOT/archive/refs/heads/main.zip"
$InstallDir = "$env:LOCALAPPDATA\JsBOT"

# -----------------------------------------------------------------------------
# 1. PREPARACIÓN O ACTUALIZACIÓN DEL DIRECTORIO DE INSTALACIÓN
# -----------------------------------------------------------------------------
Write-Host "[1/6] Preparando directorio de instalación..." -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -Path $InstallDir -ItemType Directory -Force | Out-Null
}

$hasGit = $false
try {
    $null = git --version
    $hasGit = $true
} catch {
    $hasGit = $false
}

if ($hasGit) {
    if (Test-Path "$InstallDir\.git") {
        Write-Host "       Actualizando repositorio existente con Git..." -ForegroundColor Gray
        git -C $InstallDir pull origin main --quiet
    } else {
        Write-Host "       Clonando repositorio con Git en $InstallDir..." -ForegroundColor Gray
        git clone --quiet $RepoUrl $InstallDir
    }
} else {
    Write-Host "       Descargando paquete de GitHub (sin dependencia de Git)..." -ForegroundColor Gray
    $tempZip = "$env:TEMP\JsBOT_Install.zip"
    $tempExtract = "$env:TEMP\JsBOT_Extract"
    
    Invoke-WebRequest -Uri $ZipUrl -OutFile $tempZip -UseBasicParsing
    if (Test-Path $tempExtract) { Remove-Item -Path $tempExtract -Recurse -Force }
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
    
    # Copiar contenido de JsBOT-main a InstallDir preservando archivos locales
    Copy-Item -Path "$tempExtract\JsBOT-main\*" -Destination $InstallDir -Recurse -Force
    
    Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
}

# -----------------------------------------------------------------------------
# 2. VERIFICACIÓN E INSTALACIÓN DE PYTHON
# -----------------------------------------------------------------------------
Write-Host "[2/6] Verificando intérprete de Python..." -ForegroundColor Yellow
$PythonCmd = $null

$pythonCandidates = @("py", "python", "python3")
foreach ($cmd in $pythonCandidates) {
    try {
        $null = & $cmd -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $cmd
            break
        }
    } catch {}
}

if (-not $PythonCmd) {
    Write-Host "       Python no detectado. Intentando instalación automática vía winget..." -ForegroundColor Yellow
    try {
        winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements --scope user
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
        $PythonCmd = "python"
    } catch {
        Write-Host "       [AVISO] No fue posible instalar Python automáticamente." -ForegroundColor Red
        Write-Host "       Por favor instala Python 3.10+ desde https://www.python.org/downloads/" -ForegroundColor Red
    }
} else {
    Write-Host "       Python detectado correctamente: $PythonCmd" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# 3. INSTALACIÓN DE DEPENDENCIAS PYPI
# -----------------------------------------------------------------------------
Write-Host "[3/6] Verificando y sincronizando librerías del proyecto..." -ForegroundColor Yellow
Set-Location $InstallDir
if ($PythonCmd) {
    & $PythonCmd -m pip install -r "$InstallDir\config\requirements.txt" --quiet --disable-pip-version-check
    
    # Asegurar binario de Playwright (Chromium)
    Write-Host "       Asegurando navegador de automatización (Chromium)..." -ForegroundColor Gray
    & $PythonCmd -m playwright install chromium 2>$null | Out-Null
}

# -----------------------------------------------------------------------------
# 4. GENERACIÓN DE ICONO OFICIAL Y ACCESOS DIRECTOS
# -----------------------------------------------------------------------------
Write-Host "[4/6] Integrando accesos directos al Sistema Operativo..." -ForegroundColor Yellow

$logoPng = "$InstallDir\config\assets\iconos\robot_logo.png"
$logoIco = "$InstallDir\config\assets\iconos\robot_logo.ico"

# Generar .ico desde el .png mediante Python si existe PIL
if (Test-Path $logoPng) {
    try {
        if ($PythonCmd) {
            & $PythonCmd -c "from PIL import Image; img = Image.open(r'$logoPng'); img.save(r'$logoIco', format='ICO', sizes=[(256,256), (64,64), (32,32), (16,16)])" 2>$null
        }
    } catch {}
}

$WshShell = New-Object -ComObject WScript.Shell

# Acceso Directo en el Escritorio
$desktopPath = [System.Environment]::GetFolderPath("Desktop")
$desktopShortcut = $WshShell.CreateShortcut("$desktopPath\JsBOT.lnk")
$desktopShortcut.TargetPath = "$InstallDir\JsBOT_Sin_Consola.vbs"
$desktopShortcut.WorkingDirectory = $InstallDir
$desktopShortcut.Description = "JsBOT RPA - Sistema de Automatización"
if (Test-Path $logoIco) { $desktopShortcut.IconLocation = $logoIco }
$desktopShortcut.Save()

# Acceso Directo en el Menú Inicio
$startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$startShortcut = $WshShell.CreateShortcut("$startMenuPath\JsBOT.lnk")
$startShortcut.TargetPath = "$InstallDir\JsBOT_Sin_Consola.vbs"
$startShortcut.WorkingDirectory = $InstallDir
$startShortcut.Description = "JsBOT RPA - Sistema de Automatización"
if (Test-Path $logoIco) { $startShortcut.IconLocation = $logoIco }
$startShortcut.Save()

# -----------------------------------------------------------------------------
# 5. REGISTRO DEL COMANDO GLOBAL EN TERMINAL (PATH)
# -----------------------------------------------------------------------------
Write-Host "[5/6] Registrando comando global 'jsbot' en la terminal..." -ForegroundColor Yellow

$cmdWrapper = @"
@echo off
setlocal
cd /d "$InstallDir"
if "%~1"=="" (
    start "" wscript.exe "$InstallDir\JsBOT_Sin_Consola.vbs"
) else (
    call "$InstallDir\windows.bat" %*
)
"@
Set-Content -Path "$InstallDir\jsbot.cmd" -Value $cmdWrapper -Encoding ASCII

# Agregar $InstallDir al PATH del usuario si no está presente
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$InstallDir*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
    $env:Path = "$env:Path;$InstallDir"
}

# -----------------------------------------------------------------------------
# 6. TELEMETRÍA DE INSTALACIÓN Y ARRANQUE INICIAL
# -----------------------------------------------------------------------------
Write-Host "[6/6] Finalizando configuración y despachando inicio..." -ForegroundColor Yellow

if ($PythonCmd) {
    try {
        & $PythonCmd -c "import sys; sys.path.insert(0, r'$InstallDir'); from modulos.telemetria import registrar_evento_instalacion; registrar_evento_instalacion()" 2>$null
    } catch {}
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   ¡JsBOT v5.0.0 instalado y configurado con éxito!" -ForegroundColor Green
Write-Host "   • Acceso creado en el Escritorio" -ForegroundColor Gray
Write-Host "   • Acceso creado en el Menú de Inicio" -ForegroundColor Gray
Write-Host "   • Comando 'jsbot' disponible en cualquier terminal" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

# Lanzar JsBOT inmediatamente
Start-Process "wscript.exe" -ArgumentList "`"$InstallDir\JsBOT_Sin_Consola.vbs`"" -WorkingDirectory $InstallDir
