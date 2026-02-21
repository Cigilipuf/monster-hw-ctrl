"""
Monster HW Controller - Embedded Controller Access
Clevo tabanlı Monster TULPAR T5 V19.2 için EC erişim katmanı.
Fan kontrolü, EC register okuma/yazma işlemleri.

UYARI: EC'ye yanlış değer yazmak donanıma zarar verebilir!
Bu modül dikkatli kullanılmalıdır.
"""

import os
import struct
import threading
import time
from pathlib import Path
from typing import Optional, Set

from src.utils.logger import get_logger

log = get_logger("ec_access")

EC_IO_PATH = Path("/sys/kernel/debug/ec/ec0/io")
DEV_PORT = Path("/dev/port")

# EC I/O portları (Clevo standard)
EC_CMD_PORT = 0x66
EC_DATA_PORT = 0x62
EC_SC_IBF = 0x02   # Input Buffer Full
EC_SC_OBF = 0x01   # Output Buffer Full

# EC komutları
EC_CMD_READ = 0x80
EC_CMD_WRITE = 0x81

# Güvenli yazma register'ları (Clevo fan kontrol)
# Sadece bu adreslere yazma izni verilir
SAFE_WRITE_REGISTERS: Set[int] = {
    0x68,  # CPU fan duty
    0x69,  # GPU fan duty
    0xD7,  # Fan mode (auto/manual)
}


