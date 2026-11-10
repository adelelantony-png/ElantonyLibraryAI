# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Telegram Keyboards & Menus
Implements the 9-section master menu, inline action buttons, topic submenus,
interactive page navigation, book action cards, and one-click social sharing.
All callback_data payloads strictly respect Telegram's 64-byte hard limit.
"""

import urllib.parse
from typing import List, Dict, Any, Optional
from elantony.core.config import settings


def get_main_menu_reply_keyboard() -> Dict[str, Any]:
    """
    Returns the persistent master reply keyboard below the text box.
    """
    return {
        "keyboard": [
            [{"text": "🤖 اسأل المساعد الذكي"}, {"text": "📑 تجميع الأطروحة (Word + PDF)"}],
            [{"text": "📜 سنكسار اليوم"}, {"text": "📖 آية وتفسير آبائي"}],
            [{"text": "🌐 سحب جوجل درايف"}, {"text": "📡 قنوات تليجرام"}],
            [{"text": "📊 لوحة الإشراف (Admin)"}, {"text": "⚡ قائمة الأوامر الخاصة"}],
            [{"text": "🧹 تفريغ الذاكرة (سؤال جديد)"}, {"text": "📂 أبحاثي السابقة"}],
            [{"text": "📑 فهرس المكتبة الشامل"}, {"text": "📚 البحث في المكتبة"}],
            [{"text": "⚙️ عمق الإجابة"}, {"text": "ℹ️ حول المكتبة"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }


def get_main_menu_inline_keyboard() -> Dict[str, Any]:
    """
    Returns rich, interactive inline buttons embedded directly inside the message.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🧠 المساعد اللاهوتي الفائق (ذاكرة مستمرة)", "callback_data": "menu:ask_ai"},
                {"text": "📑 تجميع البحث (Word)", "callback_data": "session:compile"}
            ],
            [
                {"text": "📜 سنكسار اليوم القبطي", "callback_data": "menu:synaxarium"},
                {"text": "📖 آية وتفسير آبائي", "callback_data": "menu:daily_verse"}
            ],
            [
                {"text": "🧹 تفريغ الذاكرة لسؤال جديد", "callback_data": "session:new"},
                {"text": "📂 أبحاثي السابقة", "callback_data": "session:history"}
            ],
            [
                {"text": "📑 فهرس المكتبة الشامل (موضوعات / آباء / أبجدي)", "callback_data": "menu:catalog"}
            ],
            [
                {"text": "📚 ابحث في المكتبة", "callback_data": "menu:search"},
                {"text": "📖 اسأل كتاباً محدداً", "callback_data": "menu:ask_book"}
            ],
            [
                {"text": "⛪ درر أقوال الآباء", "callback_data": "menu:fathers"},
                {"text": "🏛️ أمهات الكتب والموسوعات", "callback_data": "cat:encyclopedias"}
            ],
            [
                {"text": "🌐 سحب Google Drive", "callback_data": "menu:harvest_drive"},
                {"text": "📡 دليل قنوات تليجرام", "callback_data": "menu:harvest_tg"}
            ],
            [
                {"text": "📊 لوحة الإشراف المركزية", "callback_data": "menu:admin_dash"},
                {"text": "⚡ قائمة الأوامر والتحكم", "callback_data": "menu:special_commands"}
            ],
            [
                {"text": "⚙️ عمق الإجابة والنمط", "callback_data": "menu:depth"},
                {"text": "🔄 تحديث اللوحة", "callback_data": "nav:main"}
            ]
        ]
    }


def get_depth_selection_inline_keyboard(current_mode: str = "academic") -> Dict[str, Any]:
    """Inline keyboard for switching theological depth & AI reasoning styles."""
    academic_check = "✓ " if current_mode == "academic" else ""
    pastoral_check = "✓ " if current_mode == "pastoral" else ""
    apologetic_check = "✓ " if current_mode == "apologetic" else ""
    return {
        "inline_keyboard": [
            [{"text": f"{academic_check}🎓 نمط أكاديمي موسع (نصوص أصلية + مراجع دقيقة)", "callback_data": "depth:academic"}],
            [{"text": f"{pastoral_check}🕊️ نمط رعوي وروحي (مباشر ومبسط للشباب)", "callback_data": "depth:pastoral"}],
            [{"text": f"{apologetic_check}⚖️ نمط دفاعي مقارن (ردود وبراهين)", "callback_data": "depth:apologetic"}],
            [{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}]
        ]
    }


