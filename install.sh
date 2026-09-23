#!/usr/bin/env bash
# ===============================================================================
# INSTALADOR EXPRESS ONE-LINE — JsBOT RPA v5.2.0 (Canaima / Debian / Linux)
# ===============================================================================
# Uso en Terminal (1 sola línea):
# curl -sSL https://raw.githubusercontent.com/CloverJH17/JsBOT/main/install.sh | bash
# ===============================================================================

set -e

echo -e "\033[1;36m========================================================\033[0m"
echo -e "\033[1;36m   JsBOT RPA v5.2.0 — Instalador Express Autónomo       \033[0m"
echo -e "\033[1;36m========================================================\033[0m"
echo ""

REPO_URL="https://github.com/CloverJH17/JsBOT.git"
ZIP_URL="https://github.com/CloverJH17/JsBOT/archive/refs/heads/main.zip"
INSTALL_DIR="$HOME/.local/share/JsBOT"

# -----------------------------------------------------------------------------
# 1. VERIFICACIÓN DE PAQUETES BASE DEL SISTEMA (PYTHON / PIP / TKINTER)
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[1/6] Verificando dependencias del sistema operativo...\033[0m"
PAQUETES_FALTANTES=()

for pkg in python3 python3-pip python3-tk python3-venv git curl; do
    if command -v dpkg &> /dev/null; then
        if ! dpkg -s "$pkg" &> /dev/null; then
            PAQUETES_FALTANTES+=("$pkg")
        fi
    fi
done

if [ ${#PAQUETES_FALTANTES[@]} -ne 0 ]; then
    echo -e "       Instalando paquetes base requeridos: ${PAQUETES_FALTANTES[*]}"
    if command -v pkexec &> /dev/null; then
        pkexec apt-get update && pkexec apt-get install -y "${PAQUETES_FALTANTES[@]}"
    elif command -v sudo &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y "${PAQUETES_FALTANTES[@]}"
    else
        echo -e "\033[1;31m[AVISO] No se obtuvieron permisos para instalar paquetes base.\033[0m"
    fi
fi

# -----------------------------------------------------------------------------
# 2. PREPARACIÓN O ACTUALIZACIÓN DEL DIRECTORIO DE INSTALACIÓN
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[2/6] Preparando directorio de instalación en ~/.local/share/JsBOT...\033[0m"
mkdir -p "$INSTALL_DIR"

if command -v git &> /dev/null; then
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "       Actualizando repositorio existente con Git..."
        git -C "$INSTALL_DIR" pull origin main --quiet
    else
        echo "       Clonando repositorio con Git..."
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    fi
else
    echo "       Descargando paquete de GitHub vía ZIP..."
    TEMP_ZIP="/tmp/JsBOT_install.zip"
    TEMP_DIR="/tmp/JsBOT_extract"
    curl -sSL "$ZIP_URL" -o "$TEMP_ZIP"
    rm -rf "$TEMP_DIR" && mkdir -p "$TEMP_DIR"
    unzip -q "$TEMP_ZIP" -d "$TEMP_DIR"
    cp -r "$TEMP_DIR"/JsBOT-main/* "$INSTALL_DIR"/
    rm -rf "$TEMP_ZIP" "$TEMP_DIR"
fi

chmod +x "$INSTALL_DIR/linux.sh"

# -----------------------------------------------------------------------------
# 3. INSTALACIÓN DE DEPENDENCIAS PYPI
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[3/6] Sincronizando librerías Python requeridas...\033[0m"
python3 -m pip install -r "$INSTALL_DIR/config/requirements.txt" --break-system-packages --quiet --disable-pip-version-check

echo "       Asegurando navegador de automatización (Chromium)..."
python3 -m playwright install chromium 2>/dev/null || true

# -----------------------------------------------------------------------------
# 4. INTEGRACIÓN AL SISTEMA OPERATIVO (.DESKTOP EN MENÚ Y ESCRITORIO)
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[4/6] Integrando acceso directo al menú de aplicaciones y escritorio...\033[0m"
mkdir -p "$HOME/.local/share/applications"
LOGO_PATH="$INSTALL_DIR/config/assets/iconos/robot_logo.png"

DESKTOP_ENTRY="[Desktop Entry]
Version=1.0
Type=Application
Name=JsBOT RPA
GenericName=Sistema de Automatización y Auditoría
Comment=Robot de Automatización de Procesos RPA
Exec=bash $INSTALL_DIR/linux.sh
Icon=$LOGO_PATH
Terminal=false
Categories=Office;Utility;
StartupNotify=true
"

echo "$DESKTOP_ENTRY" > "$HOME/.local/share/applications/jsbot.desktop"
chmod +x "$HOME/.local/share/applications/jsbot.desktop"

# Copiar al Escritorio si existe la carpeta Desktop o Escritorio
for desk in "$HOME/Escritorio" "$HOME/Desktop"; do
    if [ -d "$desk" ]; then
        cp "$HOME/.local/share/applications/jsbot.desktop" "$desk/jsbot.desktop"
        chmod +x "$desk/jsbot.desktop"
        # Marcar como ejecutable confiable si gio está disponible (GNOME / XFCE)
        command -v gio &> /dev/null && gio set "$desk/jsbot.desktop" metadata::trusted true 2>/dev/null || true
    fi
done

# -----------------------------------------------------------------------------
# 5. REGISTRO DEL COMANDO GLOBAL EN TERMINAL (~/.local/bin/jsbot)
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[5/6] Creando comando global 'jsbot' en la terminal...\033[0m"
mkdir -p "$HOME/.local/bin"

cat << 'EOF' > "$HOME/.local/bin/jsbot"
#!/usr/bin/env bash
INSTALL_DIR="$HOME/.local/share/JsBOT"
cd "$INSTALL_DIR"
exec bash linux.sh "$@"
EOF

chmod +x "$HOME/.local/bin/jsbot"

# Asegurar que ~/.local/bin esté en el PATH si no está
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
            break
        fi
    done
fi

# -----------------------------------------------------------------------------
# 6. TELEMETRÍA DE INSTALACIÓN Y ARRANQUE INICIAL
# -----------------------------------------------------------------------------
echo -e "\033[1;33m[6/6] Finalizando configuración y despachando inicio...\033[0m"

python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from modulos.telemetria import registrar_evento_instalacion; registrar_evento_instalacion()" 2>/dev/null || true

echo ""
echo -e "\033[1;32m========================================================\033[0m"
echo -e "\033[1;32m   ¡JsBOT v5.2.0 instalado y configurado con éxito!     \033[0m"
echo -e "\033[1;37m   • Acceso creado en el Menú de Aplicaciones          \033[0m"
echo -e "\033[1;37m   • Acceso creado en el Escritorio                    \033[0m"
echo -e "\033[1;37m   • Comando 'jsbot' disponible en cualquier terminal  \033[0m"
echo -e "\033[1;32m========================================================\033[0m"
echo ""

# Lanzar JsBOT inmediatamente en segundo plano
nohup bash "$INSTALL_DIR/linux.sh" >/dev/null 2>&1 &
