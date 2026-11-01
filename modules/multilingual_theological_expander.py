# -*- coding: utf-8 -*-
"""
ArchiveMaster - Multilingual Theological Expander
محرك التوسيع والترجمة اللاهوتية العابر للغات
Bridges Arabic theological queries into Greek, Russian, English, and French
to enable cross-lingual discovery across global Orthodox Christian repositories.
"""

import re
import urllib.parse
from deep_translator import GoogleTranslator

# Canonical Orthodox Theological Lexicon (Mapping Core Concepts across 5 Languages)
THEOLOGICAL_LEXICON = {
    "تجسد الكلمة": {
        "en": "Incarnation of the Word",
        "el": "Περὶ τῆς ἐνανθρωπήσεως τοῦ Λόγου",
        "ru": "О воплощении Бога Слова",
        "fr": "Incarnation du Verbe"
    },
    "طبيعة المسيح": {
        "en": "Nature of Christ Christology",
        "el": "Χριστολογία φύσις Χριστοῦ",
        "ru": "О природе Христа Христология",
        "fr": "Nature du Christ Christologie"
    },
    "سر الافخارستيا": {
        "en": "Holy Eucharist Liturgy",
        "el": "Θεία Εὐχαριστία Λειτουργία",
        "ru": "Таинство Евхаристии Литургия",
        "fr": "Sainte Eucharistie Liturgie"
    },
    "سر التناول": {
        "en": "Holy Communion Eucharist",
        "el": "Θεία Κοινωνία",
        "ru": "Причастие Евхаристия",
        "fr": "Sainte Communion"
    },
    "الثالوث القدوس": {
        "en": "Holy Trinity",
        "el": "Ἁγία Τριάς",
        "ru": "Святая Троица",
        "fr": "Sainte Trinité"
    },
    "القديس أثناسيوس الرسولي": {
        "en": "Athanasius of Alexandria",
        "el": "Ἀθανάσιος Ἀλεξανδρείας",
        "ru": "Афанасий Великий",
        "fr": "Athanase d'Alexandrie"
    },
    "القديس أثناسيوس": {
        "en": "St. Athanasius",
        "el": "Ἅγιος Ἀθανάσιος",
        "ru": "Святитель Афанасий",
        "fr": "Saint Athanase"
    },
    "القديس كيرلس الكبير": {
        "en": "Cyril of Alexandria",
        "el": "Κύριλλος Ἀλεξανδρείας",
        "ru": "Кирилл Александрийский",
        "fr": "Cyrille d'Alexandrie"
    },
    "القديس كيرلس": {
        "en": "St. Cyril",
        "el": "Ἅγιος Κύριλλος",
        "ru": "Святитель Кирилл",
        "fr": "Saint Cyrille"
    },
    "القديس باسيليوس الكبير": {
        "en": "Basil of Caesarea",
        "el": "Βασίλειος ὁ Μέγας",
        "ru": "Василий Великий",
        "fr": "Basile de Césarée"
    },
    "القديس غريغوريوس اللاهوتي": {
        "en": "Gregory of Nazianzus",
        "el": "Γρηγόριος ὁ Θεολόγος",
        "ru": "Григорий Богослов",
        "fr": "Grégoire de Nazianze"
    },
    "القديس غريغوريوس النيصي": {
        "en": "Gregory of Nyssa",
        "el": "Γρηγόριος Νύσσης",
        "ru": "Григорий Нисский",
        "fr": "Grégoire de Nysse"
    },
    "القديس يوحنا ذهبي الفم": {
        "en": "John Chrysostom",
        "el": "Ἰωάννης ὁ Χρυσόστομος",
        "ru": "Иоанн Златоуст",
        "fr": "Jean Chrysostome"
    },
    "القديس أنطونيوس الكبير": {
        "en": "Anthony the Great",
        "el": "Ἀντώνιος ὁ Μέγας",
        "ru": "Антоний Великий",
        "fr": "Antoine le Grand"
    },
    "القديس مكاريوس الكبير": {
        "en": "Macarius the Great",
        "el": "Μακάριος ὁ Αἰγύπτιος",
        "ru": "Макарий Великий",
        "fr": "Macaire d'Égypte"
    },
    "القديس باخوميوس": {
        "en": "Pachomius the Great",
        "el": "Παχώμιος ὁ Μέγας",
        "ru": "Пахомий Великий",
        "fr": "Pachôme le Grand"
    },
    "مجمع نيقية": {
        "en": "First Council of Nicaea",
        "el": "Α΄ Οἰκουμενικὴ Σύνοδος Νίκαια",
        "ru": "Первый Никейский собор",
        "fr": "Premier concile de Nicée"
    },
    "مجمع القسطنطينية": {
        "en": "First Council of Constantinople",
        "el": "Β΄ Οἰκουμενικὴ Σύνοδος Κωνσταντινούπολις",
        "ru": "Первый Константинопольский собор",
        "fr": "Premier concile de Constantinople"
    },
    "مجمع أفسس": {
        "en": "Council of Ephesus",
        "el": "Γ΄ Οἰκουμενικὴ Σύνοδος Ἔφεσος",
        "ru": "Эфесский собор",
        "fr": "Concile d'Éphèse"
    },
    "الرهبنة القبطية": {
        "en": "Coptic Monasticism Desert Fathers",
        "el": "Αἰγυπτιακὸς Μοναχισμός",
        "ru": "Египетское монашество отцы пустынники",
        "fr": "Monachisme copte pères du désert"
    },
    "اللاهوت المقارن": {
        "en": "Comparative Theology Dogmatics",
        "el": "Συγκριτικὴ Θεολογία",
        "ru": "Сравнительное богословие",
        "fr": "Théologie comparée"
    },
    "تفسير العهد الجديد": {
        "en": "New Testament Commentary Exegesis",
        "el": "Ἑρμηνεία Καινῆς Διαθήκης",
        "ru": "Толкование Нового Завета",
        "fr": "Commentaire Nouveau Testament"
    },
    "تفسير العهد القديم": {
        "en": "Old Testament Commentary Septuagint",
        "el": "Ἑρμηνεία Παλαιᾶς Διαθήκης",
        "ru": "Толкование Ветхого Завета",
        "fr": "Commentaire Ancien Testament"
    },
    "تاريخ الكنيسة القبطية": {
        "en": "History of the Coptic Church",
        "el": "Ἱστορία Κοπτικῆς Ἐκκλησίας",
        "ru": "История Коптской Церкви",
        "fr": "Histoire de l'Église copte"
    }
}


