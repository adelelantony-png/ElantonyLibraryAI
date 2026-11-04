# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Autonomous Telegram Channel Book Harvester (Phase 7 Integration)
Discovers, validates, downloads, deduplicates, and ingests Christian/Coptic
theological PDF books from target public channels into the master library.
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.database.repository import repo


# Verified Target Public Channels Catalog
TARGET_CHANNELS = [
    {
        "id": "christianlib",
        "username": "@christianlib",
        "name": "مكتبة الكتب المسيحية",
        "category": "مكتبة شاملة (آبائيات وعقيدة وتفاسير)",
        "priority": 1
    },
    {
        "id": "SenterDescoros",
        "username": "@SenterDescoros",
        "name": "مركز البابا ديسقورس للدراسات اللاهوتية",
        "category": "أبحاث لاهوتية كريستولوجية ومجامع مسكونية",
        "priority": 1
    },
    {
        "id": "coptic_treasures",
        "username": "@coptic_treasures",
        "name": "الكنوز القبطية",
        "category": "مخطوطات وكتب نادرة ودراسات تاريخية",
        "priority": 1
    },
    {
        "id": "khedmalibrary",
        "username": "@khedmalibrary",
        "name": "مكتبة الخادم الإلكترونية",
        "category": "كتب خدمية ومناهج دراسية",
        "priority": 2
    },
    {
        "id": "fateshoelkotb",
        "username": "@fateshoelkotb",
        "name": "فتشوا الكتب",
        "category": "أمهات الكتب والآبائيات",
        "priority": 2
    },
    {
        "id": "CHBookz",
        "username": "@CHBookz",
        "name": "كتب الكنيسة والآبائيات",
        "category": "نصوص ودراسات آبائية",
        "priority": 2
    }
]


class TelegramHarvesterService:
    """Orchestrates discovery and automated ingestion of Coptic books from Telegram."""

    def __init__(self):
        self.destination_dir = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\وارد_تليجرام")
        if not self.destination_dir.parent.exists():
            self.destination_dir = settings.base_dir / "books" / "telegram_harvest"
        self.destination_dir.mkdir(parents=True, exist_ok=True)

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Returns the registered channel catalog."""
        return TARGET_CHANNELS

    def calculate_sha256(self, file_path: Path) -> str:
        """Calculates file SHA-256 hash for deduplication."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def ingest_local_telegram_file(self, temp_path: Path, original_filename: str, source_channel: str = "@Telegram") -> Dict[str, Any]:
        """
        Deduplicates, moves, and ingests a book acquired from Telegram.
        """
        if not temp_path.exists():
            return {"success": False, "error": "الملف المؤقت غير موجود"}

        file_hash = self.calculate_sha256(temp_path)
        existing_book = repo.get_book_by_sha(file_hash)

        if existing_book:
            logger.info(f"[Harvester] Book already indexed: «{original_filename}» (SHA: {file_hash[:16]})")
            # Clean up temp file to avoid disk waste
            if temp_path != self.destination_dir / original_filename:
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return {
                "success": True,
                "already_exists": True,
                "title": existing_book.get("file_name", original_filename),
                "author": existing_book.get("author", "غير محدد"),
                "sha256": file_hash
            }

        # Safe unique filename
        dest_file = self.destination_dir / original_filename
        if dest_file.exists():
            dest_file = self.destination_dir / f"{temp_path.stem}_{file_hash[:8]}.pdf"

        try:
            import shutil
            shutil.move(str(temp_path), str(dest_file))
        except Exception as e:
            logger.error(f"[Harvester] Error moving file {temp_path} -> {dest_file}: {e}")
            return {"success": False, "error": str(e)}

        # Run automated ingestion pipeline
        try:
            from services.permanent_assistant.ingestion_pipeline import auto_ingestor
            res = auto_ingestor.ingest_pdf(dest_file)
            res["already_exists"] = False
            res["source_channel"] = source_channel
            res["saved_path"] = str(dest_file)
            logger.info(f"[Harvester] Successfully harvested & indexed: «{dest_file.name}»")
            return res
        except Exception as e:
            logger.error(f"[Harvester] Ingestion error on {dest_file}: {e}")
            return {"success": False, "error": str(e)}

    def get_harvested_stats(self) -> Dict[str, Any]:
        """Returns stats on harvested books on disk."""
        files = list(self.destination_dir.glob("*.pdf")) if self.destination_dir.exists() else []
        total_size = sum(f.stat().st_size for f in files)
        return {
            "total_books_harvested": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory": str(self.destination_dir)
        }


# Global harvester service instance
telegram_harvester = TelegramHarvesterService()
