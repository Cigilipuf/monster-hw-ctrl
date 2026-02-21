#!/bin/bash
# Monster TULPAR T5 - Donanım Kontrolcüsü Başlatıcı
# Bu betik GUI'yi root yetkisiyle çalıştırır ve X11 erişimini sağlar.

# Use the directory where this script resides; fallback to install location
SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
if [ "$SCRIPT_DIR" = "/usr/local/bin" ]; then
    APP_DIR="/opt/monster-hw-ctrl"
else
    APP_DIR="$SCRIPT_DIR"
fi
PYTHON="/usr/bin/python3"

# Eğer root olarak çalıştırıldıysa (pkexec tarafından), 
# display bilgileri argüman olarak gelir
if [ "$EUID" -eq 0 ]; then
    export DISPLAY="${1:-:0}"
    export XAUTHORITY="${2:-/run/user/1000/gdm/Xauthority}"
    export XDG_RUNTIME_DIR="${3:-/run/user/1000}"
    export HOME="${4:-/root}"
    cd "$APP_DIR"
    exec "$PYTHON" -m src.main
fi

# Normal kullanıcı olarak çalışıyor — display bilgilerini kaydet ve pkexec ile yeniden çalıştır
CURR_DISPLAY="${DISPLAY:-:0}"
CURR_XAUTH="${XAUTHORITY:-$HOME/.Xauthority}"
CURR_XDG="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
CURR_HOME="$HOME"

# X11 root erişimine izin ver
xhost +local: >/dev/null 2>&1

exec pkexec "$0" "$CURR_DISPLAY" "$CURR_XAUTH" "$CURR_XDG" "$CURR_HOME"
