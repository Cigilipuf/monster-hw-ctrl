<div align="center">

# 🖥️ Monster TULPAR T5 — Linux Hardware Controller
### Clevo Tabanlı Dizüstü Bilgisayar için Kapsamlı Donanım Yöneticisi
### Comprehensive Hardware Manager for Clevo-Based Laptops on Linux

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GTK](https://img.shields.io/badge/GTK-3.0-4A86CF?logo=gnome&logoColor=white)](https://gtk.org/)
[![Platform](https://img.shields.io/badge/Platform-Pop!__OS%20%7C%20Ubuntu%20%7C%20Debian-48B9C7?logo=linux&logoColor=white)](https://pop.system76.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()

> **Pop!_OS 22.04 / Ubuntu 22.04+ / Debian 12+** üzerinde çalışan,
> Monster TULPAR T5 (Clevo-tabanlı) için CPU, GPU ve fan kontrol uygulaması.
>
> A full-featured CPU, GPU & fan control application for Monster TULPAR T5
> (Clevo-based) laptops running **Pop!_OS 22.04 / Ubuntu 22.04+ / Debian 12+**.

</div>

---

## ⚠️ Sorumluluk Reddi Beyanı / Disclaimer

> **TÜRKÇE:** Bu yazılım "olduğu gibi" (AS-IS) sunulmaktadır. Yazılımın kullanımından doğabilecek her türlü donanım hasarı, veri kaybı, sistem arızası veya diğer olumsuz sonuçlardan **yalnızca kullanıcı sorumludur**. Geliştirici(ler) hiçbir koşulda sorumluluk kabul etmez. EC registerlarına yanlış değer yazmak, fan hızını aşırı düşürmek veya CPU/GPU limitlerini yanlış ayarlamak donanımınıza kalıcı zarar verebilir. **Bu yazılımı kullanmadan önce risklerini tam olarak anladığınızdan emin olun.**
>
> **ENGLISH:** This software is provided "AS IS", without warranty of any kind. The user assumes **full and sole responsibility** for any hardware damage, data loss, system failure, or other adverse outcomes resulting from the use of this software. The developer(s) accept no liability under any circumstances. Writing incorrect values to EC registers, setting fan speeds too low, or misconfiguring CPU/GPU limits may cause permanent hardware damage. **Make sure you fully understand the risks before using this software.**

---

## 📋 İçindekiler / Table of Contents

| 🇹🇷 Türkçe | 🇬🇧 English |
|---|---|
| [Özellikler](#-özellikler) | [Features](#-features) |
| [Desteklenen Donanım](#-desteklenen-donanım) | [Supported Hardware](#-supported-hardware) |
| [Kurulum](#-kurulum) | [Installation](#-installation) |
| [Kullanım](#-kullanım) | [Usage](#-usage) |
| [Güç Profilleri](#-güç-profilleri) | [Power Profiles](#-power-profiles) |
| [Mimari](#-mimari) | [Architecture](#-architecture) |
| [Güvenlik](#-güvenlik-notları) | [Safety Notes](#-güvenlik-notları) |
| [Katkıda Bulunma](#-katkıda-bulunma) | [Contributing](#-katkıda-bulunma) |
| [Lisans](#-lisans) | [License](#-lisans) |

---

## ✨ Özellikler

| Kategori | Özellik |
|---|---|
| 🌡️ **İzleme** | Gerçek zamanlı CPU çekirdek sıcaklıkları, GPU sıcaklığı, PCH, NVMe, WiFi sensörleri |
| ⚡ **CPU Kontrolü** | `intel_pstate` governor yönetimi, min/max frekans, Turbo Boost açma/kapama, EPP ayarı |
| 🎮 **NVIDIA GPU** | Güç limiti (10-90W), saat hızı sınırlama, nvidia-smi entegrasyonu |
| 🔷 **Intel iGPU** | CometLake-H GT2 frekans kontrolü (350-1150 MHz) |
| 🌀 **Fan Kontrolü** | EC (Embedded Controller) tabanlı doğrudan fan kontrolü, özelleştirilebilir fan eğrisi |
| 🛡️ **Termal Koruma** | 88°C sert sınır — profilden bağımsız, otomatik throttle & uyarı |
| 📊 **Dashboard** | Sıcaklık geçmişi grafikleri, canlı frekans ve güç tüketimi |
| 🎯 **Profiller** | Sessiz / Dengeli / Performans / Oyun / Pil Tasarrufu profilleri |
| 🔔 **Bildirimler** | libnotify/D-Bus ile masaüstü sıcaklık uyarıları |
| 💻 **CLI** | `--daemon`, `--status`, `--profile <isim>` komut satırı desteği |
| 🖥️ **Sistem Tepsisi** | AppIndicator tabanlı sistem tepsisi ikonu |

## ✨ Features

| Category | Feature |
|---|---|
| 🌡️ **Monitoring** | Real-time CPU core temps, GPU temperature, PCH, NVMe, WiFi sensors |
| ⚡ **CPU Control** | `intel_pstate` governor management, min/max frequency, Turbo Boost toggle, EPP setting |
| 🎮 **NVIDIA GPU** | Power limit control (10-90W), clock speed limits, nvidia-smi integration |
| 🔷 **Intel iGPU** | CometLake-H GT2 frequency control (350-1150 MHz) |
| 🌀 **Fan Control** | EC (Embedded Controller) direct fan control with customizable fan curve |
| 🛡️ **Thermal Guard** | 88°C hard limit — profile-independent, auto throttle & alert |
| 📊 **Dashboard** | Temperature history graphs, live frequency and power draw |
| 🎯 **Profiles** | Silent / Balanced / Performance / Gaming / Battery Saver profiles |
| 🔔 **Notifications** | Desktop temperature alerts via libnotify/D-Bus |
| 💻 **CLI** | `--daemon`, `--status`, `--profile <name>` command-line support |
| 🖥️ **System Tray** | AppIndicator-based system tray icon |

---

## 🖥️ Desteklenen Donanım / Supported Hardware

Bu uygulama Monster TULPAR T5 V19.2 için optimize edilmiştir; benzer Clevo OEM modellerinde de çalışabilir.
Optimized for Monster TULPAR T5 V19.2. May work on other Clevo-based OEM laptops.

| Bileşen / Component | Model |
|---|---|
| **CPU** | Intel Core i7-10750H (Comet Lake-H, 6C/12T, 2.6–5.0 GHz) |
| **GPU (dGPU)** | NVIDIA GeForce RTX 2060 Mobile — 6 GB GDDR6 (10–90W TDP) |
| **GPU (iGPU)** | Intel UHD Graphics 630 (CometLake-H GT2) |
| **EC Chip** | Clevo Embedded Controller (EC register-based fan control) |
| **Kernel Driver** | `intel_pstate` (active mode), `ec_sys` |
| **OS** | Pop!_OS 22.04 LTS, Ubuntu 22.04+, Debian 12+ |
| **Kernel** | Linux 5.15+ (tested on 6.x) |

> **💡 Other Clevo models:** The EC register map (`config/ec_register_map.json`) is configurable. Refer to [YoyPa/isw](https://github.com/YoyPa/isw) for EC maps of other Clevo variants.

---

## 📦 Kurulum / Installation

### Gereksinimler / Requirements

```bash
# Sistem paketleri / System packages
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
     gir1.2-appindicator3-0.1 gir1.2-notify-0.7 libnotify-bin

# Python bağımlılıkları / Python dependencies
pip3 install psutil
```

### Hızlı Kurulum / Quick Install

```bash
git clone https://github.com/YOUR_USERNAME/monster-hw-ctrl.git
cd monster-hw-ctrl
sudo bash install.sh
```

`install.sh` şunları yapar / `install.sh` performs:
- Uygulama dosyalarını `/opt/monster-hw-ctrl/` dizinine kopyalar / Copies files to `/opt/monster-hw-ctrl/`
- Systemd servisini kurar / Installs the systemd service
- PolicyKit kuralını yükler / Installs the PolicyKit policy
- `/usr/local/bin/monster-hw-ctrl` başlatıcısını oluşturur / Creates the launcher binary
- Masaüstü kısayolu oluşturur / Creates a `.desktop` shortcut

### EC Modülünü Yükle / Load EC Module

```bash
# Manuel yükleme / Manual load
sudo modprobe ec_sys write_support=1

# Kalıcı hale getirme / Make persistent
echo "ec_sys write_support=1" | sudo tee /etc/modprobe.d/ec_sys.conf
```

### Kaldırma / Uninstall

```bash
sudo bash install.sh --uninstall
```

---

## 🚀 Kullanım / Usage

### GUI

```bash
# Normal kullanıcı — sadece izleme / Read-only monitoring
monster-hw-ctrl

# Tam kontrol (pkexec otomatik yetki yükseltir / pkexec elevates automatically)
monster-hw-ctrl
```

### CLI

```bash
# Mevcut durum / Current status
monster-hw-ctrl --status

# Profil uygula / Apply a profile
sudo monster-hw-ctrl --profile performance
sudo monster-hw-ctrl --profile silent
sudo monster-hw-ctrl --profile balanced
sudo monster-hw-ctrl --profile gaming
sudo monster-hw-ctrl --profile battery

# Daemon modu / Daemon mode
sudo monster-hw-ctrl --daemon
```

### Systemd Servisi / Systemd Service

```bash
sudo systemctl start monster-hw-ctrl
sudo systemctl enable monster-hw-ctrl     # Başlangıçta otomatik / Auto-start
systemctl status monster-hw-ctrl
journalctl -u monster-hw-ctrl -f          # Loglar / Logs
```

---

## 🎯 Güç Profilleri / Power Profiles

> **⚠️** Tüm profillerde **88°C sert sıcaklık limiti** aktiftir — devre dışı bırakılamaz.
> All profiles enforce a **hard 88°C thermal limit** — cannot be disabled.

| Profil / Profile | CPU Gov | EPP | Turbo | CPU Max | GPU Güç/Power | Fan |
|---|---|---|---|---|---|---|
| 🔇 **Sessiz / Silent** | powersave | power | ❌ | 2.6 GHz | 30W | Düşük / Low |
| ⚖️ **Dengeli / Balanced** | powersave | balance_perf | ✅ | 4.0 GHz | 60W | Otomatik / Auto |
| 🚀 **Performans / Performance** | performance | performance | ✅ | 5.0 GHz | 90W | Yüksek / High |
| 🎮 **Oyun / Gaming** | performance | performance | ✅ | 5.0 GHz | 90W | Maksimum |
| 🔋 **Pil / Battery** | powersave | power | ❌ | 1.5 GHz | 10W | Minimum |

---

## 🏗️ Mimari / Architecture

```
monster-hw-ctrl/
├── src/
│   ├── main.py                    # Giriş noktası / Entry point (GUI + CLI + daemon)
│   ├── core/
│   │   ├── cpu_controller.py      # intel_pstate, governor, EPP, Turbo
│   │   ├── gpu_nvidia.py          # nvidia-smi: güç, saat, sıcaklık
│   │   ├── gpu_intel.py           # Intel iGPU sysfs frekans kontrolü
│   │   ├── fan_controller.py      # EC tabanlı fan kontrolü + otomatik eğri
│   │   ├── temp_monitor.py        # hwmon sensör okuma (dinamik keşif)
│   │   ├── thermal_protection.py  # 88°C sert sınır sistemi
│   │   ├── profile_manager.py     # JSON profil yönetimi
│   │   ├── notifier.py            # libnotify masaüstü bildirimleri
│   │   └── ec_access.py           # /sys/kernel/debug/ec/ec0/io erişimi
│   ├── gui/
│   │   ├── main_window.py         # Ana GTK3 penceresi
│   │   ├── dashboard.py           # Gerçek zamanlı izleme paneli
│   │   ├── cpu_panel.py           # CPU ayar paneli
│   │   ├── gpu_panel.py           # GPU ayar paneli
│   │   ├── fan_panel.py           # Fan kontrol + eğri editörü
│   │   ├── profile_panel.py       # Profil yönetim paneli
│   │   ├── tray_icon.py           # Sistem tepsisi ikonu
│   │   └── widgets/
│   │       ├── fan_curve.py       # Cairo tabanlı fan eğrisi çizici
│   │       ├── freq_slider.py     # Frekans kaydırıcı widget
│   │       ├── temp_gauge.py      # Dairesel sıcaklık göstergesi
│   │       └── temp_history.py    # Geçmiş sıcaklık grafiği
│   ├── daemon/
│   │   ├── hw_daemon.py           # Root yetkili arka plan servisi
│   │   └── dbus_interface.py      # D-Bus API
│   └── utils/
│       ├── config.py              # JSON konfigürasyon yöneticisi
│       └── logger.py              # Yapılandırılmış loglama
├── config/
│   ├── profiles/                  # Aktif güç profilleri (JSON)
│   └── ec_register_map.json       # EC register haritası (Clevo)
├── systemd/
│   └── monster-hw-ctrl.service
├── polkit/
│   └── com.monster.hwctrl.policy
├── install.sh
├── monster-hw-ctrl.sh
└── requirements.txt
```

| Katman / Layer | Teknoloji |
|---|---|
| Language | Python 3.10+ |
| GUI Framework | GTK3 (PyGObject / GObject Introspection) |
| Graphics | Cairo (fan curve, temperature gauge) |
| System Monitoring | `psutil`, `hwmon` sysfs, `nvidia-smi` |
| Fan Control | EC direct I/O via `ec_sys` kernel module |
| CPU Control | `intel_pstate` sysfs interface |
| GPU Control | `nvidia-smi` CLI + NVML, Intel DRM sysfs |
| IPC | D-Bus (daemon ↔ GUI) |
| Persistence | JSON (profiles, config) |
| Privilege Elevation | PolicyKit (`pkexec`) |
| Service | systemd |

---

## 🔒 Güvenlik Notları / Safety Notes

- **Fan:** Fan hızı asla %20'nin altına düşürülmez / Fan speed never drops below 20%
- **EC:** EC register adresleri varsayılan Clevo haritasını kullanır; yanlış register kullanımı donanıma zarar verebilir / Incorrect EC register usage may damage hardware
- **Termal / Thermal:** 88°C sert bariyer tüm profillerde aktiftir / 88°C hard barrier is active in all profiles
- **Kapatma / Shutdown:** Uygulama kapatılırken fanlar otomatik moda döner / Fans return to auto mode on exit

---

## 🤝 Katkıda Bulunma / Contributing

1. Fork → `git checkout -b feature/your-feature`
2. Commit → `git commit -m "feat: description"`
3. Push → `git push origin feature/your-feature`
4. Pull Request açın / Open a Pull Request

**Katkı alanları / Areas to contribute:**
- 🗺️ Diğer Clevo modelleri için EC register haritaları / EC maps for other Clevo models
- 🔧 BIOS sürümü uyumluluk yamaları / BIOS version compatibility patches
- 🌍 Çeviri / Translations
- 🧪 Test ve hata raporları / Bug reports

---

## 🙏 Teşekkürler / Acknowledgements

- [YoyPa/isw](https://github.com/YoyPa/isw) — Clevo EC register map reference
- [pop-os/system76-power](https://github.com/pop-os/system76-power) — Pop!_OS power management
- Linux kernel `intel_pstate`, `ec_sys`, `hwmon` subsystems

---

## 📜 Lisans / License

**GNU General Public License v3.0** (GPL-3.0) — see [LICENSE](LICENSE).

---

<div align="center">

**Monster TULPAR T5 V19.2 | Linux Hardware Controller**
*Intel i7-10750H · NVIDIA RTX 2060 Mobile · Clevo EC Fan Control*

Made with ❤️ for the Linux laptop community

</div>
