# Monster TULPAR T5 V19.2 - Linux Donanım Kontrolcüsü (Hardware Controller)

## Proje Amacı
Monster TULPAR T5 V19.2 dizüstü bilgisayar için Pop!_OS (Debian/Ubuntu tabanlı) üzerinde çalışacak kapsamlı bir donanım kontrolcüsü geliştirmek. Bu uygulama; CPU, GPU (NVIDIA + Intel iGPU) frekans kontrolü, fan hız yönetimi, sıcaklık izleme ve güç profil yönetimi sağlayacak.

---

## Sistem Donanım Bilgileri

### Genel Bilgiler
- **Bilgisayar:** Monster TULPAR T5 V19.2 (Clevo tabanlı OEM)
- **Anakart Üreticisi:** MONSTER
- **BIOS:** American Megatrends Inc. (AMI), Sürüm N.1.07
- **İşletim Sistemi:** Pop!_OS 22.04 LTS (Ubuntu/Debian tabanlı)
- **Kernel:** 6.17.9-76061709-generic (x86_64)

### CPU - Intel Core i7-10750H
- **Mimari:** Comet Lake-H, 6 Çekirdek / 12 Thread
- **Taban Frekans:** 2.60 GHz
- **Minimum Frekans:** 800 MHz (800000 KHz)
- **Maksimum Frekans:** 5.00 GHz (5000000 KHz) - Turbo Boost
- **Sıcaklık Limitleri:** Max 100°C, Kritik 100°C
- **Frekans Sürücüsü:** `intel_pstate` (aktif mod)
- **Mevcut Governor:** `powersave`
- **Kullanılabilir Governor'lar:** `performance`, `powersave`
- **Energy Performance Preferences (EPP):** `default`, `performance`, `balance_performance`, `balance_power`, `power`
- **Turbo Boost:** Aktif (`no_turbo = 0`)
- **HWP Dynamic Boost:** Aktif
- **P-State Sayısı:** 43
- **Turbo Yüzdesi:** 56%
- **max_perf_pct:** 100
- **min_perf_pct:** 16

### GPU - NVIDIA GeForce RTX 2060 Mobile
- **PCI:** 01:00.0
- **Sürücü:** NVIDIA 580.119.02, CUDA 13.0
- **VRAM:** 6144 MiB
- **TDP:** 90W (min 10W - max 90W)
- **Mevcut Güç Tüketimi:** ~7W (boşta)
- **Saat Hızları:**
  - Graphics: 300 MHz (boşta) - 2100 MHz (maks)
  - Memory: 405 MHz (boşta) - 5501 MHz (maks)
  - SM: 300 MHz - 2100 MHz
  - Video: 540 MHz
- **Sıcaklık Limitleri:**
  - Mevcut: ~42°C
  - Slowdown: 93°C
  - Shutdown: 98°C
  - Max Operating: 102°C
  - Target: 87°C
- **Fan:** N/A (GPU fanı doğrudan nvidia-smi ile okunamıyor, EC üzerinden kontrol ediliyor)
- **Grafik Modu:** Hybrid (system76-power)

### Intel UHD Graphics (Entegre GPU)
- **PCI:** 00:02.0 (CometLake-H GT2)
- **DRM:** card0
- **Frekans Kontrol Dosyaları:** `/sys/class/drm/card0/`
  - `gt_act_freq_mhz`: Anlık aktif frekans
  - `gt_cur_freq_mhz`: İstenen frekans
  - `gt_min_freq_mhz`: 350 MHz (yazılabilir)
  - `gt_max_freq_mhz`: 1150 MHz (yazılabilir)
  - `gt_boost_freq_mhz`: 1150 MHz
  - `gt_RP0_freq_mhz`: 1150 MHz (donanım maks)
  - `gt_RP1_freq_mhz`: 350 MHz (donanım verimli)
  - `gt_RPn_freq_mhz`: 350 MHz (donanım min)

---

## Sıcaklık Sensörleri Haritası

### hwmon0 - AC0 (AC Adaptör)
- Sensör yok (sadece güç durumu)

### hwmon1 - acpitz (ACPI Termal Bölge)
- `temp1_input`: ACPI Zone 1 sıcaklığı
- `temp2_input`: ACPI Zone 2 sıcaklığı

