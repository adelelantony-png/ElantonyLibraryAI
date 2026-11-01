# -*- coding: utf-8 -*-
"""
Tests for ArchiveMaster ChurchAI Local RAG Preparation & Semantic Chunker
"""

import os
import json
import sqlite3
import pytest
from pathlib import Path
from modules import rag_chunker, book_discovery, church_ai_config


def test_parse_pages_from_extracted_text():
    sample_text = (
        "--- [صفحة 1 / Page 1] ---\n"
        "مقدمة في تاريخ كنيسة الإسكندرية والشهداء الأبرار.\n\n"
        "--- [صفحة 2 / Page 2] ---\n"
        "سيرة القديس أثناسيوس الرسولي حامي الإيمان الأرثوذكسي.\n"
    )
    pages = rag_chunker.parse_pages_from_extracted_text(sample_text)
    assert len(pages) == 2
    assert pages[0]["page_num"] == 1
    assert "مقدمة في تاريخ" in pages[0]["text"]
    assert pages[1]["page_num"] == 2
    assert "القديس أثناسيوس" in pages[1]["text"]


def test_split_text_into_semantic_chunks():
    para1 = "اللاهوت المقارن هو العلم الذي يبحث في الفروق العقائدية بين الكنائس المختلفة."
    para2 = "ويعتمد هذا العلم على نصوص الكتاب المقدس وأقوال الآباء الأولين والمجامع المسكونية."
    full_text = f"{para1}\n\n{para2}"

    chunks = rag_chunker.split_text_into_semantic_chunks(full_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 1
    assert any("اللاهوت المقارن" in c for c in chunks)


def test_process_book_for_rag_and_search(tmp_path):
    db_path = tmp_path / "test_rag.db"
    book_discovery.init_catalog_schema(str(db_path))

    sha = "test_sha_rag_12345"
    book_title = "تاريخ الكنيسة القبطية"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO church_books (sha256, original_path, file_name, file_size, page_count)
        VALUES (?, ?, ?, ?, ?)
    """, (sha, "C:/books/church_history.pdf", f"{book_title}.pdf", 50000, 2))
    conn.commit()
    conn.close()

    extracted_dir = tmp_path / "extracted_text"
    processed_dir = tmp_path / "processed_text"
    extracted_dir.mkdir(parents=True)

    text_file = extracted_dir / f"{sha}.txt"
    sample_content = (
        "--- [صفحة 1 / Page 1] ---\n"
        "تأسست الكنيسة في مصر على يد القديس مارمرقس الإنجيلي كاروز الديار المصرية.\n\n"
        "--- [صفحة 2 / Page 2] ---\n"
        "ومر الإيمان القبطي بعصور اضطهاد واستشهاد ناصعة في عهد دقلديانوس.\n"
    )
    text_file.write_text(sample_content, encoding="utf-8")

    cfg = church_ai_config.load_config()
    cfg["paths"]["extracted_text"] = str(extracted_dir)
    cfg["paths"]["processed_text"] = str(processed_dir)

    res = rag_chunker.process_book_for_rag(sha, config=cfg, db_path=str(db_path))
    assert res["success"] is True
    assert res["chunks_count"] == 2
    assert os.path.exists(res["jsonl_path"])

    # Verify JSONL lines
    lines = Path(res["jsonl_path"]).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    chunk0 = json.loads(lines[0])
    assert chunk0["sha256"] == sha
    assert chunk0["page_number"] == 1
    assert "[كتاب: تاريخ الكنيسة القبطية، ص: 1]" in chunk0["source_reference"]

    # Test FTS5 search
    search_res = rag_chunker.search_church_rag("مارمرقس", db_path=str(db_path))
    assert len(search_res) >= 1
    hit = search_res[0]
    assert hit["sha256"] == sha
    assert hit["page_number"] == 1
    assert "كاروز الديار المصرية" in hit["chunk_text"]
    assert "[كتاب: تاريخ الكنيسة القبطية، ص: 1]" in hit["source_reference"]
