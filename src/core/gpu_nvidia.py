"""
Monster HW Controller - NVIDIA GPU Controller
GeForce RTX 2060 Mobile için nvidia-smi tabanlı kontrol.
"""

import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import get_logger

log = get_logger("gpu_nvidia")

# Donanım limitleri
NVIDIA_POWER_MIN = 10    # Watt
NVIDIA_POWER_MAX = 90    # Watt
NVIDIA_CLOCK_MIN = 300   # MHz
NVIDIA_CLOCK_MAX = 2100  # MHz
NVIDIA_MEM_MAX = 5501    # MHz


@dataclass
class NvidiaStatus:
    """NVIDIA GPU'nun anlık durumu."""
    available: bool = False
    name: str = "N/A"
    temp: float = 0.0
    temp_slowdown: float = 93.0
    temp_shutdown: float = 98.0
    temp_target: float = 87.0
    fan_speed: str = "N/A"
    power_draw: float = 0.0
    power_limit: float = 90.0
    power_min_limit: float = 10.0
    power_max_limit: float = 90.0
    clock_graphics: int = 0
    clock_memory: int = 0
    clock_max_graphics: int = 2100
    clock_max_memory: int = 5501
    utilization_gpu: int = 0
    utilization_memory: int = 0
    vram_total: int = 6144
    vram_used: int = 0
    persistence_mode: bool = False
    driver_version: str = ""
    graphics_mode: str = "hybrid"


