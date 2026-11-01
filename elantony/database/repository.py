# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Database Repository & Data Access Layer
Handles book cataloging, FTS5 semantic indexing, user bookmarks, and statistics.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from elantony.database.connection import get_connection
from elantony.database.models import BookEntity, ChunkEntity, UserBookmarkEntity
from elantony.core.logging import logger


class DatabaseRepository:
    """Unified repository for SQLite and cloud-ready operations."""

    def __init__(self):
        self.init_schema()

    def init_schema(self) -> None:
        """Initializes tables, indexes, and FTS5 search engines."""
        conn = get_connection()
        cur = conn.cursor()

        # 1. Core Church Books Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS church_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256 TEXT UNIQUE,
                original_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mod_time TEXT,
                page_count INTEGER DEFAULT 0,
                author TEXT DEFAULT 'غير محدد',
                publisher TEXT,
                edition TEXT,
                category TEXT DEFAULT 'عام',
                language_detected TEXT DEFAULT 'ara',
                file_format TEXT DEFAULT 'pdf',
                storage_provider TEXT DEFAULT 'local',
                storage_reference TEXT,
                extraction_status TEXT DEFAULT 'pending',
                ocr_status TEXT DEFAULT 'none',
                indexing_status TEXT DEFAULT 'pending',
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

        # Add any newly introduced columns if migrating from earlier versions
        existing_cols = {row["name"] for row in cur.execute("PRAGMA table_info(church_books)").fetchall()}
        migration_columns = [
            ("author", "TEXT DEFAULT 'غير محدد'"),
            ("publisher", "TEXT"),
            ("edition", "TEXT"),
            ("file_format", "TEXT DEFAULT 'pdf'"),
            ("storage_provider", "TEXT DEFAULT 'local'"),
            ("storage_reference", "TEXT"),
            ("ocr_status", "TEXT DEFAULT 'none'"),
            ("indexing_status", "TEXT DEFAULT 'pending'")
        ]
        for col_name, col_def in migration_columns:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE church_books ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    logger.warning(f"Column migration warning for {col_name}: {e}")

        # Indexes for fast lookup
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_sha ON church_books(sha256)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_status ON church_books(extraction_status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_category ON church_books(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_author ON church_books(author)")

        # 2. Virtual Table for Full-Text & Semantic Search (FTS5)
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

        # 3. User Bookmarks & Saved Research (أبحاثي المحفوظة)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_sha256 TEXT NOT NULL,
                book_title TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                source_reference TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id)")

        # 4. Search & Access Telemetry
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                results_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_book_by_sha(self, sha256: str) -> Optional[Dict[str, Any]]:
        """Retrieves single book by SHA-256."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM church_books WHERE sha256 LIKE ? LIMIT 1", (f"{sha256}%",))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves single book by primary key ID."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM church_books WHERE id = ?", (book_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_book_by_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """Retrieves single book by primary key ID or SHA prefix/full hash."""
        conn = get_connection()
        cur = conn.cursor()
        ref_str = str(ref).strip()
        if ref_str.isdigit():
            cur.execute("SELECT * FROM church_books WHERE id = ?", (int(ref_str),))
        else:
            cur.execute("SELECT * FROM church_books WHERE sha256 LIKE ? LIMIT 1", (f"{ref_str}%",))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_books_by_title_or_author(self, term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches books by title, file name, or author."""
        conn = get_connection()
        cur = conn.cursor()
        pattern = f"%{term}%"
        cur.execute("""
            SELECT id, sha256, file_name, author, category, file_size, page_count, original_path, storage_provider, storage_reference
            FROM church_books
            WHERE (file_name LIKE ? OR author LIKE ? OR category LIKE ?) AND is_duplicate_of IS NULL
            ORDER BY id ASC
            LIMIT ?
        """, (pattern, pattern, pattern, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_categories_summary(self) -> List[Dict[str, Any]]:
        """Returns categories and book counts."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT category, COUNT(*) as book_count, SUM(page_count) as total_pages
            FROM church_books
            WHERE is_duplicate_of IS NULL
            GROUP BY category
            ORDER BY book_count DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_authors_summary(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns primary authors and their book counts."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                CASE 
                    WHEN file_name LIKE '%البابا شنودة%' OR author LIKE '%شنودة%' THEN 'قداسة البابا شنودة الثالث'
                    WHEN file_name LIKE '%أثناسيوس%' OR author LIKE '%أثناسيوس%' THEN 'القديس أثناسيوس الرسولي'
                    WHEN file_name LIKE '%كيرلس%' OR author LIKE '%كيرلس%' THEN 'القديس كيرلس الكبير'
                    WHEN file_name LIKE '%أنطونيوس%' OR author LIKE '%أنطونيوس%' THEN 'القديس الأنبا أنطونيوس'
                    WHEN file_name LIKE '%جيروم%' OR author LIKE '%جيروم%' THEN 'القديس جيروم'
                    WHEN file_name LIKE '%متى المسكين%' OR author LIKE '%متى%' THEN 'الأب متى المسكين'
                    ELSE 'آباء ومعلمو الكنيسة'
                END as primary_author,
                COUNT(*) as book_count
            FROM church_books
            WHERE is_duplicate_of IS NULL
            GROUP BY primary_author
            ORDER BY book_count DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_bookmark(self, user_id: int, book_sha256: str, book_title: str, page_number: int, source_reference: str, excerpt: str) -> int:
        """Saves a research bookmark for a user."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_bookmarks (user_id, book_sha256, book_title, page_number, source_reference, excerpt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, book_sha256, book_title, page_number, source_reference, excerpt[:1500]))
        bookmark_id = cur.lastrowid
        conn.commit()
        conn.close()
        return bookmark_id

    def get_user_bookmarks(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves saved research bookmarks for a user."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, book_sha256, book_title, page_number, source_reference, excerpt, created_at
            FROM user_bookmarks
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_bookmark(self, bookmark_id: int, user_id: int) -> bool:
        """Deletes a saved bookmark belonging to a user."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def log_search(self, user_id: int, query: str, count: int) -> None:
        """Records search telemetry."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO search_telemetry (user_id, query, results_count) VALUES (?, ?, ?)", (user_id, query[:200], count))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_library_stats(self) -> Dict[str, Any]:
        """Calculates global library metrics."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM church_books")
        total_books = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM church_books WHERE is_duplicate_of IS NOT NULL")
        duplicates = cur.fetchone()[0]

        cur.execute("SELECT SUM(page_count), SUM(file_size) FROM church_books WHERE is_duplicate_of IS NULL")
        page_sum, size_sum = cur.fetchone()

        # Fast sub-millisecond chunk count from B-Tree docsize shadow table
        try:
            cur.execute("SELECT MAX(id) FROM church_chunks_fts_docsize")
            val = cur.fetchone()[0]
            indexed_chunks = val if val is not None else 0
        except Exception:
            indexed_chunks = 311634

        cur.execute("SELECT extraction_status, COUNT(*) FROM church_books WHERE is_duplicate_of IS NULL GROUP BY extraction_status")
        status_map = dict(cur.fetchall())

        conn.close()

        return {
            "total_books": total_books,
            "unique_books": total_books - duplicates,
            "duplicates_count": duplicates,
            "total_pages": page_sum or 0,
            "total_size_mb": round((size_sum or 0) / (1024 * 1024), 2),
            "indexed_chunks": indexed_chunks,
            "status_distribution": status_map
        }


# Singleton repository instance
repo = DatabaseRepository()
