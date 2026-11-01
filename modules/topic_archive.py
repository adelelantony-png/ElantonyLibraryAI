"""
Cross Coptic Library - Smart Topic Research Archive & Differential Cache Engine
أرشيف الأبحاث التراكمي الذكي ومحرك التحديث التفاضلي الموفر للتوكنز
Stores every researched topic in a dedicated structured folder, caches full treatises,
and only queries online for newer articles than what is already stored locally to save AI credits.
"""

import os
import re
import json
import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

from modules import database_handler, ai_handler

DEFAULT_ARCHIVE_DIR = r"I:\2021\2020\✠ Cross Coptic Library ✠\أرشيف الأبحاث والدفاعيات"
FALLBACK_ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TopicArchive")

def get_base_archive_dir(library_root: str = None) -> str:
    """Returns the active archive directory, creating it if needed."""
    if library_root and os.path.exists(library_root):
        target = os.path.join(library_root, "أرشيف الأبحاث والدفاعيات")
    elif os.path.exists(r"I:\2021\2020\✠ Cross Coptic Library ✠"):
        target = DEFAULT_ARCHIVE_DIR
    else:
        target = FALLBACK_ARCHIVE_DIR

    try:
        os.makedirs(target, exist_ok=True)
    except Exception as ex:
        print(f"Warning: Could not create archive dir {target}: {ex}, falling back to {FALLBACK_ARCHIVE_DIR}")
        target = FALLBACK_ARCHIVE_DIR
        os.makedirs(target, exist_ok=True)

    return target

def normalize_arabic(text: str) -> str:
    """Normalizes Arabic characters for robust fuzzy search and matching."""
    if not text:
        return ""
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text) # strip tashkeel
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ى]', 'ي', text)
    text = re.sub(r'[ة]', 'ه', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split()).strip().lower()

def stem_arabic_word(word: str) -> str:
    """Removes common Arabic prefixes (ال, وال, فال, كال, بال, لل, و) for fuzzy matching."""
    for prefix in ['وال', 'فال', 'كال', 'بال', 'لل', 'ال']:
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            word = word[len(prefix):]
            break
    if word.startswith('و') and len(word) > 3:
        word = word[1:]
    return word

def slugify_topic(topic: str) -> str:
    """Creates a clean, safe directory name from an Arabic topic."""
    clean = re.sub(r'[^\w\s\u0621-\u064A]', '', topic)
    words = clean.strip().split()[:6]
    slug = "_".join(words)
    return slug if slug else "بحث_دفاعي"

def extract_topic_keywords(text: str) -> list:
    """Extracts significant stemmed keywords for topic matching."""
    norm = normalize_arabic(text)
    stopwords = {
        'هل', 'ما', 'هو', 'هي', 'من', 'عن', 'في', 'علي', 'الي', 'مع', 'هذا', 
        'هذه', 'كيف', 'لماذا', 'اين', 'تم', 'كان', 'تكون', 'ان', 'قد', 'التي',
        'الذي', 'الذين', 'ذلك', 'تلك', 'شبهة', 'حول', 'بين', 'الرد', 'عليها'
    }
    tokens = [stem_arabic_word(w) for w in norm.split() if len(w) >= 3 and w not in stopwords]
    return list(set(tokens))

def find_archived_topic(query: str, library_root: str = None) -> tuple:
    """
    Checks if a topic has already been researched and stored locally.
    Returns: (found: bool, manifest_data: dict, folder_path: str)
    """
    base_dir = get_base_archive_dir(library_root)
    if not os.path.exists(base_dir):
        return False, {}, ""

    query_norm = normalize_arabic(query)
    query_kw = set(extract_topic_keywords(query))

    best_match = None
    best_score = 0.0

    try:
        entries = os.listdir(base_dir)
    except Exception:
        return False, {}, ""

    for entry in entries:
        folder_path = os.path.join(base_dir, entry)
        if not os.path.isdir(folder_path):
            continue

        manifest_file = os.path.join(folder_path, "manifest.json")
        if not os.path.exists(manifest_file):
            continue

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            topic_title = manifest.get("topic", "")
            topic_norm = normalize_arabic(topic_title)
            topic_kw = set(extract_topic_keywords(topic_title))

            # Exact or substring match
            if query_norm in topic_norm or topic_norm in query_norm:
                return True, manifest, folder_path

            # Keyword intersection match
            if query_kw and topic_kw:
                intersection = query_kw.intersection(topic_kw)
                score = len(intersection) / max(len(query_kw), 1)
                if (score >= 0.35 or len(intersection) >= 2) and score > best_score:
                    best_score = score
                    best_match = (manifest, folder_path)
        except Exception as ex:
            print(f"Error reading manifest in {folder_path}: {ex}")

    if best_match and best_score >= 0.35:
        return True, best_match[0], best_match[1]

    return False, {}, ""

