"""
Monster HW Controller - CPU Controller
Intel i7-10750H için intel_pstate tabanlı CPU frekans ve governor kontrolü.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.utils.logger import get_logger

log = get_logger("cpu_controller")

INTEL_PSTATE = Path("/sys/devices/system/cpu/intel_pstate")
CPU_BASE = Path("/sys/devices/system/cpu")

# Donanım limitleri
CPU_FREQ_MIN_KHZ = 800000    # 800 MHz
CPU_FREQ_MAX_KHZ = 5000000   # 5.0 GHz
CPU_COUNT = 12               # 6 çekirdek, 12 thread


@dataclass
class CpuStatus:
    """CPU'nun anlık durumu."""
    governor: str = "powersave"
    epp: str = "balance_performance"
    available_governors: List[str] = field(default_factory=list)
    available_epp: List[str] = field(default_factory=list)
    min_freq_khz: int = CPU_FREQ_MIN_KHZ
    max_freq_khz: int = CPU_FREQ_MAX_KHZ
    cur_freqs_khz: List[int] = field(default_factory=list)
    turbo_enabled: bool = True
    hwp_dynamic_boost: bool = True
    max_perf_pct: int = 100
    min_perf_pct: int = 16
    num_pstates: int = 43
    turbo_pct: int = 56
    driver: str = "intel_pstate"
    cpu_count: int = CPU_COUNT


