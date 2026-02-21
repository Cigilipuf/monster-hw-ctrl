"""
Monster HW Controller - Thermal Protection System
88°C sert sıcaklık limiti uygular. Hiçbir bileşenin bu sıcaklığı
aşmasına izin vermez.

Koruma seviyeleri (her bileşen için bağımsız):
  Seviye 0 (<75°C):  Normal — müdahale yok
  Seviye 1 (≥75°C):  Uyarı — fan hızını en az %60'a çıkar
  Seviye 2 (≥80°C):  Agresif — fanlar %80, CPU max_perf_pct düşür
  Seviye 3 (≥84°C):  Kritik — fanlar %100, turbo kapat, GPU güç limiti düşür
  Seviye 4 (≥87°C):  ACİL — max_perf_pct=%40, GPU güç=%10W
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

from src.utils.logger import get_logger

log = get_logger("thermal_protection")

# === SABİT SINIRLAR — DEĞİŞTİRİLEMEZ ===
TEMP_ABSOLUTE_MAX = 88  # °C — bu değeri aşmak yasak

TEMP_LEVEL_0 = 75   # Normal üst sınır
TEMP_LEVEL_1 = 75   # Fan boost başlangıcı
TEMP_LEVEL_2 = 80   # Agresif soğutma
TEMP_LEVEL_3 = 84   # Kritik — donanım kısıtlama
TEMP_LEVEL_4 = 87   # ACİL — maksimum kısıtlama

# Histerez: Seviye düşüşü için sıcaklık farkı
HYSTERESIS_DEG = 2.0


@dataclass
class ThermalState:
    """Termal koruma anlık durumu."""
    active: bool = False
    level: int = 0             # 0-4
    hottest_sensor: str = ""
    hottest_temp: float = 0.0
    action_taken: str = ""


class ThermalProtection:
    """Sert 88°C sıcaklık limiti uygulayan koruma sistemi.

    Bu sistem profil ayarlarından bağımsızdır ve her zaman aktiftir.
    Hiçbir profil veya kullanıcı eylemi bu korumayı devre dışı bırakamaz.
    """

    def __init__(self, cpu_controller, nvidia_controller, fan_controller):
        self._cpu = cpu_controller
        self._nvidia = nvidia_controller
        self._fan = fan_controller

        self._state = ThermalState()
        self._last_level = 0
        self._level_enter_time: Dict[int, float] = {}

        # Orijinal değerleri saklayacak (geri dönüş için)
        self._original_max_perf_pct: Optional[int] = None
        self._original_turbo: Optional[bool] = None
        self._original_gpu_power: Optional[float] = None

        self._enabled = True  # Her zaman True — devre dışı bırakılamaz

        log.info("Termal koruma sistemi aktif — sert limit: %d°C", TEMP_ABSOLUTE_MAX)

    @property
    def state(self) -> ThermalState:
        return self._state

    @property
    def active(self) -> bool:
        """Koruma şu anda müdahale mi ediyor?"""
        return self._state.level > 0

    def check(self, temps: Dict[str, float]) -> ThermalState:
        """Tüm sıcaklıkları kontrol et ve gerekirse önlem al.

        Args:
            temps: {"cpu": 82.0, "gpu_nvidia": 75.0, "pch": 60.0, ...}

        Returns:
            ThermalState — mevcut koruma durumu
        """
        # En sıcak bileşeni bul
        hottest_sensor = ""
        hottest_temp = 0.0

        for sensor, temp in temps.items():
            if temp is None or temp <= 0:
                continue
            if temp > hottest_temp:
                hottest_temp = temp
                hottest_sensor = sensor

        # Seviye belirle (yükseliş anında normal eşikler, düşüşte histerez)
        if hottest_temp >= TEMP_LEVEL_4:
            level = 4
        elif hottest_temp >= TEMP_LEVEL_3:
            level = 3
        elif hottest_temp >= TEMP_LEVEL_2:
            level = 2
        elif hottest_temp >= TEMP_LEVEL_1:
            level = 1
        else:
            level = 0

        # Histerez: Seviye düşüşünde, sıcaklık bir alt seviyenin eşiğinden
        # HYSTERESIS_DEG kadar düşmedikçe seviye düşürülmez
        if level < self._last_level:
            thresholds = {4: TEMP_LEVEL_4, 3: TEMP_LEVEL_3, 2: TEMP_LEVEL_2, 1: TEMP_LEVEL_1}
            current_threshold = thresholds.get(self._last_level, TEMP_LEVEL_1)
            if hottest_temp > current_threshold - HYSTERESIS_DEG:
                level = self._last_level  # Henüz yeterince soğumadı

        # Seviye değişimi logla
        if level != self._last_level:
            if level > self._last_level:
                log.warning(
                    "TERMAL KORUMA: Seviye %d → %d (%s: %.0f°C)",
                    self._last_level, level, hottest_sensor, hottest_temp,
                )
            else:
                log.info(
                    "TERMAL KORUMA: Seviye %d → %d (%s: %.0f°C) — düşüş",
                    self._last_level, level, hottest_sensor, hottest_temp,
                )

        # Orijinal değerleri kaydet (ilk yükseliş anında)
        if level > 0 and self._last_level == 0:
            self._save_original_state()

        # Eylemi uygula
        action = self._apply_level(level, hottest_sensor, hottest_temp)

        # Seviye 0'a düştüyse orijinal durumu geri yükle
        if level == 0 and self._last_level > 0:
            self._restore_original_state()
            action = "Normal — koruma kalkıyor"

        self._last_level = level
        self._state = ThermalState(
            active=level > 0,
            level=level,
            hottest_sensor=hottest_sensor,
            hottest_temp=hottest_temp,
            action_taken=action,
        )
        return self._state

    def _save_original_state(self):
        """Müdahale öncesi ayarları sakla."""
        try:
            cpu_st = self._cpu.get_status()
            self._original_max_perf_pct = cpu_st.max_perf_pct
            self._original_turbo = cpu_st.turbo_enabled
        except Exception:
            self._original_max_perf_pct = 100
            self._original_turbo = True

        try:
            if self._nvidia.available:
                nv_st = self._nvidia.get_status()
                self._original_gpu_power = nv_st.power_limit
        except Exception:
            self._original_gpu_power = 90

        log.info(
            "Orijinal durum kaydedildi — CPU perf: %s%%, turbo: %s, GPU: %sW",
            self._original_max_perf_pct,
            self._original_turbo,
            self._original_gpu_power,
        )

    def _restore_original_state(self):
        """Müdahale öncesi ayarlara geri dön."""
        log.info("Orijinal durum geri yükleniyor...")
        try:
            if self._original_max_perf_pct is not None:
                self._cpu.set_max_perf_pct(self._original_max_perf_pct)
            if self._original_turbo is not None:
                self._cpu.set_turbo(self._original_turbo)
            if self._original_gpu_power is not None and self._nvidia.available:
                self._nvidia.set_power_limit(int(self._original_gpu_power))
        except Exception as e:
            log.error("Durum geri yükleme hatası: %s", e)

        self._original_max_perf_pct = None
        self._original_turbo = None
        self._original_gpu_power = None

    def _apply_level(self, level: int, sensor: str, temp: float) -> str:
        """Seviyeye uygun eylemi uygula."""
        if level == 0:
            return ""

        sensor_label = {
            "cpu": "CPU", "gpu_nvidia": "NVIDIA GPU",
            "pch": "PCH", "nvme": "NVMe",
        }.get(sensor, sensor)

        # --- Seviye 1: Fan boost ---
        if level == 1:
            if self._fan.available and self._fan.mode != "curve":
                self._fan.set_both_fans(60)
            return f"Fan boost (%60) — {sensor_label}: {temp:.0f}°C"

        # --- Seviye 2: Agresif soğutma + CPU kısıtlama ---
        if level == 2:
            if self._fan.available:
                self._fan.set_both_fans(80)
            self._cpu.set_max_perf_pct(70)
            return f"Fan %80, CPU max %70 — {sensor_label}: {temp:.0f}°C"

        # --- Seviye 3: Kritik — turbo kapat, full fan, GPU kıs ---
        if level == 3:
            if self._fan.available:
                self._fan.set_both_fans(100)
            self._cpu.set_turbo(False)
            self._cpu.set_max_perf_pct(55)
            if self._nvidia.available:
                self._nvidia.set_power_limit(45)
            return f"ACİL: Fan %100, turbo OFF, CPU %55, GPU 45W — {sensor_label}: {temp:.0f}°C"

        # --- Seviye 4: EMERGENCY — maksimum kısıtlama ---
        if level >= 4:
            if self._fan.available:
                self._fan.set_both_fans(100)
            self._cpu.set_turbo(False)
            self._cpu.set_max_perf_pct(40)
            if self._nvidia.available:
                self._nvidia.set_power_limit(10)
            log.critical(
                "!!! ACİL TERMAL KORUMA !!! %s: %.0f°C — 88°C LİMİTİNE YAKIN!",
                sensor_label, temp,
            )
            return f"!!! ACİL: Fan %100, turbo OFF, CPU %40, GPU 10W — {sensor_label}: {temp:.0f}°C"

        return ""

    def get_status_text(self) -> str:
        """Dashboard için kısa durum metni."""
        s = self._state
        if not s.active:
            return ""

        level_icons = {1: "⚠️", 2: "🔶", 3: "🔴", 4: "🚨"}
        icon = level_icons.get(s.level, "")
        return f"{icon} Termal Koruma Seviye {s.level} — {s.action_taken}"
