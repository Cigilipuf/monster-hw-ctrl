"""
Monster HW Controller - GPU Control Panel
NVIDIA RTX 2060 Mobile ve Intel UHD Graphics frekans/güç kontrolü.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from src.gui.widgets.freq_slider import FreqSlider


class GpuPanel(Gtk.Box):
    """GPU ayar paneli (NVIDIA + Intel iGPU)."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        self._nvidia_callbacks = []
        self._igpu_callbacks = []
        self._nv_user_modified = False
        self._igpu_user_modified = False

        # =============================================
        # NVIDIA GPU Bölümü
        # =============================================
        nvidia_header = Gtk.Label()
        nvidia_header.set_markup('<big><b>NVIDIA GeForce RTX 2060 Mobile</b></big>')
        nvidia_header.set_halign(Gtk.Align.START)
        self.pack_start(nvidia_header, False, False, 0)

        # --- NVIDIA Durum Bilgisi ---
        status_frame = Gtk.Frame(label=" Anlık Durum ")
        status_grid = Gtk.Grid()
        status_grid.set_column_spacing(15)
        status_grid.set_row_spacing(3)
        status_grid.set_margin_start(10)
        status_grid.set_margin_end(10)
        status_grid.set_margin_top(4)
        status_grid.set_margin_bottom(6)

        nvidia_info = [
            ("Sıcaklık:", "nv_temp"),
            ("Güç:", "nv_power"),
            ("GPU Saat:", "nv_clock"),
            ("Bellek Saat:", "nv_mem"),
            ("Kullanım:", "nv_util"),
            ("VRAM:", "nv_vram"),
            ("Sürücü:", "nv_driver"),
        ]

        self._nv_values = {}
        for row, (label_text, key) in enumerate(nvidia_info):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            status_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.START)
            value.set_hexpand(True)
            self._nv_values[key] = value
            status_grid.attach(value, 1, row, 1, 1)

        status_frame.add(status_grid)
        self.pack_start(status_frame, False, False, 0)

        # --- NVIDIA Güç Limiti ---
        power_frame = Gtk.Frame(label=" Güç Limiti ")
        power_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        power_box.set_margin_start(10)
        power_box.set_margin_end(10)
        power_box.set_margin_top(6)
        power_box.set_margin_bottom(8)

        power_lbl = Gtk.Label(label="Güç Limiti (Watt):")
        power_box.pack_start(power_lbl, False, False, 0)

        self._power_adj = Gtk.Adjustment(value=90, lower=10, upper=90,
                                          step_increment=5, page_increment=10)
        self._power_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._power_adj
        )
        self._power_scale.set_digits(0)
        self._power_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._power_scale.set_hexpand(True)
        self._power_scale.add_mark(10, Gtk.PositionType.BOTTOM, "10W")
        self._power_scale.add_mark(30, Gtk.PositionType.BOTTOM, "30W")
        self._power_scale.add_mark(60, Gtk.PositionType.BOTTOM, "60W")
        self._power_scale.add_mark(90, Gtk.PositionType.BOTTOM, "90W")
        power_box.pack_start(self._power_scale, True, True, 0)

        self._power_value_lbl = Gtk.Label(label="90 W")
        self._power_value_lbl.set_size_request(50, -1)
        self._power_adj.connect("value-changed",
            lambda adj: self._power_value_lbl.set_text(f"{int(adj.get_value())} W"))
        power_box.pack_start(self._power_value_lbl, False, False, 0)

        power_frame.add(power_box)
        self.pack_start(power_frame, False, False, 0)

        # --- NVIDIA GPU Saat Hızı ---
        nv_clock_frame = Gtk.Frame(label=" GPU Saat Limitleri ")
        nv_clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        nv_clock_box.set_margin_start(10)
        nv_clock_box.set_margin_end(10)
        nv_clock_box.set_margin_top(6)
        nv_clock_box.set_margin_bottom(8)

        self._nv_freq_slider = FreqSlider(
            label="GPU Saat Hızı",
            unit="MHz",
            hw_min=300,
            hw_max=2100,
            step=50,
            color=(0.4, 0.85, 0.3),
        )
        nv_clock_box.pack_start(self._nv_freq_slider, False, False, 0)

        self._nv_mem_slider = FreqSlider(
            label="Bellek Saat Hızı",
            unit="MHz",
            hw_min=405,
            hw_max=5501,
            step=50,
            color=(0.95, 0.7, 0.3),
        )
        nv_clock_box.pack_start(self._nv_mem_slider, False, False, 0)

        # Reset butonu
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._nv_reset_btn = Gtk.Button(label="Saat Limitlerini Sıfırla")
        self._nv_reset_btn.connect("clicked", self._on_nv_reset)
        reset_box.pack_end(self._nv_reset_btn, False, False, 0)
        nv_clock_box.pack_start(reset_box, False, False, 0)

        nv_clock_frame.add(nv_clock_box)
        self.pack_start(nv_clock_frame, False, False, 0)

        # NVIDIA Uygula Butonu
        nv_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._nv_apply_btn = Gtk.Button(label="NVIDIA Ayarlarını Uygula")
        self._nv_apply_btn.get_style_context().add_class("suggested-action")
        self._nv_apply_btn.set_size_request(200, -1)
        self._nv_apply_btn.connect("clicked", self._on_nv_apply)
        nv_btn_box.pack_end(self._nv_apply_btn, False, False, 0)

        self._nv_status = Gtk.Label()
        nv_btn_box.pack_start(self._nv_status, True, True, 0)
        self.pack_start(nv_btn_box, False, False, 0)

        # =============================================
        # Ayırıcı
        # =============================================
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        sep.set_margin_bottom(8)
        self.pack_start(sep, False, False, 0)

        # =============================================
        # Intel iGPU Bölümü
        # =============================================
        igpu_header = Gtk.Label()
        igpu_header.set_markup('<big><b>Intel UHD Graphics (CometLake-H)</b></big>')
        igpu_header.set_halign(Gtk.Align.START)
        self.pack_start(igpu_header, False, False, 0)

        # --- iGPU Durum ---
        igpu_status_frame = Gtk.Frame(label=" Anlık Durum ")
        igpu_grid = Gtk.Grid()
        igpu_grid.set_column_spacing(15)
        igpu_grid.set_row_spacing(3)
        igpu_grid.set_margin_start(10)
        igpu_grid.set_margin_end(10)
        igpu_grid.set_margin_top(4)
        igpu_grid.set_margin_bottom(6)

        igpu_info = [
            ("Aktif Frekans:", "igpu_act"),
            ("Mevcut Aralık:", "igpu_range"),
            ("Boost:", "igpu_boost"),
            ("Donanım Limiti:", "igpu_hw"),
        ]

        self._igpu_values = {}
        for row, (label_text, key) in enumerate(igpu_info):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            igpu_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.START)
            value.set_hexpand(True)
            self._igpu_values[key] = value
            igpu_grid.attach(value, 1, row, 1, 1)

        igpu_status_frame.add(igpu_grid)
        self.pack_start(igpu_status_frame, False, False, 0)

        # --- iGPU Frekans Kontrolü ---
        igpu_freq_frame = Gtk.Frame(label=" Frekans Ayarı ")
        igpu_freq_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        igpu_freq_box.set_margin_start(10)
        igpu_freq_box.set_margin_end(10)
        igpu_freq_box.set_margin_top(6)
        igpu_freq_box.set_margin_bottom(8)

        self._igpu_freq_slider = FreqSlider(
            label="iGPU Frekans",
            unit="MHz",
            hw_min=350,
            hw_max=1150,
            step=50,
            color=(0.3, 0.6, 0.95),
        )
        igpu_freq_box.pack_start(self._igpu_freq_slider, False, False, 0)

        igpu_freq_frame.add(igpu_freq_box)
        self.pack_start(igpu_freq_frame, False, False, 0)

        # iGPU Uygula
        igpu_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._igpu_apply_btn = Gtk.Button(label="iGPU Ayarlarını Uygula")
        self._igpu_apply_btn.get_style_context().add_class("suggested-action")
        self._igpu_apply_btn.set_size_request(200, -1)
        self._igpu_apply_btn.connect("clicked", self._on_igpu_apply)
        igpu_btn_box.pack_end(self._igpu_apply_btn, False, False, 0)

        self._igpu_status = Gtk.Label()
        igpu_btn_box.pack_start(self._igpu_status, True, True, 0)
        self.pack_start(igpu_btn_box, False, False, 0)

        # Kullanıcı değişiklik izleme
        self._power_adj.connect("value-changed", self._on_nv_user_change)
        self._nv_freq_slider.connect_change(self._on_nv_user_change)
        self._nv_mem_slider.connect_change(self._on_nv_user_change)
        self._igpu_freq_slider.connect_change(self._on_igpu_user_change)
        self._inhibit_nv = False
        self._inhibit_igpu = False

    def _on_nv_user_change(self, *args):
        if not self._inhibit_nv:
            self._nv_user_modified = True

    def _on_igpu_user_change(self, *args):
        if not self._inhibit_igpu:
            self._igpu_user_modified = True

    # === Callbacks ===

    def on_nvidia_apply(self, callback):
        """NVIDIA uygula callback: callback(settings_dict) -> bool"""
        self._nvidia_callbacks.append(callback)

    def on_igpu_apply(self, callback):
        """iGPU uygula callback: callback(settings_dict) -> bool"""
        self._igpu_callbacks.append(callback)

    def _on_nv_apply(self, button):
        settings = self.get_nvidia_settings()
        for cb in self._nvidia_callbacks:
            try:
                success = cb(settings)
                if success:
                    self._nv_user_modified = False
                color = "#4caf50" if success else "#f44336"
                msg = "✓ Uygulandı" if success else "✗ Hata (root gerekli olabilir)"
                self._nv_status.set_markup(f'<span color="{color}">{msg}</span>')
            except Exception as e:
                self._nv_status.set_markup(f'<span color="#f44336">✗ {e}</span>')
        GLib.timeout_add(3000, lambda: self._nv_status.set_text(""))

    def _on_igpu_apply(self, button):
        settings = self.get_igpu_settings()
        for cb in self._igpu_callbacks:
            try:
                success = cb(settings)
                if success:
                    self._igpu_user_modified = False
                color = "#4caf50" if success else "#f44336"
                msg = "✓ Uygulandı" if success else "✗ Hata (root gerekli olabilir)"
                self._igpu_status.set_markup(f'<span color="{color}">{msg}</span>')
            except Exception as e:
                self._igpu_status.set_markup(f'<span color="#f44336">✗ {e}</span>')
        GLib.timeout_add(3000, lambda: self._igpu_status.set_text(""))

    def _on_nv_reset(self, button):
        """NVIDIA saat limitlerini sıfırla."""
        for cb in self._nvidia_callbacks:
            try:
                cb({"action": "reset_clocks"})
                self._nv_status.set_markup(
                    '<span color="#4caf50">✓ Saat limitleri sıfırlandı</span>'
                )
            except Exception:
                pass
        GLib.timeout_add(3000, lambda: self._nv_status.set_text(""))

    # === Getter / Setter ===

    def get_nvidia_settings(self) -> dict:
        min_clock, max_clock = self._nv_freq_slider.get_range()
        mem_min, mem_max = self._nv_mem_slider.get_range()
        return {
            "power_limit": int(self._power_adj.get_value()),
            "gpu_clock_min": min_clock,
            "gpu_clock_max": max_clock,
            "mem_clock_min": mem_min,
            "mem_clock_max": mem_max,
        }

    def get_igpu_settings(self) -> dict:
        min_freq, max_freq = self._igpu_freq_slider.get_range()
        return {
            "min_freq_mhz": min_freq,
            "max_freq_mhz": max_freq,
        }

    def update_nvidia_status(self, nvidia_status):
        """NVIDIA bilgilerini panele yansıt."""
        v = self._nv_values

        if not nvidia_status.available:
            for val in v.values():
                val.set_markup('<span color="#f44336">GPU Erişilemiyor</span>')
            self._nv_apply_btn.set_sensitive(False)
            self._nv_reset_btn.set_sensitive(False)
            return

        self._nv_apply_btn.set_sensitive(True)
        self._nv_reset_btn.set_sensitive(True)

        temp = nvidia_status.temp
        temp_color = "#4caf50" if temp < 70 else "#ff9800" if temp < 85 else "#f44336"
        v["nv_temp"].set_markup(f'<span color="{temp_color}">{temp}°C</span>')

        v["nv_power"].set_text(
            f"{nvidia_status.power_draw:.1f}W / {nvidia_status.power_limit:.0f}W"
        )
        v["nv_clock"].set_text(f"{nvidia_status.clock_graphics} MHz")
        v["nv_mem"].set_text(f"{nvidia_status.clock_memory} MHz")
        v["nv_util"].set_text(
            f"GPU: {nvidia_status.utilization_gpu}%  Bellek: {nvidia_status.utilization_memory}%"
        )
        v["nv_vram"].set_text(
            f"{nvidia_status.vram_used} / {nvidia_status.vram_total} MiB"
        )
        v["nv_driver"].set_text(nvidia_status.driver_version)

        # Mevcut frekansı slider'a yansıt (sadece durum göstergeleri)
        self._nv_freq_slider.set_current(nvidia_status.clock_graphics)
        self._nv_mem_slider.set_current(nvidia_status.clock_memory)

        # Kontrol widget'larını güncelle (kullanıcı değiştirmediyse)
        if not self._nv_user_modified:
            self._inhibit_nv = True
            self._power_adj.set_value(nvidia_status.power_limit)
            self._inhibit_nv = False

    def update_igpu_status(self, igpu_status):
        """Intel iGPU bilgilerini panele yansıt."""
        v = self._igpu_values

        if not igpu_status.available:
            for val in v.values():
                val.set_text("N/A")
            self._igpu_apply_btn.set_sensitive(False)
            return

        self._igpu_apply_btn.set_sensitive(True)

        v["igpu_act"].set_text(f"{igpu_status.act_freq_mhz} MHz")
        v["igpu_range"].set_text(
            f"{igpu_status.min_freq_mhz} — {igpu_status.max_freq_mhz} MHz"
        )
        v["igpu_boost"].set_text(f"{igpu_status.boost_freq_mhz} MHz")
        v["igpu_hw"].set_text(
            f"{igpu_status.rpn_freq_mhz} — {igpu_status.rp0_freq_mhz} MHz"
        )

        self._igpu_freq_slider.set_current(igpu_status.act_freq_mhz)

        # Kontrol widget'larını güncelle (kullanıcı değiştirmediyse)
        if not self._igpu_user_modified:
            self._inhibit_igpu = True
            self._igpu_freq_slider.set_range(igpu_status.min_freq_mhz, igpu_status.max_freq_mhz)
            self._inhibit_igpu = False
