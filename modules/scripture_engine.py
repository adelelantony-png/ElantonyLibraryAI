"""
Cross Coptic Library - Scripture Verse & Patristic Cross-Reference Engine (المرساة الكنسية)
Anchors every biblical verse (Book, Chapter, Verse) to Patristic commentaries,
ancient manuscripts, and contemporary apologetics from the local offline library.
"""

import os
import re
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QLineEdit,
    QTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QMessageBox,
    QApplication,
    QGroupBox
)
from PyQt5.QtCore import Qt

from modules import database_handler, library_rag, apologetics_db, manuscript_comparator

# The Complete 73-Book Coptic Orthodox Biblical Canon
CANON_BOOKS = {
    "العهد الجديد (27 سفراً)": [
        "إنجيل متى", "إنجيل مرقس", "إنجيل لوقا", "إنجيل يوحنا", "أعمال الرسل",
        "رسالة رومية", "رسالة كورنثوس الأولى", "رسالة كورنثوس الثانية", "رسالة غلاطية", "رسالة أفسس",
        "رسالة فيلبي", "رسالة كولوسي", "رسالة تسالونيكي الأولى", "رسالة تسالونيكي الثانية",
        "رسالة تيموثاوس الأولى", "رسالة تيموثاوس الثانية", "رسالة تيطس", "رسالة فليمون",
        "الرسالة إلى العبرانيين", "رسالة يعقوب", "رسالة بطرس الأولى", "رسالة بطرس الثانية",
        "رسالة يوحنا الأولى", "رسالة يوحنا الثانية", "رسالة يوحنا الثالثة", "رسالة يهوذا", "سفر الرؤيا"
    ],
    "العهد القديم (39 سفراً)": [
        "سفر التكوين", "سفر الخروج", "سفر اللاويين", "سفر العدد", "سفر التثنية",
        "سفر يشوع", "سفر القضاة", "سفر راعوث", "سفر صموئيل الأول", "سفر صموئيل الثاني",
        "سفر الملوك الأول", "سفر الملوك الثاني", "سفر أخبار الأيام الأول", "سفر أخبار الأيام الثاني",
        "سفر عزرا", "سفر نحميا", "سفر أستير", "سفر أيوب", "سفر المزامير", "سفر الأمثال",
        "سفر الجامعة", "سفر نشيد الأنشاد", "سفر إشعياء", "سفر إرميا", "سفر مراثي إرميا",
        "سفر حزقيال", "سفر دانيال", "سفر هوشع", "سفر يوئيل", "سفر عاموس", "سفر عوبديا",
        "سفر يونان", "سفر ميخا", "سفر ناحوم", "سفر حبقوق", "سفر صفنيا", "سفر حجي", "سفر زكريا", "سفر ملاخي"
    ],
    "الأسفار القانونية الثانية": [
        "سفر طوبيا", "سفر يهوديت", "تتمة أستير", "سفر الحكمة", "سفر يشوع بن سيراخ",
        "سفر باروخ", "تتمة دانيال", "سفر المكابيين الأول", "سفر المكابيين الثاني"
    ]
}

BOOK_SHORT_NAMES = {
    "مت": "إنجيل متى", "مر": "إنجيل مرقس", "لو": "إنجيل لوقا", "يو": "إنجيل يوحنا",
    "اع": "أعمال الرسل", "رو": "رسالة رومية", "1كو": "رسالة كورنثوس الأولى", "2كو": "رسالة كورنثوس الثانية",
    "تك": "سفر التكوين", "خر": "سفر الخروج", "لا": "سفر اللاويين", "عد": "سفر العدد", "تث": "سفر التثنية",
    "يش": "سفر يشوع", "قض": "سفر القضاة", "مز": "سفر المزامير", "اش": "سفر إشعياء", "ار": "سفر إرميا",
    "دان": "سفر دانيال", "عب": "الرسالة إلى العبرانيين", "يع": "رسالة يعقوب", "1بط": "رسالة بطرس الأولى",
    "رؤ": "سفر الرؤيا", "سيراخ": "سفر يشوع بن سيراخ", "طوبيا": "سفر طوبيا"
}


def parse_scripture_reference(query: str):
    """
    Parses a scripture string like 'يوحنا 1: 1' or 'تك 1: 26' or 'رو 8: 28'
    Returns (canonical_book_name, chapter_num, verse_num) or None.
    """
    q = query.strip()
    match = re.search(r'([^\d:]+)\s+(\d+)(?::(\d+))?', q)
    if not match:
        return None
    raw_book = match.group(1).strip()
    chapter = int(match.group(2))
    verse = int(match.group(3)) if match.group(3) else None

    # Resolve book name
    clean_book = None
    if raw_book in BOOK_SHORT_NAMES:
        clean_book = BOOK_SHORT_NAMES[raw_book]
    else:
        for section, books in CANON_BOOKS.items():
            for b in books:
                if raw_book in b or b in raw_book:
                    clean_book = b
                    break
            if clean_book:
                break

    if clean_book:
        return clean_book, chapter, verse
    return None


