"""
Monster HW Controller - Hardware Daemon
Root yetkili arka plan servisi. D-Bus üzerinden GUI ile iletişim kurar.
pkexec ile çalıştırılır.
"""

import json
import os
import signal
import sys
from dataclasses import asdict
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.cpu_controller import CpuController
from src.core.ec_access import EcAccess
from src.core.fan_controller import FanController, FanCurvePoint
from src.core.gpu_intel import IntelGpuController
from src.core.gpu_nvidia import NvidiaGpuController
from src.core.profile_manager import ProfileManager
from src.core.temp_monitor import TempMonitor
from src.daemon.dbus_interface import (
    DBUS_INTERFACE,
    DBUS_PATH,
    DBUS_SERVICE,
    INTROSPECTION_XML,
)
from src.utils.config import ConfigManager
from src.utils.logger import get_logger, setup_logger

log = get_logger("hw_daemon")


class HwControllerService:
    """D-Bus üzerinden donanım kontrol servisi."""

    def __init__(self):
        setup_logger(level=10)  # DEBUG
        log.info("Monster HW Controller Daemon başlatılıyor...")

        # Core bileşenler
        self._config = ConfigManager()
        self._temp_monitor = TempMonitor()
        self._cpu = CpuController()
        self._nvidia = NvidiaGpuController()
        self._igpu = IntelGpuController()
        self._ec = EcAccess()
        self._fan = FanController(self._ec, self._config.get("ec_register_map"))
        self._profile_manager = ProfileManager(
            self._config, self._cpu, self._nvidia, self._igpu, self._fan
        )

        log.info("Daemon bileşenleri hazır. EC: %s, NVIDIA: %s, iGPU: %s",
                 self._ec.available, self._nvidia.available, self._igpu.available)

    def _get_cpu_temp(self) -> float:
        """Fan eğrisi için CPU sıcaklığı callback'i."""
        reading = self._temp_monitor.read_all()
        return reading.cpu_package

    # --- D-Bus method implementations ---

    def GetTemperatures(self) -> str:
        reading = self._temp_monitor.read_all()
        data = {
            "cpu_package": reading.cpu_package,
            "cpu_cores": reading.cpu_cores,
            "gpu_nvidia": reading.gpu_nvidia,
            "pch": reading.pch,
            "nvme": reading.nvme,
            "wifi": reading.wifi,
            "acpi": reading.acpi,
        }
        return json.dumps(data)

    def GetCpuStatus(self) -> str:
        status = self._cpu.get_status()
        return json.dumps(asdict(status))

    def SetCpuGovernor(self, governor: str) -> bool:
        return self._cpu.set_governor(governor)

    def SetCpuEpp(self, epp: str) -> bool:
        return self._cpu.set_epp(epp)

    def SetCpuTurbo(self, enabled: bool) -> bool:
        return self._cpu.set_turbo(enabled)

    def SetCpuMaxPerfPct(self, pct: int) -> bool:
        return self._cpu.set_max_perf_pct(pct)

    def SetCpuMinPerfPct(self, pct: int) -> bool:
        return self._cpu.set_min_perf_pct(pct)

    def SetCpuFreqRange(self, min_khz: int, max_khz: int) -> bool:
        return self._cpu.set_freq_range(min_khz, max_khz)

    def GetNvidiaStatus(self) -> str:
        status = self._nvidia.get_status()
        return json.dumps(asdict(status))

    def SetNvidiaPowerLimit(self, watts: int) -> bool:
        return self._nvidia.set_power_limit(watts)

    def SetNvidiaGpuClocks(self, min_mhz: int, max_mhz: int) -> bool:
        return self._nvidia.set_gpu_clocks(min_mhz, max_mhz)

    def ResetNvidiaClocks(self) -> bool:
        return self._nvidia.reset_gpu_clocks()

    def GetIntelGpuStatus(self) -> str:
        status = self._igpu.get_status()
        return json.dumps(asdict(status))

    def SetIntelGpuFreqRange(self, min_mhz: int, max_mhz: int) -> bool:
        return self._igpu.set_freq_range(min_mhz, max_mhz)

    def GetFanStatus(self) -> str:
        status = self._fan.get_status()
        return json.dumps(asdict(status))

    def SetFanAutoMode(self) -> bool:
        return self._fan.set_auto_mode()

    def SetFanManualMode(self, duty_pct: int) -> bool:
        return self._fan.set_both_fans(duty_pct)

    def SetCpuFan(self, duty_pct: int) -> bool:
        return self._fan.set_cpu_fan(duty_pct)

    def SetGpuFan(self, duty_pct: int) -> bool:
        return self._fan.set_gpu_fan(duty_pct)

    def SetFanCurve(self, curve_json: str) -> bool:
        try:
            points = json.loads(curve_json)
            curve = [FanCurvePoint(**p) for p in points]
            self._fan.set_fan_curve(curve)
            return True
        except (json.JSONDecodeError, TypeError) as e:
            log.error("Fan eğrisi parse hatası: %s", e)
            return False

    def StartFanCurve(self) -> bool:
        self._fan.start_auto_curve(self._get_cpu_temp)
        return True

    def ListProfiles(self) -> str:
        profiles = self._profile_manager.list_profiles()
        return json.dumps(profiles)

    def GetProfile(self, name: str) -> str:
        profile = self._profile_manager.get_profile(name)
        return json.dumps(profile) if profile else "{}"

    def ApplyProfile(self, name: str) -> bool:
        return self._profile_manager.apply_profile(name, self._get_cpu_temp)

    def SaveProfile(self, name: str, json_data: str) -> bool:
        try:
            data = json.loads(json_data)
            self._profile_manager.save_profile(name, data)
            return True
        except json.JSONDecodeError:
            return False

    def DeleteProfile(self, name: str) -> bool:
        return self._profile_manager.delete_profile(name)

    def CreateProfileFromCurrent(self, name: str, description: str) -> str:
        profile = self._profile_manager.create_profile_from_current(name, description)
        return json.dumps(profile)

    def GetActiveProfile(self) -> str:
        return self._profile_manager.active_profile or ""


