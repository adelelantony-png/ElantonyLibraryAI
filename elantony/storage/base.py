# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Storage Adapter Interface
Defines the abstract contract for multi-provider file storage.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class BaseStorageAdapter(ABC):
    """Abstract base class for all storage adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier of the storage provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the storage provider is configured and reachable."""
        pass

    @abstractmethod
    def get_file_info(self, storage_reference: str) -> Dict[str, Any]:
        """
        Retrieves file metadata from the storage provider.
        Returns dict with: exists, file_name, file_size, mime_type, and provider.
        """
        pass

    @abstractmethod
    def get_local_path(self, storage_reference: str) -> Optional[str]:
        """
        Returns a local filesystem path to the file.
        If stored in the cloud, streams/downloads to a local cache directory.
        """
        pass

    @abstractmethod
    def get_download_url(self, storage_reference: str) -> Optional[str]:
        """Returns direct or presigned URL for downloading the file, if supported."""
        pass

    @abstractmethod
    def upload_file(self, local_path: str, destination_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Uploads a local file to the storage provider.
        Returns dict with: success, storage_reference, file_size, provider.
        """
        pass