### hwmon2 - BAT0 (Batarya)
- Sensör yok

### hwmon3 - nvme (NVMe SSD)
- `temp1_input`: Composite sıcaklık
- `temp3_input`: Ek sensör

### hwmon4 - pch_cometlake (PCH - Platform Controller Hub)
- `temp1_input`: PCH sıcaklığı

### hwmon5 - coretemp (CPU Sıcaklıkları)
- `temp1_input/label`: Package id 0 (CPU toplam)
- `temp2_input/label`: Core 0
- `temp3_input/label`: Core 1
- `temp4_input/label`: Core 2
- `temp5_input/label`: Core 3
- `temp6_input/label`: Core 4
- `temp7_input/label`: Core 5
- Her sensörde `_max` ve `_crit` limitleri mevcut (100°C)

### hwmon6 - iwlwifi_1 (WiFi Kartı)
- `temp1_input`: WiFi modül sıcaklığı

### NVIDIA GPU Sıcaklığı
- `nvidia-smi -q` komutu ile okunur
- Veya `nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader`

### Termal Bölgeler
- `thermal_zone0`: acpitz (~52°C)
- `thermal_zone1`: acpitz (~52°C)
- `thermal_zone2`: pch_cometlake (~47°C)
- `thermal_zone3`: iwlwifi_1 (~37°C)
- `thermal_zone4`: x86_pkg_temp (~63°C)

---

## Fan Kontrol Mekanizması

### Önemli Notlar
Bu bilgisayar Monster TULPAR T5 V19.2 olup **Clevo tabanlı** bir OEM'dir. Fan kontrolü standart `hwmon` üzerinden PWM arayüzü sunmamaktadır. Fanlar **Embedded Controller (EC)** üzerinden kontrol edilmektedir.

### Fan Kontrol Yöntemleri (Öncelik sırasına göre)

#### 1. EC (Embedded Controller) Doğrudan Erişimi (ÖNERİLEN)
- **Modül:** `ec_sys` (`/lib/modules/.../drivers/acpi/ec_sys.ko`)
- **Yükleme:** `sudo modprobe ec_sys write_support=1`
- **EC Registerleri:** `/sys/kernel/debug/ec/ec0/io`
- **Clevo EC Register Haritası (Yaygın):**
  - `0x68`: CPU Fan Duty (yazma, 0-255 veya 0-100)
  - `0x69`: GPU Fan Duty (yazma, 0-255 veya 0-100)
  - `0xCE`: CPU Fan RPM (okuma, LSB)
  - `0xCF`: CPU Fan RPM (okuma, MSB)
  - `0xD0`: GPU Fan RPM (okuma, LSB)
  - `0xD1`: GPU Fan RPM (okuma, MSB)
  - `0xD7`: Fan Auto/Manual modu (bit kontrolü)
  
  **NOT:** Bu register adresleri modele göre farklılık gösterebilir. Uygulama ilk çalıştırıldığında EC register keşfi yapmalı ve kullanıcıdan doğrulama almalıdır.

#### 2. /dev/port Erişimi (ALTERNATİF)
- `/dev/port` dosyası mevcut
- EC komut portu: 0x66
- EC data portu: 0x62
- Doğrudan port I/O ile EC'ye komut gönderilebilir
- Root yetkisi gerektirir

#### 3. ISW (Intel Silent Wings) Aracı Entegrasyonu
- Clevo laptoplar için geliştirilmiş açık kaynak araç
- GitHub: `YoyPa/isw`
- EC register haritası JSON konfigürasyonlarıyla çalışır
- Entegre edilebilir veya referans olarak kullanılabilir

### Soğutma Cihazları (cooling_device)
- `cooling_device0-2`: PCIe Port Link Speed kontrolü
- `cooling_device3-14`: CPU Processor throttling (0-3 seviye)
- `cooling_device15`: intel_powerclamp (0-100)
- `cooling_device16`: TCC Offset (0-63) - **CPU sıcaklık hedefi ayarlama**

---

## CPU Frekans Kontrol Arayüzü

