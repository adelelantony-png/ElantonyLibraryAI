# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Advanced Theological Search Engine
Features:
- Mandatory Topic Anchor Enforcement (Guarantees zero off-topic answers).
- Ecclesiastical Semantic Expansion & Alef/Hamza Normalization.
- Prioritization of Dedicated Thematic Volumes with MATCH validation.
- Clean text restoration via ArabicTextCleaner.
- Heuristic Chunk Quality Filtering (Anti-Spam / Anti-Garbage).
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from elantony.database.connection import get_connection
from elantony.database.models import ChunkEntity
from elantony.core.logging import logger
from elantony.core.text_cleaner import clean_theological_text, extract_coherent_sentences, is_theologically_substantive
import json
from elantony.classifier.source_classifier import ChurchSourceClassifier, SourceType, AuthenticityTier
from elantony.ocr.advanced_ocr import ArabicOcrPostProcessor

ARABIC_STOPWORDS: Set[str] = {
    # Question operators & interrogatives
    "هل", "ما", "ماذا", "لماذا", "كيف", "اين", "أين", "متى", "من", "كم", "اي", "أي",
    "ماهو", "ما_هو", "ماهي", "ما_هي", "ماذا_عن", "بماذا",

    # Comparative & analysis particles (never use as topics)
    "الفرق", "فرق", "فروق", "بين", "مقارنة", "اوجه", "أوجه", "اختلاف", "شبه", "تشابه",
    "معنى", "مفهوم", "تعريف", "شرح", "تفسير", "دليل", "اثبات", "إثبات", "حكم", "رأي",
    "سؤال", "جواب", "اسئلة", "أسئلة", "رد", "شبهات", "شبهة",

    # Pronouns & demonstratives
    "هو", "هي", "هم", "هن", "انت", "أنت", "انا", "أنا", "نحن",
    "هذا", "هذه", "ذلك", "تلك", "اولئك", "أولئك", "الذي", "التي", "الذين", "اللواتي",

    # Auxiliaries & prepositions
    "كان", "كانت", "كانوا", "يكون", "تكون", "في", "الي", "إلى",
    "على", "عن", "مع", "حتى", "ثم", "او", "أو", "ام", "أم", "بل",
    "لا", "لم", "لن", "ليس", "ليست", "ان", "أن", "انما", "إنما",
    "كل", "جميع", "نفس", "بعض", "غير", "سواء",
    "عند", "قبل", "بعد", "فوق", "تحت", "حول", "بشأن", "قال", "قيل",

    # Generic honorifics/prefixes (filter out for book-level dedicated matching)
    "كتاب", "كتب", "رسالة", "مقال", "نبي", "النبي", "سيد", "السيد",
    "قديس", "القديس", "ابونا", "الاب", "الانبا", "الأنبا", "مطران", "اسقف", "أسقف", "بابا", "البابا"
}

