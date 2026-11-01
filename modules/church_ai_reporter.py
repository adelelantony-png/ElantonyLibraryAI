# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Quality Auditor & Reporting Engine
Generates detailed markdown audits and CSV reports on library volumes,
corrupted files, digital text extraction status, and OCR quality.
"""

import os
import csv
import json
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from modules import church_ai_config, book_discovery, church_ocr_engine


def get_catalog_statistics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves aggregated statistics from church_books SQLite table."""
    target_db = db_path or book_discovery.get_db_path()
    book_discovery.init_catalog_schema(target_db)
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()

    # Total discovered books
    cur.execute("SELECT COUNT(*) FROM church_books")
    total_books = cur.fetchone()[0]

    # Duplicates
    cur.execute("SELECT COUNT(*) FROM church_books WHERE is_duplicate_of IS NOT NULL")
    duplicates_count = cur.fetchone()[0]

    # Unique active books
    unique_books = total_books - duplicates_count

    # Status distribution
    cur.execute("SELECT extraction_status, COUNT(*) FROM church_books WHERE is_duplicate_of IS NULL GROUP BY extraction_status")
    status_counts = dict(cur.fetchall())

    # Total pages
    cur.execute("SELECT SUM(page_count) FROM church_books WHERE is_duplicate_of IS NULL")
    total_pages = cur.fetchone()[0] or 0

    # Total size in bytes
    cur.execute("SELECT SUM(file_size) FROM church_books WHERE is_duplicate_of IS NULL")
    total_bytes = cur.fetchone()[0] or 0

    # Language breakdown
    cur.execute("SELECT language_detected, COUNT(*) FROM church_books WHERE is_duplicate_of IS NULL AND language_detected IS NOT NULL GROUP BY language_detected")
    lang_counts = dict(cur.fetchall())

    # Average quality score
    cur.execute("SELECT AVG(quality_score) FROM church_books WHERE extraction_status IN ('completed', 'partial') AND is_duplicate_of IS NULL")
    avg_quality = cur.fetchone()[0] or 0.0

    # Damaged / unreadable files
    cur.execute("SELECT COUNT(*) FROM church_books WHERE extraction_status = 'corrupted' OR error_message IS NOT NULL")
    damaged_count = cur.fetchone()[0]

    conn.close()

    return {
        "total_books": total_books,
        "unique_books": unique_books,
        "duplicates_count": duplicates_count,
        "total_pages": total_pages,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "status_counts": status_counts,
        "language_counts": lang_counts,
        "average_quality_score": round(avg_quality, 2),
        "damaged_count": damaged_count
    }


def generate_corrupted_files_csv(output_path: Optional[str] = None, db_path: Optional[str] = None) -> str:
    """Generates a CSV report listing all corrupted or unreadable PDF files."""
    target_db = db_path or book_discovery.get_db_path()
    book_discovery.init_catalog_schema(target_db)
    cfg = church_ai_config.load_config()
    out_p = Path(output_path or (Path(cfg["paths"]["reports"]) / "corrupted_files_report.csv"))
    out_p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        SELECT sha256, original_path, file_name, file_size, error_message, first_seen_at
        FROM church_books
        WHERE extraction_status = 'corrupted' OR error_message IS NOT NULL
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    with open(out_p, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["SHA256", "Original Path", "File Name", "File Size (Bytes)", "Error Description", "Discovered Date"])
        for r in rows:
            writer.writerow(r)

    return str(out_p)


def generate_ocr_quality_csv(output_path: Optional[str] = None, db_path: Optional[str] = None) -> str:
    """Generates a CSV report detailing digital vs OCR extraction quality per book."""
    target_db = db_path or book_discovery.get_db_path()
    book_discovery.init_catalog_schema(target_db)
    cfg = church_ai_config.load_config()
    out_p = Path(output_path or (Path(cfg["paths"]["reports"]) / "ocr_quality_report.csv"))
    out_p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        SELECT sha256, file_name, page_count, pages_needing_ocr, quality_score, extraction_status, language_detected, original_path
        FROM church_books
        WHERE is_duplicate_of IS NULL
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    with open(out_p, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "SHA256", "Book Title", "Total Pages", "Pending OCR Pages Count", 
            "Quality Score", "Extraction Status", "Language", "Original Path"
        ])
        for r in rows:
            sha256, title, page_cnt, raw_pages, qscore, status, lang, path = r
            try:
                ocr_count = len(json.loads(raw_pages)) if raw_pages else 0
            except Exception:
                ocr_count = 0
            writer.writerow([sha256, title, page_cnt, ocr_count, qscore, status, lang, path])

    return str(out_p)


