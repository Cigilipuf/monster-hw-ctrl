"""
Monster HW Controller - Configuration Manager
JSON tabanlı yapılandırma yönetimi.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

log = get_logger("config")

CONFIG_DIR = Path.home() / ".config" / "monster-hw-ctrl"
PROFILES_DIR = CONFIG_DIR / "profiles"
MAIN_CONFIG_FILE = CONFIG_DIR / "settings.json"

# Varsayılan uygulama ayarları
DEFAULT_SETTINGS = {
    "refresh_interval_ms": 1500,
    "fan_refresh_interval_ms": 2500,
    "active_profile": None,
    "start_minimized": False,
    "enable_notifications": True,
    "temp_unit": "celsius",
    "language": "tr",
    "ec_confirmed": False,
    "ec_register_map": {
        "cpu_fan_duty": 0x68,
        "gpu_fan_duty": 0x69,
        "cpu_fan_rpm_lsb": 0xCE,
        "cpu_fan_rpm_msb": 0xCF,
        "gpu_fan_rpm_lsb": 0xD0,
        "gpu_fan_rpm_msb": 0xD1,
        "fan_mode": 0xD7,
    },
}


class ConfigManager:
    """JSON yapılandırma dosyalarını yönetir."""

    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._ensure_dirs()
        self._load_settings()

    def _ensure_dirs(self):
        """Gerekli dizinleri oluştur."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def _load_settings(self):
        """Ana ayar dosyasını yükle."""
        if MAIN_CONFIG_FILE.exists():
            try:
                with open(MAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Varsayılanları temel al, yüklenen değerlerle üzerine yaz
                self._settings = dict(DEFAULT_SETTINGS)
                self._settings.update(loaded)
                log.info("Ayarlar yüklendi: %s", MAIN_CONFIG_FILE)
            except (json.JSONDecodeError, IOError) as e:
                log.warning("Ayar dosyası okunamadı: %s - Varsayılanlar kullanılacak", e)
                self._settings = dict(DEFAULT_SETTINGS)
        else:
            self._settings = dict(DEFAULT_SETTINGS)
            self.save_settings()
            log.info("Varsayılan ayarlar oluşturuldu: %s", MAIN_CONFIG_FILE)

    def save_settings(self):
        """Ayarları dosyaya kaydet."""
        try:
            with open(MAIN_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            log.error("Ayarlar kaydedilemedi: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Bir ayar değeri al."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Bir ayar değeri belirle ve kaydet."""
        self._settings[key] = value
        self.save_settings()

    @property
    def settings(self) -> Dict[str, Any]:
        return dict(self._settings)

    # --- Profil Yönetimi ---

    def list_profiles(self) -> list:
        """Kayıtlı profillerin isimlerini döndür."""
        profiles = []
        for f in PROFILES_DIR.glob("*.json"):
            profiles.append(f.stem)
        return sorted(profiles)

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Bir profili yükle."""
        path = PROFILES_DIR / f"{name}.json"
        if not path.exists():
            log.warning("Profil bulunamadı: %s", name)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log.error("Profil okunamadı (%s): %s", name, e)
            return None

    def save_profile(self, name: str, data: Dict[str, Any]):
        """Bir profili kaydet."""
        path = PROFILES_DIR / f"{name}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log.info("Profil kaydedildi: %s", name)
        except IOError as e:
            log.error("Profil kaydedilemedi (%s): %s", name, e)

    def delete_profile(self, name: str) -> bool:
        """Bir profili sil."""
        path = PROFILES_DIR / f"{name}.json"
        if path.exists():
            path.unlink()
            log.info("Profil silindi: %s", name)
            if self.get("active_profile") == name:
                self.set("active_profile", None)
            return True
        return False
