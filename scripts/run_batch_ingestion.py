# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
High-Performance Batch Book Ingestion Engine (Phase 2 Roadmap)
Recursively scans library volumes, computes SHA-256, extracts page counts via PyMuPDF,
infers categories and authors, handles duplicates safely, and records to SQLite.
"""

import sys
import os
import hashlib
import sqlite3
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import fitz  # PyMuPDF
from elantony.database.repository import repo


def infer_category_and_author(file_path: str, file_name: str) -> Tuple[str, str]:
    """Infers category and ecclesiastical author from folder hierarchy and file name."""
    p = Path(file_path)
    parent_folder = p.parent.name
    
    # Category mapping
    category = "عام"
    if parent_folder and parent_folder not in ["books", "local", "downloaded", "ArchiveMaster"]:
        category = parent_folder
    
    # Author mapping
    combined = f"{parent_folder} {file_name}".lower()

    if "شنودة" in combined or "shenouda" in combined:
        author = "قداسة البابا شنودة الثالث"
    elif "أثناسيوس" in combined or "athanasius" in combined:
        author = "القديس أثناسيوس الرسولي"
    elif "كيرلس الكبير" in combined or "عمود الدين" in combined or "كيرلس الاسكندري" in combined or "cyril" in combined:
        author = "القديس كيرلس الكبير"
    elif "أنطونيوس" in combined or "antony" in combined:
        author = "القديس الأنبا أنطونيوس"
    elif "متى المسكين" in combined or "matta" in combined:
        author = "الأب متى المسكين"
    elif "تادرس يعقوب" in combined or "tadros" in combined:
        author = "القمص تادرس يعقوب ملطي"
    elif "بيشوي كامل" in combined:
        author = "القمص بيشوي كامل"
    elif "يوحنا ذهبي الفم" in combined or "chrysostom" in combined:
        author = "القديس يوحنا ذهبي الفم"
    elif "إسحق السرياني" in combined or "مار اسحق" in combined:
        author = "مار إسحق السرياني"
    elif "جيروم" in combined or "إيرونيموس" in combined or "jerome" in combined:
        author = "القديس جيروم"
    elif "غريغوريوس" in combined or "gregory" in combined:
        author = "القديس غريغوريوس اللاهوتي"
    elif "باسليوس" in combined or "basil" in combined:
        author = "القديس باسيليوس الكبير"
    elif "مقار" in combined or "مكاريوس" in combined or "macarius" in combined:
        author = "القديس مقاريوس الكبير"
    elif "يوحنا كاسيان" in combined or "cassian" in combined:
        author = "القديس يوحنا كاسيان"
    elif "أبيفانيوس" in combined:
        author = "الأنبا أبيفانيوس أسقف دير أبو مقار"
    elif "يوأنس" in combined:
        author = "الأنبا يوأنس أسقف الغربية"
    else:
        author = "آباء ومعلمو الكنيسة"

    return category, author


def compute_sha256(file_path: str, chunk_size: int = 131072) -> str:
    """Computes SHA-256 hash in 128KB chunks for fast streaming."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect_pdf_safety(file_path: str) -> Tuple[bool, int, Optional[str]]:
    """Fast probe of PDF structure and total pages via PyMuPDF."""
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(""):
                doc.close()
                return False, 0, "الملف محمي بكلمة مرور"
        page_count = len(doc)
        doc.close()
        return True, page_count, None
    except Exception as e:
        return False, 0, f"تلف في ملف PDF: {str(e)}"


