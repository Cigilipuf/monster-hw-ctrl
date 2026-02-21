"""
Monster HW Controller - Profile Panel
Güç profili oluşturma, düzenleme, silme ve profiller arası geçiş.
"""

import copy

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


# Profil ikonları
PROFILE_ICONS = {
    "sessiz": "🔇",
    "dengeli": "⚖️",
    "performans": "🚀",
    "oyun": "🎮",
    "pil_tasarrufu": "🔋",
}


class ProfilePanel(Gtk.Box):
    """Profil yönetim paneli."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        self._apply_callbacks = []
        self._create_callbacks = []
        self._delete_callbacks = []
        self._edit_callbacks = []
        self._profiles = []
        self._active_profile = None

        # === Aktif Profil Bilgisi ===
        active_frame = Gtk.Frame(label=" Aktif Profil ")
        active_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        active_box.set_margin_start(12)
        active_box.set_margin_end(12)
        active_box.set_margin_top(8)
        active_box.set_margin_bottom(10)

        self._active_label = Gtk.Label()
        self._active_label.set_markup(
            '<span size="large"><b>Profil seçilmedi</b></span>'
        )
        self._active_label.set_halign(Gtk.Align.START)
        active_box.pack_start(self._active_label, True, True, 0)

        active_frame.add(active_box)
        self.pack_start(active_frame, False, False, 0)

        # === Profil Listesi ===
        list_frame = Gtk.Frame(label=" Kayıtlı Profiller ")
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        list_box.set_margin_start(10)
        list_box.set_margin_end(10)
        list_box.set_margin_top(6)
        list_box.set_margin_bottom(8)

        # Liste
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.set_activate_on_single_click(False)
        self._listbox.connect("row-activated", self._on_row_activated)
        scroll.add(self._listbox)
        list_box.pack_start(scroll, True, True, 0)

        # Butonlar
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(4)

        self._apply_btn = Gtk.Button(label="Profil Uygula")
        self._apply_btn.get_style_context().add_class("suggested-action")
        self._apply_btn.set_size_request(140, -1)
        self._apply_btn.connect("clicked", self._on_apply)
        btn_box.pack_start(self._apply_btn, False, False, 0)

        self._edit_btn = Gtk.Button(label="Düzenle")
        self._edit_btn.connect("clicked", self._on_edit)
        btn_box.pack_start(self._edit_btn, False, False, 0)

        self._delete_btn = Gtk.Button(label="Sil")
        self._delete_btn.get_style_context().add_class("destructive-action")
        self._delete_btn.connect("clicked", self._on_delete)
        btn_box.pack_start(self._delete_btn, False, False, 0)

        list_box.pack_start(btn_box, False, False, 0)

        list_frame.add(list_box)
        self.pack_start(list_frame, True, True, 0)

        # === Yeni Profil Oluşturma ===
        create_frame = Gtk.Frame(label=" Yeni Profil Oluştur ")
        create_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        create_box.set_margin_start(10)
        create_box.set_margin_end(10)
        create_box.set_margin_top(6)
        create_box.set_margin_bottom(8)

        # İsim
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_lbl = Gtk.Label(label="Profil Adı:")
        name_lbl.set_size_request(80, -1)
        name_box.pack_start(name_lbl, False, False, 0)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_placeholder_text("örn: video_editing")
        self._name_entry.set_hexpand(True)
        name_box.pack_start(self._name_entry, True, True, 0)
        create_box.pack_start(name_box, False, False, 0)

        # Açıklama
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        desc_lbl = Gtk.Label(label="Açıklama:")
        desc_lbl.set_size_request(80, -1)
        desc_box.pack_start(desc_lbl, False, False, 0)
        self._desc_entry = Gtk.Entry()
        self._desc_entry.set_placeholder_text("Profil açıklaması (opsiyonel)")
        self._desc_entry.set_hexpand(True)
        desc_box.pack_start(self._desc_entry, True, True, 0)
        create_box.pack_start(desc_box, False, False, 0)

        create_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._create_btn = Gtk.Button(label="Mevcut Ayarlardan Profil Oluştur")
        self._create_btn.connect("clicked", self._on_create)
        create_btn_box.pack_start(self._create_btn, False, False, 0)
        create_box.pack_start(create_btn_box, False, False, 0)

        create_frame.add(create_box)
        self.pack_start(create_frame, False, False, 0)

        # Status
        self._status_label = Gtk.Label()
        self._status_label.set_halign(Gtk.Align.START)
        self.pack_start(self._status_label, False, False, 0)

    # === Callbacks ===

    def on_apply(self, callback):
        """Profil uygula: callback(profile_name) -> bool"""
        self._apply_callbacks.append(callback)

    def on_create(self, callback):
        """Profil oluştur: callback(name, description) -> bool"""
        self._create_callbacks.append(callback)

    def on_delete(self, callback):
        """Profil sil: callback(profile_name) -> bool"""
        self._delete_callbacks.append(callback)

    def on_edit(self, callback):
        """Profil düzenle: callback(profile_name, new_data) -> bool"""
        self._edit_callbacks.append(callback)

    def _on_edit(self, button):
        """Seçili profili düzenle."""
        row = self._listbox.get_selected_row()
        if not row:
            self._show_status("Lütfen bir profil seçin", error=True)
            return

        profile_name = row.get_name()
        profile_data = None
        for name, data in self._profiles:
            if name == profile_name:
                profile_data = copy.deepcopy(data)
                break
        if not profile_data:
            self._show_status("Profil verisi bulunamadı", error=True)
            return

        dialog = ProfileEditDialog(self.get_toplevel(), profile_name, profile_data)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_data = dialog.get_profile_data()
            for cb in self._edit_callbacks:
                try:
                    success = cb(profile_name, new_data)
                    if success:
                        self._show_status(f"✓ Profil güncellendi: {profile_name}")
                    else:
                        self._show_status("✗ Profil güncellenemedi", error=True)
                except Exception as e:
                    self._show_status(f"✗ Hata: {e}", error=True)

        dialog.destroy()

    def _on_row_activated(self, listbox, row):
        """Çift tıklama ile profil uygula."""
        self._on_apply(None)

    def _on_apply(self, button):
        """Seçili profili uygula."""
        row = self._listbox.get_selected_row()
        if not row:
            self._show_status("Lütfen bir profil seçin", error=True)
            return

        profile_name = row.get_name()
        for cb in self._apply_callbacks:
            try:
                success = cb(profile_name)
                if success:
                    self._show_status(f"✓ Profil uygulandı: {profile_name}")
                    self._active_profile = profile_name
                    self._update_active_label()
                    self.refresh_list(self._profiles)
                else:
                    self._show_status("✗ Profil uygulanamadı", error=True)
            except Exception as e:
                self._show_status(f"✗ Hata: {e}", error=True)

    def _on_delete(self, button):
        """Seçili profili sil."""
        row = self._listbox.get_selected_row()
        if not row:
            self._show_status("Lütfen bir profil seçin", error=True)
            return

        profile_name = row.get_name()

        # Onay diyalogu
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"'{profile_name}' profili silinsin mi?",
        )
        dialog.format_secondary_text("Bu işlem geri alınamaz.")
        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            return

        for cb in self._delete_callbacks:
            try:
                success = cb(profile_name)
                if success:
                    self._show_status(f"✓ Profil silindi: {profile_name}")
                else:
                    self._show_status("✗ Varsayılan profiller silinemez", error=True)
            except Exception as e:
                self._show_status(f"✗ Hata: {e}", error=True)

    def _on_create(self, button):
        """Mevcut ayarlardan profil oluştur."""
        name = self._name_entry.get_text().strip()
        if not name:
            self._show_status("Lütfen bir profil adı girin", error=True)
            return

        # Geçersiz karakterleri kontrol
        if not name.replace("_", "").replace("-", "").isalnum():
            self._show_status("Profil adı sadece harf, rakam, _ ve - içerebilir", error=True)
            return

        desc = self._desc_entry.get_text().strip()

        for cb in self._create_callbacks:
            try:
                success = cb(name, desc)
                if success:
                    self._show_status(f"✓ Profil oluşturuldu: {name}")
                    self._name_entry.set_text("")
                    self._desc_entry.set_text("")
                else:
                    self._show_status("✗ Profil oluşturulamadı", error=True)
            except Exception as e:
                self._show_status(f"✗ Hata: {e}", error=True)

    def _show_status(self, msg, error=False):
        color = "#f44336" if error else "#4caf50"
        self._status_label.set_markup(f'<span color="{color}">{msg}</span>')
        GLib.timeout_add(4000, lambda: self._status_label.set_text(""))

    def _update_active_label(self):
        if self._active_profile:
            icon = PROFILE_ICONS.get(self._active_profile, "📋")
            self._active_label.set_markup(
                f'<span size="large">{icon} <b>{self._active_profile.replace("_", " ").title()}</b></span>'
            )
        else:
            self._active_label.set_markup(
                '<span size="large"><b>Profil seçilmedi</b></span>'
            )

    def refresh_list(self, profiles_data):
        """Profil listesini yenile. 
        profiles_data: [(name, profile_dict), ...]
        """
        self._profiles = profiles_data

        # Mevcut satırları temizle
        for child in self._listbox.get_children():
            self._listbox.remove(child)

        for name, data in profiles_data:
            row = Gtk.ListBoxRow()
            row.set_name(name)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_start(8)
            hbox.set_margin_end(8)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)

            # İkon
            icon = PROFILE_ICONS.get(name, "📋")
            icon_lbl = Gtk.Label(label=icon)
            icon_lbl.set_size_request(30, -1)
            hbox.pack_start(icon_lbl, False, False, 0)

            # İsim ve açıklama
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            display_name = data.get("name", name.replace("_", " ").title())
            name_lbl = Gtk.Label()
            name_lbl.set_halign(Gtk.Align.START)

            if name == self._active_profile:
                name_lbl.set_markup(f'<b>{display_name}</b> <span color="#4caf50">(aktif)</span>')
            else:
                name_lbl.set_markup(f'<b>{display_name}</b>')

            text_box.pack_start(name_lbl, False, False, 0)

            desc = data.get("description", "")
            if desc:
                desc_lbl = Gtk.Label()
                desc_lbl.set_markup(f'<small><span color="#90a4ae">{desc}</span></small>')
                desc_lbl.set_halign(Gtk.Align.START)
                text_box.pack_start(desc_lbl, False, False, 0)

            hbox.pack_start(text_box, True, True, 0)

            # Profil özet bilgileri
            cpu = data.get("cpu", {})
            fan = data.get("fan", {})
            summary_parts = []
            if "governor" in cpu:
                summary_parts.append(cpu["governor"][:4])
            if "turbo" in cpu:
                summary_parts.append("T" if cpu["turbo"] else "noT")
            if "mode" in fan:
                summary_parts.append(fan["mode"][:4])

            if summary_parts:
                summary_lbl = Gtk.Label()
                summary_lbl.set_markup(
                    f'<small><span color="#78909c">{" | ".join(summary_parts)}</span></small>'
                )
                hbox.pack_end(summary_lbl, False, False, 0)

            row.add(hbox)
            self._listbox.add(row)

        self._listbox.show_all()

    def set_active_profile(self, name):
        """Aktif profili güncelle."""
        self._active_profile = name
        self._update_active_label()


class ProfileEditDialog(Gtk.Dialog):
    """Profil düzenleme diyalogu.

    CPU, GPU, iGPU ve fan ayarlarını düzenlenebilir form olarak sunar.
    """

    GOVERNORS = ["powersave", "performance"]
    EPPS = ["default", "performance", "balance_performance", "balance_power", "power"]
    FAN_MODES = ["auto", "manual", "curve"]

    def __init__(self, parent, profile_name, profile_data):
        super().__init__(
            title=f"Profil Düzenle: {profile_name}",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        self.add_buttons(
            "İptal", Gtk.ResponseType.CANCEL,
            "Kaydet", Gtk.ResponseType.OK,
        )
        self.set_default_size(520, 600)
        self._data = profile_data

        content = self.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_margin_top(8)
        content.set_margin_bottom(8)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # --- Genel ---
        gen_frame = Gtk.Frame(label=" Genel ")
        gen_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        gen_grid.set_margin_start(8)
        gen_grid.set_margin_end(8)
        gen_grid.set_margin_top(6)
        gen_grid.set_margin_bottom(8)

        gen_grid.attach(Gtk.Label(label="Ad:", halign=Gtk.Align.START), 0, 0, 1, 1)
        self._w_name = Gtk.Entry(text=profile_data.get("name", profile_name))
        self._w_name.set_hexpand(True)
        gen_grid.attach(self._w_name, 1, 0, 1, 1)

        gen_grid.attach(Gtk.Label(label="Açıklama:", halign=Gtk.Align.START), 0, 1, 1, 1)
        self._w_desc = Gtk.Entry(text=profile_data.get("description", ""))
        self._w_desc.set_hexpand(True)
        gen_grid.attach(self._w_desc, 1, 1, 1, 1)

        gen_frame.add(gen_grid)
        vbox.pack_start(gen_frame, False, False, 0)

        # --- CPU ---
        cpu = profile_data.get("cpu", {})
        cpu_frame = Gtk.Frame(label=" CPU Ayarları ")
        cpu_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        cpu_grid.set_margin_start(8)
        cpu_grid.set_margin_end(8)
        cpu_grid.set_margin_top(6)
        cpu_grid.set_margin_bottom(8)

        r = 0
        cpu_grid.attach(Gtk.Label(label="Governor:", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_governor = Gtk.ComboBoxText()
        for g in self.GOVERNORS:
            self._w_governor.append_text(g)
        cur_gov = cpu.get("governor", "powersave")
        self._w_governor.set_active(self.GOVERNORS.index(cur_gov) if cur_gov in self.GOVERNORS else 0)
        cpu_grid.attach(self._w_governor, 1, r, 1, 1)

        r += 1
        cpu_grid.attach(Gtk.Label(label="EPP:", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_epp = Gtk.ComboBoxText()
        for e in self.EPPS:
            self._w_epp.append_text(e)
        cur_epp = cpu.get("epp", "balance_performance")
        self._w_epp.set_active(self.EPPS.index(cur_epp) if cur_epp in self.EPPS else 0)
        cpu_grid.attach(self._w_epp, 1, r, 1, 1)

        r += 1
        cpu_grid.attach(Gtk.Label(label="Turbo Boost:", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_turbo = Gtk.Switch(active=cpu.get("turbo", True))
        self._w_turbo.set_halign(Gtk.Align.START)
        cpu_grid.attach(self._w_turbo, 1, r, 1, 1)

        r += 1
        cpu_grid.attach(Gtk.Label(label="Min Frekans (MHz):", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_cpu_min = Gtk.SpinButton.new_with_range(800, 5000, 100)
        self._w_cpu_min.set_value(cpu.get("min_freq_khz", 800000) / 1000)
        cpu_grid.attach(self._w_cpu_min, 1, r, 1, 1)

        r += 1
        cpu_grid.attach(Gtk.Label(label="Max Frekans (MHz):", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_cpu_max = Gtk.SpinButton.new_with_range(800, 5000, 100)
        self._w_cpu_max.set_value(cpu.get("max_freq_khz", 5000000) / 1000)
        cpu_grid.attach(self._w_cpu_max, 1, r, 1, 1)

        r += 1
        cpu_grid.attach(Gtk.Label(label="Max Perf %:", halign=Gtk.Align.START), 0, r, 1, 1)
        self._w_perf_pct = Gtk.SpinButton.new_with_range(16, 100, 1)
        self._w_perf_pct.set_value(cpu.get("max_perf_pct", 100))
        cpu_grid.attach(self._w_perf_pct, 1, r, 1, 1)

        cpu_frame.add(cpu_grid)
        vbox.pack_start(cpu_frame, False, False, 0)

        # --- NVIDIA GPU ---
        nv = profile_data.get("nvidia", {})
        nv_frame = Gtk.Frame(label=" NVIDIA GPU Ayarları ")
        nv_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        nv_grid.set_margin_start(8)
        nv_grid.set_margin_end(8)
        nv_grid.set_margin_top(6)
        nv_grid.set_margin_bottom(8)

        nv_grid.attach(Gtk.Label(label="Güç Limiti (W):", halign=Gtk.Align.START), 0, 0, 1, 1)
        self._w_nv_power = Gtk.SpinButton.new_with_range(10, 90, 5)
        self._w_nv_power.set_value(nv.get("power_limit", 60))
        nv_grid.attach(self._w_nv_power, 1, 0, 1, 1)

        nv_grid.attach(Gtk.Label(label="GPU Clock Max (MHz):", halign=Gtk.Align.START), 0, 1, 1, 1)
        self._w_nv_clock = Gtk.SpinButton.new_with_range(300, 2100, 50)
        self._w_nv_clock.set_value(nv.get("gpu_clock_max", 2100))
        nv_grid.attach(self._w_nv_clock, 1, 1, 1, 1)

        nv_grid.attach(Gtk.Label(label="Mem Clock Max (MHz):", halign=Gtk.Align.START), 0, 2, 1, 1)
        self._w_nv_mem = Gtk.SpinButton.new_with_range(405, 5501, 50)
        self._w_nv_mem.set_value(nv.get("mem_clock_max", 5501))
        nv_grid.attach(self._w_nv_mem, 1, 2, 1, 1)

        nv_frame.add(nv_grid)
        vbox.pack_start(nv_frame, False, False, 0)

        # --- Intel iGPU ---
        igpu = profile_data.get("igpu", {})
        igpu_frame = Gtk.Frame(label=" Intel iGPU Ayarları ")
        igpu_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        igpu_grid.set_margin_start(8)
        igpu_grid.set_margin_end(8)
        igpu_grid.set_margin_top(6)
        igpu_grid.set_margin_bottom(8)

        igpu_grid.attach(Gtk.Label(label="Min Frekans (MHz):", halign=Gtk.Align.START), 0, 0, 1, 1)
        self._w_igpu_min = Gtk.SpinButton.new_with_range(350, 1150, 50)
        self._w_igpu_min.set_value(igpu.get("min_freq_mhz", 350))
        igpu_grid.attach(self._w_igpu_min, 1, 0, 1, 1)

        igpu_grid.attach(Gtk.Label(label="Max Frekans (MHz):", halign=Gtk.Align.START), 0, 1, 1, 1)
        self._w_igpu_max = Gtk.SpinButton.new_with_range(350, 1150, 50)
        self._w_igpu_max.set_value(igpu.get("max_freq_mhz", 1150))
        igpu_grid.attach(self._w_igpu_max, 1, 1, 1, 1)

        igpu_frame.add(igpu_grid)
        vbox.pack_start(igpu_frame, False, False, 0)

        # --- Fan ---
        fan = profile_data.get("fan", {})
        fan_frame = Gtk.Frame(label=" Fan Ayarları ")
        fan_grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        fan_grid.set_margin_start(8)
        fan_grid.set_margin_end(8)
        fan_grid.set_margin_top(6)
        fan_grid.set_margin_bottom(8)

        fan_grid.attach(Gtk.Label(label="Mod:", halign=Gtk.Align.START), 0, 0, 1, 1)
        self._w_fan_mode = Gtk.ComboBoxText()
        for m in self.FAN_MODES:
            self._w_fan_mode.append_text(m)
        cur_mode = fan.get("mode", "auto")
        self._w_fan_mode.set_active(self.FAN_MODES.index(cur_mode) if cur_mode in self.FAN_MODES else 0)
        self._w_fan_mode.connect("changed", self._on_fan_mode_changed)
        fan_grid.attach(self._w_fan_mode, 1, 0, 1, 1)

        # Manual duty
        fan_grid.attach(Gtk.Label(label="Manuel Duty %:", halign=Gtk.Align.START), 0, 1, 1, 1)
        self._w_fan_duty = Gtk.SpinButton.new_with_range(20, 100, 5)
        self._w_fan_duty.set_value(fan.get("duty_pct", 50))
        fan_grid.attach(self._w_fan_duty, 1, 1, 1, 1)

        # Curve editor (simple text for now)
        fan_grid.attach(Gtk.Label(label="Eğri:", halign=Gtk.Align.START, valign=Gtk.Align.START), 0, 2, 1, 1)
        curve_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._curve_rows = []
        curve_data = fan.get("curve", [])
        for point in curve_data:
            crow = self._create_curve_row(point.get("temp", 50), point.get("duty_pct", 50))
            curve_box.pack_start(crow["box"], False, False, 0)
            self._curve_rows.append(crow)

        add_row_btn = Gtk.Button(label="+ Nokta Ekle")
        add_row_btn.connect("clicked", lambda b: self._add_curve_point(curve_box))
        curve_box.pack_start(add_row_btn, False, False, 0)
        self._curve_box = curve_box
        self._add_point_btn = add_row_btn

        fan_grid.attach(curve_box, 1, 2, 1, 1)

        fan_frame.add(fan_grid)
        vbox.pack_start(fan_frame, False, False, 0)

        scroll.add(vbox)
        content.pack_start(scroll, True, True, 0)

        self._on_fan_mode_changed(self._w_fan_mode)
        self.show_all()

    def _create_curve_row(self, temp, duty):
        """Tek bir eğri noktası satırı oluştur."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        t_spin = Gtk.SpinButton.new_with_range(30, 88, 5)
        t_spin.set_value(min(temp, 88))
        d_spin = Gtk.SpinButton.new_with_range(20, 100, 5)
        d_spin.set_value(duty)
        box.pack_start(Gtk.Label(label="°C:"), False, False, 0)
        box.pack_start(t_spin, False, False, 0)
        box.pack_start(Gtk.Label(label="Duty%:"), False, False, 0)
        box.pack_start(d_spin, False, False, 0)

        rm_btn = Gtk.Button(label="✗")
        rm_btn.set_size_request(30, -1)
        row_data = {"box": box, "temp": t_spin, "duty": d_spin}
        rm_btn.connect("clicked", lambda b: self._remove_curve_point(row_data))
        box.pack_start(rm_btn, False, False, 0)

        return row_data

    def _add_curve_point(self, curve_box):
        """Eğriye yeni nokta ekle (88°C sert limit)."""
        crow = self._create_curve_row(60, 50)
        # Insert before the add button
        curve_box.pack_start(crow["box"], False, False, 0)
        curve_box.reorder_child(crow["box"], len(self._curve_rows))
        self._curve_rows.append(crow)
        crow["box"].show_all()

    def _remove_curve_point(self, row_data):
        """Eğri noktasını sil."""
        if len(self._curve_rows) <= 2:
            return  # minimum 2 nokta
        if row_data in self._curve_rows:
            self._curve_rows.remove(row_data)
            row_data["box"].destroy()

    def _on_fan_mode_changed(self, combo):
        """Fan moduna göre ilgili widget'ları göster/gizle."""
        mode = combo.get_active_text()
        self._w_fan_duty.set_sensitive(mode == "manual")
        for crow in self._curve_rows:
            crow["box"].set_sensitive(mode == "curve")
        self._add_point_btn.set_sensitive(mode == "curve")

    def get_profile_data(self):
        """Dialog'daki değerleri profil dict olarak döndür."""
        data = dict(self._data)  # preserve unknown keys
        data["name"] = self._w_name.get_text().strip() or data.get("name", "")
        data["description"] = self._w_desc.get_text().strip()

        data["cpu"] = {
            "governor": self._w_governor.get_active_text(),
            "epp": self._w_epp.get_active_text(),
            "turbo": self._w_turbo.get_active(),
            "min_freq_khz": int(self._w_cpu_min.get_value()) * 1000,
            "max_freq_khz": int(self._w_cpu_max.get_value()) * 1000,
            "max_perf_pct": int(self._w_perf_pct.get_value()),
        }

        data["nvidia"] = {
            "power_limit": int(self._w_nv_power.get_value()),
            "gpu_clock_max": int(self._w_nv_clock.get_value()),
            "mem_clock_max": int(self._w_nv_mem.get_value()),
        }

        data["igpu"] = {
            "min_freq_mhz": int(self._w_igpu_min.get_value()),
            "max_freq_mhz": int(self._w_igpu_max.get_value()),
        }

        fan_mode = self._w_fan_mode.get_active_text()
        fan_data = {"mode": fan_mode}
        if fan_mode == "manual":
            fan_data["duty_pct"] = int(self._w_fan_duty.get_value())
        elif fan_mode == "curve":
            curve = []
            for crow in self._curve_rows:
                curve.append({
                    "temp": int(crow["temp"].get_value()),
                    "duty_pct": int(crow["duty"].get_value()),
                })
            curve.sort(key=lambda p: p["temp"])
            fan_data["curve"] = curve
        data["fan"] = fan_data

        return data
