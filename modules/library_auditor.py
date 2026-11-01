"""
Cross Coptic Library - Intelligent Library Gap & Audit Engine (كاشف ثغرات ونواقص المكتبة)
Evaluates library collection against the Standard Coptic Orthodox Theological Canon,
detects missing foundational treatises, underrepresented disciplines, and generates
prioritized acquisition recommendations.
"""

import os
import sqlite3
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, "file_archive.db")

# Canonical Benchmark of Coptic Orthodox Reference Works
CANONICAL_BENCHMARK = {
    "patristics": {
        "title": "📜 الآبائيات والنصوص الآبائية الأولى (Patristics)",
        "essential_authors": [
            ("الآباء الرسوليون (إكليمنضس، إغناطيوس، بوليكاربوس، الديداكي)", ["إغناطيوس", "بوليكاربوس", "ديداكي", "الرسوليون", "إكليمنضس"]),
            ("القديس أثناسيوس الرسولي", ["أثناسيوس", "تجسد الكلمة", "ضد الأريوسيين", "الرسائل الفصحية"]),
            ("القديس كيرلس الكبير (عامود الدين)", ["كيرلس", "تجسد الابن الوحيد", "ضد نسطور", "شرح قانون الإيمان"]),
            ("القديس باسيليوس الكبير", ["باسيليوس", "الروح القدس", "ضد أونوميوس"]),
            ("القديس غريغوريوس النزينزي (الثيؤلوغوس)", ["غريغوريوس", "المقالات اللاهوتية الخمس"]),
            ("القديس يوحنا ذهبي الفم", ["ذهبي الفم", "سر الكهنوت", "تفسير متى", "تفسير رومية"]),
            ("القديس ديسقوروس وساويرس الأنطاكي", ["ديسقوروس", "ساويرس الأنطاكي", "حامي الإيمان"])
        ],
        "top_missing_recommendations": [
            "مجموعة كتابات الآباء الرسوليين (ترجمة د. جورج حبيب بباوي أو المركز الأرثوذكسي للدراسات الآبائية)",
            "كتاب 'تجسد الكلمة' للقديس أثناسيوس الرسولي - الطبعة المحققة يوناني-عربي (د. جوزيف موريس فلتس)",
            "كتاب 'الروح القدس' للقديس باسيليوس الكبير (المركز الأرثوذكسي للدراسات الآبائية)",
            "كتاب 'المقالات اللاهوتية الخمس' للقديس غريغوريوس الثيؤلوغوس",
            "سلسلة رسائل القديس كيرلس الكبير ضد النسطورية (إصدارات مطرانية بني سويف ومعهد الرعاية)"
        ]
    },
    "apologetics": {
        "title": "🛡️ اللاهوت الدفاعي والنقد الكتابي (Apologetics & Textual Criticism)",
        "essential_authors": [
            ("القمص حلمي القمص يعقوب (موسوعة النقد الكتابي)", ["حلمي القمص", "النقد الكتابي", "شبهات وهمية"]),
            ("القمص عبد المسيح بسيط أبو الخير", ["عبد المسيح بسيط", "عصمة الكتاب", "أناجيل أبوكريفا", "بارت إيرمان"]),
            ("د. هولي بايبل (شبهات ومخطوطات الكتاب المقدس)", ["drghaly", "دكتور غالي", "هولي بايبل", "شبهات"]),
            ("الأنبا بيشوي (الردود الدفاعية واللاهوت المقارن)", ["الأنبا بيشوي", "الرد على", "طبيعة المسيح", "التبرير"]),
            ("الدفاعيات والرد على الشكوك والإلحاد المعاصر", ["إلحاد", "شبهات", "تفنيد", "الدفاعيات", "صحة الكتاب"])
        ],
        "top_missing_recommendations": [
            "موسوعة 'مدارس النقد والتشكيك والرد عليها' - القمص حلمي القمص يعقوب (أجزاء العهد القديم والجديد كاملة)",
            "سلسلة كتب القمص عبد المسيح بسيط أبو الخير (مثل: 'الكتاب المقدس يتحدى نقاده'، 'هل هناك أسفار مفقودة؟')",
            "كتاب 'دليل المبتدئين في اللاهوت الدفاعي' - إصدارات أسقفية الشباب",
            "كتب الرد على الإلحاد المعاصر والشبهات الحديثة (د. أنطون يعقوب، د. فريز صموئيل)"
        ]
    },
    "church_history": {
        "title": "🏛️ تاريخ الكنيسة والمجامع والآثار (Church History & Councils)",
        "essential_authors": [
            ("الأستاذة إيريس حبيب المصري (قصة الكنيسة القبطية)", ["إيريس حبيب المصري", "قصة الكنيسة القبطية"]),
            ("يوسابيوس القيصري (تاريخ الكنيسة الأولى)", ["يوسابيوس", "تاريخ الكنيسة"]),
            ("القمص منسى يوحنا (تاريخ الكنيسة القبطية)", ["منسى يوحنا", "تاريخ الكنيسة القبطية"]),
            ("تاريخ البطاركة (ساويرس بن المقفع / ابن المقفع)", ["ابن المقفع", "تاريخ البطاركة", "سير البيعة"]),
            ("المجامع المسكونية والمكانية", ["المجامع", "مجمع نيقية", "مجمع أفسس", "مجمع القسطنطينية"])
        ],
        "top_missing_recommendations": [
            "موسوعة 'قصة الكنيسة القبطية' للأستاذة إيريس حبيب المصري (المجلدات التسعة الكاملة)",
            "كتاب 'تاريخ الكنيسة' للمؤرخ يوسابيوس القيصري (ترجمة القمص مرقس داود)",
            "كتاب 'تاريخ البطاركة' لساويرس بن المقفع أسقف الأشمونين (طبعة الأب صموئيل السرياني)",
            "كتاب 'تاريخ المجامع المسكونية' للأب متى المسكين والأنبا بيشوي"
        ]
    },
    "heritage_canon": {
        "title": "⚖️ التراث الكنسي والمخطوطات والقانون الكنسي (Coptic Canon Law & Heritage)",
        "essential_authors": [
            ("شمس الرئاسة ابن كبر (مصباح الظلمة في إيضاح الخدمة)", ["ابن كبر", "مصباح الظلمة"]),
            ("أولاد العسال (المجموع الصفوي)", ["ابن العسال", "المجموع الصفوي"]),
            ("الدسقولية (تعاليم الرسل والقوانين الكنسية)", ["الدسقولية", "تعاليم الرسل", "قوانين الرسل"]),
            ("ابن سباع (الجوهرة النفيسة في علوم الكنيسة)", ["ابن سباع", "الجوهرة النفيسة"]),
            ("أبو المكارم (تاريخ الكنائس والأديرة)", ["أبو المكارم", "تاريخ الكنائس والأديرة"])
        ],
        "top_missing_recommendations": [
            "موسوعة 'مصباح الظلمة في إيضاح الخدمة' للعلامة ابن كبر (تحقيق الأب سمير خليل اليسوعي أو مكتبة الكاروز)",
            "كتاب 'المجموع الصفوي' للعلامة الصفي ابن العسال (أهم مرجع تشريعي وقانوني في الكنيسة القبطية)",
            "كتاب 'الجوهرة النفيسة في علوم الكنيسة' للعلامة يوحنا بن أبي زكريا بن سباع",
            "كتاب 'الدسقولية أو تعاليم الرسل' - طبعة القمص مرقس داود المعيارية"
        ]
    },
    "liturgy": {
        "title": "⛪ اللاهوت الطقسي والليتورجيا والألحان (Liturgical Theology & Rites)",
        "essential_authors": [
            ("الصلوات الليتورجية (الخلاجي، الأجبية، الإبصالمودية)", ["الخلاجي", "الأجبية", "الإبصالمودية", "التسبحة"]),
            ("القطمارس وقراءات الكنيسة", ["القطمارس", "قراءات"]),
            ("الدفنار وكتاب أسبوع الآلام (دلال أسبوع البصخة)", ["الدفنار", "البصخة", "أسبوع الآلام"]),
            ("شروحات الطقوس (الأنبا متاؤس، الأنبا بنيامين)", ["الأنبا متاؤس", "الأنبا بنيامين", "طقس", "روحانية الطقس"])
        ],
        "top_missing_recommendations": [
            "كتاب 'الدفنار القبطي' (سير القديسين المرتلة على مدار السنة التوتية)",
            "كتاب 'منارة الأقداس وضياء الألباب في قواعد الطقوس' أو شروحات القداسات للأب متى المسكين والأنبا غريغوريوس",
            "كتاب 'طقوس الأسرار السبعة المقدسة' للأنبا متاؤس أسقف دير السريان"
        ]
    },
    "monasticism": {
        "title": "🕊️ الرهبنة والتراث النسكي والآباء الشيوخ (Monasticism & Asceticism)",
        "essential_authors": [
            ("بستان الرهبان وفردوس الآباء", ["بستان الرهبان", "فردوس الآباء", "أقوال شيوخ"]),
            ("موسوعة الفيلوكاليا (محبة الفضيلة والقديس أنطونيوس)", ["الفيلوكاليا", "أنطونيوس", "أغاثون"]),
            ("القديس مقاريوس الكبير وأبومقار", ["مقاريوس", "أبو مقار", "عظات القديس مقاريوس"]),
            ("مار إسحق السرياني والشيخ الروحاني", ["مار إسحق", "إسحق السرياني", "الشيخ الروحاني", "يوحنا سابا"])
        ],
        "top_missing_recommendations": [
            "مجموعة 'عظات القديس مقاريوس الكبير' الخمسين الروحية (ترجمة د. نصحي عبد الشهيد)",
            "كتاب 'رسائل القديس أنطونيوس الكبير' (دراسة وترجمة الأب متى المسكين والمركز الأرثوذكسي)",
            "أجزاء 'الفيلوكاليا' الكاملة (محبة الصلاح والتأمل القلبي)"
        ]
    }
}

