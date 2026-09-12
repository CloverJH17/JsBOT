#!/usr/bin/env bash
set -e
echo "========================================================"
echo "  JsBOT v4.0.0 — Descarga e Instalación Automatizada"
echo "========================================================"
DESTINO="$HOME/JsBOT"
if [ -d "$DESTINO" ]; then
    echo "[*] Directorio detectado. Actualizando..."
    cd "$DESTINO" && git pull origin main
else
    echo "[*] Clonando repositorio oficial..."
    git clone https://github.com/CloverJH17/JsBOT.git "$DESTINO"
    cd "$DESTINO"
fi
chmod +x "$DESTINO/linux.sh"
echo "[✓] Instalación lista. Iniciando aplicación..."
"$DESTINO/linux.sh" "$@"
