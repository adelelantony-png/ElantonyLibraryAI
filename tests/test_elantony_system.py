# -*- coding: utf-8 -*-
"""
Comprehensive Unit & Integration Tests for ELANTONY LIBRARY AI
Covers:
- Configuration & Security (Whitelist, Sanitization, Masking)
- Rate Limiter Sliding Window (UserRateLimiter)
- Database Connection & Repository Operations (DatabaseRepository, BookEntity, ChunkEntity, UserBookmarkEntity)
- Storage Adapters (LocalStorageAdapter, TelegramChannelStorageAdapter, OneDriveStorageAdapter, UnlimCloudStorageAdapter)
- Search Engine (FTS5 retrieval & Scoped Book Q&A)
- AI Grounded Grounding & Rule-based Provider (Zero Hallucination)
- Telegram Keyboards & UX 9-Section verification
"""

import os
import sqlite3
import pytest
from unittest.mock import patch

from elantony.core.config import Settings
from elantony.core.security import (
    sanitize_user_input,
    is_user_authorized,
    is_user_admin,
    mask_secret,
)
from elantony.core.rate_limiter import UserRateLimiter
from elantony.database.models import BookEntity, ChunkEntity, UserBookmarkEntity
from elantony.database.repository import DatabaseRepository
from elantony.storage.local_adapter import LocalStorageAdapter
from elantony.storage.telegram_channel_adapter import TelegramChannelStorageAdapter
from elantony.storage.onedrive_adapter import OneDriveStorageAdapter
from elantony.storage.unlimcloud_adapter import UnlimCloudStorageAdapter
from elantony.storage.factory import get_storage_adapter
from elantony.search.search_engine import SearchEngine
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.telegram.keyboards import (
    get_main_menu_reply_keyboard,
    get_chunk_actions_inline_keyboard,
    get_authors_inline_keyboard,
    get_categories_inline_keyboard,
)


class TestElantonyCore:
    def test_settings_initialization(self):
        settings = Settings()
        assert settings.app_name == "ELANTONY LIBRARY AI"
        assert settings.rate_limit_per_minute > 0
        assert isinstance(settings.allowed_telegram_user_ids, set)

    def test_security_input_sanitization(self):
        dirty = "<script>alert('pwned')</script>\x00\x08تفسير إنجيل يوحنا; DROP TABLE books;--"
        clean = sanitize_user_input(dirty)
        assert "\x00" not in clean
        assert "\x08" not in clean
        assert "تفسير إنجيل يوحنا" in clean

    def test_security_authorization_open_when_empty(self):
        with patch("elantony.core.security.settings") as mock_settings:
            mock_settings.allowed_telegram_user_ids = set()
            mock_settings.admin_telegram_user_ids = set()
            assert is_user_authorized(123456) is True

    def test_security_authorization_whitelist_enforced(self):
        with patch("elantony.core.security.settings") as mock_settings:
            mock_settings.allowed_telegram_user_ids = {111, 222}
            mock_settings.admin_telegram_user_ids = {999}
            assert is_user_authorized(111) is True
            assert is_user_authorized(999) is True
            assert is_user_authorized(333) is False

    def test_security_admin_check(self):
        with patch("elantony.core.security.settings") as mock_settings:
            mock_settings.admin_telegram_user_ids = {10001}
            mock_settings.app_env = "production"
            assert is_user_admin(10001) is True
            assert is_user_admin(99999) is False

    def test_security_mask_secret(self):
        secret = "9053947122:AAG07F1yB64mOgTHmucyHL5AznFWCS39Gv0"
        masked = mask_secret(secret)
        assert secret not in masked
        assert masked.startswith("9053")
        assert masked.endswith("9Gv0")
        assert "***" in masked
        assert mask_secret("") == "***NOT_SET***"
        assert mask_secret("short") == "***REDACTED***"

    def test_rate_limiter_sliding_window(self):
        limiter = UserRateLimiter(max_requests_per_minute=3)
        user_id = 98765
        
        # 3 requests allowed
        assert limiter.is_allowed(user_id) is True
        assert limiter.is_allowed(user_id) is True
        assert limiter.is_allowed(user_id) is True
        
        # 4th request blocked within 60-second window
        assert limiter.is_allowed(user_id) is False

        # Reset user clears history
        limiter.reset_user(user_id)
        assert limiter.is_allowed(user_id) is True


