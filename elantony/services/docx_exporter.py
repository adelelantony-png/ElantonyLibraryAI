# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Microsoft Word (.docx) Research Monograph Exporter
Builds professionally formatted ecclesiastical research papers with 100% strict RTL support,
card-like chapters, verified patristic quotations, and consolidated bibliographic cards.
Guarantees clean Arabic typography with w:cs font mappings for Microsoft Word.
Clean academic layout without emojis, rigid tables, or distracting artifacts.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from elantony.core.text_cleaner import clean_book_title, clean_ocr_arabic
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def _set_paragraph_rtl(paragraph) -> None:
    """Applies right-to-left (RTL) Arabic bidirectional formatting to paragraph."""
    pPr = paragraph._element.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _set_run_font(run, font_name: str = "Traditional Arabic", size_pt: float = 14, bold: bool = False, italic: bool = False, color_rgb: Optional[RGBColor] = None) -> None:
    """Configures font name and complex-script (w:cs) font mapping for proper Arabic in Microsoft Word."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    if color_rgb:
        run.font.color.rgb = color_rgb

    # Explicitly map Complex Script font in Word XML (prevents squares/boxes on Windows Word)
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rPr.append(rFonts)

    # Complex script flag
    cs = OxmlElement('w:cs')
    cs.set(qn('w:val'), '1')
    rPr.append(cs)


def _strip_emojis(text: str) -> str:
    """Removes emojis and symbols for clean academic printing."""
    emoji_pattern = re.compile(
        "["
        "😀-🙏"
        "🌀-🗿"
        "🚀-🛿"
        "🇠-🇿"
        "✂-➰"
        "Ⓜ-🉑"
        "🤀-🧿"
        "🩰-🫿"
        "]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", text)
    # Also strip stray technical tags
    cleaned = re.sub(r"\[(QUOTATION|PARAPHRASE|SYNTHESIS|اقتباس حرفي|صياغة تحليلية|استنتاج مركب)[^\]]*\]", "", cleaned)
    return cleaned


def generate_session_docx(comp_data: Dict[str, Any], output_path: str) -> str:
    """
    Exports compiled session monograph into a beautifully formatted Microsoft Word document (.docx).
    Clean, publication-ready academic layout matching the portal's card theme without rigid tables.
    """
    doc = docx.Document()

    # Page Margins: 1 inch standard academic
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    title = _strip_emojis(comp_data.get("title", "دراسة وأطروحة لاهوتية آبائية موثقة")).strip()
    turns = comp_data.get("turns", [])
    bibliography = comp_data.get("bibliography", [])

    # 1. Header Cross & System Brand
    p_header = doc.add_paragraph()
    _set_paragraph_rtl(p_header)
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_brand = p_header.add_run("كنيسة الإسكندرية القبطية الأرثوذكسية - مكتبة الدراسات الآبائية واللاهوتية\n")
    _set_run_font(r_brand, "Traditional Arabic", 13, bold=True, color_rgb=RGBColor(135, 79, 25))

    # 2. Main Title
    p_title = doc.add_paragraph()
    _set_paragraph_rtl(p_title)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(f"« {title} »\n")
    _set_run_font(r_title, "Traditional Arabic", 22, bold=True, color_rgb=RGBColor(24, 43, 73))

    r_sub = p_title.add_run("أطروحة بحثية لاهوتية مجمعة وموثقة من أمهات الكتب الآبائية والكنسية")
    _set_run_font(r_sub, "Traditional Arabic", 14, italic=True, color_rgb=RGBColor(100, 116, 139))

    # 3. Metadata Summary Block (Zero Rigid Table - Fluid Responsive Card)
    p_meta = doc.add_paragraph()
    _set_paragraph_rtl(p_meta)
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(8)
    p_meta.paragraph_format.space_after = Pt(14)
    r_meta = p_meta.add_run(
        f"📅 تاريخ التوثيق: {datetime.now().strftime('%Y-%m-%d')}   |   "
        f"📑 عدد المباحث: {len(turns)} محاور   |   "
        f"🏛️ المراجع المعتمدة: {len(bibliography)} مصدراً كنسياً"
    )
    _set_run_font(r_meta, "Traditional Arabic", 12.5, bold=True, color_rgb=RGBColor(71, 85, 105))

    p_sep = doc.add_paragraph()
    _set_paragraph_rtl(p_sep)
    p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sep = p_sep.add_run("═══════════════════════════════════════════════")
    _set_run_font(r_sep, "Arial", 9, color_rgb=RGBColor(217, 119, 6))

    # 4. Table of Contents
    p_toc_head = doc.add_paragraph()
    _set_paragraph_rtl(p_toc_head)
    r_toc_head = p_toc_head.add_run("فهرس مباحث ومحتويات البحث:")
    _set_run_font(r_toc_head, "Traditional Arabic", 16, bold=True, color_rgb=RGBColor(15, 23, 42))

    for idx, t in enumerate(turns, 1):
        p_item = doc.add_paragraph()
        _set_paragraph_rtl(p_item)
        p_item.paragraph_format.left_indent = Inches(0.25)
        p_item.paragraph_format.right_indent = Inches(0.25)
        q_text = _strip_emojis(t.get("user_query") or t.get("question", "")).strip()
        r_item = p_item.add_run(f"• المبحث {idx}: {q_text}")
        _set_run_font(r_item, "Traditional Arabic", 13.5, bold=True, color_rgb=RGBColor(51, 65, 85))

    doc.add_paragraph()

    # 5. Core Discussion Turns (Chapters)
    for idx, t in enumerate(turns, 1):
        # Section Divider
        p_div = doc.add_paragraph()
        _set_paragraph_rtl(p_div)
        r_div = p_div.add_run("__________________________________________________________________")
        _set_run_font(r_div, "Arial", 8, color_rgb=RGBColor(203, 213, 225))

        # Question Header
        p_q = doc.add_paragraph()
        _set_paragraph_rtl(p_q)
        q_text = _strip_emojis(t.get("user_query") or t.get("question", "")).strip()
        r_q = p_q.add_run(f"المبحث {idx}: {q_text}")
        _set_run_font(r_q, "Traditional Arabic", 18, bold=True, color_rgb=RGBColor(124, 45, 18))

        # Clean answer lines
        raw_ans = t.get("ai_response", "") or t.get("answer", "")
        clean_ans = _strip_emojis(raw_ans)

        for line in clean_ans.split("\n"):
            line_str = line.strip()
            if not line_str or line_str == "---":
                continue

            # Dismantle any markdown tables into clean paragraph cards
            if line_str.startswith("|") and line_str.endswith("|"):
                if re.match(r"^\|[\s\-:|]+\|$", line_str):
                    continue
                cells = [c.strip() for c in line_str.split("|")[1:-1] if c.strip()]
                if cells:
                    p_table_card = doc.add_paragraph()
                    _set_paragraph_rtl(p_table_card)
                    p_table_card.paragraph_format.left_indent = Inches(0.3)
                    p_table_card.paragraph_format.right_indent = Inches(0.3)
                    r_t = p_table_card.add_run("✦ " + " — ".join(cells))
                    _set_run_font(r_t, "Traditional Arabic", 13, bold=True, color_rgb=RGBColor(51, 65, 85))
                continue

            p_line = doc.add_paragraph()
            _set_paragraph_rtl(p_line)
            p_line.paragraph_format.line_spacing = 1.4
            p_line.paragraph_format.space_after = Pt(5)

            if line_str.startswith("#"):
                # Subheading
                heading_level_text = re.sub(r"^#+\s*", "", line_str)
                r_head = p_line.add_run(heading_level_text)
                _set_run_font(r_head, "Traditional Arabic", 15.5, bold=True, color_rgb=RGBColor(146, 64, 14))
            elif line_str.startswith(">"):
                # Blockquote (Patristic Quotation)
                quote_text = re.sub(r"^>\s*", "", line_str)
                p_line.paragraph_format.left_indent = Inches(0.4)
                p_line.paragraph_format.right_indent = Inches(0.4)
                r_q = p_line.add_run(quote_text)
                is_bold = "*(" in quote_text or "المصدر:" in quote_text
                _set_run_font(r_q, "Traditional Arabic", 13.5, bold=is_bold, italic=not is_bold, color_rgb=RGBColor(30, 41, 59))
            elif line_str.startswith("•") or line_str.startswith("-"):
                # Bullet list
                r_bullet = p_line.add_run("  • ")
                _set_run_font(r_bullet, "Traditional Arabic", 14, bold=True, color_rgb=RGBColor(135, 79, 25))
                bullet_text = line_str.lstrip("•- ").strip()
                r_txt = p_line.add_run(bullet_text)
                _set_run_font(r_txt, "Traditional Arabic", 14)
            else:
                # Normal paragraph
                p_line.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r_txt = p_line.add_run(line_str)
                _set_run_font(r_txt, "Traditional Arabic", 14)

        doc.add_paragraph()

    # 6. Consolidated Bibliography Section (Zero Rigid Table - Beautiful Cards)
    doc.add_page_break()

    p_bib_title = doc.add_paragraph()
    _set_paragraph_rtl(p_bib_title)
    r_bib_title = p_bib_title.add_run("ثبت المصادر والمراجع البيبليوغرافية الموحدة للبحث:")
    _set_run_font(r_bib_title, "Traditional Arabic", 18, bold=True, color_rgb=RGBColor(15, 118, 110))

    p_bib_sub = doc.add_paragraph()
    _set_paragraph_rtl(p_bib_sub)
    r_bib_sub = p_bib_sub.add_run("قائمة موحدة ومحققة بجميع أمهات الكتب والمصادر الكنسية المستند إليها في هذا البحث:")
    _set_run_font(r_bib_sub, "Traditional Arabic", 13, italic=True, color_rgb=RGBColor(100, 116, 139))

    if bibliography:
        for b_idx, b in enumerate(bibliography, 1):
            p_b = doc.add_paragraph()
            _set_paragraph_rtl(p_b)
            p_b.paragraph_format.left_indent = Inches(0.2)
            p_b.paragraph_format.right_indent = Inches(0.2)
            p_b.paragraph_format.space_before = Pt(5)
            p_b.paragraph_format.space_after = Pt(4)

            b_title = clean_book_title(_strip_emojis(b.get("title") or b.get("reference", "")))
            b_author = _strip_emojis(b.get("author") or "آباء الكنيسة").strip()
            b_pages = str(b.get("pages_cited") or "مواضع متعددة")

            r_idx_title = p_b.add_run(f"[{b_idx}] « {b_title} »\n")
            _set_run_font(r_idx_title, "Traditional Arabic", 14, bold=True, color_rgb=RGBColor(24, 43, 73))

            r_details = p_b.add_run(f"    • المؤلف: {b_author}   |   📄 الصفحات المعتمدة: {b_pages}")
            _set_run_font(r_details, "Traditional Arabic", 12.5, color_rgb=RGBColor(135, 79, 25))

    doc.save(output_path)
    return output_path
