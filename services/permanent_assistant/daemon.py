# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Standalone Permanent Assistant Daemon
Master 24/7 Coordinator:
- Runs Telegram Bot Engine (@ElantonyLibrarybot)
- Runs Real-Time Library Folder Watcher (I:\2021\2020\✠ Cross Coptic Library ✠)
- Prevents Windows sleep while active
- Automatic error recovery and health heartbeat
"""

import sys
import os
import time
import asyncio
import signal
import ctypes
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix console encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.telegram.bot_service import TelegramBotEngine
from services.permanent_assistant.watcher import LibraryLiveWatcher, DEFAULT_WATCH_PATH
from services.permanent_assistant.tunnel_watchdog import CloudflareTunnelWatchdog

# Windows API to prevent sleep
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def prevent_windows_sleep():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            logger.info("Windows sleep prevention activated (ES_CONTINUOUS | ES_SYSTEM_REQUIRED).")
        except Exception as e:
            logger.warning(f"Could not set thread execution state: {e}")


def restore_windows_sleep():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass


class PermanentAssistantDaemon:
    """Orchestrates the 24/7 autonomous operations of the church research AI."""

    def __init__(self):
        self.bot_engine = TelegramBotEngine()
        self.watcher = LibraryLiveWatcher(
            watch_directory=DEFAULT_WATCH_PATH,
            on_book_ingested=self._on_book_ingested
        )
        self.tunnel_watchdog = CloudflareTunnelWatchdog(check_interval_sec=45)
        self._running = True

    def _on_book_ingested(self, book_info: dict):
        """Broadcasts announcement when a new book is added via file system."""
        title = book_info.get("title", book_info.get("file_name", ""))
        pages = book_info.get("pages", 0)
        chunks = book_info.get("chunks_count", 0)
        tier = book_info.get("authenticity_tier", 3)
        author = book_info.get("author", "آباء الكنيسة")

        logger.info(f"📢 [Permanent Assistant Alert] New book integrated into AI brain: «{title}» ({pages} p, {chunks} chunks)")

    async def run(self):
        prevent_windows_sleep()
        print("=" * 68)
        print(" ✠ ELANTONY LIBRARY AI - خادم المساعد الدائم المستقل ✠")
        print("=" * 68)
        print(f" 🤖 معرف البوت الرسمي : @ElantonyLibrarybot")
        print(f" 👁️ مسار المراقبة الحي : {DEFAULT_WATCH_PATH}")
        print(f" ⚡ خط الفهرسة التلقائي: نشط وجاهز لاستقبال أي كتاب جديد")
        print(" 🌐 مراقب النفق السحابي: حماية تلقائية ضد السقوط 24/7 (Auto-Healer)")
        print("=" * 68)

        # 1. Start live folder watcher in background thread
        watcher_started = self.watcher.start()
        if watcher_started:
            print(" ✓ تم تشغيل مراقب المجلدات الذكي بنجاح (يراقب أي كتب تضاف حديثاً)")
        else:
            print(" ⚠️ تنبيه: مسار المكتبة غير متاح حالياً، سيستمر المساعد في إعادة المحاولة.")

        # 2. Start Cloudflare Tunnel Auto-Healer task
        watchdog_task = asyncio.create_task(self.tunnel_watchdog.run())
        print(" ✓ تم تشغيل مراقب النفق السحابي الذكي (يراقب استقرار الموقع ويعيد تشغيله آلياً)")

        # 3. Run Telegram Bot in async event loop with auto-reconnect
        try:
            await self.bot_engine.run()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Telegram bot worker encountered error: {e}")
        finally:
            watchdog_task.cancel()
            self.stop()

    def stop(self):
        self._running = False
        self.watcher.stop()
        self.tunnel_watchdog.stop()
        self.bot_engine.stop()
        restore_windows_sleep()
        logger.info("Permanent Assistant Daemon shutdown complete.")


def main():
    daemon = PermanentAssistantDaemon()

    def sig_handler(sig, frame):
        print("\nجاري إيقاف المساعد الدائم بأمان...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