def expand_theological_query(query: str, target_languages: list = None) -> dict:
    """
    Expands an Arabic query into Greek, Russian, English, and French
    using the curated patristic lexicon + dynamic neural translation fallback.
    Returns:
    {
        "original": "تجسد الكلمة",
        "en": "Incarnation of the Word",
        "el": "Περὶ τῆς ἐνανθρωπήσεως τοῦ Λόγου",
        "ru": "О воплощении Бога Слова",
        "fr": "Incarnation du Verbe",
        "all_terms": ["تجسد الكلمة", "Incarnation of the Word", ...]
    }
    """
    q_clean = query.strip()
    if not q_clean:
        return {"original": "", "en": "", "el": "", "ru": "", "fr": "", "all_terms": []}

    targets = target_languages or ["en", "el", "ru", "fr"]
    result = {"original": q_clean}

    # 1. Check exact or partial matches in the Curated Lexicon
    matched_lex = None
    for k, v in THEOLOGICAL_LEXICON.items():
        if k in q_clean or q_clean in k:
            matched_lex = v
            break

    for lang in targets:
        if matched_lex and lang in matched_lex:
            result[lang] = matched_lex[lang]
        else:
            # 2. Dynamic Translation Fallback
            try:
                # Map language codes
                g_code = lang
                if lang == "el":
                    g_code = "el"  # Greek
                elif lang == "ru":
                    g_code = "ru"  # Russian
                elif lang == "fr":
                    g_code = "fr"  # French
                else:
                    g_code = "en"

                translated = GoogleTranslator(source="ar", target=g_code).translate(q_clean)
                result[lang] = translated.strip() if translated else q_clean
            except Exception:
                result[lang] = q_clean

    all_terms = [q_clean]
    for lang in targets:
        term = result.get(lang)
        if term and term not in all_terms:
            all_terms.append(term)

    result["all_terms"] = all_terms
    return result


def translate_foreign_metadata_to_arabic(text: str, source_lang: str = "auto") -> str:
    """
    Translates foreign book titles, authors, or summaries into Arabic
    so the researcher can read and understand international references instantly.
    """
    if not text or not text.strip():
        return ""
    try:
        translated = GoogleTranslator(source=source_lang, target="ar").translate(text.strip())
        return translated if translated else text
    except Exception:
        return text
