# -*- coding: utf-8 -*-
"""
Tests for ArchiveMaster ChurchAI Selective Multi-Language OCR Engine
"""

import os
import sqlite3
import pytest
import numpy as np
from PIL import Image
from modules import church_ocr_engine, church_ai_config, book_discovery


def test_check_ocr_environment_structure():
    diag = church_ocr_engine.check_ocr_environment()
    assert "is_available" in diag
    assert "available_languages" in diag
    assert "missing_languages" in diag
    assert "install_guide" in diag
    assert "winget_command" in diag["install_guide"]
    assert "UB-Mannheim.TesseractOCR" in diag["install_guide"]["winget_command"]


def test_preprocess_image_for_ocr():
    # Create synthetic noisy grayscale image
    arr = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    # Add dark text-like strokes
    arr[40:60, 20:80] = 10
    img = Image.fromarray(arr)

    processed = church_ocr_engine.preprocess_image_for_ocr(img)
    assert processed is not None
    assert processed.size == (100, 100)
    proc_arr = np.array(processed)
    # Check that it's strictly binarized (values are either 0 or 255)
    unique_vals = set(np.unique(proc_arr))
    assert unique_vals.issubset({0, 255})


def test_ocr_book_selective_graceful_missing_tesseract(tmp_path):
    # Configure with non-existent binary path to test graceful handling
    cfg = church_ai_config.load_config()
    cfg["ocr"]["tesseract_cmd"] = r"C:\fake_non_existent\tesseract.exe"

    res = church_ocr_engine.ocr_book_selective(
        pdf_path="dummy.pdf",
        sha256="abc123fake",
        pages_to_ocr=[1, 2],
        config=cfg
    )

    assert res["success"] is False
    assert "Tesseract OCR is not installed" in res["error"]
    assert "diagnostic" in res
    assert res["diagnostic"]["is_available"] is False
