# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Telegram Request & Callback Handlers
Implements robust business logic for the 9 master menu sections, interactive submenus,
live page-turning book reader, book action cards, and one-click social sharing.
All callback_data payloads strictly respect Telegram's 64-byte hard limit.
"""

import os
import asyncio
import random
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from elantony.core.config import settings
from elantony.core.security import is_user_authorized, is_user_admin, sanitize_user_input
from elantony.core.rate_limiter import rate_limiter
from elantony.core.logging import logger
from elantony.core.text_cleaner import clean_theological_text
from elantony.database.connection import get_connection
from elantony.database.repository import repo
from elantony.search.search_engine import search_engine
from elantony.ai.factory import get_ai_provider
from elantony.telegram.commands import (
    DAILY_VERSES,
    send_admin_dashboard,
    send_harvest_drive,
    send_harvest_tg,
    send_synaxarium,
    send_daily_verse,
    handle_gdrive_sync_callback,
    handle_verse_audio_callback,
    send_voice_bytes,
    send_special_commands_menu
)
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
    get_back_to_main_inline_keyboard,
    get_catalog_hub_inline_keyboard,
    get_catalog_topics_inline_keyboard,
    get_catalog_authors_inline_keyboard,
    get_catalog_alphabet_inline_keyboard,
    get_catalog_paginated_books_keyboard,
    get_random_book_inline_keyboard,
    get_encyclopedias_inline_keyboard,
    get_reference_card_keyboard,
    get_source_filter_keyboard,
    format_reference_card
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

    async def send_long_message(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Splits long theological studies into sequential parts respecting Telegram's 4096 char limit."""
        if len(text) <= 3900:
            return await self.send_message(client, chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)

        # Split on section or paragraph boundaries
        paragraphs = text.split("\n\n")
        chunks = []
        curr = []
        curr_len = 0
        for p in paragraphs:
            if curr_len + len(p) + 2 > 3700 and curr:
                chunks.append("\n\n".join(curr))
                curr = [p]
                curr_len = len(p)
            else:
                curr.append(p)
                curr_len += len(p) + 2
        if curr:
            chunks.append("\n\n".join(curr))

        total = len(chunks)
        success = True
        for i, chunk in enumerate(chunks, 1):
            header = f"*(الجزء {i} من {total})*\n\n" if total > 1 else ""
            kb = reply_markup if i == total else None
            ok = await self.send_message(client, chat_id, header + chunk, parse_mode=parse_mode, reply_markup=kb)
            if not ok:
                success = False
            await asyncio.sleep(0.4)
        return success

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

    async def send_voice_bytes(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        audio_bytes: bytes,
        filename: str = "verse.mp3",
        caption: str = ""
    ) -> bool:
        return await send_voice_bytes(self, client, chat_id, audio_bytes, filename, caption)

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

    async def compile_and_send_session(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        user_id: int,
        target_session_id: Optional[str] = None
    ) -> None:
        """Compiles active or target discussion session into a unified monograph and sends in chat and as a file."""
        if target_session_id:
            s_id = target_session_id
        else:
            active_sess = repo.get_or_create_active_session(str(user_id))
            s_id = active_sess["id"]

        comp = repo.compile_session(s_id)
        if comp.get("turns_count", 0) == 0:
            await self.send_message(
                client, chat_id,
                "⚠️ *لم تسجل أي أسئلة أو إجابات في جلستك الحالية بعد.*\n\n"
                "تفضل بطرح أي سؤال وسأجيبك وأحفظ كل الأسئلة في الذاكرة لتجميعها بنقرة واحدة!",
                reply_markup=get_back_to_main_inline_keyboard()
            )
            return

        await self.send_message(
            client, chat_id,
            f"⏳ *جاري تجميع أطروحة البحث اللاهوتية:* «{comp.get('title', '')}»\n"
            f"📊 تم إحصاء `{comp.get('turns_count', 0)}` محاور وأسئلة فرعية..."
        )

        # 1. Send monograph in chat
        await self.send_long_message(client, chat_id, comp["plain_text"])

        # 2. Generate clean research Word document (.docx) and send it directly
        doc_dir = settings.base_dir / "data" / "compiled_researches"
        doc_dir.mkdir(parents=True, exist_ok=True)
        docx_path = doc_dir / f"research_{s_id}.docx"
        try:
            from elantony.services.docx_exporter import generate_session_docx
            generate_session_docx(comp, str(docx_path))
            caption = f"📄 أطروحة بحثية لاهوتية مجمعة (ملف Word): «{comp.get('title', '')}» | منظومة ELANTONY AI"
            await self.send_document(client, chat_id, str(docx_path), caption=caption)
        except Exception as e:
            logger.warning(f"Could not generate or send compiled Word file: {e}")
            txt_path = doc_dir / f"research_{s_id}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(comp["plain_text"])
            await self.send_document(client, chat_id, str(txt_path), caption=f"📄 أطروحة بحثية: «{comp.get('title', '')}»")

        # 3. Action buttons
        kb = [
            [
                {"text": "🔄 بدء بحث جديد", "callback_data": "session:new"},
                {"text": "📂 أبحاثي السابقة", "callback_data": "session:history"}
            ],
            [
                {"text": "⚙️ عمق الإجابة", "callback_data": "menu:depth"},
                {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
            ]
        ]
        await self.send_message(
            client, chat_id,
            "💡 *تم توثيق وتجميع بحثك بنجاح كملف Word كامل! يمكنك بدء بحث جديد أو اختيار أحد الخيارات أدناه:*",
            reply_markup={"inline_keyboard": kb}
        )

    async def send_welcome_dashboard(self, client: httpx.AsyncClient, chat_id: int, user_name: str) -> None:
        """Sends the master dashboard with persistent keyboard AND rich inline buttons."""
        stats = repo.get_library_stats()
        safe_name = str(user_name).replace("_", " ").replace("*", "").replace("`", "").strip()
        if not safe_name:
            safe_name = "يا حبيب المسيح"
        welcome_text = (
            f"✠ *مرحباً بك {safe_name} في منظومة ELANTONY LIBRARY AI* ✠\n\n"
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

    async def send_catalog_hub(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends the Master Catalog Hub."""
        stats = repo.get_library_stats()
        text = (
            "📑 *فهرس مكتبة القديس أنطونيوس الشامل* 📑\n\n"
            f"📚 *إجمالي الكتب المتاحة:* `{stats['total_books']:,}` كتاباً ومجلداً.\n"
            f"📄 *إجمالي الصفحات:* `{stats['total_pages']:,}` صفحة مفهرسة بالكامل.\n\n"
            "اختر طريقة التصفح والاستعراض التي تناسبك عبر الأزرار الذكية أدناه:"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_catalog_hub_inline_keyboard())

    async def send_catalog_topics(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends the master theological categories."""
        cats = repo.get_catalog_categories_overview()
        text = (
            "📂 *فهرس الكتب حسب الموضوع والتصنيف الكنسي:*\n\n"
            "اضغط على أي قسم لعرض قائمة كتبه بنظام الصفحات مع إمكانية التنزيل والقراءة الفورية:"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_catalog_topics_inline_keyboard(cats))

    async def send_catalog_authors(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends the patristic authors list."""
        authors = repo.get_catalog_authors_overview()
        text = (
            "✍️ *فهرس الكتب حسب الآباء والمؤلفين:*\n\n"
            "اختر أحد آباء ومعلمي الكنيسة لاستعراض قائمة مؤلفاته وكتبه المسجلة بالمكتبة:"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_catalog_authors_inline_keyboard(authors))

    async def send_catalog_alphabet(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends the alphabet grid."""
        text = (
            "🔤 *الفهرس الأبجدي لعناوين الكتب (من أ إلى ي):*\n\n"
            "اضغط على أي حرف لعرض جميع الكتب التي تبدأ بهذا الحرف:"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_catalog_alphabet_inline_keyboard())

    async def send_catalog_encyclopedias(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends major foundational encyclopedias."""
        books = repo.get_major_encyclopedias()
        text = (
            "🏛️ *أمهات الكتب والموسوعات الكنسية الكبرى:*\n\n"
            "نخبة من أمهات المراجع والموسوعات التفسيرية واللاهوتية والرهبانية الأساسية:"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_encyclopedias_inline_keyboard(books))

    async def send_catalog_random_book(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends a random featured book card."""
        book = repo.get_random_featured_book()
        if not book:
            await self.send_message(client, chat_id, "⚠️ تعذر جلب كتاب عشوائي حالياً.")
            return

        fname = book["file_name"].replace(".pdf", "")
        author = book.get("author") or "آباء ومعلمو الكنيسة"
        category = book.get("category") or "كتب كنسية"
        pages = book.get("page_count", 0)
        size_mb = book.get("file_size", 0) / (1024 * 1024)

        text = (
            f"🎲 *ترشيح كتاب اليوم من كنوز المكتبة:*\n\n"
            f"📖 *عنوان الكتاب:* «{fname}»\n"
            f"✍️ *المؤلف:* `{author}`\n"
            f"🏷️ *القسم:* `{category}`\n"
            f"📄 *عدد الصفحات:* `{pages}` صفحة\n"
            f"💾 *الحجم:* `{size_mb:.1f} MB`\n\n"
            f"👇 *اضغط على الإجراء المطلوب بنقرة واحدة:*"
        )
        await self.send_message(client, chat_id, text, reply_markup=get_random_book_inline_keyboard(book["sha256"]))


    async def send_synaxarium(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends today's Synaxarium commemorations with liturgical reflections."""
        from datetime import datetime
        now = datetime.now()
        chunks = search_engine.search_fts5("سنكسار أعياد القديسين", limit=2)
        
        synax_text = (
            f"📜 *سنكسار اليوم المبارك وقراءات الكنيسة القبطية* ✠\n\n"
            f"📅 *التاريخ الميلادي:* `{now.strftime('%Y-%m-%d')}`\n"
            f"🕊️ *بركة صلوات وشفاعة آباء وقديسي هذا اليوم فلتكن مع جميعنا، آمين.*\n\n"
            "✨ *من كنوز السنكسار وسير الآباء بالمكتبة:*\n"
        )
        if chunks:
            for c in chunks:
                synax_text += f"• *{c.book_title}* (ص {c.page_number}):\n❝ {c.chunk_text[:220].strip()}... ❞\n\n"
        else:
            synax_text += "• تذكار القديسين والشهداء الأبرار الذين أرضوا الرب منذ البدء بحياتهم وجهادهم المقدس.\n\n"
            
        synax_text += "💡 *يمكنك كتابة اسم أي قديس (مثلاً: «مارجرجس» أو «الأنبا أنطونيوس») لقراءة سيرته وأقواله بالتفصيل!*"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "⛪ درر أقوال الآباء", "callback_data": "menu:fathers"}],
                [{"text": "📖 آية وتفسير آبائي", "callback_data": "menu:daily_verse"}],
                [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
            ]
        }
        await self.send_message(client, chat_id, synax_text, reply_markup=keyboard)

    async def send_daily_verse(self, client: httpx.AsyncClient, chat_id: int) -> None:
        """Sends daily scripture verse with verified patristic commentary from library."""
        verses = [
            ("«تَعَالَوْا إِلَيَّ يَا جَمِيعَ الْمُتْعَبِينَ وَالثَّقِيلِي الأَحْمَالِ، وَأَنَا أُرِيحُكُمْ.» (متى 11: 28)",
             "القديس يوحنا ذهبي الفم", "راحة المسيح ليست مجرد سكون، بل هي نزع ثقل الخطية وتجديد النفس بنعمة الروح القدس."),
            ("«أَنَا هُوَ الْقِيَامَةُ وَالْحَيَاةُ. مَنْ آمَنَ بِي وَلَوْ مَاتَ فَسَيَحْيَا.» (يوحنا 11: 25)",
             "القديس كيرلس الكبير", "بما أن الكلمة هو الحياة بالطبيعة، فإنه لما اتحد بجسدنا أباد الموت وسكب الحياة الأبدية في جبلتنا."),
            ("«كُلُّ الأَشْيَاءِ تَعْمَلُ مَعاً لِلْخَيْرِ لِلَّذِينَ يُحِبُّونَ اللهَ.» (رومية 8: 28)",
             "القديس باسيليوس الكبير", "لا تحزن إذا حلت بك ضيقة، فإن الطبيب السماوي يجري جراحة الشفاء لخلاص نفسك الأبدي."),
            ("«اَللهُ مَحَبَّةٌ، وَمَنْ يَثْبُتْ فِي الْمَحَبَّةِ، يَثْبُتْ فِي اللهِ وَاللهُ فِيهِ.» (1 يوحنا 4: 16)",
             "القديس أثناسيوس الرسولي", "المحبة الإلهية هي علة التجسد والفداء، وبها نصير شركاء الطبيعة الإلهية بالنعمة.")
        ]
        import random
        v, father, exp = random.choice(verses)
        
        verse_msg = (
            f"📖 *شاهد اليوم والتعليم الآبائي المعتمد* ✠\n\n"
            f"💎 *الآية الكريمة:*\n{v}\n\n"
            f"🏛️ *شرح {father}:*\n❝ {exp} ❞\n\n"
            "💡 *يمكنك نسخ الشاهد وسؤال المساعد: «اشرح لي هذا الشاهد لاهوتياً» لدراسة أكاديمية موسعة!*"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "📜 سنكسار اليوم القبطي", "callback_data": "menu:synaxarium"}],
                [{"text": "⛪ درر أقوال الآباء", "callback_data": "menu:fathers"}],
                [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
            ]
        }
        await self.send_message(client, chat_id, verse_msg, reply_markup=keyboard)

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

        # Document / Direct PDF Book Upload Handler
        if "document" in message:
            doc = message["document"]
            file_name = doc.get("file_name", "book.pdf")
            file_size = doc.get("file_size", 0)
            file_id = doc.get("file_id")

            if not file_name.lower().endswith(".pdf"):
                await self.send_message(
                    client, chat_id,
                    "⚠️ *عذراً، يدعم المساعد استقبال ملفات الكتب بصيغة PDF فقط.*",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return

            if file_size > 50 * 1024 * 1024:
                await self.send_message(
                    client, chat_id,
                    "⚠️ *حجم الملف كبير (أكثر من 50 ميجابايت) للإرسال المباشر عبر تيليجرام.*\nيرجى نسخه مباشرة داخل مجلد المكتبة بالكمبيوتر وسيلتقطه النظام فوراً في الخلفية.",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return

            # Admin authorization check for uploading new books
            if not is_user_admin(user_id):
                await self.send_message(
                    client, chat_id,
                    "⛔ *خاصية إضافة وتزويد المكتبة بكتب جديدة مخصصة للمسؤول (Admin) فقط.*"
                )
                return

            await self.send_message(
                client, chat_id,
                f"⏳ *جاري استلام كتاب:* «{file_name}»\n"
                f"📊 *الحجم:* `{file_size / (1024*1024):.1f} MB`\n\n"
                "يرجى الانتظار بضع ثوانٍ أثناء التنزيل، والفحص اللغوي، والتصنيف الكنسي، والفهرسة الذكية..."
            )

            try:
                get_file_url = f"{self.api_base}/getFile?file_id={file_id}"
                file_info_res = await client.get(get_file_url, timeout=15.0)
                if file_info_res.status_code == 200:
                    tg_file_path = file_info_res.json().get("result", {}).get("file_path")
                    if tg_file_path:
                        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{tg_file_path}"
                        intake_dir = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\كتب جديدة_وارد_تيليجرام")
                        if not intake_dir.parent.exists():
                            intake_dir = settings.base_dir / "books" / "telegram_uploads"
                        intake_dir.mkdir(parents=True, exist_ok=True)
                        dest_file = intake_dir / file_name

                        async with client.stream("GET", download_url, timeout=90.0) as resp:
                            if resp.status_code == 200:
                                with open(dest_file, "wb") as f_out:
                                    async for chunk_bytes in resp.aiter_bytes():
                                        f_out.write(chunk_bytes)

                        from services.permanent_assistant.ingestion_pipeline import auto_ingestor
                        result = auto_ingestor.ingest_pdf(dest_file)

                        if result.get("success"):
                            tier = result.get("authenticity_tier", 3)
                            pages = result.get("pages", 0)
                            chunks = result.get("chunks_count", 0)
                            author = result.get("author", "غير محدد")
                            s_types = ", ".join(result.get("source_types", ["دراسات كنسية"]))

                            confirm_msg = (
                                "🎉 *تم استلام الكتاب ودمجه في عقل المكتبة الذكية بنجاح!* ✠\n\n"
                                f"📚 *اسم الكتاب:* «{dest_file.stem}»\n"
                                f"👤 *المؤلف المعتمد:* `{author}`\n"
                                f"📄 *عدد الصفحات:* `{pages}` صفحة\n"
                                f"⚡ *المقاطع الدلالية في FTS5:* `+{chunks}` مقطعاً\n"
                                f"🏛️ *مرتبة التوثيق:* `Tier {tier}`\n"
                                f"🏷️ *التصنيف:* `{s_types}`\n\n"
                                "💡 *الكتاب الآن مفهرس ومتاح للبحث والأسئلة الذكية فوراً!*"
                            )
                            sref = result.get("sha256", "")[:16]
                            await self.send_message(
                                client, chat_id, confirm_msg,
                                reply_markup=get_book_card_inline_keyboard(sref)
                            )
                            return
                        else:
                            await self.send_message(
                                client, chat_id,
                                f"⚠️ تعذر استكمال فهرسة الكتاب: {result.get('error')}",
                                reply_markup=get_back_to_main_inline_keyboard()
                            )
                            return
            except Exception as doc_err:
                logger.error(f"Telegram document ingestion error: {doc_err}")
                await self.send_message(
                    client, chat_id,
                    f"⚠️ حدث خطأ أثناء تنزيل أو معالجة الكتاب: {doc_err}",
                    reply_markup=get_back_to_main_inline_keyboard()
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

        # Normalized slash command extraction
        parts = text.split()
        first_token = parts[0] if parts else ""
        cmd = first_token.split("@")[0].lower() if first_token.startswith("/") else ""

        # 0. /commands or special commands menu
        if cmd in ["/commands", "/tools", "/menu_commands"] or text in ["قائمة الأوامر", "الأوامر الخاصة", "⚡ قائمة الأوامر الخاصة", "⚡ قائمة الأوامر والتحكم"]:
            await send_special_commands_menu(self, client, chat_id)
            return

        # 1. /admin_dashboard
        if cmd == "/admin_dashboard" or text in ["لوحة الإشراف", "لوحة التحكم", "لوحة الادمن", "إحصائيات المكتبة", "📊 لوحة الإشراف"]:
            await send_admin_dashboard(self, client, chat_id, user_id)
            return

        # 2. /harvest_drive
        if cmd == "/harvest_drive" or text in ["سحب جوجل درايف", "وارد جوجل درايف", "مكتبات جوجل درايف", "جوجل درايف", "🌐 سحب جوجل درايف"]:
            await send_harvest_drive(self, client, chat_id)
            return

        # 3. /harvest_tg
        if cmd == "/harvest_tg" or text in ["قنوات تليجرام", "مكتبات تليجرام", "دليل القنوات", "تليجرام", "📡 قنوات تليجرام"]:
            await send_harvest_tg(self, client, chat_id)
            return

        # 4. /synaxarium
        if cmd == "/synaxarium" or text in ["/synaxarium", "📜 سنكسار اليوم", "سنكسار اليوم", "سنكسار", "السنكسار"]:
            await send_synaxarium(self, client, chat_id)
            return

        # 5. /verse
        if cmd == "/verse" or text in ["/verse", "📖 آية وتفسير آبائي", "آية وتفسير آبائي", "اية وتفسير ابائي", "اية اليوم", "آية اليوم", "شاهد اليوم"]:
            await send_daily_verse(self, client, chat_id)
            return

        # 6. /compile
        if cmd == "/compile" or text in [
            "/compile", "📑 تجميع البحث", "تجميع البحث", "تجميع الموضوع",
            "اجمع الموضوع", "اجمع لي الموضوع", "تجميع المناقشة", "لخص المناقشة",
            "تجميع", "تجميع الأسئلة"
        ]:
            await self.compile_and_send_session(client, chat_id, user_id)
            return

        # Direct Google Drive Link Detection
        if "drive.google.com" in text:
            await self.send_message(client, chat_id, "📥 *تم رصد رابط Google Drive!*\nجاري فحص الملف وتنزيله وفهرسته في المكتبة فوراً...")
            from elantony.services.gdrive_harvester import gdrive_harvester
            harvest_file_res = await asyncio.to_thread(gdrive_harvester.download_single_file, text.strip())
            if harvest_file_res.get("success"):
                fname = harvest_file_res.get("file", "كتاب جديد")
                await self.send_message(
                    client, chat_id,
                    f"✅ *تم بنجاح استلام وفهرسة الكتاب:* «{fname}»!\nأصبح الكتاب متاحاً الآن في ذاكرة المساعد الذكي والبحث الفوري.",
                    reply_markup=get_main_menu_inline_keyboard()
                )
            else:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ تعذر تنزيل الملف مباشرة: {harvest_file_res.get('error', 'يرجى التأكد من صلاحية الرابط وتصريح المشاركة')}",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
            return

        # 3.02 Telegram Channels Harvester Command
        if text.startswith("/harvest_tg") or text in ["قنوات تليجرام", "مكتبات تليجرام"]:
            from elantony.services.telegram_harvester import telegram_harvester
            channels = telegram_harvester.get_catalog()
            stats = telegram_harvester.get_harvested_stats()
            
            msg = (
                "📡 *دليل قنوات ومكتبات تليجرام الكنسية المعتمدة للحصاد* ✠\n\n"
                f"📊 *الكتب المستلمة والمفهرسة من تليجرام حتى الآن:* `{stats['total_books_harvested']}` كتب (`{stats['total_size_mb']} MB`)\n"
                f"📁 *المجلد المحلي:* `{stats['directory']}`\n\n"
                "👇 *اضغط على أي قناة للانتقال إليها وتصفح محتوياتها:*\n\n"
            )
            keyboard = []
            for ch in channels:
                msg += f"• *{ch['name']}* ({ch['username']})\n  _{ch['category']}_\n\n"
                clean_user = ch['username'].replace('@', '')
                keyboard.append([{"text": f"🔗 فتح: {ch['name'][:28]}", "url": f"https://t.me/{clean_user}"}])
                
            msg += "💡 *طريقة الإضافة الفورية للمكتبة:*\nعندما تجد أي كتاب يعجبك في أي قناة، اضغط على زر *(Forward / إعادة توجيه)* وأرسله هنا مباشرة للبوت، وسيقوم بتنزيله وفهرسته على جهازك تلقائياً!"
            keyboard.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, msg, reply_markup={"inline_keyboard": keyboard})
            return

        # 3. Main Command Routing (/start, /menu, /help, etc.)
        if cmd in ["/start", "/menu", "/help"] or text in [
            "/start", "/menu", "/help",
            "🔙 القائمة الرئيسية", "القائمة الرئيسية",
            "🔙 العودة للقائمة الرئيسية", "العودة للقائمة الرئيسية",
            "العودة الى القائمة الرئيسية", "العودة إلي القائمة الرئيسية",
            "🔙 العودة الى القائمة الرئيسية", "🔙 العودة إلي القائمة الرئيسية",
            "الرئيسية", "رجوع"
        ]:
            _user_states.pop(user_id, None)
            await self.send_welcome_dashboard(client, chat_id, user_name)
            return

        # 3.1 Handle Multi-turn Research Compilation Command
        if cmd in ["/compile", "/export", "/word"] or text in [
            "/compile", "📑 تجميع البحث", "تجميع البحث", "تجميع الموضوع",
            "اجمع الموضوع", "اجمع لي الموضوع", "تجميع المناقشة", "لخص المناقشة",
            "تجميع", "تجميع الأسئلة"
        ] or text.startswith("/compile"):
            await self.compile_and_send_session(client, chat_id, user_id)
            return

        # 3.2 Handle New Research Discussion Session Command
        if cmd in ["/new", "/session_new"] or text in [
            "/new", "🔄 بحث جديد", "بحث جديد", "محادثة جديدة", "جلسة جديدة"
        ] or text.startswith("/new"):
            new_id = repo.create_session(str(user_id))
            _user_states.pop(user_id, None)
            new_msg = (
                "✨ *تم فتح جلسة بحثية جديدة بنجاح!* ✠\n\n"
                "💡 *كيف تعمل الذاكرة البحثية؟*\n"
                "1. اطرح سؤالك اللاهوتي الأول وسأجيبك بأعمق الشواهد والصفحات.\n"
                "2. اسأل أسئلة فرعية وتعقيبات متتالية، وسأتذكر كل ما ناقشناه معاً.\n"
                "3. عندما تنتهي، اضغط في أي وقت على زر `📑 تجميع البحث` وسأجمع لك الموضوع كاملاً (كل سؤال وتحته إجابته وشواهده مع فهرس ومكتبة بيبليوغرافية شاملة)!"
            )
            await self.send_message(
                client, chat_id, new_msg,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🤖 ابدأ السؤال الآن", "callback_data": "menu:ask_ai"}],
                        [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                    ]
                }
            )
            return

        # 3.3 Handle Past Research History Command
        if cmd in ["/history", "/sessions"] or text in ["/history", "📑 أبحاثي السابقة", "أبحاثي السابقة"]:
            sessions = repo.list_user_sessions(str(user_id), limit=10)
            if not sessions:
                await self.send_message(
                    client, chat_id,
                    "📑 *أبحاثي ومناقشاتي السابقة:*\n\nلا توجد مناقشات سابقة مسجلة حتى الآن.\nابدأ بطرح سؤالك وسيتم حفظ كل جلسة تلقائياً!",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return
            hist_kb = []
            for s in sessions[:8]:
                title_clean = s.get("title", "بحث لاهوتي")[:30]
                hist_kb.append([{"text": f"💬 {title_clean} ({s.get('message_count', 0)} رد)", "callback_data": f"sess:view:{s['id']}"}])
            hist_kb.append([{"text": "🔄 بدء بحث جديد", "callback_data": "session:new"}])
            hist_kb.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(
                client, chat_id,
                "📑 *أبحاثك ومناقشاتك المحفوظة في ذاكرة المساعد:*\nاختر أي بحث لمراجعته أو تجميعه فوراً:",
                reply_markup={"inline_keyboard": hist_kb}
            )
            return

        # 3.4 Handle Depth & Reasoning Mode Selector
        if cmd in ["/depth", "/mode"] or text in ["/depth", "⚙️ عمق الإجابة", "عمق الإجابة", "نمط الإجابة"]:
            curr_mode = _user_states.get(user_id, {}).get("depth_mode", "academic")
            from elantony.telegram.keyboards import get_depth_selection_inline_keyboard
            depth_msg = (
                "⚙️ *إعدادات عمق الإجابة والنمط اللاهوتي:* ✠\n\n"
                "اختر النمط المناسب لاحتياجك الحالي:\n\n"
                "• *🎓 أكاديمي موسع:* دراسات مستفيضة ومراجع آبائية دقيقة.\n"
                "• *🕊️ رعوي وروحي:* إجابات مركزة ومبسطة للبناء الروحي.\n"
                "• *⚖️ دفاعي مقارن:* ردود وبراهين كتابية وتاريخية."
            )
            await self.send_message(client, chat_id, depth_msg, reply_markup=get_depth_selection_inline_keyboard(curr_mode))
            return

        # 4. Handle Master Menu Section 1: 🤖 المساعد الذكي
        if cmd in ["/ask", "/question"] or text in ["🤖 المساعد الذكي", "/ask"]:
            query_arg = text[len(first_token):].strip() if cmd in ["/ask", "/question"] else ""
            if query_arg:
                text = query_arg  # Route directly into FTS5 RAG below
            else:
                _user_states[user_id] = {"mode": "ask_ai"}
                msg = (
                    "🤖 *المساعد اللاهوتي والكنسي الذكي:*\n\n"
                    "تفضل بكتابة سؤالك اللاهوتي أو الروحي (مثال: `ما هو هدف التجسد؟` أو `كيف أنتصر على الأفكار؟`)، "
                    "وسأبحث لك في بطون أمهات الكتب وأجيبك مع توثيق اسم المرجع ورقم الصفحة بدقة."
                )
                await self.send_message(client, chat_id, msg, reply_markup=get_back_to_main_inline_keyboard())
                return

        # 4.1 Handle Master Menu: 📑 فهرس المكتبة الشامل
        if cmd in ["/catalog", "/index", "/library"] or text in ["📑 فهرس المكتبة الشامل", "فهرس المكتبة الشامل", "فهرس المكتبة", "الفهرس", "/catalog"]:
            _user_states.pop(user_id, None)
            await self.send_catalog_hub(client, chat_id)
            return

        # 5. Handle Master Menu Section 2: 📚 البحث في المكتبة
        if cmd in ["/search", "/find"] or text in ["📚 البحث في المكتبة", "/search"]:
            query_arg = text[len(first_token):].strip() if cmd in ["/search", "/find"] else ""
            if query_arg:
                books = repo.search_books_by_title_or_author(query_arg, limit=6)
                if not books:
                    await self.send_message(
                        client, chat_id,
                        f"⚠️ لم يتم العثور على كتب تطابق: «{query_arg}».",
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
                    f"📚 *الكتب المطابقة لـ «{query_arg}» (اضغط على اسم الكتاب لفتحه):*",
                    reply_markup={"inline_keyboard": keyboard}
                )
                return
            else:
                _user_states[user_id] = {"mode": "search_book"}
                msg = (
                    "📚 *البحث في أسماء وعناوين الكتب:*\n\n"
                    "اضغط على أي كتاب أدناه لتنزيله أو تصفحه فوراً، أو اكتب اسم أي كتاب باليد:"
                )
                await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
                return

        # 6. Handle Master Menu Section 3: 📖 اسأل كتابًا
        if cmd in ["/ask_book", "/book"] or text == "📖 اسأل كتابًا":
            _user_states[user_id] = {"mode": "ask_book_select"}
            msg = (
                "📖 *خاصية «اسأل كتابًا» (Book-Scoped Q&A):*\n\n"
                "اضغط على أحد الكتب أدناه لحصر الإجابة والبحث داخله فقط، أو اكتب اسم كتاب باليد:"
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_quick_books_inline_keyboard())
            return

        # 7. Handle Master Menu Section 4: ⛪ أقوال الآباء
        if cmd in ["/fathers", "/patrology"] or text in ["⛪ أقوال الآباء", "/fathers"]:
            msg = (
                "⛪ *درر من أقوال الآباء القديسين:*\n\n"
                "اختر الموضوع الروحي الذي تريد الاستنارة بأقوال الآباء فيه:"
            )
            await self.send_message(client, chat_id, msg, reply_markup=get_fathers_topics_inline_keyboard())
            return

        # 8. Handle Master Menu Section 5: 🔍 البحث حسب المؤلف
        if cmd in ["/authors", "/writers"] or text in ["🔍 البحث حسب المؤلف", "/authors"]:
            msg = "🔍 *اختر أحد آباء ومعلمي الكنيسة لعرض كتبه ومؤلفاته المسجلة:*"
            await self.send_message(client, chat_id, msg, reply_markup=get_authors_inline_keyboard())
            return

        # 9. Handle Master Menu Section 6: 📂 تصفح التصنيفات
        if cmd in ["/categories", "/topics", "/sections"] or text in ["📂 تصفح التصنيفات", "/categories"]:
            msg = "📂 *أقسام وتصنيفات المكتبة الكنسية:*\nاختر القسم المطلوب لتصفح محتوياته:"
            await self.send_message(client, chat_id, msg, reply_markup=get_categories_inline_keyboard())
            return

        # 10. Handle Master Menu Section 7: 📑 أبحاثي المحفوظة
        if cmd in ["/bookmarks", "/favs", "/saved"] or text in ["📑 أبحاثي المحفوظة", "/bookmarks"]:
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
        if cmd in ["/stats", "/info", "/status"] or text in ["⚙️ الإعدادات", "/stats"]:
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

        # Default Flow: Instant Semantic RAG Search across whole library with Source-Aware Ranking
        active_filter = user_ctx.get("active_filter") if user_ctx else None
        chunks = search_engine.search_fts5(text, limit=6, filter_source_type=active_filter)
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

        # Store last query in user state for interactive source filtering
        _user_states[user_id] = _user_states.get(user_id, {})
        _user_states[user_id]["last_query"] = text

        # Multi-turn memory: Get active discussion session
        active_sess = repo.get_or_create_active_session(str(user_id))
        session_id = active_sess["id"]

        # Pull past messages in this session
        prior_messages = repo.get_session_messages(session_id, limit=6)
        dialogue_history = [{"role": m["role"], "content": m["content"]} for m in prior_messages]
        dialogue_history.append({"role": "user", "content": text})

        ai_provider = get_ai_provider()
        user_depth = _user_states.get(user_id, {}).get("depth_mode", "academic")
        if len(dialogue_history) > 1 and hasattr(ai_provider, "generate_chat_response"):
            answer = ai_provider.generate_chat_response(dialogue_history, chunks, depth_mode=user_depth)
        else:
            answer = ai_provider.generate_answer(text, chunks, dedicated_books=dedicated_books, depth_mode=user_depth)

        # Prepare citations for persistent saving
        citations_data = []
        for c in chunks:
            citations_data.append({
                "book_title": c.book_title,
                "page_number": c.page_number,
                "printed_page": c.printed_page,
                "source_reference": c.source_reference,
                "author": c.author,
                "source_types": c.source_types,
                "authenticity_tier": c.authenticity_tier,
                "sha256": c.sha256,
                "excerpt": c.chunk_text[:300]
            })

        # Save turns to database session
        try:
            repo.add_chat_message(session_id, "user", text)
            repo.add_chat_message(session_id, "assistant", answer, citations_data)
            if active_sess.get("title") in ["بحث لاهوتي جديد", "محادثة جديدة"]:
                clean_title = text.split("\n")[0][:45]
                repo.update_session_title(session_id, clean_title)
        except Exception as save_err:
            logger.warning(f"Failed to record session turn: {save_err}")

        # Session turn context banner
        turn_number = len(dialogue_history)
        sess_title = active_sess.get("title", "بحث لاهوتي")
        banner = ""
        if turn_number > 1:
            banner = f"💬 *(المحور رقم {turn_number} في مناقشة: «{sess_title}»)*\n\n"

        # 1. Send Structured Deep Theological Synthesis
        await self.send_long_message(client, chat_id, banner + answer)

        # 2. Send Top 3 Verified Reference Cards with Interactive Action Buttons
        for idx, c in enumerate(chunks[:3], 1):
            card_text = format_reference_card(c, idx)
            card_kb = get_reference_card_keyboard(c.sha256, c.page_number, idx)
            await self.send_message(client, chat_id, card_text, reply_markup={"inline_keyboard": card_kb})

        # 3. Send Discussion Action Bar: [تجميع البحث كاملاً] & [Word] & [بحث جديد]
        session_actions_kb = [
            [
                {"text": "📑 تجميع البحث كاملاً (ملف Word + شات)", "callback_data": "session:compile"}
            ],
            [
                {"text": "🔗 فتح ومشاركة البحث على المتصفح", "url": f"https://respectively-ministries-planet-tribes.trycloudflare.com/?session={session_id}"}
            ],
            [
                {"text": "🔄 بدء بحث جديد", "callback_data": "session:new"},
                {"text": "📂 أبحاثي السابقة", "callback_data": "session:history"}
            ],
            [
                {"text": "⚙️ عمق الإجابة والنمط", "callback_data": "menu:depth"},
                {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
            ]
        ]
        await self.send_message(
            client, chat_id,
            "💡 *المساعد محتفظ بسياق المناقشة؛ يمكنك طرح سؤال متفرع آخر أو تجميع البحث بملف Word بنقرة واحدة:*",
            reply_markup={"inline_keyboard": session_actions_kb}
        )

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
        await self.answer_callback_query(client, cb_id)

        # 1. Navigation: Main Menu
        if data == "nav:main":
            _user_states.pop(user_id, None)
            await self.send_welcome_dashboard(client, chat_id, user_name)
            return

                # 1.01 Session Callbacks
        if data.startswith("depth:"):
            new_mode = data.split(":", 1)[1]
            _user_states[user_id] = _user_states.get(user_id, {})
            _user_states[user_id]["depth_mode"] = new_mode
            mode_names = {
                "academic": "🎓 النمط الأكاديمي الموسع (المراجع الأصلية)",
                "pastoral": "🕊️ النمط الرعوي والروحي المباشر",
                "apologetic": "⚖️ النمط الدفاعي والمقارن"
            }
            lbl = mode_names.get(new_mode, new_mode)
            await self.send_message(
                client, chat_id,
                f"✅ *تم تفعيل:* `{lbl}`\nستعتمد إجابات المساعد القادمة على هذا النمط المختار.",
                reply_markup=get_back_to_main_inline_keyboard()
            )
            return

        if data == "menu:depth":
            curr_mode = _user_states.get(user_id, {}).get("depth_mode", "academic")
            from elantony.telegram.keyboards import get_depth_selection_inline_keyboard
            depth_msg = "⚙️ *إعدادات عمق الإجابة والنمط اللاهوتي:* ✠\n\nاختر النمط المناسب لاحتياجك الحالي:"
            await self.send_message(client, chat_id, depth_msg, reply_markup=get_depth_selection_inline_keyboard(curr_mode))
            return

        if data == "session:history":
            sessions = repo.list_user_sessions(str(user_id), limit=10)
            if not sessions:
                await self.send_message(
                    client, chat_id,
                    "📑 *أبحاثي ومناقشاتي السابقة:*\n\nلا توجد مناقشات سابقة مسجلة حتى الآن.\nابدأ بطرح سؤالك وسيتم حفظ كل جلسة تلقائياً!",
                    reply_markup=get_back_to_main_inline_keyboard()
                )
                return
            hist_kb = []
            for s in sessions[:8]:
                title_clean = s.get("title", "بحث لاهوتي")[:26]
                hist_kb.append([
                    {"text": f"💬 {title_clean} ({s.get('message_count', 0)} رد)", "callback_data": f"sess:view:{s['id']}"},
                    {"text": "📥 Word", "callback_data": f"sess:docx:{s['id']}"}
                ])
            hist_kb.append([{"text": "🔄 بدء بحث جديد", "callback_data": "session:new"}])
            hist_kb.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(
                client, chat_id,
                "📑 *أبحاثك ومناقشاتك المحفوظة في ذاكرة المساعد:*\nاختر أي بحث لمراجعته أو تنزيله كملف Word:",
                reply_markup={"inline_keyboard": hist_kb}
            )
            return

        if data.startswith("sess:docx:"):
            target_id = data.split(":", 2)[2]
            comp = repo.compile_session(target_id)
            if comp.get("turns_count", 0) > 0:
                doc_dir = settings.base_dir / "data" / "compiled_researches"
                doc_dir.mkdir(parents=True, exist_ok=True)
                docx_path = doc_dir / f"research_{target_id}.docx"
                from elantony.services.docx_exporter import generate_session_docx
                generate_session_docx(comp, str(docx_path))
                caption = f"📄 أطروحة بحثية: «{comp.get('title', '')}» (Word) | منظومة ELANTONY AI"
                await self.send_document(client, chat_id, str(docx_path), caption=caption)
            else:
                await self.send_message(client, chat_id, "⚠️ لا توجد أسئلة مسجلة في هذه الجلسة.")
            return

        if data == "session:compile":
            await self.compile_and_send_session(client, chat_id, user_id)
            return

        if data == "session:new":
            repo.create_session(str(user_id))
            _user_states.pop(user_id, None)
            new_msg = (
                "✨ *تم فتح جلسة بحثية جديدة بنجاح!* ✠\n\n"
                "تفضل بطرح سؤالك اللاهوتي الأول، ويمكنك الاستفسار عن تفاصيل أو تعقيبات متفرعة وسأحتفظ بكل السياق حتى تطلب التجميع في أي وقت عبر زر `📑 تجميع البحث`."
            )
            await self.send_message(
                client, chat_id, new_msg,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "🤖 ابدأ السؤال الآن", "callback_data": "menu:ask_ai"}],
                        [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
                    ]
                }
            )
            return

        if data.startswith("sess:view:"):
            target_id = data.split(":", 2)[2]
            await self.compile_and_send_session(client, chat_id, user_id, target_session_id=target_id)
            return

        # 1.1 Navigation: Library Catalog Hub & Submenus
        if data == "menu:catalog":
            _user_states.pop(user_id, None)
            await self.send_catalog_hub(client, chat_id)
            return

        if data == "cat:topics":
            await self.send_catalog_topics(client, chat_id)
            return

        if data == "cat:authors":
            await self.send_catalog_authors(client, chat_id)
            return

        if data == "cat:alpha":
            await self.send_catalog_alphabet(client, chat_id)
            return

        if data == "cat:encyclopedias":
            await self.send_catalog_encyclopedias(client, chat_id)
            return

        if data == "cat:random":
            await self.send_catalog_random_book(client, chat_id)
            return

        if data == "noop":
            return

        # 1.2 Catalog Pagination Dispatcher (cp:<type>:<id>:<page>)
        if data.startswith("cp:"):
            parts = data.split(":")
            if len(parts) >= 4:
                cat_type, cat_id, page_str = parts[1], parts[2], parts[3]
                page = max(1, int(page_str))

                if cat_type == "topic":
                    books, total_count, total_pages, title = repo.get_books_by_catalog_category(cat_id, page=page)
                    header = (
                        f"📂 *قسم:* «{title}»\n"
                        f"📊 *إجمالي الكتب المسجلة:* `{total_count}` كتاباً (صفحة {page} من {total_pages})\n\n"
                        "👇 *اضغط على أي كتاب لفتحه وتنزيل الـ PDF أو قراءته فوراً:*"
                    )
                    markup = get_catalog_paginated_books_keyboard(books, page, total_pages, "topic", cat_id)
                    await self.send_message(client, chat_id, header, reply_markup=markup)
                    return

                elif cat_type == "auth":
                    books, total_count, total_pages, author_name = repo.get_books_by_catalog_author(cat_id, page=page)
                    header = (
                        f"✍️ *مؤلفات:* «{author_name}»\n"
                        f"📊 *إجمالي الكتب المتاحة:* `{total_count}` كتاباً (صفحة {page} من {total_pages})\n\n"
                        "👇 *اضغط على أي كتاب لفتحه وتنزيل الـ PDF أو قراءته فوراً:*"
                    )
                    markup = get_catalog_paginated_books_keyboard(books, page, total_pages, "auth", cat_id)
                    await self.send_message(client, chat_id, header, reply_markup=markup)
                    return

                elif cat_type == "alpha":
                    books, total_count, total_pages = repo.get_books_by_alphabet(cat_id, page=page)
                    header = (
                        f"🔤 *الكتب التي تبدأ بحرف:* [{cat_id}]\n"
                        f"📊 *إجمالي الكتب المطابقة:* `{total_count}` كتاباً (صفحة {page} من {total_pages})\n\n"
                        "👇 *اضغط على أي كتاب لفتحه وتنزيل الـ PDF أو قراءته فوراً:*"
                    )
                    markup = get_catalog_paginated_books_keyboard(books, page, total_pages, "alpha", cat_id)
                    await self.send_message(client, chat_id, header, reply_markup=markup)
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
                target_text = ""

                # Tier 1: Check extracted text directory
                txt_file = settings.extracted_text_dir / f"{sha256}.txt"
                if not txt_file.exists():
                    # Tier 2: Check I: drive mirror
                    alt_file = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster\extracted_text") / f"{sha256}.txt"
                    if alt_file.exists():
                        txt_file = alt_file

                if txt_file.exists():
                    try:
                        with open(txt_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        from modules.rag_chunker import parse_pages_from_extracted_text
                        pages = parse_pages_from_extracted_text(content)
                        target = next((p for p in pages if p["page_num"] == page_num), None)
                        if target and target["text"].strip():
                            target_text = target["text"]
                    except Exception as e:
                        logger.warning(f"Error parsing page from disk: {e}")

                # Tier 3: Direct SQLite church_chunks_fts fallback
                if not target_text:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT chunk_text FROM church_chunks_fts 
                            WHERE sha256 LIKE ? AND page_number = ? 
                            ORDER BY chunk_index ASC
                        """, (f"{sha256[:16]}%", page_num))
                        page_chunks = [r[0] for r in cur.fetchall()]
                        conn.close()
                        if page_chunks:
                            target_text = "\n\n".join(page_chunks)
                    except Exception as e:
                        logger.warning(f"Error reading page from church_chunks_fts: {e}")

                if target_text:
                    clean_page = clean_theological_text(target_text)
                    clean_title = book["file_name"].replace(".pdf", "")
                    page_msg = f"📄 *نص الصفحة {page_num} من «{clean_title}»:*\n\n{clean_page[:3500]}"
                    await self.send_message(
                        client, chat_id, page_msg,
                        reply_markup=get_page_reader_inline_keyboard(sha256[:16], page_num)
                    )
                else:
                    await self.send_message(
                        client, chat_id,
                        f"⚠️ الصفحة {page_num} فارغة أو قيد المعالجة الضوئية.",
                        reply_markup=get_page_reader_inline_keyboard(sha256[:16], page_num)
                    )
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

        # 13. Action: src:<filter_code> (Filter search results by Source Type)
        if data.startswith("src:"):
            filter_code = data.split("src:", 1)[1]
            last_query = _user_states.get(user_id, {}).get("last_query")
            if not last_query:
                await self.send_message(
                    client, chat_id,
                    "🔍 *تصفية المصادر الكنسية:*\nيرجى كتابة سؤالك أو موضوع البحث أولاً لتطبيق التصفية.",
                    reply_markup=get_main_menu_inline_keyboard()
                )
                return

            filter_type = None if filter_code == "ALL" else filter_code
            chunks = search_engine.search_fts5(last_query, limit=5, filter_source_type=filter_type)
            if not chunks:
                await self.send_message(
                    client, chat_id,
                    f"⚠️ لم يتم العثور على مراجع تطابق «{last_query}» ضمن هذا التصنيف تحديداً.",
                    reply_markup=get_source_filter_keyboard(filter_code)
                )
                return

            filter_labels = {
                "ALL": "كافة المصادر",
                "PRIMARY_PATRISTIC": "المصادر الآبائية الأصلية",
                "THEOLOGICAL_STUDIES": "الدراسات اللاهوتية والعقائدية",
                "LITURGICAL_SOURCES": "المصادر الطقسية والليتورجية",
                "HISTORICAL_SOURCES": "المصادر التاريخية"
            }
            lbl = filter_labels.get(filter_code, filter_code)
            await self.send_message(client, chat_id, f"🎯 *نتائج التصفية حسب:* «{lbl}» ({len(chunks)} مراجع):")

            for idx, c in enumerate(chunks[:3], 1):
                card_text = format_reference_card(c, idx)
                card_kb = get_reference_card_keyboard(c.sha256, c.page_number, idx)
                await self.send_message(client, chat_id, card_text, reply_markup={"inline_keyboard": card_kb})

            filter_markup = get_source_filter_keyboard(filter_code)
            filter_markup["inline_keyboard"].append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])
            await self.send_message(client, chat_id, "⚙️ *تغيير التصنيف:*", reply_markup=filter_markup)
            return

        # 14. Action: rel:<ref>:<page_num> (Find Related Patristic Excerpts)
        if data.startswith("rel:"):
            parts = data.split(":")
            if len(parts) >= 3:
                ref, page_num = parts[1], int(parts[2])
                book = repo.get_book_by_ref(ref)
                if not book:
                    await self.send_message(client, chat_id, "⚠️ لم يتم العثور على بيانات هذا المرجع.")
                    return

                # Retrieve nearby or related excerpts from the same book
                sha256 = book["sha256"]
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT page_number, chunk_text, source_reference
                    FROM church_chunks_fts
                    WHERE sha256 LIKE ? AND page_number != ?
                    LIMIT 3
                """, (f"{sha256[:16]}%", page_num))
                related_rows = cur.fetchall()
                conn.close()

                if not related_rows:
                    await self.send_message(client, chat_id, "⚠️ لم يتم العثور على شواهد أخرى مفهرسة من نفس الكتاب.")
                    return

                clean_title = book["file_name"].replace(".pdf", "")
                await self.send_message(client, chat_id, f"🔍 *شواهد أخرى متصلة من كتاب:* «{clean_title}»:")
                for r_idx, row in enumerate(related_rows, 1):
                    p_num = row[0]
                    excerpt = clean_theological_text(row[1])[:280] + "..."
                    rel_msg = f"🔖 *شاهد متصل ({r_idx}):* صـ {p_num}\n❝ {excerpt} ❞"
                    card_kb = get_reference_card_keyboard(sha256[:16], p_num, r_idx)
                    await self.send_message(client, chat_id, rel_msg, reply_markup={"inline_keyboard": card_kb})
        # Actions for Drive, Audio & Menu Shortcuts
        if data.startswith("gdrive_sync:"):
            lib_id = data.split("gdrive_sync:", 1)[1]
            await handle_gdrive_sync_callback(self, client, chat_id, lib_id)
            return

        if data.startswith("verse:audio:"):
            v_idx = int(data.split("verse:audio:", 1)[1])
            await handle_verse_audio_callback(self, client, chat_id, v_idx)
            return

        if data == "menu:synaxarium":
            await send_synaxarium(self, client, chat_id)
            return

        if data == "menu:daily_verse":
            await send_daily_verse(self, client, chat_id)
            return

        if data == "menu:harvest_drive":
            await send_harvest_drive(self, client, chat_id)
            return

        if data == "menu:harvest_tg":
            await send_harvest_tg(self, client, chat_id)
            return

        if data == "menu:special_commands":
            await send_special_commands_menu(self, client, chat_id)
            return

        if data == "menu:admin_dash":
            await send_admin_dashboard(self, client, chat_id, user_id)
            return

            return