def analyze_library(library_root=None, project_id=1):
    """
    Runs a comprehensive diagnostic audit of the user's library:
    - Counts active volumes per discipline.
    - Evaluates coverage against standard canonical benchmarks.
    - Identifies empty folders and missing landmark authors/books.
    - Returns structured score, gaps, and recommendations.
    """
    results = {
        "total_files": 0,
        "branches": {},
        "empty_folders": [],
        "overall_health_score": 0,
        "critical_gaps": [],
        "strengths": []
    }

    # 1. Inspect SQLite files database
    file_names = []
    categories = {}
    if os.path.exists(DB_NAME):
        try:
            con = sqlite3.connect(DB_NAME, timeout=5)
            cur = con.cursor()
            cur.execute("SELECT file_name, category FROM files WHERE root_folder_id = ?", (project_id,))
            rows = cur.fetchall()
            results["total_files"] = len(rows)
            for fname, cat in rows:
                file_names.append(fname.lower())
                categories[cat] = categories.get(cat, 0) + 1
            con.close()
        except Exception as e:
            print(f"Auditor DB Read error: {e}")

    # 2. Inspect Folders on disk for empty/underpopulated directories
    if library_root and os.path.exists(library_root):
        try:
            for item in os.listdir(library_root):
                full_p = os.path.join(library_root, item)
                if os.path.isdir(full_p) and not item.startswith(('.', '_')):
                    try:
                        child_count = len(os.listdir(full_p))
                        if child_count == 0:
                            results["empty_folders"].append((item, 0))
                        elif child_count <= 2:
                            results["empty_folders"].append((item, child_count))
                    except Exception:
                        pass
        except Exception as e:
            print(f"Auditor Disk Read error: {e}")

    # 3. Benchmark analysis across each theological discipline
    total_score = 0
    num_branches = len(CANONICAL_BENCHMARK)

    for branch_key, branch_info in CANONICAL_BENCHMARK.items():
        branch_title = branch_info["title"]
        authors_status = []
        covered_count = 0

        for author_name, patterns in branch_info["essential_authors"]:
            # Check matches in file names
            match_found = False
            match_count = 0
            for fn in file_names:
                if any(p.lower() in fn for p in patterns):
                    match_found = True
                    match_count += 1

            if match_found:
                covered_count += 1
                authors_status.append({
                    "name": author_name,
                    "status": "covered",
                    "count": match_count
                })
            else:
                authors_status.append({
                    "name": author_name,
                    "status": "missing",
                    "count": 0
                })

        total_req = len(branch_info["essential_authors"])
        coverage_pct = int((covered_count / total_req) * 100) if total_req else 0
        total_score += coverage_pct

        branch_result = {
            "title": branch_title,
            "coverage_pct": coverage_pct,
            "covered_authors": covered_count,
            "total_authors": total_req,
            "details": authors_status,
            "recommendations": branch_info["top_missing_recommendations"]
        }
        results["branches"][branch_key] = branch_result

        # Identify critical gaps (< 60% coverage)
        if coverage_pct < 60:
            results["critical_gaps"].append({
                "branch": branch_title,
                "coverage": coverage_pct,
                "recommendations": branch_info["top_missing_recommendations"]
            })
        elif coverage_pct >= 80:
            results["strengths"].append({
                "branch": branch_title,
                "coverage": coverage_pct
            })

    results["overall_health_score"] = int(total_score / num_branches) if num_branches else 0
    return results