### intel_pstate Sürücüsü
```
/sys/devices/system/cpu/intel_pstate/
├── no_turbo          # 0=Turbo aktif, 1=Turbo kapalı (yazılabilir, root)
├── max_perf_pct      # Maksimum performans yüzdesi (yazılabilir, root)
├── min_perf_pct      # Minimum performans yüzdesi (yazılabilir, root)
├── hwp_dynamic_boost # HWP dinamik boost (yazılabilir, root)
├── num_pstates       # P-state sayısı (sadece okunur)
├── turbo_pct         # Turbo yüzdesi (sadece okunur)
└── status            # active/passive/off (yazılabilir, root)
```

### Per-CPU Frekans Kontrolü
```
/sys/devices/system/cpu/cpu{0-11}/cpufreq/
├── scaling_governor                    # powersave veya performance (yazılabilir)
├── scaling_min_freq                    # KHz cinsinden minimum frekans (yazılabilir)
├── scaling_max_freq                    # KHz cinsinden maksimum frekans (yazılabilir)
├── scaling_cur_freq                    # Mevcut frekans (sadece okunur)
├── energy_performance_preference       # EPP ayarı (yazılabilir)
├── energy_performance_available_preferences  # Kullanılabilir EPP değerleri
└── scaling_available_governors         # Kullanılabilir governor'lar
```

### EPP (Energy Performance Preference) Değerleri
| Değer | Açıklama |
|-------|----------|
| `default` | Varsayılan |
| `performance` | Maksimum performans |
| `balance_performance` | Dengeli-performans |
| `balance_power` | Dengeli-güç tasarrufu |
| `power` | Maksimum güç tasarrufu |

---

## NVIDIA GPU Kontrol Arayüzü

### nvidia-smi Komutları
```bash
# Sıcaklık okuma
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader

# Güç tüketimi
nvidia-smi --query-gpu=power.draw --format=csv,noheader

# Saat hızları
nvidia-smi --query-gpu=clocks.gr,clocks.mem --format=csv,noheader

# Güç limiti ayarlama (root)
nvidia-smi -pl <WATT>  # 10W - 90W arası

# Saat hızı limiti (root)
nvidia-smi -lgc <MIN>,<MAX>  # GPU clock limitleri

# Bellek saat hızı limiti (root)
nvidia-smi -lmc <MIN>,<MAX>

# Saat limiti sıfırlama
nvidia-smi -rgc  # GPU clock reset
nvidia-smi -rmc  # Mem clock reset

# Persistence mode
nvidia-smi -pm 1  # Kalıcı mod aç (önerilir)
```

### Grafik Modu (system76-power)
```bash
system76-power graphics          # Mevcut mod sorgula
system76-power graphics hybrid   # Hybrid mod
system76-power graphics nvidia   # Sadece NVIDIA
system76-power graphics integrated  # Sadece Intel
```

---

## Intel iGPU Frekans Kontrolü

```
/sys/class/drm/card0/
├── gt_min_freq_mhz    # Minimum frekans (yazılabilir, root) - 350-1150 arası
├── gt_max_freq_mhz    # Maksimum frekans (yazılabilir, root) - 350-1150 arası
├── gt_boost_freq_mhz  # Boost frekans (yazılabilir, root)
├── gt_cur_freq_mhz    # İstenen frekans (sadece okunur)
├── gt_act_freq_mhz    # Gerçek anlık frekans (sadece okunur)
├── gt_RP0_freq_mhz    # Donanım maks - 1150 MHz
├── gt_RP1_freq_mhz    # Donanım verimli - 350 MHz
└── gt_RPn_freq_mhz    # Donanım min - 350 MHz
```

---

## Güç Profili Yönetimi

### system76-power (Pop!_OS yerleşik)
```bash
system76-power profile              # Mevcut profil sorgula
system76-power profile battery      # Batarya tasarrufu
system76-power profile balanced     # Dengeli
system76-power profile performance  # Yüksek performans
```

