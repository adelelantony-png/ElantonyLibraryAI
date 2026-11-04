# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Automated 24/7 Hugging Face Cloud Deployer
Uploads and boots the complete Coptic Research Assistant and Telegram Bot
on Hugging Face Spaces (Free 16GB RAM / 2 vCPU 24/7 Cloud Tier).
"""

import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elantony.core.config import settings

def deploy(token: str, space_name: str = "elantony-library-ai", is_private: bool = False):
    from huggingface_hub import HfApi

    print("=" * 70)
    print(" ✠ ELANTONY LIBRARY AI - ناشر السحابة الآلي (Hugging Face Spaces) ✠")
    print("=" * 70)

    token = token.strip()
    if not token:
        print("[-] خطأ: لم يتم إدخال الـ Token.")
        return False

    api = HfApi(token=token)

    # 1. Verify User Identity
    print(" [*] جاري التحقق من هوية الحساب على Hugging Face...")
    try:
        user_info = api.whoami()
        username = user_info.get("name", "")
        print(f" [+] مرحباً بك: {username} (تمت المصادقة بنجاح)")
    except Exception as auth_err:
        print(f"[-] فشل التحقق من الـ Token: {auth_err}")
        return False

    repo_id = f"{username}/{space_name}"
    print(f" [*] مسار الـ Space المستهدف: {repo_id}")

    # 2. Create Space if it doesn't exist
    try:
        print(" [*] جاري تجهيز الـ Space السحابي (Docker - 16GB RAM مجاناً)...")
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=is_private,
            exist_ok=True
        )
        print(" [+] الـ Space جاهز ومفعل بنجاح.")
    except Exception as cr_err:
        print(f" [!] ملاحظة أثناء تجهيز الـ Space: {cr_err}")

    # 3. Configure Secrets (Environment Variables)
    print(" [*] جاري مزامنة المفاتيح السرية (Secrets) المشفرة سحابياً...")
    secrets_to_set = {
        "ENABLE_BOT_IN_API": "true",
        "APP_ENV": "production",
        "APP_PORT": "7860"
    }

    if settings.telegram_bot_token:
        secrets_to_set["TELEGRAM_BOT_TOKEN"] = settings.telegram_bot_token
    if settings.gemini_api_key:
        secrets_to_set["GEMINI_API_KEY"] = settings.gemini_api_key

    for key, val in secrets_to_set.items():
        try:
            api.add_space_secret(repo_id=repo_id, key=key, value=val)
            print(f" [+] تم ضبط المتغير السحابي: {key}")
        except Exception as sec_err:
            print(f" [!] تنبيه ضبط {key}: {sec_err}")

    # 4. Upload Complete Project Folder in a single clean commit
    print("\n [*] جاري رفع كود المنظومة وقاعدة البيانات إلى Hugging Face في دفعة واحدة...")
    print("     (سيتم رفع الكود و 313,000+ مقطع مفهرس في file_archive.db تلقائياً)")
    
    ignore_list = [
        ".git",
        ".git/*",
        ".gitignore",
        "venv",
        "venv/*",
        "tools",
        "tools/*",
        "books",
        "books/*",
        "extracted_text",
        "extracted_text/*",
        "processed_text",
        "processed_text/*",
        "backups",
        "backups/*",
        "reports",
        "reports/*",
        "logs",
        "logs/*",
        "__pycache__",
        "__pycache__/*",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".env",
        ".env.*",
        "*.bat",
        "*.txt",
        "file_archive.db-wal",
        "file_archive.db-shm"
    ]

    try:
        t0 = time.time()
        api.upload_folder(
            folder_path=str(PROJECT_ROOT),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=ignore_list,
            commit_message="Deploy ELANTONY LIBRARY AI cloud container with FTS5 brain"
        )
        elapsed = time.time() - t0
        print(f" [+] اكتمل الرفع بنجاح في {elapsed:.1f} ثانية!")
    except Exception as up_err:
        print(f"[-] خطأ أثناء رفع المجلد: {up_err}")
        return False

    space_url = f"https://huggingface.co/spaces/{repo_id}"
    app_url = f"https://{username.lower()}-{space_name.lower().replace('_', '-')}.hf.space"

    print("\n" + "🎉" * 35)
    print(" ✠ تم النشر السحابي الكامل بنجاح على Hugging Face Spaces! ✠")
    print(f" 🌐 صفحة إدارة السيرفر السحابي : {space_url}")
    print(f" 🚀 رابط المساعد المباشر        : {app_url}")
    print(f" 🤖 بوت تليجرام يعمل الآن 24/7 : @ElantonyLibrarybot")
    print("🎉" * 35 + "\n")
    print(" 💤 بمجرد اكتمال بناء الحاوية (دقيقة أو دقيقتين على موقع Hugging Face):")
    print("    يمكنك إغلاق جهاز الكمبيوتر الشخصي تماماً؛ فالمنظومة أصبحت سحابية 100%!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    tok = sys.argv[1] if len(sys.argv) > 1 else os.getenv("HUGGINGFACE_TOKEN", "")
    if not tok:
        print("Usage: python deploy_to_huggingface.py <HF_TOKEN> or set HUGGINGFACE_TOKEN env var")
        sys.exit(1)
    deploy(tok)