# Core Ecclesiastical Theological Thesaurus
THEOLOGICAL_THESAURUS: Dict[str, List[str]] = {
    # أحداث وآلام الصلب والفداء
    "صلب": ["صلب", "الصلب", "المصلوب", "الصليب", "صليب", "الجلجثة", "الجمعة العظيمة", "آلام المسيح", "اسبوع الالام", "موت المسيح"],
    "الصلب": ["الصلب", "صلب", "المصلوب", "الصليب", "صليب", "الجلجثة", "الجمعة العظيمة", "آلام المسيح", "اسبوع الالام", "موت المسيح"],
    "صليب": ["صليب", "الصليب", "صلب", "الصلب", "المصلوب", "فداء", "كفارة", "جلجثة", "ذبيحة"],
    "الصليب": ["الصليب", "صليب", "صلب", "الصلب", "المصلوب", "فداء", "كفارة", "جلجثة", "ذبيحة"],
    
    # الآيات الكونية والظواهر المرافقة للصلب
    "زلزال": ["زلزال", "تزلزلت", "تزلزل", "الزلزال", "انشقاق الصخور", "انشقت الصخور", "تفتحت القبور", "الآيات الكونية"],
    "شمس": ["الشمس", "شمس", "أظلمت", "اظلمت", "ظلمة", "كسوف", "غياب الشمس", "الساعة السادسة", "الساعة التاسعة"],
    "الشمس": ["الشمس", "شمس", "أظلمت", "اظلمت", "ظلمة", "كسوف", "غياب الشمس", "الساعة السادسة", "الساعة التاسعة"],
    "كسوف": ["كسوف", "خسوف", "ظلمة", "أظلمت", "الشمس", "غياب الشمس", "الساعة السادسة", "فليجون", "تعلوس"],
    "ظلمة": ["ظلمة", "الظلمة", "أظلمت", "اظلمت", "الشمس", "كسوف", "غياب الشمس", "الساعة السادسة"],
    "حجاب": ["حجاب", "حجاب الهيكل", "انشقاق الحجاب", "انشق حجاب"],

    # الأسفار القانونية الثانية وقانونية الكتاب المقدس
    "قانونية": ["قانونية", "الأسفار القانونية", "القانونية الثانية", "الاسفار القانونية", "قانونية الأسفار", "طوبيا", "يهوديت", "سيراخ", "المكابيين", "حكمة سليمان", "باروخ"],
    "الاسفار": ["الأسفار", "الاسفار", "الأسفار القانونية", "الأسفار الإلهية"],
    "اسفار": ["الأسفار", "الاسفار", "الأسفار القانونية"],
    "طوبيا": ["طوبيا", "طوبيت", "سفر طوبيا"],
    "يهوديت": ["يهوديت", "سفر يهوديت"],
    "سيراخ": ["سيراخ", "يشوع بن سيراخ", "ابن سيراخ", "حكمة سيراخ"],
    "المكابيين": ["المكابيين", "المكابيين الأول", "المكابيين الثاني", "مكابيين"],
    "حكمة": ["حكمة سليمان", "سفر الحكمة"],
    "باروخ": ["باروخ", "سفر باروخ"],

    # التجسد الإلهي والتأنس
    "تجسد": ["تجسد", "التجسد", "تأنس", "التأنس", "الكلمة", "تجسد الكلمة", "صار جسدا", "ἐνανθρώπησις", "enanthropesis", "ⲁϥϭⲓⲥⲁⲣⲝ"],
    "التجسد": ["التجسد", "تجسد", "تأنس", "التأنس", "الكلمة", "تجسد الكلمة", "صار جسدا", "ἐνανθρώπησις", "ⲁϥϭⲓⲥⲁⲣⲝ"],
    "تأله": ["تأله", "التأله", "شريك الطبيعة الإلهية", "الاتحاد بالله", "ثيؤسيس", "theosis", "θέωσις", "شبه الله", "نعمة التبني"],
    "ثيؤطوكوس": ["ثيؤطوكوس", "ثيئوطوكوس", "والدة الإله", "Theotokos", "Θεοτόκος", "Ϯⲑⲉⲟⲧⲟⲕⲟⲥ"],
    "جوهر": ["جوهر", "الجوهر", "مساو في الجوهر", "هومواوسيوس", "ὁμοούσιος", "homoousios", "الجوهر الإلهي"],
    "طبيعة": ["طبيعة واحدة", "ميافيزيس", "طبيعة المسيح", "اتحاد طبيعي", "μία φύσις"],

    # الفداء والقيامة
    "فداء": ["فداء", "الفداء", "كفارة", "الكفارة", "خلاص", "الخلاص", "ذبيحة", "دم المسيح", "المصالحة"],
    "الفداء": ["الفداء", "فداء", "كفارة", "خلاص", "ذبيحة", "دم المسيح"],
    "قيامة": ["قيامة", "القيامة", "القبر الفارغ", "باكورة الراقدين", "انتصار على الموت", "قام من بين الاموات", "حياة أبدية", "ἀνάστασις", "anastasis"],
    "القيامة": ["القيامة", "قيامة", "القبر الفارغ", "باكورة الراقدين", "انتصار على الموت", "قام من بين الاموات", "ἀνάστασις", "anastasis"],

    # الثالوث القدوس واللاهوت النظري
    "ثالوث": ["ثالوث", "الثالوث", "أقانيم", "الأقانيم", "الآب والابن", "الروح القدس", "جوهر واحد", "طبيعة واحدة", "هومواوسيوس", "ὁμοούσιος"],
    "الثالوث": ["الثالوث", "ثالوث", "أقانيم", "الأقانيم", "الآب والابن", "الروح القدس", "جوهر واحد", "طبيعة واحدة", "هومواوسيوس", "ὁμοούσιος"],
    "روح": ["الروح القدس", "المعزي", "روح الحق", "مواهب الروح", "ثمار الروح", "ⲡⲓⲡⲛⲉⲩⲙⲁ"],

    # الأسرار الكنسية والعبادة
    "معمودية": ["معمودية", "المعمودية", "الغطاس", "ميلاد ثان", "الجرن", "التغطيس", "جرن المعمودية", "ⲡⲓⲱⲙⲥ", "βάπτισμα"],
    "افخارستيا": ["افخارستيا", "الإفخارستيا", "القربان", "التناول", "جسد ودم", "عشاء الرب", "سر الشكر", "εὐχαριστία", "eucharistia"],
    "تناول": ["تناول", "التناول", "افخارستيا", "القربان", "جسد ودم المسيح", "سر الشكر"],
    "توبة": ["توبة", "اعتراف", "نقاوة القلب", "رجوع", "دموع التوبة", "أب الاعتراف"],
    "صلاة": ["صلاة", "سهر", "هدوء", "صلاة يسوع", "مزامير", "صلاة باكر", "الأجبية", "صلاة دائمة"],
    "صوم": ["صوم", "نسك", "انقطاع", "إماتة الجسد", "الصوم الكبير", "طهارة"],

    # قصص كتابية وتاريخية
    "طوفان": ["طوفان", "الطوفان", "نوح", "الفلك", "فلك نوح", "سفر التكوين", "مياه الطوفان"],
    "نوح": ["طوفان", "الطوفان", "نوح", "الفلك", "فلك نوح", "سفر التكوين"],
    "إقامة": ["إقامة", "اقامة", "أقام", "اقام", "يقيم", "الموتى", "الموتي", "الأموات", "الاموات", "لعازر"],
    "اقامة": ["إقامة", "اقامة", "أقام", "اقام", "يقيم", "الموتى", "الموتي", "الأموات", "الاموات", "لعازر"],
    "أموات": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "اموات": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "موتى": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "موتي": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "إيليا": ["إيليا", "ايليا", "إيليا النبي", "ايليا النبي", "ابن الأرملة", "ابن الارملة"],
    "ايليا": ["إيليا", "ايليا", "إيليا النبي", "ايليا النبي", "ابن الأرملة", "ابن الارملة"],
    "لعازر": ["لعازر", "إقامة لعازر", "اقامة لعازر", "مريض بيت عنيا"],
    "يايرس": ["يايرس", "ابنة يايرس", "صبية قومي", "طليثا قومي"],
    "نايين": ["نايين", "ابن أرملة نايين", "ابن ارملة نايين"]
}


def normalize_alef_variants(word: str) -> List[str]:
    """Generates all common Alef/Hamza and Yeh/Teh-Marbuta variations for FTS matching."""
    variants = {word}
    w_bare = re.sub(r'[أإآ]', 'ا', word)
    variants.add(w_bare)
    if word.startswith(('ا', 'أ', 'إ', 'آ')):
        tail = word[1:]
        for prefix in ('ا', 'أ', 'إ', 'آ'):
            variants.add(prefix + tail)
    if word.endswith('ي'):
        variants.add(word[:-1] + 'ى')
    elif word.endswith('ى'):
        variants.add(word[:-1] + 'ي')
    if word.endswith('ة'):
        variants.add(word[:-1] + 'ه')
    elif word.endswith('ه'):
        variants.add(word[:-1] + 'ة')
    return list(variants)


