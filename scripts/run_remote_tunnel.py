# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Remote Cloud Access Launcher
Enables worldwide secure HTTPS access to the Web Research Portal
without VPS, port forwarding, or public IP via Cloudflare Tunnel.
"""

import os
import sys
import re
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLOUDFLARED_BIN = PROJECT_ROOT / "tools" / "cloudflared.exe"
LINK_FILE = PROJECT_ROOT / "رابط_المساعد_عن_بعد.txt"

def main():
    if not CLOUDFLARED_BIN.exists():
        print(f"[-] cloudflared.exe not found at: {CLOUDFLARED_BIN}")
        return

    print("=" * 70)
    print(" ✠ ELANTONY LIBRARY AI - مشغل الوصول السحابي الآمن عن بُعد ✠")
    print("=" * 70)
    print(" [*] جاري فتح نفق مشفر فائق السرعة عبر شبكة Cloudflare العالمية...")
    print(" [*] لا حاجة لأي إعدادات راوتر أو اشتراك أو VPS أو IP ثابت.")
    print("=" * 70)

    cmd = [str(CLOUDFLARED_BIN), "tunnel", "--url", "http://localhost:8000"]
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    url_found = None
    try:
        for line in iter(proc.stdout.readline, ""):
            match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
            if match and not url_found:
                url_found = match.group(0)
                print("\n" + "✨" * 35)
                print(f" 🌐 تم إنشاء الرابط العالمي للوصول إلى المساعد بنجاح:")
                print(f" 👉 {url_found}")
                print("✨" * 35 + "\n")
                print(" 📱 يمكنك الآن فتح هذا الرابط من هاتفك المحمول أو أي جهاز")
                print("    على أي شبكة إنترنت خارجية (4G/5G/واي فاي خارجي).")
                print(f" 💾 تم حفظ الرابط في الملف: {LINK_FILE.name}")
                print("=" * 70)

                with open(LINK_FILE, "w", encoding="utf-8") as f:
                    f.write(f"رابط الوصول للمساعد الذكي عن بعد:\n{url_found}\n\nتاريخ الإنشاء: {time.ctime()}\n")

            # Check if terminated
            if proc.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n[*] إيقاف النفق السحابي...")
        proc.terminate()

if __name__ == "__main__":
    main()
