# -*- coding: utf-8 -*-
"""
ArchiveMaster - DeepTutor Coptic Learning & Socratic Quiz Engine
محرك ديب تيوتر الكنسي: توليد مسابقات تفاعلية، اختبارات عقائدية، ومسارات تعليمية متدرجة
Inspired by HKUDS/DeepTutor: Agent-native Socratic mastery learning with 100% offline capability.
"""

import os
import sys
import json
import re
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QGroupBox, QSpinBox, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont

from modules import ai_handler, apologetics_db, database_handler


class DeepTutorWorker(QObject):
    sig_finished = pyqtSignal(dict)
    sig_status = pyqtSignal(str)
    sig_error = pyqtSignal(str)

    def __init__(self, topic: str, difficulty: str = "متوسط", num_questions: int = 5, target_group: str = "خدام وخريجين"):
        super().__init__()
        self.topic = topic
        self.difficulty = difficulty
        self.num_questions = max(3, min(num_questions, 15))
        self.target_group = target_group

    def run(self):
        try:
            self.sig_status.emit(f"🔍 تحليل موضوع «{self.topic}» واستخراج المفاهيم الكنسية الأساسية...")
            
            # 1. Fetch grounding context from local SQLite & Apologetics DB
            grounding_text = self._gather_grounding_context(self.topic)

            prompt = f"""أنت «المعلم الكنسي التفاعلي» (DeepTutor الكنسي). قم بإعداد ورقة مسابقة واختبار فهم متدرج في موضوع:
«{self.topic}»
المستوى المطلوب: {self.difficulty}
الفئة المستهدفة: {self.target_group}
عدد الأسئلة: {self.num_questions}

اعتمد على المراجع والشواهد الكنسية الآبائية التالية:
{grounding_text}

المطلوب: توليد استبيان تعليمي منظم جداً يتضمن:
1. مقدمة تعليمية موجزة ومحورية عن المفهوم (Concept Primer).
2. أسئلة اختيار من متعدد (MCQ) - كل سؤال معه 4 خيارات، مع توضيح الإجابة الصحيحة والتعليل اللاهوتي الموثق.
3. أسئلة صح أو خطأ مع تصويب الخطأ وشاهده.
4. سؤال تأملي تحليلي متقدم لربط الفكر الآبائي بالحياة المعاصرة (Socratic Reflection).

أجب بصيغة عربية فصحى دقيقة ومرتبة بعناوين واضحة وجداول."""

            sys_inst = "أنت معلم لاهوتي وقبطي أرثوذكسي رصين، تستند في كل سؤال وإجابة إلى أقوال الآباء والآيات الكتابية بدقة تامة."

            self.sig_status.emit("🧠 توليد الأسئلة والشواهد التعليمية عبر المحرك الذكي (مع إمكانية البديل الأوفلاين)...")
            res_content = ai_handler.call_ai_routed(prompt, system_instruction=sys_inst)

            result = {
                "topic": self.topic,
                "difficulty": self.difficulty,
                "target_group": self.target_group,
                "content": res_content,
                "grounding": grounding_text
            }
            self.sig_finished.emit(result)
        except Exception as e:
            self.sig_error.emit(str(e))

    def _gather_grounding_context(self, topic: str) -> str:
        ctx_parts = []
        # Check Apologetics DB
        topic_lower = topic.lower()
        for item in apologetics_db.APOLOGETICS_TOPICS:
            q = item.get("question", "")
            cat = item.get("category", "")
            kws = item.get("keywords", [])
            if any(w in topic_lower for w in [cat.lower()] + [k.lower() for k in kws] + q.lower().split()):
                ctx_parts.append(f"• المفهوم: {q}\n  الملخص: {item.get('summary')}\n  المراجع: {', '.join(item.get('core_references', []))}")
                if len(ctx_parts) >= 3:
                    break

        # Check local DB files
        try:
            conn = database_handler.get_db_connection()
            cur = conn.cursor()
            words = [w for w in re.sub(r'[^\w\s]', '', topic).split() if len(w) > 2]
            if words:
                clause = " OR ".join(["file_name LIKE ?" for _ in words[:3]])
                cur.execute(f"SELECT file_name FROM files WHERE {clause} LIMIT 4", [f"%{w}%" for w in words[:3]])
                rows = cur.fetchall()
                if rows:
                    book_names = [r[0] for r in rows]
                    ctx_parts.append(f"• مراجع محلية متوفرة في مكتبتك: {', '.join(book_names)}")
            conn.close()
        except Exception:
            pass

        return "\n".join(ctx_parts) if ctx_parts else "المصادر العامة للتراث الآبائي والكتابي القبطي الأرثوذكسي."


