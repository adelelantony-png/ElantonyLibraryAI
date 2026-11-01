# -*- coding: utf-8 -*-
"""
ArchiveMaster - Pastoral Care & Visitation Journal
مفكرة وسجل الافتقاد والرعاية الكنسية للأسر والمخدومين
مستوحى ومطور بالاستفادة من منظومة الرعاية والخدمات الكنسية الذكية.
"""

import os
import sqlite3
import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QFileDialog, QFrame,
    QAbstractItemView, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QFont, QColor

from modules import ai_handler

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "file_archive.db")

STAGES_LIST = [
    "الكل",
    "ابتدائي (مدارس الأحد)",
    "إعدادي (فتيان وفتيات)",
    "ثانوي (شباب)",
    "جامعيين وخريجين",
    "أسرة ومتزوجين حديثاً",
    "شعب عام وكبار السن",
    "مرضى ورعاية خاصة"
]

TAG_PRESETS = [
    "#افتقاد_عاجل",
    "#صلاة_خاصة",
    "#امتحانات_ثانوية",
    "#مرض_وعلاج",
    "#انقطاع_عن_الكنيسة",
    "#تحدي_أسري",
    "#سر_الاعتراف",
    "#مواظب_ومتميز"
]

def init_pastoral_table(db_path=DB_FILE):
    """Ensures the pastoral_records table exists in SQLite database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pastoral_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            stage TEXT,
            confession_father TEXT,
            confession_status TEXT,
            last_visit TEXT,
            next_visit TEXT,
            spiritual_needs TEXT,
            notes TEXT,
            tags TEXT,
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def fetch_pastoral_records(db_path=DB_FILE, search="", stage="الكل", tag="الكل"):
    """Fetches records matching search query and filters."""
    init_pastoral_table(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    query = "SELECT id, name, phone, address, stage, confession_father, confession_status, last_visit, next_visit, spiritual_needs, notes, tags, is_favorite FROM pastoral_records WHERE 1=1"
    params = []

    if search.strip():
        s = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR phone LIKE ? OR address LIKE ? OR notes LIKE ? OR spiritual_needs LIKE ?)"
        params.extend([s, s, s, s, s])

    if stage and stage != "الكل":
        query += " AND stage = ?"
        params.append(stage)

    if tag and tag != "الكل":
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    query += " ORDER BY is_favorite DESC, id DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def save_pastoral_record(record_data, db_path=DB_FILE):
    """Inserts or updates a pastoral record."""
    init_pastoral_table(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    rec_id = record_data.get("id")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if rec_id:
        cur.execute("""
            UPDATE pastoral_records
            SET name = ?, phone = ?, address = ?, stage = ?, confession_father = ?,
                confession_status = ?, last_visit = ?, next_visit = ?,
                spiritual_needs = ?, notes = ?, tags = ?, is_favorite = ?, updated_at = ?
            WHERE id = ?
        """, (
            record_data.get("name", ""),
            record_data.get("phone", ""),
            record_data.get("address", ""),
            record_data.get("stage", "ابتدائي (مدارس الأحد)"),
            record_data.get("confession_father", ""),
            record_data.get("confession_status", "منتظم"),
            record_data.get("last_visit", ""),
            record_data.get("next_visit", ""),
            record_data.get("spiritual_needs", ""),
            record_data.get("notes", ""),
            record_data.get("tags", ""),
            record_data.get("is_favorite", 0),
            now_str,
            rec_id
        ))
    else:
        cur.execute("""
            INSERT INTO pastoral_records (
                name, phone, address, stage, confession_father,
                confession_status, last_visit, next_visit,
                spiritual_needs, notes, tags, is_favorite, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_data.get("name", ""),
            record_data.get("phone", ""),
            record_data.get("address", ""),
            record_data.get("stage", "ابتدائي (مدارس الأحد)"),
            record_data.get("confession_father", ""),
            record_data.get("confession_status", "منتظم"),
            record_data.get("last_visit", ""),
            record_data.get("next_visit", ""),
            record_data.get("spiritual_needs", ""),
            record_data.get("notes", ""),
            record_data.get("tags", ""),
            record_data.get("is_favorite", 0),
            now_str,
            now_str
        ))

    conn.commit()
    conn.close()


