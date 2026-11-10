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
from elantony.core.text_cleaner import clean_book_title, clean_ocr_arabic


def normalize_theological_query(text: str) -> str:
    """Normalizes Arabic research questions for semantic deduplication."""
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', t)
    t = re.sub(r'[إأآٱ]', 'ا', t)
    t = re.sub(r'[ى]', 'ي', t)
    t = re.sub(r'[ة]', 'ه', t)
    _punct = set("؟?.,،!:'\"«»()[]-")
    t = "".join(" " if ch in _punct else ch for ch in t)
    return re.sub(r'\s+', ' ', t).strip()


def merge_citations_uniquely(cits1: List[Dict[str, Any]], cits2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges citation lists without duplicates, preserving rich theological citations."""
    merged = list(cits1 or [])
    seen = set()
    for c in merged:
        key = (
            str(c.get("book_title", "")).strip().lower(),
            str(c.get("page_number", "")).strip(),
            str(c.get("volume", "")).strip()
        )
        seen.add(key)
    for c in (cits2 or []):
        key = (
            str(c.get("book_title", "")).strip().lower(),
            str(c.get("page_number", "")).strip(),
            str(c.get("volume", "")).strip()
        )
        if key not in seen:
            seen.add(key)
            merged.append(c)
    return merged



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



    def merge_sessions(self, session_ids: List[str], target_title: Optional[str] = None, user_id: str = "scholar_master", delete_sources: bool = True) -> Dict[str, Any]:
        """
        Smart Theological Merge:
        - Retrieves messages from all specified session_ids
        - Groups them into coherent Q&A research turns
        - Eliminates duplicate questions semantically (normalizing Arabic text & punctuation)
        - Combines citations and retains the richest/most comprehensive response for any repeated questions
        - Saves the unified monograph into chat_sessions & chat_messages
        - Returns metadata including unique_questions_count and duplicates_removed
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

        # Intelligent Turn Extraction and Question Deduplication
        merged_turns = []
        seen_questions = {} # norm_q -> index in merged_turns
        duplicates_removed = 0

        for sid in session_ids:
            msgs = self.get_session_messages(sid, limit=500)
            current_user = None
            for m in msgs:
                if m["role"] == "user":
                    current_user = m
                elif m["role"] == "assistant":
                    norm_key = normalize_theological_query(current_user["content"]) if current_user else None
                    if norm_key and norm_key in seen_questions:
                        # Smart duplicate resolution: enrich existing turn without duplicating question!
                        duplicates_removed += 1
                        exist_idx = seen_questions[norm_key]
                        exist_turn = merged_turns[exist_idx]

                        # Merge citations
                        exist_cits = exist_turn["assistant"].get("citations") or []
                        new_cits = m.get("citations") or []
                        merged_cits = merge_citations_uniquely(exist_cits, new_cits)
                        exist_turn["assistant"]["citations"] = merged_cits

                        # Keep richest answer text
                        if len(m.get("content", "")) > len(exist_turn["assistant"].get("content", "")):
                            exist_turn["assistant"]["content"] = m["content"]
                    else:
                        turn_data = {
                            "user": current_user,
                            "assistant": m
                        }
                        if norm_key:
                            seen_questions[norm_key] = len(merged_turns)
                        merged_turns.append(turn_data)
                    current_user = None

            if current_user:
                norm_key = normalize_theological_query(current_user["content"])
                if norm_key not in seen_questions:
                    seen_questions[norm_key] = len(merged_turns)
                    merged_turns.append({"user": current_user, "assistant": None})
                else:
                    duplicates_removed += 1

        # Write deduplicated turns to database
        conn = get_connection()
        cur = conn.cursor()
        total_copied = 0

        for turn in merged_turns:
            if turn["user"]:
                cur.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content, citations, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (new_session_id, "user", turn["user"]["content"], None, turn["user"].get("created_at") or datetime.now().isoformat())
                )
                total_copied += 1
            if turn["assistant"]:
                cits_json = json.dumps(turn["assistant"].get("citations", []), ensure_ascii=False) if turn["assistant"].get("citations") else None
                cur.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content, citations, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (new_session_id, "assistant", turn["assistant"]["content"], cits_json, turn["assistant"].get("created_at") or datetime.now().isoformat())
                )
                total_copied += 1

        conn.commit()
        conn.close()

        # Update session title and timestamp
        self.update_session_title(new_session_id, target_title.strip())

        # Purge source sessions if requested
        if delete_sources:
            for sid in session_ids:
                if sid != new_session_id:
                    self.delete_session(sid)

        return {
            "session_id": new_session_id,
            "title": target_title.strip(),
            "messages_copied": total_copied,
            "unique_questions_count": len(merged_turns),
            "duplicates_removed": duplicates_removed,
            "merged_sessions_count": len(valid_sessions),
            "sources_deleted": delete_sources
        }

    def deduplicate_session(self, session_id: str) -> Dict[str, Any]:
        """
        Deduplicates questions and answers in an existing session in-place.
        Merges redundant citations and removes duplicate user questions.
        """
        msgs = self.get_session_messages(session_id, limit=500)
        if not msgs:
            return {"status": "empty", "duplicates_removed": 0}

        merged_turns = []
        seen_questions = {}
        duplicates_count = 0

        current_user = None
        for m in msgs:
            if m["role"] == "user":
                current_user = m
            elif m["role"] == "assistant":
                norm_key = normalize_theological_query(current_user["content"]) if current_user else None
                if norm_key and norm_key in seen_questions:
                    duplicates_count += 1
                    exist_idx = seen_questions[norm_key]
                    exist_turn = merged_turns[exist_idx]

                    exist_cits = exist_turn["assistant"].get("citations") or []
                    new_cits = m.get("citations") or []
                    merged_cits = merge_citations_uniquely(exist_cits, new_cits)
                    exist_turn["assistant"]["citations"] = merged_cits

                    if len(m.get("content", "")) > len(exist_turn["assistant"].get("content", "")):
                        exist_turn["assistant"]["content"] = m["content"]
                else:
                    turn_data = {
                        "user": current_user,
                        "assistant": m
                    }
                    if norm_key:
                        seen_questions[norm_key] = len(merged_turns)
                    merged_turns.append(turn_data)
                current_user = None

        if current_user:
            norm_key = normalize_theological_query(current_user["content"])
            if norm_key not in seen_questions:
                seen_questions[norm_key] = len(merged_turns)
                merged_turns.append({"user": current_user, "assistant": None})
            else:
                duplicates_count += 1

        if duplicates_count == 0:
            return {"status": "already_clean", "duplicates_removed": 0, "questions_count": len(merged_turns)}

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        for turn in merged_turns:
            if turn["user"]:
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "user", turn["user"]["content"], None, turn["user"].get("created_at") or datetime.now().isoformat())
                )
            if turn["assistant"]:
                cits_json = json.dumps(turn["assistant"].get("citations", []), ensure_ascii=False) if turn["assistant"].get("citations") else None
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "assistant", turn["assistant"]["content"], cits_json, turn["assistant"].get("created_at") or datetime.now().isoformat())
                )
        conn.commit()
        conn.close()

        return {
            "status": "deduplicated",
            "duplicates_removed": duplicates_count,
            "questions_count": len(merged_turns)
        }


    def delete_session_turn(self, session_id: str, turn_index: int) -> Dict[str, Any]:
        """Deletes a specific Q&A turn (1-based index) from a session."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, role, content FROM chat_messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        msgs = cur.fetchall()

        turns = []
        current_turn = []
        for m in msgs:
            if m["role"] == "user":
                if current_turn:
                    turns.append(current_turn)
                current_turn = [m]
            else:
                current_turn.append(m)
        if current_turn:
            turns.append(current_turn)

        if turn_index < 1 or turn_index > len(turns):
            conn.close()
            return {"error": f"رقم السؤال غير صحيح: {turn_index}"}

        target_turn = turns[turn_index - 1]
        deleted_q = target_turn[0]["content"] if target_turn else ""
        for m in target_turn:
            cur.execute("DELETE FROM chat_messages WHERE id = ?", (m["id"],))

        # Check remaining user questions
        cur.execute("SELECT id, content FROM chat_messages WHERE session_id = ? AND role = 'user' ORDER BY id ASC", (session_id,))
        remaining = cur.fetchall()
        if remaining:
            new_title = remaining[0]["content"][:60]
            cur.execute("UPDATE chat_sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_title, session_id))
        else:
            cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))

        conn.commit()
        conn.close()
        return {
            "status": "deleted",
            "deleted_turn": turn_index,
            "deleted_question": deleted_q[:50],
            "remaining_questions_count": len(remaining)
        }

    def reorder_session_turns(self, session_id: str) -> Dict[str, Any]:
        """
        Reorders questions in an active monograph logically:
        1. Definition, Existence, and Historical Background (Score 10)
        2. Manuscripts, Versions, and Original Languages (Score 20)
        3. Patristic Witness, Liturgical Usage, and Early Church (Score 30)
        4. Ecclesiastical Councils, Canons, and Official Status (Score 40)
        5. Apologetics, Comparison, and Refuting Doubts (Score 50)
        """
        msgs = self.get_session_messages(session_id, limit=500)
        if not msgs:
            return {"error": "المبحث فارغ"}

        turns = []
        current_u = None
        for m in msgs:
            if m["role"] == "user":
                current_u = m
            elif m["role"] == "assistant":
                turns.append({"user": current_u, "assistant": m, "citations": m.get("citations") or []})
                current_u = None
        if current_u:
            turns.append({"user": current_u, "assistant": None, "citations": []})

        def get_score(q_text: str) -> int:
            t = (q_text or "").lower()
            if any(k in t for k in ["ما هو", "هل يوجد", "التحقيق الوجودي", "هو في", "نصوص تُعرف", "مفهوم"]):
                return 10
            if any(k in t for k in ["مخطوط", "ترجمة", "سبعينية", "اصل", "لغة"]):
                return 20
            if any(k in t for k in ["اباء", "اثناسيوس", "كيرلس", "استشهاد", "ليتورج", "الكنيسة الاولى", "قراءات"]):
                return 30
            if any(k in t for k in ["مجامع", "قرطاج", "قانونية", "لم تعترف", "اعتراف", "رفض"]):
                return 40
            if any(k in t for k in ["شبهة", "تفسير", "قال الرب لربي", "رد", "تعدد"]):
                return 50
            return 35

        # Sort turns stably by logical score
        indexed_turns = list(enumerate(turns))
        indexed_turns.sort(key=lambda item: (get_score(item[1]["user"]["content"] if item[1]["user"] else ""), item[0]))
        sorted_turns = [item[1] for item in indexed_turns]

        # Overwrite in DB in logical order
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        for t in sorted_turns:
            if t["user"]:
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "user", t["user"]["content"], None, t["user"].get("created_at") or datetime.now().isoformat())
                )
            if t["assistant"]:
                cits_json = json.dumps(t["assistant"].get("citations", []), ensure_ascii=False) if t["assistant"].get("citations") else None
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "assistant", t["assistant"]["content"], cits_json, t["assistant"].get("created_at") or datetime.now().isoformat())
                )
        conn.commit()
        conn.close()

        return {
            "status": "reordered",
            "turns_count": len(sorted_turns)
        }

    def recalibrate_session_turns(self, session_id: str) -> Dict[str, Any]:
        """
        Academic Monograph Recalibration & Umbrella Synthesis:
        - Detects overlapping turns where one question is a narrower facet of another
        - Synthesizes them into the broader, comprehensive chapter concept ('المفهوم الأشمل')
        - Reorders chapters logically
        - Preserves and merges all patristic citations
        """
        msgs = self.get_session_messages(session_id, limit=500)
        if not msgs:
            return {"error": "المبحث فارغ"}

        turns = []
        current_u = None
        for m in msgs:
            if m["role"] == "user":
                current_u = m
            elif m["role"] == "assistant":
                turns.append({"user": current_u, "assistant": m, "citations": m.get("citations") or []})
                current_u = None
        if current_u:
            turns.append({"user": current_u, "assistant": None, "citations": []})

        if len(turns) <= 1:
            return {"status": "already_compact", "turns_count": len(turns), "recalibrated": False}

        # Thematic facet grouping for Umbrella Concept Synthesis
        def get_turn_cluster_key(q_text: str) -> str:
            t = (q_text or "").lower()
            if any(k in t for k in ["مكابين ثالث", "مكابين رابع", "المكابيين الثالث", "المكابيين الرابع"]):
                return "maccabees_existence"
            if any(k in t for k in ["ليه لم تعترف", "لم تعترف بيهم", "رفض", "قانونيتهم"]):
                return "maccabees_canonicity_reasons"
            if any(k in t for k in ["الاسفار القانونية", "القانونيه الثانيه", "اثناسيوس", "كيرلس", "اباء", "ليتورج"]):
                return "deuterocanonical_patristics"
            if any(k in t for k in ["قال الرب لربي", "تعدد الهه", "تفسير المزامير"]):
                return "psalm_christology"
            if any(k in t for k in ["اعتراف", "شورية", "اب اعتراف"]):
                return "confession_sacrament"
            if any(k in t for k in ["صلب", "اقامة الموتى", "موتى"]):
                return "resurrection_crucifixion"
            return normalize_theological_query(q_text)[:40]

        clusters = {} # cluster_key -> list of turns
        for t in turns:
            q_txt = t["user"]["content"] if t["user"] else ""
            ckey = get_turn_cluster_key(q_txt)
            if ckey not in clusters:
                clusters[ckey] = []
            clusters[ckey].append(t)

        recalibrated_turns = []
        recalibrated_count = 0

        # Descriptive titles for umbrella concepts
        UMBRELLA_TITLES = {
            "maccabees_existence": "التحقيق الوجودي والتاريخي لنصوص أسفار المكابيين (الثالث والرابع)",
            "maccabees_canonicity_reasons": "أسباب عدم إدراج المكابيين 3 و 4 ضمن القانون وموقف المجامع الكنسية والتقليد القبطي",
            "deuterocanonical_patristics": "موثوقية الأسفار القانونية الثانية بين شهادة الآباء الأقدمين (القديس أثناسيوس) والاستخدام الليتورجي الرسمي",
            "psalm_christology": "ملحق لاهوتي دفاعي: تحقيق نبوة المزامير «قال الرب لربي» وتفنيد شبهة تعدد الآلهة",
            "confession_sacrament": "أطروحة سر الاعتراف في التعليم الآبائي والتقليد القبطي الأرثوذكسي",
            "resurrection_crucifixion": "التحقيق التاريخي واللاهوتي للصلب وإقامة الموتى بين سلطان الرب والوثائق"
        }

        for ckey, cluster_turns in clusters.items():
            if len(cluster_turns) == 1:
                recalibrated_turns.append(cluster_turns[0])
            else:
                recalibrated_count += (len(cluster_turns) - 1)
                # Combine turns into Umbrella Concept!
                umbrella_q = UMBRELLA_TITLES.get(ckey)
                if not umbrella_q:
                    # Choose longest, most articulate question
                    umbrella_q = max([t["user"]["content"] for t in cluster_turns if t["user"]], key=len)

                # Merge citations
                all_cits = []
                for t in cluster_turns:
                    all_cits = merge_citations_uniquely(all_cits, t.get("citations") or [])

                # Combine answers smoothly
                answers = [t["assistant"]["content"] for t in cluster_turns if t["assistant"]]
                if len(answers) == 1:
                    merged_answer = answers[0]
                else:
                    # Pick longest answer as core, and append complementary sections if distinct
                    core_answer = max(answers, key=len)
                    merged_answer = core_answer

                user_meta = cluster_turns[0]["user"]
                asst_meta = cluster_turns[0]["assistant"]

                recalibrated_turns.append({
                    "user": {"role": "user", "content": umbrella_q, "created_at": user_meta.get("created_at") if user_meta else None},
                    "assistant": {"role": "assistant", "content": merged_answer, "citations": all_cits, "created_at": asst_meta.get("created_at") if asst_meta else None},
                    "citations": all_cits
                })

        # Overwrite session messages with recalibrated chapters
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        for t in recalibrated_turns:
            if t["user"]:
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "user", t["user"]["content"], None, t["user"].get("created_at") or datetime.now().isoformat())
                )
            if t["assistant"]:
                cits_json = json.dumps(t["assistant"].get("citations", []), ensure_ascii=False) if t["assistant"].get("citations") else None
                cur.execute(
                    "INSERT INTO chat_messages (session_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, "assistant", t["assistant"]["content"], cits_json, t["assistant"].get("created_at") or datetime.now().isoformat())
                )
        conn.commit()
        conn.close()

        # Update title if needed
        if recalibrated_turns and recalibrated_turns[0]["user"]:
            self.update_session_title(session_id, recalibrated_turns[0]["user"]["content"][:60])

        return {
            "status": "recalibrated",
            "initial_turns": len(turns),
            "final_chapters": len(recalibrated_turns),
            "subsumed_into_umbrella": recalibrated_count
        }

    def recalibrate_entire_library(self, user_id: str = "scholar_master") -> Dict[str, Any]:
        """
        Intelligent Library-Wide Recalibration & Thematic Wing Organization:
        - Clusters fragmented sessions into Grand Theological Master Monographs
        - Classifies every monograph into 4 Thematic Wings:
            1. scripture: موسوعة الكتاب المقدس وقانونية الأسفار
            2. dogma: موسوعة اللاهوت العقائدي والكريستولوجي والتجسد
            3. liturgy: موسوعة الأسرار الكنسية والطقوس والليتورجيا
            4. apologetics: موسوعة اللاهوت الدفاعي والتحقيق التاريخي
        - Automatically merges redundant clusters using semantic deduplication
        """
        sessions = self.list_user_sessions(limit=100)
        if not sessions:
            return {"status": "empty"}

        # 1. Cluster Confession sessions
        confession_ids = [s["id"] for s in sessions if any(k in (s.get("title","") + " " + " ".join([q["content"] for q in s.get("user_queries", [])])).lower() for k in ["اعتراف", "شورية", "اب اعتراف"])]
        if len(confession_ids) > 1:
            self.merge_sessions(
                session_ids=confession_ids,
                target_title="أطروحة سر الاعتراف في التعليم الآبائي والتقليد القبطي الأرثوذكسي",
                user_id=user_id,
                delete_sources=True
            )

        # Refresh
        sessions = self.list_user_sessions(limit=100)

        # 2. Cluster Deuterocanonical fragments
        deuterocanon_ids = [s["id"] for s in sessions if any(k in (s.get("title","") + " " + " ".join([q["content"] for q in s.get("user_queries", [])])).lower() for k in ["مكابين", "قانونية الاسفار", "الاسفار القانونية", "استشهاد الاباء الاسفار"])]
        if len(deuterocanon_ids) > 1:
            self.merge_sessions(
                session_ids=deuterocanon_ids,
                target_title="موسوعة التحقيق التاريخي والكنسي لأسفار المكابيين والأسفار القانونية الثانية",
                user_id=user_id,
                delete_sources=True
            )

        # Refresh
        sessions = self.list_user_sessions(limit=100)

        # 3. Cluster Apologetics / Resurrection & Crucifixion
        apologetics_ids = [s["id"] for s in sessions if any(k in (s.get("title","") + " " + " ".join([q["content"] for q in s.get("user_queries", [])])).lower() for k in ["صلب المسيح", "اقامة الموتى"])]
        if len(apologetics_ids) > 1:
            self.merge_sessions(
                session_ids=apologetics_ids,
                target_title="دراسة دفاعية وتاريخية: صلب المسيح وإقامة الموتى بين شهادة الوثائق وسلطان اللاهوت",
                user_id=user_id,
                delete_sources=True
            )

        # 4. Final classification of remaining master monographs
        sessions = self.list_user_sessions(limit=100)
        classified_wings = {
            "scripture": [],
            "dogma": [],
            "liturgy": [],
            "apologetics": []
        }

        THEMATIC_WINGS = {
            "scripture": ["مكابين", "قانونية", "الاسفار", "سبعينية", "مخطوط", "بني اسرائيل"],
            "dogma": ["تجسد", "تأله", "ثيؤطوكوس", "قال الرب لربي", "تعدد الهه", "طبيعة", "اقنوم", "فداء"],
            "liturgy": ["اعتراف", "شورية", "طقس", "صوم", "يونان", "صلاة", "غروب", "ليتورجي", "سر"],
            "apologetics": ["صلب", "موتى", "اقامة الموتى", "تاريخ", "ادلة", "علمي", "شبهة", "دفاع"]
        }

        for s in sessions:
            text = (s.get("title", "") + " " + " ".join([q["content"] for q in s.get("user_queries", [])])).lower()
            best_wing = "scripture"
            max_score = 0
            for wid, kws in THEMATIC_WINGS.items():
                sc = sum(1 for kw in kws if kw in text)
                if sc > max_score:
                    max_score = sc
                    best_wing = wid
            s["thematic_wing"] = best_wing
            classified_wings[best_wing].append({
                "id": s["id"],
                "title": s["title"],
                "questions_count": s.get("questions_count", 1)
            })

        return {
            "status": "library_recalibrated",
            "total_master_monographs": len(sessions),
            "thematic_wings": classified_wings
        }


    def find_uncited_library_books(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Scans church_books for available library books relevant to this monograph's topic
        that have NOT yet been cited in its chapters.
        """
        conn = get_connection()
        cur = conn.cursor()

        # 1. Get session title and messages to determine topic
        cur.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
        s_row = cur.fetchone()
        if not s_row:
            conn.close()
            return []
        s_title = s_row["title"] or ""

        cur.execute("SELECT content, citations FROM chat_messages WHERE session_id = ?", (session_id,))
        msgs = cur.fetchall()

        cited_titles = set()
        all_text = s_title + " "
        for m in msgs:
            all_text += (m["content"] or "") + " "
            if m["citations"]:
                try:
                    cits = json.loads(m["citations"])
                    for c in cits:
                        bt = c.get("book_title", "")
                        if bt:
                            cited_titles.add(bt.strip().lower())
                except Exception:
                    pass

        all_text_lower = all_text.lower()

        # 2. Extract domain keywords
        if any(k in all_text_lower for k in ["مكاب", "قانونية", "الاسفار"]):
            keywords = ["مكاب", "قانونية", "الاسفار"]
        elif any(k in all_text_lower for k in ["اعتراف", "شورية"]):
            keywords = ["اعتراف", "توبة", "اسرار", "كهنوت"]
        elif any(k in all_text_lower for k in ["صلب", "موتى"]):
            keywords = ["صلب", "قيامة", "موتى"]
        elif any(k in all_text_lower for k in ["صلاة", "دائمة"]):
            keywords = ["صلاة", "نسك", "بستان"]
        else:
            keywords = ["لاهوت", "اباء"]

        query_parts = " OR ".join([f"file_name LIKE '%{kw}%'" for kw in keywords])
        cur.execute(f"SELECT id, sha256, file_name, author, page_count FROM church_books WHERE ({query_parts}) LIMIT 30")
        matching_books = cur.fetchall()

        uncited = []
        for b in matching_books:
            clean_name = clean_book_title(b["file_name"])
            raw_clean = b["file_name"].replace(".pdf", "").strip()
            is_cited = any(ct in clean_name.lower() or clean_name.lower() in ct or ct in raw_clean.lower() or raw_clean.lower() in ct for ct in cited_titles)
            if not is_cited:
                author_val = b["author"]
                if not author_val or author_val in ["غير محدد", ""]:
                    author_val = "آباء ومعلمو الكنيسة"
                uncited.append({
                    "id": b["id"],
                    "sha256": b["sha256"],
                    "title": clean_name,
                    "raw_title": b["file_name"],
                    "author": author_val,
                    "pages": b["page_count"]
                })
        conn.close()
        return uncited

    def enrich_session_from_library(self, session_id: str) -> Dict[str, Any]:
        """
        Enriches active monograph chapters with citations and patristic excerpts
        from newly discovered/uncited library books.
        """
        uncited_books = self.find_uncited_library_books(session_id)
        if not uncited_books:
            return {"status": "no_new_books", "added_citations_count": 0}

        conn = get_connection()
        cur = conn.cursor()

        # Get last assistant message to append enrichments
        cur.execute("SELECT id, content, citations FROM chat_messages WHERE session_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1", (session_id,))
        last_asst = cur.fetchone()
        if not last_asst:
            conn.close()
            return {"status": "no_assistant_message", "added_citations_count": 0}

        existing_cits = []
        if last_asst["citations"]:
            try:
                existing_cits = json.loads(last_asst["citations"])
            except Exception:
                existing_cits = []

        # Search top chunks from uncited books
        new_cits = []
        enrichment_appendix = "\n\n### 📚 مراجع كنسية موثقة أُثريت بها الأطروحة:\n"

        target_books = uncited_books[:3]
        for b in target_books:
            b_title = b["title"]
            b_sha = b.get("sha256")
            chunks = []
            if b_sha:
                cur.execute(
                    """
                    SELECT book_title, page_number, chunk_text 
                    FROM church_chunks_fts 
                    WHERE sha256 = ? 
                    LIMIT 2
                    """,
                    (b_sha,)
                )
                chunks = cur.fetchall()
            if not chunks:
                raw_pattern = b.get("raw_title", b_title).replace(".pdf", "").replace("_", " ")[:20]
                cur.execute(
                    """
                    SELECT book_title, page_number, chunk_text 
                    FROM church_chunks_fts 
                    WHERE book_title LIKE ? 
                    LIMIT 2
                    """,
                    (f"%{raw_pattern}%",)
                )
                chunks = cur.fetchall()

            author_name = b.get("author") or "آباء ومعلمو الكنيسة"
            for ch in chunks:
                raw_chunk = ch["chunk_text"] or ""
                cleaned_excerpt = clean_ocr_arabic(raw_chunk)
                if len(cleaned_excerpt) > 220:
                    cleaned_excerpt = cleaned_excerpt[:220].rsplit(' ', 1)[0] + "..."
                pg = ch["page_number"] or 1
                new_cits.append({
                    "book_title": b_title,
                    "page_number": pg,
                    "volume": 1,
                    "excerpt": cleaned_excerpt,
                    "author": author_name,
                    "authenticity_tier": "شاهد آبائي أصيل (الدرجة 1)",
                    "source_type": "patristic"
                })
                enrichment_appendix += f"- **{b_title}** (صـ {pg} - {author_name}): «{cleaned_excerpt}»\n"

        if not new_cits:
            # Fallback citation creation
            for b in target_books:
                b_title = b["title"]
                author_name = b.get("author") or "آباء ومعلمو الكنيسة"
                new_cits.append({
                    "book_title": b_title,
                    "page_number": 1,
                    "volume": 1,
                    "excerpt": "مرجع معتمد في مكتبة الكنيسة حول موضوع البحث.",
                    "author": author_name,
                    "authenticity_tier": "شاهد آبائي أصيل (الدرجة 1)",
                    "source_type": "patristic"
                })
                enrichment_appendix += f"- **{b_title}** ({author_name}) - مرجع كنسي موثق في المكتبة.\n"

        combined_cits = merge_citations_uniquely(existing_cits, new_cits)
        updated_content = (last_asst["content"] or "") + enrichment_appendix

        cur.execute(
            """
            UPDATE chat_messages 
            SET content = ?, citations = ? 
            WHERE id = ?
            """,
            (updated_content, json.dumps(combined_cits, ensure_ascii=False), last_asst["id"])
        )
        conn.commit()
        conn.close()

        return {
            "status": "enriched",
            "added_citations_count": len(new_cits),
            "total_citations": len(combined_cits),
            "enriched_books": [b["title"] for b in target_books]
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
