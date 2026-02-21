"""
Monster HW Controller - Temperature Monitor
Tüm sıcaklık sensörlerini dinamik olarak keşfeder ve okur.
hwmon numaraları yeniden başlatmada değişebileceğinden isme göre eşleştirme yapar.
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.logger import get_logger

log = get_logger("temp_monitor")

HWMON_BASE = Path("/sys/class/hwmon")

# Bilinen hwmon sensör isimleri ve açıklamaları
KNOWN_HWMON = {
    "coretemp": "CPU",
    "pch_cometlake": "PCH",
    "acpitz": "ACPI",
    "nvme": "NVMe SSD",
    "iwlwifi_1": "WiFi",
}


@dataclass
class TempSensor:
    """Tek bir sıcaklık sensörünü temsil eder."""
    name: str           # Sensör grubu adı (ör: coretemp)
    label: str          # Sensör etiketi (ör: Core 0)
    path: str           # Sysfs dosya yolu
    temp: float = 0.0   # Derece C
    temp_max: float = 0.0
    temp_crit: float = 0.0
    category: str = ""  # CPU, GPU, NVMe vb.


@dataclass
class TempReading:
    """Tüm sensörlerin anlık okuması."""
    cpu_package: float = 0.0
    cpu_cores: List[float] = field(default_factory=list)
    gpu_nvidia: float = 0.0
    pch: float = 0.0
    nvme: float = 0.0
    wifi: float = 0.0
    acpi: List[float] = field(default_factory=list)
    sensors: List[TempSensor] = field(default_factory=list)


class TempMonitor:
    """Sistem sıcaklık sensörlerini yönetir."""

    def __init__(self):
        self._hwmon_map: Dict[str, Path] = {}  # name -> hwmon path
        self._sensors: List[TempSensor] = []
        self._last_nvidia_temp: float = 0.0
        self._discover_hwmon()
        self._discover_sensors()

    def _discover_hwmon(self):
        """hwmon cihazlarını isme göre keşfet ve eşleştir."""
        self._hwmon_map.clear()
        if not HWMON_BASE.exists():
            log.warning("hwmon dizini bulunamadı: %s", HWMON_BASE)
            return

        for hwmon_dir in sorted(HWMON_BASE.iterdir()):
            name_file = hwmon_dir / "name"
            if name_file.exists():
                try:
                    name = name_file.read_text().strip()
                    self._hwmon_map[name] = hwmon_dir
                    log.debug("hwmon keşfedildi: %s -> %s", name, hwmon_dir)
                except IOError:
                    pass

        log.info("Keşfedilen hwmon cihazları: %s",
                 {k: str(v) for k, v in self._hwmon_map.items()})

    def _discover_sensors(self):
        """Tüm sıcaklık sensörlerini keşfet."""
        self._sensors.clear()

        for name, hwmon_path in self._hwmon_map.items():
            category = KNOWN_HWMON.get(name, name)

            # temp*_input dosyalarını bul
            for temp_file in sorted(hwmon_path.glob("temp*_input")):
                idx = temp_file.name.replace("temp", "").replace("_input", "")

                # Etiket dosyasını oku
                label_file = hwmon_path / f"temp{idx}_label"
                label = ""
                if label_file.exists():
                    try:
                        label = label_file.read_text().strip()
                    except IOError:
                        label = f"{category} #{idx}"
                else:
                    label = f"{category} #{idx}"

                # Max ve crit değerleri
                temp_max = self._read_temp_file(hwmon_path / f"temp{idx}_max")
                temp_crit = self._read_temp_file(hwmon_path / f"temp{idx}_crit")

                sensor = TempSensor(
                    name=name,
                    label=label,
                    path=str(temp_file),
                    temp_max=temp_max,
                    temp_crit=temp_crit,
                    category=category,
                )
                self._sensors.append(sensor)

        log.info("Toplam %d sıcaklık sensörü keşfedildi", len(self._sensors))

    @staticmethod
    def _read_temp_file(path: Path) -> float:
        """Sysfs sıcaklık dosyasını oku, derece C olarak döndür."""
        try:
            if path.exists():
                val = int(path.read_text().strip())
                return val / 1000.0
        except (ValueError, IOError, PermissionError):
            pass
        return 0.0

    @staticmethod
    def _read_nvidia_temp() -> float:
        """NVIDIA GPU sıcaklığını nvidia-smi ile oku."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.SubprocessError, ValueError, FileNotFoundError):
            pass
        return 0.0

    def read_all(self) -> TempReading:
        """Tüm sensörlerin anlık değerlerini oku."""
        reading = TempReading()

        # hwmon sensörlerini oku
        for sensor in self._sensors:
            sensor.temp = self._read_temp_file(Path(sensor.path))

            if sensor.name == "coretemp":
                if "Package" in sensor.label:
                    reading.cpu_package = sensor.temp
                elif "Core" in sensor.label:
                    reading.cpu_cores.append(sensor.temp)
            elif sensor.name == "pch_cometlake":
                reading.pch = sensor.temp
            elif sensor.name == "nvme":
                if reading.nvme == 0.0:  # İlk sıcaklık (composite)
                    reading.nvme = sensor.temp
            elif sensor.name == "iwlwifi_1":
                reading.wifi = sensor.temp
            elif sensor.name == "acpitz":
                reading.acpi.append(sensor.temp)

        # NVIDIA GPU sıcaklığı — öncelikle cache'den, yoksa subprocess
        if self._last_nvidia_temp > 0:
            reading.gpu_nvidia = self._last_nvidia_temp
        else:
            reading.gpu_nvidia = self._read_nvidia_temp()

        reading.sensors = list(self._sensors)
        return reading

    def set_nvidia_temp(self, temp: float):
        """NVIDIA sıcaklığını dışarıdan ayarla (çift subprocess çağrısını önlemek için).
        NvidiaGpuController zaten nvidia-smi çağırıyorsa, sonucu buraya iletin.
        """
        self._last_nvidia_temp = temp

    def get_sensor_list(self) -> List[TempSensor]:
        """Keşfedilen tüm sensörlerin listesini döndür."""
        return list(self._sensors)

    def refresh_hwmon(self):
        """hwmon eşleştirmesini yeniden yap (hot-plug durumları için)."""
        self._discover_hwmon()
        self._discover_sensors()
