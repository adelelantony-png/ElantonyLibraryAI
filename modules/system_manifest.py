# -*- coding: utf-8 -*-
"""
ArchiveMaster - System Manifest & Automated Documentation Engine
ملف مساعد وتوثيق حي للمشروع يُحدّث تلقائياً بعد كل تطوير وفهرسة
Automatically updates PROJECT_SYSTEM_MANIFEST.md with live database stats,
active modules status, repository registry state, and version history.
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = PROJECT_ROOT / "PROJECT_SYSTEM_MANIFEST.md"
DB_PATH = PROJECT_ROOT / "file_archive.db"
REPOS_FILE = Path(__file__).parent / "coptic_repositories.json"


def get_live_system_metrics() -> dict:
    """Gathers real-time statistics from the local database and modules."""
    metrics = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": 0,
        "total_size_gb": 0.0,
        "indexed_content_count": 0,
        "categories_count": 0,
        "active_repos_count": 0,
        "repositories_list": [],
        "version": "2.5.0 (Enterprise Orthodox Edition)",
        "theme": "Soft Slate Eye-Care (الأزرق الإردوازي الهادئ المريح للعين)",
        "offline_ai_status": "Hob Local Bridge & SQLite FTS5 RAG Ready"
    }

    # 1. Database Stats
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='church_books'")
            has_church = cur.fetchone() is not None
            if has_church:
                cur.execute("SELECT COUNT(*), SUM(file_size) FROM church_books")
                row = cur.fetchone()
                if row:
                    metrics["total_files"] = row[0] or 0
                    metrics["total_size_gb"] = round((row[1] or 0) / (1024**3), 2)
                cur.execute("SELECT COUNT(*) FROM church_chunks_fts")
                row_c = cur.fetchone()
                if row_c:
                    metrics["indexed_content_count"] = row_c[0]
                cur.execute("SELECT COUNT(DISTINCT category) FROM church_books")
            else:
                cur.execute("SELECT COUNT(*), SUM(size) FROM files")
                row = cur.fetchone()
                if row:
                    metrics["total_files"] = row[0] or 0
                    metrics["total_size_gb"] = round((row[1] or 0) / (1024**3), 2)
                cur.execute("SELECT COUNT(*) FROM files WHERE content IS NOT NULL AND length(content) > 50")
                row_c = cur.fetchone()
                if row_c:
                    metrics["indexed_content_count"] = row_c[0]
                cur.execute("SELECT COUNT(DISTINCT category) FROM files")
            row_cat = cur.fetchone()
            if row_cat:
                metrics["categories_count"] = row_cat[0]

            conn.close()
        except Exception as e:
            metrics["db_error"] = str(e)

    # 2. Repositories Stats
    if REPOS_FILE.exists():
        try:
            with open(REPOS_FILE, "r", encoding="utf-8") as f:
                repos = json.load(f)
                metrics["active_repos_count"] = len([r for r in repos if r.get("active", True)])
                metrics["repositories_list"] = [f"{r.get('badge', '')} {r.get('name', '')} ({r.get('language_name', '')})" for r in repos]
        except Exception:
            pass

    return metrics


def generate_manifest_content(metrics: dict) -> str:
    """Generates clean GitHub-Flavored Markdown for the project manifest."""
    repos_md = "\n".join([f"- {r}" for r in metrics.get("repositories_list", [])])

    md = f"""# ✠ ملف المساعد والتوثيق الحي الشامل لنظام ArchiveMaster
> **وثيقة معمارية حية للمشروع تُحدّث تلقائياً بعد كل تطوير وفهرسة**  
> **آخر تحديث آلي:** `{metrics['timestamp']}` | **الإصدار الحالي:** `{metrics['version']}`

---

## 1. 📌 هوية وبيانات النظام الحالية (Live System Status)
- **المكتبة المركزية:** `I:\\2021\\2020\\✠ Cross Coptic Library ✠`
- **قاعدة البيانات النشطة:** `file_archive.db` (SQLite WAL Mode فائق السرعة)
- **إجمالي الكتب والملفات المسجلة:** **{metrics['total_files']:,}** مجلداً
- **الحجم الإجمالي الصافي للمكتبة:** **{metrics['total_size_gb']} GB**
- **الكتب المفهرسة نصياً للبحث العميق (FTS5):** **{metrics['indexed_content_count']:,}** كتاباً
- **عدد التصنيفات الكنسية المعتمدة:** **{metrics['categories_count']}** قسماً ولاهوتياً
- **السمة اللونية المعتمدة:** `{metrics['theme']}`
- **حالة الذكاء الاصطناعي الأوفلاين:** `{metrics['offline_ai_status']}`

