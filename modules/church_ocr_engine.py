# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Selective Multi-Language OCR Engine
Handles environment diagnostics, image preprocessing, selective page-level OCR,
RAM optimization (< 600 MB limit), and text merging for Coptic/Arabic church volumes.
"""

import os
import gc
import re
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
import pytesseract

from modules import church_ai_config, book_discovery, digital_extractor

BASE_DIR = Path(__file__).resolve().parent.parent

# Common Windows Tesseract paths (including portable bundle)
CANDIDATE_TESSERACT_PATHS = [
    r"G:\Program Files\Tesseract-OCR\tesseract.exe",
    str(BASE_DIR / "tesseract" / "bin" / "tesseract.exe"),
    str(BASE_DIR / "tesseract" / "tesseract.exe"),
    r"D:\Prog\ArchiveMasterFinal\tesseract\bin\tesseract.exe",
    r"I:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster\tesseract\bin\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
]


def find_tesseract_binary(custom_path: Optional[str] = None) -> Optional[str]:
    """Finds tesseract.exe executable on the system."""
    if custom_path and os.path.exists(custom_path) and os.path.isfile(custom_path):
        return custom_path

    # Check PATH
    which_path = shutil.which("tesseract")
    if which_path and os.path.exists(which_path):
        return which_path

    # Check common Windows install paths
    for p in CANDIDATE_TESSERACT_PATHS:
        if os.path.exists(p):
            return p

    return None


def check_ocr_environment(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Diagnoses Tesseract OCR installation, version, available language packs (ara, eng, cop),
    and returns installation commands for Windows 11 if missing.
    """
    cfg = config or church_ai_config.load_config()
    custom_path = cfg.get("ocr", {}).get("tesseract_cmd", "")
    tess_bin = find_tesseract_binary(custom_path)

    if not tess_bin:
        return {
            "is_available": False,
            "tesseract_path": None,
            "version": None,
            "available_languages": [],
            "missing_languages": ["ara", "eng"],
            "install_guide": {
                "winget_command": "winget install UB-Mannheim.TesseractOCR --silent --accept-source-agreements --accept-package-agreements",
                "manual_url": "https://github.com/UB-Mannheim/tesseract/wiki",
                "arabic_tessdata_url": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/ara.traineddata",
                "instructions_ar": "يرجى تثبيت Tesseract OCR باستخدام الأمر أعلاه في PowerShell ثم تنزيل ملف اللغة العربية ara.traineddata داخل مجلد tessdata."
            }
        }

    # Test running tesseract
    version = "unknown"
    languages: List[str] = []
    try:
        ver_proc = subprocess.run([tess_bin, "--version"], capture_output=True, text=True, timeout=5)
        if ver_proc.returncode == 0:
            first_line = ver_proc.stdout.splitlines()[0] if ver_proc.stdout else ""
            version = first_line.strip()

        langs_proc = subprocess.run([tess_bin, "--list-langs"], capture_output=True, text=True, timeout=5)
        if langs_proc.returncode == 0:
            raw_langs = langs_proc.stdout.splitlines()
            # First line is usually "List of available languages (X):"
            languages = [line.strip() for line in raw_langs if line.strip() and not line.startswith("List of")]
    except Exception:
        pass

    pytesseract.pytesseract.tesseract_cmd = tess_bin

    missing = []
    if "ara" not in languages:
        missing.append("ara")
    if "eng" not in languages:
        missing.append("eng")

    return {
        "is_available": True,
        "tesseract_path": tess_bin,
        "version": version,
        "available_languages": languages,
        "missing_languages": missing,
        "has_arabic": "ara" in languages,
        "has_english": "eng" in languages,
        "install_guide": {
            "winget_command": "winget install UB-Mannheim.TesseractOCR",
            "instructions_ar": "الأداة مثبتة بنجاح." if not missing else f"الأداة مثبتة لكن اللغات التالية ناقصة: {', '.join(missing)}."
        }
    }


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Optimized image preprocessing pipeline using OpenCV:
    Grayscale conversion, noise filtering, and Otsu binarization.
    """
    open_cv_image = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    denoised = cv2.medianBlur(gray, 3)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    del open_cv_image, gray, denoised
    return Image.fromarray(thresh)


def ocr_single_page(
    doc: fitz.Document,
    page_num: int,
    dpi: int = 150,
    lang: str = "ara+eng",
    preprocess: bool = True
) -> Dict[str, Any]:
    """
    Performs memory-safe OCR on a single page of an open PDF document.
    Forces garbage collection to keep RAM usage well below 600 MB.
    """
    if page_num < 1 or page_num > len(doc):
        return {"page_num": page_num, "text": "", "confidence": 0.0, "error": "Invalid page number"}

    pix = None
    img = None
    processed_img = None
    try:
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if preprocess:
            processed_img = preprocess_image_for_ocr(img)
            ocr_target = processed_img
        else:
            ocr_target = img

        text = pytesseract.image_to_string(ocr_target, lang=lang)

        # Estimate average confidence score
        try:
            data = pytesseract.image_to_data(ocr_target, lang=lang, output_type=pytesseract.Output.DICT)
            confs = [int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) >= 0]
            avg_conf = float(sum(confs) / max(len(confs), 1))
        except Exception:
            avg_conf = 75.0 if text.strip() else 0.0

        return {
            "page_num": page_num,
            "text": text.strip(),
            "confidence": round(avg_conf, 2),
            "error": None
        }

    except Exception as e:
        return {
            "page_num": page_num,
            "text": "",
            "confidence": 0.0,
            "error": str(e)
        }
    finally:
        # Strict memory cleanup for 8 GB Windows systems
        del pix
        del img
        del processed_img
        gc.collect()


def ocr_book_selective(
    pdf_path: str,
    sha256: str,
    pages_to_ocr: List[int],
    config: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Selectively executes OCR ONLY on pages requiring it.
    Merges OCR results into existing extracted text file and updates SQLite database.
    """
    cfg = config or church_ai_config.load_config()
    target_db = db_path or book_discovery.get_db_path()

    env_diag = check_ocr_environment(cfg)
    if not env_diag["is_available"]:
        return {
            "success": False,
            "error": "Tesseract OCR is not installed or available on the system.",
            "diagnostic": env_diag
        }

    lang = cfg.get("ocr", {}).get("default_languages", "ara+eng")
    dpi = cfg.get("ocr", {}).get("dpi", 150)
    preprocess = cfg.get("ocr", {}).get("preprocess_images", True)

    extracted_dir = Path(cfg["paths"]["extracted_text"])
    text_file = extracted_dir / f"{sha256}.txt"

    if not text_file.exists():
        # If digital extraction wasn't run yet, run it first
        dig_res = digital_extractor.extract_digital_book(pdf_path, sha256=sha256, config=cfg)
        pages_to_ocr = dig_res.get("pages_needing_ocr", [])

    if not pages_to_ocr:
        return {
            "success": True,
            "message": "No pages require OCR for this book.",
            "pages_processed": [],
            "sha256": sha256
        }

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to open PDF for OCR: {str(e)}",
            "sha256": sha256
        }

    ocr_results: Dict[int, Dict[str, Any]] = {}
    completed_pages: List[int] = []

    try:
        for pnum in pages_to_ocr:
            res = ocr_single_page(doc, pnum, dpi=dpi, lang=lang, preprocess=preprocess)
            ocr_results[pnum] = res
            if not res.get("error"):
                completed_pages.append(pnum)
    finally:
        doc.close()
        gc.collect()

    # Now merge OCR text into extracted_text/{sha256}.txt
    if text_file.exists():
        with open(text_file, "r", encoding="utf-8") as f:
            full_content = f.read()

        for pnum, ores in ocr_results.items():
            ocr_text = ores.get("text", "")
            marker = f"--- [صفحة {pnum} / Page {pnum}] ---"
            if marker in full_content and ocr_text:
                # Replace placeholder or append under page marker
                pattern = re.escape(marker) + r"[\r\n]+(\[صفحة تحتاج إلى استخراج ضوئي OCR أو صفحة فارغة\])?"
                replacement = f"{marker}\n{ocr_text}\n"
                full_content = re.sub(pattern, replacement, full_content, count=1)

        with open(text_file, "w", encoding="utf-8") as f:
            f.write(full_content)

    # Update database record
    remaining_pages = [p for p in pages_to_ocr if p not in completed_pages]
    new_status = "completed" if len(remaining_pages) == 0 else "partial"

    conn = sqlite3.connect(target_db)
    cur = conn.cursor()
    cur.execute("""
        UPDATE church_books
        SET pages_needing_ocr = ?,
            extraction_status = ?,
            last_processed_at = CURRENT_TIMESTAMP
        WHERE sha256 = ?
    """, (json.dumps(remaining_pages), new_status, sha256))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "sha256": sha256,
        "completed_pages": completed_pages,
        "remaining_pages": remaining_pages,
        "status": new_status,
        "results": ocr_results
    }
