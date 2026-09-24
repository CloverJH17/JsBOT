#Requires -Version 5.1
<#
===============================================================================
DESINSTALADOR LIMPIO — JsBOT RPA (Microsoft Windows)
===============================================================================
Elimina accesos directos, comando del PATH y archivos de instalación,
con opción de respaldar planillas y reportes locales generados.
===============================================================================
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Red
Write-Host "   Desinstalador de JsBOT RPA" -ForegroundColor Red
Write-Host "========================================================" -ForegroundColor Red
Write-Host ""

$InstallDir = "$env:LOCALAPPDATA\JsBOT"

if (-not (Test-Path $InstallDir)) {
    Write-Host "[INFO] No se encontró una instalación de JsBOT en $InstallDir." -ForegroundColor Yellow
    exit 0
}

$confirm = Read-Host "¿Está seguro de que desea desinstalar JsBOT de este equipo? (S/N)"
if ($confirm -notmatch "^[sSyY]$") {
    Write-Host "Desinstalación cancelada por el usuario." -ForegroundColor Gray
    exit 0
}

# Preguntar si desea respaldar planillas y reportes
$backupConfirm = Read-Host "¿Desea conservar una copia de seguridad de sus Planillas y Reportes? (S/N)"
if ($backupConfirm -match "^[sSyY]$") {
    $backupDir = "$HOME\Documents\JsBOT_Respaldo"
    Write-Host "Creando respaldo en $backupDir..." -ForegroundColor Yellow
    New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
    
    if (Test-Path "$InstallDir\Planillas") {
        Copy-Item -Path "$InstallDir\Planillas" -Destination "$backupDir\Planillas" -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "$InstallDir\Reportes_Auditoria") {
        Copy-Item -Path "$InstallDir\Reportes_Auditoria" -Destination "$backupDir\Reportes_Auditoria" -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Respaldo completado con éxito en: $backupDir" -ForegroundColor Green
}

# 1. Eliminar accesos directos
Write-Host "Eliminando accesos directos del sistema..." -ForegroundColor Yellow
$desktopShortcut = "$([System.Environment]::GetFolderPath('Desktop'))\JsBOT.lnk"
$startShortcut   = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\JsBOT.lnk"

if (Test-Path $desktopShortcut) { Remove-Item $desktopShortcut -Force -ErrorAction SilentlyContinue }
if (Test-Path $startShortcut)   { Remove-Item $startShortcut -Force -ErrorAction SilentlyContinue }

# 3. Remover del PATH de usuario
Write-Host "Retirando comando de la terminal (PATH)..." -ForegroundColor Yellow
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -like "*$InstallDir*") {
    $newPath = ($userPath -split ';' | Where-Object { $_ -ne $InstallDir -and $_ -ne "" }) -join ';'
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

# 4. Eliminar directorio de instalación
Write-Host "Eliminando archivos del programa..." -ForegroundColor Yellow
Set-Location $HOME
Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   ¡JsBOT ha sido desinstalado correctamente!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