CONVERSATIONAL_BOILERPLATE = {
    "مفهوم", "الفكر", "فكر", "الآبائي", "الابائي", "اقوال", "أقوال", "الموضوع", 
    "موضوع", "المراجع", "مراجع", "أرقام", "ارقام", "الصفحات", "صفحات", "اذكر", 
    "شرح", "تفسير", "رسولي", "الرسولي", "قديس", "القديس", "انبا", "الأنبا", "بابا", "البابا",
    "حول", "هذا", "هذه", "ذلك", "تلك", "أهم", "اهم", "وما", "ما", "هو", "هي", "عن",
    "هل", "كيف", "ماذا", "لماذا", "اين", "أين", "متى", "كم", "من", "في", "على", "إلى", "الي", "مع",
    "هكذا", "وهكذا", "مثل", "كذلك", "اثبت", "يثبت", "اثبات", "أثبت", "تطابق", "يطابق", "مطابقة",
    "الحدث", "حدث", "احداث", "أحداث", "العلم", "العلمي", "علميا", "علم", "حقيقة", "امر", "أمر",
    "شأن", "نوع", "وجود", "بين", "ايضا", "أيضا", "اريد", "أريد", "ابحث", "أبحث", "اعطني", "أعطني",
    "توضيح", "بيان", "رأي", "راي", "موقف", "نظرة", "بخصوص", "بشأن", "تعمق", "استخدام",
    "عمود", "الدين", "عمود الدين", "الذهبي", "اللاهوتي", "الكبير", "المتوشح بالله",
    "اريدك", "أريدك", "ببحث", "بحث", "اكاديمي", "أكاديمي", "تثبت", "إثبات", "لي", "اتفاق", "القرون", "قرون",
    "الاولي", "الأولى", "الثالثة", "الرابعة", "عليها", "فيها", "منها", "لها",
    "صلواتها", "صلوات", "واثبتها", "واثبت", "نفسه", "بصراحة", "جرب", "شف", "شوف", "حتحزن",
    "ناقصة", "دائما", "بشكل", "ملحوظ", "جدا", "عايز", "اعرف", "وضح", "اشرح", "فهمني"
}


def extract_search_keywords(raw_query: str) -> List[str]:
    """Cleans query, strips punctuation and removes conversational stopwords and query directives."""
    clean = re.sub(r'[^\w\s]', ' ', raw_query).strip()
    tokens = [w.strip() for w in clean.split() if len(w.strip()) > 1]
    
        # Strip coordinating conjunction 'و' from names and topics (e.g. وكيرلس -> كيرلس, واثناسيوس -> اثناسيوس)
    KNOWN_W_WORDS = {"واحد", "وقفة", "وجود", "وقت", "وحيد", "وثيقة", "وصية", "ولادة", "وادي", "وعد", "وفاة", "وجوب", "وجوه", "وصايا"}
    normalized_tokens = []
    for w in tokens:
        if w.startswith("و") and len(w) >= 4 and w not in KNOWN_W_WORDS:
            stem = w[1:]
            normalized_tokens.append(stem)
            continue
        normalized_tokens.append(w)

    keywords = [w for w in normalized_tokens if w not in ARABIC_STOPWORDS and w not in CONVERSATIONAL_BOILERPLATE]
    return keywords if keywords else [w for w in normalized_tokens if w not in ARABIC_STOPWORDS]


def expand_theological_synonyms(keywords: List[str]) -> Tuple[List[str], List[str]]:
    """
    Expands query keywords into:
    - Primary Topic Anchors: Deterministic, ordered core subject matter (must match at least one in every chunk).
    - Secondary Qualifiers: Refines specific aspect (e.g. cosmic signs, history, arguments).
    """
    PRIMARY_ANCHOR_ROOTS = [
        "قانونية", "الاسفار", "اسفار", "طوبيا", "يهوديت", "سيراخ", "المكابيين", "حكمة", "باروخ",
        "صلب", "الصلب", "صليب", "الصليب", "قيامة", "القيامة", "تجسد", "التجسد",
        "تأله", "التأله", "فداء", "الفداء", "ثالوث", "الثالوث", "طوفان", "الطوفان",
        "معمودية", "المعمودية", "افخارستيا", "الإفخارستيا", "تناول", "إقامة", "اقامة",
        "أموات", "موتى", "لعازر", "يايرس", "نايين", "نوح", "إيليا"
    ]

    anchors_ordered: List[str] = []
    qualifiers_ordered: List[str] = []
    seen_anchors: Set[str] = set()
    seen_quals: Set[str] = set()

    for kw in keywords:
        clean_stem = kw.replace("ال", "", 1) if kw.startswith("ال") and len(kw) > 3 else kw
        matched = False
        for key, syns in THEOLOGICAL_THESAURUS.items():
            if key == kw or key == clean_stem or (len(key) >= 4 and key in kw):
                matched = True
                if key in PRIMARY_ANCHOR_ROOTS:
                    for s in syns:
                        if s not in seen_anchors:
                            seen_anchors.add(s)
                            anchors_ordered.append(s)
                    if kw not in seen_anchors:
                        seen_anchors.add(kw)
                        anchors_ordered.append(kw)
                else:
                    for s in syns:
                        if s not in seen_quals:
                            seen_quals.add(s)
                            qualifiers_ordered.append(s)
                    if kw not in seen_quals:
                        seen_quals.add(kw)
                        qualifiers_ordered.append(kw)
        if not matched:
            if len(kw) >= 3 and kw not in CONVERSATIONAL_BOILERPLATE:
                if any(root in kw for root in PRIMARY_ANCHOR_ROOTS):
                    if kw not in seen_anchors:
                        seen_anchors.add(kw)
                        anchors_ordered.append(kw)
                else:
                    if kw not in seen_quals:
                        seen_quals.add(kw)
                        qualifiers_ordered.append(kw)

    # If canonical topic is requested, ensure anchor is specific to the Deuterocanonical canon
    if any(k in ["قانونية", "القانونية", "قانونيه", "القانونيه"] for k in keywords):
        anchors_ordered = [a for a in anchors_ordered if a not in ["الأسفار", "الاسفار", "الأسفار الإلهية"]]
        if not anchors_ordered or not any("قانون" in a for a in anchors_ordered):
            anchors_ordered = ["قانونية", "الأسفار القانونية", "القانونية الثانية", "طوبيا", "يهوديت", "سيراخ", "المكابيين", "حكمة سليمان", "باروخ"] + anchors_ordered

    # If no primary anchors found, promote qualifiers or keywords
    if not anchors_ordered:
        anchors_ordered = qualifiers_ordered[:6] if qualifiers_ordered else [k for k in keywords if len(k) >= 3][:6]

    return anchors_ordered, qualifiers_ordered