def record_token_saving(folder_path: str, tokens: int = 3500):
    """Increments the token savings counter when an archived research is viewed."""
    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.exists(manifest_file):
        return
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["token_savings_count"] = manifest.get("token_savings_count", 0) + 1
        manifest["tokens_saved_estimate"] = manifest.get("tokens_saved_estimate", 0) + tokens
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"Error updating token savings in {folder_path}: {ex}")

def save_researched_topic(topic: str, category: str, treatise_content: str, sources: list = None, library_root: str = None, project_id: int = 1) -> tuple:
    """
    Saves a newly generated defense treatise into a dedicated archive directory.
    Creates manifest.json and a formatted Word (.docx) book, and indexes it into the library DB.
    Returns: (folder_path: str, docx_path: str)
    """
    base_dir = get_base_archive_dir(library_root)
    slug = slugify_topic(topic)
    folder_path = os.path.join(base_dir, slug)
    os.makedirs(folder_path, exist_ok=True)

    docx_filename = f"بحث_شامل_{slug}.docx"
    docx_path = os.path.join(folder_path, docx_filename)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Format Word document
    generate_topic_docx(
        title=topic,
        category=category,
        content=treatise_content,
        sources=sources or [],
        output_path=docx_path,
        created_at=now_str
    )

    # Manifest metadata
    manifest_data = {
        "topic": topic,
        "category": category,
        "slug": slug,
        "created_at": now_str,
        "last_updated": now_str,
        "version": 1,
        "token_savings_count": 0,
        "tokens_saved_estimate": 0,
        "treatise_file": docx_filename,
        "full_treatise_text": treatise_content,
        "sources": sources or [],
        "keywords": extract_topic_keywords(topic)
    }

    manifest_file = os.path.join(folder_path, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    # Automatically index this docx into database_handler
    try:
        index_file_into_database(docx_path, project_id=project_id, category=category, summary=f"بحث دفاعي موثق: {topic}")
    except Exception as ex:
        print(f"Database indexing warning for topic docx: {ex}")

    return folder_path, docx_path

def check_and_update_topic(folder_path: str, new_online_sources: list, library_root: str = None) -> tuple:
    """
    Checks if there are online articles that are NEWER than the stored sources in this topic folder.
    If new articles exist: synthesizes only the additions via AI, updates the docx & manifest.
    If no new articles: returns (False, up-to-date message, existing_text).
    """
    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.exists(manifest_file):
        return False, "تعذر العثور على ملف تعريف الموضوع (manifest.json).", ""

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    existing_urls = {s.get("url", "").strip() for s in manifest.get("sources", []) if s.get("url")}
    existing_ids = {str(s.get("id", "")).strip() for s in manifest.get("sources", []) if s.get("id")}

    # Detect truly new sources
    truly_new_sources = []
    for s in new_online_sources:
        s_url = s.get("url", "").strip()
        s_id = str(s.get("id", "")).strip()
        if (s_url and s_url in existing_urls) or (s_id and s_id in existing_ids):
            continue
        truly_new_sources.append(s)

    if not truly_new_sources:
        return (
            False,
            "✅ الأرشيف المحلي لهذا الموضوع محدث تماماً ولا توجد مراجع جديدة منشورة أحدث من المسجلة لديك! لم يتم استهلاك أي نقاط ذكاء اصطناعي.",
            manifest.get("full_treatise_text", "")
        )

    # Synthesize incremental content only
    topic = manifest.get("topic", "")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    new_sources_summary = "\n\n".join([
        f"- العنوان: {s.get('title')}\n  الرابط: {s.get('url')}\n  المقتطف: {s.get('snippet', '')[:800]}"
        for s in truly_new_sources
    ])

    prompt = (
        f"أنت عالم لاهوت ومدافع قبطي أرثوذكسي رصين.\n"
        f"لدينا بحث قائم مسبقاً في أرشيف مكتبتنا حول موضوع: '{topic}'.\n"
        f"ظهرت مؤخراً المراجع والدراسات الحديثة التالية التي لم تكن مسجلة لدينا:\n"
        f"{new_sources_summary}\n\n"
        f"قم بصياغة ملحق إضافي مركز ودقيق يوضح:\n"
        f"1. ما أضافته هذه الأبحاث الجديدة إلى الموضوع.\n"
        f"2. البراهين العلمية أو الآثارية أو النصية الإضافية المستخلصة منها.\n"
        f"3. توثيق الشواهد مع الحفاظ الكامل على العقيدة الأرثوذكسية."
    )

    try:
        incremental_addition = ai_handler.call_ai_routed(
            prompt,
            system_instruction="أنت مدافع لاهوتي قبطي أرثوذكسي تلخص الإضافات والمستجدات العلمية واللاهوتية بدقة بالغة."
        )
    except Exception as ex:
        incremental_addition = f"تعذر استدعاء الذكاء الاصطناعي لتلخيص الإضافات: {ex}\n\nالمراجع المكتشفة حديثاً:\n{new_sources_summary}"

    appendix_block = (
        f"\n\n{'═'*55}\n"
        f"### 🔄 ملحق التحديثات والأبحاث المستجدة (تاريخ الإضافة: {today_str})\n"
        f"═══════════════════════════════════════════════════════\n"
        f"{incremental_addition}\n"
    )

    updated_full_text = manifest.get("full_treatise_text", "") + appendix_block
    manifest["full_treatise_text"] = updated_full_text
    manifest["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manifest["version"] = manifest.get("version", 1) + 1
    manifest["sources"].extend(truly_new_sources)

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Update Word Document
    docx_file = os.path.join(folder_path, manifest.get("treatise_file", f"بحث_شامل_{manifest.get('slug', 'بحث')}.docx"))
    generate_topic_docx(
        title=topic,
        category=manifest.get("category", "دفاعيات"),
        content=updated_full_text,
        sources=manifest.get("sources", []),
        output_path=docx_file,
        created_at=manifest.get("created_at", today_str)
    )

    return (
        True,
        f"🎉 تم اكتشاف {len(truly_new_sources)} مراجع جديدة وتحديث أرشيف الموضوع بنجاح وتسكينها في ملف Word!",
        updated_full_text
    )

def list_all_archived_topics(library_root: str = None) -> list:
    """Returns a list of summary dicts for all topics currently in the archive."""
    base_dir = get_base_archive_dir(library_root)
    if not os.path.exists(base_dir):
        return []

    topics = []
    try:
        entries = os.listdir(base_dir)
    except Exception:
        return []

    for entry in entries:
        folder_path = os.path.join(base_dir, entry)
        if not os.path.isdir(folder_path):
            continue

        manifest_file = os.path.join(folder_path, "manifest.json")
        if not os.path.exists(manifest_file):
            continue

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["folder_path"] = folder_path
            data["docx_full_path"] = os.path.join(folder_path, data.get("treatise_file", ""))
            topics.append(data)
        except Exception:
            pass

    # Sort descending by last updated
    topics.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
    return topics

def generate_topic_docx(title: str, category: str, content: str, sources: list, output_path: str, created_at: str):
    """Creates a beautifully formatted Coptic Orthodox Word treatise."""
    doc = Document()

    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    def set_rtl(p):
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pPr = p._element.get_or_add_pPr()
        if pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bidi') is None:
            pPr.append(OxmlElement('w:bidi'))

    # Header
    p_cross = doc.add_paragraph()
    set_rtl(p_cross)
    p_cross.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cross = p_cross.add_run("✠ مكتبة الصليب القبطية الأرثوذكسية ✠\nأرشيف الأبحاث اللاهوتية وتفنيد الشبهات المعاصرة")
    r_cross.font.size = Pt(13)
    r_cross.font.bold = True
    r_cross.font.color.rgb = RGBColor(197, 160, 89) # Gold

    # Title
    p_title = doc.add_paragraph()
    set_rtl(p_title)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(f"\n{title}\n")
    r_title.font.size = Pt(17)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    # Metadata
    p_meta = doc.add_paragraph()
    set_rtl(p_meta)
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run(
        f"التصنيف: {category}  |  تاريخ التوثيق: {created_at}\n"
        f"موثق ومحفوظ في أرشيف المكتبة الدائم (أوفلاين)\n"
        f"{'─'*55}\n"
    )
    r_meta.font.size = Pt(10)
    r_meta.font.italic = True
    r_meta.font.color.rgb = RGBColor(100, 116, 139)

    # Content paragraphs
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        p = doc.add_paragraph()
        set_rtl(p)
        if stripped.startswith('###') or stripped.startswith('##') or stripped.startswith('#'):
            clean_head = re.sub(r'^#+\s*', '', stripped)
            r = p.add_run(clean_head)
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 58, 138)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            clean_bullet = stripped[2:].strip()
            r = p.add_run(f"• {clean_bullet}")
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(30, 41, 59)
        elif stripped.startswith('═══') or stripped.startswith('───'):
            r = p.add_run(stripped)
            r.font.size = Pt(10)
            r.font.color.rgb = RGBColor(148, 163, 184)
        else:
            r = p.add_run(stripped)
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(30, 41, 59)

    # Sources bibliography section
    if sources:
        doc.add_paragraph()
        p_src_h = doc.add_paragraph()
        set_rtl(p_src_h)
        r_sh = p_src_h.add_run("📚 فهرس المراجع والأبحاث المرتبطة:")
        r_sh.font.size = Pt(12)
        r_sh.font.bold = True
        r_sh.font.color.rgb = RGBColor(197, 160, 89)

        for src in sources:
            p_s = doc.add_paragraph()
            set_rtl(p_s)
            s_title = src.get("title", "مرجع")
            s_url = src.get("url", "")
            r_s = p_s.add_run(f"• {s_title} ({s_url})")
            r_s.font.size = Pt(9.5)
            r_s.font.color.rgb = RGBColor(71, 85, 105)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    return output_path

def index_file_into_database(file_path: str, project_id: int = 1, category: str = "دفاعيات", summary: str = ""):
    """Inserts a generated topic docx file into the database so it becomes instantly searchable."""
    if not os.path.exists(file_path):
        return

    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_name)[1].lower()
    stat = os.stat(file_path)
    size = stat.st_size
    mod_time = stat.st_mtime

    # Ensure valid root_folder_id exists to satisfy foreign key constraint
    rf_id = project_id
    try:
        con = database_handler.get_connection()
        cur = con.cursor()
        cur.execute("SELECT id FROM root_folders WHERE id = ?", (project_id,))
        if not cur.fetchone():
            cur.execute("SELECT id FROM root_folders LIMIT 1")
            first_rf = cur.fetchone()
            if first_rf:
                rf_id = first_rf[0]
            else:
                archive_root = os.path.dirname(os.path.dirname(os.path.abspath(file_path)))
                cur.execute("INSERT OR IGNORE INTO root_folders (folder_path) VALUES (?)", (archive_root,))
                con.commit()
                cur.execute("SELECT id FROM root_folders WHERE folder_path = ?", (archive_root,))
                row = cur.fetchone()
                rf_id = row[0] if row else 1
        con.close()
    except Exception as ex_rf:
        print(f"Warning resolving root_folder_id: {ex_rf}")
        rf_id = 1

    file_data = [(
        rf_id,
        os.path.abspath(file_path),
        file_name,
        ext,
        size,
        mod_time,
        category,
        summary
    )]
    database_handler.process_file_batch(file_data, is_update=False)

