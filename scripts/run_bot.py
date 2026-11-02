# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Dedicated Telegram Bot Runner
Launches the Telegram Bot with automated command registration and interactive menu dispatch.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.telegram.bot_service import TelegramBotEngine


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
                logger.info("Telegram Bot menu commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register Telegram commands: {e}")


async def main():
    token = settings.telegram_bot_token
    if not token:
        print("❌ خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN في ملف .env")
        return

    print("=" * 65)
    print(" ✠ ELANTONY LIBRARY AI - مشغل بوت تيليجرام التفاعلي ✠")
    print("=" * 65)
    print(f" 🤖 معرف البوت الرسمي : @ElantonyLibrarybot")
    print(f" 🛡️ التوكن المعتمد    : {token[:6]}...{token[-4:]}")
    print(f" 🎯 نظام الأزرار     : مفعل (أزرار تفاعلية Inline + قائمة سفلية Reply)")
    print("=" * 65)
    print(" [*] جاري تسجيل قائمة الأوامر التفاعلية في تيليجرام...")
    await register_commands(token)

    print(" [*] البوت يعمل الآن بنجاح ويستقبل الرسائل... (اضغط Ctrl+C للإيقاف)")
    print("=" * 65)

    engine = TelegramBotEngine(token)
    while True:
        try:
            await engine.run()
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n [!] تم إيقاف البوت بنجاح.")
            engine.stop()
            break
        except Exception as e:
            logger.error(f"Unexpected bot worker disconnection: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5.0)


if __name__ == "__main__":
    asyncio.run(main())