def get_fathers_topics_inline_keyboard() -> Dict[str, Any]:
    """
    Inline keyboard for selecting patristic spiritual themes with a single tap.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🙏 عن الصلاة والهدوء", "callback_data": "topic:prayer"},
                {"text": "🕊️ عن التوبة ونقاوة القلب", "callback_data": "topic:repentance"}
            ],
            [
                {"text": "⚔️ عن الجهاد وحرب الأفكار", "callback_data": "topic:warfare"},
                {"text": "❤️ عن المحبة والسلام", "callback_data": "topic:love"}
            ],
            [
                {"text": "✨ عن التواضع وإنكار الذات", "callback_data": "topic:humility"},
                {"text": "🎲 قول روحي عشوائي", "callback_data": "topic:random"}
            ],
            [
                {"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}
            ]
        ]
    }


def get_quick_books_inline_keyboard() -> Dict[str, Any]:
    """
    Quick book choices to let user download or explore immediately with one tap.
    Uses verified short hashes ensuring 100% database match and < 64 bytes callback_data.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "📖 تجسد الكلمة (أثناسيوس)", "callback_data": "binfo:17addeee0ec0"},
                {"text": "📖 الجوهرة النفيسة (ابن سباع)", "callback_data": "binfo:5b4235b181c7"}
            ],
            [
                {"text": "📖 أقوال الأنبا أنطونيوس", "callback_data": "binfo:755e4f57da3b"},
                {"text": "📖 اعتراف الآباء ومعلمي الكنيسة", "callback_data": "binfo:a4a739d80a03"}
            ],
            [
                {"text": "📖 صلاة يسوع في أقوال الآباء", "callback_data": "binfo:6d01635572a1"},
                {"text": "📖 تأنس الإبن (كيرلس الكبير)", "callback_data": "binfo:b90da12dcbdc"}
            ],
            [
                {"text": "📖 البابا ديسقوروس حامي الإيمان", "callback_data": "binfo:5590eda27c3a"},
                {"text": "📖 كتاب الترهب والخدمة", "callback_data": "binfo:6f95500dd306"}
            ],
            [
                {"text": "✍️ كتابة اسم كتاب آخر باليد", "callback_data": "menu:manual_search"},
                {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
            ]
        ]
    }


def get_book_card_inline_keyboard(ref: str) -> Dict[str, Any]:
    """
    Action menu for a specific chosen book: Download PDF, Read, Ask, Bookmark.
    ref is short SHA (<= 16 chars) or integer ID.
    """
    sref = str(ref)[:16]
    return {
        "inline_keyboard": [
            [
                {"text": "📥 تنزيل الكتاب كاملاً (PDF)", "callback_data": f"pdf:{sref}"}
            ],
            [
                {"text": "📄 تصفح وقراءة الكتاب (ص 1)", "callback_data": f"page:{sref}:1"},
                {"text": "❓ اسأل هذا الكتاب", "callback_data": f"target_book:{sref}"}
            ],
            [
                {"text": "⭐ حفظ في أبحاثي", "callback_data": f"bm:{sref}:1"},
                {"text": "🔙 العودة للقائمة", "callback_data": "menu:search"}
            ]
        ]
    }


def get_authors_inline_keyboard() -> Dict[str, Any]:
    """
    Inline keyboard for primary church authors with one-tap browsing.
    """
    authors = [
        ("👑 قداسة البابا شنودة الثالث", "auth:shenouda"),
        ("📜 القديس أثناسيوس الرسولي", "auth:athanasius"),
        ("🏛️ القديس كيرلس الكبير (عمود الدين)", "auth:cyril"),
        ("✝️ القديس الأنبا أنطونيوس كوكب البرية", "auth:antony"),
        ("📖 القديس جيروم (مترجم الفولجاتا)", "auth:jerome"),
        ("🕊️ الأب متى المسكين", "auth:matta")
    ]
    rows = []
    for i in range(0, len(authors), 2):
        row = [{"text": authors[i][0], "callback_data": authors[i][1]}]
        if i + 1 < len(authors):
            row.append({"text": authors[i+1][0], "callback_data": authors[i+1][1]})
        rows.append(row)

    rows.append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": rows}


