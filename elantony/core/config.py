# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - System Configuration
Loads and validates settings from environment variables (.env) and local defaults.
Ensures zero hardcoded secrets and robust fallback handling.
"""

import os
from pathlib import Path
from typing import Set, List, Optional
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseModel):
    """Immutable, strongly-typed system settings."""
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "ELANTONY LIBRARY AI"))
    app_port: int = Field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    app_host: str = Field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))

    # Telegram Bot
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    telegram_mode: str = Field(default_factory=lambda: os.getenv("TELEGRAM_MODE", "polling").lower())
    telegram_webhook_url: str = Field(default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_URL", "").strip())
    telegram_webhook_secret: str = Field(default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip())

    # Access Control (Whitelists)
    allowed_telegram_user_ids: Set[int] = Field(default_factory=set)
    admin_telegram_user_ids: Set[int] = Field(default_factory=set)
    rate_limit_per_minute: int = Field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")))

    # Database
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'file_archive.db'}"))

    # Storage Providers
    default_storage_provider: str = Field(default_factory=lambda: os.getenv("DEFAULT_STORAGE_PROVIDER", "local").lower())
    telegram_storage_channel_id: Optional[str] = Field(default_factory=lambda: os.getenv("TELEGRAM_STORAGE_CHANNEL_ID") or None)
    onedrive_root_folder: str = Field(default_factory=lambda: os.getenv("ONEDRIVE_ROOT_FOLDER", "ElantonyLibrary"))

    # AI Provider
    ai_provider: str = Field(default_factory=lambda: os.getenv("AI_PROVIDER", "rule_based").lower())
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None)
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    public_base_url: str = Field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "https://enhanced-eur-nutten-aggregate.trycloudflare.com"))

    # Paths
    base_dir: Path = BASE_DIR
    library_root: Path = Field(default_factory=lambda: Path(os.getenv("LIBRARY_ROOT", r"I:\2021\2020\✠ Cross Coptic Library ✠")))
    extracted_text_dir: Path = BASE_DIR / "extracted_text"
    processed_text_dir: Path = BASE_DIR / "processed_text"
    reports_dir: Path = BASE_DIR / "reports"
    logs_dir: Path = BASE_DIR / "logs"

    def __init__(self, **data):
        super().__init__(**data)
        # Parse user ID whitelists from comma-separated env strings
        raw_allowed = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").strip()
        if raw_allowed:
            self.allowed_telegram_user_ids = {
                int(uid.strip()) for uid in raw_allowed.split(",") if uid.strip().isdigit()
            }

        raw_admins = os.getenv("ADMIN_TELEGRAM_USER_IDS", "").strip()
        if raw_admins:
            self.admin_telegram_user_ids = {
                int(uid.strip()) for uid in raw_admins.split(",") if uid.strip().isdigit()
            }


# Singleton instance
settings = Settings()
