"""
Monster HW Controller - Main Window
GTK3 ana pencere. Notebook sekmelerinde dashboard, CPU, GPU, fan ve profil panelleri.
Periyodik olarak sensör verilerini okur ve panelleri günceller.
"""

import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from src.core.cpu_controller import CpuController
from src.core.ec_access import EcAccess
from src.core.fan_controller import FanController, FanCurvePoint
from src.core.gpu_intel import IntelGpuController
from src.core.gpu_nvidia import NvidiaGpuController
from src.core.notifier import TempNotifier
from src.core.profile_manager import ProfileManager
from src.core.thermal_protection import ThermalProtection
from src.core.temp_monitor import TempMonitor
from src.gui.cpu_panel import CpuPanel
from src.gui.dashboard import DashboardPanel
from src.gui.fan_panel import FanPanel
from src.gui.gpu_panel import GpuPanel
from src.gui.profile_panel import ProfilePanel
from src.gui.tray_icon import TrayIcon
from src.utils.config import ConfigManager
from src.utils.logger import get_logger

log = get_logger("main_window")

APP_CSS = """
window {
    background-color: #1e1e2e;
}
notebook tab {
    padding: 6px 14px;
}
notebook tab label {
    color: #cdd6f4;
    font-weight: bold;
}
frame > label {
    color: #89b4fa;
    font-weight: bold;
}
frame {
    border-color: #45475a;
}
label {
    color: #cdd6f4;
}
.dim-label {
    color: #6c7086;
}
button.suggested-action {
    background-color: #89b4fa;
    color: #1e1e2e;
}
button.destructive-action {
    background-color: #f38ba8;
    color: #1e1e2e;
}
scale trough {
    min-height: 6px;
    background-color: #313244;
}
scale trough highlight {
    background-color: #89b4fa;
}
scale slider {
    min-width: 14px;
    min-height: 14px;
    border-radius: 7px;
    background-color: #cdd6f4;
}
spinbutton {
    background-color: #313244;
    color: #cdd6f4;
}
entry {
    background-color: #313244;
    color: #cdd6f4;
}
combobox button {
    background-color: #313244;
    color: #cdd6f4;
}
switch {
    background-color: #313244;
}
switch:checked {
    background-color: #89b4fa;
}
list {
    background-color: #1e1e2e;
}
list row {
    background-color: #1e1e2e;
}
list row:selected {
    background-color: #313244;
}
scrolledwindow {
    background-color: #1e1e2e;
}
"""


