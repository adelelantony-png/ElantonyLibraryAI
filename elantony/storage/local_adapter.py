# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Local Storage Adapter
Handles reading and managing books residing on local disk volumes.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from elantony.storage.base import BaseStorageAdapter
from elantony.core.logging import logger


class LocalStorageAdapter(BaseStorageAdapter):
    """Local filesystem storage adapter."""

    @property
    def provider_name(self) -> str:
        return "local"

    def is_available(self) -> bool:
        return True

    def get_file_info(self, storage_reference: str) -> Dict[str, Any]:
        p = Path(storage_reference)
        if p.exists() and p.is_file():
            stat = p.stat()
            return {
                "exists": True,
                "file_name": p.name,
                "file_size": stat.st_size,
                "mime_type": "application/pdf" if p.suffix.lower() == ".pdf" else "application/octet-stream",
                "provider": self.provider_name,
                "local_path": str(p.resolve())
            }
        return {
            "exists": False,
            "file_name": p.name if storage_reference else "unknown",
            "file_size": 0,
            "mime_type": None,
            "provider": self.provider_name,
            "local_path": None
        }

    def get_local_path(self, storage_reference: str) -> Optional[str]:
        p = Path(storage_reference)
        return str(p.resolve()) if p.exists() and p.is_file() else None

    def get_download_url(self, storage_reference: str) -> Optional[str]:
        # Local files do not have public web URLs without web server routing
        return None

    def upload_file(self, local_path: str, destination_name: Optional[str] = None) -> Dict[str, Any]:
        p = Path(local_path)
        if not p.exists():
            return {"success": False, "error": "Source file does not exist", "provider": self.provider_name}

        return {
            "success": True,
            "storage_reference": str(p.resolve()),
            "file_size": p.stat().st_size,
            "provider": self.provider_name
        }
