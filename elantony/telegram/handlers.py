# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Telegram Request & Callback Handlers
Implements robust business logic for the 9 master menu sections, interactive submenus,
live page-turning book reader, book action cards, and one-click social sharing.
All callback_data payloads strictly respect Telegram's 64-byte hard limit.
"""

import os
import random
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from elantony.core.config import settings
from elantony.core.security import is_user_authorized, is_user_admin, sanitize_user_input
from elantony.core.rate_limiter import rate_limiter
from elantony.core.logging import logger
from elantony.database.repository import repo
from elantony.search.search_engine import search_engine
from elantony.ai.factory import get_ai_provider
from elantony.telegram.keyboards import (
    get_main_menu_reply_keyboard,
    get_main_menu_inline_keyboard,
    get_fathers_topics_inline_keyboard,
    get_quick_books_inline_keyboard,
    get_book_card_inline_keyboard,
    get_authors_inline_keyboard,
    get_categories_inline_keyboard,
    get_chunk_actions_inline_keyboard,
    get_page_reader_inline_keyboard,
    get_back_to_main_inline_keyboard
)

# User state tracker for conversational flow
_user_states: Dict[int, Dict[str, Any]] = {}


class TelegramHandlerService:
    """Processes incoming Telegram updates and dispatches responses with rich buttons."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sends formatted message to Telegram chat with bulletproof multi-tier fallbacks."""
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            res = await client.post(url, json=payload, timeout=15.0)
            if res.status_code == 200:
                return True

            # Fallback 1: If Markdown formatting error, strip parse_mode
            payload.pop("parse_mode", None)
            res = await client.post(url, json=payload, timeout=15.0)
            if res.status_code == 200:
                return True

            # Fallback 2: If reply markup is too long or malformed, use minimal navigation keyboard
            payload["reply_markup"] = {
                "inline_keyboard": [[{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}]]
            }
            res = await client.post(url, json=payload, timeout=15.0)
            if res.status_code == 200:
                return True

            # Fallback 3: Send pure text without markup
            payload.pop("reply_markup", None)
            res = await client.post(url, json=payload, timeout=15.0)
            return res.status_code == 200

        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    async def send_document(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        file_path: str,
        caption: str = ""
    ) -> bool:
        """Uploads and sends local PDF document to chat."""
        if not os.path.exists(file_path):
            await self.send_message(
                client, chat_id,
                f"⚠️ لم يتم العثور على الملف محلياً: {os.path.basename(file_path)}",
                reply_markup=get_back_to_main_inline_keyboard()
            )
            return False

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 50.0:
            await self.send_message(
                client, chat_id,
                f"⚠️ حجم الكتاب كبير ({size_mb:.1f} MB) ويتجاوز حد البوت المباشر (50 MB).\n"
                f"يمكنك تصفح وقراءة صفحاته مباشرة عبر زر قراءة الصفحة المحددة.",
                reply_markup=get_back_to_main_inline_keyboard()
            )
            return False

        try:
            url = f"{self.api_base}/sendDocument"
            file_name = os.path.basename(file_path)
            await self.send_message(client, chat_id, f"⏳ جاري رفع وإرسال: «{file_name}»...")

            with open(file_path, "rb") as f:
                files = {"document": (file_name, f, "application/pdf")}
                data = {"chat_id": str(chat_id), "caption": caption[:1000]}
                res = await client.post(url, data=data, files=files, timeout=90.0)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            await self.send_message(client, chat_id, f"❌ تعذر إرسال الملف: {e}")
            return False

    async def answer_callback_query(self, client: httpx.AsyncClient, callback_id: str, text: Optional[str] = None):
        """Acknowledges callback button click."""
        try:
            url = f"{self.api_base}/answerCallbackQuery"
            payload = {"callback_query_id": callback_id}
            if text:
                payload["text"] = text
            await client.post(url, json=payload, timeout=5.0)
        except Exception:
            pass

    async def send_welcome_dashboard(self, client: httpx.AsyncClient, chat_id: int, user_name: str) -> None:
        """Sends the master dashboard with persistent keyboard AND rich inline buttons."""
        stats = repo.get_library_stats()
        welcome_text = (
            f"✠ *مرحباً بك {user_name} في منظومة ELANTONY LIBRARY AI* ✠\n\n"
            f"📚 *المكتبة الرقمية تضم:* `{stats['total_books']}` كتاباً ({stats['total_pages']:,} صفحة).\n"
            f"🧠 *محرك البحث الآبائي والـ RAG:* مفهرس به `{stats['indexed_chunks']:,}` شاهداً موثقاً.\n\n"
            f"👇 *اضغط على أي زر تفاعلي أدناه للاستخدام المباشر دون الحاجة لكتابة أوامر:*"
        )
        await self.send_message(
            client, chat_id,
            "✨ *تم تفعيل لوحة الأزرار السفلية الدائمة.*",
            reply_markup=get_main_menu_reply_keyboard()
        )
        await self.send_message(
            client, chat_id,
            welcome_text,
            reply_markup=get_main_menu_inline_keyboard()
        )

    async def handle_message(self, client: httpx.AsyncClient, message: Dict[str, Any]) -> None:
        """Main dispatcher for incoming text messages and voice notes."""
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        user_name = message.get("from", {}).get("first_name", "يا حبيب المسيح")

        if not chat_id or not user_id:
            return

        # Voice Note Handler
        if "voice" in message:
            await self.send_message(
                client, chat_id,
                f"🎤 *أهلاً بك {user_name}! تم استلام رسالتك الصوتية بنجاح.*\n\n"
                "يمكنك تصفح محتويات المكتبة أو البحث الفوري بالضغط على الأزرار الذكية بالأسفل دون عناء الكتابة:",
                reply_markup=get_main_menu_inline_keyboard()
            )
            return

        raw_text = message.get("text", "").strip()
        if not raw_text:
            return

        # 1. Access Control Check (Whitelist)
        if not is_user_authorized(user_id):
            deny_msg = (
                f"⛔ *عذراً {user_name}، هذا البوت خاص بالمصرح لهم فقط.*\n\n"
                f"معرف حسابك (User ID): `{user_id}`\n\n"
                f"يرجى إرسال هذا المعرف للمسؤول لإضافتك إلى قائمة المصرح لهم."
            )
            await self.send_message(client, chat_id, deny_msg)
            return

        # 2. Rate Limiting Check
        if not rate_limiter.is_allowed(user_id):
            rate_msg = "⏳ *تجاوزت الحد المسموح من الطلبات السريعة.*\nيرجى الانتظار بضع ثوانٍ قبل الضغط أو إرسال استفسار جديد."
            await self.send_message(client, chat_id, rate_msg)
            return

        # Sanitize input
        text = sanitize_user_input(raw_text)

        # 3. Main Command Routing (/start, /menu, /help, etc.)
        if text in ["/start", "/menu", "/help", "🔙 القائمة الرئيسية", "القائمة الرئيسية"]:
            _user_states.pop(user_id, None)
            await self.send_welcome_dashboard(client, chat_id, user_name)
            return

        # 4. Handle Master Menu Section 1: 🤖 المساعد الذكي
        if text in ["🤖 المساعد الذكي", "/ask"]:
            _user_states[user_id] = {"mode": "ask_ai"}
            msg = (
                "🤖 *المساعد اللاهوتي والكنسي الذكي:*\n\n"
                "تفضل بكتابة سؤالك اللاهوتي أو الروحي (مثال: `ما هو هدف التجسد؟` أو `كيف أنتصر على الأفكار؟`)، "
                "وسأبحث لك في بطون أمهات الكتب وأجيبك مع توثيق اسم المرجع ورقم الصفحة بدقة."
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_back_to_main_inline_keyboard())
            return

        # 5. Handle Master Menu Section 2: 📚 البحث في المكتبة
        if text in ["📚 البحث في المكتبة", "/search"]:
            _user_states[user_id] = {"mode": "search_book"}
            msg = (
                "📚 *البحث في أسماء وعناوين الكتب:*\n\n"
                "اضغط على أي كتاب أدناه لتنزيله أو تصفحه فوراً، أو اكتب اسم أي كتاب باليد:"
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
            return

        # 6. Handle Master Menu Section 3: 📖 اسأل كتابًا
        if text == "📖 اسأل كتابًا":
            _user_states[user_id] = {"mode": "ask_book_select"}
            msg = (
                "📖 *خاصية «اسأل كتابًا» (Book-Scoped Q&A):*\n\n"
                "اضغط على أحد الكتب أدناه لحصر الإجابة والبحث داخله فقط، أو اكتب اسم كتاب باليد:"
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
            return

        # 7. Handle Master Menu Section 4: ⛪ أقوال الآباء
        if text in ["⛪ أقوال الآباء", "/fathers"]:
            msg = (
                "⛪ *درر من أقوال الآباء القديسين:*\n\n"
                "اختر الموضوع الروحي الذي تريد الاستنارة بأقوال الآباء فيه:"
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_fathers_topics_inline_keyboard())
            return

        # 8. Handle Master Menu Section 5: 🔍 البحث حسب المؤلف
        if text in ["🔍 البحث حسب المؤلف", "/authors"]:
            msg = "🔍 *اختر أحد آباء ومعلمي الكنيسة لعرض كتبه ومؤلفاته المسجلة:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_authors_inline_keyboard())
            return

        # 9. Handle Master Menu Section 6: 📂 تصفح التصنيفات
        if text in ["📂 تصفح التصنيفات", "/categories"]:
            msg = "📂 *أقسام وتصنيفات المكتبة الكنسية:*\nاختر القسم المطلوب لتصفح محتوياته:"
            await self.send_message(client, chat_id, msg, reply_markup=get_categories_inline_keyboard())
            return

        # 10. Handle Master Menu Section 7: 📑 أبحاثي المحفوظة
        if text in ["📑 أبحاثي المحفوظة", "/bookmarks"]:
            bookmarks = repo.get_user_bookmarks(user_id, limit=5)
            if not bookmarks:
                await self.send_message(
                    client, chat_id,
                    "📑 *أبحاثي وشواهدي المحفوظة:*\n\n"
                    "لا توجد شواهد محفوظة لديك حتى الآن.\n"
                    "عند إجراء أي بحث، اضغط على زر `⭐ حفظ` لحفظ الشاهد هنا والرجوع إليه في أي وقت بنقرة واحدة!",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return

            bm_lines = ["📑 *الشواهد والأبحاث المحفوظة لديك:*\n"]
            keyboard = []
            for idx, bm in enumerate(bookmarks, 1):
                bm_lines.append(f"*{idx}. {bm['source_reference']}*\n❝ {bm['excerpt'][:180]}... ❞\n")
                sref = bm['book_sha256'][:16]
                keyboard.append([
                    {"text": f"📖 فتح ص {bm['page_number']}", "callback_data": f"page:{sref}:{bm['page_number']}"},
                    {"text": f"🗑️ حذف {idx}", "callback_data": f"del_bm:{bm['id']}"}
                ])
            keyboard.append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, "\n".join(bm_lines), reply_markup={"inline_keyboard": keyboard})
            return

        # 11. Handle Master Menu Section 8: ⚙️ الإعدادات أو الإحصائيات
        if text in ["⚙️ الإعدادات", "/stats"]:
            stats = repo.get_library_stats()
            role_title = "👑 مدير النظام (Admin)" if is_user_admin(user_id) else "👤 باحث مصرح له"
            ai_name = get_ai_provider().provider_name.upper()
            settings_msg = (
                f"⚙️ *لوحة النظام وإحصائيات المكتبة:*\n\n"
                f"• *معرف حسابك (User ID):* `{user_id}`\n"
                f"• *مستوى الصلاحية:* {role_title}\n"
                f"• *إجمالي الكتب الموثقة:* `{stats['total_books']}` كتاباً\n"
                f"• *إجمالي الصفحات:* `{stats['total_pages']:,}` صفحة\n"
                f"• *المقاطع الدلالية في FTS5:* `{stats['indexed_chunks']:,}` فقرة\n"
                f"• *محرك الذكاء الاصطناعي:* `{ai_name}` (خالٍ من الهلوسة)\n"
                f"• *سقف الطلبات:* `{settings.rate_limit_per_minute} طلب/دقيقة`\n"
            )
            await self.send_message(
                client, chat_id, settings_msg,
                reply_markup={"inline_keyboard": [
                    [{"text": "🔄 تحديث الإحصائيات", "callback_data": "menu:stats"}],
                    [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                ]}
            )
            return

        # 12. Handle Master Menu Section 9: ℹ️ حول المكتبة
        if text == "ℹ️ حول المكتبة":
            stats = repo.get_library_stats()
            about_msg = (
                "ℹ️ *منظومة ELANTONY LIBRARY AI* ✠\n\n"
                "مكتبة كنسية رقمية وبحث ذكي متقدم تم بناؤه بأحدث المعايير البرمجية لخدمة كنيسة المسيح والباحثين والخدام.\n\n"
                f"• *إجمالي المراجع الموثقة:* `{stats['total_books']}` مجلداً.\n"
                f"• *إجمالي الصفحات:* `{stats['total_pages']:,}` صفحة.\n"
                f"• *المقاطع الدلالية المفهرسة:* `{stats['indexed_chunks']:,}` فقرة.\n"
                "• *الميزات:* بحث دلالي فوري، قراءة صفحات تفاعلية، توثيق آبائي محكم، ومشاركة مباشرة عبر واتساب.\n\n"
                "_صلوا لأجل امتداد الخدمة._"
            )
            await self.send_message(client, chat_id, about_msg, reply_markup=get_back_to_main_inline_keyboard())
            return

        # 13. Context-Aware User Input Handling
        user_ctx = _user_states.get(user_id, {})
        mode = user_ctx.get("mode")

        if mode == "search_book":
            _user_states.pop(user_id, None)
            books = repo.search_books_by_title_or_author(text, limit=6)
            if not books:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ لم يتم العثور على كتب تطابق: «{text}».",
                    reply_markup=get_quick_books_inline_keyboard()
                )
                return

            keyboard = []
            for b in books:
                clean_name = b["file_name"].replace(".pdf", "")
                if len(clean_name) > 34:
                    clean_name = clean_name[:34] + "..."
                keyboard.append([{"text": f"📖 {clean_name}", "callback_data": f"binfo:{b['sha256'][:16]}"}])

            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(
                client, chat_id,
                f"📚 *الكتب المطابقة لـ «{text}» (اضغط على اسم الكتاب لفتحه):*",
                reply_markup={"inline_keyboard": keyboard}
            )
            return

        if mode == "ask_book_select":
            books = repo.search_books_by_title_or_author(text, limit=5)
            if not books:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ لم أجد كتاباً باسم «{text}». اختر من القائمة أو أعد المحاولة:",
                    reply_markup=get_quick_books_inline_keyboard()
                )
                return

            keyboard = []
            for b in books:
                clean_name = b["file_name"].replace(".pdf", "")
                if len(clean_name) > 34:
                    clean_name = clean_name[:34] + "..."
                keyboard.append([{"text": f"📖 {clean_name}", "callback_data": f"target_book:{b['sha256'][:16]}"}])
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, "اضغط على الكتاب الذي تريد حصر السؤال داخله:", reply_markup={"inline_keyboard": keyboard})
            return

        if mode == "ask_book_query":
            target_sha = user_ctx.get("target_sha")
            _user_states.pop(user_id, None)
            chunks = search_engine.search_scoped_book(target_sha, text, limit=3)
            ai_provider = get_ai_provider()
            answer = ai_provider.generate_answer(text, chunks)

            keyboard = []
            for idx, c in enumerate(chunks, 1):
                share_quote = f"✠ شاهد كنسي موثق من {c.source_reference}:\n{c.chunk_text[:300]}\n\nالمصدر: بوت مكتبة القديس أنطونيوس @ElantonyLibrarybot"
                keyboard.extend(get_chunk_actions_inline_keyboard(c.sha256[:16], c.page_number, idx, share_text=share_quote))
            keyboard.append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])

            await self.send_message(client, chat_id, answer, reply_markup={"inline_keyboard": keyboard})
            return

        # Default Flow: Instant Semantic RAG Search across whole library with Synonym Expansion
        chunks = search_engine.search_fts5(text, limit=6)
        dedicated_books = search_engine.find_dedicated_books(text, limit=3)
        repo.log_search(user_id, text, len(chunks))

        if not chunks and not dedicated_books:
            matched_books = repo.search_books_by_title_or_author(text, limit=4)
            if matched_books:
                keyboard = []
                for b in matched_books:
                    clean_name = b["file_name"].replace(".pdf", "")
                    if len(clean_name) > 34:
                        clean_name = clean_name[:34] + "..."
                    keyboard.append([{"text": f"📖 {clean_name}", "callback_data": f"binfo:{b['sha256'][:16]}"}])
                keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
                await self.send_message(
                    client, chat_id,
                    f"📚 *وجدت لك الكتب التالية المطابقة لـ «{text}» (اضغط على الكتاب لفتحه):*",
                    reply_markup={"inline_keyboard": keyboard}
                )
                return

            reply = (
                f"🔍 *نتائج الاستعلام عن:* «{text}»\n\n"
                f"⚠️ لم يتم العثور على شواهد كنسية مباشرة بهذه الكلمات.\n"
                f"يمكنك اختيار أحد الأقسام أو مؤلفي الكنيسة عبر الأزرار أدناه:"
            )
            await self.send_message(client, chat_id, reply, reply_markup=get_main_menu_inline_keyboard())
            return

        ai_provider = get_ai_provider()
        answer = ai_provider.generate_answer(text, chunks, dedicated_books=dedicated_books)

        keyboard = []
        if dedicated_books:
            for b in dedicated_books[:3]:
                short_title = b["clean_title"]
                if len(short_title) > 30:
                    short_title = short_title[:30] + "..."
                keyboard.append([{"text": f"📘 {short_title}", "callback_data": f"binfo:{b['sha256'][:16]}"}])

        # Compact chunk reader buttons (2 per row)
        chunk_row = []
        for idx, c in enumerate(chunks[:4], 1):
            chunk_row.append({"text": f"📖 شاهد {idx} (ص {c.page_number})", "callback_data": f"page:{c.sha256[:16]}:{c.page_number}"})

        for i in range(0, len(chunk_row), 2):
            keyboard.append(chunk_row[i:i+2])

        keyboard.append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])

        await self.send_message(client, chat_id, answer, reply_markup={"inline_keyboard": keyboard})

    async def handle_callback_query(self, client: httpx.AsyncClient, cb: Dict[str, Any]) -> None:
        """Handles all inline button clicks with rich responsive actions."""
        cb_id = cb.get("id")
        data = cb.get("data", "")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")
        user_id = cb.get("from", {}).get("id")
        user_name = cb.get("from", {}).get("first_name", "يا حبيب المسيح")

        if not chat_id or not user_id or not data:
            return

        # Acknowledge immediately to dismiss Telegram's button loading spinner
        await self.answer_callback_query(client, cb_id, "جاري المعالجة...")

        # 1. Navigation: Main Menu
        if data == "nav:main":
            _user_states.pop(user_id, None)
            await self.send_welcome_dashboard(client, chat_id, user_name)
            return

        # 2. Main Menu Shortcuts
        if data == "menu:ask_ai":
            _user_states[user_id] = {"mode": "ask_ai"}
            msg = (
                "🤖 *المساعد اللاهوتي والكنسي الذكي:*\n\n"
                "اكتب سؤالك في الشات وسأبحث لك فوراً في بطون أمهات الكتب وأجيبك مع توثيق الشواهد."
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_back_to_main_inline_keyboard())
            return

        if data == "menu:search":
            _user_states[user_id] = {"mode": "search_book"}
            msg = "📚 *اضغط على أي كتاب لفتحه وتنزيله فوراً، أو اكتب اسم أي كتاب باليد:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
            return

        if data == "menu:ask_book":
            _user_states[user_id] = {"mode": "ask_book_select"}
            msg = "📖 *اضغط على الكتاب الذي ترغب في حصر السؤال والبحث داخله:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
            return

        if data == "menu:fathers":
            msg = "⛪ *اختر الموضوع الروحي الذي تريد مطالعة أقوال الآباء فيه:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_fathers_topics_inline_keyboard())
            return

        if data == "menu:authors":
            msg = "🔍 *اختر أحد معلمي وآباء الكنيسة لعرض كتبه ومؤلفاته:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_authors_inline_keyboard())
            return

        if data == "menu:categories":
            msg = "📂 *أقسام وتصنيفات المكتبة الكنسية:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_categories_inline_keyboard())
            return

        if data == "menu:bookmarks":
            bookmarks = repo.get_user_bookmarks(user_id, limit=5)
            if not bookmarks:
                await self.send_message(
                    client, chat_id,
                    "📑 لا توجد لديك شواهد محفوظة حالياً. اضغط على `⭐ حفظ` تحت أي نتيجة بحث لحفظها هنا!",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return
            bm_lines = ["📑 *أبحاثك وشواهدك المحفوظة:*\n"]
            keyboard = []
            for idx, bm in enumerate(bookmarks, 1):
                bm_lines.append(f"*{idx}. {bm['source_reference']}*\n❝ {bm['excerpt'][:180]}... ❞\n")
                sref = bm['book_sha256'][:16]
                keyboard.append([
                    {"text": f"📖 فتح ص {bm['page_number']}", "callback_data": f"page:{sref}:{bm['page_number']}"},
                    {"text": f"🗑️ حذف {idx}", "callback_data": f"del_bm:{bm['id']}"}
                ])
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, "\n".join(bm_lines), reply_markup={"inline_keyboard": keyboard})
            return

        if data == "menu:stats":
            stats = repo.get_library_stats()
            stats_msg = (
                f"📊 *إحصائيات المكتبة الكنسية المركزية:*\n\n"
                f"• *إجمالي الكتب الموثقة:* `{stats['total_books']}` مجلداً\n"
                f"• *إجمالي الصفحات:* `{stats['total_pages']:,}` صفحة\n"
                f"• *المقاطع الدلالية في FTS5:* `{stats['indexed_chunks']:,}` فقرة\n"
                f"• *الحجم الإجمالي:* `{stats['total_size_mb']:,} MB`"
            )
            await self.send_message(
                client, chat_id, stats_msg,
                reply_markup={"inline_keyboard": [
                    [{"text": "🔄 تحديث", "callback_data": "menu:stats"}],
                    [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                ]}
            )
            return

        if data == "menu:about":
            stats = repo.get_library_stats()
            about_msg = (
                f"ℹ️ *منظومة ELANTONY LIBRARY AI* ✠\n\n"
                f"مكتبة وبحث ذكي متقدم لخدمة كنيسة المسيح والباحثين والخدام.\n"
                f"تضم `{stats['total_books']}` كتاباً و `{stats['indexed_chunks']:,}` شاهداً آبائياً."
            )
            await self.send_message(client, chat_id, about_msg, reply_markup=get_back_to_main_inline_keyboard())
            return

        # 3. Daily Spiritual Meditation & Exercise
        if data in ["menu:daily", "daily:refresh"]:
            quotes = search_engine.get_patristic_quotes(topic="الصلاة المحبة التوبة النعمة البرية السهر", limit=1)
            if quotes:
                q = quotes[0]
                snippet = q.chunk_text.strip().replace("\n", " ")
                if len(snippet) > 280:
                    snippet = snippet[:280] + "..."
                source = q.source_reference
            else:
                snippet = "الصلاة هي حفظ القلب ونقاوة الضمير، وبها يقتني الإنسان روح الله القدوس وسلام الفكر."
                source = "القديس العظيم الأنبا أنطونيوس كوكب البرية"

            exercises = [
                "خصص 10 دقائق صامتة لترديد صلاة يسوع: «ياربي يسوع المسيح، ارحمني أنا الخاطئ»، وتجنب إدانة أي شخص اليوم في فكرك أو كلامك.",
                "اقرأ إصحاحاً من الإنجيل بتأمل وهدوء، واصنع عملاً خفياً من أعمال المحبة والرحمة دون أن يراك أحد.",
                "قبل أن تبدأ يومك، قف دقيقة شكر لله على كل حال، وتذكر أن كل تجربة تجوز بك هي لنفع نفسك وتزكيتها.",
                "حارب فكر الغضب بالسكوت، وإذا شعرت بضيق في قلبك، الجأ إلى المزامير واطلب معونة النعمة."
            ]
            exercise = random.choice(exercises)

            daily_msg = (
                "🕊️ *تأمل وتدريب اليوم الروحي* ✠\n\n"
                f"📌 *درة من أقوال الآباء:*\n"
                f"❝ {snippet} ❞\n"
                f"_{source}_\n\n"
                f"✨ *التدريب العملي لليوم:*\n"
                f"{exercise}\n\n"
                f"🙏 *صلاة قصيرة:*\n"
                f"«يا رب يسوع، املأ قلبي بمحبتك، وثبتني في إيمان كنيستك القويم إلى النفس الأخير.»"
            )

            share_text = f"🕊️ تأمل وتدريب اليوم الروحي من مكتبة القديس أنطونيوس:\n\n{snippet}\n_{source}_\n\nالتدريب: {exercise}\n\nتابع البوت: @ElantonyLibrarybot"
            encoded_share = urllib.parse.quote(share_text[:500])

            keyboard = [
                [
                    {"text": "💬 مشاركة عبر WhatsApp", "url": f"https://api.whatsapp.com/send?text={encoded_share}"},
                    {"text": "📢 نشر في Telegram", "url": f"https://t.me/share/url?url={encoded_share}"}
                ],
                [
                    {"text": "🔄 تأمل آخر", "callback_data": "daily:refresh"},
                    {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
                ]
            ]
            await self.send_message(client, chat_id, daily_msg, reply_markup={"inline_keyboard": keyboard})
            return

        if data == "menu:manual_search":
            _user_states[user_id] = {"mode": "search_book"}
            await self.send_message(
                client, chat_id,
                "✍️ تفضل بكتابة اسم الكتاب أو جزء من العنوان في الشات الآن:",
                reply_markup=get_back_to_main_inline_keyboard()
            )
            return

        # 4. Book Action Card (binfo:<ref>)
        if data.startswith("binfo:"):
            ref = data.split("binfo:", 1)[1]
            book = repo.get_book_by_ref(ref)
            if not book:
                await self.send_message(
                    client, chat_id,
                    "⚠️ لم يتم العثور على بيانات هذا الكتاب.",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return

            fname = book["file_name"].replace(".pdf", "")
            pages = book["page_count"]
            size_mb = book["file_size"] / (1024 * 1024)
            short_ref = book["sha256"][:16]

            card_msg = (
                f"📖 *كتاب:* «{fname}»\n\n"
                f"📄 *عدد الصفحات:* `{pages}` صفحة\n"
                f"💾 *حجم الملف:* `{size_mb:.1f} MB`\n"
                f"🏷️ *التصنيف:* `{book['category']}`\n\n"
                f"👇 *اضغط على الإجراء المطلوب بنقرة واحدة:*"
            )
            await self.send_message(
                client, chat_id, card_msg,
                reply_markup=get_book_card_inline_keyboard(short_ref)
            )
            return

        # 5. Topic Submenu: Patristic Themes
        if data.startswith("topic:"):
            theme_key = data.split("topic:", 1)[1]
            topic_mapping = {
                "prayer": "الصلاة السهر الهدوء الدموع",
                "repentance": "التوبة نقاوة القلب البكاء",
                "warfare": "الجهاد محاربة الأفكار الشياطين الصبر",
                "love": "المحبة السلام الوداعة التسامح",
                "humility": "التواضع الاتضاع إنكار الذات الطاعة",
                "random": "النعمة الإيمان البرية الصليب الفداء"
            }
            search_query = topic_mapping.get(theme_key, "الصلاة التوبة")
            quotes = search_engine.get_patristic_quotes(topic=search_query, limit=3)
            if not quotes:
                await self.send_message(
                    client, chat_id,
                    "⚠️ لم يتم العثور على أقوال مسترجعة لهذا الموضوع حالياً.",
                    reply_markup=get_fathers_topics_inline_keyboard()
                )
                return

            reply_parts = [f"⛪ *درر من أقوال الآباء في هذا الباب:*\n"]
            keyboard = []
            for idx, q in enumerate(quotes, 1):
                snippet = q.chunk_text.strip().replace("\n", " ")[:280]
                reply_parts.append(f"*{idx}. {q.source_reference}*\n❝ {snippet}... ❞\n")
                share_quote = f"✠ قول آبائي موثق:\n{snippet}\n_{q.source_reference}_\n\nبوت @ElantonyLibrarybot"
                keyboard.extend(get_chunk_actions_inline_keyboard(q.sha256[:16], q.page_number, idx, share_text=share_quote))

            keyboard.append([{"text": "🔙 موضوع آخر", "callback_data": "menu:fathers"}])
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, "\n".join(reply_parts), reply_markup={"inline_keyboard": keyboard})
            return

        # 6. Action: pdf:<ref> (Download full book)
        if data.startswith("pdf:"):
            ref = data.split("pdf:", 1)[1]
            book = repo.get_book_by_ref(ref)
            if book:
                file_path = book["original_path"]
                fname = book["file_name"]
                await self.send_document(client, chat_id, file_path, caption=f"📖 {fname}")
            else:
                await self.send_message(client, chat_id, "⚠️ لم يتم العثور على مسار الكتاب في قاعدة البيانات.")
            return

        # 7. Action: page:<ref>:<page_num> (Read specific page with live page-flipper)
        if data.startswith("page:"):
            parts = data.split(":")
            if len(parts) >= 3:
                ref, page_num = parts[1], int(parts[2])
                book = repo.get_book_by_ref(ref)
                if not book:
                    await self.send_message(client, chat_id, "⚠️ لم يتم العثور على الكتاب.")
                    return
                sha256 = book["sha256"]
                txt_file = settings.extracted_text_dir / f"{sha256}.txt"
                if txt_file.exists():
                    with open(txt_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    from modules.rag_chunker import parse_pages_from_extracted_text
                    pages = parse_pages_from_extracted_text(content)
                    target = next((p for p in pages if p["page_num"] == page_num), None)
                    if target and target["text"].strip():
                        page_msg = f"📄 *نص الصفحة {page_num} من «{book['file_name']}»:*\n\n{target['text'][:3500]}"
                        await self.send_message(
                            client, chat_id, page_msg,
                            reply_markup=get_page_reader_inline_keyboard(sha256[:16], page_num)
                        )
                    else:
                        await self.send_message(client, chat_id, f"⚠️ الصفحة {page_num} فارغة أو قيد المعالجة الضوئية.")
                else:
                    await self.send_message(client, chat_id, "⚠️ لم يتم العثور على نصوص مفهرسة لهذا الكتاب بعد.")
            return

        # 8. Action: bm:<ref>:<page_num> (Save to user bookmarks)
        if data.startswith("bm:"):
            parts = data.split(":")
            if len(parts) >= 3:
                ref, page_num = parts[1], int(parts[2])
                book = repo.get_book_by_ref(ref)
                if book:
                    sha256 = book["sha256"]
                    title = book["file_name"]
                    source_ref = f"[كتاب: {Path(title).stem}، ص: {page_num}]"
                    repo.save_bookmark(
                        user_id=user_id,
                        book_sha256=sha256,
                        book_title=title,
                        page_number=page_num,
                        source_reference=source_ref,
                        excerpt=f"تم حفظ الشاهد من {title}"
                    )
                    await self.send_message(
                        client, chat_id,
                        f"⭐ *تم حفظ الشاهد بنجاح في «أبحاثي المحفوظة»:*\n{source_ref}",
                        reply_markup={"inline_keyboard": [
                            [{"text": "📑 عرض أبحاثي المحفوظة", "callback_data": "menu:bookmarks"}],
                            [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                        ]}
                    )
            return

        # 9. Action: del_bm:<bookmark_id> (Delete a bookmark)
        if data.startswith("del_bm:"):
            bm_id = int(data.split("del_bm:", 1)[1])
            deleted = repo.delete_bookmark(bm_id, user_id)
            if deleted:
                await self.send_message(
                    client, chat_id,
                    "🗑️ تم حذف الشاهد من أبحاثك المحفوظة.",
                    reply_markup={"inline_keyboard": [
                        [{"text": "📑 العودة لأبحاثي", "callback_data": "menu:bookmarks"}],
                        [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                    ]}
                )
            return

        # 10. Action: target_book:<ref> (Lock context for Ask a Book)
        if data.startswith("target_book:"):
            ref = data.split("target_book:", 1)[1]
            book = repo.get_book_by_ref(ref)
            if book:
                target_sha = book["sha256"]
                title = book["file_name"]
                _user_states[user_id] = {"mode": "ask_book_query", "target_sha": target_sha}
                msg = f"📖 *تم تحديد كتاب:* «{title}» بنجاح!\n\nتفضل بكتابة سؤالك الآن وسأبحث لك حصرياً داخل هذا الكتاب:"
                await self.send_message(client, chat_id, msg, reply_markup=get_back_to_main_inline_keyboard())
            else:
                await self.send_message(client, chat_id, "⚠️ لم يتم العثور على الكتاب المحدد.")
            return

        # 11. Action: auth:<author_key> (Filter books by author)
        if data.startswith("auth:"):
            auth_key = data.split("auth:", 1)[1]
            author_names = {
                "shenouda": "البابا شنودة",
                "athanasius": "أثناسيوس",
                "cyril": "كيرلس",
                "antony": "أنطونيوس",
                "jerome": "جيروم",
                "matta": "متى المسكين"
            }
            term = author_names.get(auth_key, auth_key)
            books = repo.search_books_by_title_or_author(term, limit=6)
            if not books:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ لم يتم العثور على كتب مسجلة للمؤلف: {term}",
                    reply_markup=get_authors_inline_keyboard()
                )
                return

            keyboard = []
            for b in books:
                clean_name = b["file_name"].replace(".pdf", "")
                if len(clean_name) > 34:
                    clean_name = clean_name[:34] + "..."
                keyboard.append([{"text": f"📖 {clean_name}", "callback_data": f"binfo:{b['sha256'][:16]}"}])

            keyboard.append([{"text": "🔙 مؤلف آخر", "callback_data": "menu:authors"}])
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(
                client, chat_id,
                f"🔍 *مؤلفات {term} (اضغط على اسم الكتاب لفتحه):*",
                reply_markup={"inline_keyboard": keyboard}
            )
            return

        # 12. Action: cat:<category_key> (Filter books by category)
        if data.startswith("cat:"):
            cat_key = data.split("cat:", 1)[1]
            cat_names = {
                "patristics": "أبائيات",
                "dogmatics": "عقيدة",
                "bible": "تفسير",
                "rituals": "طقس",
                "spiritual": "روحيات",
                "history": "تاريخ"
            }
            term = cat_names.get(cat_key, cat_key)
            books = repo.search_books_by_title_or_author(term, limit=6)
            if not books:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ لا توجد كتب مسجلة حالياً في قسم: {term}",
                    reply_markup=get_categories_inline_keyboard()
                )
                return

            keyboard = []
            for b in books:
                clean_name = b["file_name"].replace(".pdf", "")
                if len(clean_name) > 34:
                    clean_name = clean_name[:34] + "..."
                keyboard.append([{"text": f"📖 {clean_name}", "callback_data": f"binfo:{b['sha256'][:16]}"}])

            keyboard.append([{"text": "🔙 قسم آخر", "callback_data": "menu:categories"}])
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(
                client, chat_id,
                f"📂 *كتب قسم {term} (اضغط على اسم الكتاب لفتحه):*",
                reply_markup={"inline_keyboard": keyboard}
            )
            return
