#!/usr/bin/env bash
# ===============================================================================
# DESINSTALADOR LIMPIO — JsBOT RPA (Canaima / Debian / Linux)
# ===============================================================================

echo -e "\033[1;31m========================================================\033[0m"
echo -e "\033[1;31m   Desinstalador de JsBOT RPA (Linux)                   \033[0m"
echo -e "\033[1;31m========================================================\033[0m"
echo ""

INSTALL_DIR="$HOME/.local/share/JsBOT"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "No se encontró una instalación de JsBOT en $INSTALL_DIR."
    exit 0
fi

read -p "¿Está seguro de que desea desinstalar JsBOT de este equipo? (s/N): " confirm
if [[ ! "$confirm" =~ ^[sSyY]$ ]]; then
    echo "Desinstalación cancelada por el usuario."
    exit 0
fi

# Preguntar por respaldo de planillas
read -p "¿Desea conservar una copia de seguridad de sus Planillas y Reportes? (s/N): " backup_confirm
if [[ "$backup_confirm" =~ ^[sSyY]$ ]]; then
    BACKUP_DIR="$HOME/JsBOT_Respaldo"
    echo "Creando respaldo en $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    [ -d "$INSTALL_DIR/Planillas" ] && cp -r "$INSTALL_DIR/Planillas" "$BACKUP_DIR/"
    [ -d "$INSTALL_DIR/Reportes_Auditoria" ] && cp -r "$INSTALL_DIR/Reportes_Auditoria" "$BACKUP_DIR/"
    echo "Respaldo completado en $BACKUP_DIR."
fi

# 1. Eliminar accesos directos
echo "Eliminando accesos directos y entradas de menú..."
rm -f "$HOME/.local/share/applications/jsbot.desktop"
rm -f "$HOME/Escritorio/jsbot.desktop"
rm -f "$HOME/Desktop/jsbot.desktop"

# 3. Eliminar comando global
rm -f "$HOME/.local/bin/jsbot"

# 4. Eliminar directorio de instalación
echo "Eliminando archivos del programa..."
rm -rf "$INSTALL_DIR"

echo ""
echo -e "\033[1;32m========================================================\033[0m"
echo -e "\033[1;32m   ¡JsBOT ha sido desinstalado correctamente!           \033[0m"
echo -e "\033[1;32m========================================================\033[0m"
