# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Background OCR Worker Engine (Phase 3 & 5 Roadmap)
Selectively extracts and recognizes text from scanned pages using Tesseract OCR,
operates at low CPU/memory priority to avoid affecting system responsiveness,
updates church_books, and indexes recognized chunks directly into FTS5.
"""

import sys
import os
import io
import time
import json
import sqlite3
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Ensure UTF-8 output and immediate line buffering on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import psutil
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

from modules import church_ai_config, book_discovery
from modules.church_ocr_engine import find_tesseract_binary, check_ocr_environment
from modules.rag_chunker import split_text_into_semantic_chunks


def setup_low_process_priority():
    """Sets process priority to BELOW_NORMAL to ensure system remains fast and responsive."""
    try:
        p = psutil.Process(os.getpid())
        if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def prevent_windows_sleep():
    """Keeps the system awake during intensive background OCR processing."""
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    except Exception:
        pass


def configure_tesseract(custom_bin: Optional[str] = None) -> Optional[str]:
    """Configures pytesseract binary and local tessdata prefix."""
    tess_bin = find_tesseract_binary(custom_bin)
    if not tess_bin:
        return None

    pytesseract.pytesseract.tesseract_cmd = tess_bin

    # Point TESSDATA_PREFIX to local project tessdata if exists, else standard install dir
    local_tessdata = BASE_DIR / "tessdata"
    if local_tessdata.exists() and (local_tessdata / "ara.traineddata").exists():
        os.environ["TESSDATA_PREFIX"] = str(local_tessdata)
    else:
        install_tessdata = Path(tess_bin).parent / "tessdata"
        if install_tessdata.exists():
            os.environ["TESSDATA_PREFIX"] = str(install_tessdata)

    return tess_bin


def ocr_single_page_image(
    page: fitz.Page,
    languages: str = "ara+eng",
    dpi: int = 200
) -> str:
    """
    Renders a PDF page to image and extracts text via Tesseract OCR.
    """
    try:
        # Render page to pixmap with reasonable DPI (200 is fast and highly legible)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to PIL Image in memory
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # Run OCR
        text = pytesseract.image_to_string(img, lang=languages, config="--psm 1")
        return text.strip()
    except Exception as e:
        return ""


def process_book_ocr(
    book_row: Tuple[str, str, str, str, str, str],
    conn: sqlite3.Connection,
    cfg: Dict[str, Any],
    tess_languages: str = "ara+eng"
) -> Dict[str, Any]:
    """
    Processes a single book's scanned pages needing OCR.
    """
    sha256, original_path, file_name, author, category, pages_json = book_row
    clean_title = Path(file_name).stem

    if not os.path.exists(original_path):
        return {"success": False, "error": "File not found", "pages_processed": 0}

    try:
        pages_to_ocr = json.loads(pages_json) if pages_json else []
    except Exception:
        pages_to_ocr = []

    if not pages_to_ocr:
        # No specific pages listed; inspect full document
        try:
            doc = fitz.open(original_path)
            pages_to_ocr = list(range(1, len(doc) + 1))
            doc.close()
        except Exception as e:
            return {"success": False, "error": str(e), "pages_processed": 0}

    try:
        doc = fitz.open(original_path)
    except Exception as e:
        return {"success": False, "error": str(e), "pages_processed": 0}

    extracted_dir = Path(cfg["paths"]["extracted_text"])
    extracted_dir.mkdir(parents=True, exist_ok=True)
    out_file = extracted_dir / f"{sha256}.txt"

    recognized_chunks = []
    pages_completed = []
    chunk_size = cfg.get("rag", {}).get("chunk_size_chars", 1200)
    chunk_overlap = cfg.get("rag", {}).get("chunk_overlap_chars", 150)

    for pnum in pages_to_ocr:
        if pnum < 1 or pnum > len(doc):
            continue

        page = doc[pnum - 1]
        page_text = ocr_single_page_image(page, languages=tess_languages)

        if page_text and len(page_text.strip()) > 20:
            pages_completed.append(pnum)
            page_chunks = split_text_into_semantic_chunks(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for cidx, ctext in enumerate(page_chunks):
                source_ref = f"[كتاب: {clean_title} (OCR)، ص: {pnum}]"
                recognized_chunks.append((
                    sha256, clean_title, pnum, cidx, source_ref, ctext
                ))

            # Append to text file
            with open(out_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- [صفحة {pnum} / Page {pnum} (OCR)] ---\n")
                f.write(page_text + "\n")

        # Sleep briefly to keep CPU cool
        time.sleep(0.05)

    doc.close()

    # Commit chunks and update church_books
    cur = conn.cursor()
    if recognized_chunks:
        cur.executemany("""
            INSERT INTO church_chunks_fts (
                sha256, book_title, page_number, chunk_index, source_reference, chunk_text
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, recognized_chunks)

    remaining_pages = [p for p in pages_to_ocr if p not in pages_completed]
    new_status = "completed" if len(remaining_pages) == 0 else "partial"

    cur.execute("""
        UPDATE church_books
        SET ocr_status = ?,
            extraction_status = ?,
            pages_needing_ocr = ?,
            has_digital_text = 1,
            last_processed_at = CURRENT_TIMESTAMP
        WHERE sha256 = ?
    """, (
        "completed" if len(remaining_pages) == 0 else "in_progress",
        new_status,
        json.dumps(remaining_pages),
        sha256
    ))
    conn.commit()

    return {
        "success": True,
        "title": clean_title,
        "pages_processed": len(pages_completed),
        "chunks_added": len(recognized_chunks),
        "remaining_pages": len(remaining_pages)
    }