def run_batch_ingestion(
    target_root: str,
    db_path: str = "file_archive.db",
    max_books: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes high-throughput batch cataloging across target_root.
    """
    print("=" * 70)
    print(" ✠ ELANTONY LIBRARY AI - خطة الفهرسة الدفعية الشاملة للكتب ✠")
    print("=" * 70)
    print(f" 📂 المجلد المستهدف : {target_root}")
    print(f" 🗄️ قاعدة البيانات  : {db_path}")
    print("=" * 70)

    # 1. Initialize schema and load existing books into memory for O(1) deduplication
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")
    cur = conn.cursor()

    repo.init_schema()

    cur.execute("SELECT sha256, original_path FROM church_books")
    existing_records = {row[0]: row[1] for row in cur.fetchall()}
    existing_paths = set(existing_records.values())
    print(f" [*] عدد الكتب المسجلة مسبقاً في قاعدة البيانات: {len(existing_records)}")

    # 2. Collect all candidate PDFs
    print(" [*] جاري مسح واكتشاف جميع ملفات PDF...")
    ignore_folders = {"ArchiveMaster", "_Duplicates_Isolated", "_System_Temp_Cache", "_scripts", ".git"}
    candidate_files = []

    for root, dirs, files in os.walk(target_root):
        # Skip internal and duplicate cache folders
        dirs[:] = [d for d in dirs if d not in ignore_folders and not d.startswith(".")]
        for f in files:
            if f.lower().endswith(".pdf"):
                full_p = os.path.abspath(os.path.join(root, f))
                candidate_files.append(full_p)

    total_candidates = len(candidate_files)
    print(f" [*] إجمالي ملفات PDF المكتشفة في المسارات: {total_candidates} كتاباً")

    if max_books:
        candidate_files = candidate_files[:max_books]
        print(f" [!] تم تحديد سقف المعالجة الحالية إلى: {max_books} كتاباً للاختبار")

    stats = {
        "total_scanned": 0,
        "new_added": 0,
        "existing_unchanged": 0,
        "duplicates_detected": 0,
        "corrupted_files": 0,
        "total_pages": 0,
        "total_size_bytes": 0
    }

    batch_buffer = []
    start_time = datetime.datetime.now()

    for idx, f_path in enumerate(candidate_files, 1):
        stats["total_scanned"] += 1
        f_name = os.path.basename(f_path)

        try:
            f_stat = os.stat(f_path)
            f_size = f_stat.st_size
            mod_time = datetime.datetime.fromtimestamp(f_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            stats["corrupted_files"] += 1
            continue

        stats["total_size_bytes"] += f_size

        # If path already cataloged, skip hashing to maximize speed
        if f_path in existing_paths:
            stats["existing_unchanged"] += 1
            if idx % 100 == 0 or idx == len(candidate_files):
                print(f" -> معالجة: {idx}/{len(candidate_files)} (تخطي المفهرس مسبقاً)")
            continue

        # Compute SHA-256
        try:
            file_hash = compute_sha256(f_path)
        except Exception as e:
            stats["corrupted_files"] += 1
            continue

        category, author = infer_category_and_author(f_path, f_name)

        # Check for duplication by hash
        if file_hash in existing_records:
            stats["duplicates_detected"] += 1
            dup_sha = f"{file_hash}_dup_{stats['duplicates_detected']}"
            cur.execute("""
                INSERT OR IGNORE INTO church_books
                (sha256, original_path, file_name, file_size, mod_time, author, category, extraction_status, is_duplicate_of)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'duplicate', ?)
            """, (dup_sha, f_path, f_name, f_size, mod_time, author, category, file_hash))
            existing_records[dup_sha] = f_path
            existing_paths.add(f_path)
            continue

        # Verify PDF structure & page count
        is_valid, page_count, err = inspect_pdf_safety(f_path)
        if not is_valid:
            stats["corrupted_files"] += 1
            status = "corrupted"
        else:
            stats["new_added"] += 1
            status = "pending"
            stats["total_pages"] += page_count

        cur.execute("""
            INSERT OR REPLACE INTO church_books
            (sha256, original_path, file_name, file_size, mod_time, page_count, author, category, storage_provider, extraction_status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'local', ?, ?)
        """, (file_hash, f_path, f_name, f_size, mod_time, page_count, author, category, status, err))

        existing_records[file_hash] = f_path
        existing_paths.add(f_path)

        # Commit every 50 books for high throughput
        if stats["new_added"] % 50 == 0:
            conn.commit()

        if idx % 100 == 0 or idx == len(candidate_files):
            pct = (idx / len(candidate_files)) * 100
            print(f" -> تقدم الفهرسة: {idx}/{len(candidate_files)} ({pct:.1f}%) | مضاف جديد: {stats['new_added']} | مكرر: {stats['duplicates_detected']}")

    conn.commit()
    conn.close()

    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    print("=" * 70)
    print(" ✠ اكتملت الفهرسة الدفعية بنجاح! ✠")
    print(f" ⏱️ الوقت المستغرق       : {elapsed:.1f} ثانية")
    print(f" 📚 إجمالي الملفات المفحوصة: {stats['total_scanned']}")
    print(f" ➕ كتب جديدة أضيفت      : {stats['new_added']}")
    print(f" 🔄 كتب مفهرسة لم تتغير  : {stats['existing_unchanged']}")
    print(f" 📑 ملفات مكررة تم رصدها : {stats['duplicates_detected']}")
    print(f" ⚠️ ملفات تالفة تم حصرها  : {stats['corrupted_files']}")
    print(f" 💾 الحجم الإجمالي المفحوص: {stats['total_size_bytes'] / (1024**3):.2f} GB")
    print("=" * 70)

    # Generate Markdown Report
    report_md = f"""# 📊 تقرير الفهرسة الدفعية الشاملة للمكتبة الكنسية

**تاريخ التوليد:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**المجلد الرئيسي:** `{target_root}`

## 📈 ملخص الإحصائيات
| البند | القيمة |
| :--- | :--- |
| **إجمالي الكتب المكتشفة** | {stats['total_scanned']:,} كتاباً |
| **الكتب الجديدة التي أضيفت** | {stats['new_added']:,} كتاباً |
| **الكتب المسجلة مسبقاً (دون تغيير)** | {stats['existing_unchanged']:,} كتاباً |
| **الملفات المكررة المكتشفة** | {stats['duplicates_detected']:,} ملفاً |
| **الملفات التالفة أو المحمية بكلمة سر** | {stats['corrupted_files']:,} ملفاً |
| **الحجم الإجمالي المفحوص** | {stats['total_size_bytes'] / (1024**3):.2f} GB |
| **الوقت المستغرق في الفهرسة** | {elapsed:.1f} ثانية |

## 🛡️ سياسة حماية الملفات
- تم حفظ مسارات جميع الملفات بدقة في قاعدة البيانات `file_archive.db`.
- **لم يتم حذف أو نقل أي ملف أصلي** من مكانه على القرص.
- تم ربط الملفات المكررة بالنسخة الأصلية عبر حقل `is_duplicate_of` لتجنب استهلاك موارد الـ OCR دون داعٍ.
"""
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "BATCH_INGESTION_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f" [✓] تم حفظ التقرير الشامل في: reports/BATCH_INGESTION_REPORT.md")
    return stats


if __name__ == "__main__":
    target = r"I:\2021\2020\✠ Cross Coptic Library ✠"
    run_batch_ingestion(target_root=target)