class CpuController:
    """CPU frekans, governor ve güç ayarlarını yönetir."""

    def __init__(self):
        self._cpu_count = self._detect_cpu_count()

    @staticmethod
    def _detect_cpu_count() -> int:
        """Online CPU sayısını tespit et."""
        count = 0
        for d in CPU_BASE.iterdir():
            if d.name.startswith("cpu") and d.name[3:].isdigit():
                count += 1
        return count if count > 0 else CPU_COUNT

    @staticmethod
    def _read_sysfs(path: Path) -> str:
        """Sysfs dosyasını oku."""
        try:
            return path.read_text().strip()
        except (IOError, PermissionError) as e:
            log.debug("Sysfs okunamadı: %s - %s", path, e)
            return ""

    @staticmethod
    def _write_sysfs(path: Path, value: str) -> bool:
        """Sysfs dosyasına yaz (root gerektirir)."""
        try:
            path.write_text(value)
            log.info("Sysfs yazıldı: %s = %s", path, value)
            return True
        except (IOError, PermissionError) as e:
            log.error("Sysfs yazılamadı: %s = %s - %s", path, value, e)
            return False

    def get_status(self) -> CpuStatus:
        """CPU'nun anlık durumunu oku."""
        status = CpuStatus()
        status.cpu_count = self._cpu_count

        # intel_pstate parametreleri
        no_turbo = self._read_sysfs(INTEL_PSTATE / "no_turbo")
        status.turbo_enabled = no_turbo == "0" if no_turbo else True

        hwp = self._read_sysfs(INTEL_PSTATE / "hwp_dynamic_boost")
        status.hwp_dynamic_boost = hwp == "1" if hwp else False

        max_pct = self._read_sysfs(INTEL_PSTATE / "max_perf_pct")
        status.max_perf_pct = int(max_pct) if max_pct else 100

        min_pct = self._read_sysfs(INTEL_PSTATE / "min_perf_pct")
        status.min_perf_pct = int(min_pct) if min_pct else 16

        num_ps = self._read_sysfs(INTEL_PSTATE / "num_pstates")
        status.num_pstates = int(num_ps) if num_ps else 0

        turbo_p = self._read_sysfs(INTEL_PSTATE / "turbo_pct")
        status.turbo_pct = int(turbo_p) if turbo_p else 0

        stat = self._read_sysfs(INTEL_PSTATE / "status")
        status.driver = f"intel_pstate ({stat})" if stat else "intel_pstate"

        # Per-CPU: cpu0 referans olarak kullanılır
        cpu0_freq = CPU_BASE / "cpu0" / "cpufreq"

        status.governor = self._read_sysfs(cpu0_freq / "scaling_governor")

        avail_gov = self._read_sysfs(cpu0_freq / "scaling_available_governors")
        status.available_governors = avail_gov.split() if avail_gov else []

        status.epp = self._read_sysfs(cpu0_freq / "energy_performance_preference")

        avail_epp = self._read_sysfs(cpu0_freq / "energy_performance_available_preferences")
        status.available_epp = avail_epp.split() if avail_epp else []

        min_f = self._read_sysfs(cpu0_freq / "scaling_min_freq")
        status.min_freq_khz = int(min_f) if min_f else CPU_FREQ_MIN_KHZ

        max_f = self._read_sysfs(cpu0_freq / "scaling_max_freq")
        status.max_freq_khz = int(max_f) if max_f else CPU_FREQ_MAX_KHZ

        # Tüm çekirdeklerin anlık frekansları
        status.cur_freqs_khz = []
        for i in range(self._cpu_count):
            cur = self._read_sysfs(CPU_BASE / f"cpu{i}" / "cpufreq" / "scaling_cur_freq")
            status.cur_freqs_khz.append(int(cur) if cur else 0)

        return status

    # --- Kontrol Metotları (root gerektirir) ---

    def set_governor(self, governor: str) -> bool:
        """Tüm CPU'lar için governor ayarla."""
        if governor not in ("performance", "powersave"):
            log.error("Geçersiz governor: %s", governor)
            return False

        success = True
        for i in range(self._cpu_count):
            path = CPU_BASE / f"cpu{i}" / "cpufreq" / "scaling_governor"
            if not self._write_sysfs(path, governor):
                success = False
        return success

    def set_epp(self, epp: str) -> bool:
        """Tüm CPU'lar için Energy Performance Preference ayarla."""
        valid = ("default", "performance", "balance_performance", "balance_power", "power")
        if epp not in valid:
            log.error("Geçersiz EPP: %s", epp)
            return False

        success = True
        for i in range(self._cpu_count):
            path = CPU_BASE / f"cpu{i}" / "cpufreq" / "energy_performance_preference"
            if not self._write_sysfs(path, epp):
                success = False
        return success

    def set_turbo(self, enabled: bool) -> bool:
        """Turbo Boost aç/kapa."""
        value = "0" if enabled else "1"  # no_turbo: 0=aktif, 1=kapalı
        return self._write_sysfs(INTEL_PSTATE / "no_turbo", value)

    def set_max_perf_pct(self, pct: int) -> bool:
        """Maksimum performans yüzdesini ayarla (1-100)."""
        pct = max(1, min(100, pct))
        return self._write_sysfs(INTEL_PSTATE / "max_perf_pct", str(pct))

    def set_min_perf_pct(self, pct: int) -> bool:
        """Minimum performans yüzdesini ayarla (1-100)."""
        pct = max(1, min(100, pct))
        return self._write_sysfs(INTEL_PSTATE / "min_perf_pct", str(pct))

    def set_freq_range(self, min_khz: int, max_khz: int) -> bool:
        """Tüm CPU'lar için frekans aralığı ayarla.
        3 adımlı yazma: max yükselt -> min ayarla -> max düşür.
        Bu sayede yeni max < mevcut min olsa bile kernel reddetmez.
        """
        min_khz = max(CPU_FREQ_MIN_KHZ, min(CPU_FREQ_MAX_KHZ, min_khz))
        max_khz = max(CPU_FREQ_MIN_KHZ, min(CPU_FREQ_MAX_KHZ, max_khz))
        if min_khz > max_khz:
            min_khz, max_khz = max_khz, min_khz

        success = True
        for i in range(self._cpu_count):
            cpu_path = CPU_BASE / f"cpu{i}" / "cpufreq"
            # Adım 1: max'ı en yükseğe çek (alan aç)
            self._write_sysfs(cpu_path / "scaling_max_freq", str(CPU_FREQ_MAX_KHZ))
            # Adım 2: min'i ayarla
            if not self._write_sysfs(cpu_path / "scaling_min_freq", str(min_khz)):
                success = False
            # Adım 3: max'ı hedef değere düşür
            if not self._write_sysfs(cpu_path / "scaling_max_freq", str(max_khz)):
                success = False
        return success

    def set_hwp_dynamic_boost(self, enabled: bool) -> bool:
        """HWP Dynamic Boost aç/kapa."""
        value = "1" if enabled else "0"
        return self._write_sysfs(INTEL_PSTATE / "hwp_dynamic_boost", value)
