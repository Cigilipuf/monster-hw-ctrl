"""
Monster HW Controller - Frequency Slider Widget
CPU/GPU frekans ayar kaydırıcısı. Mevcut, minimum ve maksimum değerleri gösterir.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo


class FreqSlider(Gtk.Box):
    """Frekans kaydırıcısı: bir etiket, mevcut değer, ve min-max aralık ayarı."""

    def __init__(self, label="Frekans", unit="MHz", hw_min=0, hw_max=5000,
                 step=100, show_current=True, color=(0.3, 0.7, 1.0)):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self._label_text = label
        self._unit = unit
        self._hw_min = hw_min
        self._hw_max = hw_max
        self._step = step
        self._show_current = show_current
        self._color = color
        self._current_value = 0
        self._callbacks = []

        # Başlık satırı
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=label)
        lbl.set_markup(f"<b>{label}</b>")
        lbl.set_halign(Gtk.Align.START)
        header.pack_start(lbl, False, False, 0)

        self._current_label = Gtk.Label()
        self._current_label.set_halign(Gtk.Align.END)
        header.pack_end(self._current_label, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Min slider
        min_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        min_lbl = Gtk.Label(label="Min:")
        min_lbl.set_size_request(35, -1)
        min_lbl.set_halign(Gtk.Align.START)
        min_box.pack_start(min_lbl, False, False, 0)

        self._min_adj = Gtk.Adjustment(
            value=hw_min, lower=hw_min, upper=hw_max,
            step_increment=step, page_increment=step * 5
        )
        self._min_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._min_adj
        )
        self._min_scale.set_digits(0)
        self._min_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._min_scale.set_hexpand(True)
        self._min_scale.connect("value-changed", self._on_min_changed)
        min_box.pack_start(self._min_scale, True, True, 0)

        self._min_value_label = Gtk.Label()
        self._min_value_label.set_size_request(75, -1)
        min_box.pack_start(self._min_value_label, False, False, 0)

        self.pack_start(min_box, False, False, 0)

        # Max slider
        max_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        max_lbl = Gtk.Label(label="Max:")
        max_lbl.set_size_request(35, -1)
        max_lbl.set_halign(Gtk.Align.START)
        max_box.pack_start(max_lbl, False, False, 0)

        self._max_adj = Gtk.Adjustment(
            value=hw_max, lower=hw_min, upper=hw_max,
            step_increment=step, page_increment=step * 5
        )
        self._max_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._max_adj
        )
        self._max_scale.set_digits(0)
        self._max_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._max_scale.set_hexpand(True)
        self._max_scale.connect("value-changed", self._on_max_changed)
        max_box.pack_start(self._max_scale, True, True, 0)

        self._max_value_label = Gtk.Label()
        self._max_value_label.set_size_request(75, -1)
        max_box.pack_start(self._max_value_label, False, False, 0)

        self.pack_start(max_box, False, False, 0)

        # Başlangıç etiketlerini güncelle
        self._update_labels()

        # CSS
        css = Gtk.CssProvider()
        r, g, b = self._color
        css_data = f"""
        scale trough {{
            background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.2);
            min-height: 6px;
        }}
        scale trough highlight {{
            background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.7);
        }}
        scale slider {{
            background-color: rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.9);
            min-width: 14px;
            min-height: 14px;
            border-radius: 7px;
        }}
        """
        css.load_from_data(css_data.encode())
        for scale in (self._min_scale, self._max_scale):
            scale.get_style_context().add_provider(
                css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def on_change(self, callback):
        """Değer değiştiğinde callback: callback(min_val, max_val)"""
        self._callbacks.append(callback)

    def _notify_change(self):
        min_val = int(self._min_adj.get_value())
        max_val = int(self._max_adj.get_value())
        for cb in self._callbacks:
            try:
                cb(min_val, max_val)
            except Exception:
                pass

    def _on_min_changed(self, scale):
        min_val = int(self._min_adj.get_value())
        max_val = int(self._max_adj.get_value())
        # Min, max'ı geçemez
        if min_val > max_val:
            self._min_adj.set_value(max_val)
        self._update_labels()
        self._notify_change()

    def _on_max_changed(self, scale):
        min_val = int(self._min_adj.get_value())
        max_val = int(self._max_adj.get_value())
        # Max, min'den düşük olamaz
        if max_val < min_val:
            self._max_adj.set_value(min_val)
        self._update_labels()
        self._notify_change()

    def _update_labels(self):
        min_val = int(self._min_adj.get_value())
        max_val = int(self._max_adj.get_value())

        self._min_value_label.set_text(f"{min_val} {self._unit}")
        self._max_value_label.set_text(f"{max_val} {self._unit}")

        if self._show_current:
            self._current_label.set_markup(
                f"<span color='#80c0ff'>Mevcut: {self._current_value} {self._unit}</span>"
            )
        else:
            self._current_label.set_text("")

    def set_current(self, value):
        """Mevcut (okunan) değeri güncelle."""
        self._current_value = value
        self._update_labels()

    def set_range(self, min_val, max_val):
        """Min ve max kaydırıcı değerlerini ayarla."""
        self._min_adj.set_value(min_val)
        self._max_adj.set_value(max_val)
        self._update_labels()

    def get_range(self):
        """Mevcut min ve max değerlerini döndür."""
        return int(self._min_adj.get_value()), int(self._max_adj.get_value())

    @property
    def min_value(self):
        return int(self._min_adj.get_value())

    @property
    def max_value(self):
        return int(self._max_adj.get_value())

    def set_sensitive_all(self, sensitive):
        """Tüm kaydırıcıları aktif/pasif yap."""
        self._min_scale.set_sensitive(sensitive)
        self._max_scale.set_sensitive(sensitive)

    def connect_change(self, callback):
        """Slider değiştiğinde genel callback (kullanıcı değişiklik tespiti için)."""
        self._min_adj.connect("value-changed", lambda adj: callback())
        self._max_adj.connect("value-changed", lambda adj: callback())