def run_background_ocr_loop(
    db_path: str = "file_archive.db",
    custom_bin: Optional[str] = None,
    limit: Optional[int] = None
):
    """Main background loop."""
    setup_low_process_priority()
    prevent_windows_sleep()
    cfg = church_ai_config.load_config()

    print("=" * 72)
    print(" ✠ ELANTONY LIBRARY AI - مشغل المعالجة الضوئية الذكية في الخلفية (OCR) ✠")
    print("=" * 72)
    print(f" 📂 قاعدة البيانات   : {db_path}")

    tess_bin = configure_tesseract(custom_bin)
    if not tess_bin:
        installer_path = BASE_DIR / "installers" / "tesseract-setup.exe"
        print("\n [!] لم يتم العثور على محرك Tesseract OCR مثبتاً على نظام Windows حالياً.")
        print(f" 💡 تم تجهيز ملف التثبيت المعتمد في مجلد المشروع:\n    --> {installer_path}")
        print(" 📌 خطوات التشغيل السريعة:")
        print("    1. قم بتشغيل الملف أعلاه والموافقة على التثبيت بالخيارات الافتراضية.")
        print("    2. فور انتهاء التثبيت، أعد تشغيل هذا السكريبت وسيبدأ العمل تلقائياً في الخلفية.")
        print("=" * 72)
        return

    print(f" ⚙️ محرك Tesseract  : {tess_bin}")
    print(f" 📁 مجلد اللغات     : {os.environ.get('TESSDATA_PREFIX', 'Default')}")
    print(" 🛡️ أولوية المعالجة : منخفضة (BELOW_NORMAL) لضمان سرعة وهدوء الجهاز")
    print("=" * 72)

    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    cur = conn.cursor()

    query = """
        SELECT sha256, original_path, file_name, author, category, pages_needing_ocr
        FROM church_books
        WHERE extraction_status IN ('needs_ocr', 'partial') AND is_duplicate_of IS NULL
        ORDER BY page_count ASC
    """
    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    target_books = cur.fetchall()
    total_target = len(target_books)

    print(f"\n [*] الكتب المؤهلة للمعالجة الضوئية: {total_target:,} كتاباً")
    if total_target == 0:
        print(" [✓] لا توجد كتب تحتاج إلى OCR حالياً. جميع الكتب مفهرسة بالكامل!")
        conn.close()
        return

    total_chunks_added = 0
    total_pages_ocr = 0

    for idx, b in enumerate(target_books, 1):
        clean_title = Path(b[2]).stem
        if len(clean_title) > 36:
            clean_title = clean_title[:36] + "..."

        print(f" [>] [{idx}/{total_target}] جاري قراءة: «{clean_title}»...", end="", flush=True)

        res = process_book_ocr(b, conn, cfg)
        if res.get("success"):
            p_done = res.get("pages_processed", 0)
            c_added = res.get("chunks_added", 0)
            total_pages_ocr += p_done
            total_chunks_added += c_added
            print(f" ✓ {p_done} صفحة | +{c_added} مقطع FTS5 (إجمالي: {total_chunks_added:,})", flush=True)
        else:
            print(f" ⚠️ خطأ: {res.get('error')}", flush=True)

    conn.close()
    print("\n" + "=" * 72)
    print(f" [✓] اكتملت جلسة الـ OCR! إجمالي الصفحات: {total_pages_ocr:,} | إجمالي المقاطع: {total_chunks_added:,}")
    print("=" * 72)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ELANTONY Background OCR Engine")
    parser.add_argument("--db", type=str, default="file_archive.db")
    parser.add_argument("--tesseract-bin", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    run_background_ocr_loop(db_path=args.db, custom_bin=args.tesseract_bin, limit=args.limit)
