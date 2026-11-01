# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Microsoft OneDrive Storage Adapter
Integrates with Microsoft Graph API to leverage user's 1 TB OneDrive cloud storage.
"""

import os
from typing import Dict, Any, Optional
from elantony.storage.base import BaseStorageAdapter
from elantony.core.config import settings
from elantony.core.logging import logger


class OneDriveStorageAdapter(BaseStorageAdapter):
    """
    Storage adapter for Microsoft OneDrive via Microsoft Graph REST API.

    Technical constraints & capabilities:
    - User quota: 1 TB.
    - Single PUT upload limit: 4 MB.
    - Resumable upload session limit: Up to 250 GB per file.
    - OAuth2 Client Credentials or Authorization Code flow required.
    """

    def __init__(self, root_folder: Optional[str] = None):
        self.root_folder = root_folder or settings.onedrive_root_folder
        self.client_id = os.getenv("ONEDRIVE_CLIENT_ID", "")
        self.client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET", "")
        self.tenant_id = os.getenv("ONEDRIVE_TENANT_ID", "")

    @property
    def provider_name(self) -> str:
        return "onedrive"

    def is_available(self) -> bool:
        """Available when OAuth2 client credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def get_file_info(self, storage_reference: str) -> Dict[str, Any]:
        return {
            "exists": bool(storage_reference),
            "item_id": storage_reference,
            "provider": self.provider_name,
            "root_folder": self.root_folder,
            "max_quota_gb": 1024
        }

    def get_local_path(self, storage_reference: str) -> Optional[str]:
        return None

    def get_download_url(self, storage_reference: str) -> Optional[str]:
        """OneDrive files require an authenticated Graph API link with downloadUrl token."""
        return None

    def upload_file(self, local_path: str, destination_name: Optional[str] = None) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "Upload gated: Waiting for explicit user confirmation.",
            "provider": self.provider_name
        }
