# modules/keyword_extractor.py

import re
from collections import Counter

# قائمة بسيطة بالكلمات غير الهامة (Stop Words) باللغة العربية
# يمكن توسيعها في المستقبل أو استخدام مكتبة متخصصة
STOP_WORDS = set(
    [
        "في",
        "من",
        "على",
        "إلى",
        "عن",
        "هو",
        "هي",
        "كان",
        "يكون",
        "وقد",
        "أن",
        "أو",
        "ثم",
        "حتى",
        "لكن",
        "مع",
        "عند",
        "هذا",
        "هذه",
        "ذلك",
        "تلك",
        "كل",
        "بعض",
        "مثل",
        "أي",
        "إذ",
        "إذا",
        "التي",
        "الذي",
        "الذين",
        "اللذين",
        "اللتين",
        "اللاتي",
        "ما",
        "منذ",
        "تم",
        "يتم",
        "حيث",
        "كما",
        "أيضاً",
    ]
)


def clean_text(text):
    """
    ينظف النص من الأرقام، الرموز، والكلمات غير الهامة.
    """
    if not text:
        return ""
    # إزالة الرموز والأرقام
    text = re.sub(r"[^\u0600-\u06FFa-zA-Z0-9\s-]", " ", text)  # إبقاء الحروف العربية والمسافات فقط
    # تحويل النص إلى قائمة كلمات وإزالة الكلمات غير الهامة
    words = [word for word in text.split() if word not in STOP_WORDS and len(word) > 2]
    return " ".join(words)


def extract_top_keywords(text, top_n=10):
    """
    يستخرج أهم الكلمات المفتاحية من النص بناءً على تكرارها.
    """
    if not text:
        return []

    words = text.split()
    # عد تكرار كل كلمة
    word_counts = Counter(words)
    # الحصول على أكثر الكلمات تكراراً
    most_common = word_counts.most_common(top_n)

    # إرجاع الكلمات فقط بدون عدد التكرار
    return [word for word, count in most_common]


def get_main_concepts(full_text, top_n=10):
    """
    الدالة الرئيسية التي تجمع كل الخطوات: تنظيف واستخراج.
    """
    cleaned_text = clean_text(full_text)
    keywords = extract_top_keywords(cleaned_text, top_n)
    # تحويل قائمة الكلمات إلى نص واحد مفصول بمسافات لتخزينه
    return " ".join(keywords)
