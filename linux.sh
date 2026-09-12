#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "🔍 Verificando entorno de ejecución..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado en este equipo."
    echo "💡 Instálalo con: sudo apt update && sudo apt install -y python3 python3-pip python3-tk"
    read -p "Presiona Enter para salir..."
    exit 1
fi

if ! python3 -m pip --version &> /dev/null; then
    echo "⚠️ pip no detectado. Intentando instalar python3-pip y dependencias del sistema..."
    if command -v pkexec &> /dev/null; then
        pkexec apt-get update && pkexec apt-get install -y python3-pip python3-tk
    elif command -v sudo &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip python3-tk
    else
        echo "❌ Se requieren permisos de administrador para instalar pip y python3-tk."
        echo "💡 Ejecuta manualmente: sudo apt install -y python3-pip python3-tk"
        read -p "Presiona Enter para salir..."
        exit 1
    fi
fi

if ! python3 -c "import pandas, customtkinter, selenium" &> /dev/null; then
    echo "📦 Instalando dependencias de JsBOT por primera vez... (espera un momento)"
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error al instalar las dependencias de requirements.txt."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
fi

export LIBGL_ALWAYS_SOFTWARE=1
clear
python3 main.py "$@"

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ Se detectó un fallo al abrir la ventana gráfica (posible incompatibilidad X11/display)."
    echo "🔄 Conmutando automáticamente a modo seguro por consola (CLI)..."
    python3 main.py --cli
fi