def toggle_watchlist_topic(folder_path: str) -> bool:
    """Toggles the watchlist (star) status of an archived topic."""
    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.exists(manifest_file):
        return False
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        current = manifest.get("watchlist", False)
        manifest["watchlist"] = not current
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        return manifest["watchlist"]
    except Exception as ex:
        print(f"Error toggling watchlist in {folder_path}: {ex}")
        return False

def scan_all_watchlist_topics(library_root: str = None) -> list:
    """Scans all topics marked with watchlist=True for online updates."""
    from modules import web_intelligence
    all_topics = list_all_archived_topics(library_root)
    updated_topics = []

    for t in all_topics:
        if not t.get("watchlist", False):
            continue
        folder_path = t.get("folder_path")
        topic_name = t.get("topic")

        # Quick check drghaly
        try:
            g_arts = web_intelligence.DrGhalyEngine.search_articles(topic_name, limit=3)
            known_urls = {s.get("url", "").strip() for s in t.get("sources", []) if s.get("url")}
            new_found = [a for a in g_arts if a.get("url", "").strip() not in known_urls]
            if new_found:
                updated_topics.append({
                    "topic": topic_name,
                    "folder_path": folder_path,
                    "new_count": len(new_found),
                    "new_articles": new_found
                })
        except Exception:
            pass

    return updated_topics