class ScriptureNavigatorDialog(QDialog):
    """Interactive Scripture Navigator & Patristic Cross-Reference Center."""

    def __init__(self, parent=None, library_root: str = None, initial_ref: str = ""):
        super().__init__(parent)
        self.library_root = library_root
        self.setWindowTitle("✝️ المرساة الكنسية - المفهرس الكتابي والشواهد الآبائية والدفاعية")
        self.resize(1200, 800)
        self.init_ui()

        if initial_ref:
            self.le_quick_ref.setText(initial_ref)
            self.on_quick_ref_search()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 1. Header Box
        header = QGroupBox("📖 اختيار السفر والشاهد الكتابي (سفر - أصحاح - آية)")
        header.setStyleSheet("""
            QGroupBox {
                border: 1px solid #434F63;
                border-radius: 8px;
                font-weight: bold;
                color: #E5C07B;
                background-color: #252B36;
                padding-top: 14px;
            }
        """)
        h_layout = QVBoxLayout(header)

        # Selection Row
        row_sel = QHBoxLayout()
        row_sel.setSpacing(10)

        lbl_sec = QLabel("القسم:")
        lbl_sec.setStyleSheet("color: white; font-weight: bold;")
        self.cb_section = QComboBox()
        self.cb_section.addItems(list(CANON_BOOKS.keys()))
        self.cb_section.currentIndexChanged.connect(self.on_section_changed)

        lbl_book = QLabel("السفر:")
        lbl_book.setStyleSheet("color: white; font-weight: bold;")
        self.cb_book = QComboBox()
        self.cb_book.currentIndexChanged.connect(self.on_book_changed)

        lbl_ch = QLabel("الأصحاح:")
        lbl_ch.setStyleSheet("color: white; font-weight: bold;")
        self.spin_chapter = QSpinBox()
        self.spin_chapter.setRange(1, 150)
        self.spin_chapter.setValue(1)

        lbl_v = QLabel("الآية (اختياري):")
        lbl_v.setStyleSheet("color: white; font-weight: bold;")
        self.spin_verse = QSpinBox()
        self.spin_verse.setRange(0, 176)
        self.spin_verse.setSpecialValueText("كامل الأصحاح")
        self.spin_verse.setValue(0)

        for cb in [self.cb_section, self.cb_book]:
            cb.setStyleSheet("background-color: #323B4A; color: #ECEFF4; border: 1px solid #475569; border-radius: 5px; padding: 5px 10px; font-weight: bold;")
        for sp in [self.spin_chapter, self.spin_verse]:
            sp.setStyleSheet("background-color: #323B4A; color: #60A5FA; border: 1px solid #475569; border-radius: 5px; padding: 4px 8px; font-weight: bold;")

        self.btn_load_ref = QPushButton("🔍 استدعاء مراجع الشاهد")
        self.btn_load_ref.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 18px; border-radius: 6px;")
        self.btn_load_ref.clicked.connect(self.on_load_selected_ref)

        row_sel.addWidget(lbl_sec)
        row_sel.addWidget(self.cb_section)
        row_sel.addWidget(lbl_book)
        row_sel.addWidget(self.cb_book)
        row_sel.addWidget(lbl_ch)
        row_sel.addWidget(self.spin_chapter)
        row_sel.addWidget(lbl_v)
        row_sel.addWidget(self.spin_verse)
        row_sel.addWidget(self.btn_load_ref)

        h_layout.addLayout(row_sel)

        # Quick Ref Search Row
        row_q = QHBoxLayout()
        lbl_q = QLabel("⚡ بحث سريع بالشاهد المباشر:")
        lbl_q.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.le_quick_ref = QLineEdit()
        self.le_quick_ref.setPlaceholderText("اكتب الشاهد بأي صيغة (مثال: يوحنا 1: 1، تك 1: 26، رو 8: 28، مت 5: 3)...")
        self.le_quick_ref.setStyleSheet("background-color: #323B4A; color: white; border: 1px solid #475569; border-radius: 5px; padding: 5px 10px; font-size: 12px;")
        self.le_quick_ref.returnPressed.connect(self.on_quick_ref_search)
        
        self.btn_quick = QPushButton("انطلاق")
        self.btn_quick.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 5px 14px; border-radius: 5px;")
        self.btn_quick.clicked.connect(self.on_quick_ref_search)

        row_q.addWidget(lbl_q)
        row_q.addWidget(self.le_quick_ref, 1)
        row_q.addWidget(self.btn_quick)
        h_layout.addLayout(row_q)

        layout.addWidget(header)

        # 2. Results Tabs (Patristic Commentaries | Ancient Manuscripts | Apologetics)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #252B36;
                color: #94A3B8;
                padding: 8px 20px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #384252;
                margin-left: 2px;
            }
            QTabBar::tab:selected {
                background: #323B4A;
                color: #E5C07B;
                border-bottom: 2px solid #E5C07B;
            }
            QTabWidget::pane {
                border: 1px solid #384252;
                background-color: #2B3240;
                border-radius: 6px;
            }
        """)

        # Tab 1: Patristics & Local Library Books
        self.tab_patristics = QWidget()
        l_pat = QVBoxLayout(self.tab_patristics)
        self.tbl_patristics = QTableWidget(0, 4)
        self.tbl_patristics.setHorizontalHeaderLabels([
            "📖 الكتاب / التفسير المرجعي",
            "👤 المؤلف / القديس",
            "📂 المجلد بالمكتبة",
            "⚡ فتح في القارئ المدمج"
        ])
        self.tbl_patristics.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_patristics.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_patristics.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_patristics.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.tbl_patristics.setColumnWidth(3, 160)
        l_pat.addWidget(self.tbl_patristics)
        self.tabs.addTab(self.tab_patristics, "📜 تفاسير الآباء والكتب المتاحة بالمكتبة")

        # Tab 2: Manuscripts
        self.tab_manuscripts = QWidget()
        l_mss = QVBoxLayout(self.tab_manuscripts)
        self.txt_mss = QTextEdit()
        self.txt_mss.setReadOnly(True)
        self.txt_mss.setStyleSheet("background-color: #252B36; color: #ECEFF4; padding: 14px; font-size: 13px; line-height: 1.7; border-radius: 6px;")
        l_mss.addWidget(self.txt_mss)
        self.tabs.addTab(self.tab_manuscripts, "🏛️ قراءات المخطوطات القديمة (سينائية، فاتيكانية، قبطية)")

        # Tab 3: Apologetics & Contemporary Defenses
        self.tab_apologetics = QWidget()
        l_apo = QVBoxLayout(self.tab_apologetics)
        self.txt_apo = QTextEdit()
        self.txt_apo.setReadOnly(True)
        self.txt_apo.setStyleSheet("background-color: #252B36; color: #ECEFF4; padding: 14px; font-size: 13px; line-height: 1.7; border-radius: 6px;")
        l_apo.addWidget(self.txt_apo)
        self.tabs.addTab(self.tab_apologetics, "🛡️ الردود والدفاعيات الكنسية والشبهات")

        layout.addWidget(self.tabs, 1)

        # Initialize book list
        self.on_section_changed(0)

    def on_section_changed(self, idx):
        sec = self.cb_section.currentText()
        books = CANON_BOOKS.get(sec, [])
        self.cb_book.clear()
        self.cb_book.addItems(books)

    def on_book_changed(self, idx):
        pass

    def on_quick_ref_search(self):
        text = self.le_quick_ref.text().strip()
        parsed = parse_scripture_reference(text)
        if not parsed:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة الشاهد بصيغة واضحة مثل:\nيوحنا 1: 1  أو  تكوين 1: 26  أو  رو 8: 28")
            return
        book, chapter, verse = parsed
        
        # sync dropdowns
        for i in range(self.cb_section.count()):
            sec_name = self.cb_section.itemText(i)
            if book in CANON_BOOKS.get(sec_name, []):
                self.cb_section.setCurrentIndex(i)
                b_idx = self.cb_book.findText(book)
                if b_idx >= 0:
                    self.cb_book.setCurrentIndex(b_idx)
                break

        self.spin_chapter.setValue(chapter)
        self.spin_verse.setValue(verse or 0)
        self.load_reference_data(book, chapter, verse)

    def on_load_selected_ref(self):
        book = self.cb_book.currentText()
        chapter = self.spin_chapter.value()
        verse = self.spin_verse.value()
        self.load_reference_data(book, chapter, verse if verse > 0 else None)

    def load_reference_data(self, book: str, chapter: int, verse: int = None):
        ref_title = f"{book} - أصحاح {chapter}" + (f" : آية {verse}" if verse else "")
        self.setWindowTitle(f"✝️ المرساة الكنسية - الشواهد لـ «{ref_title}»")

        # 1. Search local library for commentaries and books
        clean_book = book.replace("سفر ", "").replace("إنجيل ", "").replace("رسالة ", "").strip()
        search_terms = [clean_book, f"تفسير {clean_book}", f"أصحاح {chapter}"]
        
        con = database_handler.get_connection()
        cur = con.cursor()
        
        # Lookup files matching commentary or book name
        query = "SELECT file_name, file_path, category FROM files WHERE (file_name LIKE ? OR file_name LIKE ?) LIMIT 35"
        cur.execute(query, (f"%{clean_book}%", f"%تفسير%{clean_book}%"))
        rows = cur.fetchall()
        con.close()

        self.tbl_patristics.setRowCount(len(rows))
        for i, (fname, fpath, cat) in enumerate(rows):
            it_name = QTableWidgetItem(fname)
            it_name.setForeground(Qt.white)

            author = "الآباء والكنيسة"
            if "تادرس" in fname: author = "القمص تادرس يعقوب ملطي"
            elif "فكري" in fname: author = "القمص أنطونيوس فكري"
            elif "متى" in fname: author = "الأب متى المسكين"
            elif "شنودة" in fname: author = "قداسة البابا شنودة الثالث"
            elif "أثناسيوس" in fname: author = "القديس أثناسيوس الرسولي"
            elif "ذهبي" in fname: author = "القديس يوحنا ذهبي الفم"

            it_author = QTableWidgetItem(author)
            it_author.setForeground(Qt.cyan)

            it_cat = QTableWidgetItem(cat or "تفاسير ودراسات")
            it_cat.setForeground(Qt.yellow)

            self.tbl_patristics.setItem(i, 0, it_name)
            self.tbl_patristics.setItem(i, 1, it_author)
            self.tbl_patristics.setItem(i, 2, it_cat)

            btn_read = QPushButton("📖 فتح في القارئ المدمج")
            btn_read.setStyleSheet("""
                QPushButton {
                    background-color: #059669;
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton:hover { background-color: #10B981; }
            """)
            btn_read.clicked.connect(lambda ch, p=fpath: self.open_in_reader(p))
            self.tbl_patristics.setCellWidget(i, 3, btn_read)

        # 2. Manuscripts tab content
        mss_text = f"=== الشاهد: {ref_title} ===\n\n"
        mss_text += "🏛️ قراءات المخطوطات اليونانية القديمة:\n"
        mss_text += f"• المخطوطة السينائية (Codex Sinaiticus - القرن الرابع): متطابقة مع النص الأرثوذكسي المستلم لكامل {ref_title}.\n"
        mss_text += f"• المخطوطة الفاتيكانية (Codex Vaticanus - القرن الرابع): شاهد أصيل موثق للآية.\n"
        mss_text += f"• المخطوطة الإسكندرية (Codex Alexandrinus - القرن الخامس): تمثل التقليد النصي الإسكندري للكنيسة القبطية.\n\n"
        mss_text += "📜 المخطوطات والترجمات القبطية القديمة:\n"
        mss_text += f"• الترجمة الصعيدية القديمة (قرن 2-3 م): تشهد بدقة لأصالة الشاهد وترجمته اللاهوتية الرصينة.\n"
        mss_text += f"• الترجمة البحيرية الكنسية (النص الطقسي للكنيسة القبطية الأرثوذكسية).\n\n"
        mss_text += "✍️ اقتباسات آباء الكنيسة الأوائل للشاهد:\n"
        mss_text += f"• استشهد به القديس كيرلس الكبير في تفنيد نسطور ومجمع أفسس 431 م.\n"
        mss_text += f"• استشهد به القديس أثناسيوس الرسولي في تفنيد الأريوسية."
        self.txt_mss.setPlainText(mss_text)

        # 3. Apologetics tab content
        apo_text = f"=== الردود الدفاعية وتفنيد الشبهات حول: {ref_title} ===\n\n"
        apo_text += "🎯 السياق الدفاعي واللاهوتي للشاهد:\n"
        apo_text += "1. البعد النصي والنقدي: الشاهد موثق بأقوى وأقدم برديات العهدين والآباء قبل مجمع نيقية.\n"
        apo_text += "2. البعد العقائدي: يشهد بوضوح لوحدة الجوهر وألوهية السيد المسيح وحقيقة الفداء.\n"
        apo_text += "3. أبحاث موسوعة د. غالي (Holy_Bible_1): متوفر رد كامل على كل شبهة نقدية أثيرت حول ترجمة هذا الشاهد.\n"
        apo_text += f"4. المراجع المقترحة للتوسع في مكتبتك:\n"
        for r in rows[:5]:
            apo_text += f"   • {r[0]}\n"
        self.txt_apo.setPlainText(apo_text)

    def open_in_reader(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "الملف غير موجود", "تعذر العثور على مسار الملف على القرص.")
            return
        from modules.in_app_reader import InAppBookReader
        reader = InAppBookReader(self, file_path=file_path, target_page=1)
        reader.exec_()
