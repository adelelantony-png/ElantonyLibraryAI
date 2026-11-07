# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Intelligent Ecclesiastical Source Classification Engine
Phase 2 (Refined): Distinguishes Primary Patristic writings, Theological Studies,
Educational curricula, Liturgical texts, Historical church sources, and
Biblical / Exegetical commentaries with multi-label support and confidence calibration.
"""

import re
import json
from enum import Enum
from typing import Dict, List, Set, Any, Tuple, Optional


class SourceType(str, Enum):
    PRIMARY_PATRISTIC = "PRIMARY_PATRISTIC"      # كتابات الآباء الأصلية وترجماتها المعتمدة
    THEOLOGICAL_STUDIES = "THEOLOGICAL_STUDIES"  # الأبحاث اللاهوتية والعقائدية وتفاسير العهدين
    EDUCATIONAL_SOURCES = "EDUCATIONAL_SOURCES"  # المناهج وإعداد الخدام والشروحات المبسطة
    LITURGICAL_SOURCES = "LITURGICAL_SOURCES"    # الأجبية والخولاجي والألحان والطقوس والتسابيح
    HISTORICAL_SOURCES = "HISTORICAL_SOURCES"    # السنكسار وتاريخ الكنيسة والمخطوطات وسير القديسين
    NEEDS_REVIEW = "NEEDS_REVIEW"                # غير مؤكد كنسياً ويحتاج لمراجعة بشرية


class AuthenticityTier(int, Enum):
    TIER_1_PRIMARY_PATRISTIC = 1       # الأصل الآبائي الصريح المترجم أو المحقق
    TIER_2_SCHOLARLY_STUDY = 2         # دراسة لاهوتية آبائية وتفاسير أمهات الكتب
    TIER_3_ENCYCLOPEDIA_CHURCH = 3     # موسوعات وكتب الآباء المعاصرين (البابا شنودة، متى المسكين، إلخ)
    TIER_4_LITURGY_HISTORY = 4         # مصادر طقسية وتاريخية وتراثية
    TIER_5_EDUCATIONAL_CATECHESIS = 5  # كتب تربوية، إعداد خدام، مدارس أحد


class ChurchSourceClassifier:
    """
    Intelligent Multi-Label Ecclesiastical Source Classifier.
    Analyzes title, folder taxonomy, authors, publishers, and theological keywords
    to assign verified classification and strict authenticity tiers.
    """

    # Primary Church Fathers (Early Church & Golden Age)
    PATRISTIC_FATHERS: Dict[str, List[str]] = {
        "أثناسيوس الرسولي": ["أثناسيوس", "اثناسيوس", "تجسد الكلمة", "ضد الآريوسيين", "رسائل الروح القدس", "حياة أنطونيوس", "athanasius"],
        "كيرلس الكبير": ["كيرلس الكبير", "كيرلس الإسكندري", "كيرلس الاول", "تفسير لوقا كيرلس", "تفسير يوحنا كيرلس", "الحوار حول الثالوث", "عمود الدين", "cyril"],
        "يوحنا ذهبي الفم": ["ذهبي الفم", "يوحنا ذهبي", "chrysostom"],
        "غريغوريوس اللاهوتي": ["غريغوريوس اللاهوتي", "النزينزي", "الخطب اللاهوتية الخمس"],
        "غريغوريوس النيصي": ["غريغوريوس أسقف نيصص", "النيصي"],
        "باسليوس الكبير": ["باسليوس الكبير", "باسليوس القيصري", "عن الروح القدس باسليوس", "basil"],
        "أنطونيوس الكبير": ["أنطونيوس الكبير", "رسائل القديس أنطونيوس", "أقوال القديس أنطونيوس", "anthony the great"],
        "مقار الكبير": ["مقار الكبير", "مكاريوس الكبير", "عظات القديس مقار", "عظات مكاريوس", "macarius"],
        "آباء البرية والرهبنة": ["أبوفثيجماتا", "بستان الرهبان", "أقوال الآباء", "فردوس الآباء", "إسحق السرياني", "مار اسحق", "يوحنا الدرجي", "سلم الفضائل", "الأنبا بولا", "الأنبا باخوميوس", "الأنبا شنودة رئيس المتوحدين"],
        "إيرينيئوس أسقف ليون": ["إيرينيئوس", "ايرينيوس", "ضد الهرطقات", "irenaeus"],
        "إغناطيوس الإنطاكي": ["إغناطيوس", "اغناطيوس الثيوفورس", "رسائل إغناطيوس", "ignatius"],
        "يوستينوس الشهيد": ["يوستينوس", "يوستين الشهيد", "الدفاع الأول", "justin martyr"],
        "كليمندس الإسكندري": ["كليمندس الإسكندري", "المربي كليمندس", "ستروماتا", "clement"],
        "ديديموس الضرير": ["ديديموس الضرير", "ديديموس الاسكندري", "عن الثالوث ديديموس", "didymus"],
        "جيروم": ["جيروم", "إيرونيموس", "ايرونيموس", "الفولجاتا", "jerome", "hieronymus"],
        "أوريجانوس": ["أوريجانوس", "اوريجانوس", "اوريجينوس", "المبادئ", "الرد على كلسس", "origen"],
        "كبريانوس القرطاجي": ["كبريانوس", "قبريانوس", "وحدة الكنيسة", "cyprian"],
        "أوغسطينوس": ["أوغسطينوس", "اوغسطينوس", "مدينة الله", "اعترافات أوغسطينوس", "augustine"],
        "كليمندس الروماني": ["كليمندس الروماني", "رسالة كليمندس الأولى", "رسالة كليمندس"],
        "بوليكاربوس الشهيد": ["بوليكاربوس", "بوليكارب", "استشهاد بوليكاربوس", "polycarp"]
    }

    # Verified Patristic Publisher Signatures
    PATRISTIC_PUBLISHERS: List[str] = [
        "المركز الأرثوذكسي للدراسات الآبائية",
        "نصوص آبائية",
        "مؤسسة القديس أنطونيوس",
        "دير القديس أنبا مقار",
        "دير السريان",
        "دار يوحنا الحبيب",
        "مركز باناريون للتراث الآبائي",
        "patristic"
    ]

    # Biblical Names (Old and New Testament)
    BIBLICAL_BOOKS: List[str] = [
        "تكوين", "خروج", "لاويين", "عدد", "تثنية", "يشوع", "قضاة", "راعوث",
        "صموئيل", "ملوك", "أخبار الأيام", "عزرا", "نحميا", "طوبيا", "يهوديت", "أستير", "ايوب", "أيوب",
        "مزامير", "مزمور", "امثال", "أمثال", "جامعة", "نشيد الأنشاد", "حكمة سليمان", "يشوع بن سيراخ",
        "إشعياء", "اشعياء", "إرميا", "ارميا", "مراثي", "باروخ", "حزقيال", "دانيال",
        "هوشع", "يوئيل", "عاموس", "عوبديا", "يونان", "ميخا", "ناحوم", "حبقوق", "صفنيا", "حجي", "زكريا", "ملاخي",
        "المكابيين",
        "متى", "متي", "مرقس", "لوقا", "يوحنا", "أعمال الرسل", "اعمال الرسل",
        "رومية", "كورنثوس", "غلاطية", "أفسس", "افسس", "فيلبي", "كولوسي", "تسالونيكي",
        "تيموثاوس", "تيطس", "فليمون", "عبرانيين", "يعقوب", "بطرس", "يهوذا", "رؤيا", "العهد الجديد", "العهد القديم"
    ]

    # Liturgical Identifiers
    LITURGICAL_TERMS: List[str] = [
        "أجبية", "اجبية", "خولاجي", "خريستوس", "تسبحة", "ابصلمودية", "إبصلمودية",
        "قطمارس", "قطماروس", "لحن", "ألحان", "طقس", "طقوس", "اسرار الكنيسة",
        "رفع بخور", "قداس", "دلال", "تسبحة نصف الليل", "أسبوع الآلام", "بصخة", "لقان",
        "دفنار", "ابصالية", "إبصالية", "ذكصولوجية"
    ]

    # Historical & Hagiographical Identifiers
    HISTORICAL_TERMS: List[str] = [
        "سنكسار", "تاريخ الكنيسة", "سير القديسين", "سيرة القديس", "شهداء",
        "تاريخ البطاركة", "تاريخ الانشقاق", "مخطوطات", "مخطوط", "يوسابيوس القيصري",
        "ابن كبر", "ابن المقفع", "تاريخ الأمة القبطية", "مخطوطة", "تاريخ الرهبنة"
    ]

    # Educational / Curricula Identifiers
    EDUCATIONAL_TERMS: List[str] = [
        "إعداد خدام", "اعداد خدام", "مدارس الأحد", "مدارس الاحد", "منهج", "مناهج",
        "مهرجان الكرازة", "أسقفية الشباب", "اسقفية الشباب", "تربية كنسية",
        "أسرة مسيحية", "شباب كنسي", "مسابقات", "ألعاب", "أشغال يدوية", "أنشطة",
        "مجلات أطفال", "مجلة الفرح", "مجلة أبطال الكنيسة"
    ]

    # Theological / Apologetic / Monastic Spiritual Identifiers
    THEOLOGICAL_TERMS: List[str] = [
        "لاهوت", "عقيدة", "دفاعيات", "اللاهوت المقارن", "طبيعة المسيح",
        "تجسد", "فداء", "كفارة", "تثليث وتوحيد", "شبهات وهمية", "مجمع نيقية",
        "مجمع أفسس", "مجمع قسطنطينية", "حلمي القمص", "الأنبا بيشوي", "تادرس يعقوب",
        "متى المسكين", "البابا شنودة", "حياة روحية", "حياة الصلاة", "توبة", "نقاوة القلب",
        "الجهاد الروحي", "اليقظة الروحية", "حياة الفضيلة", "الرهبنة", "تفسير"
    ]

    @classmethod
    def classify_source(
        cls,
        title: str,
        category: str = "",
        author: str = "",
        original_path: str = "",
        publisher: str = "",
        sample_text: str = ""
    ) -> Dict[str, Any]:
        """
        Classifies a theological volume into primary, secondary, and authenticity tiers.
        Returns a dictionary with types, primary tier, confidence, and patristic anchor.
        """
        combined = f"{title} {category} {author} {publisher} {original_path}".lower()
        
        assigned_types: Set[SourceType] = set()
        matched_fathers: List[str] = []
        confidence = 0.5
        primary_tier = AuthenticityTier.TIER_3_ENCYCLOPEDIA_CHURCH

        # --- 0. Pre-checks for Educational and Hagiographical Context ---
        is_educational = any(edu in combined for edu in ["إبتدائي", "ابتدائي", "حضانة", "إعدادي", "اعدادي", "مدارس الأحد", "تلوين", "مسابقات", "تربية كنسية"])
        is_biography = any(bio in title for bio in ["حياة ", "سيرة ", "قصة ", "تاريخ "]) and not ("حياة أنطونيوس" in title)

        # --- 1. Patristic Detection (Highest Scientific Precision) ---
        is_patristic = False
        if not is_educational and not is_biography:
            for father, keywords in cls.PATRISTIC_FATHERS.items():
                if any(kw.lower() in combined for kw in keywords):
                    matched_fathers.append(father)
                    is_patristic = True

        has_patristic_publisher = any(pub.lower() in combined for pub in cls.PATRISTIC_PUBLISHERS)

        if is_patristic:
            assigned_types.add(SourceType.PRIMARY_PATRISTIC)
            if has_patristic_publisher or "الجزء" in title or "ترجمة" in combined or "نصوص آبائية" in combined:
                primary_tier = AuthenticityTier.TIER_1_PRIMARY_PATRISTIC
                confidence = 0.95
            else:
                primary_tier = AuthenticityTier.TIER_2_SCHOLARLY_STUDY
                confidence = 0.88
                assigned_types.add(SourceType.THEOLOGICAL_STUDIES)
        elif is_biography:
            # Biographies and historical narratives mentioning Church Fathers are Tier 3 Historical Studies
            for father, keywords in cls.PATRISTIC_FATHERS.items():
                if any(kw.lower() in combined for kw in keywords):
                    matched_fathers.append(father)
            assigned_types.add(SourceType.HISTORICAL_SOURCES)
            assigned_types.add(SourceType.THEOLOGICAL_STUDIES)
            primary_tier = AuthenticityTier.TIER_3_ENCYCLOPEDIA_CHURCH
            confidence = 0.85

        # --- 2. Liturgical Detection ---
        if any(term in combined for term in cls.LITURGICAL_TERMS):
            assigned_types.add(SourceType.LITURGICAL_SOURCES)
            if not is_patristic:
                primary_tier = AuthenticityTier.TIER_4_LITURGY_HISTORY
                confidence = max(confidence, 0.90)

        # --- 3. Historical / Hagiography Detection ---
        if any(term in combined for term in cls.HISTORICAL_TERMS):
            assigned_types.add(SourceType.HISTORICAL_SOURCES)
            if not is_patristic:
                primary_tier = AuthenticityTier.TIER_4_LITURGY_HISTORY
                confidence = max(confidence, 0.88)

        # --- 4. Educational / Sunday School Detection ---
        if is_educational or any(term in combined for term in cls.EDUCATIONAL_TERMS):
            assigned_types.add(SourceType.EDUCATIONAL_SOURCES)
            if not is_patristic and SourceType.LITURGICAL_SOURCES not in assigned_types:
                primary_tier = AuthenticityTier.TIER_5_EDUCATIONAL_CATECHESIS
                confidence = max(confidence, 0.92)

        # --- 5. Biblical Exegesis & Theological Studies Detection ---
        is_biblical = any(re.search(rf"(?:^|\D){b}(?:\D|$)", combined) for b in cls.BIBLICAL_BOOKS)
        is_theological = any(term in combined for term in cls.THEOLOGICAL_TERMS) or "تفسير" in combined

        if (is_biblical or is_theological) and not is_educational:
            assigned_types.add(SourceType.THEOLOGICAL_STUDIES)
            if primary_tier > AuthenticityTier.TIER_2_SCHOLARLY_STUDY and not is_biography:
                primary_tier = AuthenticityTier.TIER_2_SCHOLARLY_STUDY if ("تفسير" in combined or "بحث" in combined or is_biblical) else AuthenticityTier.TIER_3_ENCYCLOPEDIA_CHURCH
                confidence = max(confidence, 0.85)

        # Default fallback if nothing clearly matched
        if not assigned_types:
            assigned_types.add(SourceType.NEEDS_REVIEW)
            primary_tier = AuthenticityTier.TIER_3_ENCYCLOPEDIA_CHURCH
            confidence = 0.40

        return {
            "source_types": [t.value for t in assigned_types],
            "primary_type": list(assigned_types)[0].value,
            "authenticity_tier": primary_tier.value,
            "confidence_score": round(confidence, 2),
            "matched_patristic_fathers": matched_fathers,
            "is_authoritative_patristic": (AuthenticityTier.TIER_1_PRIMARY_PATRISTIC == primary_tier),
            "needs_review": (SourceType.NEEDS_REVIEW in assigned_types or confidence < 0.60)
        }



classifier = ChurchSourceClassifier()