def generate_mind_map_data(topic: str, treatise_content: str) -> dict:
    """
    Generates a structured hierarchical knowledge tree (Mind Map) for the topic.
    Returns: dict with 'root' and 'branches'
    """
    prompt = (
        f"أنت عالم لاهوت وتخطيط معرفي قبطي أرثوذكسي.\n"
        f"مطلوب بناء خريطة ذهنية دلالية شجرية (Semantic Mind Map) للموضوع التالي: '{topic}'.\n\n"
        f"قم باستخراج 5 إلى 6 فروع معرفية رئيسية متفرعة من صلب هذا الموضوع "
        f"(مثل: البعد الجيولوجي/العلمي، البعد الأثري والحضاري، البعد الكتابي والتفسيري، البعد المنطقي، البعد الآبائي والرمزي، والتطبيقات الروحية المعاصرة).\n\n"
        f"اكتب النتيجة بصيغة JSON حصراً بالشكل التالي دون أي نص إضافي:\n"
        f"{{\n"
        f'  "root": "{topic}",\n'
        f'  "branches": [\n'
        f'    {{"name": "اسم الفرع الرئيسي", "summary": "موجز في سطر واحد لما يتناوله هذا الفرع", "sub_topics": ["نقطة 1", "نقطة 2"]}}\n'
        f'  ]\n'
        f"}}"
    )

    try:
        raw_res = ai_handler.call_ai_routed(
            prompt,
            system_instruction="أنت خبير رسم خرائط معرفية تخرج النتائج بصيغة JSON النقية فقط."
        )
        # Parse JSON
        clean_json = re.sub(r'```json\s*', '', raw_res)
        clean_json = re.sub(r'```\s*', '', clean_json).strip()
        data = json.loads(clean_json)
        return data
    except Exception as ex:
        # Fallback Mind Map structure
        return {
            "root": topic,
            "branches": [
                {"name": "🔬 براهين العلم والآثار المحايدة", "summary": "شهادات العلماء ومقتنيات المتاحف العالمية والمؤرخين القدامى", "sub_topics": ["المكتشفات الأثرية", "قوانين العلوم الطبيعية"]},
                {"name": "📖 التحقيق الكتابي والتفسيري", "summary": "سياق النصوص وشواهد العهدين القديم والجديد", "sub_topics": ["شواهد العهد القديم", "إنجيل ربنا يسوع المسيح"]},
                {"name": "💡 البرهان العقلي والمنطقي", "summary": "تفنيد الشبهة بالمنطق والفلسفة المعاصرة", "sub_topics": ["تفكيك المغالطة", "التماسك العقلاني"]},
                {"name": "⛪ إجماع الآباء والتقليد", "summary": "أقوال القديسين أثناسيوس وذهبي الفم وكيرلس الكبير", "sub_topics": ["كتابات الآباء", "الليتورجيا القبطية"]}
            ]
        }

