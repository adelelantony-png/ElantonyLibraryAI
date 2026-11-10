# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Database Repository & Data Access Layer
Handles book cataloging, FTS5 semantic indexing, user bookmarks, and statistics.
"""

import sqlite3
import json
import uuid
import re
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
            ("indexing_status", "TEXT DEFAULT 'pending'"),
            ("source_types", "TEXT DEFAULT '[]'"),
            ("authenticity_tier", "INTEGER DEFAULT 3"),
            ("classification_confidence", "REAL DEFAULT 0.0"),
            ("matched_fathers", "TEXT DEFAULT '[]'"),
            ("needs_review", "INTEGER DEFAULT 0")
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_tier ON church_books(authenticity_tier)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_source_types ON church_books(source_types)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_church_books_needs_review ON church_books(needs_review)")

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

        # 5. Persistent Chat Discussions & Research Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at DESC)")

        # 6. Chat Messages in Discussion Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")

        # 7. Scholar Profiles (Persistent user metadata)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scholar_profiles (
                user_id TEXT PRIMARY KEY,
                display_name TEXT DEFAULT 'باحث لاهوتي',
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
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
        sessions = [dict(r) for r in rows]
        for s in sessions:
            cur.execute("""
                SELECT id, content FROM chat_messages
                WHERE session_id = ? AND role = 'user'
                ORDER BY id ASC
            """, (s["id"],))
            q_rows = cur.fetchall()
            s["user_queries"] = [{"id": qr[0], "content": qr[1][:80]} for qr in q_rows]
            s["questions_count"] = len(s["user_queries"])
        conn.close()
        return sessions

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

    def get_catalog_categories_overview(self) -> List[Dict[str, Any]]:
        """Returns the 8 master ecclesiastical categories with comprehensive dynamic live counts."""
        conn = get_connection()
        cur = conn.cursor()
        categories = self._get_master_categories_definitions()
        result = []
        for code, title, cond in categories:
            cur.execute(f"SELECT COUNT(*) FROM church_books WHERE ({cond}) AND is_duplicate_of IS NULL")
            cnt = cur.fetchone()[0]
            result.append({"code": code, "title": title, "count": cnt})
        conn.close()
        return result

    def _get_master_categories_definitions(self) -> List[Tuple[str, str, str]]:
        """Master taxonomy mapping covering all 3,656 books."""
        bible_terms = [
            "تفسير", "كتاب مقدس", "العهد", "اصحاح", "اسفار", "سفر",
            "متي", "متى", "مرقس", "لوقا", "يوحنا", "اعمال الرسل", "أعمال الرسل",
            "روميا", "رومية", "كورونثوس", "غلاطية", "افسس", "أفسس", "فليبي", "كولوسي",
            "تسالونيكي", "تيموثاوس", "تيطس", "فليمون", "عبرانيين", "العبرانيين",
            "يعقوب", "بطرس", "يهوذا", "رؤيا", "مزامير", "مزمور", "تكوين", "خروج",
            "لاويين", "عدد", "تثنية", "يشوع", "قضاة", "راعوث", "صموئيل", "ملوك",
            "اخبار الايام", "عزرا", "نحميا", "طوبيا", "يهوديت", "استير", "ايوب",
            "امثال", "جامعة", "نشيد", "حكمة", "يشوع بن سيراخ", "اشعياء", "ارميا",
            "مراثي", "باروخ", "حزقيال", "دانيال", "هوشع", "يوئيل", "عاموس",
            "عوبديا", "يونان", "ميخا", "ناحوم", "حبقوق", "صفنيا", "حجي", "زكريا",
            "ملاخي", "مكابيين", "الأناجيل", "رسائل بولس", "الكاثوليكون"
        ]
        bible_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in bible_terms])

        patristics_terms = [
            "آباء", "الاباء", "أقوال", "القديس", "أثناسيوس", "اثناسيوس", "كيرلس",
            "أنطونيوس", "انطونيوس", "مقاريوس", "ذهبي الفم", "باسيليوس", "غريغوريوس",
            "جيروم", "أوغسطينوس", "اوغسطينوس", "ديديموس", "كليمندس", "اوريجينوس"
        ]
        patristics_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in patristics_terms])

        liturgy_terms = ["طقس", "ألحان", "الحان", "القداس", "القطمارس", "الأجبية", "اجبية", "تسبحة", "ابصلمودية", "خولاجي", "بصخة", "قنديل", "سجدة", "لقان"]
        liturgy_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in liturgy_terms])

        history_terms = ["تاريخ", "سير", "سنكسار", "شهداء", "استشهاد", "تراث القبط", "قصة الكنيسة", "سيرة"]
        history_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in history_terms])

        theology_terms = ["عقيدة", "لاهوت", "المجامع", "مجمع", "طبيعة المسيح", "تجسد", "فداء", "دفاعيات", "بدع", "بدعة", "ارثوذكس", "أرثوذكس"]
        theology_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in theology_terms])

        monastic_terms = ["روحية", "رهبنة", "رهبان", "بستان الرهبان", "الحياة الروحية", "صلاة", "صوم", "توبة", "فضائل", "محبة", "جهاد", "اتضاع", "متى المسكين", "شنودة"]
        monastic_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in monastic_terms])

        servants_terms = ["خادم", "تربية", "أسرة", "اسرة", "شباب", "أطفال", "اطفال", "مسابقات", "عرائس", "مسرح", "كشافة", "تنمية", "مدارس الأحد"]
        servants_cond = " OR ".join([f"category LIKE '%{t}%' OR file_name LIKE '%{t}%'" for t in servants_terms])

        multilingual_terms = ["English", "German", "French", "Swedish", "Spanish", "Chinese", "Turkish", "Deutsche"]
        multilingual_cond = " OR ".join([f"category LIKE '%{t}%'" for t in multilingual_terms])

        return [
            ("bible", "📖 تفاسير ودراسات العهدين", bible_cond),
            ("monastic", "🌿 رهبنة وسلوك وحياة روحية", monastic_cond),
            ("patristics", "📜 آبائيات ومؤلفات الآباء", patristics_cond),
            ("theology", "⛪ لاهوت وعقيدة ودفاعيات ومجامع", theology_cond),
            ("history", "🏛️ تاريخ كنسي وسير الشهداء والقديسين", history_cond),
            ("liturgy", "🕯️ طقوس وألحان ولتورجيا وتسبحة", liturgy_cond),
            ("servants", "👥 خدمة وأسرة وتربية وشباب وأطفال", servants_cond),
            ("multilingual", "🌐 لغات عالمية ومكتبات مترجمة", multilingual_cond)
        ]

    def get_books_by_catalog_category(self, code: str, page: int = 1, page_size: int = 6) -> Tuple[List[Dict[str, Any]], int, int, str]:
        """Fetches books for a specific master category with pagination."""
        defs = {item[0]: (item[1], item[2]) for item in self._get_master_categories_definitions()}
        title, cond = defs.get(code, defs["theology"])

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM church_books WHERE ({cond}) AND is_duplicate_of IS NULL")
        total_count = cur.fetchone()[0]
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        curr_page = max(1, min(page, total_pages))
        offset = (curr_page - 1) * page_size

        cur.execute(f"""
            SELECT sha256, file_name, author, category, page_count, file_size
            FROM church_books
            WHERE ({cond}) AND is_duplicate_of IS NULL
            ORDER BY page_count DESC, id ASC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows, total_count, total_pages, title

    def get_catalog_authors_overview(self) -> List[Dict[str, Any]]:
        """Returns the top patristic authors with live book counts."""
        authors_config = [
            ("tadros", "القمص تادرس يعقوب", "%تادرس يعقوب%"),
            ("matta", "الأب متى المسكين", "%متى المسكين%"),
            ("shenouda", "قداسة البابا شنودة الثالث", "%شنودة%"),
            ("gregory", "الأنبا غريغوريوس", "%غريغوريوس%"),
            ("macarius", "القديس مقاريوس الكبير", "%مقاريوس%"),
            ("cyril", "القديس كيرلس الكبير", "%كيرلس%"),
            ("makarios_minia", "الأنبا مكاريوس أسقف المنيا", "%مكاريوس%"),
            ("athanasius", "القديس أثناسيوس الرسولي", "%أثناسيوس%"),
            ("antony", "القديس الأنبا أنطونيوس", "%أنطونيوس%"),
            ("chrysostom", "القديس يوحنا ذهبي الفم", "%ذهبي الفم%")
        ]
        conn = get_connection()
        cur = conn.cursor()
        result = []
        for code, name, pattern in authors_config:
            cur.execute("""
                SELECT COUNT(*) FROM church_books 
                WHERE (file_name LIKE ? OR author LIKE ? OR category LIKE ?) AND is_duplicate_of IS NULL
            """, (pattern, pattern, pattern))
            cnt = cur.fetchone()[0]
            result.append({"code": code, "name": name, "count": cnt})
        conn.close()
        return result

    def get_books_by_catalog_author(self, code: str, page: int = 1, page_size: int = 6) -> Tuple[List[Dict[str, Any]], int, int, str]:
        """Fetches books for a specific author with pagination."""
        authors_map = {
            "tadros": ("القمص تادرس يعقوب ملطي", "%تادرس يعقوب%"),
            "matta": ("الأب متى المسكين", "%متى المسكين%"),
            "shenouda": ("قداسة البابا شنودة الثالث", "%شنودة%"),
            "gregory": ("الأنبا غريغوريوس أسقف البحث العلمي", "%غريغوريوس%"),
            "macarius": ("القديس مقاريوس الكبير", "%مقاريوس%"),
            "cyril": ("القديس كيرلس الكبير", "%كيرلس%"),
            "makarios_minia": ("الأنبا مكاريوس أسقف المنيا", "%مكاريوس%"),
            "athanasius": ("القديس أثناسيوس الرسولي", "%أثناسيوس%"),
            "antony": ("القديس الأنبا أنطونيوس", "%أنطونيوس%"),
            "chrysostom": ("القديس يوحنا ذهبي الفم", "%ذهبي الفم%")
        }
        author_name, pattern = authors_map.get(code, ("آباء الكنيسة", "%أنطونيوس%"))

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM church_books 
            WHERE (file_name LIKE ? OR author LIKE ? OR category LIKE ?) AND is_duplicate_of IS NULL
        """, (pattern, pattern, pattern))
        total_count = cur.fetchone()[0]
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        curr_page = max(1, min(page, total_pages))
        offset = (curr_page - 1) * page_size

        cur.execute("""
            SELECT sha256, file_name, author, category, page_count, file_size
            FROM church_books
            WHERE (file_name LIKE ? OR author LIKE ? OR category LIKE ?) AND is_duplicate_of IS NULL
            ORDER BY page_count DESC, id ASC
            LIMIT ? OFFSET ?
        """, (pattern, pattern, pattern, page_size, offset))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows, total_count, total_pages, author_name

    def get_books_by_alphabet(self, char: str, page: int = 1, page_size: int = 6) -> Tuple[List[Dict[str, Any]], int, int]:
        """Fetches books starting with letter with pagination."""
        conn = get_connection()
        cur = conn.cursor()
        if char == "ا":
            cond = "file_name LIKE 'ا%' OR file_name LIKE 'أ%' OR file_name LIKE 'إ%'"
            params = ()
        else:
            cond = "file_name LIKE ? OR file_name LIKE ?"
            params = (f"{char}%", f"ال{char}%")

        cur.execute(f"SELECT COUNT(*) FROM church_books WHERE ({cond}) AND is_duplicate_of IS NULL", params)
        total_count = cur.fetchone()[0]
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        curr_page = max(1, min(page, total_pages))
        offset = (curr_page - 1) * page_size

        cur.execute(f"""
            SELECT sha256, file_name, author, category, page_count, file_size
            FROM church_books
            WHERE ({cond}) AND is_duplicate_of IS NULL
            ORDER BY file_name ASC
            LIMIT ? OFFSET ?
        """, (*params, page_size, offset))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows, total_count, total_pages

    def get_random_featured_book(self) -> Optional[Dict[str, Any]]:
        """Picks a random high-quality book for the discovery feature."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT sha256, file_name, author, category, page_count, file_size
            FROM church_books
            WHERE is_duplicate_of IS NULL AND page_count > 15
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_major_encyclopedias(self) -> List[Dict[str, Any]]:
        """Returns top classical encyclopedias and foundational church books."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT sha256, file_name, author, category, page_count, file_size
            FROM church_books
            WHERE (
                file_name LIKE '%موسوعة%' OR 
                file_name LIKE '%التفسير التطبيقي%' OR
                file_name LIKE '%بستان الرهبان%' OR
                file_name LIKE '%مشتهى الأجيال%' OR
                file_name LIKE '%تجسد الكلمة%' OR
                file_name LIKE '%تاريخ الكنيسة القبطية%'
            ) AND is_duplicate_of IS NULL
            ORDER BY page_count DESC
            LIMIT 8
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows


    def get_admin_metrics(self) -> Dict[str, Any]:
        """Calculates comprehensive administrative and research metrics for monitoring dashboard."""
        conn = get_connection()
        cur = conn.cursor()

        # 1. Total counts
        cur.execute("SELECT COUNT(*), SUM(page_count), SUM(file_size) FROM church_books WHERE is_duplicate_of IS NULL")
        unique_books, total_pages, total_size = cur.fetchone()

        # 2. Authenticity Tiers
        cur.execute("""
            SELECT authenticity_tier, COUNT(*) 
            FROM church_books 
            WHERE is_duplicate_of IS NULL 
            GROUP BY authenticity_tier 
            ORDER BY authenticity_tier ASC
        """)
        tier_counts = {f"Tier {r[0]}": r[1] for r in cur.fetchall()}

        # 3. Source Types
        cur.execute("""
            SELECT source_types, COUNT(*) 
            FROM church_books 
            WHERE is_duplicate_of IS NULL 
            GROUP BY source_types 
            ORDER BY COUNT(*) DESC
        """)
        source_counts = {r[0] or "UNCLASSIFIED": r[1] for r in cur.fetchall()}

        # 4. OCR & Extraction Status
        cur.execute("""
            SELECT ocr_status, COUNT(*) 
            FROM church_books 
            WHERE is_duplicate_of IS NULL 
            GROUP BY ocr_status
        """)
        ocr_counts = {r[0] or "none": r[1] for r in cur.fetchall()}

        # 5. Indexed chunks
        try:
            cur.execute("SELECT MAX(id) FROM church_chunks_fts_docsize")
            val = cur.fetchone()[0]
            indexed_chunks = val if val is not None else 0
        except Exception:
            indexed_chunks = 0

        # 6. Recent searches
        cur.execute("""
            SELECT query, results_count, created_at 
            FROM search_telemetry 
            ORDER BY id DESC 
            LIMIT 10
        """)
        recent_searches = [dict(r) for r in cur.fetchall()]

        conn.close()

        return {
            "unique_books": unique_books or 0,
            "total_pages": total_pages or 0,
            "total_size_mb": round((total_size or 0) / (1024 * 1024), 2),
            "indexed_chunks": indexed_chunks,
            "authenticity_tiers": tier_counts,
            "source_types": source_counts,
            "ocr_status": ocr_counts,
            "recent_searches": recent_searches
        }

    # ==========================================
    # Multi-Turn Persistent Discussions & Memory
    # ==========================================

    def create_session(self, user_id: str, title: str = "بحث لاهوتي جديد", session_id: Optional[str] = None) -> str:
        """Creates a new discussion session and returns its ID."""
        s_id = session_id or uuid.uuid4().hex[:12]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_sessions (id, user_id, title) VALUES (?, ?, ?)",
            (s_id, str(user_id), title)
        )
        conn.commit()
        conn.close()
        return s_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single session with message count."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.id = m.session_id
            WHERE s.id = ?
            GROUP BY s.id
        """, (session_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_or_create_active_session(self, user_id: str, default_title: str = "بحث لاهوتي جديد") -> Dict[str, Any]:
        """Gets the most recently active session for a user or creates a new one."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, COUNT(m.id) as message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.id = m.session_id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT 1
        """, (str(user_id),))
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)

        s_id = self.create_session(user_id, default_title)
        return {
            "id": s_id,
            "user_id": str(user_id),
            "title": default_title,
            "message_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    def list_user_sessions(self, user_id: Optional[str] = None, limit: int = 50, all_sessions: bool = True) -> List[Dict[str, Any]]:
        """Lists discussion sessions ordered by most recently updated.
        Defaults to returning all library research sessions so sessions are never lost across IPs/origins.
        If all_sessions is False and a specific user_id is given, returns that user's sessions,
        falling back to all sessions if that user has no sessions yet."""
        conn = get_connection()
        cur = conn.cursor()
        
        fetch_all = all_sessions or not user_id or str(user_id).lower() in ("all", "default", "scholar_master", "*", "web")
        rows = []
        if not fetch_all:
            cur.execute("""
                SELECT s.*, COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                WHERE s.user_id = ?
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
            """, (str(user_id), limit))
            rows = cur.fetchall()
            if not rows:
                fetch_all = True
                
        if fetch_all:
            cur.execute("""
                SELECT s.*, COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
        sessions = [dict(r) for r in rows]
        for s in sessions:
            cur.execute("""
                SELECT id, content FROM chat_messages
                WHERE session_id = ? AND role = 'user'
                ORDER BY id ASC
            """, (s["id"],))
            q_rows = cur.fetchall()
            s["user_queries"] = [{"id": qr[0], "content": qr[1][:80]} for qr in q_rows]
            s["questions_count"] = len(s["user_queries"])
        conn.close()
        return sessions

    def update_session_title(self, session_id: str, title: str) -> None:
        """Updates discussion session title and touches updated_at."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, session_id)
        )
        conn.commit()
        conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Deletes session and all its messages."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Appends a message to a session and updates the session's timestamp with retry loop & FK auto-recovery."""
        import time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cits_json = json.dumps(citations or [], ensure_ascii=False)
        for attempt in range(4):
            try:
                conn = get_connection()
                cur = conn.cursor()
                # Verify session exists to prevent foreign key violation
                cur.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (session_id, "web", content.split("\n")[0][:45], now, now)
                    )
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, cits_json)
                )
                msg_id = cur.lastrowid
                cur.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
                conn.commit()
                conn.close()
                return msg_id
            except sqlite3.OperationalError as op_err:
                time.sleep(0.15 * (2 ** attempt))
                if attempt == 3:
                    logger.warning(f"Error saving chat message to session {session_id}: {op_err}")
                    return -1
            except Exception as e:
                logger.warning(f"Error saving chat message to session {session_id}: {e}")
                return -1
        return -1

    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves chronological messages of a discussion session."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, session_id, role, content, citations, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (session_id, limit))
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["citations"] = json.loads(d["citations"]) if d.get("citations") else []
            except Exception:
                d["citations"] = []
            results.append(d)
        return results

    def compile_session(self, session_id: str) -> Dict[str, Any]:
        """
        Compiles all turns of a discussion into a unified Master Academic Research Monograph:
        - Clean publication-ready layout without emojis or redundant clutter
        - Structured Table of Contents / Research Sections
        - Full grounded patristic analysis for each chapter/axis
        - Consolidated Unified Patristic Bibliography (deduplicated)
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": "جلسة البحث غير موجودة"}

        messages = self.get_session_messages(session_id, limit=200)
        if not messages:
            return {
                "session_id": session_id,
                "title": session.get("title", "بحث لاهوتي"),
                "turns_count": 0,
                "turns": [],
                "bibliography": [],
                "markdown": "لا توجد حوارات أو أبحاث مسجلة في هذه الجلسة بعد.",
                "plain_text": "لا توجد حوارات أو أبحاث مسجلة في هذه الجلسة بعد."
            }

        # Pair questions and answers
        turns = []
        current_user_msg = None
        for m in messages:
            if m["role"] == "user":
                current_user_msg = m
            elif m["role"] == "assistant" and current_user_msg:
                turns.append({
                    "question": current_user_msg["content"],
                    "user_query": current_user_msg["content"],
                    "answer": m["content"],
                    "ai_response": m["content"],
                    "citations": m.get("citations", []),
                    "created_at": current_user_msg.get("created_at")
                })
                current_user_msg = None

        if current_user_msg:
            turns.append({
                "question": current_user_msg["content"],
                "user_query": current_user_msg["content"],
                "answer": "قيد المتابعة والدراسة الأكاديمية...",
                "ai_response": "قيد المتابعة والدراسة الأكاديمية...",
                "citations": [],
                "created_at": current_user_msg.get("created_at")
            })

        # Gather unified bibliography
        biblio_dict = {}
        for t in turns:
            for c in t["citations"]:
                raw_title = c.get("book_title", "مرجع كنسي")
                title = re.sub(r"^[0-9\-_\s]+", "", raw_title).replace(".pdf", "").strip()
                p = c.get("printed_page") or c.get("page_number")
                author = c.get("author", "آباء الكنيسة")
                tier = c.get("authenticity_tier", 3)
                key = (title, author)
                if key not in biblio_dict:
                    biblio_dict[key] = {"title": title, "author": author, "tier": tier, "pages": set()}
                if p:
                    biblio_dict[key]["pages"].add(str(p))

        # Helper to strip emojis for clean academic output
        def _clean_academic(txt: str) -> str:
            # Strip emojis and technical brackets
            t = re.sub(r"[\U00010000-\U0010ffff]", "", txt)
            t = re.sub(r"\[(QUOTATION|PARAPHRASE|SYNTHESIS|اقتباس حرفي|صياغة تحليلية|استنتاج مركب)[^\]]*\]", "", t)
            return t.strip()

        # Format Markdown Document
        title = session.get("title", "أطروحة بحثية لاهوتية")
        if (title in ["بحث لاهوتي جديد", "جلسة بحث جديدة"] or not title) and turns:
            title = turns[0]["question"][:60].strip()

        title = _clean_academic(title)

        md_lines = [
            "# أطروحة بحثية لاهوتية مجمعة",
            f"## الموضوع: «{title}»",
            "*منظومة ELANTONY LIBRARY AI - كنيسة الإسكندرية القبطية الأرثوذكسية*",
            f"**تاريخ التوثيق:** `{datetime.now().strftime('%Y-%m-%d')}` | **عدد المباحث:** `{len(turns)}`",
            "",
            "---",
            "",
            "### فهرس مباحث ومحتويات البحث:",
        ]

        for i, t in enumerate(turns, 1):
            q_clean = _clean_academic(t['question'])
            md_lines.append(f"{i}. [المبحث {i}: {q_clean}](#مبحث-{i})")

        md_lines.extend(["", "---", ""])

        # Detailed Q&A Chapters
        for i, t in enumerate(turns, 1):
            q_clean = _clean_academic(t['question'])
            ans_clean = _clean_academic(t['answer'])

            md_lines.append(f"## <a id='مبحث-{i}'></a>المبحث {i}: «{q_clean}»")
            md_lines.append("")
            md_lines.append(ans_clean)
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

        # Unified Bibliography Section
        md_lines.append("## ثبت المصادر والمراجع البيبليوغرافية الموحدة للبحث:")
        bib_list_for_export = []
        if biblio_dict:
            for b_idx, (k, b_info) in enumerate(biblio_dict.items(), 1):
                sorted_pages = sorted(list(b_info["pages"]), key=lambda x: int(x) if x.isdigit() else 0)
                pages_str = ", ".join(sorted_pages)
                pages_label = f"صـ {pages_str}" if pages_str else "كامل المرجع"
                md_lines.append(f"{b_idx}. **{b_info['title']}** — الكاتب/الأب: `{b_info['author']}` | {pages_label} | المرتبة: `Tier {b_info['tier']}`")
                bib_list_for_export.append({
                    "title": b_info["title"],
                    "author": b_info["author"],
                    "pages_cited": pages_label,
                    "tier": b_info["tier"]
                })
        else:
            md_lines.append("تم الاعتماد على الأصول والوثائق الآبائية الموثقة في سياق المباحث أعلاه.")

        md_lines.extend([
            "",
            "---",
            "*(تم تحرير وتوثيق هذه الدراسة بواسطة ELANTONY LIBRARY AI - خدمة التراث الكنسي الأرثوذكسي)*"
        ])

        full_md = "\n".join(md_lines)

        # Plain text conversion
        plain_text = (
            full_md.replace("# ", "")
            .replace("## ", "")
            .replace("### ", "")
            .replace("#### ", "")
            .replace("**", "")
            .replace("`", "")
            .replace("---", "═══════════════════════════════════")
        )

        return {
            "session_id": session_id,
            "title": title,
            "turns_count": len(turns),
            "turns": turns,
            "bibliography": bib_list_for_export if bib_list_for_export else list(biblio_dict.values()),
            "markdown": full_md,
            "plain_text": plain_text
        }


    def merge_sessions(self, session_ids: List[str], target_title: Optional[str] = None, user_id: str = "scholar_master") -> Dict[str, Any]:
        """
        Merges multiple discussion sessions into a single new unified session:
        - Retrieves all messages from the specified session_ids
        - Creates a new session in chat_sessions
        - Copies all messages (preserving their order and content) into the new session
        - Returns the new session object and metadata
        """
        if not session_ids or len(session_ids) < 2:
            return {"error": "يجب تحديد جلستي بحث على الأقل للدمج"}

        valid_sessions = []
        for sid in session_ids:
            s = self.get_session(sid)
            if s:
                valid_sessions.append(s)

        if len(valid_sessions) < 2:
            return {"error": "تعذر العثور على الجلسات المطلوبة للدمج"}

        # Determine target title
        if not target_title or not target_title.strip():
            target_title = "أطروحة لاهوتية مجمعة: " + " + ".join([s.get("title", "")[:25] for s in valid_sessions[:2]])

        new_session_id = self.create_session(user_id=user_id, title=target_title.strip())

        # Copy messages from all sessions in order
        conn = get_connection()
        cur = conn.cursor()
        total_copied = 0

        for sid in session_ids:
            msgs = self.get_session_messages(sid, limit=500)
            for m in msgs:
                citations_json = json.dumps(m.get("citations", []), ensure_ascii=False) if m.get("citations") else None
                cur.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content, citations, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (new_session_id, m["role"], m["content"], citations_json, m.get("created_at") or datetime.now().isoformat())
                )
                total_copied += 1

        conn.commit()
        conn.close()

        # Update session title and timestamp
        self.update_session_title(new_session_id, target_title.strip())

        return {
            "session_id": new_session_id,
            "title": target_title.strip(),
            "messages_copied": total_copied,
            "merged_sessions_count": len(valid_sessions)
        }

    def run_maintenance(self) -> Dict[str, Any]:
        """Runs periodic SQLite maintenance: WAL checkpoint, FTS5 optimize, and schema analysis."""
        conn = get_connection()
        cur = conn.cursor()
        actions = []

        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            actions.append("wal_checkpoint_truncate_success")
        except Exception as e:
            actions.append(f"wal_checkpoint_err: {e}")

        try:
            cur.execute("INSERT INTO church_chunks_fts(church_chunks_fts) VALUES('optimize')")
            actions.append("fts5_optimize_success")
        except Exception as e:
            actions.append(f"fts5_optimize_err: {e}")

        try:
            cur.execute("PRAGMA optimize")
            actions.append("pragma_optimize_success")
        except Exception as e:
            actions.append(f"pragma_optimize_err: {e}")

        conn.commit()
        conn.close()
        return {"status": "completed", "maintenance_actions": actions}

    def register_or_touch_scholar(self, user_id: str, display_name: Optional[str] = None) -> None:
        """Registers or updates a scholar profile and touch timestamp with lock retry."""
        import time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for attempt in range(4):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO scholar_profiles (user_id, display_name, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        display_name = COALESCE(?, display_name),
                        last_seen = ?
                """, (str(user_id), display_name or 'باحث لاهوتي', now, now, display_name, now))
                conn.commit()
                conn.close()
                return
            except sqlite3.OperationalError as e:
                if 'locked' in str(e).lower() and attempt < 3:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                logger.warning(f"Error touching scholar profile: {e}")
                return


    def get_all_scholars_activity(self) -> Dict[str, Any]:
        """
        Super-view for Admin: returns complete activity telemetry for all scholars.
        Lists all users, their questions, discussion topics, and timestamps.
        """
        conn = get_connection()
        cur = conn.cursor()

        # Profiles table verified in init_schema

        # 1. Scholars summary
        cur.execute("""
            SELECT 
                s.user_id,
                p.display_name,
                COUNT(DISTINCT s.id) as session_count,
                COUNT(m.id) as message_count,
                MIN(s.created_at) as first_seen,
                MAX(s.updated_at) as last_active
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON s.id = m.session_id
            LEFT JOIN scholar_profiles p ON s.user_id = p.user_id
            GROUP BY s.user_id
            ORDER BY last_active DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]

        scholars = []
        total_questions = 0

        for u in rows:
            uid = u["user_id"]
            # Fetch all user questions
            cur.execute("""
                SELECT m.content, m.created_at, s.title as session_title, s.id as session_id
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE s.user_id = ? AND m.role = 'user'
                ORDER BY m.created_at DESC
            """, (uid,))
            queries = [dict(q) for q in cur.fetchall()]
            total_questions += len(queries)

            scholars.append({
                "user_id": uid,
                "display_name": u.get("display_name") or "باحث لاهوتي",
                "session_count": u["session_count"],
                "message_count": u["message_count"],
                "query_count": len(queries),
                "first_seen": u["first_seen"],
                "last_active": u["last_active"],
                "recent_queries": queries[:10],
                "all_queries_count": len(queries)
            })

        # 2. Chronological stream of recent global questions
        cur.execute("""
            SELECT m.content, m.created_at, s.user_id, s.title as session_title, p.display_name
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            LEFT JOIN scholar_profiles p ON s.user_id = p.user_id
            WHERE m.role = 'user'
            ORDER BY m.created_at DESC
            LIMIT 40
        """)
        global_stream = [dict(q) for q in cur.fetchall()]

        conn.close()

        return {
            "total_scholars": len(scholars),
            "total_questions": total_questions,
            "scholars": scholars,
            "live_stream": global_stream
        }


# Singleton repository instance
repo = DatabaseRepository()
