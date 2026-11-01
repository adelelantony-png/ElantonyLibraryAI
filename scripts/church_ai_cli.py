# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Command Line Interface (CLI)
PowerShell-compatible runner for library scanning, text extraction, OCR, RAG, and reporting.
"""

import sys
import os
import argparse
from pathlib import Path

# Enforce UTF-8 on Windows PowerShell / CMD to prevent charmap encoding errors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules import (
    church_ai_config,
    book_discovery,
    digital_extractor,
    church_ocr_engine,
    batch_processor,
    church_ai_reporter,
    rag_chunker
)


def cmd_status(args):
    """Displays current library cataloging and extraction status."""
    print("=" * 65)
    print(" ✠ ArchiveMaster ChurchAI - حالة المكتبة الكنسية ✠")
    print("=" * 65)
    stats = church_ai_reporter.get_catalog_statistics()
    print(f" • إجمالي الكتب المسجلة   : {stats['total_books']}")
    print(f" • الكتب الفريدة           : {stats['unique_books']}")
    print(f" • النسخ المكررة          : {stats['duplicates_count']}")
    print(f" • إجمالي عدد الصفحات     : {stats['total_pages']:,}")
    print(f" • الحجم الإجمالي         : {stats['total_size_mb']:,} MB")
    print(f" • الكتب التالفة/المتعذرة : {stats['damaged_count']}")
    print(f" • متوسط مؤشر الجودة     : {stats['average_quality_score']} / 100")
    print("\n [حالات المعالجة]:")
    for st, cnt in stats["status_counts"].items():
        print(f"   - {st:15s}: {cnt}")
    print("\n [اللغات المكتشفة]:")
    for lg, cnt in stats["language_counts"].items():
        print(f"   - {lg:15s}: {cnt}")

    print("\n [تشخيص محرك OCR]:")
    diag = church_ocr_engine.check_ocr_environment()
    if diag["is_available"]:
        print(f"   ✅ Tesseract متاح في: {diag['tesseract_path']}")
        print(f"   اللغات المتاحة: {', '.join(diag['available_languages'])}")
    else:
        print("   ⚠️ Tesseract OCR غير مثبت أو غير مضاف للمسار.")
        print(f"   لتثبيته نفذ: {diag['install_guide']['winget_command']}")
    print("=" * 65)


def cmd_scan(args):
    """Scans and catalogs PDF volumes from paths."""
    proc = batch_processor.ChurchBatchProcessor()
    paths = args.path or [r"I:\2021\2020\✠ Cross Coptic Library ✠"]
    print(f"[*] جاري فحص واكتشاف الكتب في: {paths}")
    stats = proc.scan_and_catalog(paths, progress_callback=lambda msg: print(f"  > {msg}"))
    print("\n[✔] اكتمل الفحص وتحديث قاعدة البيانات بنجاح.")


def cmd_extract(args):
    """Extracts digital text page-by-page."""
    proc = batch_processor.ChurchBatchProcessor()
    limit = args.limit
    print(f"[*] جاري بدء استخراج النصوص الرقمية (الحد الأقصى: {limit or 'الكل'})...")

    def on_prog(info):
        print(f"  [{info['current']}/{info['total']}] {info['file_name'][:40]} | حالة: {info['status']} | جودة: {info['quality_score']} | ذاكرة: {info['memory_mb']} MB")

    res = proc.run_digital_extraction(limit=limit, progress_callback=on_prog)
    print(f"\n[✔] انتهت دورة الاستخراج الرقمي: تمت معالجة {res['processed']} كتاب، فشل {res['failed']}، و {res['books_needing_ocr']} يحتاج استخراج ضوئي OCR.")


def cmd_ocr(args):
    """Runs selective OCR on pages needing it."""
    proc = batch_processor.ChurchBatchProcessor()
    limit = args.limit
    print(f"[*] جاري تشغيل التعرف الضوئي الانتقائي (الحد الأقصى: {limit or 'الكل'})...")

    def on_prog(info):
        print(f"  [{info['current']}/{info['total']}] {info['file_name'][:40]} | صفحات مكتملة: {info['completed_pages']} | صفحات متبقية: {info['remaining_pages']}")

    res = proc.run_selective_ocr(limit=limit, progress_callback=on_prog)
    if not res.get("success"):
        print(f" [!] تنبيه: {res.get('error')}")
        if "diagnostic" in res:
            print(f"     أمر التثبيت: {res['diagnostic']['install_guide']['winget_command']}")
    else:
        print(f"\n[✔] اكتملت دورة OCR: تمت معالجة {res['processed']} كتاب.")


def cmd_rag(args):
    """Chunks extracted texts for RAG and indexes in SQLite FTS5."""
    import sqlite3
    db_p = book_discovery.get_db_path()
    conn = sqlite3.connect(db_p)
    cur = conn.cursor()
    cur.execute("""
        SELECT sha256, file_name 
        FROM church_books 
        WHERE extraction_status IN ('completed', 'partial') AND processed_text_path IS NULL AND is_duplicate_of IS NULL
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"[*] جاري تجهيز مقاطع RAG وفهرستها لعدد {len(rows)} كتاب...")
    for idx, (sha, title) in enumerate(rows):
        res = rag_chunker.process_book_for_rag(sha)
        if res["success"]:
            print(f"  [{idx+1}/{len(rows)}] تم تقطيع وفهرسة: {title[:40]} ({res['chunks_count']} مقطع دلالي)")
    print("[✔] اكتمل تجهيز وفهرسة المقاطع الدلالية بنجاح.")