def delete_pastoral_record(record_id, db_path=DB_FILE):
    """Deletes a record by ID."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM pastoral_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def generate_smart_visitation_message(record_dict):
    """
    Uses ArchiveMaster AI to generate a warm, compassionate pastoral WhatsApp/SMS message
    tailored to the person's spiritual situation, age stage, and challenges.
    """
    name = record_dict.get("name", "المخدوم")
    stage = record_dict.get("stage", "شباب")
    needs = record_dict.get("spiritual_needs", "")
    notes = record_dict.get("notes", "")

    prompt = f"""
أنت خادم قبطي أرثوذكسي محب جداً ووديع وذو حكمة رعوية عالية.
مطلوب منك كتابة رسالة افتقاد وتشجيع روحية رقيقة ودافئة لإرسالها عبر الواتساب أو رسالة نصية قصيرة (SMS) إلى المخدوم.

📌 بيانات المخدوم:
- الاسم: {name}
- المرحلة: {stage}
- التحديات أو الاحتياجات المذكورة في المذكرة: {needs}
- ملاحظات الخادم: {notes}

🎯 معايير الرسالة الإلزامية:
1. أن تكون مفعمة بالمحبة المسيحية الأرثوذكسية والاهتمام الصادق بدون أي لوم أو عتاب مصطنع.
2. أن تناسب لغتها وأسلوبها مرحلته العمرية تماماً.
3. تضمين آية كتابية مشجعة ملائمة لظرفه أو تحدياته (مع ذكر الشاهد بدقة).
4. دعوة لطيفة للقاء أو الاطمئنان عليه في الكنيسة أو زيارة عائلية مباركة.
5. اختتام الرسالة بصلوات وبركة الصليب.
(اكتب نص الرسالة مباشرة جاهزاً للإرسال بنقرة واحدة).
"""
    sys_instruction = "أنت خادم ومرشد روحي كنسي، تنبض رسائلك بالمحبة والسلام الإلهي والتشجيع."
    return ai_handler.call_ai_routed(prompt, system_instruction=sys_instruction)


class EditRecordDialog(QDialog):
    """Dialog for creating or updating a pastoral record."""
    def __init__(self, parent=None, record_data=None):
        super().__init__(parent)
        self.record_data = record_data or {}
        self.setWindowTitle("تعديل بيانات مخدوم" if record_data else "إضافة مخدوم / أسرة جديدة للافتقاد")
        self.resize(550, 600)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #1E232D; color: white; font-family: 'Segoe UI', 'Cairo', Tahoma; }
            QLabel { color: #E5C07B; font-weight: bold; font-size: 12px; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #14171F; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #F59E0B; }
        """)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(18, 16, 18, 16)

        # Name
        lay.addWidget(QLabel("الاسم الكامل للمخدوم أو الأسرة:"))
        self.le_name = QLineEdit(self.record_data.get("name", ""))
        self.le_name.setPlaceholderText("مثال: مينا مجدي، أو عائلة الأستاذ فايز...")
        lay.addWidget(self.le_name)

        # Phone + Stage
        row1 = QHBoxLayout()
        v_ph = QVBoxLayout()
        v_ph.addWidget(QLabel("رقم الهاتف / الواتساب:"))
        self.le_phone = QLineEdit(self.record_data.get("phone", ""))
        self.le_phone.setPlaceholderText("01xxxxxxxxx")
        v_ph.addWidget(self.le_phone)
        row1.addLayout(v_ph, 1)

        v_st = QVBoxLayout()
        v_st.addWidget(QLabel("المرحلة الكنسية:"))
        self.combo_stage = QComboBox()
        for s in STAGES_LIST[1:]:
            self.combo_stage.addItem(s)
        if self.record_data.get("stage"):
            self.combo_stage.setCurrentText(self.record_data["stage"])
        v_st.addWidget(self.combo_stage)
        row1.addLayout(v_st, 1)
        lay.addLayout(row1)

        # Address + Confession Father
        row2 = QHBoxLayout()
        v_addr = QVBoxLayout()
        v_addr.addWidget(QLabel("العنوان أو المنطقة:"))
        self.le_addr = QLineEdit(self.record_data.get("address", ""))
        v_addr.addWidget(self.le_addr)
        row2.addLayout(v_addr, 1)

        v_cf = QVBoxLayout()
        v_cf.addWidget(QLabel("أب الاعتراف:"))
        self.le_cf = QLineEdit(self.record_data.get("confession_father", ""))
        self.le_cf.setPlaceholderText("مثال: أبونا بيشوي...")
        v_cf.addWidget(self.le_cf)
        row2.addLayout(v_cf, 1)
        lay.addLayout(row2)

        # Dates: Last Visit + Next Visit
        row3 = QHBoxLayout()
        v_lv = QVBoxLayout()
        v_lv.addWidget(QLabel("تاريخ آخر زيارة / افتقاد:"))
        self.le_last_visit = QLineEdit(self.record_data.get("last_visit", datetime.datetime.now().strftime("%Y-%m-%d")))
        v_lv.addWidget(self.le_last_visit)
        row3.addLayout(v_lv, 1)

        v_nv = QVBoxLayout()
        v_nv.addWidget(QLabel("موعد الافتقاد القادم المقترح:"))
        self.le_next_visit = QLineEdit(self.record_data.get("next_visit", ""))
        self.le_next_visit.setPlaceholderText("YYYY-MM-DD")
        v_nv.addWidget(self.le_next_visit)
        row3.addLayout(v_nv, 1)
        lay.addLayout(row3)

        # Spiritual / Social Needs
        lay.addWidget(QLabel("الاحتياجات الروحية والظروف الحالية (امتحانات، مرض، عزاء، خلافات):"))
        self.te_needs = QTextEdit(self.record_data.get("spiritual_needs", ""))
        self.te_needs.setPlaceholderText("اكتب التحديات التي يمر بها لمتابعتها وتضمينها في رسائل الافتقاد...")
        self.te_needs.setFixedHeight(65)
        lay.addWidget(self.te_needs)

        # Pastoral Notes
        lay.addWidget(QLabel("ملاحظات الافتقاد وسجل المتابعة:"))
        self.te_notes = QTextEdit(self.record_data.get("notes", ""))
        self.te_notes.setPlaceholderText("سجل ما دار في الزيارات وتوصيات أب الاعتراف والخدام...")
        self.te_notes.setFixedHeight(80)
        lay.addWidget(self.te_notes)

        # Tags
        lay.addWidget(QLabel("وسوم التصنيف (مفصولة بفواصل):"))
        self.le_tags = QLineEdit(self.record_data.get("tags", "#افتقاد"))
        lay.addWidget(self.le_tags)

        # Buttons
        b_lay = QHBoxLayout()
        btn_save = QPushButton("💾 حفظ البيانات")
        btn_save.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 9px 18px; border-radius: 6px;")
        btn_save.clicked.connect(self.save_data)
        b_lay.addWidget(btn_save)

        btn_cancel = QPushButton("إلغاء")
        btn_cancel.setStyleSheet("background-color: #334155; color: white; padding: 9px 18px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        b_lay.addWidget(btn_cancel)
        lay.addLayout(b_lay)

    def save_data(self):
        name = self.le_name.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة اسم المخدوم أو الأسرة.")
            return

        self.record_data.update({
            "name": name,
            "phone": self.le_phone.text().strip(),
            "stage": self.combo_stage.currentText(),
            "address": self.le_addr.text().strip(),
            "confession_father": self.le_cf.text().strip(),
            "last_visit": self.le_last_visit.text().strip(),
            "next_visit": self.le_next_visit.text().strip(),
            "spiritual_needs": self.te_needs.toPlainText().strip(),
            "notes": self.te_notes.toPlainText().strip(),
            "tags": self.le_tags.text().strip(),
        })
        save_pastoral_record(self.record_data)
        self.accept()


class SmartMessageWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, record_dict):
        super().__init__()
        self.record_dict = record_dict

    def run(self):
        try:
            msg = generate_smart_visitation_message(self.record_dict)
            self.finished.emit(msg)
        except Exception as e:
            self.error.emit(str(e))


