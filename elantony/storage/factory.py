# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Storage Adapter Factory
"""

from typing import Dict, Optional
from elantony.storage.base import BaseStorageAdapter
from elantony.storage.local_adapter import LocalStorageAdapter
from elantony.storage.telegram_channel_adapter import TelegramChannelStorageAdapter
from elantony.storage.onedrive_adapter import OneDriveStorageAdapter
from elantony.storage.unlimcloud_adapter import UnlimCloudStorageAdapter
from elantony.core.config import settings

_adapters: Dict[str, BaseStorageAdapter] = {
    "local": LocalStorageAdapter(),
    "telegram": TelegramChannelStorageAdapter(),
    "telegram_channel": TelegramChannelStorageAdapter(),
    "onedrive": OneDriveStorageAdapter(),
    "unlimcloud": UnlimCloudStorageAdapter(),
}


def get_storage_adapter(provider_name: Optional[str] = None) -> BaseStorageAdapter:
    """Returns the requested or default configured storage adapter."""
    name = (provider_name or settings.default_storage_provider).lower()
    return _adapters.get(name, _adapters["local"])
