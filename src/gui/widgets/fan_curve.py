"""
Monster HW Controller - Fan Curve Editor Widget
Sıcaklık-fan hızı eğrisi editörü. Noktaları sürükleyerek ayarlanabilir.
"""

import math
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
import cairo

from src.core.fan_controller import FanCurvePoint


class FanCurveEditor(Gtk.DrawingArea):
    """İnteraktif fan eğrisi editörü."""

    def __init__(self):
        super().__init__()
        self._points = [
            FanCurvePoint(40, 25),
            FanCurvePoint(50, 35),
            FanCurvePoint(60, 45),
            FanCurvePoint(68, 55),
            FanCurvePoint(75, 75),
            FanCurvePoint(82, 100),
        ]
        self._dragging_idx = -1
        self._current_temp = 0.0  # Anlık CPU sıcaklığı göstergesi
        self._callbacks = []

        # Eksen limitleri (sert limit: 88°C)
        self._temp_min = 20
        self._temp_max = 90
        self._duty_min = 0
        self._duty_max = 100

        # Çizim marjları
        self._margin_left = 45
        self._margin_right = 15
        self._margin_top = 15
        self._margin_bottom = 35

        self.set_size_request(400, 250)
        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )

        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)

    @property
    def points(self):
        return list(self._points)

    @points.setter
    def points(self, value):
        self._points = sorted(value, key=lambda p: p.temp)
        self.queue_draw()

    @property
    def current_temp(self):
        return self._current_temp

    @current_temp.setter
    def current_temp(self, value):
        self._current_temp = value
        self.queue_draw()

    def on_change(self, callback):
        """Eğri değiştiğinde çağrılacak callback ekle."""
        self._callbacks.append(callback)

    def _notify_change(self):
        for cb in self._callbacks:
            try:
                cb(self._points)
            except Exception:
                pass

    def _get_plot_area(self):
        """Çizim alanı boyutlarını döndür."""
        alloc = self.get_allocation()
        x = self._margin_left
        y = self._margin_top
        w = alloc.width - self._margin_left - self._margin_right
        h = alloc.height - self._margin_top - self._margin_bottom
        return x, y, w, h

    def _temp_to_x(self, temp, plot_x, plot_w):
        ratio = (temp - self._temp_min) / (self._temp_max - self._temp_min)
        return plot_x + ratio * plot_w

    def _duty_to_y(self, duty, plot_y, plot_h):
        ratio = (duty - self._duty_min) / (self._duty_max - self._duty_min)
        return plot_y + plot_h - ratio * plot_h

    def _x_to_temp(self, x, plot_x, plot_w):
        ratio = (x - plot_x) / plot_w
        return self._temp_min + ratio * (self._temp_max - self._temp_min)

    def _y_to_duty(self, y, plot_y, plot_h):
        ratio = 1.0 - (y - plot_y) / plot_h
        return self._duty_min + ratio * (self._duty_max - self._duty_min)

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        px, py, pw, ph = self._get_plot_area()

        # Arka plan
        cr.set_source_rgb(0.12, 0.12, 0.15)
        cr.rectangle(0, 0, alloc.width, alloc.height)
        cr.fill()

        # Grid
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.set_line_width(0.5)

        # Yatay grid (duty %)
        for duty in range(0, 101, 20):
            y = self._duty_to_y(duty, py, ph)
            cr.move_to(px, y)
            cr.line_to(px + pw, y)
            cr.stroke()

            cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)
            cr.set_font_size(10)
            cr.move_to(5, y + 4)
            cr.show_text(f"{duty}%")
            cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)

        # Dikey grid (temp °C)
        for temp in range(20, 110, 10):
            x = self._temp_to_x(temp, px, pw)
            cr.move_to(x, py)
            cr.line_to(x, py + ph)
            cr.stroke()

            cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)
            cr.set_font_size(10)
            cr.move_to(x - 8, py + ph + 15)
            cr.show_text(f"{temp}°")
            cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)

        # Fan güvenlik alt sınırı (20%)
        cr.set_source_rgba(1.0, 0.3, 0.3, 0.3)
        safety_y = self._duty_to_y(20, py, ph)
        cr.rectangle(px, safety_y, pw, py + ph - safety_y)
        cr.fill()
        cr.set_source_rgba(1.0, 0.3, 0.3, 0.6)
        cr.set_line_width(1)
        cr.set_dash([4, 4])
        cr.move_to(px, safety_y)
        cr.line_to(px + pw, safety_y)
        cr.stroke()
        cr.set_dash([])

        # Anlık CPU sıcaklığı dikey çizgi
        if self._current_temp > 0:
            temp_x = self._temp_to_x(self._current_temp, px, pw)
            cr.set_source_rgba(0.3, 0.8, 1.0, 0.6)
            cr.set_line_width(1.5)
            cr.set_dash([3, 3])
            cr.move_to(temp_x, py)
            cr.line_to(temp_x, py + ph)
            cr.stroke()
            cr.set_dash([])

            cr.set_source_rgba(0.3, 0.8, 1.0, 0.9)
            cr.set_font_size(10)
            cr.move_to(temp_x + 3, py + 12)
            cr.show_text(f"{self._current_temp:.0f}°C")

        # Eğri çizgisi
        if len(self._points) >= 2:
            cr.set_source_rgb(0.3, 0.85, 0.5)
            cr.set_line_width(2.5)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)

            p0 = self._points[0]
            cr.move_to(
                self._temp_to_x(p0.temp, px, pw),
                self._duty_to_y(p0.duty_pct, py, ph),
            )
            for p in self._points[1:]:
                cr.line_to(
                    self._temp_to_x(p.temp, px, pw),
                    self._duty_to_y(p.duty_pct, py, ph),
                )
            cr.stroke()

        # Noktalar
        for i, p in enumerate(self._points):
            x = self._temp_to_x(p.temp, px, pw)
            y = self._duty_to_y(p.duty_pct, py, ph)

            # Nokta halkası
            cr.set_source_rgb(0.3, 0.85, 0.5)
            cr.arc(x, y, 6, 0, 2 * math.pi)
            cr.fill()

            # İç daire
            if i == self._dragging_idx:
                cr.set_source_rgb(1.0, 1.0, 1.0)
            else:
                cr.set_source_rgb(0.15, 0.15, 0.18)
            cr.arc(x, y, 3.5, 0, 2 * math.pi)
            cr.fill()

            # Değer etiketi
            cr.set_source_rgba(0.9, 0.9, 0.9, 0.9)
            cr.set_font_size(9)
            cr.move_to(x - 15, y - 10)
            cr.show_text(f"{p.temp}°/{p.duty_pct}%")

        # Eksen etiketleri
        cr.set_source_rgba(0.7, 0.7, 0.7, 0.9)
        cr.set_font_size(11)
        cr.move_to(px + pw / 2 - 25, alloc.height - 2)
        cr.show_text("Sıcaklık (°C)")

        cr.save()
        cr.translate(12, py + ph / 2 + 20)
        cr.rotate(-math.pi / 2)
        cr.show_text("Fan Hızı (%)")
        cr.restore()

        return False

    def _find_nearest_point(self, mx, my):
        """Mouse'a en yakın noktayı bul."""
        px, py, pw, ph = self._get_plot_area()
        best_idx = -1
        best_dist = 20  # Minimum yakalama mesafesi (piksel)

        for i, p in enumerate(self._points):
            x = self._temp_to_x(p.temp, px, pw)
            y = self._duty_to_y(p.duty_pct, py, ph)
            dist = math.sqrt((mx - x) ** 2 + (my - y) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return best_idx

    def _on_button_press(self, widget, event):
        if event.button == 1:
            self._dragging_idx = self._find_nearest_point(event.x, event.y)

    def _on_button_release(self, widget, event):
        if self._dragging_idx >= 0:
            self._dragging_idx = -1
            self._points.sort(key=lambda p: p.temp)
            self._notify_change()
            self.queue_draw()

    def _on_motion(self, widget, event):
        if self._dragging_idx < 0:
            return

        px, py, pw, ph = self._get_plot_area()
        temp = self._x_to_temp(event.x, px, pw)
        duty = self._y_to_duty(event.y, py, ph)

        # Limitle (sert limit: 88°C)
        temp = max(self._temp_min, min(88, int(temp)))
        duty = max(20, min(100, int(duty)))  # Min %20 güvenlik

        self._points[self._dragging_idx] = FanCurvePoint(temp, duty)
        self.queue_draw()
