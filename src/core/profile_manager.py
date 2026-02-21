"""
Monster HW Controller - Profile Manager
Güç profillerini yönetir. CPU, GPU, fan ayarlarını tek bir profilde birleştirir.
"""

import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from src.core.cpu_controller import CpuController
from src.core.fan_controller import FanController, FanCurvePoint
from src.core.gpu_intel import IntelGpuController
from src.core.gpu_nvidia import NvidiaGpuController
from src.utils.config import ConfigManager
from src.utils.logger import get_logger

log = get_logger("profile_manager")

# Varsayılan profiller
DEFAULT_PROFILES = {
    "sessiz": {
        "name": "Sessiz",
        "description": "Düşük gürültü, düşük güç tüketimi",
        "cpu": {
            "governor": "powersave",
            "epp": "power",
            "turbo": False,
            "max_freq_khz": 2600000,
            "min_freq_khz": 800000,
            "max_perf_pct": 52,
        },
        "nvidia": {
            "power_limit": 30,
            "gpu_clock_max": 1000,
        },
        "igpu": {
            "min_freq_mhz": 350,
            "max_freq_mhz": 600,
        },
        "fan": {
            "mode": "curve",
            "curve": [
                {"temp": 40, "duty_pct": 25},
                {"temp": 50, "duty_pct": 30},
                {"temp": 60, "duty_pct": 40},
                {"temp": 68, "duty_pct": 55},
                {"temp": 75, "duty_pct": 75},
                {"temp": 82, "duty_pct": 100},
            ],
        },
    },
    "dengeli": {
        "name": "Dengeli",
        "description": "Performans ve gürültü arasında denge",
        "cpu": {
            "governor": "powersave",
            "epp": "balance_performance",
            "turbo": True,
            "max_freq_khz": 4000000,
            "min_freq_khz": 800000,
            "max_perf_pct": 80,
        },
        "nvidia": {
            "power_limit": 60,
            "gpu_clock_max": 1500,
        },
        "igpu": {
            "min_freq_mhz": 350,
            "max_freq_mhz": 1150,
        },
        "fan": {
            "mode": "auto",
        },
    },
    "performans": {
        "name": "Performans",
        "description": "Yüksek performans",
        "cpu": {
            "governor": "performance",
            "epp": "performance",
            "turbo": True,
            "max_freq_khz": 5000000,
            "min_freq_khz": 800000,
            "max_perf_pct": 100,
        },
        "nvidia": {
            "power_limit": 90,
            "gpu_clock_max": 2100,
        },
        "igpu": {
            "min_freq_mhz": 350,
            "max_freq_mhz": 1150,
        },
        "fan": {
            "mode": "curve",
            "curve": [
                {"temp": 40, "duty_pct": 30},
                {"temp": 50, "duty_pct": 45},
                {"temp": 60, "duty_pct": 60},
                {"temp": 68, "duty_pct": 75},
                {"temp": 75, "duty_pct": 90},
                {"temp": 82, "duty_pct": 100},
            ],
        },
    },
    "oyun": {
        "name": "Oyun",
        "description": "Maksimum performans, yüksek fan",
        "cpu": {
            "governor": "performance",
            "epp": "performance",
            "turbo": True,
            "max_freq_khz": 5000000,
            "min_freq_khz": 800000,
            "max_perf_pct": 100,
        },
        "nvidia": {
            "power_limit": 90,
            "gpu_clock_max": 2100,
        },
        "igpu": {
            "min_freq_mhz": 350,
            "max_freq_mhz": 1150,
        },
        "fan": {
            "mode": "manual",
            "duty_pct": 100,
        },
    },
    "pil_tasarrufu": {
        "name": "Pil Tasarrufu",
        "description": "Minimum güç tüketimi",
        "cpu": {
            "governor": "powersave",
            "epp": "power",
            "turbo": False,
            "max_freq_khz": 1500000,
            "min_freq_khz": 800000,
            "max_perf_pct": 30,
        },
        "nvidia": {
            "power_limit": 10,
            "gpu_clock_max": 600,
        },
        "igpu": {
            "min_freq_mhz": 350,
            "max_freq_mhz": 600,
        },
        "fan": {
            "mode": "curve",
            "curve": [
                {"temp": 40, "duty_pct": 20},
                {"temp": 55, "duty_pct": 30},
                {"temp": 65, "duty_pct": 50},
                {"temp": 75, "duty_pct": 75},
                {"temp": 82, "duty_pct": 100},
            ],
        },
    },
}


