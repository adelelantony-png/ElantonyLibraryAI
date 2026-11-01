"""
Cross Coptic Library - Presentation Generator
مولد العروض التقديمية الاحترافية (PowerPoint .pptx)
Generates 16:9 widescreen dark gold/slate Coptic Orthodox presentation slide decks
from apologetics research and topic treatises for conferences, seminars, and Sunday school.
"""

import os
import re
import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Coptic Orthodox Color Palette
COLOR_BG_DARK = RGBColor(15, 23, 42)       # #0F172A
COLOR_CARD_BG = RGBColor(30, 41, 59)       # #1E293B
COLOR_GOLD = RGBColor(212, 175, 55)        # #D4AF37
COLOR_LIGHT_GOLD = RGBColor(245, 222, 137) # #F5DE89
COLOR_WHITE = RGBColor(248, 250, 252)      # #F8FAFC
COLOR_SLATE_TEXT = RGBColor(203, 213, 225) # #CBD5E1
COLOR_BLUE_ACCENT = RGBColor(37, 99, 235)  # #2563EB
COLOR_EMERALD = RGBColor(16, 185, 129)     # #10B981

def create_slide_deck(topic_title: str, category: str, content: str, sources: list = None, output_path: str = None) -> str:
    """
    Builds an 8-slide widescreen PowerPoint presentation for the topic.
    Returns the path to the saved .pptx file.
    """
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # Blank slide

    sections = parse_treatise_sections(content)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # Slide 1: Cover Slide
    add_cover_slide(prs, blank_layout, topic_title, category, today_str)

    # Slide 2: The Core Objection (صلب الشبهة)
    add_content_slide(
        prs, blank_layout,
        title="1. صلب الشبهة ومنشؤها وخلفيتها",
        subtitle="The Core Objection & Historical Background",
        points=sections.get("objection", ["بيان الفكرة المشككة وتفكيك منطلقاتها الفلسفية والتاريخية."]),
        badge_text="🎯 تفكيك الشبهة",
        badge_color=RGBColor(220, 38, 38)
    )

    # Slide 3: Neutral Science & Archaeology (رأي العلم والمؤرخين المحايدين)
    add_content_slide(
        prs, blank_layout,
        title="2. رأي العلم والمؤرخين والآثار المحايدة",
        subtitle="Secular Scientists, Roman Historians & Global Museums",
        points=sections.get("science", ["شهادات المؤرخين الرومان واليهود ومقتنيات المتاحف العالمية وقوانين العلوم الطبيعية."]),
        badge_text="🔬 أدلة محايدة",
        badge_color=COLOR_EMERALD
    )

    # Slide 4: Biblical Proofs (التحقيق الكتابي والتفسيري)
    add_content_slide(
        prs, blank_layout,
        title="3. التحقيق الكتابي والشواهد التفسيرية",
        subtitle="Biblical Evidence, Textual Context & Scripture Proofs",
        points=sections.get("biblical", ["الشواهد الإنجيلية والعهد القديم مع الرد على اجتزاء النصوص من سياقها الأصلي."]),
        badge_text="📖 كلمة الله",
        badge_color=COLOR_BLUE_ACCENT
    )

    # Slide 5: Rational & Logical Refutation (البرهان العقلي والمنطقي)
    add_content_slide(
        prs, blank_layout,
        title="4. البرهان العقلي والمنطقي والفلسفي",
        subtitle="Logical Refutation & Philosophical Coherence",
        points=sections.get("logical", ["تفنيد الشبهة بالعقل السليم والبراهين المنطقية المعاصرة بما يناسب شباب العصر."]),
        badge_text="💡 البراهين العقلية",
        badge_color=COLOR_GOLD
    )

    # Slide 6: Patristic Consensus (إجماع آباء الكنيسة)
    add_content_slide(
        prs, blank_layout,
        title="5. إجماع آباء الكنيسة وسياق التقليد الأرثوذكسي",
        subtitle="Patristic Consensus & Holy Apostolic Tradition",
        points=sections.get("patristic", ["أقوال القديسين: أثناسيوس، كيرلس الكبير، ذهبي الفم، أغسطينوس، وباسيليوس."]),
        badge_text="⛪ تقليد الآباء",
        badge_color=RGBColor(168, 85, 247)
    )

    # Slide 7: Comparison & Quick Summary Table
    add_summary_slide(prs, blank_layout, topic_title, sections)

    # Slide 8: Key References & Conclusion
    add_references_slide(prs, blank_layout, topic_title, sources or [], sections.get("references", []))

    if not output_path:
        clean_slug = re.sub(r'[^\w\s\u0621-\u064A]', '', topic_title).strip().replace(" ", "_")[:30]
        output_path = f"عرض_{clean_slug}.pptx"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    prs.save(output_path)
    return output_path

