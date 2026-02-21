"""
Monster HW Controller - CPU Control Panel
CPU governor, EPP, Turbo Boost, frekans aralığı ve performans yüzdesi ayarları.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from src.gui.widgets.freq_slider import FreqSlider


class CpuPanel(Gtk.Box):
    """CPU ayar paneli."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        self._apply_callbacks = []
        self._inhibit_signals = False
        self._user_modified = False  # Kullanıcı değişiklik yaptı mı?

        # === Governor Seçimi ===
        gov_frame = Gtk.Frame(label=" Governor ")
        gov_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        gov_box.set_margin_start(10)
        gov_box.set_margin_end(10)
        gov_box.set_margin_top(6)
        gov_box.set_margin_bottom(8)

        self._gov_powersave = Gtk.RadioButton.new_with_label(None, "Powersave")
        self._gov_performance = Gtk.RadioButton.new_with_label_from_widget(
            self._gov_powersave, "Performance"
        )
        gov_box.pack_start(self._gov_powersave, False, False, 0)
        gov_box.pack_start(self._gov_performance, False, False, 0)

        # Governor açıklama
        self._gov_desc = Gtk.Label()
        self._gov_desc.set_markup(
            '<small><span color="#90a4ae">'
            'Powersave: İşlemci duruma göre frekans ayarlar  |  '
            'Performance: Her zaman yüksek frekans'
            '</span></small>'
        )
        self._gov_desc.set_halign(Gtk.Align.START)
        self._gov_desc.set_line_wrap(True)

        gov_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        gov_vbox.pack_start(gov_box, False, False, 0)
        gov_vbox.pack_start(self._gov_desc, False, False, 0)
        gov_frame.add(gov_vbox)
        self.pack_start(gov_frame, False, False, 0)

        # === EPP (Energy Performance Preference) ===
        epp_frame = Gtk.Frame(label=" Enerji Performans Tercihi (EPP) ")
        epp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        epp_box.set_margin_start(10)
        epp_box.set_margin_end(10)
        epp_box.set_margin_top(6)
        epp_box.set_margin_bottom(8)

        self._epp_combo = Gtk.ComboBoxText()
        epp_options = [
            ("default", "Varsayılan"),
            ("performance", "Performans"),
            ("balance_performance", "Dengeli - Performans"),
            ("balance_power", "Dengeli - Güç Tasarrufu"),
            ("power", "Güç Tasarrufu"),
        ]
        for value, label in epp_options:
            self._epp_combo.append(value, label)
        self._epp_combo.set_active_id("balance_performance")
        epp_box.pack_start(self._epp_combo, False, False, 0)

        epp_desc = Gtk.Label()
        epp_desc.set_markup(
            '<small><span color="#90a4ae">'
            'Intel HWP tarafından kullanılan enerji/performans dengesi tercihi'
            '</span></small>'
        )
        epp_desc.set_halign(Gtk.Align.START)
        epp_desc.set_line_wrap(True)
        epp_box.pack_start(epp_desc, False, False, 0)

        epp_frame.add(epp_box)
        self.pack_start(epp_frame, False, False, 0)

        # === Turbo Boost ===
        turbo_frame = Gtk.Frame(label=" Turbo Boost ")
        turbo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        turbo_box.set_margin_start(10)
        turbo_box.set_margin_end(10)
        turbo_box.set_margin_top(6)
        turbo_box.set_margin_bottom(8)

        self._turbo_switch = Gtk.Switch()
        self._turbo_switch.set_active(True)
        turbo_label = Gtk.Label(label="Turbo Boost (maks. 5.0 GHz)")
        turbo_box.pack_start(turbo_label, False, False, 0)
        turbo_box.pack_end(self._turbo_switch, False, False, 0)

        turbo_frame.add(turbo_box)
        self.pack_start(turbo_frame, False, False, 0)

        # === Frekans Aralığı ===
        freq_frame = Gtk.Frame(label=" CPU Frekans Aralığı ")
        freq_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        freq_box.set_margin_start(10)
        freq_box.set_margin_end(10)
        freq_box.set_margin_top(6)
        freq_box.set_margin_bottom(8)

        self._freq_slider = FreqSlider(
            label="CPU Frekans",
            unit="MHz",
            hw_min=800,
            hw_max=5000,
            step=100,
            color=(0.3, 0.7, 1.0),
        )
        freq_box.pack_start(self._freq_slider, False, False, 0)

        freq_frame.add(freq_box)
        self.pack_start(freq_frame, False, False, 0)

        # === Performans Yüzdesi ===
        perf_frame = Gtk.Frame(label=" intel_pstate Performans Yüzdesi ")
        perf_grid = Gtk.Grid()
        perf_grid.set_column_spacing(10)
        perf_grid.set_row_spacing(6)
        perf_grid.set_margin_start(10)
        perf_grid.set_margin_end(10)
        perf_grid.set_margin_top(6)
        perf_grid.set_margin_bottom(8)

        # Min perf pct
        min_pct_lbl = Gtk.Label(label="Min Perf %:")
        min_pct_lbl.set_halign(Gtk.Align.START)
        perf_grid.attach(min_pct_lbl, 0, 0, 1, 1)

        self._min_perf_adj = Gtk.Adjustment(value=16, lower=1, upper=100,
                                             step_increment=1, page_increment=5)
        self._min_perf_spin = Gtk.SpinButton(adjustment=self._min_perf_adj)
        self._min_perf_spin.set_digits(0)
        perf_grid.attach(self._min_perf_spin, 1, 0, 1, 1)

        # Max perf pct
        max_pct_lbl = Gtk.Label(label="Max Perf %:")
        max_pct_lbl.set_halign(Gtk.Align.START)
        perf_grid.attach(max_pct_lbl, 0, 1, 1, 1)

        self._max_perf_adj = Gtk.Adjustment(value=100, lower=1, upper=100,
                                             step_increment=1, page_increment=5)
        self._max_perf_spin = Gtk.SpinButton(adjustment=self._max_perf_adj)
        self._max_perf_spin.set_digits(0)
        perf_grid.attach(self._max_perf_spin, 1, 1, 1, 1)

        perf_desc = Gtk.Label()
        perf_desc.set_markup(
            '<small><span color="#90a4ae">'
            'intel_pstate sürücüsünün izin verdiği performans aralığı (1-100%)'
            '</span></small>'
        )
        perf_desc.set_halign(Gtk.Align.START)
        perf_desc.set_line_wrap(True)
        perf_grid.attach(perf_desc, 0, 2, 2, 1)

        perf_frame.add(perf_grid)
        self.pack_start(perf_frame, False, False, 0)

        # === Uygula Butonu ===
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        self._apply_btn = Gtk.Button(label="Uygula")
        self._apply_btn.get_style_context().add_class("suggested-action")
        self._apply_btn.set_size_request(120, -1)
        self._apply_btn.connect("clicked", self._on_apply)
        btn_box.pack_end(self._apply_btn, False, False, 0)

        self._status_label = Gtk.Label()
        self._status_label.set_halign(Gtk.Align.START)
        btn_box.pack_start(self._status_label, True, True, 0)

        self.pack_start(btn_box, False, False, 4)

        # Kullanıcı değişikliklerini izle
        self._gov_powersave.connect("toggled", self._on_user_change)
        self._gov_performance.connect("toggled", self._on_user_change)
        self._epp_combo.connect("changed", self._on_user_change)
        self._turbo_switch.connect("notify::active", self._on_user_change)
        self._freq_slider.connect_change(self._on_user_change)
        self._min_perf_adj.connect("value-changed", self._on_user_change_adj)
        self._max_perf_adj.connect("value-changed", self._on_user_change_adj)

    def _on_user_change(self, *args):
        """Kullanıcı bir ayarı değiştirdi."""
        if not self._inhibit_signals:
            self._user_modified = True

    def _on_user_change_adj(self, adj):
        """Adjustment değişikliği (kullanıcı veya programatik)."""
        if not self._inhibit_signals:
            self._user_modified = True

    def on_apply(self, callback):
        """Uygula callback: callback(settings_dict)"""
        self._apply_callbacks.append(callback)

    def _on_apply(self, button):
        """Uygula butonuna tıklandığında."""
        settings = self.get_settings()
        for cb in self._apply_callbacks:
            try:
                success = cb(settings)
                if success:
                    self._user_modified = False  # Değişiklikler uygulandı
                    self._status_label.set_markup(
                        '<span color="#4caf50">✓ Ayarlar uygulandı</span>'
                    )
                else:
                    self._status_label.set_markup(
                        '<span color="#f44336">✗ Hata oluştu (root yetkisi gerekli olabilir)</span>'
                    )
            except Exception as e:
                self._status_label.set_markup(
                    f'<span color="#f44336">✗ Hata: {e}</span>'
                )

        # 3 saniye sonra mesajı temizle
        GLib.timeout_add(3000, lambda: self._status_label.set_text(""))

    def get_settings(self) -> dict:
        """Mevcut panel ayarlarını sözlük olarak döndür."""
        governor = "performance" if self._gov_performance.get_active() else "powersave"
        epp = self._epp_combo.get_active_id() or "balance_performance"
        turbo = self._turbo_switch.get_active()
        min_freq, max_freq = self._freq_slider.get_range()

        return {
            "governor": governor,
            "epp": epp,
            "turbo": turbo,
            "min_freq_khz": min_freq * 1000,  # MHz -> KHz
            "max_freq_khz": max_freq * 1000,
            "min_perf_pct": int(self._min_perf_adj.get_value()),
            "max_perf_pct": int(self._max_perf_adj.get_value()),
        }

    def update_from_status(self, cpu_status):
        """CPU durumunu panele yansıt. Kullanıcı değişiklik yapmışsa atla."""
        if self._user_modified:
            return  # Kullanıcının ayarlarını ezmemek için güncelleme yapma

        self._inhibit_signals = True

        if cpu_status.governor == "performance":
            self._gov_performance.set_active(True)
        else:
            self._gov_powersave.set_active(True)

        if cpu_status.epp:
            self._epp_combo.set_active_id(cpu_status.epp)

        self._turbo_switch.set_active(cpu_status.turbo_enabled)

        # Frekanslar KHz -> MHz 
        min_mhz = cpu_status.min_freq_khz // 1000
        max_mhz = cpu_status.max_freq_khz // 1000
        self._freq_slider.set_range(min_mhz, max_mhz)

        # Mevcut ortalama frekans
        if cpu_status.cur_freqs_khz:
            avg_mhz = sum(cpu_status.cur_freqs_khz) / len(cpu_status.cur_freqs_khz) / 1000
            self._freq_slider.set_current(int(avg_mhz))

        self._min_perf_adj.set_value(cpu_status.min_perf_pct)
        self._max_perf_adj.set_value(cpu_status.max_perf_pct)

        self._inhibit_signals = False