---

## 2. 🏛️ خريطة الأقطاب التشغيلية الـ 6 الموحدة (The 6 Consolidated Master Hubs)
تم فض تداخل الـ 14 زراً السابقة وتوحيد النظام بالكامل في **6 مراكز قوة رئيسية متكاملة**:

### القطب 1: 🔍 محرك الاستكشاف الشامل 360° (Omnibox & Deep Search)
- **الملف المسؤول:** `modules/omnibox_dialog.py`
- **الوظائف المدمجة:** 
  1. البحث السريع في أسماء المراجع والفهارس.
  2. الفهرسة العميقة لبطون الكتب أوفلاين (Full-Text Search FTS5).
  3. شواهد الكتاب المقدس الـ 73 مع التفاسير الآبائية.
  4. فحص ثغرات الموضوع وتنزيل النواقص تلقائياً.

### القطب 2: 🌐 المركز الاتحادي للمستودعات وحصاد الثغرات الكنسية (Universal Repositories Studio)
- **الملف المسؤول:** `modules/global_repository_studio.py` و `modules/repository_registry.py`
- **الوظائف المدمجة:**
  1. **سجل المستودعات العالمية المفتوح:** يضم الـ 8 مستودعات الأساسية مع إمكانية التوسع لأي موقع.
  2. **زر السحر `[ ➕ إضافة مستودع كنسي ]`:** فاحص ذاتي لأي موقع جديد (WordPress API, Sitemap, HTML).
  3. **الحاصد الآلي لمؤلفي أوتار السماء الـ 82:** مسح تلقائي لمؤلفات كل قديس وتنزيل الثغرات فقط دون تكرار.
  4. **محرك الاستكشاف العابر للغات:** البحث باليونانية، والروسية، والإنجليزية، وتوطين المراجع أوفلاين للأبد.

### القطب 3: 📖 القارئ والمستعرض الكنسي المدمج (In-App Reader & Citations)
- **الملف المسؤول:** `modules/in_app_reader.py`
- **الوظائف المدمجة:**
  1. عرض ملفات PDF والوثائق بدقة عالية 120 DPI مع أدوات التكبير والتنقل.
  2. استخراج نصوص الصفحات لحظياً والبحث الداخلي في محتوى الكتاب.
  3. مولد التوثيق والاقتباس الآبائي بنقرة واحدة: `[كتاب: ...، ص ...]`.

### القطب 4: 🛡️ حصن الإيمان والمساعد اللاهوتي والدفاعي (Apologetics & AI Fortress)
- **الملفات المسؤولة:** `modules/apologetics_hub_dialog.py` و `modules/ai_handler.py` و `modules/hob_manager.py`
- **الوظائف المدمجة:**
  1. استشارة المساعد الكنسي والرد على الشبهات اللاهوتية والتاريخية.
  2. موسوعة أبحاث د. غالي وتفنيد الشبهات النصية والعقائدية.
  3. بديل انقطاع الإنترنت التلقائي: التبديل إلى **Hob / llama.cpp** محلياً أو محرك المعرفة الكنسية الداخلي.

