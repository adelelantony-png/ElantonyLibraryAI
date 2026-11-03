# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Advanced Arabic OCR & Dual-Text Preservation Engine
Phase 3: Maintains strict separation between ORIGINAL_OCR_TEXT and NORMALIZED_TEXT,
computes per-page OCR Confidence Scores, extracts printed page numbers,
and repairs common Arabic OCR character segmentations without speculative guessing.
"""

import re
import io
from typing import Dict, Any, Tuple, Optional, List
from PIL import Image

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

from elantony.core.text_cleaner import clean_theological_text


class ArabicOcrPostProcessor:
    """
    Advanced Arabic OCR cleaner and dual-text generator.
    Guarantees document integrity by preserving verbatim original output
    while producing a high-accuracy normalized stream for theological indexing.
    """

    # Common OCR character confusions & segmentation patterns
    BROKEN_PATTERNS = [
        (r'\bال\s+([أ-ي])', r'ال\1'),           # Fix segmented "ال " prefix
        (r'(\d+)\s*[-–—]\s*(\d+)', r'\1-\2'),  # Fix page/verse ranges
        (r'([أ-ي])\s*ـ+\s*([أ-ي])', r'\1\2'),   # Remove broken tatweel
        (r'[^\w\s\u0600-\u06FF\.\,\:\(\)\-\"\'«»؟!\d]', ' '), # Strip non-ecclesiastical OCR noise symbols
    ]

    # Regex patterns for detecting printed page numbers in headers and footers
    PRINTED_PAGE_PATTERNS = [
        re.compile(r'(?:^|\n)\s*[-–—(\[]?\s*(\d{1,4})\s*[-–—)\]]?\s*(?:\n|$)', re.MULTILINE),
        re.compile(r'(?:ص|صـ|صفحة)\s*[:.]?\s*(\d{1,4})', re.IGNORECASE),
        re.compile(r'(?:Page|p\.)\s*[:.]?\s*(\d{1,4})', re.IGNORECASE)
    ]

    @classmethod
    def extract_printed_page_number(cls, raw_text: str, default_page: int) -> int:
        """
        Extracts the authentic printed book page number from header/footer text.
        Falls back to physical PDF page index if no printed number is found.
        """
        if not raw_text:
            return default_page

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return default_page

        # Check top 2 lines (headers) and bottom 2 lines (footers)
        candidate_lines = lines[:2] + lines[-2:]
        for line in candidate_lines:
            for pat in cls.PRINTED_PAGE_PATTERNS:
                m = pat.search(line)
                if m:
                    try:
                        p_val = int(m.group(1))
                        # Plausible book page range (1 to 2500)
                        if 1 <= p_val <= 2500:
                            return p_val
                    except (ValueError, TypeError):
                        pass

        return default_page

    @classmethod
    def compute_ocr_confidence_score(cls, raw_text: str, tesseract_conf_mean: Optional[float] = None) -> float:
        """
        Calculates a holistic OCR quality confidence score between 0.0 and 1.0.
        Balances Tesseract word confidence with Arabic vocabulary coherence ratio.
        """
        if not raw_text or len(raw_text.strip()) < 10:
            return 0.1

        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', raw_text))
        total_chars = max(1, len(raw_text.strip()))
        arabic_ratio = arabic_chars / total_chars

        # Check for garbled garbage (high density of isolated single-letter tokens)
        words = raw_text.split()
        if not words:
            return 0.1

        single_letter_tokens = sum(1 for w in words if len(w) == 1 and w not in {'و', 'ف', 'ب', 'ل'})
        garbage_ratio = single_letter_tokens / len(words)

        # Baseline score from linguistic coherence
        base_score = min(1.0, (arabic_ratio * 0.7) + (max(0.0, 1.0 - garbage_ratio) * 0.3))

        if tesseract_conf_mean is not None and tesseract_conf_mean > 0:
            # Blend Tesseract engine confidence with linguistic check
            return round((base_score * 0.4) + ((tesseract_conf_mean / 100.0) * 0.6), 2)

        return round(base_score, 2)

    @classmethod
    def process_dual_stream(
        cls,
        raw_ocr_text: str,
        physical_page_num: int,
        tesseract_conf: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generates the dual-representation:
        1. ORIGINAL_OCR_TEXT: Verbatim raw text (never modified).
        2. NORMALIZED_TEXT: High-readability theological text for FTS and AI.
        3. Confidence metrics and printed page identification.
        """
        original_verbatim = raw_ocr_text.strip()
        confidence = cls.compute_ocr_confidence_score(original_verbatim, tesseract_conf)
        printed_page = cls.extract_printed_page_number(original_verbatim, physical_page_num)

        # Conservative, non-speculative normalization
        normalized = original_verbatim
        for pattern, replacement in cls.BROKEN_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized)

        # Apply ecclesiastical normalizer
        cleaned_normalized = clean_theological_text(normalized)

        is_low_confidence = confidence < 0.60

        return {
            "original_ocr_text": original_verbatim,
            "normalized_text": cleaned_normalized,
            "physical_page": physical_page_num,
            "printed_page": printed_page,
            "ocr_confidence": confidence,
            "is_low_confidence": is_low_confidence,
            "page_has_content": len(cleaned_normalized) > 20
        }
