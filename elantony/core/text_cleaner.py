# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Advanced Arabic Theological Text Cleaner & Restorer
Normalizes OCR artifacts, restores broken ligatures, strips corrupt glyphs,
rejoins hyphenated/split words, and fixes RTL BiDi number/percentage inversions.
"""

import re
from typing import Dict, List, Optional

# Common OCR misrecognitions and broken Arabic ligatures in ecclesiastical scans
ARABIC_OCR_CORRECTIONS: Dict[str, str] = {
    # Broken Lam-Alef and Alef variants
    "االنسان": "الإنسان",
    "االنسانية": "الإنسانية",
    "األشرار": "الأشرار",
    "األرض": "الأرض",
    "األباء": "الآباء",
    "اآلباء": "الآباء",
    "اإلله": "الإله",
    "اإلنجيل": "الإنجيل",
    "اإلسكيمو": "الإسكيمو",
    "اإليمان": "الإيمان",
    "األمم": "الأمم",
    "األقانيم": "الأقانيم",
    "األول": "الأول",
    "األولى": "الأولى",
    "األنبياء": "الأنبياء",
    "األحجار": "الأحجار",

    # Soft / broken 'Alif-Lam' OCR ligature artifacts
    "املقدس": "المقدس",
    "المقنس": "المقدس",
    "املسيح": "المسيح",
    "املؤمن": "المؤمن",
    "املؤمنين": "المؤمنين",
    "املالحظ": "الملاحظ",
    "املقطع": "المقطع",
    "املحيط": "المحيط",
    "املطر": "المطر",
    "املعنى": "المعنى",
    "املفهوم": "المفهوم",
    "املراجع": "المراجع",
    "املؤلف": "المؤلف",
    "املجامع": "المجامع",
    "املوت": "الموت",
    "احلياة": "الحياة",
    "احلقيقة": "الحقيقة",
    "احلب": "الحب",
    "الالهية": "الإلهية",

    # Divinity and Christological names
    "اهلل": "الله",
    "للا": "الله",
    "وآالخالق": "والخالق",
    "كالم": "كلام",
    "الكليسة": "الكنيسة",
    "مخلضنا": "مخلصنا",

    # Word wrapping / broken space artifacts from PDF extraction
    "لكُالف": "الفلك",
    "لكالف": "الفلك",
    "الف لك": "الفلك",
    "الف\nلك": "الفلك",
    "أمري كا": "أمريكا",
    "أمري\nكا": "أمريكا",
    "سيبي ريا": "سيبيريا",
    "سيبي\nريا": "سيبيريا",
    "أيس لندا": "أيسلندا",
    "نيو زيلندا": "نيوزيلندا",
    "إسكي مو": "إسكيمو"
}

# Regex patterns for watermarks and URLs
WATERMARK_PATTERN = re.compile(
    r'(?:https?://\S+|www\.[a-zA-Z0-9.\-_/]+|difa3iat\.com|st-takla\.org|coptic-treasures|ch-joy\.com)',
    re.IGNORECASE
)

# Private use unicode characters, wingdings and decorative bullets
GLYPH_NOISE_PATTERN = re.compile(r'[\uf000-\uf8ff\u200b-\u200f\u00ad\ufeff\ufffd]')
BULLET_PATTERN = re.compile(r'^[►◄▼▲■□●○★☆♦•\-\*]+\s*')


def clean_theological_text(text: str) -> str:
    """
    Cleans raw chunk text:
    1. Removes wingdings, private use characters, and non-printable bytes.
    2. Filters out watermark URLs and repetitive metadata.
    3. Restores broken Arabic ligatures and common OCR spelling corruptions.
    4. Realigns numbers and percentages for proper RTL rendering.
    5. Normalizes whitespace and formats as coherent readable text.
    """
    if not text:
        return ""

    # 1. Strip raw binary / non-printable / private unicode glyphs
    t = GLYPH_NOISE_PATTERN.sub(' ', text)

    # 2. Strip watermark URLs
    t = WATERMARK_PATTERN.sub('', t)

    # 3. Apply Arabic OCR word & ligature corrections
    for old, new in ARABIC_OCR_CORRECTIONS.items():
        t = t.replace(old, new)

    # 4. Normalize hyphenated and line-broken words
    t = re.sub(r'(\b[\u0600-\u06FF]+)\s*-\s*\n\s*([\u0600-\u06FF]+\b)', r'\1\2', t)
    t = re.sub(r'(\b[\u0600-\u06FF]+)\s*\n\s*([\u0600-\u06FF]+\b)', r'\1 \2', t)

    # 5. Fix percentage and number alignment (e.g. "95 % اتفقوا" -> "• 95% اتفقوا")
    t = re.sub(r'(\d{1,3})\s*%\s*', r'\1% ', t)

    # 6. Clean line by line
    raw_lines = t.split('\n')
    cleaned_lines: List[str] = []

    for line in raw_lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Check if line was an isolated bullet/number
        line_str = BULLET_PATTERN.sub('', line_str).strip()
        if not line_str or line_str in ['%', '-', '•', '.', '..', '...']:
            continue

        # Remove repetitive single-word lines
        if len(line_str) <= 2 and not line_str.isdigit():
            continue

        # Standardize spacing inside line
        line_str = re.sub(r'\s+', ' ', line_str)
        cleaned_lines.append(line_str)

    if not cleaned_lines:
        return ""

    # 7. Join lines into coherent readable text
    result = " ".join(cleaned_lines)
    result = re.sub(r'\s+', ' ', result).strip()

    # Rejoin common split phrases
    result = result.replace("الف لك", "الفلك").replace("أمري كا", "أمريكا").replace("سيبي ريا", "سيبيريا")

    return result


def extract_coherent_sentences(text: str, max_length: int = 350) -> str:
    """Extracts a self-contained, grammatically clean excerpt from cleaned text."""
    cleaned = clean_theological_text(text)
    if len(cleaned) <= max_length:
        return cleaned

    # Try cutting at sentence boundary (. or ؟ or !)
    truncated = cleaned[:max_length]
    last_stop = max(truncated.rfind('.'), truncated.rfind('،'), truncated.rfind('؛'))
    if last_stop > int(max_length * 0.6):
        return truncated[:last_stop + 1].strip()

    # Otherwise cut at last space
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].strip() + "..."
    return truncated + "..."
