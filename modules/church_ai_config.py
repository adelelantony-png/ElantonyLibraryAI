# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Configuration Engine
Manages paths, thresholds, OCR language parameters, and resource limits.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config" / "church_ai_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "project_name": "ArchiveMaster - ChurchAI",
    "version": "1.0.0",
    "paths": {
        "books_local": str(BASE_DIR / "books" / "local"),
        "books_downloaded": str(BASE_DIR / "books" / "downloaded"),
        "extracted_text": str(BASE_DIR / "extracted_text"),
        "processed_text": str(BASE_DIR / "processed_text"),
        "database": str(BASE_DIR / "file_archive.db"),
        "reports": str(BASE_DIR / "reports"),
        "logs": str(BASE_DIR / "logs")
    },
    "ocr": {
        "tesseract_cmd": "",
        "tessdata_dir": "",
        "default_languages": "ara+eng",
        "dpi": 150,
        "preprocess_images": True,
        "confidence_threshold": 60.0
    },
    "extraction": {
        "min_text_len_per_page": 30,
        "min_arabic_ratio": 0.2,
        "max_pages_per_book": 1000,
        "batch_size_books": 20,
        "max_memory_mb": 600
    },
    "rag": {
        "chunk_size_chars": 1200,
        "chunk_overlap_chars": 150,
        "preserve_page_markers": True
    }
}


def load_config() -> Dict[str, Any]:
    """Loads configuration from JSON file or returns defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge defaults for any missing keys
        merged = DEFAULT_CONFIG.copy()
        for k, v in data.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                merged[k].update(v)
            else:
                merged[k] = v
        # Overlay environment variables
        env_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if env_token:
            merged.setdefault("cloud", {})["telegram_bot_token"] = env_token

        env_db = os.getenv("DATABASE_URL")
        if env_db and env_db.startswith("sqlite:///"):
            sqlite_file = env_db.replace("sqlite:///", "")
            merged.setdefault("paths", {})["database"] = sqlite_file

        return merged
    except Exception as e:
        print(f"Warning: Failed to parse {CONFIG_FILE} ({e}). Using defaults.")
        return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> None:
    """Saves configuration to JSON file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_abs_path(path_key: str) -> Path:
    """Resolves an absolute path from the config paths dictionary."""
    cfg = load_config()
    raw = cfg.get("paths", {}).get(path_key, "")
    p = Path(raw)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p