def parse_treatise_sections(content: str) -> dict:
    """Extracts bullet points from treatise markdown headers."""
    sections = {
        "objection": [],
        "science": [],
        "biblical": [],
        "logical": [],
        "patristic": [],
        "references": []
    }
    current_key = None

    for line in content.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        if "1. صلب الشبهة" in line_s or "منشؤها" in line_s:
            current_key = "objection"
        elif "2. رأي العلم" in line_s or "المحايد" in line_s or "الآثار" in line_s:
            current_key = "science"
        elif "3. التحقيق الكتابي" in line_s or "التفسيري" in line_s:
            current_key = "biblical"
        elif "4. البرهان العقلي" in line_s or "المنطقي" in line_s:
            current_key = "logical"
        elif "5. إجماع آباء" in line_s or "التقليد" in line_s:
            current_key = "patristic"
        elif "6. مراجع" in line_s or "للتعمق" in line_s:
            current_key = "references"
        elif line_s.startswith("### ") or line_s.startswith("## "):
            current_key = None
        else:
            if current_key and len(line_s) > 10:
                clean_text = line_s.lstrip("-*•🔹 \t")
                if len(sections[current_key]) < 4:
                    sections[current_key].append(clean_text)

    return sections

def set_slide_background(slide):
    """Sets background color of slide to dark slate."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG_DARK

def add_cover_slide(prs, layout, topic_title: str, category: str, date_str: str):
    slide = prs.slides.add_slide(layout)
    set_slide_background(slide)

    # Decorative Cross Banner Header
    shape_header = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.73), Inches(0.6))
    shape_header.fill.solid()
    shape_header.fill.fore_color.rgb = COLOR_CARD_BG
    shape_header.line.color.rgb = COLOR_GOLD
    p_h = shape_header.text_frame.paragraphs[0]
    p_h.text = "✠ مكتبة الصليب القبطية الأرثوذكسية  •  منصة الدفاعيات وحصن الإيمان ✠"
    p_h.font.size = Pt(13)
    p_h.font.bold = True
    p_h.font.color.rgb = COLOR_GOLD
    p_h.alignment = PP_ALIGN.CENTER

    # Main Title Card
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.0), Inches(10.93), Inches(3.6))
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_CARD_BG
    card.line.color.rgb = COLOR_GOLD
    card.line.width = Pt(1.5)

    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    p_badge = tf.paragraphs[0]
    p_badge.text = f"🎯 دراسة لاهوتية ودفاعية موثقة  |  القسم: {category}"
    p_badge.font.size = Pt(14)
    p_badge.font.bold = True
    p_badge.font.color.rgb = COLOR_EMERALD
    p_badge.alignment = PP_ALIGN.CENTER

    p_t = tf.add_paragraph()
    p_t.text = f"\n{topic_title}\n"
    p_t.font.size = Pt(28)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_WHITE
    p_t.alignment = PP_ALIGN.CENTER

    p_sub = tf.add_paragraph()
    p_sub.text = "تفنيد شامل بالـ 6 أركان: الكتاب المقدس، العلم المحايد، المنطق العقلي، وإجماع الآباء"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = COLOR_SLATE_TEXT
    p_sub.alignment = PP_ALIGN.CENTER

    # Footer Info
    tx_box = slide.shapes.add_textbox(Inches(1.2), Inches(6.0), Inches(10.93), Inches(0.8))
    p_f = tx_box.text_frame.paragraphs[0]
    p_f.text = f"📅 تاريخ التوثيق والعرض: {date_str}   •   مُعد للخدمة والخدام ومؤتمرات الشباب"
    p_f.font.size = Pt(11)
    p_f.font.color.rgb = COLOR_SLATE_TEXT
    p_f.alignment = PP_ALIGN.CENTER

def add_content_slide(prs, layout, title: str, subtitle: str, points: list, badge_text: str, badge_color):
    slide = prs.slides.add_slide(layout)
    set_slide_background(slide)

    # Top Header Box
    head_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.6), Inches(11.73), Inches(1.1))
    head_box.fill.solid()
    head_box.fill.fore_color.rgb = COLOR_CARD_BG
    head_box.line.color.rgb = badge_color
    head_box.line.width = Pt(1.5)

    tf_h = head_box.text_frame
    tf_h.word_wrap = True
    p1 = tf_h.paragraphs[0]
    p1.text = f"{title}"
    p1.font.size = Pt(20)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_GOLD
    p1.alignment = PP_ALIGN.RIGHT

    p2 = tf_h.add_paragraph()
    p2.text = f"{subtitle}  |  {badge_text}"
    p2.font.size = Pt(11)
    p2.font.color.rgb = COLOR_SLATE_TEXT
    p2.alignment = PP_ALIGN.RIGHT

    # Content Points Cards
    if not points:
        points = ["تفاصيل البحث والدفاع موثقة وفق العقيدة الأرثوذكسية الرصينة ومراجع الكنيسة الجامعة."]

    top_offset = 2.0
    card_height = min(1.1, 4.8 / max(len(points), 1))

    for idx, pt_text in enumerate(points[:4]):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(top_offset + idx * (card_height + 0.18)), Inches(11.73), Inches(card_height))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = RGBColor(51, 65, 85)
        card.line.width = Pt(1.0)

        tf = card.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

        p = tf.paragraphs[0]
        p.text = f"🔹 {pt_text}"
        p.font.size = Pt(13)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.RIGHT

def add_summary_slide(prs, layout, topic_title: str, sections: dict):
    slide = prs.slides.add_slide(layout)
    set_slide_background(slide)

    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.73), Inches(0.8))
    p_t = t_box.text_frame.paragraphs[0]
    p_t.text = "📋 مصفوفة ملخص الردود والدفاعيات الشاملة"
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_GOLD
    p_t.alignment = PP_ALIGN.RIGHT

    # 4 Comparative Columns Cards
    pillars = [
        ("🎯 صلب الشبهة", sections.get("objection", ["تفكيك منطلقات الاعتراض"])[0] if sections.get("objection") else "تفكيك الاعتراض", RGBColor(220, 38, 38)),
        ("🔬 العلم المحايد", sections.get("science", ["براهين الآثار والمؤرخين"])[0] if sections.get("science") else "براهين الآثار والعلوم", COLOR_EMERALD),
        ("📖 البرهان الكتابي", sections.get("biblical", ["الشواهد الإنجيلية"])[0] if sections.get("biblical") else "النصوص والسياق الصحيح", COLOR_BLUE_ACCENT),
        ("⛪ إجماع الآباء", sections.get("patristic", ["أقوال الآباء القديسين"])[0] if sections.get("patristic") else "التقليد الأرثوذكسي المسلم", COLOR_GOLD)
    ]

    col_width = Inches(2.78)
    col_gap = Inches(0.2)
    left_start = Inches(0.8)

    for i, (p_title, p_content, p_color) in enumerate(pillars):
        x = left_start + i * (col_width + col_gap)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.6), col_width, Inches(5.0))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = p_color
        card.line.width = Pt(1.5)

        tf = card.text_frame
        tf.word_wrap = True

        p_h = tf.paragraphs[0]
        p_h.text = p_title
        p_h.font.size = Pt(16)
        p_h.font.bold = True
        p_h.font.color.rgb = p_color
        p_h.alignment = PP_ALIGN.CENTER

        p_c = tf.add_paragraph()
        p_c.text = f"\n{p_content[:280]}..."
        p_c.font.size = Pt(12)
        p_c.font.color.rgb = COLOR_WHITE
        p_c.alignment = PP_ALIGN.RIGHT

def add_references_slide(prs, layout, topic_title: str, sources: list, extra_refs: list):
    slide = prs.slides.add_slide(layout)
    set_slide_background(slide)

    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.73), Inches(0.8))
    p_t = t_box.text_frame.paragraphs[0]
    p_t.text = "📚 المراجع والدراسات المعتمدة للبحث والتعمق"
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_GOLD
    p_t.alignment = PP_ALIGN.RIGHT

    # References Box
    ref_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(11.73), Inches(5.0))
    ref_card.fill.solid()
    ref_card.fill.fore_color.rgb = COLOR_CARD_BG
    ref_card.line.color.rgb = COLOR_GOLD
    ref_card.line.width = Pt(1.0)

    tf = ref_card.text_frame
    tf.word_wrap = True

    p_intro = tf.paragraphs[0]
    p_intro.text = "مراجع معتمدة من مكتبة الصليب القبطية الأرثوذكسية وموسوعة د. غالي والمتاحف العالمية:"
    p_intro.font.size = Pt(14)
    p_intro.font.bold = True
    p_intro.font.color.rgb = COLOR_LIGHT_GOLD
    p_intro.alignment = PP_ALIGN.RIGHT

    all_refs = []
    for s in sources:
        all_refs.append(f"🔗 {s.get('title', 'مرجع')} ({s.get('url', '')})")
    for r in extra_refs:
        all_refs.append(f"📖 {r}")

    if not all_refs:
        all_refs = [
            "📖 أمهات كتب اللاهوت الدفاعي والعقيدي القبطي الأرثوذكسي.",
            "🌐 موسوعة الدفاعيات والرد على الشبهات (د. غالي - Holy_Bible_1).",
            "🏛️ مقتنيات المتحف البريطاني ومتحف اللوفر للمكتشفات الأثرية الكتابية."
        ]

    for ref_item in all_refs[:6]:
        p = tf.add_paragraph()
        p.text = f"\n{ref_item}"
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.RIGHT