class MainWindow(Gtk.Window):
    """Ana uygulama penceresi."""

    def __init__(self):
        super().__init__(title="Monster TULPAR T5 - Donanım Kontrolcüsü")
        self.set_default_size(820, 680)
        self.set_position(Gtk.WindowPosition.CENTER)

        # CSS uygula
        self._apply_css()

        # Core bileşenleri başlat
        self._init_controllers()

        # GUI oluştur
        self._build_ui()

        # Callback'leri bağla
        self._connect_callbacks()

        # Profil listesini yükle
        self._refresh_profiles()

        # System tray icon
        self._tray = TrayIcon(self)

        # Periyodik güncelleme zamanlayıcıları
        refresh_ms = self._config.get("refresh_interval_ms", 1500)
        fan_refresh_ms = self._config.get("fan_refresh_interval_ms", 2500)

        self._timer_main = GLib.timeout_add(refresh_ms, self._on_refresh)
        self._timer_fan = GLib.timeout_add(fan_refresh_ms, self._on_fan_refresh)

        # İlk güncelleme
        GLib.idle_add(self._on_refresh)
        GLib.idle_add(self._on_fan_refresh)

        # Pencere kapatma
        self.connect("destroy", self._on_destroy)

        log.info("Ana pencere başlatıldı")

    def _apply_css(self):
        """Uygulama CSS stilini uygula."""
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_data(APP_CSS.encode())
            screen = Gdk.Screen.get_default()
            Gtk.StyleContext.add_provider_for_screen(
                screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            log.warning("CSS yüklenemedi: %s", e)

    def _init_controllers(self):
        """Core kontrol bileşenlerini başlat."""
        self._config = ConfigManager()
        self._temp_monitor = TempMonitor()
        self._cpu = CpuController()
        self._nvidia = NvidiaGpuController()
        self._igpu = IntelGpuController()
        self._ec = EcAccess()
        self._fan = FanController(self._ec)
        self._profile_manager = ProfileManager(
            self._config, self._cpu, self._nvidia, self._igpu, self._fan
        )
        self._notifier = TempNotifier()
        self._thermal = ThermalProtection(self._cpu, self._nvidia, self._fan)

        log.info("Controller'lar başlatıldı - EC: %s, NVIDIA: %s, iGPU: %s",
                 self._ec.available, self._nvidia.available, self._igpu.available)

    def _build_ui(self):
        """GUI bileşenlerini oluştur."""
        # Ana container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Monster HW Controller")
        header.set_subtitle("TULPAR T5 V19.2")
        self.set_titlebar(header)

        # Hızlı profil butonları (headerbar'da)
        profile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        btn_sessiz = Gtk.Button(label="🔇")
        btn_sessiz.set_tooltip_text("Sessiz Profil")
        btn_sessiz.connect("clicked", lambda b: self._quick_profile("sessiz"))
        profile_box.pack_start(btn_sessiz, False, False, 0)

        btn_dengeli = Gtk.Button(label="⚖️")
        btn_dengeli.set_tooltip_text("Dengeli Profil")
        btn_dengeli.connect("clicked", lambda b: self._quick_profile("dengeli"))
        profile_box.pack_start(btn_dengeli, False, False, 0)

        btn_perf = Gtk.Button(label="🚀")
        btn_perf.set_tooltip_text("Performans Profil")
        btn_perf.connect("clicked", lambda b: self._quick_profile("performans"))
        profile_box.pack_start(btn_perf, False, False, 0)

        btn_game = Gtk.Button(label="🎮")
        btn_game.set_tooltip_text("Oyun Profil")
        btn_game.connect("clicked", lambda b: self._quick_profile("oyun"))
        profile_box.pack_start(btn_game, False, False, 0)

        btn_battery = Gtk.Button(label="🔋")
        btn_battery.set_tooltip_text("Pil Tasarrufu")
        btn_battery.connect("clicked", lambda b: self._quick_profile("pil_tasarrufu"))
        profile_box.pack_start(btn_battery, False, False, 0)

        header.pack_start(profile_box)

        # Refresh butonu
        refresh_btn = Gtk.Button()
        refresh_btn.set_tooltip_text("Yenile")
        refresh_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic",
                                                      Gtk.IconSize.BUTTON)
        refresh_btn.set_image(refresh_icon)
        refresh_btn.connect("clicked", lambda b: self._on_refresh())
        header.pack_end(refresh_btn)

        # Notebook (sekmeler)
        self._notebook = Gtk.Notebook()
        self._notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Paneller
        self._dashboard = DashboardPanel()
        self._cpu_panel = CpuPanel()
        self._gpu_panel = GpuPanel()
        self._fan_panel = FanPanel()
        self._profile_panel = ProfilePanel()

        # Scrolled wrapper'lar
        panels = [
            (self._dashboard, "📊 Dashboard"),
            (self._cpu_panel, "🔲 CPU"),
            (self._gpu_panel, "🎯 GPU"),
            (self._fan_panel, "💨 Fan"),
            (self._profile_panel, "📋 Profiller"),
        ]

        for panel, title in panels:
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.add(panel)
            tab_label = Gtk.Label(label=title)
            self._notebook.append_page(scroll, tab_label)

        main_box.pack_start(self._notebook, True, True, 0)

        # Alt bilgi çubuğu
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.set_margin_start(8)
        status_bar.set_margin_end(8)
        status_bar.set_margin_top(2)
        status_bar.set_margin_bottom(2)

        self._ec_indicator = Gtk.Label()
        status_bar.pack_start(self._ec_indicator, False, False, 0)

        self._nvidia_indicator = Gtk.Label()
        status_bar.pack_start(self._nvidia_indicator, False, False, 0)

        self._igpu_indicator = Gtk.Label()
        status_bar.pack_start(self._igpu_indicator, False, False, 0)

        # Root uyarısı
        self._root_label = Gtk.Label()
        if os.geteuid() != 0:
            self._root_label.set_markup(
                '<small><span color="#ff9800">⚠ Root yetkisi yok — kontrol işlevleri çalışmayabilir</span></small>'
            )
        else:
            self._root_label.set_markup(
                '<small><span color="#4caf50">✓ Root yetkisi mevcut</span></small>'
            )
        status_bar.pack_end(self._root_label, False, False, 0)

        main_box.pack_start(status_bar, False, False, 0)

        self.add(main_box)
        self._update_indicators()

    def _update_indicators(self):
        """Alt çubuk göstergelerini güncelle."""
        ec_color = "#4caf50" if self._ec.available else "#f44336"
        ec_text = "EC:✓" if self._ec.available else "EC:✗"
        self._ec_indicator.set_markup(
            f'<small><span color="{ec_color}"> {ec_text} </span></small>'
        )

        nv_color = "#4caf50" if self._nvidia.available else "#78909c"
        nv_text = "NV:✓" if self._nvidia.available else "NV:—"
        self._nvidia_indicator.set_markup(
            f'<small><span color="{nv_color}"> {nv_text} </span></small>'
        )

        ig_color = "#4caf50" if self._igpu.available else "#78909c"
        ig_text = "iGPU:✓" if self._igpu.available else "iGPU:—"
        self._igpu_indicator.set_markup(
            f'<small><span color="{ig_color}"> {ig_text} </span></small>'
        )

    def _connect_callbacks(self):
        """Panel callback'lerini controller'lara bağla."""

        # CPU Panel
        self._cpu_panel.on_apply(self._apply_cpu)

        # GPU Panel
        self._gpu_panel.on_nvidia_apply(self._apply_nvidia)
        self._gpu_panel.on_igpu_apply(self._apply_igpu)

        # Fan Panel
        self._fan_panel.on_apply(self._apply_fan)

        # Profile Panel
        self._profile_panel.on_apply(self._apply_profile)
        self._profile_panel.on_create(self._create_profile)
        self._profile_panel.on_delete(self._delete_profile)
        self._profile_panel.on_edit(self._edit_profile)

    # === Controller Callback'leri ===

    def _apply_cpu(self, settings):
        """CPU ayarlarını uygula."""
        success = True
        if "governor" in settings:
            success &= self._cpu.set_governor(settings["governor"])
        if "epp" in settings:
            success &= self._cpu.set_epp(settings["epp"])
        if "turbo" in settings:
            success &= self._cpu.set_turbo(settings["turbo"])
        if "min_freq_khz" in settings and "max_freq_khz" in settings:
            success &= self._cpu.set_freq_range(
                settings["min_freq_khz"], settings["max_freq_khz"]
            )
        if "min_perf_pct" in settings:
            success &= self._cpu.set_min_perf_pct(settings["min_perf_pct"])
        if "max_perf_pct" in settings:
            success &= self._cpu.set_max_perf_pct(settings["max_perf_pct"])
        return success

    def _apply_nvidia(self, settings):
        """NVIDIA ayarlarını uygula."""
        if settings.get("action") == "reset_clocks":
            return self._nvidia.reset_gpu_clocks()

        success = True
        if "power_limit" in settings:
            success &= self._nvidia.set_power_limit(settings["power_limit"])
        if "gpu_clock_min" in settings and "gpu_clock_max" in settings:
            success &= self._nvidia.set_gpu_clocks(
                settings["gpu_clock_min"], settings["gpu_clock_max"]
            )
        if "mem_clock_min" in settings and "mem_clock_max" in settings:
            success &= self._nvidia.set_mem_clocks(
                settings["mem_clock_min"], settings["mem_clock_max"]
            )
        return success

    def _apply_igpu(self, settings):
        """iGPU ayarlarını uygula."""
        return self._igpu.set_freq_range(
            settings["min_freq_mhz"], settings["max_freq_mhz"]
        )

    def _apply_fan(self, settings):
        """Fan ayarlarını uygula."""
        mode = settings.get("mode", "auto")

        if mode == "auto":
            return self._fan.set_auto_mode()
        elif mode == "manual":
            cpu_duty = settings.get("cpu_duty_pct", 50)
            gpu_duty = settings.get("gpu_duty_pct", 50)
            s1 = self._fan.set_cpu_fan(cpu_duty)
            s2 = self._fan.set_gpu_fan(gpu_duty)
            return s1 and s2
        elif mode == "curve":
            curve_data = settings.get("curve", [])
            if curve_data:
                curve = [FanCurvePoint(**p) for p in curve_data]
                self._fan.set_fan_curve(curve)

                def get_cpu_temp():
                    reading = self._temp_monitor.read_all()
                    return reading.cpu_package

                self._fan.start_auto_curve(get_cpu_temp)
                return True
        return False

    def _apply_profile(self, profile_name):
        """Profil uygula."""
        def temp_cb():
            return self._temp_monitor.read_all().cpu_package

        success = self._profile_manager.apply_profile(profile_name, temp_callback=temp_cb)
        if success:
            self._profile_panel.set_active_profile(profile_name)
            self._dashboard.update_profile(profile_name)
            self._tray.update_profile(profile_name)
            self._refresh_profiles()
        return success

    def _create_profile(self, name, description):
        """Mevcut ayarlardan profil oluştur."""
        try:
            self._profile_manager.create_profile_from_current(name, description)
            self._refresh_profiles()
            return True
        except Exception as e:
            log.error("Profil oluşturulamadı: %s", e)
            return False

    def _delete_profile(self, name):
        """Profil sil."""
        success = self._profile_manager.delete_profile(name)
        if success:
            self._refresh_profiles()
        return success

    def _edit_profile(self, name, new_data):
        """Profil düzenle ve kaydet."""
        try:
            self._profile_manager.save_profile(name, new_data)
            self._refresh_profiles()
            return True
        except Exception as e:
            log.error("Profil düzenlenemedi: %s", e)
            return False

    def _quick_profile(self, name):
        """Header bar'dan hızlı profil geçişi."""
        self._apply_profile(name)

    def _refresh_profiles(self):
        """Profil listesini yenile."""
        profile_names = self._profile_manager.list_profiles()
        profiles_data = []
        for name in profile_names:
            data = self._profile_manager.get_profile(name) or {}
            profiles_data.append((name, data))

        self._profile_panel.refresh_list(profiles_data)
        active = self._profile_manager.active_profile
        if active:
            self._profile_panel.set_active_profile(active)

    # === Periyodik Güncelleme ===

    def _on_refresh(self):
        """Ana güncelleme döngüsü (sıcaklık, CPU, GPU)."""
        try:
            # Sıcaklık
            temp_reading = self._temp_monitor.read_all()
            self._dashboard.update_temps(temp_reading)

            # Tray icon sıcaklık güncelleme
            self._tray.update_temps(temp_reading.cpu_package, temp_reading.gpu_nvidia)

            # CPU sıcaklığını fan eğrisi editörüne ilet
            self._fan_panel.set_current_temp(temp_reading.cpu_package)

            # CPU
            cpu_status = self._cpu.get_status()
            self._dashboard.update_cpu(cpu_status)
            self._cpu_panel.update_from_status(cpu_status)

            # NVIDIA GPU
            nvidia_status = self._nvidia.get_status()
            self._dashboard.update_nvidia(nvidia_status)
            self._gpu_panel.update_nvidia_status(nvidia_status)

            # NVIDIA sıcaklığını TempMonitor'a ilet (çift subprocess engelleme)
            if nvidia_status.available and nvidia_status.temp > 0:
                self._temp_monitor.set_nvidia_temp(nvidia_status.temp)

            # Sıcaklık bildirimlerini kontrol et
            temp_dict = {
                "cpu": temp_reading.cpu_package,
                "gpu_nvidia": temp_reading.gpu_nvidia,
                "nvme": temp_reading.nvme,
                "pch": temp_reading.pch,
            }
            self._notifier.check_and_notify(temp_dict)

            # TERMAL KORUMA — 88°C sert limit (profilden bağımsız)
            thermal_state = self._thermal.check(temp_dict)
            self._dashboard.update_thermal_status(thermal_state)

            # Intel iGPU
            igpu_status = self._igpu.get_status()
            self._dashboard.update_igpu(igpu_status)
            self._gpu_panel.update_igpu_status(igpu_status)

        except Exception as e:
            log.error("Güncelleme hatası: %s", e)

        return True  # GLib.timeout_add devam etsin

    def _on_fan_refresh(self):
        """Fan güncelleme döngüsü (daha yavaş, EC erişimi)."""
        try:
            fan_status = self._fan.get_status()
            self._dashboard.update_fan(fan_status)
            self._fan_panel.update_fan_status(fan_status)
        except Exception as e:
            log.error("Fan güncelleme hatası: %s", e)

        return True

    def _on_destroy(self, widget):
        """Pencere kapatılırken temizlik."""
        log.info("Uygulama kapatılıyor...")

        # Fan'ı otomatik moda geri al
        if self._fan.mode != "auto":
            try:
                self._fan.set_auto_mode()
                log.info("Fan otomatik moda alındı")
            except Exception:
                pass

        # Zamanlayıcıları durdur
        if self._timer_main:
            GLib.source_remove(self._timer_main)
        if self._timer_fan:
            GLib.source_remove(self._timer_fan)

        Gtk.main_quit()
