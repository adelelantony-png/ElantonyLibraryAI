# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Standalone Permanent Assistant Service
Live Directory Watcher
Monitors library root folder on drive I: for newly added PDFs,
debounces file events, and routes new files through the auto-ingestion pipeline.
"""

import sys
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, Set, Dict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileMovedEvent

from elantony.core.logging import logger
from services.permanent_assistant.ingestion_pipeline import auto_ingestor

# Default Library Physical Storage Path
DEFAULT_WATCH_PATH = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠")


class LibraryFileEventHandler(FileSystemEventHandler):
    """Handles real-time file creation and modification events with smart debouncing."""

    def __init__(self, on_book_ingested: Optional[Callable[[Dict], None]] = None):
        super().__init__()
        self.on_book_ingested = on_book_ingested
        self._pending_files: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _is_valid_church_pdf(self, path_str: str) -> bool:
        """Filters out non-PDFs, temporary browser downloads, and lock files."""
        p = Path(path_str)
        if p.suffix.lower() != ".pdf":
            return False
        fname = p.name
        if fname.startswith("~") or fname.startswith(".") or ".tmp" in fname.lower() or ".crdownload" in fname.lower():
            return False
        return True

    def on_created(self, event):
        if not event.is_directory and self._is_valid_church_pdf(event.src_path):
            with self._lock:
                self._pending_files[event.src_path] = time.time()
                logger.debug(f"[Watcher] New PDF detected: {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory and self._is_valid_church_pdf(event.src_path):
            with self._lock:
                self._pending_files[event.src_path] = time.time()

    def on_moved(self, event):
        if not event.is_directory and self._is_valid_church_pdf(event.dest_path):
            with self._lock:
                self._pending_files[event.dest_path] = time.time()
                logger.debug(f"[Watcher] Moved PDF detected: {event.dest_path}")

    def _process_queue(self):
        """Worker loop that processes files after a 3-second write-settling debounce window."""
        while self._running:
            time.sleep(1.0)
            ready_files = []
            now = time.time()

            with self._lock:
                for path_str, detected_at in list(self._pending_files.items()):
                    # Wait 3 seconds of silence after last write event
                    if now - detected_at >= 3.0:
                        ready_files.append(path_str)
                        del self._pending_files[path_str]

            for path_str in ready_files:
                p = Path(path_str)
                if not p.exists():
                    continue

                logger.info(f"⚡ [Auto-Ingest] Processing newly detected book: «{p.name}»")
                try:
                    result = auto_ingestor.ingest_pdf(p)
                    if result.get("success") and result.get("status") == "ingested":
                        logger.info(f"🎉 [Auto-Ingest Complete] «{p.name}» added to library ({result.get('chunks_count')} chunks, Tier {result.get('authenticity_tier')})")
                        if self.on_book_ingested:
                            try:
                                self.on_book_ingested(result)
                            except Exception as cb_err:
                                logger.warning(f"Callback error after book ingestion: {cb_err}")
                except Exception as err:
                    logger.error(f"Error during automated ingestion of {p.name}: {err}")

    def stop(self):
        self._running = False


class LibraryLiveWatcher:
    """Manages the background filesystem observer for the church library."""

    def __init__(self, watch_directory: Optional[Path] = None, on_book_ingested: Optional[Callable[[Dict], None]] = None):
        self.watch_directory = watch_directory or DEFAULT_WATCH_PATH
        self.on_book_ingested = on_book_ingested
        self.observer: Optional[Observer] = None
        self.handler: Optional[LibraryFileEventHandler] = None

    def start(self):
        """Starts real-time monitoring."""
        if not self.watch_directory.exists():
            logger.warning(f"Watch directory does not exist: {self.watch_directory}. Watcher will retry.")
            return False

        self.handler = LibraryFileEventHandler(on_book_ingested=self.on_book_ingested)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_directory), recursive=True)
        self.observer.start()
        logger.info(f"👁️ Library Live Watcher started on: {self.watch_directory}")
        return True

    def stop(self):
        """Stops real-time monitoring."""
        if self.handler:
            self.handler.stop()
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Library Live Watcher stopped.")


# Singleton helper
watcher = LibraryLiveWatcher()
