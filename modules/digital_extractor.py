# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Digital Text Extraction & Quality Engine
Extracts digital text page-by-page, analyzes linguistic quality (Arabic, Coptic, English),
detects gibberish/scanned pages, and flags pages requiring OCR.
"""

import os
import re
import json
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import fitz  # PyMuPDF
from modules import church_ai_config, book_discovery

# Regex ranges for linguistic detection
RE_ARABIC = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
RE_COPTIC = re.compile(r'[\u2C80-\u2CFF\u0370-\u03FF]')
RE_ENGLISH = re.compile(r'[a-zA-Z]')
RE_DIGITS = re.compile(r'[0-9\u0660-\u0669]')
RE_GIBBERISH_SYMBOLS = re.compile(r'[\uFFFD\u0000-\u0008\u000B\u000C\u000E-\u001F]')


def evaluate_text_quality(text: str, min_clean_len: int = 30) -> Dict[str, Any]:
    """
    Evaluates linguistic quality and coherence of extracted page text.
    Detects Arabic, Coptic, English ratios and identifies font corruption/gibberish.
    """
    if not text or not text.strip():
        return {
            "status": "empty",
            "quality_score": 0.0,
            "total_chars": 0,
            "clean_chars": 0,
            "arabic_ratio": 0.0,
            "coptic_ratio": 0.0,
            "english_ratio": 0.0,
            "gibberish_score": 0.0,
            "needs_ocr": True,
            "detected_language": "unknown"
        }

    raw_len = len(text)
    clean_text = re.sub(r'\s+', '', text)
    clean_len = len(clean_text)

    if clean_len == 0:
        return {
            "status": "empty",
            "quality_score": 0.0,
            "total_chars": raw_len,
            "clean_chars": 0,
            "arabic_ratio": 0.0,
            "coptic_ratio": 0.0,
            "english_ratio": 0.0,
            "gibberish_score": 0.0,
            "needs_ocr": True,
            "detected_language": "unknown"
        }

    arabic_chars = len(RE_ARABIC.findall(clean_text))
    coptic_chars = len(RE_COPTIC.findall(clean_text))
    english_chars = len(RE_ENGLISH.findall(clean_text))
    digit_chars = len(RE_DIGITS.findall(clean_text))
    gibberish_chars = len(RE_GIBBERISH_SYMBOLS.findall(text))

    # Detect excessive non-alphanumeric punctuation ratio indicative of encoding corruption
    alphanumeric_count = arabic_chars + coptic_chars + english_chars + digit_chars
    non_alphanumeric_count = clean_len - alphanumeric_count

    arabic_ratio = arabic_chars / clean_len
    coptic_ratio = coptic_chars / clean_len
    english_ratio = english_chars / clean_len
    gibberish_score = (gibberish_chars * 3 + max(0, non_alphanumeric_count - 10)) / max(clean_len, 1)
    gibberish_score = min(1.0, max(0.0, gibberish_score))

    # Determine dominant language
    lang_scores = {"ara": arabic_chars, "cop": coptic_chars, "eng": english_chars}
    dominant_lang = max(lang_scores, key=lang_scores.get)
    if lang_scores[dominant_lang] == 0:
        dominant_lang = "unknown"

    # Compute overall composite quality score (0.0 to 100.0)
    # Rewards meaningful words, penalizes length deficiency and gibberish
    if clean_len < min_clean_len:
        quality_score = max(5.0, (clean_len / min_clean_len) * 40.0)
        status = "short_or_scanned"
        needs_ocr = True
    elif gibberish_score > 0.4:
        quality_score = max(0.0, (1.0 - gibberish_score) * 40.0)
        status = "gibberish_font_error"
        needs_ocr = True
    else:
        # High quality digital text
        base_score = 70.0 + (min(clean_len, 500) / 500.0) * 30.0
        penalty = gibberish_score * 40.0
        quality_score = min(100.0, max(0.0, base_score - penalty))
        status = "clean_digital"
        needs_ocr = False

    return {
        "status": status,
        "quality_score": round(quality_score, 2),
        "total_chars": raw_len,
        "clean_chars": clean_len,
        "arabic_ratio": round(arabic_ratio, 3),
        "coptic_ratio": round(coptic_ratio, 3),
        "english_ratio": round(english_ratio, 3),
        "gibberish_score": round(gibberish_score, 3),
        "needs_ocr": needs_ocr,
        "detected_language": dominant_lang
    }


def extract_digital_book(
    pdf_path: str,
    sha256: Optional[str] = None,
    output_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extracts text page-by-page from a PDF using PyMuPDF.
    Evaluates quality of each page, marks pages requiring OCR,
    and writes extracted text to extracted_text/{sha256}.txt with standard page delimiters.
    """
    cfg = config or church_ai_config.load_config()
    min_clean_len = cfg.get("extraction", {}).get("min_text_len_per_page", 30)

    if not sha256:
        sha256 = book_discovery.compute_sha256(pdf_path)

    out_dir = Path(output_dir or cfg["paths"]["extracted_text"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{sha256}.txt"

    pages_needing_ocr: List[int] = []
    page_qualities: List[float] = []
    detected_languages_count: Dict[str, int] = {"ara": 0, "eng": 0, "cop": 0}
    extracted_pages_data: List[Tuple[int, str, Dict[str, Any]]] = []

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to open PDF: {str(e)}",
            "sha256": sha256,
            "page_count": 0,
            "pages_needing_ocr": [],
            "quality_score": 0.0,
            "status": "corrupted"
        }

    total_pages = len(doc)
    digital_page_count = 0

    try:
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            # Extract raw digital text
            text = page.get_text("text") or ""
            eval_res = evaluate_text_quality(text, min_clean_len=min_clean_len)

            # Check if page has images when text is absent or low quality
            image_list = page.get_images()
            has_images = len(image_list) > 0

            # If text is too short or gibberish, and page has images, it definitely needs OCR
            if eval_res["needs_ocr"] or (eval_res["clean_chars"] < min_clean_len and has_images):
                pages_needing_ocr.append(page_num)
            else:
                digital_page_count += 1

            lang = eval_res["detected_language"]
            if lang in detected_languages_count:
                detected_languages_count[lang] += 1

            page_qualities.append(eval_res["quality_score"])
            extracted_pages_data.append((page_num, text.strip(), eval_res))

        doc.close()

    except Exception as e:
        if 'doc' in locals() and doc:
            doc.close()
        return {
            "success": False,
            "error": f"Error during page extraction: {str(e)}",
            "sha256": sha256,
            "page_count": total_pages,
            "pages_needing_ocr": pages_needing_ocr,
            "quality_score": 0.0,
            "status": "failed"
        }

    # Save to disk with standardized page delimiters
    with open(out_file, "w", encoding="utf-8") as f:
        for page_num, ptext, peval in extracted_pages_data:
            f.write(f"--- [صفحة {page_num} / Page {page_num}] ---\n")
            if ptext:
                f.write(ptext + "\n\n")
            else:
                f.write("[صفحة تحتاج إلى استخراج ضوئي OCR أو صفحة فارغة]\n\n")

    avg_quality = round(sum(page_qualities) / max(total_pages, 1), 2)
    has_digital_text = 1 if digital_page_count > 0 else 0

    # Determine overall status
    if total_pages == 0:
        overall_status = "empty"
    elif len(pages_needing_ocr) == 0:
        overall_status = "completed"
    elif digital_page_count > 0:
        overall_status = "partial"
    else:
        overall_status = "needs_ocr"

    dominant_lang = max(detected_languages_count, key=detected_languages_count.get)
    if detected_languages_count[dominant_lang] == 0:
        dominant_lang = "ara"

    result = {
        "success": True,
        "sha256": sha256,
        "pdf_path": pdf_path,
        "page_count": total_pages,
        "digital_pages_count": digital_page_count,
        "ocr_needed_pages_count": len(pages_needing_ocr),
        "pages_needing_ocr": pages_needing_ocr,
        "quality_score": avg_quality,
        "has_digital_text": has_digital_text,
        "extraction_status": overall_status,
        "language_detected": dominant_lang,
        "extracted_text_path": str(out_file),
        "total_chars": sum(p[2]["total_chars"] for p in extracted_pages_data)
    }

    return result


def update_catalog_digital_status(
    result: Dict[str, Any],
    db_path: Optional[str] = None
) -> None:
    """
    Updates the church_books record in SQLite with digital extraction results.
    """
    target_db = db_path or book_discovery.get_db_path()
    conn = sqlite3.connect(target_db)
    cur = conn.cursor()

    cur.execute("""
        UPDATE church_books
        SET has_digital_text = ?,
            quality_score = ?,
            pages_needing_ocr = ?,
            extraction_status = ?,
            language_detected = ?,
            extracted_text_path = ?,
            page_count = CASE WHEN page_count = 0 THEN ? ELSE page_count END,
            last_processed_at = CURRENT_TIMESTAMP
        WHERE sha256 = ?
    """, (
        result.get("has_digital_text", 0),
        result.get("quality_score", 0.0),
        json.dumps(result.get("pages_needing_ocr", [])),
        result.get("extraction_status", "pending"),
        result.get("language_detected", "ara"),
        result.get("extracted_text_path", ""),
        result.get("page_count", 0),
        result.get("sha256", "")
    ))

    conn.commit()
    conn.close()


def process_digital_extraction_batch(
    limit: int = 50,
    db_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetches pending books from church_books and extracts digital text.
    """
    target_db = db_path or book_discovery.get_db_path()
    cfg = config or church_ai_config.load_config()

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        SELECT sha256, original_path, file_name 
        FROM church_books 
        WHERE extraction_status = 'pending' AND is_duplicate_of IS NULL
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    processed_count = 0
    clean_count = 0
    partial_count = 0
    needs_ocr_count = 0
    errors: List[Dict[str, Any]] = []

    for sha256, original_path, file_name in rows:
        if not os.path.exists(original_path):
            continue

        res = extract_digital_book(original_path, sha256=sha256, config=cfg)
        if res["success"]:
            update_catalog_digital_status(res, db_path=target_db)
            processed_count += 1
            st = res["extraction_status"]
            if st == "completed":
                clean_count += 1
            elif st == "partial":
                partial_count += 1
            elif st == "needs_ocr":
                needs_ocr_count += 1
        else:
            errors.append({"sha256": sha256, "file": file_name, "error": res.get("error", "")})

    return {
        "processed_count": processed_count,
        "clean_count": clean_count,
        "partial_count": partial_count,
        "needs_ocr_count": needs_ocr_count,
        "errors_count": len(errors),
        "errors": errors
    }
