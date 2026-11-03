# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Standalone Permanent Assistant Service
Auto-Ingestion Pipeline for New Church Books
Detects new PDFs, extracts text/OCR, performs ecclesiastical classification,
and indexes chunks into SQLite FTS5 in real-time.
"""

import sys
import os
import re
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import fitz  # PyMuPDF

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.core.text_cleaner import clean_theological_text
from elantony.database.connection import get_connection
from elantony.classifier.source_classifier import ChurchSourceClassifier
from elantony.ocr.advanced_ocr import ArabicOcrPostProcessor


def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash in 64KB blocks."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def wait_for_file_stability(filepath: Path, timeout: float = 10.0, check_interval: float = 1.0) -> bool:
    """
    Ensures a newly created file is completely written (e.g., from browser download or file copy).
    Returns True when file size remains stable and is readable.
    """
    start_time = time.time()
    last_size = -1

    while time.time() - start_time < timeout:
        try:
            if not filepath.exists():
                time.sleep(check_interval)
                continue
            curr_size = filepath.stat().st_size
            if curr_size > 0 and curr_size == last_size:
                # Test opening file for reading
                with open(filepath, "rb") as f:
                    _ = f.read(1024)
                return True
            last_size = curr_size
        except (PermissionError, OSError):
            pass
        time.sleep(check_interval)

    return filepath.exists() and filepath.stat().st_size > 0


class LibraryAutoIngestor:
    """Automated ingestion pipeline for incoming church books."""

    def __init__(self):
        self.classifier = ChurchSourceClassifier()
        self.ocr_processor = ArabicOcrPostProcessor()

    def is_book_indexed(self, sha256: str) -> bool:
        """Checks if book already exists and is indexed in database."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM church_books WHERE sha256 = ?", (sha256,))
        row = cur.fetchone()
        conn.close()
        return bool(row)

    def ingest_pdf(self, pdf_path: Path, forced: bool = False) -> Dict[str, Any]:
        """
        Full autonomous ingestion of a PDF book into ELANTONY LIBRARY AI:
        1. Stability check & SHA-256 calculation.
        2. Check for duplicate/existing record.
        3. Digital text extraction (or OCR fallback for scanned books).
        4. Ecclesiastical classification (Patristic, Theological, Liturgical, History).
        5. FTS5 full-text indexing & disk storage.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
            return {"success": False, "error": f"الملف غير صالح أو غير موجود: {pdf_path}"}

        # Wait until write operations finish
        if not wait_for_file_stability(pdf_path):
            return {"success": False, "error": f"الملف قيد الاستخدام أو لم يكتمل نسخه: {pdf_path.name}"}

        file_size = pdf_path.stat().st_size
        mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pdf_path.stat().st_mtime))
        sha256 = compute_file_sha256(pdf_path)

        if not forced and self.is_book_indexed(sha256):
            logger.info(f"Book already indexed in library: {pdf_path.name} (SHA: {sha256[:16]})")
            return {
                "success": True,
                "status": "already_indexed",
                "sha256": sha256,
                "file_name": pdf_path.name,
                "message": "الكتاب موجود بالفعل ومفهرس مسبقاً بالمكتبة"
            }

        logger.info(f"Starting auto-ingestion for new church book: «{pdf_path.name}» (Size: {file_size / (1024*1024):.1f} MB)")

        # 1. Text Extraction via PyMuPDF
        pages_data: List[Dict[str, Any]] = []
        sample_texts: List[str] = []
        is_digital = False

        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            for page_idx in range(page_count):
                page_num = page_idx + 1
                page = doc.load_page(page_idx)
                raw_page_text = page.get_text("text") or ""
                cleaned_page_text = self.ocr_processor.normalize_arabic_for_search(raw_page_text)

                if len(cleaned_page_text.strip()) > 30:
                    is_digital = True

                printed_page = self.ocr_processor.extract_printed_page_number(raw_page_text, page_num)
                pages_data.append({
                    "page_num": page_num,
                    "printed_page": printed_page,
                    "text": cleaned_page_text
                })

                if page_idx < 10 and cleaned_page_text.strip():
                    sample_texts.append(cleaned_page_text[:400])

            doc.close()
        except Exception as e:
            logger.error(f"Error extracting PDF pages from {pdf_path.name}: {e}")
            return {"success": False, "error": f"فشل فتح ملف الـ PDF: {e}"}

        # 2. Ecclesiastical Classification
        sample_context = " ".join(sample_texts)
        classification = self.classifier.classify_book(
            file_name=pdf_path.name,
            folder_category=pdf_path.parent.name,
            author=None,
            text_sample=sample_context
        )

        source_types = classification["source_types"]
        authenticity_tier = classification["authenticity_tier"]
        matched_fathers = ", ".join(classification["matched_patristic_fathers"])
        clean_title = pdf_path.stem

        # Guess author from matched fathers or classification
        author = "غير محدد"
        if classification["matched_patristic_fathers"]:
            author = classification["matched_patristic_fathers"][0]
        elif "شنودة" in pdf_path.name:
            author = "قداسة البابا شنودة الثالث"
        elif "متى المسكين" in pdf_path.name:
            author = "الأب متى المسكين"
        elif "تادرس يعقوب" in pdf_path.name:
            author = "القمص تادرس يعقوب ملطي"

        # 3. Save extracted text to disk
        txt_path = settings.extracted_text_dir / f"{sha256}.txt"
        settings.extracted_text_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                for p in pages_data:
                    f.write(f"--- [صفحة {p['page_num']} | Page {p['page_num']}] ---\n")
                    f.write(p["text"] + "\n\n")
        except Exception as txt_err:
            logger.warning(f"Failed to write extracted text file: {txt_err}")

        # 4. Chunking for FTS5
        chunks_to_insert: List[Tuple[str, str, int, int, str, str]] = []
        chunk_idx = 0

        for p in pages_data:
            p_num = p["page_num"]
            p_printed = p["printed_page"]
            text = p["text"].strip()
            if len(text) < 25:
                continue

            page_label = f"صـ {p_printed} (مطبوعة)" if p_printed != p_num else f"صـ {p_num}"
            source_ref = f"كتاب: «{clean_title}»، {page_label}"

            # Split large pages into ~1000 char chunks with slight overlap
            if len(text) > 1200:
                paragraphs = re.split(r'\n\s*\n', text)
                cur_block = []
                cur_len = 0
                for para in paragraphs:
                    cur_block.append(para)
                    cur_len += len(para)
                    if cur_len >= 800:
                        chunk_text = "\n".join(cur_block)
                        chunks_to_insert.append((sha256, clean_title, p_num, chunk_idx, source_ref, chunk_text))
                        chunk_idx += 1
                        cur_block = []
                        cur_len = 0
                if cur_block:
                    chunks_to_insert.append((sha256, clean_title, p_num, chunk_idx, source_ref, "\n".join(cur_block)))
                    chunk_idx += 1
            else:
                chunks_to_insert.append((sha256, clean_title, p_num, chunk_idx, source_ref, text))
                chunk_idx += 1

        # 5. Insert into SQLite Database with WAL transaction
        conn = get_connection()
        cur = conn.cursor()

        try:
            # Insert or replace in church_books
            cur.execute("""
                INSERT OR REPLACE INTO church_books (
                    sha256, original_path, file_name, file_size, mod_time, page_count,
                    author, category, language_detected, file_format, storage_provider,
                    extraction_status, ocr_status, indexing_status, has_digital_text,
                    source_types, authenticity_tier, classification_confidence, matched_fathers, needs_review,
                    extracted_text_path, last_processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                sha256,
                str(pdf_path),
                pdf_path.name,
                file_size,
                mod_time,
                page_count,
                author,
                pdf_path.parent.name,
                "ara",
                "pdf",
                "local",
                "completed",
                "none" if is_digital else "needed",
                "indexed",
                1 if is_digital else 0,
                json.dumps(source_types, ensure_ascii=False),
                authenticity_tier,
                classification["confidence_score"],
                matched_fathers,
                1 if classification["needs_review"] else 0,
                str(txt_path)
            ))

            # Delete old chunks if any and insert new chunks into FTS5
            cur.execute("DELETE FROM church_chunks_fts WHERE sha256 = ?", (sha256,))
            if chunks_to_insert:
                cur.executemany("""
                    INSERT INTO church_chunks_fts (sha256, book_title, page_number, chunk_index, source_reference, chunk_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, chunks_to_insert)

            conn.commit()
            logger.info(f"Book auto-ingested successfully: «{pdf_path.name}» | +{len(chunks_to_insert)} FTS5 chunks | Tier: {authenticity_tier}")

        except Exception as db_err:
            conn.rollback()
            logger.error(f"Database error during auto-ingestion of {pdf_path.name}: {db_err}")
            return {"success": False, "error": f"خطأ في قاعدة البيانات: {db_err}"}
        finally:
            conn.close()

        return {
            "success": True,
            "status": "ingested",
            "sha256": sha256,
            "file_name": pdf_path.name,
            "title": clean_title,
            "author": author,
            "pages": page_count,
            "chunks_count": len(chunks_to_insert),
            "authenticity_tier": authenticity_tier,
            "source_types": source_types,
            "is_digital": is_digital
        }


# Global singleton instance
auto_ingestor = LibraryAutoIngestor()
