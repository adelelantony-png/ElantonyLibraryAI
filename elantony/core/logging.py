# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Structured Logging & Monitoring
Provides rotated logging, console formatting, and error tracking.
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from elantony.core.config import settings

LOGS_DIR = settings.logs_dir
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "elantony_ai.log"


def setup_logger(name: str = "ElantonyAI") -> logging.Logger:
    """Configures and returns a structured logger with rotation."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO if settings.app_env == "production" else logging.DEBUG)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (UTF-8 safe)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (Max 10 MB per file, up to 5 backups)
    file_handler = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
