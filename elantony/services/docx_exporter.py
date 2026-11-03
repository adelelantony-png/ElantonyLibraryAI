# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Microsoft Word (.docx) Research Monograph Exporter
Builds professionally formatted ecclesiastical research papers with RTL support,
tables of contents, verified patristic quotations, and consolidated bibliographies.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def _set_paragraph_rtl(paragraph) -> None:
    """Applies right-to-left (RTL) Arabic bidirectional formatting to paragraph."""
    pPr = paragraph._element.get_or_add_pPr()
    bidi = OxmlElement('w:bidi')
    bidi.set(qn('w:val'), '1')
    pPr.append(bidi)


def _set_cell_background(cell, fill_hex: str) -> None:
    """Sets cell shading color in hexadecimal (e.g. 'F1F5F9')."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)


def generate_session_docx(comp_data: Dict[str, Any], output_path: str) -> str:
    """
    Exports compiled session monograph into a beautifully formatted Microsoft Word document (.docx).
    """
    doc = docx.Document()

    # Page Margins: 1 inch on all sides
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    title = comp_data.get("title", "أطروحة لاهوتية آبائية")
    turns = comp_data.get("turns", [])
    bibliography = comp_data.get("bibliography", [])

    # 1. Header Cross & System Brand
    p_header = doc.add_paragraph()
    _set_paragraph_rtl(p_header)
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_brand = p_header.add_run("✠ منظومة ELANTONY LIBRARY AI - مكتبة كنيسة المشرق والتقليد الأرثوذكسي ✠\n")
    r_brand.font.name = "Arial"
    r_brand.font.size = Pt(11)
    r_brand.font.color.rgb = RGBColor(140, 100, 30)

    # 2. Main Title
    p_title = doc.add_paragraph()
    _set_paragraph_rtl(p_title)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(f"« {title} »\n")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(30, 60, 130)

    r_sub = p_title.add_run("أطروحة بحثية لاهوتية مجمعة وموثقة من أمهات الكتب الآبائية")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(13)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(100, 116, 139)

    # 3. Metadata Table
    table_meta = doc.add_table(rows=1, cols=3)
    table_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table_meta.rows[0].cells

    for c in hdr_cells:
        _set_cell_background(c, "F8FAFC")

    p0 = hdr_cells[0].paragraphs[0]
    _set_paragraph_rtl(p0)
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    r0.font.size = Pt(10)
    r0.font.bold = True

    p1 = hdr_cells[1].paragraphs[0]
    _set_paragraph_rtl(p1)
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p1.add_run(f"📊 عدد المحاور: {len(turns)} محاور")
    r1.font.size = Pt(10)
    r1.font.bold = True

    p2 = hdr_cells[2].paragraphs[0]
    _set_paragraph_rtl(p2)
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(f"🏛️ المراجع المعتمدة: {len(bibliography)} مراجع")
    r2.font.size = Pt(10)
    r2.font.bold = True

    doc.add_paragraph()  # Spacing

    # 4. Table of Questions / Contents
    p_toc_head = doc.add_paragraph()
    _set_paragraph_rtl(p_toc_head)
    r_toc_head = p_toc_head.add_run("📋 فهرس المحاور والأسئلة المتفرعة في البحث:")
    r_toc_head.font.name = "Arial"
    r_toc_head.font.size = Pt(14)
    r_toc_head.font.bold = True
    r_toc_head.font.color.rgb = RGBColor(15, 23, 42)

    for idx, t in enumerate(turns, 1):
        p_item = doc.add_paragraph()
        _set_paragraph_rtl(p_item)
        r_num = p_item.add_run(f"  {idx}. ")
        r_num.font.bold = True
        r_num.font.color.rgb = RGBColor(37, 99, 235)
        r_q = p_item.add_run(f"{t['question']}")
        r_q.font.name = "Arial"
        r_q.font.size = Pt(11)

    p_div = doc.add_paragraph()
    _set_paragraph_rtl(p_div)
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_div = p_div.add_run("═══════════════════════════════════════════════════")
    r_div.font.color.rgb = RGBColor(203, 213, 225)

    # 5. Detailed Q&A Sections
    for idx, t in enumerate(turns, 1):
        # Section Heading
        p_qhead = doc.add_paragraph()
        _set_paragraph_rtl(p_qhead)
        r_qhead = p_qhead.add_run(f"🔹 المحور رقم ({idx}): «{t['question']}»")
        r_qhead.font.name = "Arial"
        r_qhead.font.size = Pt(15)
        r_qhead.font.bold = True
        r_qhead.font.color.rgb = RGBColor(30, 58, 138)

        # Answer body
        p_ahead = doc.add_paragraph()
        _set_paragraph_rtl(p_ahead)
        r_ahead = p_ahead.add_run("📖 التحليل والإجابة اللاهوتية الموثقة:")
        r_ahead.font.name = "Arial"
        r_ahead.font.size = Pt(12)
        r_ahead.font.bold = True
        r_ahead.font.color.rgb = RGBColor(180, 110, 10)

        # Clean markdown formatting for Word
        clean_ans = t["answer"].replace("### ", "").replace("## ", "").replace("# ", "")
        for line in clean_ans.split("\n"):
            line_str = line.strip()
            if not line_str:
                continue
            p_line = doc.add_paragraph()
            _set_paragraph_rtl(p_line)
            p_line.paragraph_format.line_spacing = 1.25

            if line_str.startswith("•") or line_str.startswith("-"):
                r_bullet = p_line.add_run("  • ")
                r_bullet.font.bold = True
                r_bullet.font.color.rgb = RGBColor(37, 99, 235)
                line_str = line_str.lstrip("•- ")

            r_txt = p_line.add_run(line_str)
            r_txt.font.name = "Arial"
            r_txt.font.size = Pt(11)

        # Citations for this turn
        turn_citations = t.get("citations", [])
        if turn_citations:
            p_cithdr = doc.add_paragraph()
            _set_paragraph_rtl(p_cithdr)
            r_cithdr = p_cithdr.add_run("🏛️ الشواهد والمراجع المعتمدة لهذا المحور:")
            r_cithdr.font.name = "Arial"
            r_cithdr.font.size = Pt(11)
            r_cithdr.font.bold = True
            r_cithdr.font.color.rgb = RGBColor(71, 85, 105)

            for c_idx, c in enumerate(turn_citations, 1):
                p_c = doc.add_paragraph()
                _set_paragraph_rtl(p_c)
                p_c.paragraph_format.left_indent = Inches(0.2)
                p_c.paragraph_format.right_indent = Inches(0.2)

                p_label = f"صـ {c.get('printed_page') or c.get('page_number')}"
                auth = c.get('author') or 'آباء الكنيسة'
                tier = c.get('authenticity_tier', 3)

                r_ref = p_c.add_run(f"[{c_idx}] {c.get('book_title')} (الكاتب: {auth}) - {p_label} | المرتبة: Tier {tier}\n")
                r_ref.font.bold = True
                r_ref.font.size = Pt(10)
                r_ref.font.color.rgb = RGBColor(30, 41, 59)

                if c.get("excerpt"):
                    r_ex = p_c.add_run(f"    « {c['excerpt'][:240]}... »\n")
                    r_ex.font.italic = True
                    r_ex.font.size = Pt(9.5)
                    r_ex.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_paragraph()

    # 6. Consolidated Bibliography Section
    doc.add_page_break()

    p_bib_title = doc.add_paragraph()
    _set_paragraph_rtl(p_bib_title)
    r_bib_title = p_bib_title.add_run("📚 المكتبة البيبليوغرافية الموحدة للبحث (Consolidated Patristic Bibliography):")
    r_bib_title.font.name = "Arial"
    r_bib_title.font.size = Pt(15)
    r_bib_title.font.bold = True
    r_bib_title.font.color.rgb = RGBColor(15, 23, 42)

    p_bib_sub = doc.add_paragraph()
    _set_paragraph_rtl(p_bib_sub)
    r_bib_sub = p_bib_sub.add_run("قائمة مرقمة بجميع أمهات الكتب والمراجع الكنسية التي تم الاعتماد عليها وتوثيقها في هذا البحث:")
    r_bib_sub.font.size = Pt(11)
    r_bib_sub.font.italic = True
    r_bib_sub.font.color.rgb = RGBColor(100, 116, 139)

    if bibliography:
        table_bib = doc.add_table(rows=1, cols=4)
        table_bib.alignment = WD_TABLE_ALIGNMENT.CENTER
        b_hdr = table_bib.rows[0].cells
        b_hdr[0].text = "م"
        b_hdr[1].text = "اسم الكتاب / المرجع"
        b_hdr[2].text = "المؤلف / الأب"
        b_hdr[3].text = "الصفحات الموثقة"

        for cell in b_hdr:
            _set_cell_background(cell, "E2E8F0")
            for p in cell.paragraphs:
                _set_paragraph_rtl(p)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.bold = True
                    r.font.size = Pt(10)

        for b_idx, b in enumerate(bibliography, 1):
            row_cells = table_bib.add_row().cells
            row_cells[0].text = str(b_idx)
            row_cells[1].text = b.get("title", "")
            row_cells[2].text = b.get("author", "غير محدد")
            pages_list = sorted(b.get("pages", set()), key=lambda x: int(x) if x.isdigit() else 0)
            row_cells[3].text = ", ".join(pages_list) if pages_list else "كامل الكتاب"

            for cell in row_cells:
                for p in cell.paragraphs:
                    _set_paragraph_rtl(p)
                    for r in p.runs:
                        r.font.size = Pt(9.5)

    doc.add_paragraph()
    p_ftr = doc.add_paragraph()
    _set_paragraph_rtl(p_ftr)
    p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ftr = p_ftr.add_run("✠ تم إعداد وتوثيق هذه الدراسة بواسطة منظومة ELANTONY LIBRARY AI - خدمة التراث الكنسي الأرثوذكسي ✠")
    r_ftr.font.size = Pt(9.5)
    r_ftr.font.italic = True
    r_ftr.font.color.rgb = RGBColor(148, 163, 184)

    # Ensure parent dir exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path