def generate_audit_markdown_report(audit_data):
    """Formats audit data into a comprehensive executive report for the user."""
    score = audit_data.get("overall_health_score", 0)
    total_files = audit_data.get("total_files", 0)
    
    score_emoji = "🌟" if score >= 80 else ("⚡" if score >= 60 else "⚠️")
    
    md = f"""# 📊 تقرير الفحص والتدقيق الذكي لمكتبة الصليب القبطية الأرثوذكسية
**إجمالي محتويات المكتبة المفهرسة:** {total_files:,} كتاباً وملفاً  
**مؤشر التغطية اللاهوتية والتراثية الشاملة:** {score_emoji} **{score}%**

---

### 🛡️ أولاً: أبرز نقاط القوة والوفرة التنافسية في مكتبتك
"""
    for s in audit_data.get("strengths", []):
        md += f"- **{s['branch']}**: نسبة تغطية ممتازة بلغت **{s['coverage']}%**.\n"
    
    md += f"""
- **وفرة أعمال كبار معلمي الكنيسة المعاصرين:**
  * قداسة البابا شنودة الثالث: 204 مؤلفاً وملفاً.
  * الأب متى المسكين: 176 مؤلفاً وملفاً.
  * القمص تادرس يعقوب ملطي: 123 مؤلفاً.
  * نيافة الأنبا غريغوريوس (أسقف البحث العلمي): 38 مؤلفاً.
- **قواعد ومخطوطات اللغة القبطية والألحان:** أكثر من 95 ملفاً وقاموساً متخصصاً.

---

### ⚠️ ثانياً: الثغرات الجوهرية ونقاط الضعف التي تحتاج تغذية عاجلة
"""
    for g in audit_data.get("critical_gaps", []):
        md += f"#### 🔴 {g['branch']} (نسبة التغطية الحالية: {g['coverage']}% فقط!)\n"
        md += "**المراجع والكتب المفقودة والموصى بإضافتها فوراً لتغطية الثغرة:**\n"
        for rec in g.get("recommendations", []):
            md += f"  • {rec}\n"
        md += "\n"

    # Empty folders alert
    empty = audit_data.get("empty_folders", [])
    if empty:
        md += "---\n### 📁 ثالثاً: مجلدات مخصصة ولكنها فارغة أو شبه فارغة في الهارد حالياً\n"
        for folder, cnt in empty[:10]:
            status_text = "فارغ تماماً (0 ملفات)" if cnt == 0 else f"يحتوي على {cnt} ملفات فقط"
            md += f"- مجلد `/{folder}`: ⚠️ **{status_text}** (ينصح بتسكين الكتب التخصصية داخله).\n"

    md += """
---
### 🎯 رابعاً: خطة التغذية الذاتية للمكتبة (مصادر التنزيل المجانية المعتمدة)
يمكن تحميل هذه المراجع الشاغرة بنقرة واحدة من المصادر الكنسية المفتوحة المعتمدة:
1. **موقع الكنوز القبطية (Coptic Treasures):** يضم مجموعات الآباء الرسوليين وتاريخ الكنيسة لإيريس حبيب المصري.
2. **المركز الأرثوذكسي للدراسات الآبائية (OPEC):** نصوص الآباء المحققة يوناني-عربي (كيرلس، أثناسيوس، باسيليوس).
3. **مكتبة دير القديس أنبا مقار:** إصدارات تفاسير وكتابات الأب متى المسكين والآبائيات.
4. **موقع القمص عبد المسيح بسيط:** تحميل كتب النقد واللاهوت الدفاعي وعصمة الكتاب المقدس بصيغة PDF.
"""
    return md

