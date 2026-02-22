#!/usr/bin/env bash
#
# Monster TULPAR T5 - Donanım Kontrolcüsü Kurulum Betiği
#
set -e

APP_NAME="monster-hw-ctrl"
INSTALL_DIR="/opt/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Renk tanımları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[UYARI]${NC} $1"; }
error() { echo -e "${RED}[HATA]${NC} $1"; }

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    error "Bu betik root yetkisi ile çalıştırılmalıdır."
    echo "  sudo bash install.sh"
    exit 1
fi

# Kaldırma modu — kurulumdan önce kontrol et
if [ "${1}" = "--uninstall" ]; then
    echo ""
    info "Kaldırılıyor..."

    systemctl stop monster-hw-ctrl 2>/dev/null || true
    systemctl disable monster-hw-ctrl 2>/dev/null || true

    rm -f /etc/systemd/system/monster-hw-ctrl.service
    rm -f /usr/share/polkit-1/actions/com.monster.hwctrl.policy
    rm -f /usr/share/applications/monster-hw-ctrl.desktop
    rm -f /usr/local/bin/monster-hw-ctrl
    rm -rf "$INSTALL_DIR"

    systemctl daemon-reload

    ok "Kaldırma tamamlandı"
    exit 0
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Monster TULPAR T5 V19.2 - Donanım Kontrolcüsü ║"
echo "║  Kurulum Betiği                                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Bağımlılıkları kontrol et ve kur
info "Bağımlılıklar kontrol ediliyor..."

PACKAGES="python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-psutil"
MISSING=""

for pkg in $PACKAGES; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    info "Eksik paketler kuruluyor:$MISSING"
    apt-get update -qq
    apt-get install -y -qq $MISSING
    ok "Bağımlılıklar kuruldu"
else
    ok "Tüm bağımlılıklar mevcut"
fi

# 2. Uygulama dosyalarını kopyala
info "Dosyalar kopyalanıyor: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/" 2>/dev/null || true
ok "Uygulama dosyaları kopyalandı"

# 3. Systemd servisini kur
info "Systemd servisi kuruluyor..."
cp "$SCRIPT_DIR/systemd/monster-hw-ctrl.service" /etc/systemd/system/
systemctl daemon-reload
ok "Systemd servisi kuruldu"

# 4. PolicyKit kuralını kur
info "PolicyKit kuralı kuruluyor..."
cp "$SCRIPT_DIR/polkit/com.monster.hwctrl.policy" /usr/share/polkit-1/actions/
ok "PolicyKit kuralı kuruldu"

# 5. ec_sys modülünü yükle
info "EC modülü kontrol ediliyor..."
if modprobe ec_sys write_support=1 2>/dev/null; then
    ok "ec_sys modülü yüklendi (write_support=1)"
    
    # Kalıcı yükleme
    if ! grep -q "ec_sys" /etc/modules-load.d/*.conf 2>/dev/null; then
        echo "ec_sys" > /etc/modules-load.d/ec_sys.conf
        echo "options ec_sys write_support=1" > /etc/modprobe.d/ec_sys.conf
        ok "ec_sys modülü kalıcı olarak ayarlandı"
    fi
else
    warn "ec_sys modülü yüklenemedi. Fan kontrolü çalışmayabilir."
fi

# 6. Masaüstü kısayolu oluştur
info "Masaüstü kısayolu oluşturuluyor..."
cat > /usr/share/applications/monster-hw-ctrl.desktop << EOF
[Desktop Entry]
Name=Monster HW Controller
Comment=Monster TULPAR T5 Donanım Kontrolcüsü
Exec=pkexec /usr/bin/python3 /opt/monster-hw-ctrl/src/main.py
Path=/opt/monster-hw-ctrl
Icon=preferences-system
Terminal=false
Type=Application
Categories=System;Settings;HardwareSettings;
Keywords=fan;cpu;gpu;temperature;hardware;monster;tulpar;
EOF
ok "Masaüstü kısayolu oluşturuldu"

# 7. Çalıştırma betiği
cat > /usr/local/bin/monster-hw-ctrl << 'EOF'
#!/usr/bin/env bash
cd /opt/monster-hw-ctrl
exec python3 -m src.main "$@"
EOF
chmod +x /usr/local/bin/monster-hw-ctrl
ok "Çalıştırma betiği: /usr/local/bin/monster-hw-ctrl"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Kurulum tamamlandı!                            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                 ║"
echo "║  Çalıştırma:                                    ║"
echo "║    sudo monster-hw-ctrl        (tam kontrol)    ║"
echo "║    monster-hw-ctrl             (sadece izleme)  ║"
echo "║                                                 ║"
echo "║  Daemon başlatma:                               ║"
echo "║    sudo systemctl start monster-hw-ctrl         ║"
echo "║    sudo systemctl enable monster-hw-ctrl        ║"
echo "║                                                 ║"
echo "║  Kaldırma:                                      ║"
echo "║    sudo bash install.sh --uninstall             ║"
echo "║                                                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""