class PastoralCareJournalDialog(QDialog):
    """
    Main Pastoral Care & Visitation Journal Dialog
    واجهة مفكرة وسجل الافتقاد والرعاية الكنسية
    """
    def __init__(self, parent=None, db_path=DB_FILE):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("📋 مفكرة وسجل الافتقاد والرعاية الكنسية الذكية (Pastoral Care Journal)")
        self.resize(1100, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        self.current_rows = []
        self.worker_thread = None
        self.worker = None

        self.init_ui()
        self.load_records()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #14171F; font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif; }
            QWidget { background-color: transparent; color: #D7DAE0; font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif; }
            QLabel { font-size: 13px; color: #E2E8F0; font-weight: 500; }
            QLineEdit, QComboBox {
                background-color: #1E222A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 7px 12px; font-size: 13px;
            }
            QTableWidget {
                background-color: #1A1D24; color: #F8FAFC; border: 1px solid #334155;
                gridline-color: #2D3748; selection-background-color: #0369A1;
                border-radius: 8px; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1E232D; color: #E5C07B; font-weight: bold;
                border: 1px solid #334155; padding: 6px; font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #065F46, stop:1 #0F172A);
                border-radius: 8px; border: 1px solid #10B981; padding: 6px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_icon = QLabel("📋")
        h_icon.setStyleSheet("font-size: 32px; background: transparent;")
        h_lay.addWidget(h_icon)

        v_t = QVBoxLayout()
        lbl_title = QLabel("مفكرة وسجل الافتقاد والرعاية الكنسية الذكية")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #34D399; background: transparent;")
        lbl_sub = QLabel("متابعة زيارات الأسر والمخدومين، وتدوين الاحتياجات الروحية، وتوليد رسائل الافتقاد الذكية للواتساب بنقرة واحدة.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")
        v_t.addWidget(lbl_title)
        v_t.addWidget(lbl_sub)
        h_lay.addLayout(v_t, 1)

        # Quick stats badge
        self.lbl_stats = QLabel("المسجلون: 0")
        self.lbl_stats.setStyleSheet("font-size: 13px; font-weight: bold; color: #FCD34D; background: rgba(0,0,0,0.3); padding: 6px 14px; border-radius: 6px;")
        h_lay.addWidget(self.lbl_stats)

        layout.addWidget(header)

        # 2. Search & Filter Bar
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 بحث بالاسم، رقم الهاتف، العنوان، أو الملاحظات...")
        self.le_search.textChanged.connect(self.load_records)
        bar.addWidget(self.le_search, 1)

        lbl_s = QLabel("المرحلة:")
        self.combo_filter_stage = QComboBox()
        self.combo_filter_stage.addItems(STAGES_LIST)
        self.combo_filter_stage.currentIndexChanged.connect(self.load_records)
        bar.addWidget(lbl_s)
        bar.addWidget(self.combo_filter_stage)

        btn_add = QPushButton("➕ إضافة مخدوم جديد")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #059669; color: white; font-weight: bold;
                padding: 8px 16px; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        btn_add.clicked.connect(self.add_new_record)
        bar.addWidget(btn_add)

        layout.addLayout(bar)

        # 3. Main Splitter: Table (left) & Detail / Smart Message (right)
        splitter = QSplitter(Qt.Horizontal)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "الاسم الكامل", "المرحلة", "رقم الهاتف", "أب الاعتراف", "آخر زيارة", "الوسوم"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        self.table.doubleClicked.connect(self.edit_selected_record)
        splitter.addWidget(self.table)

        # Right Side: Detail & Action Panel
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #1A1D24; border: 1px solid #334155; border-radius: 8px; padding: 12px;")
        r_lay = QVBoxLayout(right_panel)
        r_lay.setSpacing(8)

        lbl_r_title = QLabel("📌 بطاقة رعاية المخدوم والمتابعة:")
        lbl_r_title.setStyleSheet("color: #E5C07B; font-weight: bold; font-size: 13px;")
        r_lay.addWidget(lbl_r_title)

        self.lbl_sel_name = QLabel("اختر مخدوماً من الجدول لمعاينة التفاصيل...")
        self.lbl_sel_name.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        r_lay.addWidget(self.lbl_sel_name)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setStyleSheet("background-color: #14171F; color: #E2E8F0; border: 1px solid #334155; border-radius: 6px; font-size: 12px;")
        r_lay.addWidget(self.txt_details, 1)

        # Smart Message Box
        lbl_msg = QLabel("💌 رسالة الافتقاد الذكية للواتساب:")
        lbl_msg.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        r_lay.addWidget(lbl_msg)

        self.txt_smart_msg = QTextEdit()
        self.txt_smart_msg.setStyleSheet("background-color: #14171F; color: #34D399; border: 1px solid #059669; border-radius: 6px; font-size: 12px;")
        self.txt_smart_msg.setPlaceholderText("اضغط على زر التوليد الذكي أدناه لصياغة رسالة افتقاد وتشجيع مخصصة تناسب ظروفه...")
        self.txt_smart_msg.setFixedHeight(120)
        r_lay.addWidget(self.txt_smart_msg)

        # Buttons on right
        btn_gen_msg = QPushButton("🤖 توليد رسالة افتقاد بالذكاء الاصطناعي")
        btn_gen_msg.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 8px; border-radius: 5px;")
        btn_gen_msg.clicked.connect(self.generate_msg_for_selected)
        r_lay.addWidget(btn_gen_msg)

        b_row = QHBoxLayout()
        btn_copy_msg = QPushButton("📋 نسخ الرسالة")
        btn_copy_msg.setStyleSheet("background-color: #334155; color: white; padding: 7px; border-radius: 5px;")
        btn_copy_msg.clicked.connect(self.copy_smart_msg)
        b_row.addWidget(btn_copy_msg)

        btn_edit = QPushButton("✏️ تعديل")
        btn_edit.setStyleSheet("background-color: #D97706; color: white; padding: 7px; border-radius: 5px;")
        btn_edit.clicked.connect(self.edit_selected_record)
        b_row.addWidget(btn_edit)

        btn_del = QPushButton("🗑️ حذف")
        btn_del.setStyleSheet("background-color: #DC2626; color: white; padding: 7px; border-radius: 5px;")
        btn_del.clicked.connect(self.delete_selected_record)
        b_row.addWidget(btn_del)
        r_lay.addLayout(b_row)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # 4. Bottom Footer Bar
        foot_bar = QHBoxLayout()
        btn_export = QPushButton("📊 تصدير كشف الافتقاد إلى Excel / CSV")
        btn_export.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        btn_export.clicked.connect(self.export_records_csv)
        foot_bar.addWidget(btn_export)

        foot_bar.addStretch()

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("background-color: #1E222A; color: #94A3B8; padding: 8px 16px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        foot_bar.addWidget(btn_close)

        layout.addLayout(foot_bar)

    def load_records(self):
        s_text = self.le_search.text().strip()
        stage_filter = self.combo_filter_stage.currentText()
        self.current_rows = fetch_pastoral_records(self.db_path, search=s_text, stage=stage_filter)

        self.table.setRowCount(len(self.current_rows))
        for row_idx, r in enumerate(self.current_rows):
            # r = (id, name, phone, address, stage, confession_father, confession_status, last_visit, next_visit, spiritual_needs, notes, tags, is_favorite)
            self.table.setItem(row_idx, 0, QTableWidgetItem(f"👤 {r[1]}"))
            self.table.setItem(row_idx, 1, QTableWidgetItem(r[4] or ""))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r[2] or ""))
            self.table.setItem(row_idx, 3, QTableWidgetItem(r[5] or ""))
            self.table.setItem(row_idx, 4, QTableWidgetItem(r[7] or ""))
            self.table.setItem(row_idx, 5, QTableWidgetItem(r[11] or ""))

        self.lbl_stats.setText(f"إجمالي المخدومين: {len(self.current_rows)}")

    def get_selected_record_dict(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        row_idx = self.table.currentRow()
        if row_idx < 0 or row_idx >= len(self.current_rows):
            return None
        r = self.current_rows[row_idx]
        return {
            "id": r[0],
            "name": r[1],
            "phone": r[2],
            "address": r[3],
            "stage": r[4],
            "confession_father": r[5],
            "confession_status": r[6],
            "last_visit": r[7],
            "next_visit": r[8],
            "spiritual_needs": r[9],
            "notes": r[10],
            "tags": r[11],
            "is_favorite": r[12]
        }

    def on_row_selected(self):
        rec = self.get_selected_record_dict()
        if not rec:
            return
        self.lbl_sel_name.setText(f"👤 {rec['name']} ({rec['stage']})")
        info_lines = [
            f"📱 رقم الهاتف: {rec['phone'] or 'غير مسجل'}",
            f"📍 العنوان: {rec['address'] or 'غير مسجل'}",
            f"⛪ أب الاعتراف: {rec['confession_father'] or 'غير محدد'}",
            f"📅 آخر افتقاد: {rec['last_visit'] or '—'} | القادم: {rec['next_visit'] or '—'}",
            f"🏷️ الوسوم: {rec['tags'] or '—'}",
            "",
            "🎯 الاحتياجات والظروف الخاصة:",
            rec['spiritual_needs'] or "لا توجد احتياجات مسجلة.",
            "",
            "📝 ملاحظات وتوصيات الخدمة:",
            rec['notes'] or "لا توجد ملاحظات مسجلة."
        ]
        self.txt_details.setText("\n".join(info_lines))

    def add_new_record(self):
        dlg = EditRecordDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_records()

    def edit_selected_record(self):
        rec = self.get_selected_record_dict()
        if not rec:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مخدوم من الجدول أولاً.")
            return
        dlg = EditRecordDialog(self, record_data=rec)
        if dlg.exec_() == QDialog.Accepted:
            self.load_records()
            self.on_row_selected()

    def delete_selected_record(self):
        rec = self.get_selected_record_dict()
        if not rec:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مخدوم لحذفه.")
            return
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف سجل المخدوم:\n{rec['name']}؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_pastoral_record(rec['id'], self.db_path)
            self.load_records()
            self.txt_details.clear()
            self.lbl_sel_name.setText("تم حذف السجل.")

    def generate_msg_for_selected(self):
        rec = self.get_selected_record_dict()
        if not rec:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مخدوم من الجدول لتوليد الرسالة له.")
            return

        self.txt_smart_msg.setText("⏳ جاري صياغة رسالة الافتقاد بالمحبة وآيات الكتاب المقدس...")

        self.worker_thread = QThread()
        self.worker = SmartMessageWorker(rec)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_msg_generated)
        self.worker.error.connect(lambda e: self.txt_smart_msg.setText(f"خطأ: {e}"))

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_msg_generated(self, msg_text):
        self.txt_smart_msg.setText(msg_text)

    def copy_smart_msg(self):
        text = self.txt_smart_msg.toPlainText().strip()
        if not text:
            return
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "تم النسخ", "تم نسخ رسالة الافتقاد إلى الحافظة، جاهزة للصق في واتساب مباشرة!")

    def export_records_csv(self):
        if not self.current_rows:
            QMessageBox.information(self, "تنبيه", "لا توجد سجلات لتصديرها.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير كشف الافتقاد",
            f"كشف_افتقاد_المكتبة_{datetime.date.today()}.csv",
            "ملفات CSV (*.csv)"
        )
        if not save_path:
            return

        import csv
        try:
            with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "الكود", "الاسم الكامل", "الهاتف", "العنوان", "المرحلة",
                    "أب الاعتراف", "حالة الاعتراف", "آخر افتقاد", "الافتقاد القادم",
                    "الاحتياجات والظروف", "الملاحظات", "الوسوم"
                ])
                for r in self.current_rows:
                    writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]])
            QMessageBox.information(self, "تم التصدير", f"تم حفظ كشف الافتقاد بنجاح في:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ الملف:\n{e}")
