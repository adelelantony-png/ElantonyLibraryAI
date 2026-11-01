# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Book Discovery & Catalog Engine
Recursively discovers, hashes, verifies, and catalogs PDF library books in SQLite.
"""

import os
import hashlib
import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional, Tuple

import fitz  # PyMuPDF
from modules import church_ai_config

def get_db_path() -> str:
    """Returns absolute path to the SQLite database."""
    cfg = church_ai_config.load_config()
    db_p = Path(cfg["paths"]["database"])
    if not db_p.is_absolute():
        db_p = church_ai_config.BASE_DIR / db_p
    return str(db_p)


def init_catalog_schema(db_path: Optional[str] = None) -> None:
    """Initializes the church_books schema in SQLite."""
    target_db = db_path or get_db_path()
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS church_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sha256 TEXT UNIQUE,
            original_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mod_time TEXT,
            page_count INTEGER DEFAULT 0,
            category TEXT DEFAULT 'عام',
            language_detected TEXT DEFAULT 'ara',
            extraction_status TEXT DEFAULT 'pending',
            has_digital_text INTEGER DEFAULT 0,
            pages_needing_ocr TEXT DEFAULT '[]',
            quality_score REAL DEFAULT 0.0,
            extracted_text_path TEXT,
            processed_text_path TEXT,
            is_duplicate_of TEXT,
            error_message TEXT,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_processed_at TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_status ON church_books(extraction_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_sha ON church_books(sha256)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_path ON church_books(original_path)")
    conn.commit()
    conn.close()


def compute_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 hash using chunked streaming to avoid memory overhead."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect_pdf_safety(file_path: str) -> Tuple[bool, int, Optional[str]]:
    """
    Safely probes a PDF file with PyMuPDF to extract page count and check integrity.
    Returns: (is_valid, page_count, error_message)
    """
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            # Check if empty password works
            if not doc.authenticate(""):
                doc.close()
                return False, 0, "الملف محمي بكلمة مرور ولا يمكن فتحه"
        page_count = len(doc)
        doc.close()
        return True, page_count, None
    except Exception as e:
        return False, 0, f"تلف في بنية PDF: {str(e)}"


def scan_directory(dir_path: str, recursive: bool = True) -> Generator[Dict[str, Any], None, None]:
    """Recursively yields candidate PDF file dictionaries using blazing fast os.walk."""
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return

    if recursive:
        for root, dirs, files in os.walk(dir_path):
            if "ArchiveMaster" in root or "_Duplicates" in root or "_System_Temp_Cache" in root:
                continue
            for f in files:
                if f.lower().endswith(".pdf"):
                    f_path = os.path.join(root, f)
                    try:
                        stat = os.stat(f_path)
                        yield {
                            "original_path": os.path.abspath(f_path),
                            "file_name": f,
                            "file_size": stat.st_size,
                            "mod_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        }
                    except Exception:
                        continue
    else:
        for f in os.listdir(dir_path):
            if f.lower().endswith(".pdf"):
                f_path = os.path.join(dir_path, f)
                if os.path.isfile(f_path):
                    try:
                        stat = os.stat(f_path)
                        yield {
                            "original_path": os.path.abspath(f_path),
                            "file_name": f,
                            "file_size": stat.st_size,
                            "mod_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        }
                    except Exception:
                        continue


def catalog_books(
    paths: List[str],
    recursive: bool = True,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scans paths, computes SHA-256, verifies PDFs, and records catalog into SQLite.
    Returns summary statistics.
    """
    target_db = db_path or get_db_path()
    init_catalog_schema(target_db)

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()

    stats = {
        "total_scanned": 0,
        "new_added": 0,
        "existing_unchanged": 0,
        "duplicates_detected": 0,
        "corrupted_files": 0
    }

    manifest_records = []

    for d in paths:
        for item in scan_directory(d, recursive=recursive):
            stats["total_scanned"] += 1
            f_path = item["original_path"]

            # Compute SHA-256
            try:
                file_hash = compute_sha256(f_path)
            except Exception as e:
                stats["corrupted_files"] += 1
                cur.execute("""
                    INSERT OR REPLACE INTO church_books 
                    (original_path, file_name, file_size, mod_time, extraction_status, error_message)
                    VALUES (?, ?, ?, ?, 'corrupted', ?)
                """, (f_path, item["file_name"], item["file_size"], item["mod_time"], f"تعذر قراءة الملف: {e}"))
                conn.commit()
                continue

            # Check if this SHA-256 already exists in DB
            cur.execute("SELECT id, original_path, extraction_status FROM church_books WHERE sha256 = ?", (file_hash,))
            existing = cur.fetchone()

            if existing:
                existing_id, existing_path, existing_status = existing
                if existing_path == f_path:
                    # Same book, same location -> unchanged
                    stats["existing_unchanged"] += 1
                    manifest_records.append({
                        "id": existing_id,
                        "sha256": file_hash,
                        "file_name": item["file_name"],
                        "path": f_path,
                        "status": existing_status
                    })
                    continue
                else:
                    # Same hash but different location -> duplicate!
                    stats["duplicates_detected"] += 1
                    cur.execute("""
                        INSERT OR IGNORE INTO church_books
                        (sha256, original_path, file_name, file_size, mod_time, extraction_status, is_duplicate_of)
                        VALUES (?, ?, ?, ?, ?, 'duplicate', ?)
                    """, (f"{file_hash}_dup_{stats['duplicates_detected']}", f_path, item["file_name"], item["file_size"], item["mod_time"], file_hash))
                    conn.commit()
                    continue

            # New Book: Probe PDF structure
            is_valid, page_count, err = inspect_pdf_safety(f_path)

            if not is_valid:
                stats["corrupted_files"] += 1
                status = "corrupted"
            else:
                stats["new_added"] += 1
                status = "pending"

            cur.execute("""
                INSERT INTO church_books 
                (sha256, original_path, file_name, file_size, mod_time, page_count, extraction_status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_hash, f_path, item["file_name"], item["file_size"], item["mod_time"], page_count, status, err))
            conn.commit()

            manifest_records.append({
                "sha256": file_hash,
                "file_name": item["file_name"],
                "path": f_path,
                "pages": page_count,
                "status": status,
                "error": err
            })

    conn.close()

    # Save manifest summary
    manifest_dir = church_ai_config.get_abs_path("reports")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "books_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "stats": stats, "sample": manifest_records[:50]}, f, indent=2, ensure_ascii=False)

    return stats