class TestElantonyDatabase:
    def test_pydantic_models(self):
        book = BookEntity(
            title="تجسد الكلمة",
            sha256="abc123def456",
            author="القديس أثناسيوس الرسولي",
            category="لاهوت عقيدي",
            page_count=120,
            file_size=1048576,
        )
        assert book.author == "القديس أثناسيوس الرسولي"
        assert book.page_count == 120
        assert book.file_format == "pdf"

        chunk = ChunkEntity(
            sha256="abc123def456",
            book_title="تجسد الكلمة",
            page_number=14,
            chunk_index=1,
            source_reference="كتاب تجسد الكلمة ص 14",
            chunk_text="لأنه إذ رأى الكلمة أن فساد البشرية لا يمكن أن يبطل إلا بالموت...",
        )
        assert chunk.page_number == 14
        assert chunk.chunk_index == 1

        bm = UserBookmarkEntity(
            user_id=123,
            book_sha256="abc123def456",
            book_title="تجسد الكلمة",
            page_number=14,
            source_reference="كتاب تجسد الكلمة ص 14",
            excerpt="لأنه إذ رأى الكلمة...",
        )
        assert bm.user_id == 123

    def test_repository_with_mocked_db(self, tmp_path):
        db_path = str(tmp_path / "test_repo.db")

        def make_connection():
            c = sqlite3.connect(db_path)
            c.row_factory = sqlite3.Row
            return c

        with patch("elantony.database.repository.get_connection", side_effect=make_connection):
            repo = DatabaseRepository()

            # Insert test book
            conn = make_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO church_books (
                    sha256, original_path, file_name, file_size, mod_time, page_count,
                    author, category, storage_provider, extraction_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "sha_life_antony", "/books/antony.pdf", "سيرة_أنطونيوس.pdf", 500000,
                "2026-01-01", 85, "القديس أثناسيوس الرسولي", "سير وتاريخ", "local", "completed"
            ))
            conn.commit()
            conn.close()

            # Search by title/author
            results = repo.search_books_by_title_or_author("أنطونيوس")
            assert len(results) >= 1
            assert results[0]["sha256"] == "sha_life_antony"

            # Test categories summary
            cats = repo.get_categories_summary()
            assert any(c["category"] == "سير وتاريخ" for c in cats)

            # Test bookmarks CRUD
            bm_id = repo.save_bookmark(
                user_id=555,
                book_sha256="sha_life_antony",
                book_title="سيرة أنطونيوس",
                page_number=10,
                source_reference="سيرة أنطونيوس ص 10",
                excerpt="فخرج إلى البرية..."
            )
            assert bm_id > 0

            bookmarks = repo.get_user_bookmarks(user_id=555)
            assert len(bookmarks) == 1
            assert bookmarks[0]["page_number"] == 10

            assert repo.delete_bookmark(bookmark_id=bm_id, user_id=555) is True
            assert len(repo.get_user_bookmarks(user_id=555)) == 0


class TestElantonyStorage:
    def test_local_storage_adapter(self, tmp_path):
        adapter = LocalStorageAdapter()
        test_file = tmp_path / "sample.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        file_info = adapter.get_file_info(str(test_file))
        assert file_info["exists"] is True
        assert file_info["file_size"] == len(b"%PDF-1.4 test")
        assert file_info["mime_type"] == "application/pdf"
        assert adapter.get_local_path(str(test_file)) is not None

    def test_storage_factory(self):
        local_ad = get_storage_adapter(provider_name="local")
        assert isinstance(local_ad, LocalStorageAdapter)

        tg_ad = get_storage_adapter(provider_name="telegram")
        assert isinstance(tg_ad, TelegramChannelStorageAdapter)

        od_ad = get_storage_adapter(provider_name="onedrive")
        assert isinstance(od_ad, OneDriveStorageAdapter)

        unlim_ad = get_storage_adapter(provider_name="unlimcloud")
        assert isinstance(unlim_ad, UnlimCloudStorageAdapter)