### Önerilen Özel Profiller
| Profil | CPU Gov | EPP | Turbo | CPU Max | GPU PL | GPU Clock | Fan |
|--------|---------|-----|-------|---------|--------|-----------|-----|
| Sessiz | powersave | power | Kapalı | 2.6GHz | 30W | 300-1000 | Düşük |
| Dengeli | powersave | balance_performance | Açık | 4.0GHz | 60W | 300-1500 | Otomatik |
| Performans | performance | performance | Açık | 5.0GHz | 90W | 300-2100 | Yüksek |
| Oyun | performance | performance | Açık | 5.0GHz | 90W | 300-2100 | Maks |
| Pil Tasarrufu | powersave | power | Kapalı | 1.5GHz | 10W | 300-600 | Min |

> **ÖNEMLİ:** Tüm profillerde 88°C sert sıcaklık limiti geçerlidir. Termal koruma sistemi
> profillerden bağımsız çalışır ve hiçbir bileşenin 88°C'yi aşmasına izin vermez.

---

## Geliştirme Ortamı ve Teknik Kararlar

### Dil ve Framework
- **Dil:** Python 3.10.12 (sistemde mevcut)
- **GUI Framework:** GTK3 (PyGObject/GI - sistemde mevcut, Pop!_OS ile uyumlu)
- **Paket Yönetimi:** `pip3` kurulması gerekecek veya `apt` ile Python paketleri
- **Ek Bağımlılıklar:**
  - `psutil` - Sistem bilgisi
  - `pynvml` veya subprocess ile `nvidia-smi` - NVIDIA GPU
  - `cairo` - Grafik çizimleri (GTK ile gelir)

### Yetki Yönetimi
- Fan kontrolü, frekans ayarları ve güç limitleri **root yetkisi** gerektirir
- Uygulama `pkexec` (PolicyKit) ile yetki yükseltme yapmalı
- Alternatif: Systemd servisi olarak arka plan daemon'u + kullanıcı arayüzü D-Bus üzerinden iletişim

### Mimari Tasarım
```
fan_c/
├── .github/
│   └── copilot-instructions.md
├── src/
│   ├── __init__.py
│   ├── main.py                    # Uygulama giriş noktası
│   ├── daemon/
│   │   ├── __init__.py
│   │   ├── hw_daemon.py           # Root yetkili arka plan servisi
│   │   └── dbus_interface.py      # D-Bus API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cpu_controller.py      # CPU frekans ve governor kontrolü
│   │   ├── gpu_nvidia.py          # NVIDIA GPU kontrolü
│   │   ├── gpu_intel.py           # Intel iGPU kontrolü
│   │   ├── fan_controller.py      # EC-tabanlı fan kontrolü
│   │   ├── temp_monitor.py        # Sıcaklık izleme
│   │   ├── profile_manager.py     # Güç profili yönetimi
│   │   └── ec_access.py           # Embedded Controller erişim katmanı
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Ana GTK penceresi
│   │   ├── dashboard.py           # Anlık izleme paneli
│   │   ├── cpu_panel.py           # CPU ayar paneli
│   │   ├── gpu_panel.py           # GPU ayar paneli
│   │   ├── fan_panel.py           # Fan kontrol paneli
│   │   ├── profile_panel.py       # Profil yönetim paneli
│   │   └── widgets/
│   │       ├── __init__.py
│   │       ├── temp_gauge.py      # Sıcaklık göstergesi
│   │       ├── fan_curve.py       # Fan eğrisi editörü
│   │       └── freq_slider.py     # Frekans kaydırıcısı
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # JSON konfigürasyon yönetimi
│       └── logger.py              # Loglama
├── config/
│   ├── profiles/                  # Kayıtlı güç profilleri (JSON)
│   │   ├── silent.json
│   │   ├── balanced.json
│   │   ├── performance.json
│   │   └── gaming.json
│   └── ec_register_map.json       # EC register haritası
├── systemd/
│   └── monster-hw-ctrl.service    # Systemd servis dosyası
├── polkit/
│   └── com.monster.hwctrl.policy  # PolicyKit kuralları
├── requirements.txt
├── setup.py
├── install.sh                     # Kurulum betiği
└── README.md
```

### Kritik Geliştirme Notları

1. **EC Register Keşfi:** Monster TULPAR T5 V19.2'nin EC register haritası bilinmiyor. `isw` projesinin (https://github.com/YoyPa/isw) Clevo model konfigürasyonları referans alınmalı. Uygulama ilk kurulumda EC register taraması yapmalı.

