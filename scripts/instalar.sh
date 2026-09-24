#!/usr/bin/env bash
set -e

DESTINO="$HOME/JsBOT"

if [ -d "$DESTINO" ]; then
    echo "[*] Directorio detectado en $DESTINO. Actualizando..."
    cd "$DESTINO" && git pull origin main || true
else
    echo "[*] Clonando repositorio oficial en $DESTINO..."
    git clone https://github.com/CloverJH17/JsBOT.git "$DESTINO"
    cd "$DESTINO"
fi

VERSION=$(python3 -c "import sys; sys.path.insert(0, '$DESTINO'); from modulos.version import ETIQUETA_VERSION; print(ETIQUETA_VERSION)" 2>/dev/null || echo "RPA")

echo "========================================================"
echo "  JsBOT $VERSION — Descarga e Instalación Automatizada"
echo "========================================================"

chmod +x "$DESTINO/linux.sh"
echo "[✓] Instalación lista. Iniciando aplicación..."
exec "$DESTINO/linux.sh" "$@"