def generate_markdown_audit_report(output_path: Optional[str] = None, db_path: Optional[str] = None) -> str:
    """Generates a comprehensive executive Markdown audit report for the church library."""
    target_db = db_path or book_discovery.get_db_path()
    cfg = church_ai_config.load_config()
    out_p = Path(output_path or (Path(cfg["paths"]["reports"]) / "church_ai_audit_report.md"))
    out_p.parent.mkdir(parents=True, exist_ok=True)

    stats = get_catalog_statistics(db_path=target_db)
    ocr_diag = church_ocr_engine.check_ocr_environment(cfg)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = f"""# تقرير التدقيق الفني الشامل لمكتبة ChurchAI الكنسية
**تاريخ إصدار التقرير:** {now_str}  
**قاعدة البيانات:** `{target_db}`  

---

## 1. الملخص التنفيذي للمكتبة (Executive Summary)

| المؤشر | القيمة | الوصف |
| :--- | :--- | :--- |
| **إجمالي الكتب المفهرسة** | `{stats['total_books']}` | إجمالي ملفات PDF المسجلة داخل النظام |
| **الكتب الفريدة المستقلة** | `{stats['unique_books']}` | بعد استبعاد النسخ المكررة والمطابقة SHA-256 |
| **الكتب المكررة المكتشفة** | `{stats['duplicates_count']}` | تم ربطها تلقائيًا بالأصل دون تكرار المعالجة |
| **إجمالي الصفحات المقروءة** | `{stats['total_pages']:,}` | صفحة مسجلة |
| **الحجم الإجمالي للكتب** | `{stats['total_size_mb']:,} MB` | مساحة التخزين الفعلية |
| **الملفات التالفة أو غير القابلة للقراءة** | `{stats['damaged_count']}` | تم توثيقها في تقرير التوالف المنفصل |
| **متوسط مؤشر جودة النصوص** | `{stats['average_quality_score']} / 100` | جودة النصوص العربية والقبطية المستخرجة |

---

## 2. حالة المعالجة والاستخراج (Processing Pipeline Status)

```
"""
    status_counts = stats["status_counts"]
    for status, count in status_counts.items():
        pct = (count / max(stats['unique_books'], 1)) * 100
        md += f"  - {status:15s}: {count:5d} كتاب ({pct:5.1f}%)\n"

    md += f"""```

- **نصوص رقمية مكتملة (Completed):** كتب تحتوي على طبقة نصية رقمية سليمة 100% ولا تتطلب أي OCR.
- **معالجة جزئية (Partial):** كتب تم استخراج نصوص صفحاتها الرقمية مع وجود بعض الصفحات المصورة قيد جدولة OCR.
- **تتطلب استخراجًا ضوئيًا (Needs OCR):** كتب ومجلدات مصورة وممسوحة ضوئيًا بالكامل.
- **قيد الانتظار (Pending):** كتب تم فهرستها في انتظار دورة المعالجة.

---

## 3. التوزيع اللغوي للمراجع (Linguistic Distribution)

| اللغة المكتشفة | الرمز | عدد المراجع | النسبة |
| :--- | :---: | :---: | :---: |
"""
    lang_counts = stats["language_counts"]
    total_lang_books = sum(lang_counts.values()) or 1
    lang_labels = {"ara": "العربية", "cop": "القبطية الكنسية", "eng": "الإنجليزية / لغات أخرى"}
    for lang, cnt in lang_counts.items():
        label = lang_labels.get(lang, lang)
        pct = (cnt / total_lang_books) * 100
        md += f"| {label} | `{lang}` | {cnt} | {pct:.1f}% |\n"

    md += f"""
---

## 4. تشخيص أدوات التعرف الضوئي OCR (Tesseract Environment)

- **حالة الأداة في النظام:** {'✅ جاهزة ومتاحة' if ocr_diag['is_available'] else '⚠️ غير مثبتة أو غير مفعلة في المسار الافتراضي'}
- **مسار الأداة:** `{ocr_diag.get('tesseract_path') or 'غير محدد'}`
- **الإصدار الحالي:** `{ocr_diag.get('version') or 'غير متوفر'}`
- **اللغات المثبتة:** `{', '.join(ocr_diag.get('available_languages', [])) or 'لا يوجد'}`
- **اللغات الناقصة:** `{', '.join(ocr_diag.get('missing_languages', [])) or 'لا يوجد'}`

### أمر التثبيت السريع عبر Windows 11 (winget):
```powershell
{ocr_diag['install_guide']['winget_command']}
```

---

## 5. تقارير التدقيق المرفقة
- **تقرير الملفات التالفة:** [`reports/corrupted_files_report.csv`](file:///{cfg['paths']['reports'].replace(os.sep, '/')}/corrupted_files_report.csv)
- **تقرير جودة الاستخراج الضوئي:** [`reports/ocr_quality_report.csv`](file:///{cfg['paths']['reports'].replace(os.sep, '/')}/ocr_quality_report.csv)
"""

    with open(out_p, "w", encoding="utf-8") as f:
        f.write(md)

    return str(out_p)
