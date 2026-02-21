"""
Monster HW Controller - Fan Controller
EC (Embedded Controller) üzerinden fan hız kontrolü.
Clevo tabanlı Monster TULPAR T5 V19.2 için.

GÜVENLİK: Fan hızı asla %20'nin altına düşürülmez.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from src.core.ec_access import EcAccess
from src.utils.logger import get_logger

log = get_logger("fan_controller")

# Güvenlik limitleri
FAN_DUTY_MIN_PCT = 20    # Minimum fan hızı (%)
FAN_DUTY_MAX_PCT = 100   # Maksimum fan hızı (%)
FAN_DUTY_MIN_RAW = 51    # %20 = 51/255
FAN_DUTY_MAX_RAW = 255   # %100

# Varsayılan EC register adresleri (Clevo)
DEFAULT_REGISTERS = {
    "cpu_fan_duty": 0x68,
    "gpu_fan_duty": 0x69,
    "cpu_fan_rpm_lsb": 0xCE,
    "cpu_fan_rpm_msb": 0xCF,
    "gpu_fan_rpm_lsb": 0xD0,
    "gpu_fan_rpm_msb": 0xD1,
    "fan_mode": 0xD7,
}


@dataclass
class FanStatus:
    """Fan durumu."""
    ec_available: bool = False
    ec_method: str = "none"
    cpu_fan_rpm: int = 0
    gpu_fan_rpm: int = 0
    cpu_fan_duty_pct: int = 0
    gpu_fan_duty_pct: int = 0
    mode: str = "auto"  # "auto" veya "manual"


@dataclass
class FanCurvePoint:
    """Fan eğrisi noktası."""
    temp: int      # °C
    duty_pct: int  # %


# Varsayılan fan eğrileri (88°C sert limit — 82°C'de %100'e ulaşır)
DEFAULT_FAN_CURVE = [
    FanCurvePoint(temp=40, duty_pct=25),
    FanCurvePoint(temp=50, duty_pct=35),
    FanCurvePoint(temp=60, duty_pct=45),
    FanCurvePoint(temp=68, duty_pct=55),
    FanCurvePoint(temp=75, duty_pct=75),
    FanCurvePoint(temp=82, duty_pct=100),
]


class FanController:
    """EC tabanlı fan hız kontrolü."""

    def __init__(self, ec: EcAccess, registers: Optional[Dict[str, int]] = None):
        self._ec = ec
        self._registers = registers or dict(DEFAULT_REGISTERS)
        self._mode = "auto"
        self._fan_curve = list(DEFAULT_FAN_CURVE)
        self._auto_thread: Optional[threading.Thread] = None
        self._auto_running = False
        self._temp_callback: Optional[Callable[[], float]] = None
        self._last_duty: int = 0  # Son uygulanan duty (histerez için)
        self._hysteresis_deg: float = 3.0  # ±3°C histerez

    @property
    def available(self) -> bool:
        return self._ec.available

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def registers(self) -> Dict[str, int]:
        return dict(self._registers)

    def update_registers(self, registers: Dict[str, int]):
        """EC register haritasını güncelle."""
        self._registers.update(registers)
        log.info("EC register haritası güncellendi: %s", 
                 {k: f"0x{v:02X}" for k, v in self._registers.items()})

    def _read_rpm(self, lsb_reg: int, msb_reg: int) -> int:
        """Fan RPM değerini oku (16-bit, LSB+MSB)."""
        lsb = self._ec.read_byte(lsb_reg)
        msb = self._ec.read_byte(msb_reg)
        if lsb is not None and msb is not None:
            raw = (msb << 8) | lsb
            # Clevo EC'lerde RPM hesaplama: 
            # RPM = 2156220 / raw_value (eğer raw > 0)
            if raw > 0:
                return int(2156220 / raw)
        return 0

    def _read_duty(self, reg: int) -> int:
        """Fan duty cycle oku (0-255 -> 0-100%)."""
        val = self._ec.read_byte(reg)
        if val is not None:
            return int(val * 100 / 255)
        return 0

    def get_status(self) -> FanStatus:
        """Fan durumunu oku."""
        status = FanStatus()
        status.ec_available = self._ec.available
        status.ec_method = self._ec.method
        status.mode = self._mode

        if not self._ec.available:
            return status

        # RPM okuma
        status.cpu_fan_rpm = self._read_rpm(
            self._registers["cpu_fan_rpm_lsb"],
            self._registers["cpu_fan_rpm_msb"],
        )
        status.gpu_fan_rpm = self._read_rpm(
            self._registers["gpu_fan_rpm_lsb"],
            self._registers["gpu_fan_rpm_msb"],
        )

        # Duty cycle okuma
        status.cpu_fan_duty_pct = self._read_duty(self._registers["cpu_fan_duty"])
        status.gpu_fan_duty_pct = self._read_duty(self._registers["gpu_fan_duty"])

        return status

    # --- Kontrol Metotları ---

    def _clamp_duty(self, pct: int) -> int:
        """Fan hızını güvenlik limitleri içinde tut."""
        return max(FAN_DUTY_MIN_PCT, min(FAN_DUTY_MAX_PCT, pct))

    def _pct_to_raw(self, pct: int) -> int:
        """Yüzdeyi EC raw değerine dönüştür (0-255)."""
        pct = self._clamp_duty(pct)
        return int(pct * 255 / 100)

    def set_manual_mode(self) -> bool:
        """Fan kontrolünü manuel moda al."""
        if not self._ec.available:
            return False

        # Çalışan fan eğrisi thread'ini durdur
        self._stop_auto_curve()

        # EC fan mode register'ına yaz
        # Clevo'da genellikle bit 0 = manual mode
        if self._ec.write_byte(self._registers["fan_mode"], 0x01):
            self._mode = "manual"
            log.info("Fan modu: MANUAL")
            return True
        return False

    def set_auto_mode(self) -> bool:
        """Fan kontrolünü EC otomatik moduna geri al."""
        self._stop_auto_curve()
        if not self._ec.available:
            return False

        # EC fan mode register'ına yaz
        if self._ec.write_byte(self._registers["fan_mode"], 0x00):
            self._mode = "auto"
            log.info("Fan modu: AUTO (EC)")
            return True
        return False

    def set_cpu_fan(self, pct: int) -> bool:
        """CPU fan hızını ayarla (%)."""
        if self._mode != "manual":
            self.set_manual_mode()

        raw = self._pct_to_raw(pct)
        pct = self._clamp_duty(pct)
        log.info("CPU fan: %d%% (raw: %d)", pct, raw)
        return self._ec.write_byte(self._registers["cpu_fan_duty"], raw)

    def set_gpu_fan(self, pct: int) -> bool:
        """GPU fan hızını ayarla (%)."""
        if self._mode != "manual":
            self.set_manual_mode()

        raw = self._pct_to_raw(pct)
        pct = self._clamp_duty(pct)
        log.info("GPU fan: %d%% (raw: %d)", pct, raw)
        return self._ec.write_byte(self._registers["gpu_fan_duty"], raw)

    def set_both_fans(self, pct: int) -> bool:
        """Her iki fanı da aynı hıza ayarla."""
        s1 = self.set_cpu_fan(pct)
        s2 = self.set_gpu_fan(pct)
        return s1 and s2

    # --- Fan Eğrisi (Auto Curve) ---

    @property
    def fan_curve(self) -> List[FanCurvePoint]:
        return list(self._fan_curve)

    def set_fan_curve(self, curve: List[FanCurvePoint]):
        """Fan eğrisini güncelle.
        Güvenlik: 88°C sert limit — son eğri noktası en geç 82°C'de %100 olmalı.
        """
        # Sıcaklığa göre sırala
        curve.sort(key=lambda p: p.temp)
        # Her noktayı güvenlik limitlerinde tut
        for point in curve:
            point.duty_pct = self._clamp_duty(point.duty_pct)
            point.temp = min(point.temp, 88)  # Sert limit

        # 82°C'den sonra %100 olduğundan emin ol
        has_full_before_limit = any(p.duty_pct >= 100 and p.temp <= 82 for p in curve)
        if not has_full_before_limit:
            # Son noktayı 82°C/%100 olarak ekle veya güncelle
            curve = [p for p in curve if p.temp < 82]
            curve.append(FanCurvePoint(temp=82, duty_pct=100))
            curve.sort(key=lambda p: p.temp)
            log.warning("Fan eğrisi: 82°C/%100 noktası zorla eklendi (88°C sert limit)")

        self._fan_curve = curve
        log.info("Fan eğrisi güncellendi: %s",
                 [(p.temp, p.duty_pct) for p in self._fan_curve])

    def _interpolate_duty(self, temp: float) -> int:
        """Sıcaklığa göre fan hızını fan eğrisinden hesapla (lineer interpolasyon)."""
        if not self._fan_curve:
            return FAN_DUTY_MAX_PCT

        if temp <= self._fan_curve[0].temp:
            return self._fan_curve[0].duty_pct
        if temp >= self._fan_curve[-1].temp:
            return self._fan_curve[-1].duty_pct

        for i in range(len(self._fan_curve) - 1):
            t1 = self._fan_curve[i].temp
            t2 = self._fan_curve[i + 1].temp
            d1 = self._fan_curve[i].duty_pct
            d2 = self._fan_curve[i + 1].duty_pct

            if t1 <= temp <= t2:
                ratio = (temp - t1) / (t2 - t1) if t2 > t1 else 0
                duty = d1 + ratio * (d2 - d1)
                return self._clamp_duty(int(duty))

        return FAN_DUTY_MAX_PCT

    def start_auto_curve(self, temp_callback: Callable[[], float], interval: float = 2.0):
        """Sıcaklık tabanlı otomatik fan eğrisi başlat."""
        self._stop_auto_curve()
        self._temp_callback = temp_callback
        self._auto_running = True
        self._last_duty = 0

        def _auto_loop():
            error_count = 0
            while self._auto_running:
                try:
                    temp = self._temp_callback()
                    target_duty = self._interpolate_duty(temp)

                    # Histerez: Sadece anlamlı fark varsa fan hızını değiştir
                    duty_diff = abs(target_duty - self._last_duty)
                    if duty_diff >= 3 or self._last_duty == 0:
                        self.set_both_fans(target_duty)
                        self._last_duty = target_duty
                        log.debug("Auto curve: %.1f°C -> %d%%", temp, target_duty)

                    error_count = 0  # Başarılı, hata sayacı sıfırla
                except Exception as e:
                    error_count += 1
                    log.error("Auto curve hatası (%d): %s", error_count, e)
                    if error_count >= 10:
                        log.critical("Auto curve: Çok fazla hata, durduruluyor!")
                        self._auto_running = False
                        break
                time.sleep(interval)

        self._mode = "curve"
        self._auto_thread = threading.Thread(target=_auto_loop, daemon=True, name="fan-curve")
        self._auto_thread.start()
        log.info("Otomatik fan eğrisi başlatıldı")

    def _stop_auto_curve(self):
        """Otomatik fan eğrisini durdur."""
        self._auto_running = False
        if self._auto_thread and self._auto_thread.is_alive():
            self._auto_thread.join(timeout=5)
            self._auto_thread = None
