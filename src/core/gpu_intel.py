"""
Monster HW Controller - Intel iGPU Controller
Intel UHD Graphics (CometLake-H GT2) frekans kontrolü.
"""

from dataclasses import dataclass
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger("gpu_intel")

DRM_BASE = Path("/sys/class/drm")

# Donanım limitleri (MHz)
IGPU_FREQ_MIN = 350
IGPU_FREQ_MAX = 1150


def _find_intel_drm_card() -> Path:
    """Intel iGPU DRM card'ını dinamik olarak bul."""
    # Önce bilinen Intel PCI ID'leri ile dene
    for card_dir in sorted(DRM_BASE.iterdir()):
        if not card_dir.name.startswith("card"):
            continue
        # renderD* gibi girdileri atla
        if not card_dir.name.replace("card", "").isdigit():
            continue
        # gt_cur_freq_mhz varsa Intel iGPU'dur
        if (card_dir / "gt_cur_freq_mhz").exists():
            log.info("Intel iGPU bulundu: %s", card_dir)
            return card_dir
    # Fallback
    return DRM_BASE / "card0"


DRM_CARD = _find_intel_drm_card()


@dataclass
class IntelGpuStatus:
    """Intel iGPU anlık durumu."""
    available: bool = False
    act_freq_mhz: int = 0     # Gerçek anlık frekans
    cur_freq_mhz: int = 0     # İstenen frekans
    min_freq_mhz: int = IGPU_FREQ_MIN
    max_freq_mhz: int = IGPU_FREQ_MAX
    boost_freq_mhz: int = IGPU_FREQ_MAX
    rp0_freq_mhz: int = IGPU_FREQ_MAX  # Donanım maks
    rp1_freq_mhz: int = IGPU_FREQ_MIN  # Donanım verimli
    rpn_freq_mhz: int = IGPU_FREQ_MIN  # Donanım min


class IntelGpuController:
    """Intel entegre GPU frekans kontrolü."""

    def __init__(self):
        self._available = DRM_CARD.exists() and (DRM_CARD / "gt_cur_freq_mhz").exists()

    @property
    def available(self) -> bool:
        return self._available

    @staticmethod
    def _read_freq(filename: str) -> int:
        """DRM frekans dosyasını oku (MHz)."""
        path = DRM_CARD / filename
        try:
            if path.exists():
                return int(path.read_text().strip())
        except (ValueError, IOError, PermissionError):
            pass
        return 0

    @staticmethod
    def _write_freq(filename: str, value: int) -> bool:
        """DRM frekans dosyasına yaz."""
        path = DRM_CARD / filename
        try:
            path.write_text(str(value))
            log.info("iGPU %s = %d MHz", filename, value)
            return True
        except (IOError, PermissionError) as e:
            log.error("iGPU %s yazılamadı: %s", filename, e)
            return False

    def get_status(self) -> IntelGpuStatus:
        """iGPU anlık durumunu oku."""
        status = IntelGpuStatus()
        status.available = self._available

        if not self._available:
            return status

        status.act_freq_mhz = self._read_freq("gt_act_freq_mhz")
        status.cur_freq_mhz = self._read_freq("gt_cur_freq_mhz")
        status.min_freq_mhz = self._read_freq("gt_min_freq_mhz")
        status.max_freq_mhz = self._read_freq("gt_max_freq_mhz")
        status.boost_freq_mhz = self._read_freq("gt_boost_freq_mhz")
        status.rp0_freq_mhz = self._read_freq("gt_RP0_freq_mhz")
        status.rp1_freq_mhz = self._read_freq("gt_RP1_freq_mhz")
        status.rpn_freq_mhz = self._read_freq("gt_RPn_freq_mhz")

        return status

    # --- Kontrol Metotları (root gerektirir) ---

    def set_freq_range(self, min_mhz: int, max_mhz: int) -> bool:
        """iGPU frekans aralığını ayarla.
        3 adımlı: max yükselt -> min ayarla -> max düşür.
        """
        min_mhz = max(IGPU_FREQ_MIN, min(IGPU_FREQ_MAX, min_mhz))
        max_mhz = max(IGPU_FREQ_MIN, min(IGPU_FREQ_MAX, max_mhz))
        if min_mhz > max_mhz:
            min_mhz, max_mhz = max_mhz, min_mhz

        # Adım 1: max'ı donanım limitine çek (alan aç)
        self._write_freq("gt_max_freq_mhz", IGPU_FREQ_MAX)
        # Adım 2: min'i ayarla
        s1 = self._write_freq("gt_min_freq_mhz", min_mhz)
        # Adım 3: max'ı hedef değere düşür
        s2 = self._write_freq("gt_max_freq_mhz", max_mhz)
        return s1 and s2

    def set_boost_freq(self, mhz: int) -> bool:
        """Boost frekansını ayarla."""
        mhz = max(IGPU_FREQ_MIN, min(IGPU_FREQ_MAX, mhz))
        return self._write_freq("gt_boost_freq_mhz", mhz)