class EcAccess:
    """Embedded Controller düşük seviye erişim katmanı.

    İki yöntem destekler:
    1. ec_sys modülü (/sys/kernel/debug/ec/ec0/io) - tercih edilen
    2. /dev/port doğrudan I/O - alternatif
    """

    def __init__(self):
        self._method: Optional[str] = None
        self._port_fd: Optional[int] = None
        self._lock = threading.Lock()
        self._safe_registers = set(SAFE_WRITE_REGISTERS)
        self._detect_method()

    def _detect_method(self):
        """Kullanılabilir EC erişim yöntemini belirle."""
        try:
            if EC_IO_PATH.exists():
                self._method = "ec_sys"
                log.info("EC erişim yöntemi: ec_sys (%s)", EC_IO_PATH)
                return
        except (PermissionError, OSError):
            # debugfs genellikle root gerektirir
            log.debug("EC_IO_PATH erişim izni reddedildi, root ile deneyin")

        try:
            if DEV_PORT.exists():
                self._method = "dev_port"
                log.info("EC erişim yöntemi: /dev/port")
                return
        except (PermissionError, OSError):
            log.debug("/dev/port erişim izni reddedildi")

        self._method = None
        log.warning("EC erişim yöntemi bulunamadı! "
                   "Fan kontrolü kullanılamaz. "
                   "'sudo modprobe ec_sys write_support=1' deneyin.")

    @property
    def available(self) -> bool:
        return self._method is not None

    @property
    def method(self) -> str:
        return self._method or "none"

    def add_safe_register(self, offset: int):
        """Güvenli yazma listesine yeni register ekle."""
        self._safe_registers.add(offset)
        log.info("Güvenli register eklendi: 0x%02X", offset)

    def read_byte(self, offset: int) -> Optional[int]:
        """EC register'ından bir byte oku (thread-safe)."""
        with self._lock:
            if self._method == "ec_sys":
                return self._ec_sys_read(offset)
            elif self._method == "dev_port":
                return self._port_read(offset)
            return None

    def write_byte(self, offset: int, value: int, force: bool = False) -> bool:
        """EC register'ına bir byte yaz (thread-safe).
        
        UYARI: Yanlış değer yazmak donanıma zarar verebilir!
        Sadece güvenli register listesindeki adreslere yazılır.
        force=True ile güvenlik kontrolü atlanabilir (dikkat!).
        """
        if value < 0 or value > 255:
            log.error("Geçersiz EC değer: 0x%02X (0-255 arası olmalı)", value)
            return False

        if not force and offset not in self._safe_registers:
            log.error(
                "EC güvenlik: Register 0x%02X güvenli listede değil! "
                "Yazma engellendi. Bilinen güvenli: %s",
                offset,
                {f"0x{r:02X}" for r in self._safe_registers},
            )
            return False

        with self._lock:
            if self._method == "ec_sys":
                return self._ec_sys_write(offset, value)
            elif self._method == "dev_port":
                return self._port_write(offset, value)
            return False

    # --- ec_sys yöntemi ---

    @staticmethod
    def _ec_sys_read(offset: int) -> Optional[int]:
        """ec_sys üzerinden EC register oku."""
        try:
            with open(EC_IO_PATH, "rb") as f:
                f.seek(offset)
                data = f.read(1)
                if data:
                    return data[0]
        except (IOError, PermissionError) as e:
            log.debug("EC okuma hatası (offset 0x%02X): %s", offset, e)
        return None

    @staticmethod
    def _ec_sys_write(offset: int, value: int) -> bool:
        """ec_sys üzerinden EC register yaz."""
        try:
            with open(EC_IO_PATH, "r+b") as f:
                f.seek(offset)
                f.write(bytes([value]))
                f.flush()
            log.debug("EC yazıldı: 0x%02X = 0x%02X (%d)", offset, value, value)
            return True
        except (IOError, PermissionError) as e:
            log.error("EC yazma hatası (offset 0x%02X): %s", offset, e)
            return False

    # --- /dev/port yöntemi ---

    def _port_wait_ibf_clear(self, fd: int, timeout: float = 0.1) -> bool:
        """EC Input Buffer Full bayrağının temizlenmesini bekle."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            os.lseek(fd, EC_CMD_PORT, os.SEEK_SET)
            status = struct.unpack("B", os.read(fd, 1))[0]
            if not (status & EC_SC_IBF):
                return True
            time.sleep(0.001)
        log.warning("EC IBF timeout!")
        return False

    def _port_wait_obf_set(self, fd: int, timeout: float = 0.1) -> bool:
        """EC Output Buffer Full bayrağının set olmasını bekle."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            os.lseek(fd, EC_CMD_PORT, os.SEEK_SET)
            status = struct.unpack("B", os.read(fd, 1))[0]
            if status & EC_SC_OBF:
                return True
            time.sleep(0.001)
        log.warning("EC OBF timeout!")
        return False

    def _port_read(self, offset: int) -> Optional[int]:
        """/dev/port üzerinden EC register oku."""
        try:
            fd = self._get_port_fd()
            if fd is None:
                return None

            # Komut gönder: READ
            if not self._port_wait_ibf_clear(fd):
                return None
            os.lseek(fd, EC_CMD_PORT, os.SEEK_SET)
            os.write(fd, struct.pack("B", EC_CMD_READ))

            # Adres gönder
            if not self._port_wait_ibf_clear(fd):
                return None
            os.lseek(fd, EC_DATA_PORT, os.SEEK_SET)
            os.write(fd, struct.pack("B", offset))

            # Veriyi oku
            if not self._port_wait_obf_set(fd):
                return None
            os.lseek(fd, EC_DATA_PORT, os.SEEK_SET)
            data = struct.unpack("B", os.read(fd, 1))[0]
            return data
        except (IOError, PermissionError, OSError) as e:
            log.debug("EC port okuma hatası (0x%02X): %s", offset, e)
            self._close_port_fd()
            return None

    def _port_write(self, offset: int, value: int) -> bool:
        """/dev/port üzerinden EC register yaz."""
        try:
            fd = self._get_port_fd()
            if fd is None:
                return False

            # Komut gönder: WRITE
            if not self._port_wait_ibf_clear(fd):
                return False
            os.lseek(fd, EC_CMD_PORT, os.SEEK_SET)
            os.write(fd, struct.pack("B", EC_CMD_WRITE))

            # Adres gönder
            if not self._port_wait_ibf_clear(fd):
                return False
            os.lseek(fd, EC_DATA_PORT, os.SEEK_SET)
            os.write(fd, struct.pack("B", offset))

            # Veri gönder
            if not self._port_wait_ibf_clear(fd):
                return False
            os.lseek(fd, EC_DATA_PORT, os.SEEK_SET)
            os.write(fd, struct.pack("B", value))

            log.debug("EC port yazıldı: 0x%02X = 0x%02X", offset, value)
            return True
        except (IOError, PermissionError, OSError) as e:
            log.error("EC port yazma hatası (0x%02X): %s", offset, e)
            self._close_port_fd()
            return False

    def _get_port_fd(self) -> Optional[int]:
        """Kalıcı /dev/port file descriptor al veya oluştur."""
        if self._port_fd is None:
            try:
                self._port_fd = os.open(str(DEV_PORT), os.O_RDWR)
            except (IOError, PermissionError, OSError) as e:
                log.error("/dev/port açılamadı: %s", e)
                return None
        return self._port_fd

    def _close_port_fd(self):
        """Port FD'yi temizle."""
        if self._port_fd is not None:
            try:
                os.close(self._port_fd)
            except OSError:
                pass
            self._port_fd = None

    def __del__(self):
        """Cleanup."""
        self._close_port_fd()

    def read_block(self, start: int, length: int) -> bytes:
        """EC register bloğu oku (keşif için). Atomik okuma."""
        data = bytearray()
        with self._lock:
            for i in range(length):
                offset = start + i
                if self._method == "ec_sys":
                    val = self._ec_sys_read(offset)
                elif self._method == "dev_port":
                    val = self._port_read(offset)
                else:
                    val = None
                data.append(val if val is not None else 0)
        return bytes(data)

    def dump_ec(self) -> Optional[bytes]:
        """Tüm EC registerlarını dump et (256 byte)."""
        if not self.available:
            return None
        return self.read_block(0, 256)