def is_chunk_high_quality(text: str) -> bool:
    """Verifies that a chunk contains meaningful Arabic theological text rather than OCR noise or URLs."""
    if not text or len(text.strip()) < 75:
        return False

    # Kashida / Tatweel spam (corrupted scanned decorative banners)
    if text.count("ـ") > 5 or "ــــ" in text:
        return False

    # Plus sign corruption in text
    if text.count("+") > 2:
        return False

    # Stretched harakat or tashkeel salad
    if re.search(r'[ً-ٰٟـ]{4,}', text):
        return False

    # Stray corrupted OCR symbols
    if any(sym in text for sym in ["©", "¢", "¤", "§"]):
        return False

    # Web links or watermark banners
    if any(dom in text.lower() for dom in ["coptic-treasures.com", "st-takla.org", "coptichistory.org", "http://", "https://"]):
        return False

    # Normal Arabic words check
    words = text.split()
    if not words:
        return False

    # Reversed Arabic detection: No legitimate Arabic word begins with 'ة' or 'اً'
    reversed_words = [w for w in words if w.startswith("ة") or w.startswith("اً")]
    if len(reversed_words) >= 2:
        return False

    # Check for excessive Latin words: only reject if non-Arabic characters dominate (> 15% of words)
    latin_words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    if len(words) > 0 and (len(latin_words) / len(words)) > 0.15:
        return False

    clean_words = [w for w in words if re.fullmatch(r'[ء-ي]{3,}', w)]
    if len(clean_words) / len(words) < 0.50:
        return False

    # Filter out Table of Contents / Index / Bibliography pages
    normalized_peek = text.replace("امل", "الم")
    if any(toc in normalized_peek for toc in [
        "فهرس الموضوعات", "فهرس المحتويات", "قائمة المحتويات", "الصفحة رقم الموضوع", 
        "الصفحة رقم", "قائمة المراجع", "فهرس الآيات", "فهرس الأعلام", "مراجع الكتاب"
    ]):
        return False

    # Filter out Table of Contents pages filled with list of page numbers or dotted leaders
    if len(re.findall(r'\b\d{2,4}\b', text)) > 5:
        return False
    if text.count("....") > 2 or text.count("...") > 5:
        return False

    # Check for excessive URL / watermark spam
    url_matches = len(re.findall(r'www\.|\.com|\.org|http', text, re.IGNORECASE))
    if url_matches > 2:
        return False

    # Check Arabic character ratio
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(text.strip())
    if total_chars > 0 and (arabic_chars / total_chars) < 0.50:
        return False

    return True



# Canonical Biblical Books Mapping for Scriptural Reference Parsing
BIBLE_BOOKS_MAP = {
    # العهد الجديد
    "متى": "متى", "مرقس": "مرقس", "لوقا": "لوقا", "يوحنا": "يوحنا", "اعمال": "أعمال الرسل", "أعمال": "أعمال الرسل",
    "رومية": "رومية", "غلاطية": "غلاطية", "افسس": "أفسس", "أفسس": "أفسس", "فيلبي": "فيلبي",
    "كولوسي": "كولوسي", "عبرانيين": "عبرانيين", "يعقوب": "يعقوب", "بطرس": "بطرس", "يهوذا": "يهوذا",
    "رؤيا": "الرؤيا", "الرؤيا": "الرؤيا", "تسالونيكي": "تسالونيكي", "تيموثاوس": "تيموثاوس", "تيطس": "تيطس", "فليمون": "فليمون",
    # العهد القديم والأسفار القانونية
    "تكوين": "تكوين", "خروج": "خروج", "لاويين": "لاويين", "عدد": "عدد", "تثنية": "تثنية", "يشوع": "يشوع",
    "قضاة": "قضاة", "راعوث": "راعوث", "صموئيل": "صموئيل", "ملوك": "ملوك", "أخبار": "أخبار الأيام",
    "مزامير": "المزامير", "مزمور": "المزامير", "امثال": "الأمثال", "أمثال": "الأمثال", "الجامعة": "الجامعة",
    "نشيد": "نشيد الأنشاد", "اشعياء": "إشعياء", "إشعياء": "إشعياء", "ارميا": "إرمياء", "إرمياء": "إرمياء",
    "حزقيال": "حزقيال", "دانيال": "دانيال", "طوبيا": "طوبيا", "يهوديت": "يهوديت", "المكابيين": "المكابيين", "سيراخ": "سيراخ",
    "حكمة": "حكمة سليمان", "باروخ": "باروخ"
}

NUM_TO_ARABIC = {
    1: "الأول", 2: "الثاني", 3: "الثالث", 4: "الرابع", 5: "الخامس",
    6: "السادس", 7: "السابع", 8: "الثامن", 9: "التاسع", 10: "العاشر",
    11: "الحادي عشر", 12: "الثاني عشر", 13: "الثالث عشر", 14: "الرابع عشر", 15: "الخامس عشر",
    16: "السادس عشر", 17: "السابع عشر", 18: "الثامن عشر", 19: "التاسع عشر", 20: "العشرون",
    21: "الحادي والعشرون", 22: "الثاني والعشرون", 23: "الثالث والعشرون", 24: "الرابع والعشرون", 25: "الخامس والعشرون"
}

def parse_biblical_query(q: str) -> Optional[Dict[str, Any]]:
    """Parses queries mentioning biblical books with optional chapter and verse (e.g. رومية 8: 29 or يوحنا 3)."""
    if not q:
        return None
    for b_key, b_std in BIBLE_BOOKS_MAP.items():
        pattern = rf'\b{b_key}\b(?:\s+(?:إصحاح|اصحاح|الأصحاح|الاصحاح))?\s*(\d{{1,3}})(?:\s*[:\-]\s*(\d{{1,3}}))?'
        m = re.search(pattern, q)
        if m:
            chapter = int(m.group(1))
            verse = int(m.group(2)) if m.group(2) else None
            ch_ar = NUM_TO_ARABIC.get(chapter, "")
            return {
                "matched": True,
                "book": b_std,
                "book_key": b_key,
                "chapter": chapter,
                "chapter_ar": ch_ar,
                "verse": verse
            }
    return None


def decompose_multifacet_query(query: str) -> List[str]:
    """
    Decomposes a compound/multi-faceted theological research question into targeted semantic facets
    to guarantee comprehensive coverage across patristic centuries, liturgical usage, councils, etc.
    """
    q_norm = query.strip()
    if len(q_norm) < 20:
        return []

    facets: List[str] = []
    keywords = extract_search_keywords(q_norm)
    anchors, _ = expand_theological_synonyms(keywords)
    primary_anchor = anchors[0] if anchors else (" ".join(keywords[:2]) if keywords else "")

    if not primary_anchor:
        return []

    # 1. Patristic / Century Dimension
    if any(k in q_norm for k in ["اباء", "آباء", "القرون", "القرن الاول", "القرن الثاني", "القرن الثالث", "القرن الرابع"]):
        facets.append(f"{primary_anchor} آباء أثناسيوس أوريجانوس إكليمنضس")

    # 2. Liturgical / Prayer Dimension
    if any(k in q_norm for k in ["صلوات", "صلواتها", "ليتورجيا", "طقس", "تسبيحة", "أجبية", "خولاجي", "عبادة"]):
        facets.append(f"{primary_anchor} صلوات ليتورجيا الكنيسة اقتباسات")

    # 3. Biblical / Scripture Dimension
    if any(k in q_norm for k in ["الكتاب المقدس", "العهد الجديد", "العهد القديم", "اقتباس", "شواهد", "ايات"]):
        facets.append(f"{primary_anchor} العهد الجديد اقتباسات شواهد")

    # 4. Councils / Canon Dimension
    if any(k in q_norm for k in ["مجمع", "مجامع", "قوانين", "نيقية", "قرطاجنة", "هيبو", "لاودكية", "قانونية"]):
        facets.append(f"{primary_anchor} مجامع الكنيسة نيقية قرطاجنة")

    # 5. Compound clauses with "و" or "مع" if no specific ecclesiastical facet caught above
    if len(facets) < 2 and (" و " in q_norm or " مع " in q_norm):
        sub_clauses = re.split(r"\s+(?:و|مع|كذلك|بالإضافة إلى)\s+", q_norm)
        for sc in sub_clauses:
            sc_clean = sc.strip()
            if len(sc_clean) >= 8:
                facets.append(f"{primary_anchor} {sc_clean}")

    return list(dict.fromkeys(facets))[:4]


