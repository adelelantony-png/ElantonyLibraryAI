# -*- coding: utf-8 -*-
"""
ArchiveMaster - Sunday School & Church Lesson Builder
محرك إعداد وتحضير دروس ومدارس الأحد والمناهج الكنسية بالذكاء الاصطناعي والمراجع
مطور ومحدث بالاستفادة من منظومة الرعاية والخدمات الكنسية الذكية.
"""

import os
import re
import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from modules import ai_handler
from modules import library_rag

# Curriculum Stages
CURRICULUM_STAGES = {
    "kg": {
        "name": "مرحلة الحضانة والطفولة المبكرة (KG)",
        "tone": "بسيط جداً، قصصي حركي، يركز على محبة الله وأمانه ورعايته عبر الحواس والتشبيهات البسيطة",
        "focus": "قصة قصيرة جذابة، نشاط حركي ملون، تدريب عملي في البيت مع الوالدين"
    },
    "primary_early": {
        "name": "المرحلة الابتدائية الأولى (الصف 1 - 2)",
        "tone": "قصصي مشوق، مفاهيم إيمانية ملموسة، ربط الآية بالسلوك اليومي في المدرسة والبيت",
        "focus": "آية حفظ قصيرة، لعبة فصل تفاعلية، شكر وطاعة ومحبة"
    },
    "primary_late": {
        "name": "المرحلة الابتدائية المتقدمة (الصف 3 - 6)",
        "tone": "قصص كتابية وتاريخية مفصلة، غرس عقائدي مبسط، أبطال الإيمان وسير القديسين والشهداء",
        "focus": "فهم معاني الطقوس والأسرار، مواجهة الغضب والتنمر، الأمانة، حفظ الشواهد"
    },
    "preparatory": {
        "name": "المرحلة الإعدادية (12 - 15 سنة)",
        "tone": "حواري فكري وجداني، بناء الهوية المسيحية، الإجابة عن التساؤلات وبداية الشكوك بحكمة",
        "focus": "إدارة المشاعر، اختيار الأصدقاء، نقاء الفكر والجسد، الانتماء للكنيسة وأسرارها"
    },
    "secondary_youth": {
        "name": "المرحلة الثانوية والجامعية (16+ سنة)",
        "tone": "عميق، لاهوتي دفاعي وحياتي، مناقشة تحديات العصر، الإلحاد، السوشيال ميديا، الفلسفة",
        "focus": "تأصيل لاهوتي آبائي، نقاش مفتوح، ربط الإيمان بالعلم، تدريب خلوة وصلاة يسوع"
    },
    "family": {
        "name": "اجتماع الأسرة والشعب العام",
        "tone": "واقعي يلامس تفاصيل البيوت اليومية، التفاهم الزوجي، وتربية الأبناء بروح الإنجيل",
        "focus": "بناء المذبح العائلي، البركة والسلام البيتي، التوبة والرجاء المستمر"
    }
}

# The 5 Ecclesiastical Pillars (الركائز الكنسية الخمس)
ECCLESIASTICAL_PILLARS = {
    "bible": "📖 دراسة كتابية (أسفار وشخصيات ونبوات العهدين)",
    "dogma_rite": "⛪ عقيدة وطقوس وأسرار كنسية أرثوذكسية",
    "spiritual_life": "🕊️ روحي وحياتي وتدريب سلوكي عملي",
    "patristics_history": "🏛️ تاريخ كنسي وسير آباء وشهداء قبطية",
    "apologetics_ethics": "🛡️ دفاعي وفكري وأخلاقي ومواجهة تحديات العصر"
}

# Service Types
SERVICE_TYPES = {
    "sunday_school": "فصل مدارس الأحد الأسبوعي",
    "youth_meeting": "اجتماع الشباب والفتيان",
    "sermon_liturgy": "عظة قداس إلهي / نهضة روحية",
    "bible_study": "دراسة كتاب مقدس وتأملات آبائية",
    "servants_prep": "إعداد خدام ودراسات لاهوتية تربوية"
}

# Durations
LESSON_DURATIONS = {
    "15": "15 دقيقة (مكثف سريع لمدارس الأحد)",
    "25": "25 دقيقة (درس نموذجي متوازن)",
    "35": "35 دقيقة (اجتماع شباب وفصل فتيان)",
    "45": "45 دقيقة (عظة ودراسة تفصيلية مستفيضة)"
}

