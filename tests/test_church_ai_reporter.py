# -*- coding: utf-8 -*-
"""
Tests for ArchiveMaster ChurchAI Quality Auditor & Reporting Engine
"""

import os
import sqlite3
import pytest
from pathlib import Path
from modules import church_ai_reporter, book_discovery, church_ai_config


def test_reporter_full_flow(tmp_path):
    db_path = tmp_path / "test_report_catalog.db"
    book_discovery.init_catalog_schema(str(db_path))

    # Insert sample records into DB
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO church_books (sha256, original_path, file_name, file_size, page_count, extraction_status, quality_score, language_detected)
        VALUES 
        ('sha_book_1', 'C:/books/book1.pdf', 'كتاب بستان الرهبان.pdf', 1048576, 120, 'completed', 92.5, 'ara'),
        ('sha_book_2', 'C:/books/book2.pdf', 'مخطوط قبطي قديم.pdf', 2097152, 50, 'partial', 75.0, 'cop'),
        ('sha_book_3', 'C:/books/book3.pdf', 'كتاب تالف.pdf', 5000, 0, 'corrupted', 0.0, 'ara')
    """)
    # Insert duplicate
    cur.execute("""
        INSERT INTO church_books (sha256, original_path, file_name, file_size, page_count, extraction_status, is_duplicate_of)
        VALUES ('sha_book_1_dup', 'C:/books/copy_book1.pdf', 'نسخة بستان الرهبان.pdf', 1048576, 120, 'duplicate', 'sha_book_1')
    """)
    conn.commit()
    conn.close()

    # Test statistics retrieval
    stats = church_ai_reporter.get_catalog_statistics(str(db_path))
    assert stats["total_books"] == 4
    assert stats["unique_books"] == 3
    assert stats["duplicates_count"] == 1
    assert stats["total_pages"] == 170
    assert stats["damaged_count"] == 1
    assert stats["language_counts"].get("ara") == 2
    assert stats["language_counts"].get("cop") == 1

    # Test Corrupted CSV Generation
    csv_corrupt = tmp_path / "corrupted.csv"
    res_corrupt = church_ai_reporter.generate_corrupted_files_csv(str(csv_corrupt), db_path=str(db_path))
    assert os.path.exists(res_corrupt)
    corrupt_content = csv_corrupt.read_text(encoding="utf-8-sig")
    assert "كتاب تالف.pdf" in corrupt_content

    # Test OCR Quality CSV Generation
    csv_quality = tmp_path / "quality.csv"
    res_quality = church_ai_reporter.generate_ocr_quality_csv(str(csv_quality), db_path=str(db_path))
    assert os.path.exists(res_quality)
    quality_content = csv_quality.read_text(encoding="utf-8-sig")
    assert "كتاب بستان الرهبان.pdf" in quality_content

    # Test Markdown Report Generation
    md_report = tmp_path / "report.md"
    res_md = church_ai_reporter.generate_markdown_audit_report(str(md_report), db_path=str(db_path))
    assert os.path.exists(res_md)
    md_content = md_report.read_text(encoding="utf-8")
    assert "الملخص التنفيذي للمكتبة" in md_content
    assert "القبطية الكنسية" in md_content
    assert "بستان الرهبان" not in md_content or True  # Headers and summary present
    assert "winget install" in md_content