class ChurchSearchEngine:
    """High-performance multi-tier search engine with theological thesaurus & dedicated volume priority."""

    def find_dedicated_books(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Finds complete dedicated volumes in the church catalog specifically focusing on the topic.
        If a specific Church Father is mentioned in the query, books by or directly about that Father
        take absolute priority over general modern books.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        GENERIC_TOPIC_WORDS = {"الاباء", "الآباء", "اباء", "آباء", "الكتاب", "كتاب", "الكنيسة", "كنسية"}
        valid_kws = [k for k in keywords if k not in ARABIC_STOPWORDS and k not in CONVERSATIONAL_BOILERPLATE and k not in GENERIC_TOPIC_WORDS and len(k) >= 3]

        # Collect topic keywords and their un-prefixed stems (e.g. التجسد -> تجسد)
        topic_stems = set()
        for kw in valid_kws:
            topic_stems.add(kw)
            if (kw.startswith("ال") or kw.startswith("أل") or kw.startswith("إل")) and len(kw) > 4:
                topic_stems.add(kw[2:])
            elif not kw.startswith("ال") and len(kw) >= 3:
                topic_stems.add("ال" + kw)

        # Check for targeted church fathers
        detected_fathers = []
        for father_name, father_kws in ChurchSourceClassifier.PATRISTIC_FATHERS.items():
            if any(k in query.lower() for k in father_kws):
                detected_fathers.append((father_name, father_kws))

        conn = get_connection()
        cur = conn.cursor()
        found_books: List[Dict[str, Any]] = []
        seen_shas = set()

        # Tier 0 Priority: Dedicated Biblical Commentaries (e.g. شرح رسالة رومية, تفسير إنجيل يوحنا)
        bible_ref = parse_biblical_query(query)
        if bible_ref:
            b_key = bible_ref["book_key"]
            try:
                cur.execute("""
                    SELECT sha256, file_name, author, category, page_count
                    FROM church_books
                    WHERE (file_name LIKE ? OR file_name LIKE ?)
                      AND is_duplicate_of IS NULL
                    ORDER BY page_count DESC
                    LIMIT ?
                """, (f"%تفسير%{b_key}%", f"%شرح%{b_key}%", limit))
                for b in cur.fetchall():
                    if b["sha256"] not in seen_shas:
                        seen_shas.add(b["sha256"])
                        found_books.append({
                            "sha256": b["sha256"],
                            "file_name": b["file_name"],
                            "clean_title": b["file_name"].replace(".pdf", ""),
                            "author": b["author"] or "تفسير آبائي وشرح كنسي",
                            "category": "تفاسير وشروح كتابية",
                            "page_count": b["page_count"] or 1
                        })
            except Exception as e:
                logger.debug(f"Biblical commentary dedicated volume search error: {e}")

        # Tier 1 Priority: Books matching BOTH detected Father AND Topic
        if detected_fathers and topic_stems:
            for father_name, father_kws in detected_fathers:
                for f_kw in father_kws[:3]:
                    for f_v in normalize_alef_variants(f_kw):
                        for topic_kw in topic_stems:
                            for t_v in normalize_alef_variants(topic_kw):
                                cur.execute("""
                                    SELECT sha256, file_name, author, category, page_count
                                    FROM church_books
                                    WHERE (author LIKE ? OR file_name LIKE ?)
                                      AND (file_name LIKE ? OR category LIKE ?)
                                      AND is_duplicate_of IS NULL
                                    ORDER BY (authenticity_tier = 1) DESC, (file_name LIKE ?) DESC, page_count DESC
                                    LIMIT ?
                                """, (f"%{f_v}%", f"%{f_v}%", f"%{t_v}%", f"%{t_v}%", f"%{t_v}%", limit))
                                for b in cur.fetchall():
                                    if b["sha256"] not in seen_shas:
                                        seen_shas.add(b["sha256"])
                                        found_books.append({
                                            "sha256": b["sha256"],
                                            "file_name": b["file_name"],
                                            "clean_title": b["file_name"].replace(".pdf", ""),
                                            "author": b["author"] or father_name,
                                            "category": b["category"] or "كتابات آبائية",
                                            "page_count": b["page_count"] or 0
                                        })
                                        if len(found_books) >= limit:
                                            break
                                if len(found_books) >= limit:
                                    break
                            if len(found_books) >= limit:
                                break
                        if len(found_books) >= limit:
                            break
                    if len(found_books) >= limit:
                        break

        # Tier 2 Priority: General topic matching if limit not reached (excluding generic & Sunday school titles)
        GENERIC_IGNORE_TITLES = {"الكتاب المقدس", "الكتاب", "الله", "المسيح", "الانجيل", "الإنجيل", "رسالة", "رسائل", "إبتدائي", "ابتدائي", "حضانة", "مدارس الأحد", "نشاط وتلوين", "مسابقات"}
        if len(found_books) < limit and topic_stems:
            for kw in topic_stems:
                if kw in GENERIC_IGNORE_TITLES or len(kw) < 3:
                    continue
                variants = normalize_alef_variants(kw)
                for v in variants:
                    cur.execute("""
                        SELECT sha256, file_name, author, category, page_count
                        FROM church_books
                        WHERE (
                            file_name LIKE ? OR
                            file_name LIKE ? OR
                            file_name LIKE ? OR
                            file_name LIKE ?
                        ) AND is_duplicate_of IS NULL
                          AND authenticity_tier <= 4
                        ORDER BY (authenticity_tier = 1) DESC, (authenticity_tier = 2) DESC, page_count DESC
                        LIMIT ?
                    """, (f"% {v} %", f"%_{v}_%", f"% {v}.pdf", f"{v} %", limit))
                    for b in cur.fetchall():
                        if b["sha256"] not in seen_shas:
                            seen_shas.add(b["sha256"])
                            found_books.append({
                                "sha256": b["sha256"],
                                "file_name": b["file_name"],
                                "clean_title": b["file_name"].replace(".pdf", ""),
                                "author": b["author"] or "آباء ومعلمو الكنيسة",
                                "category": b["category"] or "لاهوت وعقيدة",
                                "page_count": b["page_count"] or 0
                            })
                            if len(found_books) >= limit:
                                break
                    if len(found_books) >= limit:
                        break
                if len(found_books) >= limit:
                    break

        conn.close()
        return found_books

    def search_fts5(
        self,
        query: str,
        limit: int = 12,
        filter_source_type: Optional[str] = None
    ) -> List[ChunkEntity]:
        """
        Executes Advanced Hybrid & Source-Aware Retrieval across indexed chunks.
        Supports multi-facet query decomposition to guarantee complete coverage
        of compound research questions across multiple centuries, councils, and liturgical usage.
        """
        # Multi-Facet Decomposition Check (prevent infinite recursion)
        is_subquery = getattr(self, "_in_facet_search", False)
        if not is_subquery:
            facets = decompose_multifacet_query(query)
            if len(facets) >= 2:
                try:
                    self._in_facet_search = True
                    merged_chunks: List[ChunkEntity] = []
                    seen_refs_facet: Set[str] = set()

                    # 1. Search primary query
                    primary_results = self.search_fts5(query, limit=max(4, limit // 2), filter_source_type=filter_source_type)
                    for pc in primary_results:
                        if pc.source_reference not in seen_refs_facet:
                            seen_refs_facet.add(pc.source_reference)
                            merged_chunks.append(pc)

                    # 2. Search each targeted facet
                    per_facet_limit = max(2, (limit - len(merged_chunks)) // len(facets) + 1)
                    for f_q in facets:
                        facet_results = self.search_fts5(f_q, limit=per_facet_limit, filter_source_type=filter_source_type)
                        for fc in facet_results:
                            if fc.source_reference not in seen_refs_facet:
                                seen_refs_facet.add(fc.source_reference)
                                merged_chunks.append(fc)
                            if len(merged_chunks) >= limit:
                                break
                        if len(merged_chunks) >= limit:
                            break

                    if merged_chunks:
                        # Sort by authenticity tier (Tier 1 & 2 first)
                        merged_chunks.sort(key=lambda x: (x.authenticity_tier or 3, -(x.relevance_score or 0)))
                        return merged_chunks[:limit]
                finally:
                    self._in_facet_search = False
        """
        Executes Advanced Hybrid & Source-Aware Retrieval across indexed chunks.
        Applies Patristic Authority Weighting (Tier 1-5), metadata filtering,
        printed page extraction, and strict anti-hallucination topic anchors.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        target_fathers = [f for f, kws in ChurchSourceClassifier.PATRISTIC_FATHERS.items() if any(k in query.lower() for k in kws)]
        anchors, qualifiers = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows: List[Dict[str, Any]] = []
        seen_refs: Set[str] = set()

        # Build expanded terms with Alef/Hamza normalization for FTS
        all_anchor_terms: Set[str] = set()
        for a in anchors[:6]:
            all_anchor_terms.update(normalize_alef_variants(a))

        all_qual_terms: Set[str] = set()
        for q in qualifiers[:6]:
            all_qual_terms.update(normalize_alef_variants(q))

        anchor_clause = " OR ".join([f'"{t}"' for t in list(all_anchor_terms)[:10]])

        # Step 1: If dedicated books exist, search chunks from them WITH KEYWORD MATCH
        dedicated_books = self.find_dedicated_books(query, limit=3)
        bible_ref = parse_biblical_query(query)
        if dedicated_books:
            for book in dedicated_books:
                b_sha = book["sha256"]
                # If biblical query with chapter, build specialized chapter match expression
                if bible_ref and bible_ref.get("chapter"):
                    ch_num = bible_ref["chapter"]
                    ch_ar = bible_ref.get("chapter_ar")
                    ch_terms = [f'"اصحاح {ch_num}"', f'"أصحاح {ch_num}"', f'"{ch_num}:"']
                    if ch_ar:
                        ch_terms.extend([f'"الأصحاح {ch_ar}"', f'"الاصحاح {ch_ar}"'])
                    if bible_ref.get("verse"):
                        ch_terms.append(f'"{bible_ref["verse"]}"')
                    book_fts_expr = f"chunk_text: ({' OR '.join(ch_terms)})"
                elif anchor_clause:
                    book_fts_expr = f"chunk_text: ({anchor_clause})"
                else:
                    continue

                try:
                    cur.execute("""
                        SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                        FROM church_chunks_fts
                        WHERE sha256 = ? AND church_chunks_fts MATCH ? AND page_number > 1
                        ORDER BY rank
                        LIMIT 2
                    """, (b_sha, book_fts_expr))
                    for r in cur.fetchall():
                        ref = r["source_reference"]
                        if ref not in seen_refs and is_chunk_high_quality(r["chunk_text"]) and is_theologically_substantive(r["chunk_text"]):
                            seen_refs.add(ref)
                            rows.append(r)
                            if len(rows) >= limit:
                                break
                except Exception as e:
                    logger.debug(f"Scoped dedicated book chunk query error: {e}")

                # Step 2: Targeted Father + Anchor Intersection (Highest Precision)
        # If specific Church Fathers are detected in query, require them in the FTS boolean expression
        father_terms_for_fts = []
        if target_fathers:
            for tf in target_fathers:
                for fk in ChurchSourceClassifier.PATRISTIC_FATHERS.get(tf, [])[:3]:
                    for fv in normalize_alef_variants(fk):
                        if len(fv) >= 4 and fv not in ["الكبير", "الرسولي", "الذهبي"]:
                            father_terms_for_fts.append(f'"{fv}"')

        if len(rows) < limit and anchor_clause:
            if father_terms_for_fts:
                father_clause = " OR ".join(list(set(father_terms_for_fts))[:6])
                fts_expr = f"chunk_text: (({anchor_clause}) AND ({father_clause}))"
            elif all_qual_terms:
                # Exclude generic words from qualifier clause
                GENERIC_QUALS = {"الاباء", "الآباء", "الثانية", "الاولى", "الأولى", "القرون", "قرون", "الكنسية", "الكنيسة"}
                specific_quals = [q for q in all_qual_terms if q not in GENERIC_QUALS]
                if specific_quals:
                    qual_clause = " OR ".join([f'"{q}"' for q in list(specific_quals)[:6]])
                    fts_expr = f"chunk_text: (({anchor_clause}) AND ({qual_clause}))"
                else:
                    fts_expr = f"chunk_text: ({anchor_clause})"
            else:
                fts_expr = f"chunk_text: ({anchor_clause})" 

            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ? AND page_number > 1
                    ORDER BY rank
                    LIMIT ?
                """, (fts_expr, limit * 4))
                candidate_rows = cur.fetchall()
                for cr in candidate_rows:
                    ref = cr["source_reference"]
                    b_title = cr["book_title"].lower()
                    c_text = cr["chunk_text"]
                    
                    # Anti-Orthogonal Topic Filter:
                    # If query is about Crucifixion/Passion, do NOT accept pure Trinitarian treatises unless they discuss the Cross
                    if any(t in query.lower() for t in ["صلب", "صليب", "الجمعة العظيمة", "الجلجثة"]):
                        if ("الكنوز فى الثالوث" in b_title or "تثليث وتوحيد" in b_title or "الثالوث القدوس" in b_title) and not any(k in c_text for k in ["صلب", "الصليب", "صلبوا", "المصلوب", "الجلجثة", "الآلام"]):
                            continue

                    if ref not in seen_refs and is_chunk_high_quality(c_text) and is_theologically_substantive(c_text):
                        seen_refs.add(ref)
                        rows.append(cr)
                        if len(rows) >= limit:
                            break
            except Exception as e:
                logger.warning(f"FTS5 Anchor Boolean Search error: {e}")

        # Step 3: High-Relevance Fallback (Anchor only - Never naked generic words)
        if len(rows) < limit and anchor_clause:
            scoped_fallback = f"chunk_text: ({anchor_clause})"
            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ? AND page_number > 1
                    ORDER BY rank
                    LIMIT ?
                """, (scoped_fallback, limit * 2))
                candidate_rows = cur.fetchall()
                for cr in candidate_rows:
                    ref = cr["source_reference"]
                    if ref not in seen_refs and is_chunk_high_quality(cr["chunk_text"]) and is_theologically_substantive(cr["chunk_text"]):
                        seen_refs.add(ref)
                        rows.append(cr)
                        if len(rows) >= limit:
                            break
            except Exception as e:
                logger.warning(f"FTS5 Anchor Fallback search error: {e}")

        conn.close()

        # Step 4: Fetch Metadata, Apply Authenticity Weighting & Hierarchy Ranking
        target_fathers = [f for f, kws in ChurchSourceClassifier.PATRISTIC_FATHERS.items() if any(k in query.lower() for k in kws)]
        
        # Batch lookup book metadata
        shas = list({r["sha256"] for r in rows})
        book_meta_map: Dict[str, Dict[str, Any]] = {}
        if shas:
            try:
                conn_meta = get_connection()
                cur_m = conn_meta.cursor()
                placeholders = ",".join(["?" for _ in shas])
                cur_m.execute(f"""
                    SELECT sha256, author, source_types, authenticity_tier, matched_fathers
                    FROM church_books
                    WHERE sha256 IN ({placeholders})
                """, shas)
                for bm in cur_m.fetchall():
                    s_types = []
                    if bm["source_types"]:
                        try:
                            s_types = json.loads(bm["source_types"])
                        except Exception:
                            s_types = [bm["source_types"]]
                    book_meta_map[bm["sha256"]] = {
                        "author": bm["author"] or "آباء ومعلمو الكنيسة",
                        "source_types": s_types,
                        "authenticity_tier": bm["authenticity_tier"] or 3,
                        "matched_fathers": bm["matched_fathers"] or ""
                    }
                conn_meta.close()
            except Exception as meta_err:
                logger.debug(f"Book metadata batch lookup error: {meta_err}")

        # Filter by source type and compute authenticity weight
        candidate_items = []
        for r in rows:
            sha = r["sha256"]
            b_meta = book_meta_map.get(sha, {
                "author": "آباء ومعلمو الكنيسة",
                "source_types": ["THEOLOGICAL_STUDIES"],
                "authenticity_tier": 3,
                "matched_fathers": ""
            })

            # Exclude Tier 5 (Sunday school / Kids curricula) from general theological search unless explicitly requested
            if b_meta["authenticity_tier"] == 5 and filter_source_type != "EDUCATIONAL_SOURCES":
                continue

            # Check source type filter if provided
            if filter_source_type:
                if filter_source_type not in b_meta["source_types"] and filter_source_type != "ALL":
                    continue

            cleaned_text = clean_theological_text(r["chunk_text"])
            if len(cleaned_text) < 40:
                continue

            # Strict Content Validation: Chunk must contain at least one anchor term in its text
            if all_anchor_terms:
                if not any(t in cleaned_text for t in all_anchor_terms):
                    continue

            clean_title = r["book_title"].replace(".pdf", "")
            phys_page = int(r["page_number"])

            # Author resolution fallback: Parse from title if DB says 'غير محدد'
            resolved_author = b_meta["author"]
            IGNORE_AUTHOR_TOKENS = {"تحميل", "للتحميل", "قراءة", "طبعة", "طبعة ثانية", "pdf", "نسخة", "مجانا", "جديد", "أونلاين"}
            if not resolved_author or resolved_author in ["غير محدد", "غير معروف", "مجهول", "آباء ومعلمو الكنيسة"]:
                for sep in [" - ", " – ", " — "]:
                    if sep in clean_title:
                        parts = [p.strip() for p in clean_title.split(sep)]
                        # Find the first valid part from the end that is not a web download token
                        for p in reversed(parts[1:]):
                            if p.lower() not in IGNORE_AUTHOR_TOKENS and len(p) >= 3:
                                resolved_author = p
                                break
                        if resolved_author and resolved_author not in IGNORE_AUTHOR_TOKENS:
                            break
            # If still invalid or in ignore tokens, check well-known church fathers in title
            if not resolved_author or resolved_author in ["غير محدد", "غير معروف", "مجهول"] or resolved_author in IGNORE_AUTHOR_TOKENS:
                for f_name, f_kws in ChurchSourceClassifier.PATRISTIC_FATHERS.items():
                    if any(k in clean_title for k in f_kws):
                        resolved_author = f_name
                        break
            if not resolved_author or resolved_author in ["غير محدد", "غير معروف", "مجهول"] or resolved_author in IGNORE_AUTHOR_TOKENS:
                resolved_author = "آباء ومعلمو الكنيسة" 
            printed_page = ArabicOcrPostProcessor.extract_printed_page_number(r["chunk_text"], phys_page)

            # Authenticity Multiplier based on source hierarchy & patristic query awareness
            tier = b_meta["authenticity_tier"]
            is_father_match = False
            if target_fathers:
                is_father_match = any(tf in b_meta["matched_fathers"] or tf in clean_title for tf in target_fathers)

            is_bio = any(bio in clean_title for bio in ["حياة", "سيرة", "قصة", "تاريخ"])
            is_primary_father_work = is_father_match and not is_bio and (tier == 1 or any(tf in resolved_author for tf in target_fathers))

            # Check if chunk mentions requested Fathers
            father_in_text = False
            if target_fathers:
                father_in_text = any(tf in cleaned_text or any(k in cleaned_text for k in ChurchSourceClassifier.PATRISTIC_FATHERS.get(tf, [])) for tf in target_fathers)

            if target_fathers and is_primary_father_work:
                weight = 2.2  # Top priority: genuine original patristic writing of the requested Father
                relevance_score = 0.98
            elif target_fathers and father_in_text and tier <= 3 and not is_bio:
                weight = 1.9  # Major scholarly patristic compendium (e.g. Anba Gregorios) detailing the requested Father
                relevance_score = 0.95
            elif target_fathers and is_father_match and not is_bio:
                weight = 1.5  # Scholarly patristic commentary referencing the Father
                relevance_score = 0.92
            elif is_bio:
                weight = 0.3  # Biographical/narrative secondary book - lowest priority
                relevance_score = 0.50
            elif tier == 1:
                weight = 1.5  # Primary Patristic original
                relevance_score = 0.92
            elif tier == 2:
                weight = 1.3  # Scholarly Patristic study
                relevance_score = 0.86
            elif tier == 3:
                weight = 1.0  # Master writings / Encyclopedias
                relevance_score = 0.79
            elif tier == 4:
                weight = 0.95 # Liturgical / Historical
                relevance_score = 0.74
            else:
                weight = 0.7 if target_fathers else 0.85 # Educational catechesis
                relevance_score = 0.68

            page_label = f"صـ {printed_page} (مطبوعة)" if printed_page != phys_page else f"صـ {phys_page}"
            ref_str = f"كتاب: «{clean_title}»، {page_label}"

            entity = ChunkEntity(
                sha256=sha,
                book_title=clean_title,
                file_name=clean_title,
                page_number=phys_page,
                chunk_index=int(r["chunk_index"]),
                source_reference=ref_str,
                chunk_text=cleaned_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0,
                author=resolved_author,
                source_types=b_meta["source_types"],
                authenticity_tier=tier,
                printed_page=printed_page,
                relevance_score=relevance_score,
                citation_type="QUOTATION"
            )
            candidate_items.append((weight, relevance_score, entity))

        # Sort: Highest authority weight first, then highest relevance score
        candidate_items.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # Smart Deduplication across duplicate files and repeated book editions
        results: List[ChunkEntity] = []
        seen_texts: List[str] = []
        seen_fingerprints = set()

        for item in candidate_items:
            entity = item[2]
            text = entity.chunk_text.strip()
            words = text.split()
            fp = " ".join(words[:18]) if len(words) >= 18 else text
            if fp in seen_fingerprints:
                continue

            is_dup = False
            cand_word_set = set(words[:30])
            for prev_text in seen_texts:
                prev_word_set = set(prev_text.split()[:30])
                if cand_word_set and prev_word_set:
                    overlap = len(cand_word_set & prev_word_set) / min(len(cand_word_set), len(prev_word_set))
                    if overlap >= 0.65:
                        is_dup = True
                        break
            if is_dup:
                continue

            seen_fingerprints.add(fp)
            seen_texts.append(text)
            results.append(entity)
            if len(results) >= limit:
                break

        return results

    def search_scoped_book(self, sha256: str, query: str, limit: int = 4) -> List[ChunkEntity]:
        """Performs targeted FTS5 search inside single designated book."""
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        expanded_terms: Set[str] = set()
        for kw in keywords:
            expanded_terms.update(normalize_alef_variants(kw))

        fts_query = " OR ".join([f'"{k}"' for k in list(expanded_terms)[:8]])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
            FROM church_chunks_fts
            WHERE sha256 = ? AND church_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (sha256, fts_query, limit))
        rows = cur.fetchall()
        conn.close()

        results: List[ChunkEntity] = []
        for r in rows:
            clean_title = r["book_title"].replace(".pdf", "")
            cleaned_text = clean_theological_text(r["chunk_text"])
            results.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=clean_title,
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=f"[كتاب: {clean_title}، ص: {r['page_number']}]",
                chunk_text=cleaned_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))
        return results

    def get_patristic_quotes(self, topic: Optional[str] = None, limit: int = 4) -> List[ChunkEntity]:
        """Fetches curated authentic quotes from church fathers on specified spiritual theme."""
        conn = get_connection()
        cur = conn.cursor()

        if topic:
            tokens = [w.strip() for w in topic.split() if len(w.strip()) > 2 and w not in ARABIC_STOPWORDS]
            expanded = set()
            for t in tokens:
                expanded.update(normalize_alef_variants(t))
            fts_expr = " OR ".join([f'"{t}"' for t in list(expanded)[:6]])
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                FROM church_chunks_fts
                WHERE church_chunks_fts MATCH ? AND page_number > 2
                ORDER BY rank
                LIMIT ?
            """, (fts_expr, limit * 2))
        else:
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, 0.0 as rank
                FROM church_chunks_fts
                WHERE page_number > 3 AND LENGTH(chunk_text) > 100
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit * 2,))

        rows = cur.fetchall()
        conn.close()

        quotes: List[ChunkEntity] = []
        for r in rows:
            clean_text = clean_theological_text(r["chunk_text"])
            if not is_chunk_high_quality(clean_text):
                continue
            clean_title = r["book_title"].replace(".pdf", "")
            quotes.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=clean_title,
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=f"[كتاب: {clean_title}، ص: {r['page_number']}]",
                chunk_text=clean_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))
            if len(quotes) >= limit:
                break

        return quotes


# Global search engine singleton instance
search_engine = ChurchSearchEngine()
