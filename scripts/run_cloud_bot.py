# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Cloud Production Server with Telegram Bot Daemon
Designed for 24/7 cloud hosting (Koyeb, Render, Railway, Docker).
Provides:
1. Fast HTTP /health endpoint to satisfy cloud container health checks.
2. Concurrent background execution of TelegramBotEngine.
3. Automated database check and optional cloud bootstrap.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output on Windows / Linux
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import uvicorn
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.database.repository import repo
from elantony.telegram.bot_service import TelegramBotEngine

# Global background task
bot_task: asyncio.Task = None


async def register_commands(token: str):
    """Registers native Telegram Bot Menu commands."""
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
            res = await client.post(
                f"https://api.telegram.org/bot{token}/setMyCommands",
                json={"commands": commands}
            )
            if res.status_code == 200:
                logger.info("Telegram Bot menu commands registered successfully in cloud.")
    except Exception as e:
        logger.warning(f"Could not register Telegram commands: {e}")


def ensure_database():
    """Verifies that file_archive.db exists and is ready."""
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    if db_path.exists() and db_path.stat().st_size > 1000:
        logger.info(f"Database verified at {db_path} ({db_path.stat().st_size / (1024*1024):.1f} MB)")
        return

    # Check if download URL is provided in environment
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan: boots up Telegram bot and manages background tasks."""
    global bot_task
    ensure_database()

    token = settings.telegram_bot_token
    if token:
        logger.info("Starting ELANTONY Telegram Bot worker...")
        await register_commands(token)
        engine = TelegramBotEngine()
        bot_task = asyncio.create_task(engine.start())
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not provided; bot worker is idle.")

    yield

    if bot_task and not bot_task.done():
        logger.info("Shutting down Telegram Bot worker...")
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ELANTONY LIBRARY AI - Cloud Gateway",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
@app.get("/health")
async def health_check():
    """Health check endpoint for Koyeb, Docker, and monitoring."""
    try:
        stats = repo.get_library_stats()
        db_status = "connected"
    except Exception as e:
        stats = {}
        db_status = f"degraded: {str(e)}"

    return JSONResponse(content={
        "status": "healthy",
        "service": "ELANTONY LIBRARY AI",
        "version": "2.0.0",
        "database": db_status,
        "indexed_chunks": stats.get("indexed_chunks", 0),
        "total_books": stats.get("total_books", 0),
        "telegram_bot": "@ElantonyLibrarybot" if settings.telegram_bot_token else "disabled"
    })


def main():
    port = int(os.getenv("PORT", os.getenv("APP_PORT", 8000)))
    host = os.getenv("HOST", os.getenv("APP_HOST", "0.0.0.0"))
    logger.info(f"Starting Cloud Server on {host}:{port}")
    uvicorn.run("scripts.run_cloud_bot:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