def run_daemon():
    """Daemon'u GLib mainloop ile başlat."""
    try:
        import gi
        gi.require_version("Gio", "2.0")
        gi.require_version("GLib", "2.0")
        from gi.repository import Gio, GLib

    except (ImportError, ValueError):
        log.error("GLib/Gio bulunamadı. GTK3 geliştirme paketleri gerekli.")
        sys.exit(1)

    service = HwControllerService()
    loop = GLib.MainLoop()

    def on_bus_acquired(connection, name):
        log.info("D-Bus bağlantısı sağlandı: %s", name)

        node_info = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION_XML)
        interface_info = node_info.interfaces[0]

        def on_method_call(connection, sender, object_path, interface_name,
                          method_name, parameters, invocation):
            """D-Bus metot çağrılarını işle (güvenlik beyaz listesi ile)."""
            # Güvenlik: Sadece izin verilen metotlar çağrılabilir
            ALLOWED_METHODS = {
                "GetTemperatures", "GetCpuStatus", "SetCpuGovernor",
                "SetCpuEpp", "SetCpuTurbo", "SetCpuMaxPerfPct",
                "SetCpuMinPerfPct", "SetCpuFreqRange",
                "GetNvidiaStatus", "SetNvidiaPowerLimit",
                "SetNvidiaGpuClocks", "ResetNvidiaClocks",
                "GetIntelGpuStatus", "SetIntelGpuFreqRange",
                "GetFanStatus", "SetFanAutoMode", "SetFanManualMode",
                "SetCpuFan", "SetGpuFan", "SetFanCurve", "StartFanCurve",
                "ListProfiles", "GetProfile", "ApplyProfile",
                "SaveProfile", "DeleteProfile",
                "CreateProfileFromCurrent", "GetActiveProfile",
            }

            try:
                if method_name not in ALLOWED_METHODS:
                    log.warning("Reddedilen D-Bus çağrısı: %s (gönderen: %s)",
                                method_name, sender)
                    invocation.return_error_literal(
                        Gio.dbus_error_quark(), Gio.DBusError.UNKNOWN_METHOD,
                        f"Bilinmeyen veya yasaklı metot: {method_name}"
                    )
                    return

                method = getattr(service, method_name)

                # Parametreleri unpack et
                args = []
                if parameters:
                    for i in range(parameters.n_children()):
                        child = parameters.get_child_value(i)
                        # GVariant tipine göre dönüştür
                        vtype = child.get_type_string()
                        if vtype == "s":
                            args.append(child.get_string())
                        elif vtype == "i":
                            args.append(child.get_int32())
                        elif vtype == "b":
                            args.append(child.get_boolean())
                        elif vtype == "d":
                            args.append(child.get_double())

                result = method(*args)

                # Sonucu GVariant olarak paketle
                if isinstance(result, bool):
                    ret = GLib.Variant("(b)", (result,))
                elif isinstance(result, str):
                    ret = GLib.Variant("(s)", (result,))
                elif isinstance(result, int):
                    ret = GLib.Variant("(i)", (result,))
                else:
                    ret = GLib.Variant("(s)", (str(result),))

                invocation.return_value(ret)

            except Exception as e:
                log.error("D-Bus metot hatası (%s): %s", method_name, e)
                invocation.return_error_literal(
                    Gio.dbus_error_quark(), Gio.DBusError.FAILED, str(e)
                )

        connection.register_object(
            DBUS_PATH,
            interface_info,
            on_method_call,
            None,  # get_property
            None,  # set_property
        )

    def on_name_acquired(connection, name):
        log.info("D-Bus ismi alındı: %s", name)

    def on_name_lost(connection, name):
        log.warning("D-Bus ismi kaybedildi: %s", name)
        loop.quit()

    Gio.bus_own_name(
        Gio.BusType.SYSTEM,
        DBUS_SERVICE,
        Gio.BusNameOwnerFlags.NONE,
        on_bus_acquired,
        on_name_acquired,
        on_name_lost,
    )

    # SIGTERM/SIGINT ile düzgün kapatma
    def shutdown(signum, frame):
        log.info("Daemon kapatılıyor (sinyal: %d)...", signum)
        service._fan.set_auto_mode()  # Kapanırken fanları otomatiğe al
        loop.quit()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info("Daemon çalışıyor...")
    try:
        loop.run()
    except KeyboardInterrupt:
        service._fan.set_auto_mode()
        log.info("Daemon durduruldu.")


if __name__ == "__main__":
    run_daemon()
