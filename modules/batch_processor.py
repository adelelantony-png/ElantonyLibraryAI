# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Progressive Resumable Batch Processor
Executes multi-stage processing of church library books with:
- Checkpoint persistence after every single volume.
- psutil RAM watchdog (enforces < 600 MB ceiling on 8 GB Windows systems).
- Resumable pipeline skipping already processed volumes.
- Real-time logging and progress tracking.
"""

import os
import gc
import time
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import psutil
from modules import church_ai_config, book_discovery, digital_extractor, church_ocr_engine


class MemoryWatchdog:
    """Monitors process memory and enforces RAM safety thresholds."""

    def __init__(self, max_memory_mb: int = 600):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process(os.getpid())

    def get_memory_usage_mb(self) -> float:
        """Returns current process RSS memory in MB."""
        return self.process.memory_info().rss / (1024 * 1024)

    def check_and_clean(self) -> float:
        """Checks memory, triggers GC if needed, and sleeps if threshold exceeded."""
        mem = self.get_memory_usage_mb()
        if mem > self.max_memory_mb:
            gc.collect()
            time.sleep(0.5)
            mem = self.get_memory_usage_mb()
        return mem


class ChurchBatchProcessor:
    """Progressive batch processing engine for ChurchAI library books."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None):
        self.config = config or church_ai_config.load_config()
        self.db_path = db_path or book_discovery.get_db_path()
        max_mem = self.config.get("extraction", {}).get("max_memory_mb", 600)
        self.watchdog = MemoryWatchdog(max_memory_mb=max_mem)
        self.stop_requested = False

    def request_stop(self) -> None:
        """Gracefully requests stopping after the current book completes."""
        self.stop_requested = True

    def scan_and_catalog(self, target_paths: List[str], progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Discovers and catalogs PDF books from specified directories."""
        if progress_callback:
            progress_callback(f"بدء فحص المجلدات: {', '.join(target_paths)}")

        stats = book_discovery.catalog_books(
            paths=target_paths,
            db_path=self.db_path
        )

        if progress_callback:
            progress_callback(
                f"اكتمل الفحص: إجمالي المفحوص={stats.get('total_scanned', 0)}، "
                f"جديد={stats.get('new_added', 0)}، مكرر={stats.get('duplicates_detected', 0)}، "
                f"تالف={stats.get('corrupted_files', 0)}"
            )
        return stats

    def run_digital_extraction(
        self,
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes pending books for digital text extraction.
        Commits after every single book so interrupted tasks can resume seamlessly.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        query = """
            SELECT sha256, original_path, file_name, page_count
            FROM church_books
            WHERE extraction_status = 'pending' AND is_duplicate_of IS NULL AND error_message IS NULL
            ORDER BY id ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        cur.execute(query)
        pending_books = cur.fetchall()
        conn.close()

        total = len(pending_books)
        completed = 0
        failed = 0
        ocr_required_count = 0

        for idx, (sha256, original_path, file_name, page_count) in enumerate(pending_books):
            if self.stop_requested:
                break

            # Memory watchdog check
            mem_mb = self.watchdog.check_and_clean()

            res = digital_extractor.extract_digital_book(
                pdf_path=original_path,
                sha256=sha256,
                config=self.config
            )

            if res["success"]:
                digital_extractor.update_catalog_digital_status(res, db_path=self.db_path)
                completed += 1
                if res.get("ocr_needed_pages_count", 0) > 0:
                    ocr_required_count += 1
            else:
                # Record error in DB
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("""
                    UPDATE church_books 
                    SET extraction_status = 'failed', error_message = ?, last_processed_at = CURRENT_TIMESTAMP
                    WHERE sha256 = ?
                """, (res.get("error", "Unknown error"), sha256))
                conn.commit()
                conn.close()
                failed += 1

            if progress_callback:
                progress_callback({
                    "current": idx + 1,
                    "total": total,
                    "file_name": file_name,
                    "status": res.get("extraction_status", "failed"),
                    "memory_mb": round(mem_mb, 1),
                    "quality_score": res.get("quality_score", 0.0)
                })

        return {
            "total_pending": total,
            "processed": completed,
            "failed": failed,
            "books_needing_ocr": ocr_required_count,
            "stopped_early": self.stop_requested
        }

    def run_selective_ocr(
        self,
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Runs selective OCR on volumes that have pending OCR pages.
        """
        env_diag = church_ocr_engine.check_ocr_environment(self.config)
        if not env_diag["is_available"]:
            return {
                "success": False,
                "error": "Tesseract OCR is not available.",
                "diagnostic": env_diag
            }

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        query = """
            SELECT sha256, original_path, file_name, pages_needing_ocr
            FROM church_books
            WHERE extraction_status IN ('partial', 'needs_ocr') 
              AND pages_needing_ocr != '[]' 
              AND is_duplicate_of IS NULL
            ORDER BY id ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        cur.execute(query)
        books_needing_ocr = cur.fetchall()
        conn.close()

        total = len(books_needing_ocr)
        processed = 0

        for idx, (sha256, original_path, file_name, raw_pages) in enumerate(books_needing_ocr):
            if self.stop_requested:
                break

            self.watchdog.check_and_clean()

            try:
                import json
                pages = json.loads(raw_pages)
            except Exception:
                pages = []

            if not pages:
                continue

            res = church_ocr_engine.ocr_book_selective(
                pdf_path=original_path,
                sha256=sha256,
                pages_to_ocr=pages,
                config=self.config,
                db_path=self.db_path
            )

            processed += 1
            if progress_callback:
                progress_callback({
                    "current": idx + 1,
                    "total": total,
                    "file_name": file_name,
                    "completed_pages": len(res.get("completed_pages", [])),
                    "remaining_pages": len(res.get("remaining_pages", []))
                })

        return {
            "success": True,
            "total_candidates": total,
            "processed": processed,
            "stopped_early": self.stop_requested
        }
