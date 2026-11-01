"""
Cross Coptic Library - Topic Visualizers & Interactive Apologetic Tools
1. MindMapViewerDialog: Interactive Semantic Mind Map & Knowledge Tree.
2. DebateMatrixDialog: Structured Quick-Answer & Objection Refutation Matrix (Cheat Sheet).
"""

import os
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QApplication,
    QSplitter,
    QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

from modules import topic_archive

class MindMapWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, topic, content):
        super().__init__()
        self.topic = topic
        self.content = content

    def run(self):
        try:
            data = topic_archive.generate_mind_map_data(self.topic, self.content)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class DebateMatrixWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, topic, content):
        super().__init__()
        self.topic = topic
        self.content = content

    def run(self):
        try:
            data = topic_archive.generate_debate_matrix(self.topic, self.content)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class MindMapViewerDialog(QDialog):
    """نافذة الخريطة الذهنية وشجرة الروابط الدلالية للموضوع."""
    drillDownRequested = pyqtSignal(str)

    def __init__(self, topic: str, content: str = "", parent=None):
        super().__init__(parent)
        self.topic = topic
        self.content = content
        self.setWindowTitle(f"🧠 الخريطة الذهنية وشبكة الروابط الدلالية: {topic}")
        self.resize(850, 620)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #F8FAFC;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QTreeWidget {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px;
                border-bottom: 1px solid #334155;
            }
            QTreeWidget::item:selected {
                background-color: #1D4ED8;
                color: #FFFFFF;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        t = QLabel(f"🧠 الخريطة المعرفية والشجرة الدلالية: {self.topic}")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        d = QLabel("الفروع المعرفية المتفرعة من صلب هذا الموضوع مع إمكانية التوسع والبحث المباشر في أي فرع")
        d.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(t)
        layout.addWidget(d)

        # Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["الفرع المعرفي والمفاهيم المرتبطة", "الموجز التوضيحي"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self.on_node_double_clicked)
        layout.addWidget(self.tree, 1)

        # Status & Action bar
        act_box = QHBoxLayout()
        self.status_lbl = QLabel("جاري توليد الشجرة المعرفية...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-style: italic;")
        act_box.addWidget(self.status_lbl, 1)

        self.btn_drill = QPushButton("🚀 استكشاف وتوليد بحث تفصيلي للفرع المختار")
        self.btn_drill.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_drill.clicked.connect(self.on_drill_clicked)
        act_box.addWidget(self.btn_drill)

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("background-color: #334155; color: white; padding: 8px 16px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        act_box.addWidget(btn_close)

        layout.addLayout(act_box)

        self.load_mind_map()

    def load_mind_map(self):
        self.thread = QThread()
        self.worker = MindMapWorker(self.topic, self.content)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.populate_tree)
        self.worker.error.connect(self.on_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def populate_tree(self, data):
        self.tree.clear()
        self.status_lbl.setText("تم توليد الخريطة الذهنية بنجاح. انقر مرتين على أي فرع للتوسع فيه.")

        root_item = QTreeWidgetItem([f"🎯 {data.get('root', self.topic)}", "الموضوع الجذري الرئيسي"])
        root_item.setForeground(0, Qt.yellow)
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)

        for branch in data.get("branches", []):
            b_item = QTreeWidgetItem([f"📂 {branch.get('name')}", branch.get('summary', '')])
            b_item.setForeground(0, Qt.cyan)
            b_font = b_item.font(0)
            b_font.setBold(True)
            b_item.setFont(0, b_font)

            for sub in branch.get("sub_topics", []):
                sub_item = QTreeWidgetItem([f"  🔹 {sub}", "مفهوم تفصيلي فرعي"])
                b_item.addChild(sub_item)

            root_item.addChild(b_item)

        self.tree.addTopLevelItem(root_item)
        self.tree.expandAll()

    def on_error(self, err):
        self.status_lbl.setText(f"تعذر بناء الخريطة: {err}")

    def on_node_double_clicked(self, item, col):
        self.on_drill_clicked()

    def on_drill_clicked(self):
        item = self.tree.currentItem()
        if not item:
            return
        branch_name = item.text(0).replace("🎯 ", "").replace("📂 ", "").replace("🔹 ", "").strip()
        full_query = f"{self.topic} - {branch_name}"
        self.drillDownRequested.emit(full_query)
        self.accept()

class DebateMatrixDialog(QDialog):
    """نافذة مصفوفة الردود السريعة والمقارنة الجدلية (Cheat Sheet)."""
    def __init__(self, topic: str, content: str = "", parent=None):
        super().__init__(parent)
        self.topic = topic
        self.content = content
        self.matrix_data = []
        self.setWindowTitle(f"📋 مصفوفة الردود السريعة والمقارنة الجدلية: {topic}")
        self.resize(1050, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #F8FAFC;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QTableWidget {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #0B0F19;
                color: #D4AF37;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header
        t = QLabel(f"📋 مصفوفة الردود السريعة والمقارنة الجدلية: {self.topic}")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        d = QLabel("دليل موجز ومكثف (Cheat Sheet) للخدام والشباب لتفنيد الشبهة في 5 أركان متقابلة بنظرة واحدة")
        d.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(t)
        layout.addWidget(d)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setWordWrap(True)
        self.table.setHorizontalHeaderLabels([
            "🎯 الشبهة أو الادعاء",
            "🛡️ الرد الأرثوذكسي المكثف",
            "📖 الشاهد الكتابي",
            "🔬 العلم والآثار المحايدة",
            "⛪ إجماع الآباء القديسين"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(2, 120)
        self.table.setStyleSheet("QTableWidget::item { padding: 8px; }")
        layout.addWidget(self.table, 1)

        # Footer Actions
        act_box = QHBoxLayout()
        self.status_lbl = QLabel("جاري صياغة مصفوفة الردود...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-style: italic;")
        act_box.addWidget(self.status_lbl, 1)

        self.btn_copy = QPushButton("📋 نسخ محتوى المصفوفة")
        self.btn_copy.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_copy.clicked.connect(self.copy_matrix)
        act_box.addWidget(self.btn_copy)

        self.btn_export = QPushButton("📄 تصدير كجدول Word (.docx)")
        self.btn_export.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_export.clicked.connect(self.export_docx_table)
        act_box.addWidget(self.btn_export)

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("background-color: #1E293B; color: #94A3B8; padding: 8px 16px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        act_box.addWidget(btn_close)

        layout.addLayout(act_box)

        self.load_matrix()

    def load_matrix(self):
        self.thread = QThread()
        self.worker = DebateMatrixWorker(self.topic, self.content)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.populate_table)
        self.worker.error.connect(self.on_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def populate_table(self, data):
        self.matrix_data = data
        self.table.setRowCount(len(data))
        self.status_lbl.setText("تم بناء مصفوفة الردود السريعة بنجاح.")

        for i, row in enumerate(data):
            it_obj = QTableWidgetItem(row.get("objection", ""))
            it_obj.setForeground(Qt.red)
            it_ref = QTableWidgetItem(row.get("refutation", ""))
            it_scr = QTableWidgetItem(row.get("scripture", ""))
            it_scr.setForeground(Qt.cyan)
            it_sci = QTableWidgetItem(row.get("science", ""))
            it_sci.setForeground(Qt.green)
            it_pat = QTableWidgetItem(row.get("patristic", ""))
            it_pat.setForeground(Qt.yellow)

            self.table.setItem(i, 0, it_obj)
            self.table.setItem(i, 1, it_ref)
            self.table.setItem(i, 2, it_scr)
            self.table.setItem(i, 3, it_sci)
            self.table.setItem(i, 4, it_pat)

        self.table.resizeRowsToContents()

    def on_error(self, err):
        self.status_lbl.setText(f"خطأ: {err}")

    def copy_matrix(self):
        lines = [f"📋 مصفوفة الردود السريعة والمقارنة الجدلية: {self.topic}\n"]
        for row in self.matrix_data:
            lines.append(f"• الشبهة: {row.get('objection')}")
            lines.append(f"  - الرد المكثف: {row.get('refutation')}")
            lines.append(f"  - الشاهد: {row.get('scripture')}")
            lines.append(f"  - العلم والآثار: {row.get('science')}")
            lines.append(f"  - أقوال الآباء: {row.get('patristic')}\n")
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "تم النسخ", "تم نسخ نصوص المصفوفة بالكامل إلى الحافظة! 📋")

    def export_docx_table(self):
        save_path = f"مصفوفة_ردود_{self.topic[:25]}.docx".replace(" ", "_")
        doc = Document()
        doc.add_heading(f"📋 مصفوفة الردود السريعة والمقارنة: {self.topic}", level=1)

        t = doc.add_table(rows=1, cols=5)
        hdr_cells = t.rows[0].cells
        hdr_cells[0].text = "الشبهة"
        hdr_cells[1].text = "الرد الأرثوذكسي"
        hdr_cells[2].text = "الشاهد"
        hdr_cells[3].text = "العلم والآثار"
        hdr_cells[4].text = "أقوال الآباء"

        for row in self.matrix_data:
            row_cells = t.add_row().cells
            row_cells[0].text = row.get("objection", "")
            row_cells[1].text = row.get("refutation", "")
            row_cells[2].text = row.get("scripture", "")
            row_cells[3].text = row.get("science", "")
            row_cells[4].text = row.get("patristic", "")

        doc.save(save_path)
        QMessageBox.information(self, "تم التصدير", f"تم حفظ جدول المصفوفة كملف Word في:\n{save_path}")
