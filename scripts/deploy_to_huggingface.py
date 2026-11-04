# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Automated 24/7 Hugging Face Cloud Deployer
Uploads and boots the complete Coptic Research Assistant and Telegram Bot
on Hugging Face Spaces (Free 16GB RAM / 2 vCPU 24/7 Cloud Tier).
"""

import os
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elantony.core.config import settings

def deploy(token: str, space_name: str = "elantony-library-ai", is_private: bool = False):
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[-] huggingface_hub not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
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
        print("    يرجى التأكد من إنشاء Token بصلاحية (Write) من: https://huggingface.co/settings/tokens")
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
        print(" [+] الـ Space جاهز ومفعل.")
    except Exception as cr_err:
        print(f"[-] ملاحظة أثناء إنشاء الـ Space: {cr_err}")

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

    # 4. Upload Files
    print(" [*] جاري رفع ملفات المنظومة وكود المساعد إلى السحابة...")
    essential_files = [
        "Dockerfile",
        "requirements.txt",
        "README.md",
        ".dockerignore"
    ]

    for fname in essential_files:
        fpath = PROJECT_ROOT / fname
        if fpath.exists():
            print(f" [>] رفع: {fname}...")
            api.upload_file(
                path_or_fileobj=str(fpath),
                path_in_repo=fname,
                repo_id=repo_id,
                repo_type="space"
            )

    # Upload Code Directories
    code_folders = ["elantony", "modules", "scripts"]
    for folder in code_folders:
        fdir = PROJECT_ROOT / folder
        if fdir.exists():
            print(f" [>] رفع مجلد الكود: {folder}...")
            api.upload_folder(
                folder_path=str(fdir),
                path_in_repo=folder,
                repo_id=repo_id,
                repo_type="space",
                ignore_patterns=["__pycache__/*", "*.pyc", "*.pyo"]
            )

    # 5. Upload Database file_archive.db
    db_path = PROJECT_ROOT / "file_archive.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f" [*] جاري رفع قاعدة بيانات المكتبة الآبائية ({size_mb:.1f} MB)...")
        print("     (قد يستغرق بضع دقائق حسب سرعة رفع الإنترنت لديك...)")
        api.upload_file(
            path_or_fileobj=str(db_path),
            path_in_repo="file_archive.db",
            repo_id=repo_id,
            repo_type="space"
        )
        print(" [+] تم رفع قاعدة البيانات بنجاح.")

    space_url = f"https://huggingface.co/spaces/{repo_id}"
    app_url = f"https://{username}-{space_name.replace('_', '-')}.hf.space"

    print("\n" + "🎉" * 35)
    print(" ✠ تم النشر السحابي الكامل بنجاح على Hugging Face Spaces! ✠")
    print(f" 🌐 رابط الـ Space: {space_url}")
    print(f" 🚀 رابط المساعد المباشر: {app_url}")
    print(f" 🤖 بوت تليجرام يعمل الآن 24/7 في السحاب: @ElantonyLibrarybot")
    print("🎉" * 35 + "\n")
    print(" 💤 يمكنك الآن إغلاق جهاز الكمبيوتر الشخصي تماماً؛")
    print("    فالمنظومة أصبحت تعمل في السحابة على مدار الساعة بدون توقف!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deploy(sys.argv[1])
    else:
        tok = input("أدخل Hugging Face Write Token: ").strip()
        deploy(tok)
