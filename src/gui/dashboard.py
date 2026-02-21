"""
Monster HW Controller - Dashboard Panel
Anlık izleme paneli: sıcaklıklar, frekanslar, fan hızları, güç tüketimi.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from src.gui.widgets.temp_gauge import TempGauge
from src.gui.widgets.temp_history import TempHistoryChart


class DashboardPanel(Gtk.Box):
    """Ana izleme dashboard'u."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        # --- Sıcaklık Göstergeleri ---
        temp_frame = Gtk.Frame(label=" Sıcaklıklar ")
        temp_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        temp_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        temp_box.set_margin_start(8)
        temp_box.set_margin_end(8)
        temp_box.set_margin_top(6)
        temp_box.set_margin_bottom(6)
        temp_box.set_halign(Gtk.Align.CENTER)

        self.gauge_cpu = TempGauge("CPU Package", size=110,
                                    warning_temp=75, critical_temp=84)
        self.gauge_gpu = TempGauge("NVIDIA GPU", size=110,
                                    warning_temp=75, critical_temp=84)
        self.gauge_pch = TempGauge("PCH", size=90,
                                    warning_temp=72, critical_temp=82)
        self.gauge_nvme = TempGauge("NVMe", size=90,
                                     warning_temp=60, critical_temp=72)
        self.gauge_wifi = TempGauge("WiFi", size=90,
                                     warning_temp=55, critical_temp=70)

        for gauge in (self.gauge_cpu, self.gauge_gpu, self.gauge_pch,
                      self.gauge_nvme, self.gauge_wifi):
            temp_box.pack_start(gauge, False, False, 4)

        temp_frame.add(temp_box)
        self.pack_start(temp_frame, False, False, 0)

        # --- Sıcaklık Geçmişi Grafiği ---
        history_frame = Gtk.Frame(label=" Sıcaklık Geçmişi ")
        self._temp_chart = TempHistoryChart(max_points=180, height=160)
        self._temp_chart.set_margin_start(4)
        self._temp_chart.set_margin_end(4)
        self._temp_chart.set_margin_top(2)
        self._temp_chart.set_margin_bottom(4)
        history_frame.add(self._temp_chart)
        self.pack_start(history_frame, False, False, 0)

        # --- CPU/GPU Bilgileri Grid ---
        info_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        info_hbox.set_homogeneous(True)

        # CPU Bilgileri
        cpu_frame = Gtk.Frame(label=" CPU ")
        cpu_grid = Gtk.Grid()
        cpu_grid.set_column_spacing(12)
        cpu_grid.set_row_spacing(4)
        cpu_grid.set_margin_start(8)
        cpu_grid.set_margin_end(8)
        cpu_grid.set_margin_top(4)
        cpu_grid.set_margin_bottom(6)

        cpu_labels = [
            ("Governor:", "cpu_governor"),
            ("EPP:", "cpu_epp"),
            ("Turbo Boost:", "cpu_turbo"),
            ("Frekans Aralığı:", "cpu_freq_range"),
            ("Ortalama Frekans:", "cpu_avg_freq"),
            ("Perf. Yüzdesi:", "cpu_perf_pct"),
        ]

        self._cpu_values = {}
        for row, (label_text, key) in enumerate(cpu_labels):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            cpu_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.END)
            value.set_hexpand(True)
            value.set_selectable(True)
            self._cpu_values[key] = value
            cpu_grid.attach(value, 1, row, 1, 1)

        cpu_frame.add(cpu_grid)
        info_hbox.pack_start(cpu_frame, True, True, 0)

        # NVIDIA GPU Bilgileri
        gpu_frame = Gtk.Frame(label=" NVIDIA GPU ")
        gpu_grid = Gtk.Grid()
        gpu_grid.set_column_spacing(12)
        gpu_grid.set_row_spacing(4)
        gpu_grid.set_margin_start(8)
        gpu_grid.set_margin_end(8)
        gpu_grid.set_margin_top(4)
        gpu_grid.set_margin_bottom(6)

        gpu_labels = [
            ("GPU Saat:", "gpu_clock"),
            ("Bellek Saat:", "gpu_mem_clock"),
            ("Güç:", "gpu_power"),
            ("Kullanım:", "gpu_util"),
            ("VRAM:", "gpu_vram"),
            ("Grafik Modu:", "gpu_mode"),
        ]

        self._gpu_values = {}
        for row, (label_text, key) in enumerate(gpu_labels):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            gpu_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.END)
            value.set_hexpand(True)
            value.set_selectable(True)
            self._gpu_values[key] = value
            gpu_grid.attach(value, 1, row, 1, 1)

        gpu_frame.add(gpu_grid)
        info_hbox.pack_start(gpu_frame, True, True, 0)

        self.pack_start(info_hbox, False, False, 0)

        # --- Fan ve iGPU bilgileri ---
        lower_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lower_hbox.set_homogeneous(True)

        # Fan Bilgileri
        fan_frame = Gtk.Frame(label=" Fan Durumu ")
        fan_grid = Gtk.Grid()
        fan_grid.set_column_spacing(12)
        fan_grid.set_row_spacing(4)
        fan_grid.set_margin_start(8)
        fan_grid.set_margin_end(8)
        fan_grid.set_margin_top(4)
        fan_grid.set_margin_bottom(6)

        fan_labels = [
            ("Mod:", "fan_mode"),
            ("CPU Fan:", "fan_cpu_rpm"),
            ("GPU Fan:", "fan_gpu_rpm"),
            ("CPU Duty:", "fan_cpu_duty"),
            ("GPU Duty:", "fan_gpu_duty"),
        ]

        self._fan_values = {}
        for row, (label_text, key) in enumerate(fan_labels):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            fan_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.END)
            value.set_hexpand(True)
            value.set_selectable(True)
            self._fan_values[key] = value
            fan_grid.attach(value, 1, row, 1, 1)

        fan_frame.add(fan_grid)
        lower_hbox.pack_start(fan_frame, True, True, 0)

        # Intel iGPU Bilgileri
        igpu_frame = Gtk.Frame(label=" Intel iGPU ")
        igpu_grid = Gtk.Grid()
        igpu_grid.set_column_spacing(12)
        igpu_grid.set_row_spacing(4)
        igpu_grid.set_margin_start(8)
        igpu_grid.set_margin_end(8)
        igpu_grid.set_margin_top(4)
        igpu_grid.set_margin_bottom(6)

        igpu_labels = [
            ("Aktif Frekans:", "igpu_act"),
            ("Frekans Aralığı:", "igpu_range"),
            ("Boost:", "igpu_boost"),
            ("HW Limit:", "igpu_hw_limit"),
        ]

        self._igpu_values = {}
        for row, (label_text, key) in enumerate(igpu_labels):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.get_style_context().add_class("dim-label")
            igpu_grid.attach(label, 0, row, 1, 1)

            value = Gtk.Label(label="—")
            value.set_halign(Gtk.Align.END)
            value.set_hexpand(True)
            value.set_selectable(True)
            self._igpu_values[key] = value
            igpu_grid.attach(value, 1, row, 1, 1)

        igpu_frame.add(igpu_grid)
        lower_hbox.pack_start(igpu_frame, True, True, 0)

        self.pack_start(lower_hbox, False, False, 0)

        # --- CPU Çekirdek Frekansları & Sıcaklıkları ---
        cores_frame = Gtk.Frame(label=" CPU Çekirdek Frekansları & Sıcaklıkları ")
        self._cores_box = Gtk.FlowBox()
        self._cores_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._cores_box.set_min_children_per_line(4)
        self._cores_box.set_max_children_per_line(12)
        self._cores_box.set_column_spacing(4)
        self._cores_box.set_row_spacing(4)
        self._cores_box.set_margin_start(8)
        self._cores_box.set_margin_end(8)
        self._cores_box.set_margin_top(4)
        self._cores_box.set_margin_bottom(6)

        self._core_labels = []
        self._core_temps = []  # Per-core sıcaklıklar (update_cpu'da kullanılır)
        for i in range(12):
            core_lbl = Gtk.Label()
            core_lbl.set_markup(f"<small>T{i}: — MHz</small>")
            core_lbl.set_size_request(120, -1)
            self._cores_box.add(core_lbl)
            self._core_labels.append(core_lbl)

        cores_frame.add(self._cores_box)
        self.pack_start(cores_frame, False, False, 0)

        # --- Termal koruma durumu ---
        self._thermal_label = Gtk.Label()
        self._thermal_label.set_halign(Gtk.Align.START)
        self._thermal_label.set_margin_start(4)
        self.pack_start(self._thermal_label, False, False, 0)

        # --- Aktif profil bilgisi ---
        profile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        profile_box.set_margin_top(4)
        prof_lbl = Gtk.Label()
        prof_lbl.set_markup("<b>Aktif Profil:</b>")
        profile_box.pack_start(prof_lbl, False, False, 0)
        self._profile_label = Gtk.Label(label="—")
        profile_box.pack_start(self._profile_label, False, False, 0)
        self.pack_start(profile_box, False, False, 0)

    def update_temps(self, temp_reading):
        """Sıcaklık değerlerini güncelle."""
        self.gauge_cpu.temp = temp_reading.cpu_package
        self.gauge_gpu.temp = temp_reading.gpu_nvidia
        self.gauge_pch.temp = temp_reading.pch
        self.gauge_nvme.temp = temp_reading.nvme
        self.gauge_wifi.temp = temp_reading.wifi

        # Per-core sıcaklıkları sakla (update_cpu'da kullanılacak)
        self._core_temps = list(temp_reading.cpu_cores) if temp_reading.cpu_cores else []

        # Geçmiş grafiğine veri ekle
        self._temp_chart.add_data({
            "CPU": temp_reading.cpu_package,
            "GPU": temp_reading.gpu_nvidia,
            "PCH": temp_reading.pch,
            "NVMe": temp_reading.nvme,
            "WiFi": temp_reading.wifi,
        })

    def update_cpu(self, cpu_status):
        """CPU bilgilerini güncelle."""
        v = self._cpu_values

        gov_text = cpu_status.governor.capitalize()
        v["cpu_governor"].set_markup(f"<b>{gov_text}</b>")

        epp_map = {
            "default": "Varsayılan",
            "performance": "Performans",
            "balance_performance": "Dengeli-Perf.",
            "balance_power": "Dengeli-Güç",
            "power": "Güç Tasarrufu",
        }
        v["cpu_epp"].set_text(epp_map.get(cpu_status.epp, cpu_status.epp))

        turbo_color = "#4caf50" if cpu_status.turbo_enabled else "#f44336"
        turbo_text = "Açık" if cpu_status.turbo_enabled else "Kapalı"
        v["cpu_turbo"].set_markup(f'<span color="{turbo_color}">{turbo_text}</span>')

        min_ghz = cpu_status.min_freq_khz / 1_000_000
        max_ghz = cpu_status.max_freq_khz / 1_000_000
        v["cpu_freq_range"].set_text(f"{min_ghz:.1f} — {max_ghz:.1f} GHz")

        if cpu_status.cur_freqs_khz:
            avg = sum(cpu_status.cur_freqs_khz) / len(cpu_status.cur_freqs_khz) / 1000
            v["cpu_avg_freq"].set_text(f"{avg:.0f} MHz")
        else:
            v["cpu_avg_freq"].set_text("—")

        v["cpu_perf_pct"].set_text(f"{cpu_status.min_perf_pct}% — {cpu_status.max_perf_pct}%")

        # Çekirdek frekansları + sıcaklıkları
        core_temps = getattr(self, "_core_temps", [])
        for i, freq_khz in enumerate(cpu_status.cur_freqs_khz):
            if i < len(self._core_labels):
                freq_mhz = freq_khz / 1000
                if freq_mhz >= 3500:
                    color = "#ff9800"
                elif freq_mhz >= 2000:
                    color = "#8bc34a"
                else:
                    color = "#78909c"

                # Her iki thread bir core'a denk gelir (HT): T0-T1 → Core 0, ...
                core_idx = i // 2
                temp_str = ""
                if core_idx < len(core_temps) and core_temps[core_idx] > 0:
                    ct = core_temps[core_idx]
                    tc = "#f44336" if ct >= 90 else "#ff9800" if ct >= 75 else "#78909c"
                    temp_str = f' <span color="{tc}">{ct:.0f}°</span>'

                self._core_labels[i].set_markup(
                    f'<small>T{i}: <span color="{color}">{freq_mhz:.0f}</span>MHz{temp_str}</small>'
                )

    def update_nvidia(self, nvidia_status):
        """NVIDIA GPU bilgilerini güncelle."""
        v = self._gpu_values

        if not nvidia_status.available:
            for val in v.values():
                val.set_text("N/A")
            return

        v["gpu_clock"].set_text(f"{nvidia_status.clock_graphics} MHz")
        v["gpu_mem_clock"].set_text(f"{nvidia_status.clock_memory} MHz")
        v["gpu_power"].set_text(
            f"{nvidia_status.power_draw:.1f}W / {nvidia_status.power_limit:.0f}W"
        )
        v["gpu_util"].set_text(
            f"GPU: {nvidia_status.utilization_gpu}%  Mem: {nvidia_status.utilization_memory}%"
        )
        v["gpu_vram"].set_text(
            f"{nvidia_status.vram_used} / {nvidia_status.vram_total} MiB"
        )
        mode_map = {"hybrid": "Hybrid", "nvidia": "NVIDIA", "integrated": "Entegre"}
        v["gpu_mode"].set_text(mode_map.get(nvidia_status.graphics_mode,
                                             nvidia_status.graphics_mode))

    def update_fan(self, fan_status):
        """Fan bilgilerini güncelle."""
        v = self._fan_values

        if not fan_status.ec_available:
            for val in v.values():
                val.set_text("EC Erişilemiyor")
            return

        mode_map = {"auto": "Otomatik (EC)", "manual": "Manuel", "curve": "Eğri (Oto.)"}
        v["fan_mode"].set_text(mode_map.get(fan_status.mode, fan_status.mode))
        v["fan_cpu_rpm"].set_text(f"{fan_status.cpu_fan_rpm} RPM")
        v["fan_gpu_rpm"].set_text(f"{fan_status.gpu_fan_rpm} RPM")
        v["fan_cpu_duty"].set_text(f"{fan_status.cpu_fan_duty_pct}%")
        v["fan_gpu_duty"].set_text(f"{fan_status.gpu_fan_duty_pct}%")

    def update_igpu(self, igpu_status):
        """Intel iGPU bilgilerini güncelle."""
        v = self._igpu_values

        if not igpu_status.available:
            for val in v.values():
                val.set_text("N/A")
            return

        v["igpu_act"].set_text(f"{igpu_status.act_freq_mhz} MHz")
        v["igpu_range"].set_text(
            f"{igpu_status.min_freq_mhz} — {igpu_status.max_freq_mhz} MHz"
        )
        v["igpu_boost"].set_text(f"{igpu_status.boost_freq_mhz} MHz")
        v["igpu_hw_limit"].set_text(
            f"{igpu_status.rpn_freq_mhz} — {igpu_status.rp0_freq_mhz} MHz"
        )

    def update_profile(self, profile_name):
        """Aktif profil bilgisini güncelle."""
        if profile_name:
            self._profile_label.set_markup(f'<span color="#4fc3f7"><b>{profile_name}</b></span>')
        else:
            self._profile_label.set_text("Yok")

    def update_thermal_status(self, thermal_state):
        """Termal koruma durum göstergesini güncelle."""
        if not thermal_state.active:
            self._thermal_label.set_text("")
            return

        level_colors = {1: "#ff9800", 2: "#ff5722", 3: "#f44336", 4: "#d50000"}
        color = level_colors.get(thermal_state.level, "#f44336")
        self._thermal_label.set_markup(
            f'<span color="{color}" weight="bold">'
            f'🛡 Termal Koruma Aktif (Seviye {thermal_state.level}) — '
            f'{thermal_state.action_taken}'
            f'</span>'
        )
