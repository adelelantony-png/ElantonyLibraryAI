# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Hugging Face Gradio Hub & Telegram Bot Server
Runs concurrently:
1. Gradio Web Interface for direct browser search & library telemetry.
2. Background Asyncio Telegram Bot Daemon for @ElantonyLibrarybot (24/7 Always-On).
"""

import sys
import os
import asyncio
import threading
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import gradio as gr
import httpx
from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.database.repository import repo
from elantony.search.search_engine import ChurchSearchEngine
from elantony.ai.factory import AIProviderFactory
from elantony.telegram.bot_service import TelegramBotEngine


def ensure_database():
    """Verifies that file_archive.db exists; bootstraps from cloud URL if missing."""
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    if db_path.exists() and db_path.stat().st_size > 1000:
        logger.info(f"Database verified at {db_path} ({db_path.stat().st_size / (1024*1024):.1f} MB)")
        return

    db_download_url = os.getenv("DATABASE_DOWNLOAD_URL", "").strip()
    if db_download_url:
        logger.info(f"Database missing. Downloading from {db_download_url}...")
        import urllib.request
        import shutil
        import zipfile
        temp_zip = BASE_DIR / "file_archive_temp.zip"
        req = urllib.request.Request(db_download_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as response, open(temp_zip, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        logger.info("Extracting database...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(BASE_DIR)
        temp_zip.unlink(missing_ok=True)
        logger.info("Database bootstrap completed successfully.")
    else:
        logger.warning(f"Database file not found at {db_path} and DATABASE_DOWNLOAD_URL not set.")


async def register_commands(token: str):
    """Registers Telegram Bot Menu commands."""
    commands = [
        {"command": "start", "description": "✠ القائمة الرئيسية ولوحة الأزرار"},
        {"command": "ask", "description": "🤖 سؤال المساعد الذكي الموثق"},
        {"command": "search", "description": "📚 البحث في كتب ومحتوى المكتبة"},
        {"command": "fathers", "description": "⛪ درر من أقوال الآباء القديسين"},
        {"command": "authors", "description": "🔍 البحث بمؤلفي ومعلمي الكنيسة"},
        {"command": "categories", "description": "📂 تصفح أقسام وتصنيفات المكتبة"},
        {"command": "bookmarks", "description": "📑 أبحاثي وشواهدي المحفوظة"},
        {"command": "stats", "description": "📊 إحصائيات وحالة المكتبة"},
        {"command": "help", "description": "ℹ️ دليل المساعدة والإرشادات"}
    ]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/setMyCommands",
                json={"commands": commands}
            )
            logger.info("Telegram Bot menu commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register Telegram commands: {e}")


def start_telegram_bot_daemon():
    """Runs the Telegram Bot engine in a dedicated background thread."""
    ensure_database()
    token = settings.telegram_bot_token
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set; Telegram Bot daemon will not start.")
        return

    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Starting ELANTONY Telegram Bot worker in background thread...")
        loop.run_until_complete(register_commands(token))
        engine = TelegramBotEngine()
        loop.run_until_complete(engine.start())

    t = threading.Thread(target=run_loop, daemon=True, name="TelegramBotDaemon")
    t.start()
    logger.info("Telegram Bot daemon thread launched.")


# Search logic for Gradio UI
search_engine = ChurchSearchEngine()
ai_provider = AIProviderFactory.create_provider()


def web_search(query: str):
    """Processes search query from web interface."""
    if not query.strip():
        return "⚠️ برجاء إدخال نص البحث أو السؤال اللاهوتي."

    try:
        chunks = search_engine.search(query.strip(), limit=5)
        if not chunks:
            return f"لم يتم العثور على شواهد مباشرة تطابق: «{query}» في بطون الكتب المفهرسة حالياً."

        answer = ai_provider.generate_theological_response(query.strip(), chunks)
        return answer
    except Exception as e:
        return f"حدث خطأ أثناء البحث: {str(e)}"


def get_library_stats():
    """Returns formatted stats for Gradio display."""
    try:
        stats = repo.get_library_stats()
        return (
            f"📚 إجمالي الكتب المفهرسة: {stats.get('total_books', 0):,} مجلداً\n"
            f"📑 المقاطع النصية المفهرسة: {stats.get('indexed_chunks', 0):,} مقطعاً\n"
            f"📄 إجمالي الصفحات المستخرجة: {stats.get('total_pages', 0):,} صفحة\n"
            f"🤖 بوت تيليجرام: @ElantonyLibrarybot (نشط 24/7)\n"
            f"🛡️ حالة النظام: تشغيل سحابي فائق السرعة ومستمر"
        )
    except Exception as e:
        return f"تعذر استرجاع الإحصائيات: {str(e)}"


# Launch background Telegram Bot daemon
start_telegram_bot_daemon()

# Build Gradio UI
with gr.Blocks(title="ELANTONY LIBRARY AI", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # ⛪ مكتبة الأنبا أنطونيوس الذكية (ELANTONY LIBRARY AI)
        ### النظام السحابي الموحد للبحث اللاهوتي وتوثيق مصادر الكنيسة القبطية الأرثوذكسية
        **🤖 البوت السحابي متاح 24/7 على تيليجرام:** [@ElantonyLibrarybot](https://t.me/ElantonyLibrarybot)
        """
    )
    with gr.Tab("🔍 البحث اللاهوتي الموثق"):
        query_input = gr.Textbox(
            label="السؤال أو الموضوع اللاهوتي",
            placeholder="مثال: هل كان الطوفان عالمي؟ أو أهمية الصلاة الدائمة عند القديس أنطونيوس...",
            lines=2
        )
        search_btn = gr.Button("🔎 بحث وتوثيق بالشواهد", variant="primary")
        output_display = gr.Markdown(label="الإجابة والشواهد المعتمدة")
        search_btn.click(fn=web_search, inputs=query_input, outputs=output_display)

    with gr.Tab("📊 إحصائيات المكتبة الكنسية"):
        stats_display = gr.Textbox(label="بيانات الفهرسة السحابية", value=get_library_stats, lines=7)
        refresh_btn = gr.Button("🔄 تحديث الإحصائيات")
        refresh_btn.click(fn=get_library_stats, inputs=[], outputs=stats_display)

    gr.Markdown(
        """
        ---
        *✠ نظام توثيق كنسي خالي من الهلاوس - جميع الإجابات مستخرجة مباشرة من بطون الكتب الكنسية المعتمدة.*
        """
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