### القطب 5: 🎓 منظومة الرعاية والخدمة والمسرح الكنسي (Pastoral Care, Drama Studio & Sunday School)
- **الملفات المسؤولة:** `modules/church_drama_studio.py` و `modules/pastoral_care_journal.py` و `modules/sunday_school_dialog.py` و `modules/deeptutor_engine.py`
- **الوظائف المدمجة (مستوحاة ومطورة بالاستفادة من منظومة الرعاية والخدمات الكنسية الذكية):**
  1. **ورشة تحضير الدروس والعظات الكنسية:** تحضير كنسي آبائي متكامل يشمل الأهداف، الشرح، التطبيق العملي، وأسئلة المناقشة التفاعلية، مع **سيناريو الإلقاء الشفهي المباشر** الجاهز للإلقاء في الاجتماع.
  2. **أستوديو الاسكتش والمسرحيات الكنسية الهادفة:** تأليف سيناريوهات مسرحية كاملة لمختلف المناسبات والمراحل العمرية، متضمنة الديكور، الإضاءة، المؤثرات الصوتية والألحان القبطية، والتوجيهات الحركية، مع التصدير المنسق إلى Word.
  3. **أكاديمية DeepTutor ومولد المسابقات السقراطية:** توليد مسابقات فهم دقيقة (MCQ وصواب وخطأ) مستندة إلى بطون الكتب المرجعية والبراهين اللاهوتية.
  4. **مفكرة وسجل الافتقاد والرعاية الفردية للأسر:** قاعدة بيانات محلية آمنة لمتابعة مخدومي الفصول والأسر، ومواعيد الاعترافات، وتوليد رسائل تشجيع وافتقاد ذكية للواتساب بنقرة واحدة.

### القطب 6: ⚡ مركز صيانة وترتيب وفهرسة المكتبة (Maintenance & Excel)
- **الملفات المسؤولة:** `modules/library_organizer.py` و `modules/database_handler.py`
- **الوظائف المدمجة:**
  1. تسكين وترتيب الكتب الواردة الجديدة فوراً في مجلداتها الكنسية المخصصة.
  2. إنشاء وتحديث فهرس الإكسيل التفاعلي المربوط بروابط فتح الملفات محلياً.
  3. النسخ الاحتياطي اللحظي لقاعدة البيانات وحمايتها من التلف.

---

## 3. 🌐 شبكة المستودعات الكنسية المعتمدة حالياً ({metrics['active_repos_count']} مستودعاً)
{repos_md}

---

## 4. 📝 سجل التطورات والتحديثات المتسلسلة (Auto-Changelog)
- **v2.5.0 ({metrics['timestamp']}):**
  - **دمج منظومة الرعاية والخدمات الكنسية الذكية:** إضافة أستوديو الاسكتش والمسرحيات الكنسية (`church_drama_studio.py`) ومفكرة وسجل الافتقاد للأسر والمخدومين (`pastoral_care_journal.py`).
  - **سيناريو الإلقاء الشفهي المباشر:** تزويد ورشة تحضير الدروس بنص منبري جاهز للإلقاء المباشر في الاجتماع مع أسئلة المناقشة التفاعلية.
  - **توليد رسائل الافتقاد الذكية للواتساب:** صياغة رسائل تشجيعية دافئة تدعم المخدوم بآيات كتابية بحسب ظروفه الخاصة بنقرة واحدة.
- **v2.4.0:**
  - **فض الاشتباك الشامل:** دمج الـ 14 زراً المشتتة في 6 أقطاب رئيسية بالغة الوضوح والنظام.
  - **أستوديو المستودعات العالمية المفتوحة:** زر السحر لاكتشاف أي موقع، ومحرك التوسيع اللاهوتي العابر للغات (يوناني، روسي، إنجليزي).
  - **محاكي الروابط السحابية:** فك قيود وتحذيرات Google Drive وميديا فاير والتحميل بالتدفق المتدرج.
  - **منظومة الذكاء الأوفلاين 100% (Hob Bridge):** التحويل التلقائي عند انقطاع النت دون رسائل خطأ مع المتابعة الدورية لإصدارات GitHub.
  - **أكاديمية DeepTutor:** توليد مسابقات كنسية متدرجة وتصديرها إلى Word.
  - **إنشاء وتفعيل نظام التوثيق الذاتي:** ملف `PROJECT_SYSTEM_MANIFEST.md` الذي يحدّث بياناته ومؤشراته آلياً.
"""
    return md


def auto_update_manifest() -> str:
    """Updates the PROJECT_SYSTEM_MANIFEST.md file on disk."""
    metrics = get_live_system_metrics()
    content = generate_manifest_content(metrics)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    return str(MANIFEST_FILE)


if __name__ == "__main__":
    path = auto_update_manifest()
    print(f"Successfully generated system manifest at: {path}")
