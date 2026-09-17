#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "========================================================"
echo "  JsBOT v4.3.0 — Entorno Canaima GNU/Linux (PyPI Fast)"
echo "========================================================"

# 1. Asegurar binarios críticos del sistema operativo
PAQUETES_BASE=()
for pkg in python3-tk python3-pip; do
    if ! dpkg -s "$pkg" &> /dev/null; then
        PAQUETES_BASE+=("$pkg")
    fi
done

if [ ${#PAQUETES_BASE[@]} -ne 0 ]; then
    echo "🔍 Instalando soporte gráfico y gestor base: ${PAQUETES_BASE[*]}"
    if command -v pkexec &> /dev/null; then
        pkexec apt-get install -y "${PAQUETES_BASE[@]}"
    elif command -v sudo &> /dev/null; then
        sudo apt-get install -y "${PAQUETES_BASE[@]}"
    fi
fi

# 2. Instalación rápida de dependencias vía Wheels precompilados (Bypass PEP 668)
echo "🔍 Verificando paquetes Python del proyecto..."
if ! python3 -c "import pandas, selenium, PIL, openpyxl, customtkinter, InquirerPy, rich" &> /dev/null; then
    echo "📦 Descargando librerías precompiladas desde PyPI (esto tomará pocos segundos)..."
    python3 -m pip install -r requirements.txt --break-system-packages
    if [ $? -ne 0 ]; then
        echo "❌ Error durante la instalación de paquetes PyPI."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
fi

# 3. Forzar estabilidad en servidor gráfico X11
export LIBGL_ALWAYS_SOFTWARE=1
clear

# 4. Lanzamiento de JsBOT con fallback bimodal automático
python3 main.py "$@"

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ Fallo en el servidor gráfico X11 al levantar CustomTkinter."
    echo "🔄 Conmutando automáticamente a modo seguro por consola (CLI)..."
    python3 main.py --cli
fi
