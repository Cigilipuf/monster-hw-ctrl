"""
Monster HW Controller - System Tray Icon
Sistem tepsisi ikonu: anlık sıcaklık, hızlı profil geçişi, bildirimler.
AppIndicator3 veya StatusIcon fallback kullanır.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    HAS_INDICATOR = True
except (ValueError, ImportError):
    HAS_INDICATOR = False

from src.utils.logger import get_logger

log = get_logger("tray_icon")


class TrayIcon:
    """Sistem tepsisi ikonu."""

    def __init__(self, window):
        self._window = window
        self._indicator = None
        self._status_icon = None
        self._cpu_temp = 0.0
        self._gpu_temp = 0.0
        self._active_profile = "—"
        self._menu = self._build_menu()

        if HAS_INDICATOR:
            self._setup_indicator()
        else:
            self._setup_status_icon()

        log.info("Tray icon başlatıldı (method: %s)",
                 "AppIndicator" if HAS_INDICATOR else "StatusIcon")

    def _setup_indicator(self):
        """AppIndicator3 ile tray icon."""
        self._indicator = AppIndicator3.Indicator.new(
            "monster-hw-ctrl",
            "utilities-system-monitor",
            AppIndicator3.IndicatorCategory.HARDWARE,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._menu)
        self._indicator.set_title("Monster HW Controller")
        self._update_label()

    def _setup_status_icon(self):
        """GTK StatusIcon fallback (GTK3 deprecated ama çalışır)."""
        self._status_icon = Gtk.StatusIcon()
        self._status_icon.set_from_icon_name("utilities-system-monitor")
        self._status_icon.set_tooltip_text("Monster HW Controller")
        self._status_icon.set_visible(True)
        self._status_icon.connect("activate", self._on_activate)
        self._status_icon.connect("popup-menu", self._on_popup)

    def _build_menu(self) -> Gtk.Menu:
        """Tray menüsü oluştur."""
        menu = Gtk.Menu()

        # Durum satırı (tıklanamaz)
        self._temp_item = Gtk.MenuItem(label="CPU: —°C  |  GPU: —°C")
        self._temp_item.set_sensitive(False)
        menu.append(self._temp_item)

        self._profile_item = Gtk.MenuItem(label="Profil: —")
        self._profile_item.set_sensitive(False)
        menu.append(self._profile_item)

        menu.append(Gtk.SeparatorMenuItem())

        # Hızlı profiller
        profiles = [
            ("🔇 Sessiz", "sessiz"),
            ("⚖️ Dengeli", "dengeli"),
            ("🚀 Performans", "performans"),
            ("🎮 Oyun", "oyun"),
            ("🔋 Pil Tasarrufu", "pil_tasarrufu"),
        ]
        for label, name in profiles:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", self._on_profile, name)
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        # Pencereyi göster/gizle
        show_item = Gtk.MenuItem(label="Pencereyi Göster")
        show_item.connect("activate", self._on_show)
        menu.append(show_item)

        # Çıkış
        quit_item = Gtk.MenuItem(label="Çıkış")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def update_temps(self, cpu_temp: float, gpu_temp: float):
        """Sıcaklık bilgilerini güncelle."""
        self._cpu_temp = cpu_temp
        self._gpu_temp = gpu_temp
        self._temp_item.set_label(f"CPU: {cpu_temp:.0f}°C  |  GPU: {gpu_temp:.0f}°C")
        self._update_label()

    def update_profile(self, profile_name: str):
        """Aktif profil bilgisini güncelle."""
        self._active_profile = profile_name
        self._profile_item.set_label(f"Profil: {profile_name}")

    def _update_label(self):
        """AppIndicator etiketini güncelle."""
        if self._indicator:
            label = f"CPU:{self._cpu_temp:.0f}° GPU:{self._gpu_temp:.0f}°"
            self._indicator.set_label(label, "")

    # --- Callbacks ---

    def _on_activate(self, icon):
        """StatusIcon tıklama — pencereyi göster."""
        self._on_show(None)

    def _on_popup(self, icon, button, time):
        """StatusIcon sağ tıklama menüsü."""
        self._menu.popup(None, None, None, None, button, time)

    def _on_show(self, item):
        """Pencereyi göster ve öne getir."""
        self._window.present()
        self._window.show_all()

    def _on_profile(self, item, profile_name):
        """Hızlı profil geçişi."""
        if hasattr(self._window, '_quick_profile'):
            self._window._quick_profile(profile_name)

    def _on_quit(self, item):
        """Uygulamayı kapat."""
        self._window.destroy()