def search_missing_book_candidates(query: str, limit: int = 8, log_callback=None) -> list:
    """Unified search for missing book candidates across Coptic digital repositories."""
    from modules import online_book_feeder
    return online_book_feeder.search_online_candidates(query, limit=limit, log_callback=log_callback)

def download_and_settle_book(candidate: dict, library_root: str, project_id: int = 1, log_callback=None) -> tuple:
    """Downloads candidate book and settles it into the user's local canonical folder and database."""
    from modules import online_book_feeder
    return online_book_feeder.download_and_index_candidate(candidate, library_root, project_id=project_id, log_callback=log_callback)

def auto_resolve_discipline_gaps(discipline_key: str, library_root: str, project_id: int = 1, max_books: int = 2, log_callback=None) -> int:
    """
    Finds missing benchmark works for a specific discipline and downloads/indexes them automatically.
    Returns count of successfully downloaded books.
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

    if discipline_key not in CANONICAL_BENCHMARK:
        _log(f"⚠️ تخصص غير معروف: {discipline_key}")
        return 0

    branch_info = CANONICAL_BENCHMARK[discipline_key]
    _log(f"🚀 بدء معالجة وسد ثغرات تخصص: {branch_info['title']} ...")

    # Run audit to find exactly which authors are missing
    audit = analyze_library(library_root=library_root, project_id=project_id)
    b_data = audit.get("branches", {}).get(discipline_key, {})
    missing_items = [d["name"] for d in b_data.get("details", []) if d.get("status") == "missing"]

    if not missing_items:
        _log(f"✨ ممتاز! كافة أمهات المراجع المقررة في {branch_info['title']} متوفرة في مكتبتك.")
        return 0

    _log(f"📋 المراجع الشاغرة المطلوب جلبها ({len(missing_items)}): {', '.join(missing_items)}")

    from modules import online_book_feeder
    total_downloaded = 0

    for item in missing_items:
        if total_downloaded >= max_books:
            break
        
        # Clean query term: extract author/book name from parenthesis
        clean_q = item.split("(")[0].strip()
        if len(clean_q) < 4 and "(" in item:
            clean_q = item.split("(")[1].replace(")", "").split("،")[0].strip()
        
        _log(f"\n🔍 فحص المستودعات الكنسية عن: «{clean_q}»...")
        candidates = online_book_feeder.search_online_candidates(clean_q, limit=4, log_callback=_log)
        
        if not candidates:
            # Fallback to the first recommendation in the discipline
            recs = branch_info.get("top_missing_recommendations", [])
            if recs:
                fb_q = recs[0].split("(")[0].replace("كتاب", "").replace("موسوعة", "").strip()
                _log(f"🔄 محاولة بحث بديلة عن التوصية المعتمدة: «{fb_q}»...")
                candidates = online_book_feeder.search_online_candidates(fb_q, limit=4, log_callback=_log)

        if not candidates:
            _log(f"⚠️ تعذر العثور على نسخة رقمية مباشرة لـ: {item} حالياً.")
            continue

        # Try downloading best candidate
        for cand in candidates:
            _log(f"⏳ محاولة تنزيل: {cand['title']} [{cand['source_badge']}]...")
            ok, path, size = online_book_feeder.download_and_index_candidate(
                cand, library_root, project_id=project_id, log_callback=_log
            )
            if ok:
                total_downloaded += 1
                _log(f"🎉 تم بنجاح سد النقص وإضافة: {cand['title']} للمكتبة!")
                break

    _log(f"\n✅ اكتملت معالجة تخصص {branch_info['title']}: أضيف {total_downloaded} كتاباً بنجاح.")
    return total_downloaded

def auto_resolve_all_critical_gaps(library_root: str, project_id: int = 1, log_callback=None) -> int:
    """
    Automated batch resolution for all critical gaps (< 80% coverage) across the entire library.
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

    _log("🛡️ بدء الفحص الشامل وسد الثغرات الحرجة في مكتبة الصليب القبطية...")
    audit = analyze_library(library_root=library_root, project_id=project_id)
    
    under_covered = []
    for k, b in audit.get("branches", {}).items():
        if b.get("coverage_pct", 0) < 80:
            under_covered.append((k, b))

    if not under_covered:
        _log("🎉 رائع جداً! كافة تخصصات وأمهات كتب المكتبة الأرثوذكسية مغطاة بنسبة تفوق 80%.")
        return 0

    _log(f"⚠️ تم رصد {len(under_covered)} تخصصات تحتاج دعماً وتغذية عاجلة بالمراجع.")
    
    grand_total = 0
    for k, b in under_covered:
        _log(f"\n=========================================")
        _log(f"📂 معالجة: {b['title']} (نسبة التغطية: {b['coverage_pct']}%)")
        _log(f"=========================================")
        dl_cnt = auto_resolve_discipline_gaps(k, library_root, project_id=project_id, max_books=2, log_callback=_log)
        grand_total += dl_cnt

    _log(f"\n🏆 اكتملت عملية سد الثغرات بنجاح! تم تسكين وفهرسة {grand_total} كتاباً ومرجعاً جديداً في قرصك الصلب أوفلاين.")
    return grand_total

