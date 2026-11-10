# -*- coding: utf-8 -*-
PREVIEW_TOOLBAR_JS = r"""<script>
  function downloadStandaloneHtml() {
    try {
      var parser = new DOMParser();
      var cleanDoc = parser.parseFromString(document.documentElement.outerHTML, 'text/html');
      var toolbar = cleanDoc.querySelector('.no-print');
      if (toolbar) toolbar.remove();
      var cleanHtml = '<!DOCTYPE html>\n' + cleanDoc.documentElement.outerHTML;
      var blob = new Blob([cleanHtml], { type: 'text/html;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      var safeTitle = (document.title || 'أطروحة_لاهوتية_موثقة').replace(/[/\\:*?"<>|]/g, '_').trim();
      a.download = safeTitle + '.html';
      document.body.appendChild(a);
      a.click();
      setTimeout(function() {
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      }, 1000);
    } catch(e) {
      alert('⚠️ تعذر حفظ ملف المعاينة: ' + e.message);
    }
  }

  function downloadPdfFile() {
    try {
      var parts = window.location.pathname.split('/');
      var sId = null;
      for (var i = 0; i < parts.length; i++) {
        if (parts[i] === 'sessions' && i + 1 < parts.length) {
          sId = parts[i + 1];
          break;
        }
      }
      if (sId) {
        window.location.href = '/api/sessions/' + sId + '/export?format=pdf';
      } else {
        window.print();
      }
    } catch(e) {
      window.print();
    }
  }

  function copyPreviewLink() {
    var url = window.location.href;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function() {
        alert("✅ تم نسخ رابط المعاينة بنجاح!\n\n" + url + "\n\nيمكنك الآن إرساله أو مشاركته مع أي باحث.");
      }).catch(function() {
        fallbackCopy(url);
      });
    } else {
      fallbackCopy(url);
    }
  }

  function fallbackCopy(text) {
    prompt("انسخ رابط المعاينة التالي لمشاركته:", text);
  }

  function shareViaWhatsApp() {
    var title = document.title || 'أطروحة لاهوتية موثقة';
    var text = encodeURIComponent('✠ ' + title + ' - ' + window.location.href);
    window.open('https://api.whatsapp.com/send?text=' + text, '_blank');
  }

  function shareViaTelegram() {
    var title = document.title || 'أطروحة لاهوتية موثقة';
    var url = encodeURIComponent(window.location.href);
    var text = encodeURIComponent('✠ ' + title);
    window.open('https://t.me/share/url?url=' + url + '&text=' + text, '_blank');
  }

  function closePreview() {
    if (window.opener) {
      window.close();
    } else if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = '/';
    }
  }
</script>"""

"""
Official Ecclesiastical Monograph HTML & Print Publisher for ELANTONY LIBRARY AI.
Generates publication-quality, beautifully styled theological research monographs
mirroring the exact visual aesthetic, color tokens, and layout of the Web Portal.
Optimized for A4 printing and Microsoft Edge Headless PDF generation.
Guarantees 100% clean RTL Arabic typography, card-based layout, and zero rigid tables.
"""

import html
from elantony.core.text_cleaner import clean_book_title, clean_ocr_arabic
import re
from datetime import datetime
from typing import Dict, Any, List