class DeepTutorDialog(QDialog):
    """
    Dedicated Interactive Socratic Tutor & Quiz Generator Window (DeepTutor Coptic Suite).
    """
    def __init__(self, parent=None, initial_topic=""):
        super().__init__(parent)
        self.setWindowTitle("🎓 المعلم الكنسي التفاعلي ومولد المسابقات (DeepTutor Suite)")
        self.resize(920, 680)
        self.setLayoutDirection(Qt.RightToLeft)

        self.initial_topic = initial_topic
        self.current_result = None

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1E232D;
                color: #E2E8F0;
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
            }
            QGroupBox {
                background-color: #252B36;
                border: 1px solid #3A4454;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                font-size: 13px;
                color: #E5C07B;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 10px;
            }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #14171E;
                color: white;
                border: 1px solid #3A4454;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #14171E;
                color: #E2E8F0;
                border: 1px solid #3A4454;
                border-radius: 6px;
                font-size: 13px;
                line-height: 1.6;
                padding: 10px;
            }
            QPushButton {
                background-color: #2D3442;
                color: white;
                border: 1px solid #3A4454;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #384254; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        h_box = QHBoxLayout()
        icon_lbl = QLabel("🎓")
        icon_lbl.setStyleSheet("font-size: 32px;")
        h_box.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        t_lbl = QLabel("المعلم الكنسي التفاعلي ومولد المسابقات والامتحانات (DeepTutor Suite)")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E5C07B;")
        v_head.addWidget(t_lbl)

        sub_lbl = QLabel("تحويل أمهات الكتب والموضوعات اللاهوتية إلى مسارات دراسية تفاعلية، ومسابقات لمدارس الأحد مع شواهد توثيقية.")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_head.addWidget(sub_lbl)
        h_box.addLayout(v_head, 1)
        layout.addLayout(h_box)

        # Controls Group
        grp_ctrl = QGroupBox("⚙️ إعدادات الدرس / المسابقة")
        g_lay = QVBoxLayout(grp_ctrl)

        row1 = QHBoxLayout()
        lbl_top = QLabel("الموضوع أو الكتاب:")
        row1.addWidget(lbl_top)

        self.le_topic = QLineEdit()
        self.le_topic.setPlaceholderText("مثال: تجسد الكلمة للقديس أثناسيوس، سر التناول، طبيعة المسيح، مجمع نيقية...")
        if self.initial_topic:
            self.le_topic.setText(self.initial_topic)
        row1.addWidget(self.le_topic, 1)

        g_lay.addLayout(row1)

        row2 = QHBoxLayout()
        lbl_lvl = QLabel("مستوى الصعوبة:")
        row2.addWidget(lbl_lvl)

        self.cb_level = QComboBox()
        self.cb_level.addItems(["مبتدئ (مفاهيم ميسرة)", "متوسط (دراسة متعمقة)", "متقدم وباحثين (لاهوت مقارن وتاريخ نصوص)"])
        self.cb_level.setCurrentIndex(1)
        row2.addWidget(self.cb_level)

        lbl_grp = QLabel("الفئة المستهدفة:")
        row2.addWidget(lbl_grp)

        self.cb_group = QComboBox()
        self.cb_group.addItems(["أطفال مدارس الأحد (ابتدائي)", "فتيان وإعدادي/ثانوي", "خدام وشباب جامعي", "باحثون ودارسو إكليريكية"])
        self.cb_group.setCurrentIndex(2)
        row2.addWidget(self.cb_group)

        lbl_num = QLabel("عدد الأسئلة:")
        row2.addWidget(lbl_num)

        self.spn_num = QSpinBox()
        self.spn_num.setRange(3, 15)
        self.spn_num.setValue(5)
        row2.addWidget(self.spn_num)

        self.btn_generate = QPushButton("✨ توليد المسابقة التفاعلية الآن")
        self.btn_generate.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981); color: white; padding: 8px 20px;")
        self.btn_generate.clicked.connect(self.start_generation)
        row2.addWidget(self.btn_generate)

        g_lay.addLayout(row2)
        layout.addWidget(grp_ctrl)

        # Status & Progress
        self.lbl_status = QLabel("جاهز لتوليد المادة التعليمية والمسابقات.")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        # Result View
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setPlaceholderText("ستظهر هنا المادة التعليمية والأسئلة والخيارات والإجابات النموذجية والشواهد...")
        layout.addWidget(self.txt_result, 1)

        # Bottom Actions
        act_row = QHBoxLayout()
        self.btn_export_word = QPushButton("📝 تصدير إلى مستند Word جاهز للطباعة")
        self.btn_export_word.setEnabled(False)
        self.btn_export_word.setStyleSheet("background-color: #2563EB; color: white;")
        self.btn_export_word.clicked.connect(self.export_to_word)
        act_row.addWidget(self.btn_export_word)

        self.btn_copy = QPushButton("📋 نسخ المحتوى بالكامل")
        self.btn_copy.clicked.connect(self.copy_content)
        act_row.addWidget(self.btn_copy)

        act_row.addStretch()

        self.btn_close = QPushButton("إغلاق")
        self.btn_close.clicked.connect(self.accept)
        act_row.addWidget(self.btn_close)

        layout.addLayout(act_row)

    def start_generation(self):
        topic = self.le_topic.text().strip()
        if not topic:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة الموضوع أو اسم الكتاب المطلوب إعداد المسابقة حوله.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_export_word.setEnabled(False)
        self.lbl_status.setText("⏳ جاري استدعاء المعلم الكنسي التفاعلي والربط مع رصيد المكتبة...")

        self.thread = QThread()
        self.worker = DeepTutorWorker(
            topic=topic,
            difficulty=self.cb_level.currentText(),
            num_questions=self.spn_num.value(),
            target_group=self.cb_group.currentText()
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.sig_status.connect(self.lbl_status.setText)
        self.worker.sig_finished.connect(self.on_generation_finished)
        self.worker.sig_error.connect(self.on_generation_error)

        self.worker.sig_finished.connect(self.thread.quit)
        self.worker.sig_finished.connect(self.worker.deleteLater)
        self.worker.sig_error.connect(self.thread.quit)
        self.worker.sig_error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_generation_finished(self, result):
        self.btn_generate.setEnabled(True)
        self.btn_export_word.setEnabled(True)
        self.current_result = result
        self.txt_result.setPlainText(result.get("content", ""))
        self.lbl_status.setText("✅ اكتمل توليد المسابقة التعليمية بنجاح!")

    def on_generation_error(self, err):
        self.btn_generate.setEnabled(True)
        self.lbl_status.setText("❌ حدث خطأ أثناء التوليد.")
        QMessageBox.critical(self, "خطأ", f"تعذر استكمال التوليد:\n{err}")

    def copy_content(self):
        text = self.txt_result.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "تم النسخ", "تم نسخ نص المسابقة إلى الحافظة بنجاح.")

    def export_to_word(self):
        if not self.current_result:
            return
        topic = self.current_result.get("topic", "مسابقة_كنسية")
        safe_name = re.sub(r'[\\/*?:"<>|]', '', topic)
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ المسابقة كمستند Word",
            f"مسابقة_{safe_name}.docx",
            "Word Documents (*.docx)"
        )
        if not save_path:
            return

        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()
            title = doc.add_paragraph()
            title.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = title.add_run(f"مسابقة واختبار فهم: {topic}")
            run.font.size = Pt(18)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x99, 0x1B, 0x1B)

            sub = doc.add_paragraph()
            sub.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            sub.add_run(f"الفئة: {self.current_result.get('target_group')} | المستوى: {self.current_result.get('difficulty')} | إعداد: المعلم الكنسي DeepTutor\n")

            content = self.current_result.get("content", "")
            for line in content.split("\n"):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p.add_run(line)

            doc.save(save_path)
            QMessageBox.information(self, "تم التصدير", f"✅ تم حفظ مستند Word بنجاح في:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر التصدير إلى Word:\n{e}")
