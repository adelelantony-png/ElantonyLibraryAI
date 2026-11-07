# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Database Connection Manager
Provides connection pooling, SQLite WAL mode optimization, and PostgreSQL readiness.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional
from elantony.core.config import settings
from elantony.core.logging import logger


def get_sqlite_path() -> str:
    """Extracts filesystem path from SQLite database URL."""
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        path_str = db_url.replace("sqlite:///", "")
        p = Path(path_str)
        if not p.is_absolute():
            p = settings.base_dir / p
        return str(p)
    return str(settings.base_dir / "file_archive.db")


def get_connection() -> sqlite3.Connection:
    """
    Creates an optimized SQLite connection with:
    - WAL Mode (Write-Ahead Logging) for concurrent reads & writes.
    - 64MB Cache size.
    - Row factory enabled for dictionary-like column access.
    """
    db_path = get_sqlite_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row

    # Performance and concurrency optimizations
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn
