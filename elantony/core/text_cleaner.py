# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Advanced Arabic Theological Text Cleaner & Restorer
Normalizes OCR artifacts, restores archaic non-standard font glyph shifts,
reconstructs broken ligatures, strips corrupt characters, realigns BiDi numbers,
and eliminates watermark/Tashkeel garbage.
"""

import re
from typing import Dict, List, Optional

# Archaic non-standard Arabic font shifts (from old Coptic/Arabic Word/PDF converters)
# In these fonts, 'لا' (Lam-Alef) was encoded at 'بل', 'و' encoded as 'ك', 'ن' as 'ف', 'ل' as 'م', etc.
ARCHAIC_FONT_WORD_MAP: Dict[str, str] = {
    # Lam-Alef shifts ('بل' -> 'لا')
    "ثبلثة": "ثلاثة",
    "ثبلث": "ثلاث",
    "ثبلثين": "ثلاثين",
    "ثبلثمائة": "ثلاثمائة",
    "كبل": "كلا",
    "إسبلم": "إسلام",
    "سبلم": "سلام",
    "كبلم": "كلام",
    "كبلمه": "كلامه",
    "ببلد": "بلاد",
    "ببلده": "بلاده",
    "تبلوة": "تلاوة",
    "صبلة": "صلاة",
    "صلبة": "صلاة",
    "أصلب": "أصلا",
    "كنبلحظ": "ونلاحظ",
    "نبلحظ": "نلاحظ",
    "يبلحظ": "يلاحظ",

    # Common shifted prepositions and verbs at word boundaries
    "كليس": "وليس",
    "كقد": "وقد",
    "ككان": "وكان",
    "كقال": "وقال",
    "ككانت": "وكانت",
    "كإف": "وإن",
    "كأف": "وأن",

    # OCR substitutions for divinity, theological terms, and ecclesiastical language
    "األمكات": "الأموات",
    "االمكات": "الأموات",
    "مكت الخطية": "موت الخطية",
    "مكت": "موت",
    "اإلليى": "الإلهي",
    "عممو": "عمله",
    "حمقيا": "حلقها",
    "فيي": "فهي",
    "فرحيا": "فرحها",
    "سقؼ": "سقف",
    "العمؽ": "العمق",
    "بالشفتيف": "بالشفتين",
    "القمب": "القلب",
    "عَمَى": "على",
    "عمى": "على",
    "إلى": "إلى",
    "النَّلائِمِين": "النائمين",
    "السَّلائِغَةُ": "السائغة",
    "المقنس": "المقدس",
    "املقدس": "المقدس",
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
    "اهلل": "الله",
    "للا": "الله",
    "وآالخالق": "والخالق",
    "الكليسة": "الكنيسة",
    "مخلضنا": "مخلصنا",

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
    "األموات": "الأموات",

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
    r'(?:https?://\S+|www\.[a-zA-Z0-9.\-_/]+|difa3iat\.com|st-takla\.org|coptic-books\.blogspot\.com|christian-lib\.com|coptic-treasures|ch-joy\.com)',
    re.IGNORECASE
)

# Private use unicode characters, wingdings and decorative bullets
GLYPH_NOISE_PATTERN = re.compile(r'[\uf000-\uf8ff\u200b-\u200f\u00ad\ufeff\ufffd]')
BULLET_PATTERN = re.compile(r'^[►◄▼▲■□●○★☆♦•\-\*]+\s*')

# Tashkeel salad detector: detect garbled text like "اَآىَا رَّمَمَف ا اَيَ لَاؿَقَا"
TASHKEEL_SALAD_PATTERN = re.compile(r'[\u064B-\u065F\u0670]{2,}')


def fix_archaic_font_shifts(text: str) -> str:
    """Corrects non-standard archaic Arabic PDF font substitutions and non-standard unicodes."""
    # 1. Replace isolated archaic Unicode non-standard characters
    t = text.replace('ؿ', 'ل').replace('ؽ', 'ق').replace('ؼ', 'ف')

    # 2. Word-boundary regex substitutions for shifted letters
    # e.g. "قاـ" at end of word -> "قام", "تـ" -> "تم", "معمـ" -> "معلم"
    t = re.sub(r'(\b[\u0600-\u06FF]+)ـ\b', r'\1م', t)
    # "مف" -> "من", "عف" -> "عن", "إف" -> "إن", "أف" -> "أن", "كاف" -> "كان"
    t = re.sub(r'\bمف\b', 'من', t)
    t = re.sub(r'\bعف\b', 'عن', t)
    t = re.sub(r'\bإف\b', 'إن', t)
    t = re.sub(r'\bأف\b', 'أن', t)
    t = re.sub(r'\bكاف\b', 'كان', t)
    # "بعمؿ" or "بعمل"
    t = re.sub(r'\bبعم[ؿل]\b', 'بعمل', t)

    # 3. Direct dictionary substitutions
    for old, new in ARCHAIC_FONT_WORD_MAP.items():
        if old in t:
            t = t.replace(old, new)

    return t


def clean_theological_text(text: str) -> str:
    """
    Cleans raw chunk text:
    1. Removes wingdings, private use characters, and non-printable bytes.
    2. Filters out watermark URLs and repetitive metadata.
    3. Restores archaic Arabic font shifts and broken OCR ligatures.
    4. Realigns numbers and percentages for proper RTL rendering.
    5. Filters garbled Tashkeel noise lines.
    6. Normalizes whitespace and formats as coherent readable Arabic prose.
    """
    if not text:
        return ""

    # 1. Strip raw binary / non-printable / private unicode glyphs
    t = GLYPH_NOISE_PATTERN.sub(' ', text)

    # 2. Strip watermark URLs and site signatures
    t = WATERMARK_PATTERN.sub('', t)

    # 3. Fix archaic font substitutions and ligatures
    t = fix_archaic_font_shifts(t)

    # 4. Normalize hyphenated and line-broken words
    t = re.sub(r'(\b[\u0600-\u06FF]+)\s*-\s*\n\s*([\u0600-\u06FF]+\b)', r'\1\2', t)
    t = re.sub(r'(\b[\u0600-\u06FF]+)\s*\n\s*([\u0600-\u06FF]+\b)', r'\1 \2', t)

    # 5. Fix percentage and number alignment
    t = re.sub(r'(\d{1,3})\s*%\s*', r'\1% ', t)

    # 6. Clean line by line
    raw_lines = t.split('\n')
    cleaned_lines: List[str] = []

    for line in raw_lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Check if line is garbled Tashkeel noise (e.g. "اَآىَا رَّمَمَف ا اَيَ لَاؿَقَا")
        tashkeel_count = len(re.findall(r'[\u064B-\u065F\u0670]', line_str))
        letter_count = len(re.findall(r'[\u0621-\u064A]', line_str))
        if letter_count > 0 and (tashkeel_count / letter_count) > 0.8 and letter_count < 30:
            continue

        # Check if line was an isolated bullet/number/separator
        line_str = BULLET_PATTERN.sub('', line_str).strip()
        if not line_str or line_str in ['%', '-', '•', '.', '..', '...', ':', '::']:
            continue

        # Skip watermark remnant lines
        if any(w in line_str.lower() for w in ['blogspot', 'christian-lib', 'difa3iat', 'st-takla']):
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

    # 8. Strip standalone 1-4 letter Latin OCR fragments that contaminate Arabic books (e.g. Ges, dig, Und, oe, etc.)
    arabic_char_count = len(re.findall(r'[؀-ۿ]', result))
    if arabic_char_count > 40:
        result = re.sub(r'(?<![a-zA-Z])[a-zA-Z]{1,4}(?![a-zA-Z])', ' ', result)
        result = re.sub(r'[»«‹›]', ' ', result)
        result = re.sub(r'\?\s*\.', ' ', result)
        result = re.sub(r'\s+', ' ', result).strip()

    return result


def extract_coherent_sentences(text: str, max_length: int = 350) -> str:
    """Extracts a self-contained, grammatically clean excerpt from text without cutting mid-word."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text.strip()

    truncated = text[:max_length]
    last_stop = max(truncated.rfind('.'), truncated.rfind('،'), truncated.rfind('؛'))
    if last_stop > int(max_length * 0.6):
        return truncated[:last_stop + 1].strip()

    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].strip() + "..."
    return truncated + "..."


# Core theological and biblical vocabulary for verifying citation substance
THEOLOGICAL_SUBSTANTIVE_KEYWORDS = {
    # Doctrine & Trinity
    "لاهوت", "عقيدة", "إيمان", "جوهر", "طبيعة", "أقنوم", "أقانيم", "ثالوث", "الآب", "الابن", "الروح القدس",
    "مساو", "مساوٍ", "مساويا", "سرمدي", "أزلي", "مولود", "منبثق", "واحد",
    # Christology & Salvation
    "تجسد", "تأنس", "فداء", "خلاص", "صليب", "قيامة", "كفارة", "موت", "حياة", "مخلص", "فادي", "يسوع", "المسيح",
    "تجديد", "فساد", "غلبة", "نعمة", "بر", "قداسة",
    # Scripture & Canon
    "كتاب", "مقدس", "إنجيل", "رسالة", "أصحاح", "آية", "سفر", "أسفار", "قانونية", "توراة", "مزامير", "نبوءة", "نبي",
    "طوبيا", "يهوديت", "حكمة", "سيراخ", "باروخ", "مكابيين", "تتمة",
    # Church & Sacraments
    "كنيسة", "أسرار", "معمودية", "إفخارستيا", "ميرون", "توبة", "اعتراف", "كهنوت", "قداس", "صلوات", "ليتورجية",
    # Patristic & Councils
    "آباء", "مجمع", "نيقية", "أفسس", "قسطنطينية", "أرثوذكسية", "تقليد", "رسولي", "تعليم", "عظة", "تفسير"
}


def is_theologically_substantive(text: str) -> bool:
    """Verifies that a chunk discusses real theological, biblical, or ecclesiastical doctrine
    rather than purely administrative anecdotes, travel stories, or editorial boilerplate."""
    if not text or len(text.strip()) < 80:
        return False
    lower_t = text.lower()
    matches = sum(1 for kw in THEOLOGICAL_SUBSTANTIVE_KEYWORDS if kw in lower_t)
    return matches >= 2


def clean_leading_ocr_noise(text: str) -> str:
    """Detects and removes leading OCR scanning garbage, footnote markers, and broken punct."""
    if not text:
        return ""

    # 1. Strip directionality and invisible unicode noise
    t = re.sub(r'[\u200E\u200F\u200B-\u200D\u202A-\u202E\uFEFF\uFFFD]', '', text)

    # 2. Strip footnote bracket numbers like (1), [2], {3}
    t = re.sub(r'[\(\[\{][0-9]{1,3}[\)\]\}]', ' ', t)

    # 3. Fix punctuation and symbols stuck INSIDE Arabic words (e.g. نفس!ر -> نفسر)
    t = re.sub(r'([\u0621-\u064A])[\!\u061F\?\#\$\%\^\&\*\_\-]+([\u0621-\u064A])', r'\1\2', t)

    # 4. Strip standalone 1-6 letter Latin OCR fragments (e.g. dlg, Und, Ges, oe)
    t = re.sub(r'(?<![a-zA-Z])[a-zA-Z]{1,6}(?![a-zA-Z])', ' ', t)

    # 5. Strip guillemets and stray quote noise
    t = re.sub(r'[\u00AB\u00BB\u2039\u203A\[\]\<\>\{\}]', ' ', t)

    # 6. Fix repetitive adjacent words (e.g. الله الله -> الله)
    t = re.sub(r'(?<![\u0621-\u064A])([\u0621-\u064A]{2,})\s+\1(?![\u0621-\u064A])', r'\1', t)

    # 7. Common OCR typos in classical Church texts
    TYPO_CORRECTIONS = {
        "\u0634\u0633\u0639\u0628": "\u0634\u0639\u0628",          # شسعب -> شعب
        "\u0627\u0643\u0627\u0628": "\u0623\u0643\u0627\u0628",          # اكاب -> أكاب
        "\u0627\u0645\u0644\u0642\u062f\u0633": "\u0627\u0644\u0642\u062f\u0633",  # املقدس -> المقدس
        "\u0627\u0645\u0644\u0633\u064a\u062d": "\u0627\u0644\u0645\u0633\u064a\u062d",  # املسيح -> المسيح
        "\u0627\u0647\u0644\u0644": "\u0627\u0644\u0644\u0647",          # اهلل -> الله
        "\u0644\u0644\u0627": "\u0627\u0644\u0644\u0647",                  # للا -> الله
        "\u0627\u0644\u0643\u0644\u064a\u0633\u0629": "\u0627\u0644\u0643\u0646\u064a\u0633\u0629",  # الكليسة -> الكنيسة
        "\u0627\u062d\u0644\u0642\u064a\u0642\u0629": "\u0627\u0644\u062d\u0642\u064a\u0642\u0629",  # احلقيقة -> الحقيقة
        "\u0627\u062d\u0644\u064a\u0627\u0629": "\u0627\u0644\u062d\u064a\u0627\u0629",          # احلياة -> الحياة
    }
    for bad_w, good_w in TYPO_CORRECTIONS.items():
        t = re.sub(r'(?<![\u0621-\u064A])' + bad_w + r'(?![\u0621-\u064A])', good_w, t)

    # 8. Strip lone stray non-Arabic symbols at start of string
    t = re.sub(r'^[\.\,\-\:\;\!\u061F\?\_\*\#\%\^\&\s]+', '', t).strip()

    # 9. Clean excessive spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def clean_citation_excerpt(text: str, max_length: int = 320) -> str:
    """Full-pipeline professional excerpt cleaner for UI citation cards."""
    cleaned = clean_theological_text(text)
    cleaned = clean_leading_ocr_noise(cleaned)
    cleaned = re.sub(r'^[\.\,\-\:\;\!\u061F\s]+', '', cleaned).strip()
    return extract_coherent_sentences(cleaned, max_length=max_length)
