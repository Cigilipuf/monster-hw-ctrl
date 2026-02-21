"""
Monster HW Controller - Fan Control Panel  
EC tabanlı fan modu, hız ayarı ve fan eğrisi editörü.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from src.gui.widgets.fan_curve import FanCurveEditor
from src.core.fan_controller import FanCurvePoint


class FanPanel(Gtk.Box):
    """Fan kontrol paneli."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        self._apply_callbacks = []

        # === EC Dürum ===
        ec_frame = Gtk.Frame(label=" EC (Embedded Controller) Durumu ")
        ec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ec_box.set_margin_start(10)
        ec_box.set_margin_end(10)
        ec_box.set_margin_top(6)
        ec_box.set_margin_bottom(8)

        ec_grid = Gtk.Grid()
        ec_grid.set_column_spacing(15)
        ec_grid.set_row_spacing(3)

        ec_info = [
            ("EC Erişim:", "ec_access"),
            ("Yöntem:", "ec_method"),
        ]

        self._ec_values = {}
        for row, (lbl, key) in enumerate(ec_info):
            label = Gtk.Label(label=lbl)
            label.set_halign(Gtk.Align.START)
            ec_grid.attach(label, 0, row, 1, 1)
            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.START)
            self._ec_values[key] = value
            ec_grid.attach(value, 1, row, 1, 1)

        ec_box.pack_start(ec_grid, False, False, 0)

        ec_warn = Gtk.Label()
        ec_warn.set_markup(
            '<small><span color="#ff9800">'
            '⚠ EC fan kontrolü donanıma zarar verebilir. '
            'Register adresleri doğrulanana kadar dikkatli olun.'
            '</span></small>'
        )
        ec_warn.set_line_wrap(True)
        ec_warn.set_halign(Gtk.Align.START)
        ec_box.pack_start(ec_warn, False, False, 4)

        ec_frame.add(ec_box)
        self.pack_start(ec_frame, False, False, 0)

        # === Fan Durumu ===
        fan_status_frame = Gtk.Frame(label=" Fan Hızları ")
        fan_grid = Gtk.Grid()
        fan_grid.set_column_spacing(20)
        fan_grid.set_row_spacing(4)
        fan_grid.set_margin_start(10)
        fan_grid.set_margin_end(10)
        fan_grid.set_margin_top(6)
        fan_grid.set_margin_bottom(8)

        fan_info = [
            ("CPU Fan RPM:", "cpu_rpm"),
            ("GPU Fan RPM:", "gpu_rpm"),
            ("CPU Duty:", "cpu_duty"),
            ("GPU Duty:", "gpu_duty"),
        ]

        self._fan_values = {}
        for row, (lbl, key) in enumerate(fan_info):
            label = Gtk.Label(label=lbl)
            label.set_halign(Gtk.Align.START)
            fan_grid.attach(label, 0, row, 1, 1)
            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.START)
            value.set_hexpand(True)
            self._fan_values[key] = value
            fan_grid.attach(value, 1, row, 1, 1)

        fan_status_frame.add(fan_grid)
        self.pack_start(fan_status_frame, False, False, 0)

        # === Fan Mod Seçimi ===
        mode_frame = Gtk.Frame(label=" Fan Modu ")
        mode_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mode_box.set_margin_start(10)
        mode_box.set_margin_end(10)
        mode_box.set_margin_top(6)
        mode_box.set_margin_bottom(8)

        # Radio butonlar
        radio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)

        self._mode_auto = Gtk.RadioButton.new_with_label(None, "Otomatik (EC)")
        self._mode_manual = Gtk.RadioButton.new_with_label_from_widget(
            self._mode_auto, "Manuel"
        )
        self._mode_curve = Gtk.RadioButton.new_with_label_from_widget(
            self._mode_auto, "Fan Eğrisi"
        )
        self._mode_auto.set_active(True)

        radio_box.pack_start(self._mode_auto, False, False, 0)
        radio_box.pack_start(self._mode_manual, False, False, 0)
        radio_box.pack_start(self._mode_curve, False, False, 0)
        mode_box.pack_start(radio_box, False, False, 0)

        # Mod açıklamaları
        mode_desc = Gtk.Label()
        mode_desc.set_markup(
            '<small><span color="#90a4ae">'
            'Otomatik: EC kendi algoritmasıyla kontrol eder  |  '
            'Manuel: Sabit hız ayarı  |  '
            'Eğri: Sıcaklığa göre otomatik fan hızı'
            '</span></small>'
        )
        mode_desc.set_halign(Gtk.Align.START)
        mode_desc.set_line_wrap(True)
        mode_box.pack_start(mode_desc, False, False, 0)

        mode_frame.add(mode_box)
        self.pack_start(mode_frame, False, False, 0)

        # === Manuel Mod Kontrolleri ===
        self._manual_frame = Gtk.Frame(label=" Manuel Fan Hızı ")
        manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        manual_box.set_margin_start(10)
        manual_box.set_margin_end(10)
        manual_box.set_margin_top(6)
        manual_box.set_margin_bottom(8)

        # CPU Fan
        cpu_fan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cpu_fan_lbl = Gtk.Label(label="CPU Fan (%):")
        cpu_fan_lbl.set_size_request(90, -1)
        cpu_fan_box.pack_start(cpu_fan_lbl, False, False, 0)

        self._cpu_fan_adj = Gtk.Adjustment(value=50, lower=20, upper=100,
                                            step_increment=5, page_increment=10)
        self._cpu_fan_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._cpu_fan_adj
        )
        self._cpu_fan_scale.set_digits(0)
        self._cpu_fan_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._cpu_fan_scale.set_hexpand(True)
        self._cpu_fan_scale.add_mark(20, Gtk.PositionType.BOTTOM, "20%")
        self._cpu_fan_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self._cpu_fan_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        cpu_fan_box.pack_start(self._cpu_fan_scale, True, True, 0)
        manual_box.pack_start(cpu_fan_box, False, False, 0)

        # GPU Fan
        gpu_fan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        gpu_fan_lbl = Gtk.Label(label="GPU Fan (%):")
        gpu_fan_lbl.set_size_request(90, -1)
        gpu_fan_box.pack_start(gpu_fan_lbl, False, False, 0)

        self._gpu_fan_adj = Gtk.Adjustment(value=50, lower=20, upper=100,
                                            step_increment=5, page_increment=10)
        self._gpu_fan_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._gpu_fan_adj
        )
        self._gpu_fan_scale.set_digits(0)
        self._gpu_fan_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._gpu_fan_scale.set_hexpand(True)
        self._gpu_fan_scale.add_mark(20, Gtk.PositionType.BOTTOM, "20%")
        self._gpu_fan_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self._gpu_fan_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        gpu_fan_box.pack_start(self._gpu_fan_scale, True, True, 0)
        manual_box.pack_start(gpu_fan_box, False, False, 0)

        # Link CPU/GPU
        link_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._link_fans = Gtk.CheckButton(label="CPU ve GPU fanlarını birlikte kontrol et")
        self._link_fans.set_active(True)
        self._link_fans.connect("toggled", self._on_link_toggled)
        link_box.pack_start(self._link_fans, False, False, 0)
        manual_box.pack_start(link_box, False, False, 0)

        self._manual_frame.add(manual_box)
        self.pack_start(self._manual_frame, False, False, 0)

        # === Fan Eğrisi Editörü ===
        self._curve_frame = Gtk.Frame(label=" Fan Eğrisi ")
        curve_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        curve_box.set_margin_start(10)
        curve_box.set_margin_end(10)
        curve_box.set_margin_top(6)
        curve_box.set_margin_bottom(8)

        self._curve_editor = FanCurveEditor()
        curve_box.pack_start(self._curve_editor, True, True, 0)

        # Eğri butonları
        curve_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._add_point_btn = Gtk.Button(label="Nokta Ekle")
        self._add_point_btn.connect("clicked", self._on_add_point)
        curve_btn_box.pack_start(self._add_point_btn, False, False, 0)

        self._remove_point_btn = Gtk.Button(label="Son Noktayı Sil")
        self._remove_point_btn.connect("clicked", self._on_remove_point)
        curve_btn_box.pack_start(self._remove_point_btn, False, False, 0)

        self._reset_curve_btn = Gtk.Button(label="Varsayılana Dön")
        self._reset_curve_btn.connect("clicked", self._on_reset_curve)
        curve_btn_box.pack_start(self._reset_curve_btn, False, False, 0)

        curve_box.pack_start(curve_btn_box, False, False, 0)

        self._curve_frame.add(curve_box)
        self.pack_start(self._curve_frame, False, False, 0)

        # === Uygula ===
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        self._apply_btn = Gtk.Button(label="Fan Ayarlarını Uygula")
        self._apply_btn.get_style_context().add_class("suggested-action")
        self._apply_btn.set_size_request(200, -1)
        self._apply_btn.connect("clicked", self._on_apply)
        btn_box.pack_end(self._apply_btn, False, False, 0)

        self._status_label = Gtk.Label()
        btn_box.pack_start(self._status_label, True, True, 0)
        self.pack_start(btn_box, False, False, 4)

        # Mod değişikliğinde panel görünürlüğünü güncelle
        self._mode_auto.connect("toggled", self._on_mode_changed)
        self._mode_manual.connect("toggled", self._on_mode_changed)
        self._mode_curve.connect("toggled", self._on_mode_changed)
        self._on_mode_changed(None)

        # Link toggled -> CPU slider'ı GPU'ya eşitle
        self._cpu_fan_adj.connect("value-changed", self._on_cpu_fan_changed)

    def _on_mode_changed(self, widget):
        """Mod değiştiğinde ilgili panelleri göster/gizle."""
        is_manual = self._mode_manual.get_active()
        is_curve = self._mode_curve.get_active()

        self._manual_frame.set_visible(is_manual)
        self._curve_frame.set_visible(is_curve)

    def _on_link_toggled(self, check):
        """Fan bağlantısı değiştiğinde GPU slider'ı aktif/pasif yap."""
        linked = check.get_active()
        self._gpu_fan_scale.set_sensitive(not linked)
        if linked:
            self._gpu_fan_adj.set_value(self._cpu_fan_adj.get_value())

    def _on_cpu_fan_changed(self, adj):
        """CPU fan değiştiğinde, bağlıysa GPU'yu da ayarla."""
        if self._link_fans.get_active():
            self._gpu_fan_adj.set_value(adj.get_value())

    def _on_add_point(self, button):
        """Fan eğrisine yeni nokta ekle."""
        points = self._curve_editor.points
        if len(points) >= 10:
            return  # Maksimum nokta
        # Son noktanın 5°C sonrasına yeni nokta ekle (88°C sert limit)
        if points:
            last = points[-1]
            new_temp = min(last.temp + 5, 88)
            new_duty = min(last.duty_pct + 10, 100)
        else:
            new_temp = 50
            new_duty = 40
        points.append(FanCurvePoint(new_temp, max(20, new_duty)))
        self._curve_editor.points = points

    def _on_remove_point(self, button):
        """Son fan eğrisi noktasını sil."""
        points = self._curve_editor.points
        if len(points) > 2:  # En az 2 nokta kalsın
            points.pop()
            self._curve_editor.points = points

    def _on_reset_curve(self, button):
        """Varsayılan fan eğrisine dön."""
        from src.core.fan_controller import DEFAULT_FAN_CURVE
        self._curve_editor.points = list(DEFAULT_FAN_CURVE)

    def on_apply(self, callback):
        """Uygula callback: callback(settings_dict) -> bool"""
        self._apply_callbacks.append(callback)

    def _on_apply(self, button):
        settings = self.get_settings()
        for cb in self._apply_callbacks:
            try:
                success = cb(settings)
                if success:
                    self._status_label.set_markup(
                        '<span color="#4caf50">✓ Fan ayarları uygulandı</span>'
                    )
                else:
                    self._status_label.set_markup(
                        '<span color="#f44336">✗ Hata (EC erişimi gerekli)</span>'
                    )
            except Exception as e:
                self._status_label.set_markup(
                    f'<span color="#f44336">✗ {e}</span>'
                )
        GLib.timeout_add(3000, lambda: self._status_label.set_text(""))

    def get_settings(self) -> dict:
        """Mevcut panel ayarlarını döndür."""
        if self._mode_auto.get_active():
            mode = "auto"
        elif self._mode_manual.get_active():
            mode = "manual"
        else:
            mode = "curve"

        settings = {"mode": mode}

        if mode == "manual":
            settings["cpu_duty_pct"] = int(self._cpu_fan_adj.get_value())
            settings["gpu_duty_pct"] = int(self._gpu_fan_adj.get_value())
        elif mode == "curve":
            settings["curve"] = [
                {"temp": p.temp, "duty_pct": p.duty_pct}
                for p in self._curve_editor.points
            ]

        return settings

    def update_fan_status(self, fan_status):
        """Fan durumunu panele yansıt."""
        ec = self._ec_values
        fv = self._fan_values

        if fan_status.ec_available:
            ec["ec_access"].set_markup('<span color="#4caf50">✓ Bağlantı var</span>')
            ec["ec_method"].set_text(fan_status.ec_method)
            self._apply_btn.set_sensitive(True)
        else:
            ec["ec_access"].set_markup('<span color="#f44336">✗ Erişilemiyor</span>')
            ec["ec_method"].set_text("—")
            self._apply_btn.set_sensitive(False)
            for val in fv.values():
                val.set_text("—")
            return

        fv["cpu_rpm"].set_text(f"{fan_status.cpu_fan_rpm} RPM")
        fv["gpu_rpm"].set_text(f"{fan_status.gpu_fan_rpm} RPM")
        fv["cpu_duty"].set_text(f"{fan_status.cpu_fan_duty_pct}%")
        fv["gpu_duty"].set_text(f"{fan_status.gpu_fan_duty_pct}%")

    def set_current_temp(self, temp):
        """Anlık CPU sıcaklığını fan eğrisi editörüne ilet."""
        self._curve_editor.current_temp = temp