# Depth Levels
DEPTH_LEVELS = {
    "simple": "مبسط وقصصي ميسر للصغار",
    "balanced": "متوازن يجمع بين القصة والعمق والتطبيق",
    "deep": "عميق لاهوتياً وتفسيرياً غني بأقوال الآباء الأولين"
}

# Advanced Ecclesiastical Prompt Template
SUNDAY_SCHOOL_PROMPT_TEMPLATE = """
أنت باحث لاهوتي وتربوي قبطي أرثوذكسي خبير في إعداد المناهج ومدارس الأحد وأسقفية الشباب.
مطلوب منك إعداد تحضير درس كنسي نموذجي شامل وموثق وشيق جداً باللغة العربية الفصحى الرصينة.

📌 مواصفات الدرس المطلوبة:
- الفئة المستهدفة: {stage_name}
- التوجه التربوي: {stage_tone}
- الموضوع أو الفكرة الأساسية: {topic}
- الشاهد الكتابي المقترح: {scripture}
- الركيزة الكنسية: {pillar_name}
- نوع اللقاء الكنسي: {service_name}
- مدة اللقاء التقديرية: {duration_text}
- عمق الطرح: {depth_text}

📚 مقتطفات مراجع مسترجعة من مكتبة الكنيسة المحلية:
{rag_context}

🎯 يجب صياغة الدرس وفق البنية الهيكلية النموذجية الإلزامية التالية بدقة واحترافية:

# ✝ عنوان الدرس: {topic} ✝
**الفئة المستهدفة:** {stage_name} | **الركيزة:** {pillar_name} | **نوع اللقاء:** {service_name} | **المدة المقترحة:** {duration_text}

---

### 1. بطاقة تعريف الدرس والأهداف الثلاثية (Lesson ID & Threefold Objectives)
- **الآية الذهبية المشكولة:** «اكتب الآية هنا بالتشكيل الدقيق» [الشاهد: السفر، الأصحاح: الآية]
- **الهدف المعرفي (ماذا سيتعلم المخدوم عقلياً وكتابياً؟):**
- **الهدف الوجداني (بماذا سيشعر المخدوم في قلبه وعلاقته بالله؟):**
- **الهدف السلوكي التطبيقي (ماذا سيمارس المخدوم في سلوكه هذا الأسبوع؟):**

### 2. المدخل التشويقي وسؤال البداية (The Creative Hook & Opening Question)
(سؤال غير تقليدي أو موقف واقعي أو وسيلة حسية تشد انتباه المخدومين فوراً وتكسر الجليد قبل الدخول في الشرح).

### 3. صلب الدرس والشرح المتدرج (Graded Biblical & Patristic Core)
(قسّم الشرح إلى 3 نقاط رئيسية واضحة، واكتب لكل نقطة:
- **عنوان النقطة:**
- **الملخص الفكري:**
- **التفسير والشرح الآبائي الأرثوذكسي:** (استند لتفاسير القمص تادرس يعقوب ملطي، القمص أنطونيوس فكري، وأقوال الآباء: ذهبي الفم، أثناسيوس، كيرلس...).
- **التطبيق الحياتي لهذه النقطة:** كيف تمس حياة الطالب اليوم؟).

### 4. أسئلة المناقشة التفاعلية مع إجابات الخادم (Interactive Q&A for Dialogue)
(اكتب 3 أسئلة حوارية ذكية تفتح نقاشاً ممتعاً مع المخدومين، واكتب أمام كل سؤال:
- **السؤال التفاعلي:**
- **إجابة وتعقيب مقترح للخادم:** كيف يدير الخادم النقاش ويوجهه نحو الفضيلة؟).

### 5. وسيلة الإيضاح أو النشاط التفاعلي داخل الفصل (Object Lesson / Classroom Game)
(فكرة نشاط عملي أو لعبة هادفة بدون أي تكلفة باهظة، ترسخ الفكرة في الأذهان من خلال التجربة والمشاركة).

### 6. التدريب الروحي والتطبيق العملي الأسبوعي (Weekly Spiritual Exercise)
(تدريب يومي ملموس ومحدد يمكن للطالب ممارسته ومتابعته في البيت وصلاته الخاصة، مثل: مزمور يومي، صلاة يسوع، تدريب الصمت، عدم إدانة الآخرين...).

### 7. صلاة ختامية نابعة من فكرة الدرس
(صلاة قصيرة رقيقة من القلب يختم بها الخادم لقاءه مع المخدومين).

### 8. 🎙️ سيناريو الإلقاء الشفهي المباشر (Oral Delivery Script - جاهز للقراءة في الاجتماع)
(نص كلامي متصل ومكتوب بأسلوب المخاطبة المباشرة الحارة والدافئة [جاهز ليقرأه الخادم بصوته أمام المخدومين كلمة بكلمة]؛ يبدأ بترحيب حار وسؤال تشويقي، ويتدرج بأسلوب قصصي شيق، ويصل للخاتمة المؤثرة بثقة وانطلاق، بدون أي ارتباك).

### 9. مراجع وقراءات مقترحة للخادم من المكتبة القبطية
(أسماء كتب وتفاسير من مكتبة الكنيسة القبطية متصلة بالدرس للتعمق والتوسع).
"""