2. **Güvenlik:** EC'ye yanlış değer yazmak donanıma zarar verebilir. Tüm yazma işlemlerinde güvenlik kontrolleri ve limit doğrulaması yapılmalı. Fan hızı asla %0'a düşürülmemeli (minimum %20-30 güvenlik eşiği).

3. **Sıcaklık Tabanlı Otomatik Fan:** Sıcaklık eşiklerine göre otomatik fan eğrisi desteği olmalı. EC'nin kendi otomatik moduna geri dönüş seçeneği de sunulmalı.

4. **Veri Yenileme:** Sıcaklık ve frekans verileri 1-2 saniye aralıklarla okunmalı. Fan RPM verileri 2-3 saniye aralıklarla okunmalı. nvidia-smi çağrıları subprocess overhead'i nedeniyle optimize edilmeli (pynvml tercih edilmeli).

5. **Profil Kalıcılığı:** Profiller JSON formatında `~/.config/monster-hw-ctrl/profiles/` dizininde saklanmalı. Sistem başlangıcında son aktif profil otomatik yüklenmeli (systemd servisi ile).

6. **Hata Yönetimi:** Sensör okunamama durumunda "N/A" gösterilmeli. EC erişim hatası durumunda kullanıcı bilgilendirilmeli. NVIDIA GPU kapalıysa (hybrid modda) ilgili panel devre dışı kalmalı.

7. **Pop!_OS Entegrasyonu:** `system76-power` ile çakışma olmamalı. Grafik modu değiştirme system76-power'a devredilmeli. COSMIC/GNOME panel entegrasyonu düşünülebilir (tray icon).

### Sysfs Dosya Yolları Özeti (Hızlı Referans)
```python
PATHS = {
    # CPU
    "cpu_governor": "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor",
    "cpu_min_freq": "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_min_freq",
    "cpu_max_freq": "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_max_freq",
    "cpu_cur_freq": "/sys/devices/system/cpu/cpu{}/cpufreq/scaling_cur_freq",
    "cpu_epp": "/sys/devices/system/cpu/cpu{}/cpufreq/energy_performance_preference",
    "cpu_no_turbo": "/sys/devices/system/cpu/intel_pstate/no_turbo",
    "cpu_max_perf_pct": "/sys/devices/system/cpu/intel_pstate/max_perf_pct",
    "cpu_min_perf_pct": "/sys/devices/system/cpu/intel_pstate/min_perf_pct",
    
    # CPU Temps (coretemp - hwmon5)
    "cpu_pkg_temp": "/sys/class/hwmon/hwmon5/temp1_input",
    "cpu_core_temp": "/sys/class/hwmon/hwmon5/temp{}_input",  # 2-7 arası
    "cpu_core_label": "/sys/class/hwmon/hwmon5/temp{}_label",
    
    # Intel iGPU
    "igpu_min_freq": "/sys/class/drm/card0/gt_min_freq_mhz",
    "igpu_max_freq": "/sys/class/drm/card0/gt_max_freq_mhz",
    "igpu_cur_freq": "/sys/class/drm/card0/gt_cur_freq_mhz",
    "igpu_act_freq": "/sys/class/drm/card0/gt_act_freq_mhz",
    "igpu_boost_freq": "/sys/class/drm/card0/gt_boost_freq_mhz",
    
    # PCH
    "pch_temp": "/sys/class/hwmon/hwmon4/temp1_input",
    
    # ACPI
    "acpi_temp1": "/sys/class/hwmon/hwmon1/temp1_input",
    "acpi_temp2": "/sys/class/hwmon/hwmon1/temp2_input",
    
    # NVMe
    "nvme_temp": "/sys/class/hwmon/hwmon3/temp1_input",
    
    # WiFi
    "wifi_temp": "/sys/class/hwmon/hwmon6/temp1_input",
    
    # EC
    "ec_io": "/sys/kernel/debug/ec/ec0/io",
    
    # Thermal
    "tcc_offset": "/sys/class/thermal/cooling_device16/cur_state",  # TCC Offset (0-63)
}
```

