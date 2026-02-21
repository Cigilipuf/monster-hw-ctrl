"""
Monster HW Controller - Logger Utility
Merkezi loglama yapılandırması.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "monster-hw-ctrl" / "logs"
LOG_FILE = LOG_DIR / "monster-hw-ctrl.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3


def setup_logger(name: str = "monster-hw-ctrl", level: int = logging.INFO) -> logging.Logger:
    """Uygulama logger'ını yapılandır ve döndür."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)-20s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Dosya handler (rotating)
    try:
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILE, encoding="utf-8",
            maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except (PermissionError, OSError) as e:
        # Dosya yazılamıyorsa konsola uyar
        sys.stderr.write(f"[monster-hw-ctrl] Log dosyası oluşturulamadı: {e}\n")

    # Konsol handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Alt modül için logger al."""
    return logging.getLogger(f"monster-hw-ctrl.{module_name}")