class TestElantonySearchAndAI:
    def test_rule_based_ai_strict_citation(self):
        provider = RuleBasedChurchProvider()
        chunks = [
            ChunkEntity(
                sha256="sha_inc",
                book_title="تجسد الكلمة",
                page_number=14,
                chunk_index=1,
                source_reference="كتاب: تجسد الكلمة | ص 14",
                chunk_text="الكلمة صار جسدًا لكي نصير نحن شركاء الطبيعة الإلهية بنعمته."
            )
        ]
        answer = provider.generate_answer(
            question="ما هو هدف تجسد الكلمة؟",
            context_chunks=chunks
        )
        assert "تجسد الكلمة" in answer
        assert "ص 14" in answer
        assert "شركاء الطبيعة الإلهية" in answer

    def test_rule_based_ai_empty_fallback(self):
        provider = RuleBasedChurchProvider()
        answer = provider.generate_answer(
            question="موضوع غير موجود",
            context_chunks=[]
        )
        assert "لم يتم العثور على شواهد" in answer

    def test_search_engine_fts5(self, tmp_path):
        db_path = str(tmp_path / "test_search.db")

        def make_connection():
            c = sqlite3.connect(db_path)
            c.row_factory = sqlite3.Row
            return c

        init_conn = make_connection()
        cur = init_conn.cursor()
        cur.execute("""
            CREATE VIRTUAL TABLE church_chunks_fts USING fts5(
                sha256 UNINDEXED,
                book_title,
                page_number UNINDEXED,
                chunk_index UNINDEXED,
                source_reference,
                chunk_text,
                tokenize = 'unicode61'
            )
        """)
        cur.execute("""
            INSERT INTO church_chunks_fts (
                sha256, book_title, page_number, chunk_index, source_reference, chunk_text
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "sha_001", "بستان الرهبان", 25, 2, "بستان الرهبان ص 25",
            "سئل شيخ عن الصلاة الدائمة فقال هي حفظ القلب من الأفكار الدنسة"
        ))
        init_conn.commit()
        init_conn.close()

        with patch("elantony.search.search_engine.get_connection", side_effect=make_connection):
            engine = SearchEngine()
            results = engine.search_fts5("الصلاة الدائمة", limit=3)
            assert len(results) == 1
            assert results[0].book_title == "بستان الرهبان"
            assert results[0].page_number == 25

            scoped = engine.search_scoped_book("sha_001", "القلب", limit=3)
            assert len(scoped) == 1


class TestElantonyTelegramKeyboards:
    def test_main_menu_sections(self):
        kb = get_main_menu_reply_keyboard()
        buttons_text = []
        for row in kb["keyboard"]:
            for btn in row:
                buttons_text.append(btn["text"])

        # Verify all 9 sections are present
        assert any("المساعد الذكي" in b for b in buttons_text)
        assert any("البحث في المكتبة" in b for b in buttons_text)
        assert any("اسأل كتابًا" in b for b in buttons_text)
        assert any("أقوال الآباء" in b for b in buttons_text)
        assert any("البحث حسب المؤلف" in b for b in buttons_text)
        assert any("تصفح التصنيفات" in b for b in buttons_text)
        assert any("أبحاثي المحفوظة" in b for b in buttons_text)
        assert any("الإعدادات" in b for b in buttons_text)
        assert any("حول المكتبة" in b for b in buttons_text)

    def test_inline_keyboards(self):
        actions = get_chunk_actions_inline_keyboard("sha_test", 15, 1)
        flat_callbacks = [b["callback_data"] for row in actions for b in row]
        assert "pdf:sha_test" in flat_callbacks
        assert "page:sha_test:15" in flat_callbacks
        assert "bm:sha_test:15" in flat_callbacks

        auth_kb = get_authors_inline_keyboard()
        assert len(auth_kb["inline_keyboard"]) >= 3

        cat_kb = get_categories_inline_keyboard()
        assert len(cat_kb["inline_keyboard"]) >= 3
