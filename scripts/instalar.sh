#!/usr/bin/env bash
set -e

echo "========================================================"
echo "  JsBOT v4.10.0 — Descarga e Instalación Automatizada"
echo "========================================================"

DESTINO="$HOME/JsBOT"

if [ -d "$DESTINO" ]; then
    echo "[*] Directorio detectado en $DESTINO. Actualizando..."
    cd "$DESTINO" && git pull origin main || true
else
    echo "[*] Clonando repositorio oficial en $DESTINO..."
    git clone https://github.com/CloverJH17/JsBOT.git "$DESTINO"
    cd "$DESTINO"
fi

chmod +x "$DESTINO/linux.sh"
echo "[✓] Instalación lista. Iniciando aplicación..."
exec "$DESTINO/linux.sh" "$@"
