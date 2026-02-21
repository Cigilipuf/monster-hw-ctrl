#!/usr/bin/env python3
"""
Monster TULPAR T5 V19.2 - Linux Donanım Kontrolcüsü
Ana giriş noktası.

Kullanım:
    python3 -m src.main                  # GUI başlat
    sudo python3 -m src.main --daemon    # Arka plan daemon
    python3 -m src.main status           # Anlık durum özeti
    python3 -m src.main profile list     # Profilleri listele
    python3 -m src.main profile apply <ad>  # Profil uygula
    python3 -m src.main cpu --governor performance --turbo on
    python3 -m src.main gpu --power-limit 60
    python3 -m src.main fan --mode auto
"""

import argparse
import sys
import os
import signal

# Proje kökünü sys.path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def run_gui():
    """GTK3 GUI uygulamasını başlat."""
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib

    from src.gui.main_window import MainWindow
    from src.utils.logger import setup_logger, get_logger

    # Logger'ı başlat (tüm alt modüller için handler oluşturulur)
    setup_logger()
    log = get_logger("main")

    # SIGINT ile düzgün kapanma
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, Gtk.main_quit)

    log.info("=" * 50)
    log.info("Monster HW Controller başlatılıyor...")
    log.info("PID: %d, UID: %d, Root: %s",
             os.getpid(), os.getuid(), os.geteuid() == 0)
    log.info("Python: %s", sys.version.split()[0])
    log.info("=" * 50)

    # Global exception handler
    def on_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical("Yakalanmamış hata!", exc_info=(exc_type, exc_value, exc_tb))
    sys.excepthook = on_exception

    win = MainWindow()
    win.show_all()
    Gtk.main()

    log.info("Uygulama kapatıldı")


def run_daemon():
    """Root yetkili arka plan daemon'unu başlat."""
    from src.daemon.hw_daemon import run_daemon
    run_daemon()


# ============================================================
# CLI Komutları
# ============================================================

def _init_cli_controllers():
    """CLI için core controller'ları başlat."""
    from src.core.cpu_controller import CpuController
    from src.core.ec_access import EcAccess
    from src.core.fan_controller import FanController
    from src.core.gpu_intel import IntelGpuController
    from src.core.gpu_nvidia import NvidiaGpuController
    from src.core.temp_monitor import TempMonitor
    from src.core.profile_manager import ProfileManager
    from src.utils.config import ConfigManager

    config = ConfigManager()
    cpu = CpuController()
    nvidia = NvidiaGpuController()
    igpu = IntelGpuController()
    ec = EcAccess()
    fan = FanController(ec)
    temp = TempMonitor()
    pm = ProfileManager(config, cpu, nvidia, igpu, fan)

    return {
        "config": config, "cpu": cpu, "nvidia": nvidia,
        "igpu": igpu, "ec": ec, "fan": fan, "temp": temp, "pm": pm,
    }


