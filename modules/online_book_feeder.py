"""
Cross Coptic Library - Intelligent Online Book Feeder (Ultra Pro Max)
Crawls and downloads authorized Coptic Orthodox books from:
1. Coptic Reads (copticreads.org)
2. Coptic Treasures (coptic-treasures.com)
3. ChristianLib (christianlib.com)
Directly into the canonical library folders and updates database index.
"""

import os
import re
import sys
import json
import sqlite3
import httpx
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}

DB_PATH = "D:/Prog/ArchiveMasterFinal/file_archive.db"

# -------------------------------------------------------------
# CURATED PACKS - باقات النهضة الروحية والتعليمية الكنسية الجاهزة
# -------------------------------------------------------------
CURATED_PACKS = {
    "sunday_school_curricula": {
        "title": "🎒 باقة مناهج التربية الكنسية المعتمدة (المجمع المقدس)",
        "desc": "مناهج التربية الكنسية الرسمية الصادرة عن المجمع المقدس من الحضانة حتى الإعدادي",
        "books": [
            ("منهج التربية الكنسية إصدار المجمع المقدس - مرحلة الحضانة KG2", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-17/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - الصف الأول الإبتدائي", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-15/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - الصف الثاني الإبتدائي", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-13/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - الصف الثالث الإبتدائي", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-11/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - الصف الخامس الإبتدائي", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-7/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - الصف السادس الإبتدائي", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-5/"),
            ("منهج التربية الكنسية إصدار المجمع المقدس - المرحلة الإعدادية", 
             "https://coptic-treasures.com/book/%d9%85%d9%86%d9%87%d8%ac-%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a%d8%a9-%d8%a5%d8%b5%d8%af%d8%a7%d8%b1-%d8%a7%d9%84%d9%85%d8%ac%d9%85%d8%b9-%d8%a7%d9%84%d9%85-4/")
        ]
    },
    "servants_preparation": {
        "title": "💡 باقة إعداد الخدام وفلسفة التعليم الكنسي",
        "desc": "أدلة الخادم في التدريس التفاعلي ووسائل الإيضاح وإعداد دروس مدارس الأحد",
        "books": [
            ("كيف نخدم الأطفال؟ - خدام بيت محبة الله", 
             "https://coptic-treasures.com/book/%d9%83%d9%8a%d9%81-%d9%86%d8%ae%d8%af%d9%85-%d8%a7%d9%84%d8%a3%d8%b7%d9%81%d8%a7%d9%84%d8%9f-%d8%ae%d8%af%d8%a7%d9%85-%d8%a8%d9%8a%d8%aa-%d9%85%d8%ad%d8%a8%d8%a9-%d8%a7%d9%84%d9%84%d9%87/"),
            ("وسائل الإيضاح في تعليم المسيح - المهندس أندراوس عبد المسيح", 
             "https://coptic-treasures.com/book/%d9%88%d8%b3%d8%a7%d8%a6%d9%84-%d8%a7%d9%84%d8%a5%d9%8a%d8%b6%d8%a7%d8%ad-%d9%81%d9%8a-%d8%aa%d8%b9%d9%84%d9%8a%d9%85-%d8%a7%d9%84%d9%85%d8%b3%d9%8a%d8%ad-%d8%a7%d9%84%d9%85%d9%87%d9%86%d8%af%d8%b3/"),
            ("الدرس التفاعلي - الدكتور مجدي فرج", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%af%d8%b1%d8%b3-%d8%a7%d9%84%d8%aa%d9%81%d8%a7%d8%b9%d9%84%d9%8a-%d8%a7%d9%84%d8%af%d9%83%d8%aa%d9%88%d8%b1-%d9%85%d8%ac%d8%af%d9%8a-%d9%81%d8%b1%d8%ac/"),
            ("التعليم الكنسي - فلسفة التعليم في الكنيسة - الدكتور مجدي فرج", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%aa%d8%b9%d9%84%d9%8a%d9%85-%d8%a7%d9%84%d9%83%d9%86%d8%b3%d9%8a-%d9%81%d9%84%d8%b3%d9%81%d8%a9-%d8%a7%d9%84%d8%aa%d8%b9%d9%84%d9%8a%d9%85-%d9%81%d9%8a-%d8%a7%d9%84%d9%83%d9%86%d9%8a/"),
            ("إتبعني - كيف تعد نفسك لخدمة الرب؟ - الدكتور مجدي فرج", 
             "https://coptic-treasures.com/book/%d8%a5%d8%aa%d8%a8%d8%b9%d9%86%d9%8a-%d9%83%d9%8a%d9%81-%d8%aa%d8%b9%d8%af-%d9%86%d9%81%d8%b3%d9%83-%d9%84%d8%ae%d8%af%d9%85%d8%a9-%d8%a7%d9%84%d8%b1%d8%a8%d8%9f-%d8%a7%d9%84%d8%af%d9%83%d8%aa/"),
            ("التربية المسيحية - الأنبا بيمن أسقف ملوي والدكتور سليمان نسيم", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%aa%d8%b1%d8%a8%d9%8a%d8%a9-%d8%a7%d9%84%d9%85%d8%b3%d9%8a%d8%ad%d9%8a%d8%a9-%d8%a7%d9%84%d8%a3%d9%86%d8%a8%d8%a7-%d8%a8%d9%8a%d9%85%d9%86-%d8%a3%d8%b3%d9%82%d9%81-%d9%85%d9%84%d9%88/")
        ]
    },
    "family_counseling": {
        "title": "🕊️ باقة الأسرة المسيحية والإرشاد والمشورة",
        "desc": "أهم المراجع الأرثوذكسية في التربية، حماية الأبناء، الزواج والمذبح العائلي",
        "books": [
            ("حتى لا نفقد أولادنا - الأنبا مكاريوس أسقف المنيا", 
             "https://coptic-treasures.com/book/%d8%ad%d8%aa%d9%89-%d9%84%d8%a7-%d9%86%d9%81%d9%82%d8%af-%d8%a3%d9%88%d9%84%d8%a7%d8%af%d9%86%d8%a7-%d8%a7%d9%84%d8%a3%d9%86%d8%a8%d8%a7-%d9%85%d9%83%d8%a7%d8%b1%d9%8a%d9%88%d8%b3-%d8%a7%d8%b3%d9%82/"),
            ("المذبح العائلي جـ1 - خدام بيت محبة الله", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d9%85%d8%b0%d8%a8%d8%ad-%d8%a7%d9%84%d8%b9%d8%a7%d8%a6%d9%84%d9%8a-%d8%ac%d9%801-%d8%ae%d8%af%d8%a7%d9%85-%d8%a8%d9%8a%d8%aa-%d9%85%d8%ad%d8%a8%d8%a9-%d8%a7%d9%84%d9%84%d9%87/"),
            ("الأسرة المسيحية من الألف للياء - القمص بيشوي وديع", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%a3%d8%b3%d8%b1%d8%a9-%d8%a7%d9%84%d9%85%d8%b3%d9%8a%d8%ad%d9%8a%d8%a9-%d9%85%d9%86-%d8%a7%d9%84%d8%a7%d9%84%d9%81-%d9%84%d9%84%d9%8a%d8%a7%d8%a1-%d8%a7%d9%84%d9%82%d9%85%d8%b5-%d8%a8/"),
            ("الأمومة رسالة متكاملة - القمص بيشوي وديع", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%a3%d9%85%d9%88%d9%85%d8%a9-%d8%b1%d8%b3%d8%a7%d9%84%d8%a9-%d9%85%d8%aa%d9%83%d8%a7%d9%85%d9%84%d8%a9-%d8%a7%d9%84%d9%82%d9%85%d8%b5-%d8%a8%d9%8a%d8%b4%d9%88%d9%89-%d9%88%d8%af%d9%8a/"),
            ("العاطفة والحب والجنس والخطوبة والزواج - القس أباكير فرج", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%b9%d8%a7%d8%b7%d9%81%d8%a9-%d9%88%d8%a7%d9%84%d8%ad%d8%a8-%d9%88%d8%a7%d9%84%d8%ac%d9%86%d8%b3-%d9%88%d8%a7%d9%84%d8%ae%d8%b7%d9%88%d8%a8%d8%a9-%d9%88%d8%a7%d9%84%d8%b2%d9%88%d8%a7/"),
            ("كتاب الجهاد الروحي للمرأة - إيريس المصري",
             "https://www.christianlib.com/36899.html/%d9%83%d8%aa%d8%a7%d8%a8-%d8%a7%d9%84%d8%ac%d9%87%d8%a7%d8%af-%d8%a7%d9%84%d8%b1%d9%88%d8%ad%d9%8a-%d9%84%d9%84%d9%85%d8%b1%d8%a3%d8%a9-%d8%a5%d9%8a%d8%b1%d9%8a%d8%b3-%d8%a7%d9%84%d9%85%d8%b5%d8%b1/")
        ]
    },
    "patristic_classics": {
        "title": "📜 باقة نصوص وشروح الآباء القديسين المحققة",
        "desc": "كتابات البابا كيرلس الكبير، العلامة ترتيليانوس، إكليمندس السكندري وساويرس المقفع",
        "books": [
            ("شرح قانون الإيمان للقديس كيرلس السكندري - ترجمة د. موريس تاوضروس ود. نصحي عبد الشهيد", 
             "https://coptic-treasures.com/book/%d8%b4%d8%b1%d8%ad-%d9%82%d8%a7%d9%86%d9%88%d9%86-%d8%a7%d9%84%d8%a7%d9%8a%d9%85%d8%a7%d9%86-%d9%84%d9%84%d9%82%d8%af%d9%8a%d8%b3-%d9%83%d9%8a%d8%b1%d9%84%d8%b3-%d8%a7%d9%84%d8%b3%d9%83%d9%86%d8%af/"),
            ("رسائل القديس كيرلس (51-83) جـ4 - ترجمة د. موريس تاوضروس ود. نصحي", 
             "https://coptic-treasures.com/book/%d8%b1%d8%b3%d8%a7%d8%a6%d9%84-%d8%a7%d9%84%d9%82%d8%af%d9%8a%d8%b3-%d9%83%d9%8a%d8%b1%d9%84%d8%b3-51-83-%d8%ac%d9%804-%d8%aa%d8%b1%d8%ac%d9%85%d8%a9-%d8%af-%d9%85%d9%88%d8%b1%d9%8a%d8%b3/"),
            ("رسائل القديس كيرلس (32-50) جـ3 - ترجمة د. موريس تاوضروس ود. نصحي", 
             "https://coptic-treasures.com/book/%d8%b1%d8%b3%d8%a7%d8%a6%d9%84-%d8%a7%d9%84%d9%82%d8%af%d9%8a%d8%b3-%d9%83%d9%8a%d8%b1%d9%84%d8%b3-32-50-%d8%a7%d9%84%d8%a8%d8%a7%d8%a8%d8%a7-%d9%83%d9%8a%d8%b1%d9%84%d8%b3-%d8%a7%d9%84%d8%a3-2/"),
            ("الإفخارستيا عند القديس كيرلس الإسكندري - الدكتور موريس تاوضروس", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%a5%d9%81%d8%ae%d8%a7%d8%b1%d8%b3%d8%aa%d9%8a%d8%a7-%d8%b9%d9%86%d8%af-%d8%a7%d9%84%d9%82%d8%af%d9%8a%d8%b3-%d9%83%d9%8a%d8%b1%d9%84%d8%b3-%d8%a7%d9%84%d8%a7%d8%b3%d9%83%d9%86%d8%af/"),
            ("الفكر اللاهوتي للقديس ساويرس بن المقفع - القس أباكير فرج", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d9%81%d9%83%d8%b1-%d8%a7%d9%84%d9%84%d8%a7%d9%87%d9%88%d8%aa%d9%89-%d9%84%d9%84%d9%82%d8%af%d9%8a%d8%b3-%d8%b3%d8%a7%d9%88%d9%8a%d8%b1%d8%b3-%d8%a8%d9%86-%d8%a7%d9%84%d9%85%d9%82%d9%81/"),
            ("أقوال العلامة ترتيليانوس عن التوبة - الشماس يوسف حبيب", 
             "https://coptic-treasures.com/book/%d8%a7%d9%82%d9%88%d8%a7%d9%84-%d8%a7%d9%84%d8%b9%d9%84%d8%a7%d9%85%d8%a9-%d8%aa%d8%b1%d8%aa%d9%8a%d9%84%d9%8a%d8%a7%d9%86%d9%88%d8%b3-%d8%b9%d9%86-%d8%a7%d9%84%d8%aa%d9%88%d8%a8%d8%a9-%d8%a7%d9%84/")
        ]
    },
    "apologetics_faith": {
        "title": "🛡️ باقة اللاهوت الدفاعي والرد على الإلحاد والشبهات",
        "desc": "موسوعات الدفاع عن العقيدة، الرد على التشكيك في وجود الله، وتفنيد الشبهات",
        "books": [
            ("الإلحاد جـ1 - خدام بيت محبة الله", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%a7%d9%84%d8%ad%d8%a7%d8%af-%d8%ac%d9%801-%d8%ae%d8%af%d8%a7%d9%85-%d8%a8%d9%8a%d8%aa-%d9%85%d8%ad%d8%a8%d8%a9-%d8%a7%d9%84%d9%84%d9%87/"),
            ("الإلحاد جـ2 - خدام بيت محبة الله", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%a7%d9%84%d8%ad%d8%a7%d8%af-%d8%ac%d9%802-%d8%ae%d8%af%d8%a7%d9%85-%d8%a8%d9%8a%d8%aa-%d9%85%d8%ad%d8%a8%d8%a9-%d8%a7%d9%84%d9%84%d9%87/"),
            ("أسئلة هامة عن التثليث والتوحيد والتجسد - خدام بيت محبة الله", 
             "https://coptic-treasures.com/book/%d8%a3%d8%b3%d8%a6%d9%84%d8%a9-%d9%87%d8%a7%d9%85%d8%a9-%d8%b9%d9%86-%d8%a7%d9%84%d8%aa%d8%ab%d9%84%d9%8a%d8%ab-%d9%88%d8%a7%d9%84%d8%aa%d9%88%d8%ad%d9%8a%d8%af-%d9%88-%d8%a7%d9%84%d8%aa%d8%ac%d8%b3/"),
            ("التدين السليم - الأنبا بيمن أسقف ملوي المتنيح", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%aa%d8%af%d9%8a%d9%86-%d8%a7%d9%84%d8%b3%d9%84%d9%8a%d9%85-%d9%83%d9%85%d8%a7%d9%84-%d8%ad%d8%a8%d9%8a%d8%a8-%d8%a7%d9%84%d8%a3%d9%86%d8%a8%d8%a7-%d8%a8%d9%8a%d9%85%d9%86-%d8%a3/"),
            ("الديانة المسيحية مفاهيم أساسية مقارنة بالمعتقدات الأخرى - الدكتور موريس تاوضروس", 
             "https://coptic-treasures.com/book/%d8%a7%d9%84%d8%af%d9%8a%d8%a7%d9%86%d8%a9-%d8%a7%d9%84%d9%85%d8%b3%d9%8a%d8%ad%d9%8a%d8%a9-%d9%85%d9%81%d8%a7%d9%87%d9%8a%d9%85-%d8%a3%d8%b3%d8%a7%d8%b3%d9%8a%d8%a9-%d9%85%d9%82%d8%a7%d8%b1%d9%86/"),
            ("كتاب حتميات الإيمان المسيحي دراسة مقارنة",
             "https://www.christianlib.com/35609.html/%d9%83%d8%aa%d8%a7%d8%a8-%d8%ad%d8%aa%d9%85%d9%8a%d8%a7%d8%aa-%d8%a7%d9%84%d8%a5%d9%8a%d9%85%d8%a7%d9%86-%d8%a7%d9%84%d9%85%d8%b3%d9%8a%d8%ad%d9%8a-%d8%af%d8%b1%d8%a7%d8%b3%d8%a9-%d9%85%d9%82%d8%a7/")
        ]
    }
}

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=10)

def record_downloaded_file(dest_path, filename, category_folder):
    """Indexes downloaded file into SQLite database."""
    try:
        fsize = os.path.getsize(dest_path)
        mtime = os.path.getmtime(dest_path)
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO files (root_folder_id, file_path, file_name, extension, size, mod_time, category, ai_status)
            VALUES (1, ?, ?, '.pdf', ?, ?, '📄 PDF', 'pending')
        """, (dest_path, filename, fsize, mtime))
        con.commit()
        con.close()
    except Exception as e:
        print(f"Index error for {filename}: {e}")

def resolve_direct_pdf_url(url: str, timeout: float = 15.0) -> str:
    """
    Smart Headless/Cloud Drive & Mediafire Emulator Resolver:
    Unpacks intermediate landing pages (Mediafire JS, Google Drive Confirmation, ChristianLib, Archive.org)
    and resolves them to the final direct downloadable stream URL.
    """
    if not url:
        return ""

    url_clean = url.strip()
    if url_clean.lower().endswith(".pdf") and "drive.google" not in url_clean and "mediafire.com" not in url_clean:
        return url_clean

    # 1. Mediafire smart deep extractor (handles modern JS patterns and direct CDN links)
    if "mediafire.com" in url_clean:
        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
                r = client.get(url_clean)
                patterns = [
                    r'href="(https?://download\d*\.mediafire\.com/[^"]+)"',
                    r'aria-label="Download file"\s+href="([^"]+)"',
                    r'id="downloadButton"\s+href="([^"]+)"',
                    r'kNO\s*=\s*["\'](https?://[^"\']+)["\']',
                    r'window\.location\.href\s*=\s*["\'](https?://download[^"\']+)["\']',
                    r'class="input popsok"\s+href="([^"]+)"',
                    r'<a\s+[^>]*class="[^"]*download_link[^"]*"[^>]*href="([^"]+)"'
                ]
                for p in patterns:
                    m = re.search(p, r.text, re.IGNORECASE)
                    if m:
                        candidate = m.group(1).replace("&amp;", "&")
                        if "mediafire.com" in candidate or candidate.startswith("http"):
                            return candidate
        except Exception as e:
            print(f"Mediafire resolve notice: {e}")

    # 2. Google Drive multi-stage resolver
    if "drive.google.com" in url_clean or "drive.usercontent.google.com" in url_clean:
        m_id = re.search(r'id=([a-zA-Z0-9_\-]{25,})', url_clean)
        if not m_id:
            m_id = re.search(r'/d/([a-zA-Z0-9_\-]+)', url_clean)
        if not m_id:
            m_id = re.search(r'file/d/([a-zA-Z0-9_\-]+)', url_clean)
        if m_id:
            file_id = m_id.group(1)
            return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"

    # 3. Archive.org details page resolution
    if "archive.org/details/" in url_clean:
        try:
            ident = url_clean.split("/details/")[-1].split("/")[0].split("?")[0]
            meta_url = f"https://archive.org/metadata/{ident}/files"
            with httpx.Client(headers=HEADERS, timeout=timeout) as client:
                r = client.get(meta_url)
                files = r.json().get("result", [])
                pdf_files = [f for f in files if f.get("name", "").lower().endswith(".pdf")]
                if pdf_files:
                    pdf_files.sort(key=lambda x: int(x.get("size", 0) or 0), reverse=True)
                    best_name = pdf_files[0].get("name")
                    return f"https://archive.org/download/{ident}/{urllib.parse.quote(best_name)}"
        except Exception as e:
            print(f"Archive.org resolve error: {e}")

    return url_clean

def resolve_and_download_pdf(dl_url, dest_path, log_callback=None):
    """
    Robust multi-stage streaming downloader for Mediafire, Google Drive, Archive.org, and Church repos.
    Handles session cookies, virus scan confirmations, chunked memory streaming, and PDF magic byte verification.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    resolved_url = resolve_direct_pdf_url(dl_url) or dl_url

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=180.0) as client:
            resp = client.get(resolved_url)

            # Check for Google Drive large file virus check bypass
            if resp.status_code == 200 and b"%PDF" not in resp.content[:64]:
                # Check for direct confirmation link or form token
                confirm_match = re.search(r'href="(/uc\?[^"]*confirm=[^"]*)"', resp.text)
                if not confirm_match:
                    confirm_match = re.search(r'href="(/download\?[^"]*confirm=[^"]*)"', resp.text)
                if not confirm_match:
                    token_m = re.search(r'confirm=([a-zA-Z0-9_\-]+)', resp.text)
                    if token_m:
                        confirm_token = token_m.group(1)
                        confirm_url = f"{resolved_url}&confirm={confirm_token}"
                        _log("  ℹ️ محاكاة تأكيد فحص الفيروسات لملف Google Drive كبير...")
                        resp = client.get(confirm_url)
                elif confirm_match:
                    _log("  ℹ️ تأكيد تنزيل ملف Google Drive عبر الرابط الموثق...")
                    confirm_path = confirm_match.group(1).replace("&amp;", "&")
                    if confirm_path.startswith("http"):
                        confirm_url = confirm_path
                    else:
                        base = "https://drive.usercontent.google.com" if "usercontent" in resolved_url else "https://drive.google.com"
                        confirm_url = base + confirm_path
                    resp = client.get(confirm_url)

            # Check for Mediafire intermediate landing page on initial response
            if resp.status_code == 200 and b"%PDF" not in resp.content[:64] and "mediafire.com" in resp.text:
                m_btn = re.search(r'href="(https?://download\d*\.mediafire\.com/[^"]+)"', resp.text)
                if m_btn:
                    direct_mf = m_btn.group(1)
                    _log(f"  ℹ️ التقاط رابط التحميل المباشر لـ Mediafire: {direct_mf[:60]}...")
                    resp = client.get(direct_mf)

            if resp.status_code != 200:
                _log(f"  ❌ استجابة الخادم غير ناجحة: كود {resp.status_code}")
                return False

            first_chunk = resp.content[:1024]
            if b"%PDF" not in first_chunk:
                _log("  ⚠️ تنبيه: الملف المستلم لم يتطابق مع ترويسة PDF القياسية.")
                return False

            # Write stream to disk safely
            idx = first_chunk.find(b"%PDF")
            with open(dest_path, "wb") as f_out:
                f_out.write(resp.content[idx:])

            f_size = os.path.getsize(dest_path)
            _log(f"  💾 تم حفظ الملف بنجاح ({f_size / (1024*1024):.2f} ميجابايت).")
            return True
    except Exception as e:
        _log(f"  ❌ تعذر التنزيل: {e}")
        return False

def sync_copticreads(library_root, max_books=15, query=None, log_callback=None):
    """
    Crawls copticreads.org sitemap and downloads books directly.
    Supports filtering by query.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer

    _log("🌐 الاتصال بموقع Coptic Reads وقراءة الفهرس الرقمي الشامل...")
    try:
        r_sitemap = httpx.get("https://copticreads.org/sitemap.xml", headers=HEADERS, timeout=25.0)
        root = ET.fromstring(r_sitemap.text)
        book_urls = []
        for child in root:
            loc = child.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None and loc.text and '/ar/books/' in loc.text:
                if query:
                    # Filter query
                    q_clean = query.strip().lower()
                    url_clean = urllib.parse.unquote(loc.text).lower()
                    if q_clean in url_clean:
                        book_urls.append(loc.text)
                else:
                    book_urls.append(loc.text)
        _log(f"✅ تم العثور على {len(book_urls)} كتاباً متاحاً في Coptic Reads.")
    except Exception as e:
        _log(f"❌ تعذر قراءة فهرس Coptic Reads: {e}")
        return 0

    downloaded = 0
    for b_url in book_urls:
        if downloaded >= max_books:
            break
        try:
            r_page = httpx.get(b_url, headers=HEADERS, timeout=15.0)
            soup = BeautifulSoup(r_page.text, 'html.parser')
            title = soup.title.string.replace('| Coptic Reads', '').strip() if soup.title else ""
            if not title:
                title = b_url.split('/')[-1]

            pdf_match = re.search(r'https://kerolesmas-001-site4\.mtempurl\.com/Uploads/BookFiles/[a-zA-Z0-9\-]+\.pdf', r_page.text)
            if not pdf_match:
                continue

            pdf_url = pdf_match.group(0)
            safe_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
            filename = f"{safe_title}.pdf"

            category_folder = library_organizer.get_target_folder(filename)
            dest_dir = os.path.join(library_root, category_folder)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
                _log(f"  ⏭️ موجود بالفعل: {safe_title}")
                continue

            _log(f"📥 جاري تنزيل: {safe_title} -> مجلد /{category_folder} ...")
            if resolve_and_download_pdf(pdf_url, dest_path, log_callback=_log):
                record_downloaded_file(dest_path, filename, category_folder)
                downloaded += 1
                fsize = os.path.getsize(dest_path)
                _log(f"  ✅ تم بنجاح حفظ وفهرسة: {filename} ({fsize:,} بايت)")

        except Exception as e:
            _log(f"⚠️ خطأ أثناء تنزيل {b_url}: {e}")

    _log(f"🎉 اكتملت التغذية من Coptic Reads! أضيف {downloaded} كتاباً جديداً للمكتبة.")
    return downloaded

def sync_coptic_treasures_category(library_root, category_slug="sunday-school-curriculums", max_books=10, log_callback=None):
    """
    Crawls coptic-treasures.com category (e.g. sunday-school-curriculums, sunday-school-service, patrology).
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer

    cat_url = f"https://coptic-treasures.com/category/{category_slug}/"
    _log(f"🌐 الاتصال بمشروع الكنوز القبطية - قسم: {category_slug}...")

    try:
        r = httpx.get(cat_url, headers=HEADERS, follow_redirects=True, timeout=20.0)
        soup = BeautifulSoup(r.text, 'html.parser')
        book_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            txt = a.get_text(strip=True)
            if '/book/' in href and txt and len(txt) > 3:
                if (txt, href) not in book_links:
                    book_links.append((txt, href))
        _log(f"✅ تم العثور على {len(book_links)} كتاباً في هذا القسم.")
    except Exception as e:
        _log(f"❌ تعذر الاتصال بالكنوز القبطية: {e}")
        return 0

    downloaded = 0
    for title, b_url in book_links:
        if downloaded >= max_books:
            break
        try:
            r_book = httpx.get(b_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
            drive_match = re.search(r'https://drive\.google\.com/(?:open|file/d/[^/]+)\?id=([a-zA-Z0-9_\-]+)', r_book.text)
            if not drive_match:
                drive_match = re.search(r'id=([a-zA-Z0-9_\-]{25,})', r_book.text)

            if not drive_match:
                continue

            file_id = drive_match.group(1)
            dl_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"

            safe_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
            filename = f"{safe_title}.pdf"

            category_folder = library_organizer.get_target_folder(filename)
            dest_dir = os.path.join(library_root, category_folder)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
                _log(f"  ⏭️ موجود بالفعل: {safe_title}")
                continue

            _log(f"📥 جاري جلب من Drive: {safe_title} -> /{category_folder} ...")
            if resolve_and_download_pdf(dl_url, dest_path, log_callback=_log):
                record_downloaded_file(dest_path, filename, category_folder)
                downloaded += 1
                fsize = os.path.getsize(dest_path)
                _log(f"  ✅ تم بنجاح حفظ وفهرسة: {filename} ({fsize:,} بايت)")

        except Exception as e:
            _log(f"⚠️ تنبيه أثناء تنزيل {title}: {e}")

    _log(f"🎉 اكتملت التغذية من الكنوز القبطية! أضيف {downloaded} كتاباً.")
    return downloaded

def sync_christianlib_category(library_root, category_slug="التربية-و-الخدمة-تحميل-pdf", max_books=10, log_callback=None):
    """
    Crawls christianlib.com category and downloads books via Mediafire/Direct links.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer

    cat_encoded = urllib.parse.quote(category_slug)
    url = f"https://www.christianlib.com/category/{cat_encoded}/"
    _log(f"🌐 الاتصال بمكتبة الكتب المسيحية ChristianLib - قسم: {category_slug}...")

    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article')
        book_items = []
        for art in articles:
            a = art.find('a', href=True)
            h = art.find(['h2', 'h1', 'h3'])
            if a and h:
                t = h.get_text(strip=True)
                if t and a['href'] not in [x[1] for x in book_items]:
                    book_items.append((t, a['href']))
        _log(f"✅ تم العثور على {len(book_items)} كتاباً في هذا القسم.")
    except Exception as e:
        _log(f"❌ تعذر الاتصال بمكتبة ChristianLib: {e}")
        return 0

    downloaded = 0
    for title, b_url in book_items:
        if downloaded >= max_books:
            break
        try:
            r_page = httpx.get(b_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
            
            # Find download link: Mediafire or Direct PDF
            mf_match = re.search(r'https?://(?:www\.)?mediafire\.com/(?:file_premium|download|file)/[^\s"\'<>]+', r_page.text)
            drive_match = re.search(r'https://drive\.google\.com/(?:open|file/d/[^/]+)\?id=([a-zA-Z0-9_\-]+)', r_page.text)
            
            dl_url = None
            if mf_match:
                dl_url = mf_match.group(0)
            elif drive_match:
                dl_url = f"https://drive.usercontent.google.com/download?id={drive_match.group(1)}&export=download"

            if not dl_url:
                continue

            safe_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
            filename = f"{safe_title}.pdf"

            category_folder = library_organizer.get_target_folder(filename)
            dest_dir = os.path.join(library_root, category_folder)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
                _log(f"  ⏭️ موجود بالفعل: {safe_title}")
                continue

            _log(f"📥 جاري تنزيل من ChristianLib: {safe_title} -> /{category_folder} ...")
            if resolve_and_download_pdf(dl_url, dest_path, log_callback=_log):
                record_downloaded_file(dest_path, filename, category_folder)
                downloaded += 1
                fsize = os.path.getsize(dest_path)
                _log(f"  ✅ تم بنجاح حفظ وفهرسة: {filename} ({fsize:,} بايت)")

        except Exception as e:
            _log(f"⚠️ تنبيه أثناء تنزيل {title}: {e}")

    _log(f"🎉 اكتملت التغذية من ChristianLib! أضيف {downloaded} كتاباً.")
    return downloaded

def download_single_book_url(library_root, book_url, title_hint=None, log_callback=None):
    """Downloads a single book from Coptic-Treasures or ChristianLib or direct URL."""
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer

    safe_title = re.sub(r'[\\/*?:"<>|]', '', title_hint or "كتاب كنسي").strip()
    filename = f"{safe_title}.pdf"

    category_folder = library_organizer.get_target_folder(filename)
    dest_dir = os.path.join(library_root, category_folder)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        _log(f"  ⏭️ موجود بالفعل في المكتبة: {safe_title}")
        return True

    _log(f"🔍 فحص رابط الكتاب: {safe_title} ...")
    try:
        r_page = httpx.get(book_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
        
        # Check Google Drive
        drive_match = re.search(r'https://drive\.google\.com/(?:open|file/d/[^/]+)\?id=([a-zA-Z0-9_\-]+)', r_page.text)
        if not drive_match:
            drive_match = re.search(r'id=([a-zA-Z0-9_\-]{25,})', r_page.text)
            
        # Check Mediafire
        mf_match = re.search(r'https?://(?:www\.)?mediafire\.com/(?:file_premium|download|file)/[^\s"\'<>]+', r_page.text)

        # Check CopticReads CDN
        cdn_match = re.search(r'https://kerolesmas-001-site4\.mtempurl\.com/Uploads/BookFiles/[a-zA-Z0-9\-]+\.pdf', r_page.text)

        dl_url = None
        if drive_match:
            file_id = drive_match.group(1)
            dl_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"
        elif mf_match:
            dl_url = mf_match.group(0)
        elif cdn_match:
            dl_url = cdn_match.group(0)

        if not dl_url:
            _log(f"  ❌ لم يتم العثور على رابط تحميل مباشر لـ: {safe_title}")
            return False

        _log(f"📥 جاري التنزيل المباشر -> /{category_folder} ...")
        if resolve_and_download_pdf(dl_url, dest_path, log_callback=_log):
            record_downloaded_file(dest_path, filename, category_folder)
            fsize = os.path.getsize(dest_path)
            _log(f"  ✅ تم بنجاح حفظ وفهرسة: {filename} ({fsize:,} بايت)")
            return True
        return False
    except Exception as e:
        _log(f"  ❌ خطأ أثناء معالجة الكتاب: {e}")
        return False

def download_curated_pack(library_root, pack_key, log_callback=None):
    """Downloads all books in a pre-curated collection."""
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    if pack_key not in CURATED_PACKS:
        _log(f"❌ باقة غير معروفة: {pack_key}")
        return 0

    pack = CURATED_PACKS[pack_key]
    _log(f"🚀 بدء تنزيل: {pack['title']} ...")
    _log(f"ℹ️ {pack['desc']}")
    
    downloaded = 0
    for title, url in pack['books']:
        success = download_single_book_url(library_root, url, title_hint=title, log_callback=_log)
        if success:
            downloaded += 1

    _log(f"🎉 اكتملت باقة {pack['title']}! تم تنزيل وتسكين {downloaded} كتاباً بنجاح.")
    return downloaded

def search_and_download_online(library_root, query, max_books=10, log_callback=None):
    """
    Unified smart search across ChristianLib and Coptic-Treasures by keyword.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    _log(f"🔎 البحث الشامل عن «{query}» في المستودعات الكنسية...")
    candidates = []

    # 1. Search Coptic Treasures
    try:
        t_url = f"https://coptic-treasures.com/?s={urllib.parse.quote(query)}"
        r = httpx.get(t_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            txt = a.get_text(strip=True)
            if '/book/' in href and txt and len(txt) > 3:
                if (txt, href) not in candidates:
                    candidates.append((txt, href))
        _log(f"  * تم العثور على {len(candidates)} نتيجة في مشروع الكنوز القبطية.")
    except Exception as e:
        _log(f"  * تنبيه الكنوز القبطية: {e}")

    # 2. Search ChristianLib
    try:
        cl_url = f"https://www.christianlib.com/?s={urllib.parse.quote(query)}"
        r = httpx.get(cl_url, headers=HEADERS, follow_redirects=True, timeout=15.0)
        soup = BeautifulSoup(r.text, 'html.parser')
        cl_found = 0
        for art in soup.find_all('article'):
            a = art.find('a', href=True)
            h = art.find(['h2', 'h1', 'h3'])
            if a and h:
                txt = h.get_text(strip=True)
                if txt and (txt, a['href']) not in candidates:
                    candidates.append((txt, a['href']))
                    cl_found += 1
        _log(f"  * تم العثور على {cl_found} نتيجة في مكتبة ChristianLib.")
    except Exception as e:
        _log(f"  * تنبيه ChristianLib: {e}")

    if not candidates:
        _log("⚠️ لم يتم العثور على نتائج للكلمة المحددة.")
        return 0

    downloaded = 0
    for title, url in candidates[:max_books]:
        if download_single_book_url(library_root, url, title_hint=title, log_callback=_log):
            downloaded += 1

    _log(f"🎉 اكتمل البحث والتنزيل! تم تسكين وفهرسة {downloaded} كتاباً بنجاح.")
    return downloaded

def get_awtar_alsama_catalog() -> list:
    """
    Returns list of {'name': author_name, 'url': author_url}
    for all 82 authors in the master index https://library.awtar-alsama.com/1/
    Uses cached JSON file if available, or crawls live.
    """
    cat_path = Path(__file__).parent / "awtar_alsama_catalog.json"
    if cat_path.exists():
        try:
            with open(cat_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass

    # Crawl online fallback
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
            r = client.get("https://library.awtar-alsama.com/1/")
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                content = soup.find("div", class_="entry-content") or soup.find("article")
                if content:
                    catalog = []
                    for a in content.find_all("a", href=True):
                        href = a["href"].strip()
                        txt = a.get_text(separator=" ", strip=True)
                        if "awtar-alsama.com" in href and not any(x in href for x in ["contact", "اتصل-بنا", "category"]):
                            if txt and len(txt) > 2 and "مراسلتنا" not in txt:
                                catalog.append({"name": txt, "url": href})
                    if catalog:
                        try:
                            with open(cat_path, "w", encoding="utf-8") as f:
                                json.dump(catalog, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        return catalog
    except Exception:
        pass
    return []

def cross_reference_candidates_with_local_db(candidates: list, db_path: str = DB_PATH) -> list:
    """
    Intelligently cross-references discovered books with the local 7,424+ library volumes in SQLite.
    Tags each candidate with local ownership status, detecting true gaps vs existing volumes.
    """
    if not candidates or not os.path.exists(db_path):
        return candidates

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for cand in candidates:
            title = cand.get("title", "")
            # Clean title to extract core identifying keywords
            clean = re.sub(r'[\(\)\[\]\{\}\-_،,.]', ' ', title)
            clean = re.sub(r'^(كتاب|سلسلة|تفسير|مقال|دراسة)\s+', '', clean).strip()
            words = [w for w in clean.split() if len(w) > 2 and w not in ["في", "على", "من", "إلى", "عن", "مع", "أو", "أن", "قد", "تم", "هو", "هي"]]
            
            match_found = None
            if words:
                # Query local DB for matching file names
                query = "SELECT file_name, file_path FROM files WHERE " + " AND ".join(["file_name LIKE ?" for _ in words[:3]])
                params = [f"%{w}%" for w in words[:3]]
                cursor.execute(query, params)
                row = cursor.fetchone()
                if row:
                    match_found = row[0]
            
            if match_found:
                cand["local_status"] = "EXISTING"
                cand["local_badge"] = "✅ متوفر لديك بالمكتبة"
                cand["local_file"] = match_found
            else:
                cand["local_status"] = "GAP"
                cand["local_badge"] = "⭐ ثغرة مفقودة بالمكتبة"
                cand["local_file"] = None
        conn.close()
    except Exception:
        pass
    return candidates

def crawl_and_extract_books_from_url(url: str, limit: int = 150, log_callback=None) -> list:
    """
    Crawls an external webpage (such as library.awtar-alsama.com, st-takla, coptic archive)
    and extracts all book items with their direct PDF download links.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer
    from concurrent.futures import ThreadPoolExecutor

    _log(f"🌐 الاتصال بالرابط وفحص محتويات الصفحة: {url} ...")

    # Check if the URL itself is a direct cloud storage book link (Google Drive or Mediafire)
    if any(x in url.lower() for x in ["mediafire.com", "drive.google.com", "drive.usercontent.google.com"]):
        _log("☁️ تم التعرف على رابط كتاب سحابي مباشر (Google Drive / Mediafire). جاري فك الرابط وتجهيزه...")
        direct_pdf = resolve_direct_pdf_url(url)
        clean_title = ""
        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10.0) as client:
                r_meta = client.get(url)
                if r_meta.status_code == 200:
                    s_meta = BeautifulSoup(r_meta.text, "html.parser")
                    raw_t = s_meta.title.string.strip() if s_meta.title else ""
                    clean_title = re.sub(r'(\s*-\s*(MediaFire|Google Drive|Google Docs).*$)', '', raw_t, flags=re.IGNORECASE).strip()
        except Exception:
            pass

        if not clean_title or len(clean_title) < 3 or clean_title.lower() in ["view", "file", "download"]:
            unquoted = urllib.parse.unquote(url.split("/")[-1].replace(".pdf", "").replace("/file", "").strip())
            clean_title = unquoted if len(unquoted) > 2 else "كتاب سحابي كنسي"

        target_folder = library_organizer.get_target_folder(clean_title)
        single_item = [{
            "title": clean_title,
            "source": "سحابة جوجل درايف / ميديا فاير",
            "source_badge": "☁️ تخزين سحابي",
            "page_url": url,
            "download_url": direct_pdf,
            "format": "PDF",
            "target_folder": target_folder,
            "details": "تم فك وتجهيز الرابط السحابي بنجاح"
        }]
        return cross_reference_candidates_with_local_db(single_item)

    results = []
    seen_links = set()

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15.0) as client:
            r = client.get(url)
            if r.status_code != 200:
                _log(f"❌ تعذر الاتصال بالرابط: كود {r.status_code}")
                return []
            soup = BeautifulSoup(r.text, "html.parser")
            page_title = soup.title.string.strip() if soup.title else ""
            _log(f"📄 تم فتح الصفحة: «{page_title}»")

            # 1. Direct PDF links on the page
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                txt = a.get_text(separator=" ", strip=True)
                full_href = urllib.parse.urljoin(url, href)
                if full_href.lower().endswith(".pdf") or ("/wp-content/uploads/" in full_href and ".pdf" in full_href.lower()):
                    if full_href not in seen_links:
                        seen_links.add(full_href)
                        title = txt if (txt and len(txt) > 3 and "تحميل" not in txt and "قراءة" not in txt) else urllib.parse.unquote(full_href.split("/")[-1].replace(".pdf", ""))
                        clean_t = re.sub(r'[\r\n\t]+', ' ', title).strip()
                        target_f = library_organizer.get_target_folder(clean_t + " " + page_title)
                        results.append({
                            "title": clean_t,
                            "source": f"مكتبة ({urllib.parse.urlparse(url).netloc})",
                            "source_badge": "🎶 أوتار السماء" if "awtar-alsama" in url else "🌐 رابط مباشر",
                            "page_url": full_href,
                            "download_url": full_href,
                            "format": "PDF",
                            "target_folder": target_f,
                            "details": "رابط PDF مباشر من الصفحة"
                        })

            # 2. Book Subpages (e.g. /41-xxx/ or /book/ or /post/)
            subpages = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                txt = a.get_text(separator=" ", strip=True)
                full_href = urllib.parse.urljoin(url, href)
                
                is_subpage = False
                if "awtar-alsama.com" in full_href:
                    # Matches book posts like /41-001/, /30-005/, /100-009/, /11320-2/, etc.
                    if re.search(r'/\d+-\d+/?$', full_href):
                        is_subpage = True
                if not is_subpage and any(x in full_href for x in ["/book/", "/item/", "/b-", "/article/"]):
                    is_subpage = True
                elif not is_subpage and (txt.startswith("كتاب ") or "تحميل" in txt or "قراءة" in txt):
                    if len(txt) > 3 and full_href != url and "/category/" not in full_href:
                        is_subpage = True

                if is_subpage and full_href not in seen_links and full_href != url:
                    seen_links.add(full_href)
                    title = txt if txt and len(txt) > 3 else full_href.split("/")[-1]
                    clean_t = re.sub(r'[\r\n\t]+', ' ', title).strip()
                    subpages.append((clean_t, full_href))

            if subpages:
                _log(f"🔎 تم العثور على {len(subpages)} كتاباً في الصفحة، جاري فحص واستخراج روابط الـ PDF بالتوازي...")

                def _resolve_subpage(item):
                    book_title, sp_url = item
                    try:
                        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10.0) as cl:
                            rsp = cl.get(sp_url)
                            s_sp = BeautifulSoup(rsp.text, "html.parser")
                            for a_sp in s_sp.find_all("a", href=True):
                                h_sp = urllib.parse.urljoin(sp_url, a_sp["href"].strip())
                                if h_sp.lower().endswith(".pdf") or ("/wp-content/uploads/" in h_sp and ".pdf" in h_sp.lower()):
                                    return (book_title, sp_url, h_sp)
                                elif any(x in h_sp for x in ["drive.google.com", "mediafire.com"]):
                                    return (book_title, sp_url, h_sp)
                    except Exception:
                        pass
                    return (book_title, sp_url, sp_url)

                with ThreadPoolExecutor(max_workers=10) as executor:
                    resolved_list = list(executor.map(_resolve_subpage, subpages[:limit]))

                for b_title, sp_url, dl_url in resolved_list:
                    target_f = library_organizer.get_target_folder(b_title + " " + page_title)
                    results.append({
                        "title": b_title,
                        "source": f"مكتبة ({urllib.parse.urlparse(url).netloc})",
                        "source_badge": "🎶 أوتار السماء" if "awtar-alsama" in url else "🌐 رابط خارجي",
                        "page_url": sp_url,
                        "download_url": dl_url,
                        "format": "PDF",
                        "target_folder": target_f,
                        "details": "تم استخراج ملف الـ PDF المباشر بنجاح"
                    })

    except Exception as e:
        _log(f"❌ خطأ أثناء فحص الرابط: {e}")

    # Intelligently cross-reference with local 7,424+ books in DB
    results = cross_reference_candidates_with_local_db(results)
    existing_count = sum(1 for r in results if r.get("local_status") == "EXISTING")
    gap_count = len(results) - existing_count
    _log(f"🧠 الفحص الذكي مع مكتبتك: {existing_count} متوفر لديك بالفعل، و {gap_count} ثغرة جديدة.")

    _log(f"✅ اكتمل فحص الرابط! تم استخراج {len(results)} كتاباً ومرجعاً جاهزاً للتنزيل والتسكين.")
    return results

def search_online_candidates(query: str, limit: int = 10, log_callback=None) -> list:
    """
    Searches across authorized Coptic digital archives:
    1. Direct URL Crawling (if query is a link like awtar-alsama or any web page)
    2. Archive.org (Coptic/Christian texts)
    3. ChristianLib (christianlib.com)
    4. Coptic-Treasures (coptic-treasures.com)
    5. Dr. Ghaly Encyclopedia (drghaly.com)
    6. Awtar Al-Sama (library.awtar-alsama.com)
    Returns structured list of candidate books ready for 1-click download.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    from modules import library_organizer

    q_clean = query.strip()
    if not q_clean:
        return []

    # Check if query is an external URL (Web Page Link)
    if q_clean.startswith("http://") or q_clean.startswith("https://"):
        _log(f"🌐 تم رصد رابط صفحة خارجية: {q_clean}")
        return crawl_and_extract_books_from_url(q_clean, limit=limit or 50, log_callback=_log)

    results = []
    seen_titles = set()

    _log(f"🔍 البحث عن كتب ومراجع «{q_clean}» في كبرى المستودعات الكنسية...")

    # 1. Archive.org search
    try:
        q_enc = urllib.parse.quote(q_clean)
        ia_url = f"https://archive.org/advancedsearch.php?q={q_enc}+AND+mediatype:texts&fl[]=identifier,title,creator,year&rows=6&output=json"
        with httpx.Client(headers=HEADERS, timeout=8.0) as client:
            r = client.get(ia_url)
            if r.status_code == 200:
                docs = r.json().get("response", {}).get("docs", [])
                for d in docs:
                    ident = d.get("identifier")
                    raw_title = d.get("title") or ident
                    clean_title = re.sub(r'[\r\n\t]+', ' ', str(raw_title)).strip()
                    if clean_title and clean_title.lower() not in seen_titles:
                        seen_titles.add(clean_title.lower())
                        target_f = library_organizer.get_target_folder(clean_title)
                        results.append({
                            "title": clean_title,
                            "source": "أرشيف الإنترنت (Archive.org)",
                            "source_badge": "🏛️ أرشيف الإنترنت",
                            "page_url": f"https://archive.org/details/{ident}",
                            "download_url": f"https://archive.org/details/{ident}",
                            "format": "PDF",
                            "target_folder": target_f,
                            "details": f"المعرف: {ident}"
                        })
    except Exception as e:
        _log(f"⚠️ تنبيه أرشيف الإنترنت: {e}")

    # 2. ChristianLib search
    try:
        cl_url = f"https://www.christianlib.com/?s={urllib.parse.quote(q_clean)}"
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
            r = client.get(cl_url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for art in soup.find_all("article"):
                    a = art.find("a", href=True)
                    h = art.find(["h2", "h1", "h3"])
                    if a and h:
                        t = h.get_text(separator=" ", strip=True)
                        t_clean = re.sub(r'^كتاب\s+', '', t).strip()
                        if t_clean and t_clean.lower() not in seen_titles:
                            seen_titles.add(t_clean.lower())
                            target_f = library_organizer.get_target_folder(t_clean)
                            results.append({
                                "title": t_clean,
                                "source": "مكتبة الكتب المسيحية (ChristianLib)",
                                "source_badge": "📚 ChristianLib",
                                "page_url": a["href"],
                                "download_url": a["href"],
                                "format": "PDF",
                                "target_folder": target_f,
                                "details": "متاح عبر روابط مباشرة / ميديافاير"
                            })
                            if len(results) >= limit + 4:
                                break
    except Exception as e:
        _log(f"⚠️ تنبيه مكتبة ChristianLib: {e}")

    # 3. Coptic Treasures search (short timeout so it won't block)
    try:
        ct_url = f"https://coptic-treasures.com/?s={urllib.parse.quote(q_clean)}"
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=6.0) as client:
            r = client.get(ct_url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    if "/book/" in a["href"] and len(a.get_text(strip=True)) > 3:
                        t = a.get_text(separator=" ", strip=True)
                        if t and t.lower() not in seen_titles:
                            seen_titles.add(t.lower())
                            target_f = library_organizer.get_target_folder(t)
                            results.append({
                                "title": t,
                                "source": "مشروع الكنوز القبطية (Coptic-Treasures)",
                                "source_badge": "💎 الكنوز القبطية",
                                "page_url": a["href"],
                                "download_url": a["href"],
                                "format": "PDF",
                                "target_folder": target_f,
                                "details": "متاح عبر Google Drive"
                            })
                            if len(results) >= limit + 4:
                                break
    except Exception:
        pass

    # 4. Dr. Ghaly search (for apologetics / biblical questions)
    try:
        from modules import web_intelligence
        ghaly_arts = web_intelligence.DrGhalyEngine.search_articles(q_clean, limit=3)
        for art in ghaly_arts:
            t = art.get("title", "")
            if t and t.lower() not in seen_titles:
                seen_titles.add(t.lower())
                results.append({
                    "title": t,
                    "source": "موسوعة د. غالي (Holy_Bible_1)",
                    "source_badge": "✝️ د. غالي",
                    "page_url": art["url"],
                    "download_url": art["url"],
                    "format": "بحث مرجعي Word",
                    "target_folder": "03 - دراسات لاهوتية وعقائدية/موسوعة أبحاث د. غالي للدفاعيات",
                    "details": "بحث دفاعي موثق"
                })
    except Exception:
        pass

    # 5. Awtar Al-Sama search (library.awtar-alsama.com)
    try:
        as_url = f"https://library.awtar-alsama.com/?s={urllib.parse.quote(q_clean)}"
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
            r = client.get(as_url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    h = a["href"]
                    t = a.get_text(separator=" ", strip=True)
                    if "awtar-alsama.com/" in h and len(t) > 3 and any(w in t for w in ["كتاب", "الأنبا", "الانبا", "القديس", "القمص"]):
                        if t and t.lower() not in seen_titles:
                            seen_titles.add(t.lower())
                            target_f = library_organizer.get_target_folder(t)
                            results.append({
                                "title": t,
                                "source": "مكتبة أوتار السماء (Awtar-AlSama)",
                                "source_badge": "🎶 أوتار السماء",
                                "page_url": h,
                                "download_url": h,
                                "format": "PDF",
                                "target_folder": target_f,
                                "details": "متاح عبر تنزيل مباشر PDF"
                            })
                            if len(results) >= limit + 6:
                                break
    except Exception:
        pass

    # Intelligently cross-reference with local 7,424+ books in DB
    results = cross_reference_candidates_with_local_db(results)
    existing_count = sum(1 for r in results if r.get("local_status") == "EXISTING")
    gap_count = len(results) - existing_count
    _log(f"🧠 الفحص الذكي مع مكتبتك: {existing_count} متوفر لديك بالفعل، و {gap_count} ثغرة جديدة.")

    _log(f"✅ تم العثور على {len(results)} كتاباً ومرجعاً متاحاً للتنزيل والتسكين.")
    return results[:limit]

def download_and_index_candidate(candidate: dict, library_root: str, project_id: int = 1, log_callback=None) -> tuple:
    """
    Downloads a candidate book, places it in the designated canonical library folder,
    and indexes it into the SQLite database.
    Returns (success: bool, dest_path: str, size: int)
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        try:
            print(msg)
        except Exception:
            pass

    title = candidate.get("title", "كتاب كنسي")
    safe_title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
    target_folder = candidate.get("target_folder") or "أبائيات"
    fmt = candidate.get("format", "PDF")
    
    dest_dir = os.path.join(library_root, target_folder)
    os.makedirs(dest_dir, exist_ok=True)

    # 1. Dr. Ghaly article
    if candidate.get("source_badge") == "✝️ د. غالي":
        from modules import web_intelligence
        docx_name = f"بحث_{safe_title}.docx"
        dest_path = os.path.join(dest_dir, docx_name)
        _log(f"📥 جاري جلب وتحويل بحث د. غالي: {safe_title} ...")
        art_data = web_intelligence.DrGhalyEngine.get_article_content(candidate["page_url"])
        content = art_data.get("content", "")
        if not content:
            _log("❌ تعذر قراءة محتوى البحث من الموقع.")
            return False, "", 0
        
        try:
            web_intelligence.save_article_as_docx(safe_title, content, candidate["page_url"], dest_path)
            ok = os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000
        except Exception as docx_err:
            _log(f"❌ خطأ أثناء توليد ملف Word: {docx_err}")
            return False, "", 0
        if ok and os.path.exists(dest_path):
            fsize = os.path.getsize(dest_path)
            try:
                con = get_db_connection()
                cur = con.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO files (root_folder_id, file_path, file_name, extension, size, mod_time, category, ai_status)
                    VALUES (?, ?, ?, '.docx', ?, ?, '📝 أبحاث وWord', 'pending')
                """, (project_id, dest_path, docx_name, fsize, os.path.getmtime(dest_path)))
                con.commit()
                con.close()
            except Exception as ex:
                _log(f"تنبيه فهرسة: {ex}")
            _log(f"✅ تم بنجاح تسكين وفهرسة البحث: {docx_name} ({fsize:,} بايت)")
            return True, dest_path, fsize
        return False, "", 0

    # 2. PDF download
    filename = f"{safe_title}.pdf"
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        _log(f"⏭️ الكتاب موجود بالفعل محلياً: {filename}")
        return True, dest_path, os.path.getsize(dest_path)

    _log(f"📥 جاري تنزيل: {safe_title} -> {target_folder}/ ...")
    
    page_url = candidate.get("page_url", "")
    dl_url = candidate.get("download_url", "")

    if "christianlib.com" in page_url:
        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                r_page = client.get(page_url)
                mf_match = re.search(r'https?://(?:www\.)?mediafire\.com/(?:file_premium|download|file)/[^\s"\'<>]+', r_page.text)
                drive_match = re.search(r'https://drive\.google\.com/(?:open|file/d/[^/]+)\?id=([a-zA-Z0-9_\-]+)', r_page.text)
                if mf_match:
                    dl_url = mf_match.group(0)
                elif drive_match:
                    dl_url = f"https://drive.usercontent.google.com/download?id={drive_match.group(1)}&export=download"
        except Exception as e:
            _log(f"  تنبيه قراءة صفحة الكتاب: {e}")

    elif "coptic-treasures.com" in page_url and "drive" not in dl_url:
        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10.0) as client:
                r_b = client.get(page_url)
                drive_match = re.search(r'id=([a-zA-Z0-9_\-]{25,})', r_b.text)
                if drive_match:
                    dl_url = f"https://drive.usercontent.google.com/download?id={drive_match.group(1)}&export=download"
        except Exception:
            pass

    elif "archive.org/details/" in dl_url:
        dl_url = resolve_direct_pdf_url(dl_url)

    if not dl_url:
        _log("❌ لم يتم العثور على رابط تنزيل مباشر.")
        return False, "", 0

    success = resolve_and_download_pdf(dl_url, dest_path, log_callback=_log)
    if success and os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        fsize = os.path.getsize(dest_path)
        try:
            con = get_db_connection()
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO files (root_folder_id, file_path, file_name, extension, size, mod_time, category, ai_status)
                VALUES (?, ?, ?, '.pdf', ?, ?, '📄 PDF', 'pending')
            """, (project_id, dest_path, filename, fsize, os.path.getmtime(dest_path)))
            con.commit()
            con.close()
        except Exception as ex:
            _log(f"تنبيه فهرسة: {ex}")
        _log(f"✅ تم بنجاح حفظ وفهرسة: {filename} ({fsize:,} بايت)")
        return True, dest_path, fsize
    else:
        _log("❌ تعذر إتمام التنزيل بشكل صالح.")
        return False, "", 0
