# -*- coding: utf-8 -*-
import os
import sqlite3
import tempfile
from pathlib import Path
import fitz
import pytest

from modules.book_discovery import (
    init_catalog_schema,
    compute_sha256,
    inspect_pdf_safety,
    catalog_books
)

@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_file = tmp_path / "test_books.db"
        books_dir = tmp_path / "كتب_قبطية_تجريبية"
        books_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create a clean digital PDF with Arabic text
        pdf1 = books_dir / "كتاب_تجسد_الكلمة.pdf"
        doc1 = fitz.open()
        p1 = doc1.new_page()
        p1.insert_text((50, 72), "القديس أثناسيوس الرسولي - تجسد الكلمة", fontname="helv", fontsize=12)
        doc1.save(str(pdf1))
        doc1.close()

        # 2. Create an identical duplicate in a subfolder
        sub_dir = books_dir / "مجلد_فرعي"
        sub_dir.mkdir(parents=True, exist_ok=True)
        pdf2 = sub_dir / "نسخة_مكررة_تجسد_الكلمة.pdf"
        pdf2.write_bytes(pdf1.read_bytes())

        # 3. Create a corrupted file
        pdf_corrupt = books_dir / "كتاب_تالف_معطوب.pdf"
        pdf_corrupt.write_bytes(b"%PDF-1.4 non-valid garbage bytes that cannot open")

        yield {
            "db_path": str(db_file),
            "books_dir": str(books_dir),
            "pdf1": str(pdf1),
            "pdf2": str(pdf2),
            "pdf_corrupt": str(pdf_corrupt)
        }


def test_schema_init(temp_env):
    db_p = temp_env["db_path"]
    init_catalog_schema(db_p)
    conn = sqlite3.connect(db_p)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='church_books'")
    assert cur.fetchone() is not None
    conn.close()


def test_compute_sha256(temp_env):
    h1 = compute_sha256(temp_env["pdf1"])
    h2 = compute_sha256(temp_env["pdf2"])
    assert len(h1) == 64
    assert h1 == h2  # identical content


def test_inspect_pdf_safety(temp_env):
    valid, pages, err = inspect_pdf_safety(temp_env["pdf1"])
    assert valid is True
    assert pages == 1
    assert err is None

    # Corrupt
    valid_c, pages_c, err_c = inspect_pdf_safety(temp_env["pdf_corrupt"])
    assert valid_c is False
    assert pages_c == 0
    assert err_c is not None


def test_catalog_discovery_and_duplicates(temp_env):
    db_p = temp_env["db_path"]
    b_dir = temp_env["books_dir"]

    stats = catalog_books([b_dir], recursive=True, db_path=db_p)

    assert stats["total_scanned"] == 3
    assert stats["new_added"] == 1  # 1 genuine valid book
    assert stats["duplicates_detected"] == 1  # 1 duplicate detected
    assert stats["corrupted_files"] == 1  # 1 corrupt detected

    # Verify SQLite rows
    conn = sqlite3.connect(db_p)
    cur = conn.cursor()
    cur.execute("SELECT file_name, extraction_status, is_duplicate_of FROM church_books")
    rows = cur.fetchall()
    conn.close()

    statuses = {r[1] for r in rows}
    assert "pending" in statuses
    assert "duplicate" in statuses
    assert "corrupted" in statuses
