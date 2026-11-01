# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Telegram Keyboards & Menus
Implements the 9-section master menu, inline action buttons, topic submenus,
interactive page navigation, book action cards, and one-click social sharing.
All callback_data payloads strictly respect Telegram's 64-byte hard limit.
"""

import urllib.parse
from typing import List, Dict, Any, Optional


def get_main_menu_reply_keyboard() -> Dict[str, Any]:
    """
    Returns the persistent 9-section master reply keyboard below the text box.
    """
    return {
        "keyboard": [
            [{"text": "🤖 المساعد الذكي"}, {"text": "📚 البحث في المكتبة"}],
            [{"text": "📖 اسأل كتابًا"}, {"text": "⛪ أقوال الآباء"}],
            [{"text": "🔍 البحث حسب المؤلف"}, {"text": "📂 تصفح التصنيفات"}],
            [{"text": "📑 أبحاثي المحفوظة"}, {"text": "⚙️ الإعدادات"}],
            [{"text": "ℹ️ حول المكتبة"}]
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
                {"text": "🤖 اسأل المساعد الذكي", "callback_data": "menu:ask_ai"},
                {"text": "📚 ابحث في المكتبة", "callback_data": "menu:search"}
            ],
            [
                {"text": "📖 اسأل كتاباً محدداً", "callback_data": "menu:ask_book"},
                {"text": "⛪ درر أقوال الآباء", "callback_data": "menu:fathers"}
            ],
            [
                {"text": "🔍 كبار معلمي الكنيسة", "callback_data": "menu:authors"},
                {"text": "📂 تصفح أقسام المكتبة", "callback_data": "menu:categories"}
            ],
            [
                {"text": "📑 أبحاثي وشواهدي المحفوظة", "callback_data": "menu:bookmarks"},
                {"text": "📊 إحصائيات المكتبة", "callback_data": "menu:stats"}
            ],
            [
                {"text": "🕊️ تأمل وتدريب اليوم الروحي", "callback_data": "menu:daily"},
                {"text": "ℹ️ حول المكتبة", "callback_data": "menu:about"}
            ],
            [
                {"text": "🔄 تحديث اللوحة", "callback_data": "nav:main"}
            ]
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