def _clean_markdown_to_html(text: str) -> str:
    """
    Converts markdown text to elegant semantic HTML elements matching the portal theme.
    Disassembles any markdown tables into clean structured cards/lists ('فركشة الجداول').
    """
    if not text:
        return ""

    lines = text.split("\n")
    html_parts = []
    in_quote = False
    quote_lines = []
    in_bullet_list = False

    def flush_quote():
        nonlocal in_quote, quote_lines
        if quote_lines:
            q_full = " ".join(quote_lines).strip()
            # Separate citation subtitle if present: *(المصدر: ...)*
            cit_match = re.search(r"\*\((.*?)\)\*", q_full)
            if cit_match:
                cit_text = cit_match.group(1)
                q_body = q_full.replace(cit_match.group(0), "").strip()
                html_parts.append(
                    f'<div class="quote-card">'
                    f'<div class="quote-text">« {html.escape(q_body.strip("«» "))} »</div>'
                    f'<div class="quote-src">*( {html.escape(cit_text)} )*</div>'
                    f'</div>'
                )
            else:
                html_parts.append(
                    f'<div class="quote-card">'
                    f'<div class="quote-text">{html.escape(q_full)}</div>'
                    f'</div>'
                )
            quote_lines = []
            in_quote = False

    def flush_bullets():
        nonlocal in_bullet_list
        if in_bullet_list:
            html_parts.append('</ul>')
            in_bullet_list = False

    for line in lines:
        line_s = line.strip()

        # Handle Empty Lines
        if not line_s:
            flush_quote()
            flush_bullets()
            continue

        # Handle Blockquotes (> «...»)
        if line_s.startswith(">"):
            flush_bullets()
            in_quote = True
            clean_q = re.sub(r"^>\s*", "", line_s)
            quote_lines.append(clean_q)
            continue
        else:
            flush_quote()

        # Handle Dismantling / Flattening any Markdown Table lines (| col | col |)
        if line_s.startswith("|") and line_s.endswith("|"):
            flush_bullets()
            # Skip separator line like |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", line_s):
                continue
            cells = [c.strip() for c in line_s.split("|")[1:-1] if c.strip()]
            if cells:
                # Render table row as an elegant card row instead of a rigid table
                joined_cells = " &mdash; ".join(html.escape(c) for c in cells)
                html_parts.append(f'<div class="table-card-row">✦ {joined_cells}</div>')
            continue

        # Handle Headings
        if line_s.startswith("### "):
            flush_bullets()
            h_text = html.escape(line_s[4:].strip())
            html_parts.append(f'<h4 class="m-subheading">{h_text}</h4>')
            continue
        elif line_s.startswith("## "):
            flush_bullets()
            h_text = html.escape(line_s[3:].strip())
            html_parts.append(f'<h3 class="m-heading">{h_text}</h3>')
            continue
        elif line_s.startswith("# "):
            flush_bullets()
            h_text = html.escape(line_s[2:].strip())
            html_parts.append(f'<h2 class="m-main-heading">{h_text}</h2>')
            continue

        # Handle Bullets (• or -)
        if line_s.startswith("•") or line_s.startswith("- ") or line_s.startswith("* "):
            if not in_bullet_list:
                html_parts.append('<ul class="m-bullet-list">')
                in_bullet_list = True
            b_text = re.sub(r"^[•\-\*]\s*", "", line_s)
            # Support bold in bullets: **text**
            b_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html.escape(b_text))
            html_parts.append(f'<li>{b_html}</li>')
            continue
        else:
            flush_bullets()

        # Normal Paragraph with bold formatting
        p_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html.escape(line_s))
        html_parts.append(f'<p class="m-paragraph">{p_html}</p>')

    flush_quote()
    flush_bullets()
    return "\n".join(html_parts)


