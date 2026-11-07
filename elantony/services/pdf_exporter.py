"""
Official Ecclesiastical Academic PDF Exporter for ELANTONY LIBRARY AI.
Generates publication-quality theological research monographs with Arabic RTL support,
cross headers, custom typography, citations tables, and verified church source bibliography.
"""
import os
import io
import time
from typing import Dict, Any, List
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

import arabic_reshaper
from bidi.algorithm import get_display


def reshape_ar(text: str) -> str:
    """Reshapes and applies bidirectional algorithm to Arabic text for ReportLab rendering."""
    if not text:
        return ""
    try:
        # Standardize spaces
        t = " ".join(text.split())
        reshaped = arabic_reshaper.reshape(t)
        return get_display(reshaped)
    except Exception:
        return text


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page counting and ecclesiastical running headers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#7c2d12"))

        # Header running line on pages > 1
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#d97706"))
            self.setLineWidth(0.5)
            self.line(40, 805, 555, 805)

        # Footer running line & page numbers
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 45, 555, 45)

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(555, 32, page_str)
        footer_brand = reshape_ar("منظومة ELANTONY LIBRARY AI - أمانة التوثيق الكنسي والآبائي")
        self.drawString(40, 32, footer_brand)
        self.restoreState()


def generate_session_pdf(comp_data: Dict[str, Any], output_path: str) -> str:
    """
    Compiles an entire theological discussion session into a publication-grade PDF monograph.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'EcclTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=24,
        alignment=1, # Center
        textColor=colors.HexColor('#7c2d12'),
        spaceAfter=10
    )

    header_brand_style = ParagraphStyle(
        'EcclHeaderBrand',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#92400e'),
        spaceAfter=15
    )

    meta_style = ParagraphStyle(
        'EcclMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20
    )

    q_style = ParagraphStyle(
        'EcclQuestion',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        alignment=2, # Right
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'EcclBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        alignment=2, # Right
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )

    cit_style = ParagraphStyle(
        'EcclCitation',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#475569')
    )

    story = []

    # 1. Header Cross & Brand
    brand_text = reshape_ar("✠ بطريركية الأقباط الأرثوذكس - منظومة ELANTONY LIBRARY AI الأكاديمية ✠")
    story.append(Paragraph(brand_text, header_brand_style))

    # 2. Document Title
    raw_title = comp_data.get("title", "دراسة وأطروحة لاهوتية آبائية موثقة")
    story.append(Paragraph(reshape_ar(raw_title), title_style))

    # 3. Metadata
    cur_date = time.strftime('%Y-%m-%d %H:%M')
    meta_text = reshape_ar(f"تاريخ التصدير: {cur_date}  |  المصنف: بحث لاهوتي أكاديمي موثق")
    story.append(Paragraph(meta_text, meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d97706'), spaceAfter=15))

    # 4. Turns
    turns = comp_data.get("turns", [])
    for idx, t in enumerate(turns, 1):
        q_text = reshape_ar(f"المبحث {idx}: {t.get('user_query', '')}")
        story.append(Paragraph(q_text, q_style))

        # Answer body
        raw_ans = t.get('ai_response', '')
        for p in raw_ans.split('\n'):
            p_strip = p.strip()
            if not p_strip:
                continue
            story.append(Paragraph(reshape_ar(p_strip), body_style))

        # Citations Table if available
        citations = t.get('citations', [])
        if citations:
            table_data = [[Paragraph(reshape_ar("<b>الشواهد الكنسية والآبائية المعتمدة الموثقة لهذا المبحث</b>"), cit_style)]]
            for c_idx, c in enumerate(citations[:5], 1):
                b_title = c.get('book_title', '')
                p_num = c.get('printed_page') or c.get('page_number', '')
                author = c.get('author', 'آباء الكنيسة')
                tier = c.get('authenticity_tier', 2)
                c_line = f"[{c_idx}] «{b_title}» صـ {p_num} | المؤلف: {author} (مرتبة التوثيق: {tier})"
                table_data.append([Paragraph(reshape_ar(c_line), cit_style)])

            cit_table = Table(table_data, colWidths=[515])
            cit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#94a3b8')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(Spacer(1, 4))
            story.append(cit_table)
            story.append(Spacer(1, 10))

        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=12, spaceBefore=8))

    # 5. Bibliography Section
    bib = comp_data.get("bibliography", [])
    if bib:
        story.append(KeepTogether([
            Paragraph(reshape_ar("<b>قائمة المصادر والمراجع الكنسية الموثقة في هذا البحث</b>"), q_style),
            Spacer(1, 4)
        ]))
        bib_data = []
        for b_idx, b in enumerate(bib, 1):
            ref_str = b.get('reference', '')
            author = b.get('author', 'آباء الكنيسة')
            b_line = f"{b_idx}. {ref_str} — تأليف: {author}"
            bib_data.append([Paragraph(reshape_ar(b_line), cit_style)])

        bib_table = Table(bib_data, colWidths=[515])
        bib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(bib_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
