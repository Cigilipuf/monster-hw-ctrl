"""
Monster HW Controller - Temperature Gauge Widget
Cairo ile çizilen dairesel sıcaklık göstergesi.
"""

import math
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo


class TempGauge(Gtk.DrawingArea):
    """Dairesel sıcaklık göstergesi widget'ı."""

    def __init__(self, label: str = "CPU", max_temp: float = 100.0,
                 warning_temp: float = 75.0, critical_temp: float = 84.0,
                 size: int = 120):
        super().__init__()
        self._label = label
        self._temp = 0.0
        self._max_temp = max_temp
        self._warning_temp = warning_temp
        self._critical_temp = critical_temp
        self._size = size

        self.set_size_request(size, size + 30)
        self.connect("draw", self._on_draw)

    @property
    def temp(self) -> float:
        return self._temp

    @temp.setter
    def temp(self, value: float):
        self._temp = value
        self.queue_draw()

    def _get_color(self, temp: float):
        """Sıcaklığa göre renk döndür."""
        if temp >= self._critical_temp:
            return (0.9, 0.1, 0.1)   # Kırmızı
        elif temp >= self._warning_temp:
            return (0.95, 0.6, 0.1)  # Turuncu
        elif temp >= 50:
            return (0.95, 0.85, 0.2) # Sarı
        else:
            return (0.2, 0.8, 0.4)   # Yeşil

    def _on_draw(self, widget, cr):
        """Cairo ile çiz."""
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height
        cx = w / 2
        cy = (h - 25) / 2
        radius = min(cx, cy) - 8

        # Arka plan yayı (gri)
        start_angle = 0.75 * math.pi
        end_angle = 2.25 * math.pi
        cr.set_line_width(10)
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.4)
        cr.arc(cx, cy, radius, start_angle, end_angle)
        cr.stroke()

        # Değer yayı (renkli)
        ratio = min(self._temp / self._max_temp, 1.0) if self._max_temp > 0 else 0
        value_angle = start_angle + ratio * (end_angle - start_angle)
        color = self._get_color(self._temp)
        cr.set_source_rgb(*color)
        cr.set_line_width(10)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        if ratio > 0.01:
            cr.arc(cx, cy, radius, start_angle, value_angle)
            cr.stroke()

        # Sıcaklık değeri (merkez)
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(radius * 0.45)
        text = f"{self._temp:.0f}°C"
        extents = cr.text_extents(text)
        cr.move_to(cx - extents.width / 2, cy + extents.height / 3)
        cr.show_text(text)

        # Etiket (alt)
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.set_font_size(11)
        extents = cr.text_extents(self._label)
        cr.move_to(cx - extents.width / 2, h - 8)
        cr.show_text(self._label)

        return False