def generate_session_html(comp_data: Dict[str, Any]) -> str:
    """
    Generates a stunning, publication-grade, self-contained HTML monograph
    mirroring the exact visual aesthetic, color tokens, and cards of the Web Portal.
    """
    raw_title = comp_data.get("title", "دراسة وأطروحة لاهوتية آبائية موثقة")
    title = html.escape(re.sub(r"[^\w\s\u0600-\u06FF\u2720\-\.\(\)]", "", raw_title).strip())
    turns = comp_data.get("turns", [])
    bibliography = comp_data.get("bibliography", [])
    doc_date = datetime.now().strftime("%Y-%m-%d")

    # Render Chapters / Mubahith
    mubahith_html = []
    for idx, t in enumerate(turns, 1):
        q_raw = t.get("user_query") or t.get("question", "")
        q_clean = html.escape(q_raw.strip())
        ans_raw = t.get("ai_response") or t.get("answer", "")
        ans_html = _clean_markdown_to_html(ans_raw)

        # Single Turn Citations if present
        citations = t.get("citations", [])
        cit_html_list = []
        if citations:
            seen_c = set()
            for c in citations:
                b_name = (c.get("book_title") or "مرجع كنسي").replace(".pdf", "")
                p_val = c.get("printed_page") or c.get("page_number", "")
                author = c.get("author", "آباء الكنيسة")
                tier = c.get("authenticity_tier", 2)
                key = (b_name, str(p_val))
                if key not in seen_c:
                    seen_c.add(key)
                    tier_label = "نص كتابي مقدس" if tier == 1 else ("شاهد آبائي أصيل" if tier == 2 else "دراسة لاهوتية معتمدة")
                    cit_html_list.append(
                        f'<div class="ref-pill">'
                        f'<span class="ref-icon">📖</span>'
                        f'<span class="ref-title">«{html.escape(b_name)}»</span> '
                        f'<span class="ref-meta">(صـ {html.escape(str(p_val))} | {html.escape(author)})</span> '
                        f'<span class="ref-tier-badge">{tier_label}</span>'
                        f'</div>'
                    )

        cit_section = ""
        if cit_html_list:
            cit_section = (
                f'<div class="turn-citations-card">'
                f'<div class="citations-header">🏛️ الشواهد الآبائية والكنسية المستند إليها في هذا المبحث:</div>'
                f'<div class="citations-pills-wrap">{"".join(cit_html_list)}</div>'
                f'</div>'
            )

        mubahith_html.append(
            f'<section class="mبحث-card" id="mبحث_{idx}">'
            f'<div class="mبحث-header">'
            f'<span class="mبحث-badge">المبحث {idx}</span>'
            f'<h2 class="mبحث-title">{q_clean}</h2>'
            f'</div>'
            f'<div class="mبحث-body">{ans_html}</div>'
            f'{cit_section}'
            f'</section>'
        )

    # Render Bibliography as Structured Reference Cards (Zero Rigid Tables!)
    bib_cards_html = []
    if bibliography:
        for b_idx, b in enumerate(bibliography, 1):
            ref_title = html.escape(clean_book_title(b.get("title") or b.get("reference") or "مرجع كنسي"))
            author = html.escape(b.get("author") or "آباء الكنيسة القبطية")
            pages = html.escape(str(b.get("pages_cited") or "مواضع متعددة"))
            tier = b.get("tier", 2)
            tier_badge = "نص كتابي مقدس" if tier == 1 else ("شاهد آبائي أصيل" if tier == 2 else "دراسات وبحوث لاهوتية")

            bib_cards_html.append(
                f'<div class="biblio-card">'
                f'<div class="bib-index">{b_idx}</div>'
                f'<div class="bib-details">'
                f'<div class="bib-title-row">'
                f'<strong class="bib-title">« {ref_title} »</strong>'
                f'<span class="bib-author">تأليف: {author}</span>'
                f'</div>'
                f'<div class="bib-meta-row">'
                f'<span class="bib-pages">📄 الصفحات المعتمدة: <strong>{pages}</strong></span>'
                f'<span class="bib-badge">{tier_badge}</span>'
                f'</div>'
                f'</div>'
                f'</div>'
            )

    bib_section_html = ""
    if bib_cards_html:
        bib_section_html = (
            f'<section class="mبحث-card biblio-section-card">'
            f'<div class="mبحث-header">'
            f'<span class="mبحث-badge" style="background:#0f766e;">ثبت المصادر</span>'
            f'<h2 class="mبحث-title">قائمة المصادر والمراجع البيبليوغرافية المعتمدة في هذا البحث</h2>'
            f'</div>'
            f'<p class="biblio-intro">قائمة موحدة ومحققة بجميع أمهات الكتب والمخطوطات الكنسية التي استندت إليها مباحث هذه الدراسة:</p>'
            f'<div class="biblio-cards-grid">{"".join(bib_cards_html)}</div>'
            f'</section>'
        )

    # Assemble Full Standalone Monograph HTML
    html_body = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — أطروحة بحثية لاهوتية</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@400;600;700;800;900&display=swap');

  @page {{
    size: A4 portrait;
    margin: 18mm 15mm 18mm 15mm;
    @bottom-center {{
      content: counter(page);
      font-family: 'Cairo', sans-serif;
      font-size: 9pt;
      color: #94a3b8;
    }}
  }}

  *, *::before, *::after {{
    box-sizing: border-box;
  }}

  body {{
    direction: rtl;
    text-align: right;
    font-family: 'Amiri', 'Traditional Arabic', serif;
    font-size: 14pt;
    line-height: 1.85;
    color: #1e293b;
    background-color: #f8fafc;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}

  .page-wrapper {{
    max-width: 900px;
    margin: 0 auto;
    padding: 24px 20px;
    background: #ffffff;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    border-radius: 12px;
  }}

  /* Top Liturgical Header */
  .doc-header {{
    text-align: center;
    border-bottom: 2px solid #d97706;
    padding-bottom: 18px;
    margin-bottom: 24px;
    position: relative;
  }}

  .church-brand {{
    font-family: 'Cairo', sans-serif;
    font-size: 11pt;
    font-weight: 700;
    color: #7c2d12;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }}

  .doc-title {{
    font-family: 'Cairo', sans-serif;
    font-size: 22pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.35;
    margin: 10px 0;
  }}

  .doc-subtitle {{
    font-size: 12.5pt;
    color: #64748b;
    font-style: italic;
    margin-bottom: 16px;
  }}

  /* Metadata Badges Bar (Zero Table) */
  .meta-bar {{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
    padding: 10px 16px;
    background: #fdfdfd;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 24px;
  }}

  .meta-chip {{
    font-family: 'Cairo', sans-serif;
    font-size: 10.5pt;
    font-weight: 600;
    color: #334155;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .meta-chip strong {{
    color: #7c2d12;
  }}

  /* Mubahith Chapters (Cards Layout matching Portal) */
  .mبحث-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-right: 5px solid #7c2d12;
    border-radius: 10px;
    padding: 22px 24px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    page-break-inside: avoid;
  }}

  .mبحث-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 12px;
    margin-bottom: 16px;
  }}

  .mبحث-badge {{
    font-family: 'Cairo', sans-serif;
    font-size: 10pt;
    font-weight: 800;
    background: #7c2d12;
    color: #ffffff;
    padding: 4px 10px;
    border-radius: 6px;
    white-space: nowrap;
  }}

  .mبحث-title {{
    font-family: 'Cairo', sans-serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
    line-height: 1.4;
  }}

  .mبحث-body {{
    font-size: 13.5pt;
    line-height: 1.9;
    color: #1e293b;
  }}

  .m-paragraph {{
    margin: 0 0 16px 0;
    text-align: justify;
    text-justify: inter-word;
    text-align-last: right;
    line-height: 1.9;
    font-size: 14pt;
    color: #1e293b;
    hyphens: none;
    -webkit-hyphens: none;
    font-feature-settings: "kern" 1, "liga" 1;
  }}

  .m-main-heading {{
    font-family: 'Cairo', sans-serif;
    font-size: 15pt;
    font-weight: 700;
    color: #7c2d12;
    margin: 18px 0 10px 0;
  }}

  .m-heading {{
    font-family: 'Cairo', sans-serif;
    font-size: 14pt;
    font-weight: 700;
    color: #92400e;
    margin: 16px 0 8px 0;
  }}

  .m-subheading {{
    font-family: 'Cairo', sans-serif;
    font-size: 13pt;
    font-weight: 700;
    color: #1e293b;
    margin: 14px 0 6px 0;
  }}

  /* Quotation Cards (Golden Callout Boxes matching portal) */
  .quote-card {{
    background: #fffbeb;
    border-right: 4px solid #d97706;
    border-left: 1px solid #fef3c7;
    border-top: 1px solid #fef3c7;
    border-bottom: 1px solid #fef3c7;
    border-radius: 6px;
    padding: 14px 20px;
    margin: 16px 0;
    page-break-inside: avoid;
  }}

  .quote-text {{
    font-size: 13.5pt;
    font-style: italic;
    color: #1c1917;
    line-height: 1.8;
  }}

  .quote-src {{
    font-size: 11pt;
    font-weight: 700;
    color: #92400e;
    margin-top: 8px;
    text-align: left;
    direction: rtl;
  }}

  /* Bullets matching Portal */
  .m-bullet-list {{
    margin: 10px 0 16px 0;
    padding-right: 22px;
  }}

  .m-bullet-list li {{
    margin-bottom: 8px;
    line-height: 1.75;
  }}

  /* Flattened Table Row Card (Zero Rigid Tables!) */
  .table-card-row {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 14px;
    margin: 8px 0;
    font-size: 12.5pt;
    color: #334155;
    font-weight: 600;
  }}

  /* Turn Citations Bar */
  .turn-citations-card {{
    margin-top: 18px;
    padding: 12px 16px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    page-break-inside: avoid;
  }}

  .citations-header {{
    font-family: 'Cairo', sans-serif;
    font-size: 11pt;
    font-weight: 700;
    color: #7c2d12;
    margin-bottom: 8px;
  }}

  .citations-pills-wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .ref-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 20px;
    padding: 4px 10px;
    font-size: 10.5pt;
    color: #334155;
  }}

  .ref-title {{
    font-weight: 700;
    color: #1e293b;
  }}

  .ref-meta {{
    color: #64748b;
  }}

  .ref-tier-badge {{
    background: #f1f5f9;
    color: #0369a1;
    font-size: 9pt;
    font-family: 'Cairo', sans-serif;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 10px;
  }}

  /* Bibliography Cards (Replaces Rigid 4-Column Tables!) */
  .biblio-section-card {{
    border-right-color: #0f766e;
    page-break-before: always;
  }}

  .biblio-intro {{
    font-size: 12pt;
    color: #64748b;
    margin: 0 0 16px 0;
  }}

  .biblio-cards-grid {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .biblio-card {{
    display: flex;
    align-items: center;
    gap: 14px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 16px;
    transition: all 0.2s ease;
    page-break-inside: avoid;
  }}

  .bib-index {{
    font-family: 'Cairo', sans-serif;
    font-size: 12pt;
    font-weight: 800;
    background: #f1f5f9;
    color: #0f766e;
    min-width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  .bib-details {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .bib-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .bib-title {{
    font-size: 13.5pt;
    color: #0f172a;
    font-weight: 700;
  }}

  .bib-author {{
    font-size: 11.5pt;
    color: #874f19;
    font-weight: 600;
  }}

  .bib-meta-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10.5pt;
    color: #64748b;
  }}

  .bib-badge {{
    background: #ccfbf1;
    color: #0f766e;
    font-family: 'Cairo', sans-serif;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 9.5pt;
  }}

  /* Floating Print Action Bar (Hidden when printing) */
  .no-print {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #0f172a;
    color: #ffffff;
    padding: 12px 24px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-family: 'Cairo', sans-serif;
  }}

  .btn-print-action {{
    background: #d97706;
    color: #ffffff;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    font-size: 12pt;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .btn-print-action:hover {{
    background: #b45309;
  }}


    /* Mobile Phone & Tablet Optimization (عرض فاخر ومتجاوب 100% على شاشات الموبايل) */
  @media (max-width: 768px) {{
    html, body {{
      font-size: 13pt;
      background-color: #ffffff;
      padding: 0;
      margin: 0;
      width: 100vw;
      max-width: 100vw;
      overflow-x: hidden;
    }}
    .page-wrapper {{
      width: 100% !important;
      max-width: 100% !important;
      padding: 12px 10px;
      box-shadow: none;
      border-radius: 0;
      box-sizing: border-box;
      overflow-x: hidden;
    }}
    .no-print {{
      flex-direction: column;
      align-items: stretch;
      gap: 10px;
      padding: 12px;
      border-radius: 8px;
      width: 100% !important;
      max-width: 100% !important;
      box-sizing: border-box;
    }}
    .no-print > div:first-child {{
      text-align: center;
    }}
    .no-print div[style*="display:flex"] {{
      justify-content: center;
      gap: 6px;
      width: 100%;
      box-sizing: border-box;
    }}
    .btn-print-action {{
      font-size: 9.5pt;
      padding: 6px 10px;
      flex: 1 1 calc(50% - 6px);
      max-width: calc(50% - 6px);
      justify-content: center;
      text-align: center;
      box-sizing: border-box;
    }}
    .doc-title {{
      font-size: 16pt;
      line-height: 1.4;
      word-break: break-word;
    }}
    .church-brand {{
      font-size: 9pt;
      word-break: break-word;
    }}
    .doc-subtitle {{
      font-size: 10.5pt;
    }}
    .meta-bar {{
      flex-direction: column;
      align-items: stretch;
      gap: 6px;
      width: 100%;
      box-sizing: border-box;
    }}
    .axis-title {{
      font-size: 13pt;
      word-break: break-word;
    }}
    .ref-card {{
      padding: 10px;
      box-sizing: border-box;
      max-width: 100%;
    }}
    .ref-item {{
      padding: 10px;
      box-sizing: border-box;
      max-width: 100%;
    }}
    .toc-container {{
      padding: 12px;
      box-sizing: border-box;
      max-width: 100%;
    }}
  }}

  /* Printing Overrides */
  @media print {{
    body {{
      background: #ffffff !important;
      font-size: 12pt !important;
    }}
    .page-wrapper {{
      max-width: 100% !important;
      padding: 0 !important;
      box-shadow: none !important;
      border-radius: 0 !important;
    }}
    .no-print {{
      display: none !important;
    }}
    .mبحث-card {{
      box-shadow: none !important;
      border: 1px solid #cbd5e1 !important;
      border-right: 4px solid #7c2d12 !important;
    }}
  }}
</style>
</head>
<body>

<div class="page-wrapper">
  <!-- Screen Floating Print Action -->
  <div class="no-print">
    <div>
      <div style="font-size: 13pt; font-weight: 800; color: #f59e0b;">✠ أمانة التوثيق والبحث اللاهوتي الأكاديمي</div>
      <div style="font-size: 10pt; opacity: 0.85;">معاينة جاهزة للطباعة بجودة النشر A4، أو الإرسال والمشاركة بنقرة واحدة</div>
    </div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
      <button class="btn-print-action" onclick="window.print()" title="طباعة الأطروحة بنمط A4 الفاخر">
        <span>🖨️</span> طباعة فورية (Ctrl + P)
      </button>
      <button class="btn-print-action" style="background:#dc2626;" onclick="downloadPdfFile()" title="تحميل ملف PDF مطبوع جاهز">
        <span>📕</span> تحميل PDF
      </button>
      <button class="btn-print-action" style="background:#059669;" onclick="downloadStandaloneHtml()" title="حفظ المستند بالكامل كملف مستقل لإرساله عبر واتساب أو تليجرام أو فتحه دون إنترنت">
        <span>📥</span> حفظ ملف المعاينة (.html)
      </button>
      <button class="btn-print-action" style="background:#0284c7;" onclick="copyPreviewLink()" title="نسخ رابط هذه المعاينة المباشر لمشاركته مع أي باحث">
        <span>🔗</span> نسخ الرابط
      </button>
      <button class="btn-print-action" style="background:#16a34a;" onclick="shareViaWhatsApp()" title="إرسال رابط المعاينة عبر واتساب">
        <span>💬</span> واتساب
      </button>
      <button class="btn-print-action" style="background:#2563eb;" onclick="shareViaTelegram()" title="إرسال رابط المعاينة عبر تليجرام">
        <span>✈️</span> تليجرام
      </button>
      <button class="btn-print-action" style="background:#475569;" onclick="closePreview()" title="إغلاق المعاينة">
        <span>✕</span>
      </button>
    </div>
  </div>

  <!-- Document Header -->
  <header class="doc-header">
    <div class="church-brand">✠ كنيسة الإسكندرية القبطية الأرثوذكسية &mdash; مكتبة الدراسات الآبائية واللاهوتية ✠</div>
    <h1 class="doc-title">« {title} »</h1>
    <div class="doc-subtitle">أطروحة بحثية لاهوتية آبائية مجمعة وموثقة من أمهات الكتب الكنسية المعتمدة</div>
  </header>

  <!-- Metadata Summary Bar (Zero Table) -->
  <div class="meta-bar">
    <div class="meta-chip">📅 تاريخ التوثيق: <strong>{doc_date}</strong></div>
    <div class="meta-chip">📑 عدد المباحث: <strong>{len(turns)} محاور</strong></div>
    <div class="meta-chip">🏛️ المراجع الموثقة: <strong>{len(bibliography)} مصدراً</strong></div>
    <div class="meta-chip">🔒 مرتبة التحقيق: <strong>أمانة التوثيق الكنسي</strong></div>
  </div>

  <!-- Mubahith Chapters Section -->
  <main>
    {"".join(mubahith_html)}
    {bib_section_html}
  </main>
</div>
"""
    return html_body + PREVIEW_TOOLBAR_JS + """
</body>
</html>"""