def cmd_status(_args):
    """Anlık sistem durum özeti yazdır."""
    c = _init_cli_controllers()

    temp_reading = c["temp"].read_all()
    cpu_st = c["cpu"].get_status()
    nv_st = c["nvidia"].get_status()
    igpu_st = c["igpu"].get_status()
    fan_st = c["fan"].get_status()

    print("=== Monster HW Controller — Anlık Durum ===\n")

    print(f"  CPU Sıcaklık:  {temp_reading.cpu_package}°C")
    print(f"  CPU Governor:  {cpu_st.governor}   EPP: {cpu_st.epp}")
    print(f"  CPU Turbo:     {'Açık' if cpu_st.turbo_enabled else 'Kapalı'}")
    avg_freq = sum(cpu_st.cur_freqs_khz) / len(cpu_st.cur_freqs_khz) / 1000 if cpu_st.cur_freqs_khz else 0
    print(f"  CPU Frekans:   {cpu_st.min_freq_khz/1000:.0f}–{cpu_st.max_freq_khz/1000:.0f} MHz  "
          f"(şu an ~{avg_freq:.0f} MHz)")
    print(f"  Max Perf %:    {cpu_st.max_perf_pct}%")
    print()

    if nv_st.available:
        print(f"  NVIDIA GPU:    {nv_st.temp}°C   {nv_st.power_draw:.1f}W / {nv_st.power_limit:.0f}W")
        print(f"  GPU Clock:     {nv_st.clock_graphics} MHz   Mem: {nv_st.clock_memory} MHz")
        print(f"  Kullanım:      GPU {nv_st.utilization_gpu}%  Mem {nv_st.utilization_memory}%")
    else:
        print("  NVIDIA GPU:    Erişilemiyor")
    print()

    if igpu_st.available:
        print(f"  Intel iGPU:    {igpu_st.act_freq_mhz} MHz  ({igpu_st.min_freq_mhz}–{igpu_st.max_freq_mhz} MHz)")
    else:
        print("  Intel iGPU:    Erişilemiyor")
    print()

    if fan_st.ec_available:
        print(f"  Fan CPU RPM:   {fan_st.cpu_fan_rpm}")
        print(f"  Fan GPU RPM:   {fan_st.gpu_fan_rpm}")
        print(f"  Fan Modu:      {fan_st.mode}")
    else:
        print("  Fan:           EC erişilemiyor")

    others = []
    if temp_reading.pch:
        others.append(f"PCH: {temp_reading.pch}°C")
    if temp_reading.nvme:
        others.append(f"NVMe: {temp_reading.nvme}°C")
    if temp_reading.wifi:
        others.append(f"WiFi: {temp_reading.wifi}°C")
    if others:
        print(f"\n  Diğer:         {', '.join(others)}")

    print()


def cmd_profile(args):
    """Profil yönetimi."""
    c = _init_cli_controllers()
    pm = c["pm"]

    if args.profile_action == "list":
        profiles = pm.list_profiles()
        active = pm.active_profile
        print("Kayıtlı Profiller:")
        for name in profiles:
            p = pm.get_profile(name) or {}
            marker = " (aktif)" if name == active else ""
            desc = p.get("description", "")
            print(f"  • {name}{marker}" + (f" — {desc}" if desc else ""))

    elif args.profile_action == "apply":
        if not args.profile_name:
            print("Hata: Profil adı belirtilmeli. Örnek: profile apply dengeli")
            sys.exit(1)
        name = args.profile_name

        def temp_cb():
            return c["temp"].read_all().cpu_package

        if pm.apply_profile(name, temp_callback=temp_cb):
            print(f"✓ Profil uygulandı: {name}")
        else:
            print(f"✗ Profil uygulanamadı: {name}")
            sys.exit(1)
    else:
        print("Bilinmeyen profil alt komutu. Kullanım: profile list|apply <ad>")


def cmd_cpu(args):
    """CPU ayarlarını CLI'den uygula."""
    c = _init_cli_controllers()
    cpu = c["cpu"]
    changed = False

    if args.governor:
        if cpu.set_governor(args.governor):
            print(f"✓ Governor: {args.governor}")
        else:
            print(f"✗ Governor ayarlanamadı: {args.governor}")
        changed = True

    if args.epp:
        if cpu.set_epp(args.epp):
            print(f"✓ EPP: {args.epp}")
        else:
            print(f"✗ EPP ayarlanamadı: {args.epp}")
        changed = True

    if args.turbo is not None:
        val = args.turbo.lower() in ("on", "1", "true", "yes")
        if cpu.set_turbo(val):
            print(f"✓ Turbo: {'Açık' if val else 'Kapalı'}")
        else:
            print("✗ Turbo ayarlanamadı")
        changed = True

    if args.max_perf_pct is not None:
        if cpu.set_max_perf_pct(args.max_perf_pct):
            print(f"✓ Max Perf %: {args.max_perf_pct}")
        else:
            print("✗ Max Perf % ayarlanamadı")
        changed = True

    if not changed:
        # Sadece durum göster
        st = cpu.get_status()
        print(f"Governor: {st.governor}  EPP: {st.epp}  Turbo: {'on' if st.turbo_enabled else 'off'}")
        print(f"Frekans: {st.min_freq_khz/1000:.0f}–{st.max_freq_khz/1000:.0f} MHz  Max Perf: {st.max_perf_pct}%")


