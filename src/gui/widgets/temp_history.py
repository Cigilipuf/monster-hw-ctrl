"""
Monster HW Controller - Temperature History Chart
Son N dakikanın sıcaklık geçmişini çizen Cairo widget'ı.
"""

import time
from collections import deque
from typing import Dict, List, Tuple

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import cairo


# Renk paleti (Catppuccin Mocha)
CHART_COLORS = {
    "CPU": (0.537, 0.706, 0.980),    # Blue (#89b4fa)
    "GPU": (0.627, 0.839, 0.294),    # Green (#a6e3a1)
    "PCH": (0.980, 0.702, 0.529),    # Peach (#fab387)
    "NVMe": (0.580, 0.647, 0.878),   # Lavender (#9399b2)
    "WiFi": (0.953, 0.545, 0.659),   # Pink (#f38ba8)
}

CHART_BG = (0.118, 0.118, 0.180)        # Surface0 (#1e1e2e)
CHART_GRID = (0.271, 0.278, 0.353, 0.5)  # Overlay0 (#45475a)
CHART_TEXT = (0.804, 0.839, 0.957)       # Text (#cdd6f4)


class TempHistoryChart(Gtk.DrawingArea):
    """Sıcaklık geçmişi grafiği (Cairo)."""

    def __init__(self, max_points: int = 180, height: int = 180):
        """
        max_points: Saklanacak maksimum veri noktası (ör. 180 = 1.5s aralıkla ~4.5 dakika)
        """
        super().__init__()
        self.set_size_request(-1, height)
        self._max_points = max_points
        self._series: Dict[str, deque] = {}
        self._visible: Dict[str, bool] = {}
        self._temp_min = 20.0
        self._temp_max = 100.0

        # Başlangıç serileri
        for name in CHART_COLORS:
            self._series[name] = deque(maxlen=max_points)
            self._visible[name] = True

        self.connect("draw", self._on_draw)

    def add_data(self, temps: Dict[str, float]):
        """Yeni sıcaklık verisi ekle. temps: {"CPU": 65.0, "GPU": 42.0, ...}"""
        for name, temp in temps.items():
            if name not in self._series:
                self._series[name] = deque(maxlen=self._max_points)
                self._visible[name] = True
            self._series[name].append(temp)
        self.queue_draw()

    def set_visible(self, name: str, visible: bool):
        """Bir serinin görünürlüğünü ayarla."""
        self._visible[name] = visible
        self.queue_draw()

    def _on_draw(self, widget, cr: cairo.Context):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Kenar boşlukları
        margin_left = 45
        margin_right = 15
        margin_top = 10
        margin_bottom = 25
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        if chart_w <= 0 or chart_h <= 0:
            return

        # Arka plan
        cr.set_source_rgb(*CHART_BG)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Sıcaklık aralığını dinamik belirle
        all_temps = []
        for name, data in self._series.items():
            if self._visible.get(name, True) and data:
                all_temps.extend(data)

        if all_temps:
            self._temp_min = max(15, min(all_temps) - 5)
            self._temp_max = max(self._temp_min + 20, max(all_temps) + 5)
        else:
            self._temp_min, self._temp_max = 20, 100

        temp_range = self._temp_max - self._temp_min

        # Izgara çizgileri
        cr.set_source_rgba(*CHART_GRID)
        cr.set_line_width(0.5)

        # Yatay (sıcaklık) çizgileri
        num_h_lines = 5
        for i in range(num_h_lines + 1):
            temp = self._temp_min + (temp_range * i / num_h_lines)
            y = margin_top + chart_h - (chart_h * i / num_h_lines)

            cr.move_to(margin_left, y)
            cr.line_to(w - margin_right, y)
            cr.stroke()

            # Etiket
            cr.set_source_rgba(*CHART_TEXT, 0.7)
            cr.set_font_size(10)
            cr.move_to(5, y + 4)
            cr.show_text(f"{temp:.0f}°C")
            cr.set_source_rgba(*CHART_GRID)

        # Dikey çizgiler (zaman)
        num_v_lines = 6
        for i in range(num_v_lines + 1):
            x = margin_left + (chart_w * i / num_v_lines)
            cr.move_to(x, margin_top)
            cr.line_to(x, h - margin_bottom)
            cr.stroke()

        # Veri serilerini çiz
        for name, data in self._series.items():
            if not self._visible.get(name, True) or len(data) < 2:
                continue

            color = CHART_COLORS.get(name, (0.8, 0.8, 0.8))
            cr.set_source_rgba(*color, 0.9)
            cr.set_line_width(1.5)

            points = list(data)
            n = len(points)

            for i, temp in enumerate(points):
                x = margin_left + (chart_w * i / (self._max_points - 1))
                y = margin_top + chart_h * (1.0 - (temp - self._temp_min) / temp_range)
                y = max(margin_top, min(margin_top + chart_h, y))

                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)

            cr.stroke()

        # Lejant
        legend_x = margin_left + 5
        legend_y = margin_top + 5
        cr.set_font_size(10)

        for name, color in CHART_COLORS.items():
            if not self._visible.get(name, True):
                continue
            data = self._series.get(name, deque())
            last_val = data[-1] if data else 0

            cr.set_source_rgba(*color, 1.0)
            cr.rectangle(legend_x, legend_y, 8, 8)
            cr.fill()

            cr.set_source_rgba(*CHART_TEXT, 0.9)
            cr.move_to(legend_x + 12, legend_y + 8)
            cr.show_text(f"{name}: {last_val:.0f}°C")

            legend_x += 90
