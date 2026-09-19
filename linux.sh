#!/usr/bin/env bash
cd "$(dirname "$0")"

# -----------------------------------------------------------------------------
# 1. VERIFICACIÓN E INSTALACIÓN PRIORITARIA DE PYTHON Y DEPENDENCIAS DEL SISTEMA
# -----------------------------------------------------------------------------
PAQUETES_BASE=()
for pkg in python3 python3-pip python3-tk python3-venv; do
    if ! dpkg -s "$pkg" &> /dev/null; then
        PAQUETES_BASE+=("$pkg")
    fi
done

if [ ${#PAQUETES_BASE[@]} -ne 0 ]; then
    echo "🔍 Instalando soporte Python y paquetes base del sistema: ${PAQUETES_BASE[*]}"
    if command -v pkexec &> /dev/null; then
        pkexec apt-get update && pkexec apt-get install -y "${PAQUETES_BASE[@]}"
    elif command -v sudo &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y "${PAQUETES_BASE[@]}"
    else
        echo "❌ No se encontraron permisos de administrador (pkexec/sudo) para instalar: ${PAQUETES_BASE[*]}"
        echo "   Por favor ejecuta: sudo apt install ${PAQUETES_BASE[*]}"
        read -p "Presiona Enter para continuar..."
    fi
fi

# -----------------------------------------------------------------------------
# 2. LECTURA DINÁMICA DE VERSIÓN
# -----------------------------------------------------------------------------
JSBOT_VER=$(python3 -c "import sys; sys.path.insert(0, '.'); import modulos.version as _v; print(_v.__version__)" 2>/dev/null)
[ -z "$JSBOT_VER" ] && JSBOT_VER="4.8.0"

echo "========================================================"
echo "  JsBOT v${JSBOT_VER} — Entorno Canaima / Debian GNU/Linux"
echo "========================================================"

# -----------------------------------------------------------------------------
# 3. VERIFICACIÓN E INSTALACIÓN DE DEPENDENCIAS PYPI
# -----------------------------------------------------------------------------
echo "🔍 Verificando paquetes Python del proyecto..."
if ! python3 -c "import pandas, playwright, python_calamine, PIL, openpyxl, customtkinter, InquirerPy, rich, bs4, requests" &> /dev/null; then
    echo "📦 Descargando librerías requeridas desde PyPI..."
    python3 -m pip install -r config/requirements.txt --break-system-packages
    if [ $? -ne 0 ]; then
        echo "❌ Error durante la instalación de paquetes PyPI."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo "🔍 Asegurando navegador Playwright (Chromium)..."
    python3 -m playwright install chromium 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# 4. FORZAR ESTABILIDAD EN SERVIDOR GRÁFICO X11
# -----------------------------------------------------------------------------
export LIBGL_ALWAYS_SOFTWARE=1
clear

# -----------------------------------------------------------------------------
# 5. LANZAMIENTO DE JSBOT CON FALLBACK BIMODAL AUTOMÁTICO
# -----------------------------------------------------------------------------
python3 main.py "$@"

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ Fallo en el servidor gráfico X11 al levantar CustomTkinter."
    echo "🔄 Conmutando automáticamente a modo seguro por consola (CLI)..."
    python3 main.py --cli
fi