class NvidiaGpuController:
    """NVIDIA GPU izleme ve kontrol."""

    def __init__(self):
        self._available = self._check_available()
        self._graphics_mode_cache: str = "unknown"
        self._graphics_mode_time: float = 0.0
        self._graphics_mode_ttl: float = 30.0  # 30 saniyede bir sorgula

    @staticmethod
    def _check_available() -> bool:
        """nvidia-smi mevcut mu kontrol et."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False

    @property
    def available(self) -> bool:
        return self._available

    def _run_smi(self, *args) -> Optional[str]:
        """nvidia-smi komutunu çalıştır."""
        if not self._available:
            return None
        try:
            result = subprocess.run(
                ["nvidia-smi", *args],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                log.debug("nvidia-smi hata: %s", result.stderr.strip())
                return None
        except subprocess.TimeoutExpired:
            log.warning("nvidia-smi zaman aşımı (%s)", args)
            return None
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            log.debug("nvidia-smi çalıştırılamadı: %s", e)
            return None

    def _query(self, fields: str) -> Optional[str]:
        """nvidia-smi query komutu çalıştır."""
        return self._run_smi(f"--query-gpu={fields}", "--format=csv,noheader,nounits")

    def get_status(self) -> NvidiaStatus:
        """GPU'nun anlık durumunu oku."""
        status = NvidiaStatus()
        status.available = self._available

        if not self._available:
            return status

        # Toplu query - tek subprocess çağrısı ile tüm verileri al
        query_fields = (
            "name,temperature.gpu,fan.speed,"
            "power.draw,power.limit,power.min_limit,power.max_limit,"
            "clocks.gr,clocks.mem,clocks.max.gr,clocks.max.mem,"
            "utilization.gpu,utilization.memory,"
            "memory.total,memory.used,"
            "persistence_mode,driver_version"
        )
        result = self._query(query_fields)
        if not result:
            return status

        parts = [p.strip() for p in result.split(",")]
        if len(parts) < 17:
            log.warning("nvidia-smi beklenen alandan az döndü: %d", len(parts))
            return status

        try:
            status.name = parts[0]
            status.temp = self._safe_float(parts[1])
            status.fan_speed = parts[2] if parts[2] != "[N/A]" else "N/A"
            status.power_draw = self._safe_float(parts[3])
            status.power_limit = self._safe_float(parts[4])
            status.power_min_limit = self._safe_float(parts[5])
            status.power_max_limit = self._safe_float(parts[6])
            # power.limit N/A ise max_limit'i kullan
            if status.power_limit <= 0 and status.power_max_limit > 0:
                status.power_limit = status.power_max_limit
            status.clock_graphics = self._safe_int(parts[7])
            status.clock_memory = self._safe_int(parts[8])
            status.clock_max_graphics = self._safe_int(parts[9])
            status.clock_max_memory = self._safe_int(parts[10])
            status.utilization_gpu = self._safe_int(parts[11])
            status.utilization_memory = self._safe_int(parts[12])
            status.vram_total = self._safe_int(parts[13])
            status.vram_used = self._safe_int(parts[14])
            status.persistence_mode = parts[15].lower() == "enabled"
            status.driver_version = parts[16]
        except (IndexError, ValueError) as e:
            log.warning("nvidia-smi parse hatası: %s", e)

        # Grafik modu (cache'li)
        status.graphics_mode = self._get_graphics_mode_cached()

        return status

    @staticmethod
    def _safe_float(val: str) -> float:
        try:
            clean = val.replace("[N/A]", "0").replace("N/A", "0").strip()
            return float(clean) if clean else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _safe_int(val: str) -> int:
        try:
            clean = val.replace("[N/A]", "0").replace("N/A", "0").strip()
            return int(float(clean)) if clean else 0
        except ValueError:
            return 0

    @staticmethod
    def _get_graphics_mode() -> str:
        """system76-power ile grafik modunu sorgula."""
        try:
            result = subprocess.run(
                ["system76-power", "graphics"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
        return "unknown"

    def _get_graphics_mode_cached(self) -> str:
        """Grafik modunu cache ile sorgula (TTL: 30s)."""
        now = time.monotonic()
        if now - self._graphics_mode_time > self._graphics_mode_ttl:
            self._graphics_mode_cache = self._get_graphics_mode()
            self._graphics_mode_time = now
        return self._graphics_mode_cache

    # --- Kontrol Metotları (root gerektirir) ---

    def set_power_limit(self, watts: int) -> bool:
        """GPU güç limitini ayarla (Watt)."""
        watts = max(NVIDIA_POWER_MIN, min(NVIDIA_POWER_MAX, watts))
        result = self._run_smi("-pl", str(watts))
        if result is not None:
            log.info("NVIDIA güç limiti: %dW", watts)
            return True
        return False

    def set_gpu_clocks(self, min_mhz: int, max_mhz: int) -> bool:
        """GPU saat hızı limitleri ayarla."""
        min_mhz = max(NVIDIA_CLOCK_MIN, min(NVIDIA_CLOCK_MAX, min_mhz))
        max_mhz = max(NVIDIA_CLOCK_MIN, min(NVIDIA_CLOCK_MAX, max_mhz))
        if min_mhz > max_mhz:
            min_mhz, max_mhz = max_mhz, min_mhz

        result = self._run_smi("-lgc", f"{min_mhz},{max_mhz}")
        if result is not None:
            log.info("NVIDIA GPU clock: %d-%d MHz", min_mhz, max_mhz)
            return True
        return False

    def set_mem_clocks(self, min_mhz: int, max_mhz: int) -> bool:
        """GPU bellek saat hızı limitleri ayarla."""
        max_mhz = max(0, min(NVIDIA_MEM_MAX, max_mhz))
        min_mhz = max(0, min(max_mhz, min_mhz))
        result = self._run_smi("-lmc", f"{min_mhz},{max_mhz}")
        if result is not None:
            log.info("NVIDIA Mem clock: %d-%d MHz", min_mhz, max_mhz)
            return True
        return False

    def reset_gpu_clocks(self) -> bool:
        """GPU ve bellek saat hızı limitlerini sıfırla."""
        r1 = self._run_smi("-rgc")
        r2 = self._run_smi("-rmc")
        return r1 is not None and r2 is not None

    def reset_mem_clocks(self) -> bool:
        """Sadece bellek saat hızı limitlerini sıfırla."""
        r = self._run_smi("-rmc")
        return r is not None

    def set_persistence_mode(self, enabled: bool) -> bool:
        """Persistence mode aç/kapa."""
        val = "1" if enabled else "0"
        result = self._run_smi("-pm", val)
        return result is not None
