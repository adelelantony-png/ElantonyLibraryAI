# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Mobile Cloud & Telegram Server Launcher
Spins up the FastAPI server, detects local IP for Wi-Fi access,
and provides Cloudflare Tunnel instructions for global mobile access.
"""

import sys
import os
import socket
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

import uvicorn
from modules import church_ai_config, church_ai_reporter


def get_local_ip() -> str:
    """Gets local network IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def main():
    cfg = church_ai_config.load_config()
    cloud_cfg = cfg.get("cloud", {})
    host = cloud_cfg.get("host", "0.0.0.0")
    port = int(cloud_cfg.get("port", 8000))
    tg_token = cloud_cfg.get("telegram_bot_token", "").strip()

    local_ip = get_local_ip()
    stats = church_ai_reporter.get_catalog_statistics()

    print("=" * 70)
    print(" ✠ ArchiveMaster ChurchAI - سيرفر الجوال وبوت تيليجرام ✠")
    print("=" * 70)
    print(f" 📚 قاعدة المراجع النشطة : {stats['total_books']} مجلداً ({stats['total_pages']:,} صفحة)")
    print(f" 🌐 المنفذ المحلي        : http://localhost:{port}")
    print(f" 📱 رابط الموبايل (Wi-Fi): http://{local_ip}:{port}")
    print("-" * 70)
    print(" 🤖 حالة بوت تيليجرام:")
    if tg_token:
        masked = tg_token[:6] + "..." + tg_token[-4:]
        print(f"    ✅ مفعل ومتصل بالتوكن: {masked}")
    else:
        print("    ⚠️ غير مفعل حالياً (يمكنك إدخال التوكن من واجهة الموبايل أو ملف الإعدادات)")

    print("-" * 70)
    print(" 🌍 لفتح السيرفر على جوالك من أي مكان في العالم مجاناً وبأمان تام:")
    print("    1. افتح نافذة PowerShell جديدة كمسؤول.")
    print("    2. شغل أمر النفق السحابي المشفر (Cloudflare Tunnel):")
    print(f"       cloudflared tunnel --url http://localhost:{port}")
    print("    3. انسخ الرابط المشفر (https://....trycloudflare.com) وافتحه على جوالك!")
    print("=" * 70)
    print(" [*] جاري تشغيل خادم Uvicorn... اضغط Ctrl+C للإيقاف.")
    print("=" * 70)

    uvicorn.run("modules.church_cloud_server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