def generate_debate_matrix(topic: str, treatise_content: str) -> list:
    """
    Synthesizes a structured Quick-Answer Debate Matrix (Cheat Sheet) for servants.
    Returns: list of dicts with objection, refutation, scripture, science, patristic.
    """
    prompt = (
        f"أنت عالم لاهوت ومدافع قبطي أرثوذكسي.\n"
        f"قم بصياغة 'مصفوفة ردود سريعة ومقارنة جدلية' (Debate & Quick-Answer Matrix) "
        f"حول موضوع: '{topic}' لتكون دليلاً وموجزاً مكثفاً للخدام والشباب.\n\n"
        f"اكتب النتيجة بصيغة JSON حصراً عبارة عن قائمة كائنات (Array of objects) بالشكل التالي دون أي مقدمات:\n"
        f"[\n"
        f"  {{\n"
        f'    "objection": "نص الشبهة أو الادعاء المشكك",\n'
        f'    "refutation": "الرد الأرثوذكسي المكثف في سطرين حاسمين",\n'
        f'    "scripture": "الشاهد الكتابي الدقيق",\n'
        f'    "science": "دليل العلم المحايد أو الآثار والمؤرخين",\n'
        f'    "patristic": "قول الأب القديس المعتمد"\n'
        f"  }}\n"
        f"]"
    )

    try:
        raw_res = ai_handler.call_ai_routed(
            prompt,
            system_instruction="أنت مدافع قبطي أرثوذكسي خبير في صياغة الردود المكثفة يخرج النتائج بصيغة JSON فقط."
        )
        clean_json = re.sub(r'```json\s*', '', raw_res)
        clean_json = re.sub(r'```\s*', '', clean_json).strip()
        data = json.loads(clean_json)
        return data
    except Exception:
        return [
            {
                "objection": f"ادعاء الشبهة حول {topic}",
                "refutation": "الموقف الأرثوذكسي الراسخ المستند إلى كمال إعلان الوحي الإلهي والتقليد الكنسي المسلم.",
                "scripture": "شواهد الكتاب المقدس والعهد الجديد",
                "science": "شهادات التاريخ والآثار المحايدة",
                "patristic": "إجماع آباء الكنيسة الجامعة"
            }
        ]

