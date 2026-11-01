"""
Cross Coptic Library - In-App Split-Screen Reader & Viewer (القارئ والمستعرض المدمج)
Interactive document reader with page rendering, text extraction, in-page keyword search,
split-screen AI insights, and 1-click citation generators.
"""

import os
import re
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QLineEdit,
    QTextEdit,
    QScrollArea,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QShortcut,
    QApplication,
    QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QFont

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class InAppBookReader(QDialog):
    """Modern eye-friendly document reader embedded within ArchiveMaster."""

    def __init__(self, parent=None, file_path: str = None, target_page: int = 1, highlight_term: str = ""):
        super().__init__(parent)
        self.file_path = file_path
        self.current_page = max(1, target_page)
        self.total_pages = 1
        self.zoom_level = 1.25
        self.highlight_term = highlight_term or ""
        self.doc = None
        self.is_pdf = False
        self.is_docx = False

        self.setWindowTitle(f"📖 القارئ الكنسي المدمج - {os.path.basename(file_path) if file_path else ''}")
        self.resize(1300, 850)
        self.init_ui()

        if file_path and os.path.exists(file_path):
            self.load_document(file_path, target_page)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Top Control Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #2F3746;
                border: 1px solid #434F63;
                border-radius: 8px;
            }
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(8)

        # Document Title Label
        self.lbl_title = QLabel("📖 جاري تحميل الكتاب...")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #E5C07B; font-size: 13px; background: transparent; border: none;")
        tb_layout.addWidget(self.lbl_title, 1)

        # Page Navigation Controls
        self.btn_first = QPushButton("⏮️ الأولى")
        self.btn_first.clicked.connect(self.go_first_page)
        self.btn_prev = QPushButton("◀️ السابقة")
        self.btn_prev.clicked.connect(self.go_prev_page)

        self.lbl_page_prefix = QLabel("صفحة:")
        self.lbl_page_prefix.setStyleSheet("color: #E2E8F0; background: transparent; border: none;")
        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(1)
        self.spin_page.setValue(1)
        self.spin_page.setStyleSheet("""
            QSpinBox {
                background-color: #252B36;
                color: #60A5FA;
                font-weight: bold;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
            }
        """)
        self.spin_page.valueChanged.connect(self.on_spin_page_changed)

        self.lbl_total_pages = QLabel("من 1")
        self.lbl_total_pages.setStyleSheet("color: #94A3B8; background: transparent; border: none;")

        self.btn_next = QPushButton("التالية ▶️")
        self.btn_next.clicked.connect(self.go_next_page)
        self.btn_last = QPushButton("الأخيرة ⏭️")
        self.btn_last.clicked.connect(self.go_last_page)

        nav_btns = [self.btn_first, self.btn_prev, self.btn_next, self.btn_last]
        for b in nav_btns:
            b.setStyleSheet("""
                QPushButton {
                    background-color: #384252;
                    color: #E2E8F0;
                    border: 1px solid #4B5563;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #475569; color: white; }
            """)

        tb_layout.addWidget(self.btn_first)
        tb_layout.addWidget(self.btn_prev)
        tb_layout.addWidget(self.lbl_page_prefix)
        tb_layout.addWidget(self.spin_page)
        tb_layout.addWidget(self.lbl_total_pages)
        tb_layout.addWidget(self.btn_next)
        tb_layout.addWidget(self.btn_last)

        # Zoom Controls
        self.btn_zoom_out = QPushButton("🔍-")
        self.btn_zoom_out.setToolTip("تصغير")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_in.setToolTip("تكبير")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        for b in [self.btn_zoom_out, self.btn_zoom_in]:
            b.setStyleSheet("background-color: #384252; color: #E2E8F0; border: 1px solid #4B5563; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
            tb_layout.addWidget(b)

        # External Viewer Button
        self.btn_external = QPushButton("🗗 فتح خارجياً")
        self.btn_external.setStyleSheet("background-color: #1E3A8A; color: white; border-radius: 5px; padding: 5px 12px; font-size: 11px; font-weight: bold;")
        self.btn_external.clicked.connect(self.open_in_external_app)
        tb_layout.addWidget(self.btn_external)

        main_layout.addWidget(toolbar)

        # 2. Main Splitter (Left: Book View | Right: AI Insights & Citations)
        splitter = QSplitter(Qt.Horizontal)

        # --- LEFT PANEL: DOCUMENT PAGE DISPLAY ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # In-page Search Box
        search_bar = QHBoxLayout()
        self.le_doc_search = QLineEdit()
        self.le_doc_search.setPlaceholderText("🔍 ابحث داخل هذا الكتاب (أو اكتب كلمة للانتقال لمواضعها)...")
        self.le_doc_search.setStyleSheet("""
            QLineEdit {
                background-color: #252B36;
                color: #FFFFFF;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        self.le_doc_search.returnPressed.connect(self.search_in_document)
        search_bar.addWidget(self.le_doc_search, 1)

        self.btn_search_doc = QPushButton("بحث في الكتاب")
        self.btn_search_doc.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        self.btn_search_doc.clicked.connect(self.search_in_document)
        search_bar.addWidget(self.btn_search_doc)

        left_layout.addLayout(search_bar)

        # Scroll Area for Page Image / Document Text
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #384252; background-color: #222731; border-radius: 8px; }")

        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("background-color: #222731; padding: 12px;")
        self.scroll_area.setWidget(self.page_label)

        # Fallback Text Viewer for docx/txt or textual mode
        self.text_viewer = QTextEdit()
        self.text_viewer.setReadOnly(True)
        self.text_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #252B36;
                color: #ECEFF4;
                border: 1px solid #384252;
                border-radius: 8px;
                padding: 18px;
                font-size: 14px;
                line-height: 1.8;
                font-family: 'Segoe UI', 'Cairo', 'Arial';
            }
        """)
        self.text_viewer.hide()

        left_layout.addWidget(self.scroll_area, 1)
        left_layout.addWidget(self.text_viewer, 1)

        splitter.addWidget(left_widget)

        # --- RIGHT PANEL: AI INSIGHTS, CITATION GENERATOR, NOTES ---
        right_panel = QWidget()
        right_panel.setMinimumWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 8, 0)
        right_layout.setSpacing(10)

        # Citation Generator Card
        lbl_cite_title = QLabel("📜 التوثيق والإحالة المرجعية التلقائية:")
        lbl_cite_title.setStyleSheet("font-weight: bold; color: #E5C07B; font-size: 12px;")
        right_layout.addWidget(lbl_cite_title)

        self.txt_citation = QTextEdit()
        self.txt_citation.setFixedHeight(90)
        self.txt_citation.setReadOnly(True)
        self.txt_citation.setStyleSheet("""
            QTextEdit {
                background-color: #252B36;
                color: #60A5FA;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(self.txt_citation)

        btn_copy_cite = QPushButton("📋 نسخ الإحالة المرجعية الموثقة")
        btn_copy_cite.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px; border-radius: 5px;")
        btn_copy_cite.clicked.connect(self.copy_citation)
        right_layout.addWidget(btn_copy_cite)

        # Page Extracted Text Box
        lbl_page_text = QLabel("📝 نص الصفحة الحالية المفرغ (للاقتباس):")
        lbl_page_text.setStyleSheet("font-weight: bold; color: #94A3B8; font-size: 12px;")
        right_layout.addWidget(lbl_page_text)

        self.txt_page_content = QTextEdit()
        self.txt_page_content.setStyleSheet("""
            QTextEdit {
                background-color: #252B36;
                color: #E2E8F0;
                border: 1px solid #434F63;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        right_layout.addWidget(self.txt_page_content, 1)

        btn_copy_text = QPushButton("📄 نسخ النص المقتبس من الصفحة")
        btn_copy_text.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px; border-radius: 5px;")
        btn_copy_text.clicked.connect(self.copy_page_text)
        right_layout.addWidget(btn_copy_text)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, 1)

        # Shortcuts
        QShortcut(QKeySequence("Left"), self, self.go_next_page)
        QShortcut(QKeySequence("Right"), self, self.go_prev_page)

    def load_document(self, file_path: str, target_page: int = 1):
        self.file_path = file_path
        filename = os.path.basename(file_path)
        self.lbl_title.setText(f"📖 {filename}")
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                self.doc = fitz.open(file_path)
                self.total_pages = len(self.doc)
                self.is_pdf = True
                self.is_docx = False
                self.spin_page.setMaximum(self.total_pages)
                self.lbl_total_pages.setText(f"من {self.total_pages}")
                self.scroll_area.show()
                self.text_viewer.hide()
                self.go_to_page(target_page)
            except Exception as e:
                QMessageBox.warning(self, "خطأ في فتح الملف", f"تعذر فتح ملف الـ PDF:\n{e}")

        elif ext in [".docx", ".doc", ".txt"]:
            self.is_pdf = False
            self.is_docx = True
            self.scroll_area.hide()
            self.text_viewer.show()
            self.spin_page.setEnabled(False)
            self.btn_first.setEnabled(False)
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.btn_last.setEnabled(False)

            content = ""
            if ext == ".docx" and HAS_DOCX:
                try:
                    d = docx.Document(file_path)
                    content = "\n\n".join(p.text for p in d.paragraphs if p.text.strip())
                except Exception as e:
                    content = f"تعذر قراءة ملف Word: {e}"
            else:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    content = f"تعذر قراءة الملف: {e}"

            self.text_viewer.setPlainText(content)
            self.txt_page_content.setPlainText(content[:2500])
            self.update_citation_display(1)

    def render_current_page(self):
        if not self.is_pdf or not self.doc:
            return

        page_idx = self.current_page - 1
        if page_idx < 0 or page_idx >= len(self.doc):
            return

        try:
            page = self.doc[page_idx]
            # Matrix scaling based on zoom level
            mat = fitz.Matrix(self.zoom_level, self.zoom_level)
            pix = page.get_pixmap(matrix=mat)

            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            qpix = QPixmap.fromImage(qimg)
            self.page_label.setPixmap(qpix)

            # Update text in side box
            t = page.get_text()
            self.txt_page_content.setPlainText(t if t.strip() else "(هذه الصفحة مصورة أو لا تحتوي على نصوص مفرغة بعد)")
            self.update_citation_display(self.current_page)

        except Exception as e:
            self.page_label.setText(f"خطأ في عرض الصفحة: {e}")

    def update_citation_display(self, page_num: int):
        bname = os.path.basename(self.file_path).replace(".pdf", "").replace(".docx", "")
        cite_text = f"📖 مرجع موثق: [{bname}]، صفحة: {page_num}.\nمكتبة الصليب القبطية الأرثوذكسية."
        self.txt_citation.setPlainText(cite_text)

    def go_to_page(self, page_num: int):
        self.current_page = max(1, min(self.total_pages, page_num))
        self.spin_page.blockSignals(True)
        self.spin_page.setValue(self.current_page)
        self.spin_page.blockSignals(False)
        self.render_current_page()

    def go_prev_page(self):
        if self.current_page > 1:
            self.go_to_page(self.current_page - 1)

    def go_next_page(self):
        if self.current_page < self.total_pages:
            self.go_to_page(self.current_page + 1)

    def go_first_page(self):
        self.go_to_page(1)

    def go_last_page(self):
        self.go_to_page(self.total_pages)

    def on_spin_page_changed(self, val):
        self.go_to_page(val)

    def zoom_in(self):
        if self.zoom_level < 3.0:
            self.zoom_level += 0.25
            self.render_current_page()

    def zoom_out(self):
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.25
            self.render_current_page()

    def search_in_document(self):
        term = self.le_doc_search.text().strip()
        if not term or not self.doc or not self.is_pdf:
            return

        # Find first matching page starting from current page onwards
        found_page = None
        for pno in range(self.current_page - 1, len(self.doc)):
            p = self.doc[pno]
            if term.lower() in p.get_text().lower():
                found_page = pno + 1
                break

        if not found_page:
            # Wrap around search from beginning
            for pno in range(0, self.current_page - 1):
                p = self.doc[pno]
                if term.lower() in p.get_text().lower():
                    found_page = pno + 1
                    break

        if found_page:
            self.go_to_page(found_page)
        else:
            QMessageBox.information(self, "نتائج البحث", f"لم يتم العثور على «{term}» في نصوص هذا الكتاب.")

    def copy_citation(self):
        txt = self.txt_citation.toPlainText()
        if txt:
            QApplication.clipboard().setText(txt)
            QMessageBox.information(self, "تم النسخ", "تم نسخ الإحالة المرجعية الموثقة إلى الحافظة بنجاح.")

    def copy_page_text(self):
        txt = self.txt_page_content.toPlainText()
        if txt:
            QApplication.clipboard().setText(txt)
            QMessageBox.information(self, "تم النسخ", "تم نسخ نص الصفحة إلى الحافظة بنجاح.")

    def open_in_external_app(self):
        if self.file_path and os.path.exists(self.file_path):
            os.startfile(self.file_path)

    def closeEvent(self, event):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
        event.accept()