def generate_sunday_school_lesson(
    stage_key="primary_late",
    topic="الأمانة في القليل",
    scripture="",
    pillar_key="bible",
    service_key="sunday_school",
    duration="25",
    depth_key="balanced",
    library_root=None,
    project_id=1
):
    """
    Retrieves local RAG context from the Coptic library and queries AI
    to generate an advanced, fully structured Sunday School lesson.
    """
    stage_info = CURRICULUM_STAGES.get(stage_key, CURRICULUM_STAGES["primary_late"])
    pillar_name = ECCLESIASTICAL_PILLARS.get(pillar_key, ECCLESIASTICAL_PILLARS["bible"])
    service_name = SERVICE_TYPES.get(service_key, SERVICE_TYPES["sunday_school"])
    duration_text = LESSON_DURATIONS.get(str(duration), LESSON_DURATIONS["25"])
    depth_text = DEPTH_LEVELS.get(depth_key, DEPTH_LEVELS["balanced"])

    # 1. Gather RAG context from local church library
    rag_context = ""
    try:
        search_query = f"{topic} {scripture}"
        has_sources, context_text, _ = library_rag.extract_relevant_snippets(
            search_query,
            library_root=library_root,
            project_id=project_id,
            max_total_chars=3500
        )
        if has_sources and context_text:
            rag_context = context_text
    except Exception as e:
        print(f"Lesson RAG warning: {e}")

    if not rag_context:
        rag_context = "مستند إلى تعاليم الكنيسة القبطية الأرثوذكسية وتفاسير الآباء ومناهج المجمع المقدس وأسقفية الشباب."

    # 2. Craft Prompt
    prompt = SUNDAY_SCHOOL_PROMPT_TEMPLATE.format(
        stage_name=stage_info["name"],
        stage_tone=stage_info["tone"],
        topic=topic,
        scripture=scripture or "بحسب مناسبة الموضوع من العهدين",
        pillar_name=pillar_name,
        service_name=service_name,
        duration_text=duration_text,
        depth_text=depth_text,
        rag_context=rag_context
    )

    # 3. Call AI Model
    system_instruction = (
        "أنت خبير تربوي ولاهوتي قبطي أرثوذكسي معتمد، تُعد دروس التربية الكنسية "
        "بأسلوب منهجي شيق وموثق يجمع بين التفسير الآبائي الرصين وسيناريو الإلقاء المنبري الجذاب."
    )
    response = ai_handler.call_ai_routed(prompt, system_instruction=system_instruction)

    # Extract oral script if present
    oral_script = extract_oral_script(response)

    return {
        "stage_key": stage_key,
        "stage_name": stage_info["name"],
        "topic": topic,
        "scripture": scripture,
        "pillar_name": pillar_name,
        "service_name": service_name,
        "duration": duration,
        "content": response,
        "oral_script": oral_script,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }


def extract_oral_script(full_markdown):
    """Extracts Section 8 (سيناريو الإلقاء الشفهي المباشر) from generated markdown."""
    pattern = r"### 8\. [^\n]*\n(.*?)(?=\n### 9\.|\Z)"
    match = re.search(pattern, full_markdown, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def set_paragraph_rtl(paragraph):
    """Helper to enforce proper Arabic RTL orientation in Word document."""
    try:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pPr = paragraph._element.get_or_add_pPr()
        bidi = OxmlElement('w:bidi')
        pPr.append(bidi)
    except Exception:
        pass


def export_lesson_to_docx(lesson_data, output_path):
    """
    Exports the generated lesson data to an enterprise Coptic Church Word (.docx) document.
    """
    doc = Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Header Title Banner
    header_p = doc.add_paragraph()
    set_paragraph_rtl(header_p)
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_cross = header_p.add_run("✠ باسم الآب والابن والروح القدس، الإله الواحد. آمين ✠\n")
    run_cross.font.name = "Segoe UI"
    run_cross.font.size = Pt(13)
    run_cross.font.bold = True
    run_cross.font.color.rgb = RGBColor(180, 83, 9)  # Gold/Amber

    run_title = header_p.add_run(f"تحضير درس: {lesson_data.get('topic', 'درس كنسي')}\n")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(18)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(18, 61, 88)  # Deep Slate Blue

    # Info Box Table
    info_table = doc.add_table(rows=3, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_table.autofit = True

    cells = [
        (0, 0, f"المرحلة: {lesson_data.get('stage_name', '')}"),
        (0, 1, f"الموضوع: {lesson_data.get('topic', '')}"),
        (1, 0, f"الركيزة: {lesson_data.get('pillar_name', 'كتاب مقدس')}"),
        (1, 1, f"نوع اللقاء: {lesson_data.get('service_name', 'مدارس الأحد')}"),
        (2, 0, f"الشاهد: {lesson_data.get('scripture') or 'شواهد كتابية متعددة'}"),
        (2, 1, f"تاريخ التحضير: {lesson_data.get('created_at', '')}")
    ]
    for r, c, val in cells:
        cell = info_table.cell(r, c)
        p = cell.paragraphs[0]
        set_paragraph_rtl(p)
        run = p.add_run(val)
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph()  # Spacer

    # Content Sections
    raw_content = lesson_data.get("content", "")
    lines = raw_content.splitlines()

    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith("# ✝"):
            continue

        p = doc.add_paragraph()
        set_paragraph_rtl(p)

        if line_s.startswith("### ") or line_s.startswith("## "):
            clean_h = re.sub(r'^#+\s*', '', line_s)
            run = p.add_run(clean_h)
            run.font.name = "Arial"
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = RGBColor(18, 61, 88)
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
        elif line_s.startswith("- **") or line_s.startswith("* **"):
            parts = line_s.split("**")
            if len(parts) >= 3:
                r_bullet = p.add_run("• ")
                r_bullet.font.bold = True
                r_bullet.font.color.rgb = RGBColor(25, 125, 128)
                r_bold = p.add_run(parts[1] + ": ")
                r_bold.font.bold = True
                r_bold.font.color.rgb = RGBColor(30, 41, 59)
                r_rest = p.add_run("".join(parts[2:]).lstrip(": "))
                r_rest.font.name = "Arial"
                r_rest.font.size = Pt(11)
            else:
                run = p.add_run(line_s)
                run.font.name = "Arial"
                run.font.size = Pt(11)
        elif line_s.startswith("«") and "»" in line_s:
            # Golden verse highlight
            run = p.add_run(line_s)
            run.font.name = "Arial"
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(180, 83, 9)
        else:
            run_text = p.add_run(line_s)
            run_text.font.name = "Arial"
            run_text.font.size = Pt(11)
            run_text.font.color.rgb = RGBColor(15, 23, 42)
            p.paragraph_format.space_after = Pt(3)

    # Footer note
    footer_p = doc.add_paragraph()
    set_paragraph_rtl(footer_p)
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_p.paragraph_format.space_before = Pt(16)
    run_f = footer_p.add_run("✠ تم تحضير هذا الدرس عبر ورشة التربية الكنسية الذكية بمكتبة الصليب القبطية ✠")
    run_f.font.name = "Arial"
    run_f.font.size = Pt(9)
    run_f.font.italic = True
    run_f.font.color.rgb = RGBColor(148, 163, 184)

    doc.save(output_path)
    return output_path
