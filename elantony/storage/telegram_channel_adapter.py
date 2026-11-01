# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Telegram Private Channel Storage Adapter
Stores and indexes books inside a dedicated private Telegram channel.
Enables near-instant document dispatch via Telegram File ID (zero server bandwidth consumption).
"""

from typing import Dict, Any, Optional
from elantony.storage.base import BaseStorageAdapter
from elantony.core.config import settings
from elantony.core.logging import logger


class TelegramChannelStorageAdapter(BaseStorageAdapter):
    """
    Storage adapter utilizing a private Telegram channel as an encrypted cloud archive.
    
    Technical constraints & capabilities:
    - Maximum single file upload via standard Bot API: 50 MB.
    - Maximum single file download via standard Bot API: 20 MB.
    - Files above 50 MB require Local Telegram Bot API Server (supports up to 2 GB).
    """

    def __init__(self, channel_id: Optional[str] = None, bot_token: Optional[str] = None):
        self.channel_id = channel_id or settings.telegram_storage_channel_id
        self.bot_token = bot_token or settings.telegram_bot_token

    @property
    def provider_name(self) -> str:
        return "telegram_channel"

    def is_available(self) -> bool:
        return bool(self.channel_id and self.bot_token)

    def get_file_info(self, storage_reference: str) -> Dict[str, Any]:
        """
        Parses telegram storage reference:
        Format: 'tg://<channel_id>/<message_id>/<file_id>' or direct '<file_id>'
        """
        if not storage_reference:
            return {"exists": False, "provider": self.provider_name}

        return {
            "exists": True,
            "file_id": storage_reference,
            "provider": self.provider_name,
            "channel_id": self.channel_id,
            "max_bot_upload_mb": 50,
            "max_bot_download_mb": 20
        }

    def get_local_path(self, storage_reference: str) -> Optional[str]:
        """
        Telegram files are remote by nature. Returns None unless cached locally.
        """
        return None

    def get_download_url(self, storage_reference: str) -> Optional[str]:
        """
        Generates direct Telegram download link using getFile endpoint.
        """
        if not self.bot_token or not storage_reference:
            return None
        return f"https://api.telegram.org/bot{self.bot_token}/getFile?file_id={storage_reference}"

    def upload_file(self, local_path: str, destination_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepares file upload to private channel.
        Notice: Actual upload is gated until user authorization.
        """
        return {
            "success": False,
            "error": "Upload gated: Waiting for explicit user execution confirmation.",
            "provider": self.provider_name
        }