class ProfileManager:
    """Güç profil yönetimi."""

    def __init__(
        self,
        config: ConfigManager,
        cpu: CpuController,
        nvidia: NvidiaGpuController,
        igpu: IntelGpuController,
        fan: FanController,
    ):
        self._config = config
        self._cpu = cpu
        self._nvidia = nvidia
        self._igpu = igpu
        self._fan = fan
        self._active_profile: Optional[str] = None
        self._init_default_profiles()

    def _init_default_profiles(self):
        """Varsayılan profilleri henüz yoksa oluştur."""
        existing = self._config.list_profiles()
        for name, data in DEFAULT_PROFILES.items():
            if name not in existing:
                self._config.save_profile(name, data)
                log.info("Varsayılan profil oluşturuldu: %s", name)

    @property
    def active_profile(self) -> Optional[str]:
        return self._active_profile

    def list_profiles(self) -> List[str]:
        """Kayıtlı profillerin listesini döndür."""
        return self._config.list_profiles()

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Bir profili oku."""
        return self._config.load_profile(name)

    def save_profile(self, name: str, data: Dict[str, Any]):
        """Bir profili kaydet."""
        self._config.save_profile(name, data)

    def delete_profile(self, name: str) -> bool:
        """Bir profili sil."""
        if name in DEFAULT_PROFILES:
            log.warning("Varsayılan profiller silinemez: %s", name)
            return False
        return self._config.delete_profile(name)

    def _capture_current_state(self) -> dict:
        """Profil uygulamadan önce mevcut durumu yakala (rollback için)."""
        try:
            cpu_st = self._cpu.get_status()
            igpu_st = self._igpu.get_status()
            state = {
                "cpu": {
                    "governor": cpu_st.governor,
                    "epp": cpu_st.epp,
                    "turbo": cpu_st.turbo_enabled,
                    "max_freq_khz": cpu_st.max_freq_khz,
                    "min_freq_khz": cpu_st.min_freq_khz,
                    "max_perf_pct": cpu_st.max_perf_pct,
                },
                "igpu": {
                    "min_freq_mhz": igpu_st.min_freq_mhz,
                    "max_freq_mhz": igpu_st.max_freq_mhz,
                },
            }
            # NVIDIA güç limiti
            if self._nvidia.available:
                try:
                    nv_st = self._nvidia.get_status()
                    state["nvidia"] = {
                        "power_limit": int(nv_st.power_limit),
                    }
                except Exception:
                    pass
            return state
        except Exception as e:
            log.warning("Durum yakalama hatası (rollback devre dışı): %s", e)
            return {}

    def _rollback(self, state: dict):
        """Önceki duruma geri dön."""
        if not state:
            return
        log.warning("Profil uygulaması kısmi başarısızlık — rollback başlıyor")

        cpu = state.get("cpu", {})
        if cpu:
            try:
                if "governor" in cpu:
                    self._cpu.set_governor(cpu["governor"])
                if "epp" in cpu:
                    self._cpu.set_epp(cpu["epp"])
                if "turbo" in cpu:
                    self._cpu.set_turbo(cpu["turbo"])
                if "max_perf_pct" in cpu:
                    self._cpu.set_max_perf_pct(cpu["max_perf_pct"])
                if "min_freq_khz" in cpu and "max_freq_khz" in cpu:
                    self._cpu.set_freq_range(cpu["min_freq_khz"], cpu["max_freq_khz"])
            except Exception as e:
                log.error("CPU rollback hatası: %s", e)

        igpu = state.get("igpu", {})
        if igpu and self._igpu.available:
            try:
                self._igpu.set_freq_range(
                    igpu.get("min_freq_mhz", 350),
                    igpu.get("max_freq_mhz", 1150),
                )
            except Exception as e:
                log.error("iGPU rollback hatası: %s", e)

        # NVIDIA saat limitleri ve güç limiti geri yükle
        if self._nvidia.available:
            try:
                self._nvidia.reset_gpu_clocks()
                nv = state.get("nvidia", {})
                if "power_limit" in nv:
                    self._nvidia.set_power_limit(nv["power_limit"])
            except Exception:
                pass

        log.info("Rollback tamamlandı")

    def apply_profile(self, name: str, temp_callback=None) -> bool:
        """Bir profili uygula."""
        profile = self._config.load_profile(name)
        if not profile:
            log.error("Profil bulunamadı: %s", name)
            return False

        log.info("Profil uygulanıyor: %s", profile.get("name", name))

        # Rollback için mevcut durumu yakala
        prev_state = self._capture_current_state()
        success = True
        failed_components = []

        # CPU ayarları
        cpu_settings = profile.get("cpu", {})
        if cpu_settings:
            cpu_ok = True
            if "governor" in cpu_settings:
                if not self._cpu.set_governor(cpu_settings["governor"]):
                    cpu_ok = False
            if "epp" in cpu_settings:
                if not self._cpu.set_epp(cpu_settings["epp"]):
                    cpu_ok = False
            if "turbo" in cpu_settings:
                if not self._cpu.set_turbo(cpu_settings["turbo"]):
                    cpu_ok = False
            if "max_perf_pct" in cpu_settings:
                if not self._cpu.set_max_perf_pct(cpu_settings["max_perf_pct"]):
                    cpu_ok = False
            if "max_freq_khz" in cpu_settings and "min_freq_khz" in cpu_settings:
                if not self._cpu.set_freq_range(
                    cpu_settings["min_freq_khz"], cpu_settings["max_freq_khz"]
                ):
                    cpu_ok = False
            if not cpu_ok:
                success = False
                failed_components.append("CPU")

        # NVIDIA GPU ayarları
        nvidia_settings = profile.get("nvidia", {})
        if nvidia_settings and self._nvidia.available:
            nv_ok = True
            if "power_limit" in nvidia_settings:
                if not self._nvidia.set_power_limit(nvidia_settings["power_limit"]):
                    nv_ok = False
            if "gpu_clock_max" in nvidia_settings:
                if not self._nvidia.set_gpu_clocks(300, nvidia_settings["gpu_clock_max"]):
                    nv_ok = False
            if "mem_clock_max" in nvidia_settings:
                if not self._nvidia.set_mem_clocks(405, nvidia_settings["mem_clock_max"]):
                    nv_ok = False
            if not nv_ok:
                failed_components.append("NVIDIA")

        # Intel iGPU ayarları
        igpu_settings = profile.get("igpu", {})
        if igpu_settings and self._igpu.available:
            min_f = igpu_settings.get("min_freq_mhz", 350)
            max_f = igpu_settings.get("max_freq_mhz", 1150)
            if not self._igpu.set_freq_range(min_f, max_f):
                failed_components.append("iGPU")

        # Fan ayarları
        fan_settings = profile.get("fan", {})
        if fan_settings and self._fan.available:
            fan_mode = fan_settings.get("mode", "auto")
            if fan_mode == "auto":
                self._fan.set_auto_mode()
            elif fan_mode == "manual":
                duty = fan_settings.get("duty_pct", 50)
                self._fan.set_both_fans(duty)
            elif fan_mode == "curve":
                curve_data = fan_settings.get("curve", [])
                if curve_data:
                    curve = [FanCurvePoint(**p) for p in curve_data]
                    self._fan.set_fan_curve(curve)
                    if temp_callback:
                        self._fan.start_auto_curve(temp_callback)

        # Kısmi başarısızlıkta rollback
        if failed_components:
            log.warning("Profil kısmi başarısızlık: %s", ", ".join(failed_components))
            self._rollback(prev_state)
            return False

        self._active_profile = name
        self._config.set("active_profile", name)
        log.info("Profil uygulandı: %s (başarı: True)", name)
        return True

    def create_profile_from_current(self, name: str, description: str = "") -> Dict[str, Any]:
        """Mevcut sistem ayarlarından profil oluştur."""
        cpu_status = self._cpu.get_status()
        nvidia_status = self._nvidia.get_status()
        igpu_status = self._igpu.get_status()

        profile = {
            "name": name,
            "description": description,
            "cpu": {
                "governor": cpu_status.governor,
                "epp": cpu_status.epp,
                "turbo": cpu_status.turbo_enabled,
                "max_freq_khz": cpu_status.max_freq_khz,
                "min_freq_khz": cpu_status.min_freq_khz,
                "max_perf_pct": cpu_status.max_perf_pct,
            },
            "nvidia": {
                "power_limit": int(nvidia_status.power_limit),
                "gpu_clock_max": nvidia_status.clock_max_graphics,
            },
            "igpu": {
                "min_freq_mhz": igpu_status.min_freq_mhz,
                "max_freq_mhz": igpu_status.max_freq_mhz,
            },
            "fan": {
                "mode": self._fan.mode,
                "curve": [{"temp": p.temp, "duty_pct": p.duty_pct} for p in self._fan.fan_curve],
            },
        }

        self._config.save_profile(name, profile)
        return profile