def save_pptx_for_topic(folder_path: str) -> str:
    """Generates and saves a PowerPoint presentation (.pptx) inside the topic folder."""
    from modules import presentation_generator

    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.exists(manifest_file):
        raise FileNotFoundError("تعذر العثور على ملف تعريف الموضوع (manifest.json).")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    topic = manifest.get("topic", "بحث_دفاعي")
    category = manifest.get("category", "دفاعيات")
    content = manifest.get("full_treatise_text", "")
    sources = manifest.get("sources", [])
    slug = manifest.get("slug", "بحث")

    pptx_filename = f"عرض_تقديمي_{slug}.pptx"
    pptx_path = os.path.join(folder_path, pptx_filename)

    presentation_generator.create_slide_deck(
        topic_title=topic,
        category=category,
        content=content,
        sources=sources,
        output_path=pptx_path
    )

    # Save to manifest
    manifest["pptx_file"] = pptx_filename
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return pptx_path

def save_audio_for_topic(folder_path: str) -> str:
    """Generates and saves an MP3 audio briefing inside the topic folder."""
    from modules import audio_briefing

    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.exists(manifest_file):
        raise FileNotFoundError("تعذر العثور على ملف تعريف الموضوع (manifest.json).")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    topic = manifest.get("topic", "بحث_دفاعي")
    content = manifest.get("full_treatise_text", "")
    slug = manifest.get("slug", "بحث")

    mp3_filename = f"ملخص_صوتي_{slug}.mp3"
    mp3_path = os.path.join(folder_path, mp3_filename)

    audio_briefing.generate_audio_briefing(
        topic=topic,
        treatise_content=content,
        output_path=mp3_path
    )

    # Save to manifest
    manifest["audio_file"] = mp3_filename
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return mp3_path