def cmd_gpu(args):
    """GPU ayarlarını CLI'den uygula."""
    c = _init_cli_controllers()
    nv = c["nvidia"]
    changed = False

    if not nv.available:
        print("✗ NVIDIA GPU erişilemiyor")
        sys.exit(1)

    if args.power_limit is not None:
        if nv.set_power_limit(args.power_limit):
            print(f"✓ Güç limiti: {args.power_limit}W")
        else:
            print("✗ Güç limiti ayarlanamadı")
        changed = True

    if args.reset_clocks:
        nv.reset_gpu_clocks()
        nv.reset_mem_clocks()
        print("✓ Saat limitleri sıfırlandı")
        changed = True

    if not changed:
        st = nv.get_status()
        print(f"Sıcaklık: {st.temp}°C  Güç: {st.power_draw:.1f}W/{st.power_limit:.0f}W")
        print(f"GPU Clock: {st.clock_graphics} MHz  Mem: {st.clock_memory} MHz  Util: {st.utilization_gpu}%")


def cmd_fan(args):
    """Fan ayarlarını CLI'den uygula."""
    c = _init_cli_controllers()
    fan = c["fan"]

    if not fan.available:
        print("✗ EC erişilemiyor, fan kontrolü kullanılamaz")
        sys.exit(1)

    if args.mode == "auto":
        fan.set_auto_mode()
        print("✓ Fan modu: auto")
    elif args.mode == "manual":
        duty = args.duty or 50
        fan.set_both_fans(duty)
        print(f"✓ Fan modu: manual — duty {duty}%")
    elif args.mode:
        print(f"Bilinmeyen fan modu: {args.mode}")
    else:
        st = fan.get_status()
        print(f"Mod: {st.mode}  CPU RPM: {st.cpu_fan_rpm}  GPU RPM: {st.gpu_fan_rpm}")


def build_parser() -> argparse.ArgumentParser:
    """Argparse parser oluştur."""
    parser = argparse.ArgumentParser(
        prog="monster-hw-ctrl",
        description="Monster TULPAR T5 V19.2 — Donanım Kontrolcüsü",
    )
    sub = parser.add_subparsers(dest="command")

    # GUI (varsayılan)
    sub.add_parser("gui", help="GTK3 arayüzünü başlat")

    # Daemon
    sub.add_parser("daemon", help="Root yetkili arka plan daemon")

    # Status
    sub.add_parser("status", help="Anlık sistem durumunu göster")

    # Profile
    p_prof = sub.add_parser("profile", help="Profil yönetimi")
    p_prof.add_argument("profile_action", choices=["list", "apply"], help="list veya apply")
    p_prof.add_argument("profile_name", nargs="?", help="Profil adı (apply için)")

    # CPU
    p_cpu = sub.add_parser("cpu", help="CPU ayarları")
    p_cpu.add_argument("--governor", choices=["powersave", "performance"])
    p_cpu.add_argument("--epp", choices=["default", "performance", "balance_performance", "balance_power", "power"])
    p_cpu.add_argument("--turbo", help="on/off")
    p_cpu.add_argument("--max-perf-pct", type=int, dest="max_perf_pct")

    # GPU
    p_gpu = sub.add_parser("gpu", help="NVIDIA GPU ayarları")
    p_gpu.add_argument("--power-limit", type=int, dest="power_limit")
    p_gpu.add_argument("--reset-clocks", action="store_true", dest="reset_clocks")

    # Fan
    p_fan = sub.add_parser("fan", help="Fan kontrolü")
    p_fan.add_argument("--mode", choices=["auto", "manual"])
    p_fan.add_argument("--duty", type=int, help="Manuel mod için duty % (20-100)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cmd = args.command

    if cmd == "daemon" or (len(sys.argv) > 1 and sys.argv[1] == "--daemon"):
        run_daemon()
    elif cmd == "status":
        cmd_status(args)
    elif cmd == "profile":
        cmd_profile(args)
    elif cmd == "cpu":
        cmd_cpu(args)
    elif cmd == "gpu":
        cmd_gpu(args)
    elif cmd == "fan":
        cmd_fan(args)
    else:
        # Varsayılan: GUI
        run_gui()


if __name__ == "__main__":
    main()