### NVIDIA Komut Referansı
```python
NVIDIA_CMDS = {
    "temp": "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader",
    "power": "nvidia-smi --query-gpu=power.draw --format=csv,noheader",
    "clocks": "nvidia-smi --query-gpu=clocks.gr,clocks.mem --format=csv,noheader",
    "fan": "nvidia-smi --query-gpu=fan.speed --format=csv,noheader",
    "util": "nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader",
    "all": "nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.gr,clocks.mem,fan.speed,utilization.gpu --format=csv,noheader",
    "set_power_limit": "nvidia-smi -pl {}",  # Watt
    "set_gpu_clocks": "nvidia-smi -lgc {},{}",  # min,max MHz
    "set_mem_clocks": "nvidia-smi -lmc {},{}",  # min,max MHz
    "reset_gpu_clocks": "nvidia-smi -rgc",
    "reset_mem_clocks": "nvidia-smi -rmc",
    "persistence": "nvidia-smi -pm 1",
}
```

### Donanım Limitleri (GÜVENLİK)
```python
LIMITS = {
    "cpu_freq_min_khz": 800000,       # 800 MHz
    "cpu_freq_max_khz": 5000000,      # 5.0 GHz
    "cpu_temp_warning": 75,            # °C
    "cpu_temp_critical": 84,           # °C
    "cpu_temp_shutdown": 88,           # °C - SERT LİMİT
    
    "gpu_nvidia_power_min": 10,        # Watt
    "gpu_nvidia_power_max": 90,        # Watt
    "gpu_nvidia_clock_min": 300,       # MHz
    "gpu_nvidia_clock_max": 2100,      # MHz
    "gpu_nvidia_mem_max": 5501,        # MHz
    "gpu_nvidia_temp_warning": 75,     # °C
    "gpu_nvidia_temp_critical": 84,    # °C
    "gpu_nvidia_temp_shutdown": 88,    # °C - SERT LİMİT
    
    "igpu_freq_min": 350,              # MHz
    "igpu_freq_max": 1150,             # MHz
    
    "fan_duty_min_pct": 20,            # Minimum fan hızı (güvenlik)
    "fan_duty_max_pct": 100,           # Maksimum fan hızı
}
```

### hwmon Numaralarının Dinamik Keşfi
**ÖNEMLİ:** hwmon numaraları (hwmon0, hwmon1, vb.) sistem yeniden başlatıldığında değişebilir! Uygulama başlarken `/sys/class/hwmon/hwmonX/name` dosyasını okuyarak sensörleri **isme göre eşleştirmelidir:**
```python
HWMON_NAMES = {
    "coretemp": "CPU sıcaklıkları",
    "pch_cometlake": "PCH sıcaklığı", 
    "acpitz": "ACPI termal bölge",
    "nvme": "NVMe SSD sıcaklığı",
    "iwlwifi_1": "WiFi modül sıcaklığı",
}
```

---

## Geliştirme Öncelikleri

### Faz 1 - Temel İzleme (MVP)
1. Tüm sıcaklık sensörlerini okuma ve gösterme
2. CPU frekans bilgilerini gösterme
3. NVIDIA GPU bilgilerini gösterme
4. Intel iGPU bilgilerini gösterme
5. Basit GTK3 dashboard

### Faz 2 - Kontrol
1. CPU governor ve frekans ayarlama
2. CPU Turbo Boost açma/kapama
3. NVIDIA GPU güç limiti ayarlama
4. Intel iGPU frekans ayarlama
5. EPP ayarlama

### Faz 3 - Fan Kontrolü
1. EC modülü yükleme ve erişim
2. Fan RPM okuma
3. Fan duty cycle ayarlama
4. Sıcaklık-fan eğrisi tanımlama
5. Otomatik fan modu

### Faz 4 - Profil Sistemi
1. Profil oluşturma/kaydetme/silme
2. Profiller arası geçiş
3. Systemd servisi ile başlangıç profili
4. Hızlı profil geçiş kısayolları

### Faz 5 - İleri Özellikler
1. System tray icon
2. Bildirim sistemi (sıcaklık uyarıları)
3. Geçmiş grafikleri (sıcaklık/frekans/fan)
4. Export/import profiller
5. CLI arayüzü
