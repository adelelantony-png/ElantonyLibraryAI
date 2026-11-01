# -*- coding: utf-8 -*-
"""
Tests for ArchiveMaster ChurchAI Digital Text Extraction & Quality Engine
"""

import os
import sqlite3
import pytest
import fitz  # PyMuPDF
from pathlib import Path
from modules import digital_extractor, book_discovery, church_ai_config


def test_evaluate_text_quality_empty():
    res = digital_extractor.evaluate_text_quality("")
    assert res["status"] == "empty"
    assert res["quality_score"] == 0.0
    assert res["needs_ocr"] is True


def test_evaluate_text_quality_arabic():
    sample_arabic = (
        "مقدمة في علم اللاهوت المقارن وتاريخ المجامع المسكونية المقدسة "
        "بكنيسة الإسكندرية القبطية الأرثوذكسية تحت رعاية قداسة البابا شنودة الثالث."
    )
    res = digital_extractor.evaluate_text_quality(sample_arabic)
    assert res["status"] == "clean_digital"
    assert res["arabic_ratio"] > 0.7
    assert res["detected_language"] == "ara"
    assert res["needs_ocr"] is False
    assert res["quality_score"] >= 70.0


def test_evaluate_text_quality_coptic():
    sample_coptic = "Ⲟⲩⲭⲁⲓ ϧⲉⲛ ⲡϭⲟⲉⲓⲥ ⲛⲁⲥⲛⲏⲟⲩ ⲉⲑⲟⲩⲁⲃ ⲧⲏⲣⲟⲩ"
    res = digital_extractor.evaluate_text_quality(sample_coptic)
    assert res["coptic_ratio"] > 0.5
    assert res["detected_language"] == "cop"
    assert res["needs_ocr"] is False


def test_evaluate_text_quality_gibberish():
    sample_gibberish = "\uFFFD\uFFFD%^&*#!~???\uFFFD\uFFFD??###;;;;---++=="
    res = digital_extractor.evaluate_text_quality(sample_gibberish)
    assert res["status"] == "gibberish_font_error"
    assert res["needs_ocr"] is True
    assert res["quality_score"] < 40.0


def test_extract_digital_book_and_db_update(tmp_path):
    # 1. Create a synthetic test PDF with 2 pages
    pdf_path = tmp_path / "church_test_volume.pdf"
    doc = fitz.open()

    # Page 1: Digital Text
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Orthodox Patristic Theological Library Volume 1 - Church History and Ecclesiastical Studies.")

    # Page 2: Blank page (needs OCR or empty)
    p2 = doc.new_page()
    # No text on page 2

    doc.save(str(pdf_path))
    doc.close()

    # 2. Setup temporary DB and catalog the book
    db_path = tmp_path / "test_catalog.db"
    book_discovery.init_catalog_schema(str(db_path))

    sha256 = book_discovery.compute_sha256(str(pdf_path))
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO church_books (sha256, original_path, file_name, file_size, page_count)
        VALUES (?, ?, ?, ?, ?)
    """, (sha256, str(pdf_path), "church_test_volume.pdf", os.path.getsize(str(pdf_path)), 2))
    conn.commit()
    conn.close()

    # 3. Run digital extraction
    extracted_dir = tmp_path / "extracted_text"
    cfg = church_ai_config.load_config()
    cfg["paths"]["extracted_text"] = str(extracted_dir)

    result = digital_extractor.extract_digital_book(
        str(pdf_path),
        sha256=sha256,
        output_dir=str(extracted_dir),
        config=cfg
    )

    assert result["success"] is True
    assert result["page_count"] == 2
    assert result["digital_pages_count"] == 1
    assert 2 in result["pages_needing_ocr"]
    assert result["has_digital_text"] == 1
    assert result["extraction_status"] == "partial"

    # Verify extracted text file on disk
    text_file = extracted_dir / f"{sha256}.txt"
    assert text_file.exists()
    content = text_file.read_text(encoding="utf-8")
    assert "--- [صفحة 1 / Page 1] ---" in content
    assert "--- [صفحة 2 / Page 2] ---" in content
    assert "Orthodox Patristic Theological Library" in content

    # 4. Update catalog DB
    digital_extractor.update_catalog_digital_status(result, db_path=str(db_path))

    # Verify DB record
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT has_digital_text, extraction_status, pages_needing_ocr, quality_score FROM church_books WHERE sha256 = ?", (sha256,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == 1  # has_digital_text
    assert row[1] == "partial"
    assert "[2]" in row[2]
    assert row[3] > 0.0