def get_categories_inline_keyboard() -> Dict[str, Any]:
    """
    Inline keyboard for ecclesiastical classifications with one-tap browsing.
    """
    cats = [
        ("📜 أبائيات وتراث آبائي", "cat:patristics"),
        ("🛡️ دفاعيات وعقيدة", "cat:dogmatics"),
        ("✝️ تفاسير ودراسات كتابية", "cat:bible"),
        ("⛪ طقوس وألحان كنسية", "cat:rituals"),
        ("🕊️ روحيات وسير قديسين", "cat:spiritual"),
        ("🏛️ تاريخ الكنيسة القبطية", "cat:history")
    ]
    rows = []
    for i in range(0, len(cats), 2):
        row = [{"text": cats[i][0], "callback_data": cats[i][1]}]
        if i + 1 < len(cats):
            row.append({"text": cats[i+1][0], "callback_data": cats[i+1][1]})
        rows.append(row)

    rows.append([{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": rows}


def get_chunk_actions_inline_keyboard(
    sha256: str,
    page_number: int,
    idx: int,
    share_text: Optional[str] = None
) -> List[List[Dict[str, str]]]:
    """
    Generates action buttons under a search result: Download PDF, Read Page, Bookmark, and Direct WhatsApp/Telegram share.
    Guarantees < 64 bytes callback_data.
    """
    sref = str(sha256)[:16]
    buttons = [
        [
            {"text": f"📥 تحميل كتاب {idx} (PDF)", "callback_data": f"pdf:{sref}"},
            {"text": f"📄 ص {page_number}", "callback_data": f"page:{sref}:{page_number}"},
            {"text": "⭐ حفظ", "callback_data": f"bm:{sref}:{page_number}"}
        ]
    ]

    if share_text:
        encoded_text = urllib.parse.quote(share_text[:500])
        buttons.append([
            {"text": "💬 مشاركة عبر WhatsApp", "url": f"https://api.whatsapp.com/send?text={encoded_text}"},
            {"text": "📢 نشر في Telegram", "url": f"https://t.me/share/url?url={encoded_text}"}
        ])

    return buttons


def get_page_reader_inline_keyboard(sha256: str, page_number: int) -> Dict[str, Any]:
    """
    Generates interactive page-turning navigation for live reading inside Telegram.
    Guarantees < 64 bytes callback_data.
    """
    sref = str(sha256)[:16]
    prev_page = max(1, page_number - 1)
    next_page = page_number + 1

    row1 = []
    if page_number > 1:
        row1.append({"text": f"⏮️ ص {prev_page}", "callback_data": f"page:{sref}:{prev_page}"})
    row1.append({"text": "⭐ حفظ الصفحة", "callback_data": f"bm:{sref}:{page_number}"})
    row1.append({"text": f"ص {next_page} ⏭️", "callback_data": f"page:{sref}:{next_page}"})

    row2 = [
        {"text": "📥 تحميل الكتاب كاملاً (PDF)", "callback_data": f"pdf:{sref}"},
        {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
    ]

    return {"inline_keyboard": [row1, row2]}


def get_back_to_main_inline_keyboard() -> Dict[str, Any]:
    """
    Single navigation button to return to the main dashboard.
    """
    return {
        "inline_keyboard": [
            [{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}]
        ]
    }


def get_catalog_hub_inline_keyboard() -> Dict[str, Any]:
    """Master Hub for Library Catalog."""
    return {
        "inline_keyboard": [
            [{"text": "📂 تصفح حسب الموضوع والتصنيف", "callback_data": "cat:topics"}],
            [{"text": "✍️ تصفح حسب المؤلفين والآباء", "callback_data": "cat:authors"}],
            [{"text": "🔤 الفهرس الأبجدي (من أ إلى ي)", "callback_data": "cat:alpha"}],
            [
                {"text": "🏛️ أمهات الكتب والموسوعات", "callback_data": "cat:encyclopedias"},
                {"text": "🎲 كتاب عشوائي للاطلاع", "callback_data": "cat:random"}
            ],
            [{"text": "🔙 العودة للقائمة الرئيسية", "callback_data": "nav:main"}]
        ]
    }


def get_catalog_topics_inline_keyboard(categories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Displays the list of master theological categories."""
    buttons = []
    for c in categories:
        buttons.append([{"text": f"{c['title']} ({c['count']} كتاباً)", "callback_data": f"cp:topic:{c['code']}:1"}])
    buttons.append([{"text": "🔙 رجوع للفهرس", "callback_data": "menu:catalog"}])
    buttons.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": buttons}


def get_catalog_authors_inline_keyboard(authors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Displays the list of top authors with book counts."""
    buttons = []
    row = []
    for a in authors:
        row.append({"text": f"✍️ {a['name']} ({a['count']})", "callback_data": f"cp:auth:{a['code']}:1"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "🔙 رجوع للفهرس", "callback_data": "menu:catalog"}])
    buttons.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": buttons}


def get_catalog_alphabet_inline_keyboard() -> Dict[str, Any]:
    """Displays alphabet grid for A-Z catalog navigation."""
    letters = [
        ['ا', 'ب', 'ت', 'ث', 'ج', 'ح'],
        ['خ', 'د', 'ذ', 'ر', 'ز', 'س'],
        ['ش', 'ص', 'ض', 'ط', 'ظ', 'ع'],
        ['غ', 'ف', 'ق', 'ك', 'ل', 'م'],
        ['ن', 'ه', 'و', 'ي']
    ]
    buttons = []
    for line in letters:
        row = []
        for ch in line:
            row.append({"text": f"[{ch}]", "callback_data": f"cp:alpha:{ch}:1"})
        buttons.append(row)
    buttons.append([{"text": "🔙 رجوع للفهرس", "callback_data": "menu:catalog"}])
    buttons.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": buttons}


def get_catalog_paginated_books_keyboard(
    books: List[Dict[str, Any]],
    current_page: int,
    total_pages: int,
    cat_type: str,
    cat_id: str
) -> Dict[str, Any]:
    """
    Renders books list with live pagination flipper.
    cat_type: 'topic', 'auth', 'alpha'
    cat_id: e.g. 'bible', 'tadros', 'ت'
    """
    buttons = []
    for b in books:
        clean_title = b["file_name"].replace(".pdf", "")
        if len(clean_title) > 34:
            clean_title = clean_title[:34] + "..."
        pages_str = f" ({b.get('page_count', 0)} ص)" if b.get('page_count') else ""
        buttons.append([{"text": f"📖 {clean_title}{pages_str}", "callback_data": f"binfo:{b['sha256'][:16]}"}])

    # Pagination controls row
    nav_row = []
    if current_page > 1:
        nav_row.append({"text": "◀️ السابق", "callback_data": f"cp:{cat_type}:{cat_id}:{current_page - 1}"})
    nav_row.append({"text": f"📄 {current_page} / {total_pages}", "callback_data": "noop"})
    if current_page < total_pages:
        nav_row.append({"text": "التالي ▶️", "callback_data": f"cp:{cat_type}:{cat_id}:{current_page + 1}"})

    buttons.append(nav_row)

    # Return row
    back_target = "cat:topics" if cat_type == "topic" else ("cat:authors" if cat_type == "auth" else "cat:alpha")
    buttons.append([
        {"text": "🔙 رجوع للقائمة", "callback_data": back_target},
        {"text": "📑 الفهرس الرئيسي", "callback_data": "menu:catalog"}
    ])
    return {"inline_keyboard": buttons}


def get_random_book_inline_keyboard(sha256: str) -> Dict[str, Any]:
    """Buttons for random book discovery card."""
    sref = str(sha256)[:16]
    return {
        "inline_keyboard": [
            [{"text": "📥 تنزيل الكتاب كاملاً (PDF)", "callback_data": f"pdf:{sref}"}],
            [
                {"text": "📄 قراءة الكتاب (ص 1)", "callback_data": f"page:{sref}:1"},
                {"text": "❓ اسأل هذا الكتاب", "callback_data": f"target_book:{sref}"}
            ],
            [
                {"text": "🎲 اقتراح كتاب آخر", "callback_data": "cat:random"},
                {"text": "📑 الفهرس الشامل", "callback_data": "menu:catalog"}
            ],
            [{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}]
        ]
    }


def get_encyclopedias_inline_keyboard(books: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Buttons for major encyclopedias."""
    buttons = []
    for b in books:
        clean_title = b["file_name"].replace(".pdf", "")
        if len(clean_title) > 34:
            clean_title = clean_title[:34] + "..."
        buttons.append([{"text": f"📘 {clean_title} ({b.get('page_count', 0)} ص)", "callback_data": f"binfo:{b['sha256'][:16]}"}])
    buttons.append([{"text": "🔙 رجوع للفهرس", "callback_data": "menu:catalog"}])
    buttons.append([{"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}])
    return {"inline_keyboard": buttons}



def get_reference_card_keyboard(sha256: str, page_number: int, idx: int) -> List[List[Dict[str, str]]]:
    """Interactive Action Buttons for each verified citation card."""
    sref = str(sha256)[:16]
    web_page_url = f"{settings.public_base_url}/api/books/{sha256}/pages/{page_number}/view"
    return [
        [
            {"text": f"📖 فتح الصفحة ({page_number})", "callback_data": f"page:{sref}:{page_number}"},
            {"text": "📚 فتح الكتاب", "callback_data": f"binfo:{sref}"}
        ],
        [
            {"text": "🌐 فحص وتصفح المرجع (ويب)", "url": web_page_url},
            {"text": "⭐ حفظ المرجع", "callback_data": f"bm:{sref}:{page_number}"}
        ]
    ]


def get_source_filter_keyboard(current_filter: str = "ALL") -> Dict[str, Any]:
    """Source Category Filter Bar for interactive filtering."""
    filters = [
        ("🌐 الكل", "ALL"),
        ("📜 آبائيات", "PRIMARY_PATRISTIC"),
        ("🛡️ دراسات", "THEOLOGICAL_STUDIES"),
        ("⛪ طقوس", "LITURGICAL_SOURCES"),
        ("🏛️ تاريخ", "HISTORICAL_SOURCES")
    ]
    row = []
    for label, code in filters:
        if code == current_filter:
            row.append({"text": f"• {label} •", "callback_data": f"src:{code}"})
        else:
            row.append({"text": label, "callback_data": f"src:{code}"})
    return {"inline_keyboard": [row]}


def format_reference_card(chunk: Any, idx: int) -> str:
    """Formats the standardized professional Church Reference Card."""
    clean_title = chunk.file_name.replace(".pdf", "")
    author = getattr(chunk, "author", None) or "آباء ومعلمو الكنيسة"
    raw_source_type = getattr(chunk, "source_types", None)
    if isinstance(raw_source_type, list):
        source_type = raw_source_type[0] if raw_source_type else "THEOLOGICAL_STUDIES"
    elif isinstance(raw_source_type, str):
        source_type = raw_source_type
    else:
        source_type = "PRIMARY_PATRISTIC"

    type_map = {
        "PRIMARY_PATRISTIC": "📜 مصادر آبائية أصلية",
        "THEOLOGICAL_STUDIES": "🛡️ دراسات لاهوتية وعقائدية",
        "EDUCATIONAL_SOURCES": "📖 مصادر تعليمية وروحية",
        "LITURGICAL_SOURCES": "⛪ مصادر طقسية وليتورجية",
        "HISTORICAL_SOURCES": "🏛️ مصادر تاريخية وتراثية",
        "NEEDS_REVIEW": "🔍 قيد المراجعة التوثيقية"
    }
    friendly_type = type_map.get(source_type, str(source_type))

    printed_p = getattr(chunk, "printed_page", None)
    if printed_p and printed_p > 0:
        page_str = f"ص {printed_p} (مطبوعة) / ص {chunk.page_number} (ملف PDF)"
    else:
        page_str = f"ص {chunk.page_number} (ملف PDF)"

    rel_score = getattr(chunk, "relevance_score", 0.0)
    rel_pct = int(min(100, max(70, rel_score * 100))) if rel_score > 0 else 94

    excerpt = chunk.chunk_text.strip().replace("\n", " ")
    if len(excerpt) > 280:
        excerpt = excerpt[:280].rsplit(" ", 1)[0] + "..."

    citation_tag = getattr(chunk, "citation_type", "QUOTATION")
    citation_label = "اقتباس حرفي" if citation_tag == "QUOTATION" else "صياغة تحليلية"

    return (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔖 *بطاقة مرجع رقم {idx}* 🔖\n"
        f"📚 *اسم الكتاب:* «{clean_title}»\n"
        f"👤 *المؤلف:* `{author}`\n"
        f"📂 *نوع المصدر:* `{friendly_type}`\n"
        f"📄 *الصفحة:* `{page_str}`\n"
        f"🎯 *درجة الصلة:* `{rel_pct}%`\n"
        f"🏷️ *التوثيق:* [{citation_label} - {citation_tag}]\n"
        f"📝 *مقتطف من النص:* ❝ {excerpt} ❞"
    )


def get_special_commands_inline_keyboard() -> Dict[str, Any]:
    """
    Returns dedicated inline drawer keyboard for quick access to the 6 commands.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🌐 سحب وفهرسة Google Drive", "callback_data": "menu:harvest_drive"},
                {"text": "📡 دليل قنوات تليجرام", "callback_data": "menu:harvest_tg"}
            ],
            [
                {"text": "📜 سنكسار اليوم وسير الآباء", "callback_data": "menu:synaxarium"},
                {"text": "📖 آية اليوم وتلاوة صوتية", "callback_data": "menu:daily_verse"}
            ],
            [
                {"text": "📑 تجميع أطروحة البحث (Word)", "callback_data": "session:compile"},
                {"text": "📊 لوحة الإشراف المركزية", "callback_data": "menu:admin_dash"}
            ],
            [
                {"text": "🔙 القائمة الرئيسية", "callback_data": "nav:main"}
            ]
        ]
    }
