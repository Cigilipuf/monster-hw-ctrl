"""
Monster HW Controller - D-Bus Interface
Root yetkili daemon ile kullanıcı GUI arasındaki iletişimi sağlar.
"""

import json
from typing import Any, Dict

from src.utils.logger import get_logger

log = get_logger("dbus_interface")

# D-Bus servis bilgileri
DBUS_SERVICE = "com.monster.hwctrl"
DBUS_PATH = "/com/monster/hwctrl"
DBUS_INTERFACE = "com.monster.hwctrl.Controller"

# D-Bus introspection XML
INTROSPECTION_XML = f"""
<node>
  <interface name="{DBUS_INTERFACE}">
    <!-- Sıcaklık okuma -->
    <method name="GetTemperatures">
      <arg direction="out" type="s" name="json_data"/>
    </method>

    <!-- CPU durum/kontrol -->
    <method name="GetCpuStatus">
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="SetCpuGovernor">
      <arg direction="in" type="s" name="governor"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuEpp">
      <arg direction="in" type="s" name="epp"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuTurbo">
      <arg direction="in" type="b" name="enabled"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuMaxPerfPct">
      <arg direction="in" type="i" name="pct"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuMinPerfPct">
      <arg direction="in" type="i" name="pct"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuFreqRange">
      <arg direction="in" type="i" name="min_khz"/>
      <arg direction="in" type="i" name="max_khz"/>
      <arg direction="out" type="b" name="success"/>
    </method>

    <!-- NVIDIA GPU durum/kontrol -->
    <method name="GetNvidiaStatus">
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="SetNvidiaPowerLimit">
      <arg direction="in" type="i" name="watts"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetNvidiaGpuClocks">
      <arg direction="in" type="i" name="min_mhz"/>
      <arg direction="in" type="i" name="max_mhz"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="ResetNvidiaClocks">
      <arg direction="out" type="b" name="success"/>
    </method>

    <!-- Intel iGPU durum/kontrol -->
    <method name="GetIntelGpuStatus">
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="SetIntelGpuFreqRange">
      <arg direction="in" type="i" name="min_mhz"/>
      <arg direction="in" type="i" name="max_mhz"/>
      <arg direction="out" type="b" name="success"/>
    </method>

    <!-- Fan durum/kontrol -->
    <method name="GetFanStatus">
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="SetFanAutoMode">
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetFanManualMode">
      <arg direction="in" type="i" name="duty_pct"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetCpuFan">
      <arg direction="in" type="i" name="duty_pct"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetGpuFan">
      <arg direction="in" type="i" name="duty_pct"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SetFanCurve">
      <arg direction="in" type="s" name="curve_json"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="StartFanCurve">
      <arg direction="out" type="b" name="success"/>
    </method>

    <!-- Profil yönetimi -->
    <method name="ListProfiles">
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="GetProfile">
      <arg direction="in" type="s" name="name"/>
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="ApplyProfile">
      <arg direction="in" type="s" name="name"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="SaveProfile">
      <arg direction="in" type="s" name="name"/>
      <arg direction="in" type="s" name="json_data"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="DeleteProfile">
      <arg direction="in" type="s" name="name"/>
      <arg direction="out" type="b" name="success"/>
    </method>
    <method name="CreateProfileFromCurrent">
      <arg direction="in" type="s" name="name"/>
      <arg direction="in" type="s" name="description"/>
      <arg direction="out" type="s" name="json_data"/>
    </method>
    <method name="GetActiveProfile">
      <arg direction="out" type="s" name="name"/>
    </method>
  </interface>
</node>
"""
