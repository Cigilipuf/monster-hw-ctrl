"""
Monster HW Controller - Temperature Notification System
Sıcaklık eşik değerlerini aşıldığında masaüstü bildirimi gönderir.
"""

import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from src.utils.logger import get_logger

log = get_logger("notifier")


@dataclass
class TempThresholds:
    """Bir sensör için sıcaklık eşikleri."""
    warning: float = 80.0
    critical: float = 95.0


# Varsayılan eşik değerleri (88°C sert limit — uyarılar öncesinde)
DEFAULT_THRESHOLDS: Dict[str, TempThresholds] = {
    "cpu": TempThresholds(warning=75, critical=84),
    "gpu_nvidia": TempThresholds(warning=75, critical=84),
    "nvme": TempThresholds(warning=60, critical=72),
    "pch": TempThresholds(warning=72, critical=82),
}


class TempNotifier:
    """Sıcaklık bildirim yöneticisi.

    Belirlenen eşik değerlerini aşan sıcaklıklar için masaüstü bildirimi gönderir.
    Aynı sensör için tekrar bildirim göndermeden önce bekleme süresi uygular (cooldown).
    """

    COOLDOWN_SEC = 60  # Aynı sensör için minimum bildirim aralığı

    SENSOR_LABELS = {
        "cpu": "CPU",
        "gpu_nvidia": "NVIDIA GPU",
        "nvme": "NVMe SSD",
        "pch": "PCH",
    }

    def __init__(self, thresholds: Optional[Dict[str, TempThresholds]] = None):
        self._thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
        self._last_notify: Dict[str, float] = {}  # sensor -> timestamp
        self._enabled = True
        self._notify_available = self._check_notify()

    def _check_notify(self) -> bool:
        """notify-send komutunun mevcut olup olmadığını kontrol et."""
        try:
            result = subprocess.run(
                ["which", "notify-send"],
                capture_output=True, timeout=3,
            )
            return result.returncode == 0
        except Exception:
            log.warning("notify-send bulunamadı, bildirimler devre dışı")
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def set_threshold(self, sensor: str, warning: float, critical: float):
        """Bir sensör için eşik değerlerini ayarla."""
        self._thresholds[sensor] = TempThresholds(warning=warning, critical=critical)

    def get_threshold(self, sensor: str) -> TempThresholds:
        """Bir sensörün eşiklerini döndür."""
        return self._thresholds.get(sensor, TempThresholds())

    def check_and_notify(self, temps: Dict[str, float]):
        """Sıcaklıkları kontrol et, eşik aşılıyorsa bildirim gönder.

        Args:
            temps: {"cpu": 82.0, "gpu_nvidia": 75.0, ...}
        """
        if not self._enabled or not self._notify_available:
            return

        now = time.time()

        for sensor, temp in temps.items():
            if temp is None or temp <= 0:
                continue

            threshold = self._thresholds.get(sensor)
            if not threshold:
                continue

            # Cooldown kontrolü
            last = self._last_notify.get(sensor, 0)
            if now - last < self.COOLDOWN_SEC:
                continue

            label = self.SENSOR_LABELS.get(sensor, sensor)

            if temp >= threshold.critical:
                self._send_notification(
                    f"🔴 KRİTİK: {label} Sıcaklığı!",
                    f"{label} sıcaklığı {temp:.0f}°C — kritik seviyede!\n"
                    f"Eşik: {threshold.critical:.0f}°C",
                    urgency="critical",
                )
                self._last_notify[sensor] = now
                log.warning("KRİTİK sıcaklık: %s = %.0f°C", sensor, temp)

            elif temp >= threshold.warning:
                self._send_notification(
                    f"⚠ UYARI: {label} Sıcaklığı",
                    f"{label} sıcaklığı {temp:.0f}°C — yüksek!\n"
                    f"Eşik: {threshold.warning:.0f}°C",
                    urgency="normal",
                )
                self._last_notify[sensor] = now
                log.info("Sıcaklık uyarısı: %s = %.0f°C", sensor, temp)

    def _send_notification(self, title: str, body: str, urgency: str = "normal"):
        """Masaüstü bildirimi gönder."""
        try:
            subprocess.Popen(
                [
                    "notify-send",
                    "--urgency", urgency,
                    "--app-name", "Monster HW Controller",
                    "--icon", "dialog-warning" if urgency == "normal" else "dialog-error",
                    "-t", "8000",
                    title,
                    body,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log.error("Bildirim gönderilemedi: %s", e)

    def reset_cooldowns(self):
        """Tüm cooldown'ları sıfırla."""
        self._last_notify.clear()
