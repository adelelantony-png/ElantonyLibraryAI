# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Local RAG Preparation & Semantic Chunker
Splits extracted church texts into paragraph-aware chunks with ecclesiastical citations,
page tracking, JSONL serialization, and local SQLite FTS5 indexing.
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator

from modules import church_ai_config, book_discovery

PAGE_MARKER_REGEX = re.compile(r'^---\s*\[(?:صفحة|Page)\s+(\d+)\s*(?:/|\|)\s*(?:Page|صفحة)\s+\d+\]\s*---$', re.MULTILINE)


def parse_pages_from_extracted_text(text: str) -> List[Dict[str, Any]]:
    """
    Parses extracted text file into separate pages based on standard page markers.
    Returns a list of dicts: [{'page_num': 1, 'text': '...'}]
    """
    pages: List[Dict[str, Any]] = []
    splits = list(PAGE_MARKER_REGEX.finditer(text))

    if not splits:
        # No standard markers found, treat as single page 1
        return [{"page_num": 1, "text": text.strip()}]

    for i in range(len(splits)):
        m = splits[i]
        page_num = int(m.group(1))
        start_idx = m.end()
        end_idx = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        page_content = text[start_idx:end_idx].strip()
        pages.append({
            "page_num": page_num,
            "text": page_content
        })

    return pages


def split_text_into_semantic_chunks(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 150
) -> List[str]:
    """
    Splits text into chunks respecting paragraph and sentence boundaries.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # First split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for para in paragraphs:
        p = para.strip()
        if not p:
            continue

        p_len = len(p)
        if current_len + p_len + 2 <= chunk_size:
            current_chunk.append(p)
            current_len += p_len + 2
        else:
            if current_chunk:
                joined = "\n\n".join(current_chunk)
                chunks.append(joined)
                # Overlap: keep last paragraph if it fits within overlap
                if len(current_chunk[-1]) <= chunk_overlap:
                    current_chunk = [current_chunk[-1], p]
                    current_len = len(current_chunk[0]) + p_len + 2
                else:
                    current_chunk = [p]
                    current_len = p_len
            else:
                # Single paragraph exceeds chunk_size, split by sentences
                sentences = re.split(r'(?<=[.،؛؟\n])\s+', p)
                sub_chunk: List[str] = []
                sub_len = 0
                for sent in sentences:
                    if sub_len + len(sent) + 1 <= chunk_size:
                        sub_chunk.append(sent)
                        sub_len += len(sent) + 1
                    else:
                        if sub_chunk:
                            chunks.append(" ".join(sub_chunk))
                        sub_chunk = [sent]
                        sub_len = len(sent)
                if sub_chunk:
                    current_chunk = [" ".join(sub_chunk)]
                    current_len = sub_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def init_rag_fts_schema(db_path: Optional[str] = None) -> None:
    """Initializes FTS5 table for lightning fast local semantic search."""
    target_db = db_path or book_discovery.get_db_path()
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS church_chunks_fts USING fts5(
            sha256 UNINDEXED,
            book_title,
            page_number UNINDEXED,
            chunk_index UNINDEXED,
            source_reference,
            chunk_text,
            tokenize = 'unicode61'
        )
    """)
    conn.commit()
    conn.close()


def process_book_for_rag(
    sha256: str,
    config: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Loads extracted text for a book, chunks it by page and paragraph,
    writes processed JSONL, indexes in SQLite FTS5, and updates church_books.
    """
    cfg = config or church_ai_config.load_config()
    target_db = db_path or book_discovery.get_db_path()
    init_rag_fts_schema(target_db)

    extracted_dir = Path(cfg["paths"]["extracted_text"])
    processed_dir = Path(cfg["paths"]["processed_text"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    text_file = extracted_dir / f"{sha256}.txt"
    if not text_file.exists():
        return {
            "success": False,
            "error": f"Extracted text file not found for SHA256: {sha256}",
            "sha256": sha256
        }

    # Fetch book metadata
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("SELECT file_name, original_path FROM church_books WHERE sha256 = ?", (sha256,))
    row = cur.fetchone()
    conn.close()

    file_name = row[0] if row else "مرجع كنسي"
    clean_title = Path(file_name).stem

    with open(text_file, "r", encoding="utf-8") as f:
        full_text = f.read()

    pages = parse_pages_from_extracted_text(full_text)
    chunk_size = cfg.get("rag", {}).get("chunk_size_chars", 1200)
    chunk_overlap = cfg.get("rag", {}).get("chunk_overlap_chars", 150)

    chunks_data: List[Dict[str, Any]] = []
    global_chunk_idx = 0

    for page in pages:
        pnum = page["page_num"]
        ptext = page["text"]
        # Skip OCR placeholder texts
        if not ptext or "[صفحة تحتاج إلى استخراج ضوئي" in ptext:
            continue

        page_chunks = split_text_into_semantic_chunks(ptext, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for ctext in page_chunks:
            source_ref = f"[كتاب: {clean_title}، ص: {pnum}]"
            chunks_data.append({
                "sha256": sha256,
                "book_title": clean_title,
                "page_number": pnum,
                "chunk_index": global_chunk_idx,
                "source_reference": source_ref,
                "chunk_text": ctext
            })
            global_chunk_idx += 1

    # Save to JSONL
    out_jsonl = processed_dir / f"{sha256}_chunks.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for c in chunks_data:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Index in SQLite FTS5 (first clean previous index for this book if any)
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("DELETE FROM church_chunks_fts WHERE sha256 = ?", (sha256,))
    if chunks_data:
        cur.executemany("""
            INSERT INTO church_chunks_fts (sha256, book_title, page_number, chunk_index, source_reference, chunk_text)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (c["sha256"], c["book_title"], c["page_number"], c["chunk_index"], c["source_reference"], c["chunk_text"])
            for c in chunks_data
        ])

    # Update church_books
    cur.execute("""
        UPDATE church_books
        SET processed_text_path = ?,
            last_processed_at = CURRENT_TIMESTAMP
        WHERE sha256 = ?
    """, (str(out_jsonl), sha256))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "sha256": sha256,
        "chunks_count": len(chunks_data),
        "jsonl_path": str(out_jsonl),
        "title": clean_title
    }


def search_church_rag(
    query: str,
    limit: int = 10,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Performs fast FTS5 search across all indexed chunks in the church library.
    """
    target_db = db_path or book_discovery.get_db_path()
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()

    # Clean query for FTS5 syntax
    clean_q = re.sub(r'[\'"]', '', query).strip()
    if not clean_q:
        conn.close()
        return []

    # Safe FTS5 phrase or token search
    try:
        cur.execute("""
            SELECT sha256, book_title, page_number, source_reference, chunk_text, rank
            FROM church_chunks_fts
            WHERE church_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (f'"{clean_q}"' if ' ' in clean_q else f'{clean_q}*', limit))
        rows = cur.fetchall()
    except Exception:
        # Fallback to simple query if special characters conflict with FTS5
        cur.execute("""
            SELECT sha256, book_title, page_number, source_reference, chunk_text, 0.0
            FROM church_chunks_fts
            WHERE chunk_text LIKE ?
            LIMIT ?
        """, (f"%{clean_q}%", limit))
        rows = cur.fetchall()

    conn.close()

    results = []
    for r in rows:
        results.append({
            "sha256": r[0],
            "book_title": r[1],
            "page_number": r[2],
            "source_reference": r[3],
            "chunk_text": r[4],
            "rank": round(float(r[5]), 3)
        })

    return results