def cmd_report(args):
    """Generates Markdown audit and CSV quality reports."""
    print("[*] جاري توليد تقارير التدقيق الفني الشاملة...")
    md_p = church_ai_reporter.generate_markdown_audit_report()
    c_p = church_ai_reporter.generate_corrupted_files_csv()
    q_p = church_ai_reporter.generate_ocr_quality_csv()
    print(f" [✔] تم توليد التقرير التنفيذي: {md_p}")
    print(f" [✔] تم توليد تقرير الملفات التالفة: {c_p}")
    print(f" [✔] تم توليد تقرير جودة OCR: {q_p}")


def cmd_search(args):
    """Searches indexed ecclesiastical texts using local FTS5."""
    query = args.query
    print(f"[*] البحث الدلالي السريع عن: '{query}'...")
    hits = rag_chunker.search_church_rag(query, limit=args.limit)
    if not hits:
        print("  لم يتم العثور على نتائج مطابقة.")
        return
    print(f"\nتم العثور على {len(hits)} نتيجة مطابقة:\n")
    for i, h in enumerate(hits, 1):
        print(f"  [{i}] {h['source_reference']}")
        snippet = h['chunk_text'].strip().replace("\n", " ")[:200]
        print(f"      \"{snippet}...\"\n")


def cmd_server(args):
    """Starts ChurchAI Mobile Cloud & Telegram Server."""
    from scripts import start_church_cloud
    start_church_cloud.main()


def cmd_pipeline(args):
    """Executes the complete end-to-end pipeline."""
    print("=" * 65)
    print(" ✠ بدء خط المعالجة المتكامل الكامل لمكتبة ChurchAI ✠")
    print("=" * 65)
    cmd_scan(args)
    cmd_extract(args)
    cmd_ocr(args)
    cmd_rag(args)
    cmd_report(args)
    cmd_status(args)
    print("\n[✔] اكتمل خط المعالجة المتكامل بنجاح تام.")


def main():
    parser = argparse.ArgumentParser(description="ArchiveMaster ChurchAI CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # status
    p_status = subparsers.add_parser("status", help="Display library catalog and OCR status")

    # scan
    p_scan = subparsers.add_parser("scan", help="Discover and catalog PDF library books")
    p_scan.add_argument("--path", nargs="+", help="Directory paths to scan")

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract digital text page-by-page")
    p_extract.add_argument("--limit", type=int, default=None, help="Max number of books to process")

    # ocr
    p_ocr = subparsers.add_parser("ocr", help="Run selective OCR on pages needing it")
    p_ocr.add_argument("--limit", type=int, default=None, help="Max number of books to OCR")

    # rag
    p_rag = subparsers.add_parser("rag", help="Chunk extracted books and build FTS5 index")

    # report
    p_report = subparsers.add_parser("report", help="Generate Markdown audit and CSV reports")

    # search
    p_search = subparsers.add_parser("search", help="Search the indexed library chunks")
    p_search.add_argument("query", help="Text query to search")
    p_search.add_argument("--limit", type=int, default=5, help="Max results to return")

    # server
    p_server = subparsers.add_parser("server", help="Launch Mobile Cloud & Telegram Server")

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="Run full pipeline: scan -> extract -> ocr -> rag -> report")
    p_pipe.add_argument("--path", nargs="+", help="Directory paths to scan")
    p_pipe.add_argument("--limit", type=int, default=None, help="Max books to process")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "scan": cmd_scan,
        "extract": cmd_extract,
        "ocr": cmd_ocr,
        "rag": cmd_rag,
        "report": cmd_report,
        "search": cmd_search,
        "server": cmd_server,
        "pipeline": cmd_pipeline
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
