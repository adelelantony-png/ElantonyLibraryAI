# -*- coding: utf-8 -*-
"""
ArchiveMaster - Church Drama & Sketch Studio
أستوديو الاسكتش والمسرحيات الكنسية الهادفة لمدارس الأحد ومؤتمرات الشباب
مستوحى ومطور بالاستفادة من منظومة الرعاية والخدمات الكنسية الذكية.
"""

import os
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextBrowser, QProgressBar, QMessageBox,
    QGroupBox, QFileDialog, QTabWidget, QWidget, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QFont

from modules import ai_handler
from modules import library_rag

# Church Drama Presets
DRAMA_PRESETS = [
    ("سفينة النجاة والسلام الداخلي وسط العاصفة", "مرقس 4: 35-41", "شباب وإعدادي", "متوسط (10-15 دقيقة)"),
    ("الابن الضال: العودة من كورة الخنازير لحضن الآب", "لوقا 15: 11-32", "إعدادي وثانوي", "متوسط (10-15 دقيقة)"),
    ("داود وجليات: الإيمان البسيط يسقط عملاق الخوف", "1 صموئيل 17", "أطفال ومدارس أحد", "قصير (5-7 دقائق)"),
    ("أمانة يوسف الصديق في بيت فوطيفار والسجن", "تكوين 39", "فتيان وشباب", "متوسط (10-15 دقيقة)"),
    ("فخ الشاشات والسوشيال ميديا: مينا واستعادة السلام الروحي", "1 كورنثوس 6: 12", "إعدادي وثانوي", "متوسط (10-15 دقيقة)"),
    ("صداقة حقيقية أم مسايرة العالم؟", "1 كورنثوس 15: 33", "شباب وجامعيين", "متوسط (10-15 دقيقة)"),
    ("القديس أبانوب النهيسي: ثبات الإيمان ووداعة الشهداء", "سير الشهداء", "أطفال وفتيان", "قصير (5-7 دقائق)"),
    ("مثل السامري الصالح: المحبة العملية وكسر الحواجز", "لوقا 10: 25-37", "اجتماع عام وأسرة", "متوسط (10-15 دقيقة)")
]

DRAMA_STAGES = {
    "primary": {
        "name": "أطفال مدارس الأحد (ابتدائي 1 - 6)",
        "tone": "بسيط ومرح ومباشر، شخصيات محبوبة، مواقف طريفة تجذب الانتباه، رسالة واضحة لا لبس فيها."
    },
    "prep": {
        "name": "مرحلة الفتيان والناشئين (إعدادي 12 - 15 سنة)",
        "tone": "حوار واقعي يلامس مشاكل الدراسة وضغط الأصدقاء، صراع بين الرغبة في التميز وثبات المبادئ."
    },
    "youth": {
        "name": "مرحلة الشباب والجامعيين (ثانوي وجامعة)",
        "tone": "حوار عميق، نقاش فكري ولاهوتي ووجداني، معالجة مشاعر التوهان والبحث عن الهوية والرجاء الحقيقي."
    },
    "family": {
        "name": "اجتماع الأسرة والشعب العام",
        "tone": "يلامس تفاصيل البيوت اليومية، التفاهم الزوجي، تربية الأبناء، واللجوء للكنيسة والصلاة."
    }
}

DRAMA_LENGTHS = {
    "short": "اسكتش قصير سريع (5 دقائق - مشهدان مركزان)",
    "medium": "اسكتش متوسط متكامل (10 - 15 دقيقة - 3 مشاهد)",
    "full": "مسرحية كنسية كاملة (20 دقيقة - مشاهد متعددة للمهرجانات)"
}

DRAMA_PROMPT_TEMPLATE = """
أنت كاتب ومخرج مسرحي قبطي أرثوذكسي متمرس وخبير في عروض التربية الكنسية ومهرجانات الكرازة المرقسية.
مطلوب منك كتابة سيناريو مسرحي/اسكتش هادف وشيق ومؤثر جداً باللغة العربية الفصحى أو العامية المصرية الراقية الدافئة (الحوار اليومي المسيحي المليء بالمحبة).

📌 مواصفات العمل المطلوبة:
- الفئة المستهدفة: {stage_name} ({stage_tone})
- موضوع العمل: {topic}
- الشاهد الكتابي أو المناسبة: {scripture}
- مدة العرض ونوعه: {duration}
- عدد الشخصيات المقترح: {char_count}

📚 شواهد ومقتطفات من المكتبة الكنسية المحلية:
{rag_context}

🎯 الهيكل الإلزامي للنص المسرحي (يجب كتابته بتفصيل درامي ممتع واحترافي):

# عنوان المسرحية / الاسكتش

### 1. بطاقة العمل والهدف الروحي
- **الهدف الروحي الرئيسي:** ما هي الرسالة التي ستصل لقلب المشاهد في نهاية العرض؟
- **الآية المركزية للعمل:**
- **المناسبة المقترحة:** (مدارس أحد، مؤتمر، حفلة عيد، نهضة، إلخ).

### 2. كشف الشخصيات والتوصيف الدرامي
(اكتب جدولاً أو قائمة لكل شخصية: الاسم، السن التقريبي، التوصيف النفسي، طبيعة الملابس أو المظهر، الدافع في القصة).

### 3. المشاهد المسرحية (Scene by Scene)
لكل مشهد من المشاهد، يجب كتابة التفاصيل التالية بدقة إخراجية احترافية:
- **عنوان المشهد وملخصه السريع:**
- **الديكور وتوزيع خشبة المسرح (Decor & Place):** كيف يبدو المسرح عند فتح الستار؟
- **إشارات الإضاءة المسرحية (Lighting Cue):** (مثال: إضاءة دافئة، بقعة ضوء زرقاء مركزة، إظلام تدريجي...).
- **المؤثرات الصوتية والموسيقى (Sound & Coptic Music):** (مثال: ناي حزين، لحن قبطي خافت، أصوات رياح...).
- **نص الحوار الكامل بين الشخصيات:** 
  - يجب كتابة اسم الشخصية قبل كل جملة.
  - يجب وضع توجيهات الحركة والانفعال ولغة الجسد بين قوسين معقوفين `[actionCue]` مثل: `[ينظر بحيرة ويتنهد]` أو `[يبتسم ويضع يده على كتفه بمحبة]`.
- **ملاحظات المخرج الكنسي للمشهد (Director's Notes):** نصائح للممثلين لتوصيل الرسالة دون مبالغة مصطنعة.

### 4. الخاتمة والاقتراح اللحني أو الترنيمة الختامية
- المشهد الختامي ورسالة الرجاء.
- اقتراح ترنيمة أو لحن قبطي مناسب يختتم به العمل مع نزول الستار.
"""

def generate_church_drama_script(stage_key, topic, scripture="", duration="medium", char_count="3 إلى 4 شخصيات", library_root=None, project_id=1):
    """Generates a complete church drama script using ArchiveMaster AI and local RAG."""
    stage_info = DRAMA_STAGES.get(stage_key, DRAMA_STAGES["prep"])
    duration_text = DRAMA_LENGTHS.get(duration, DRAMA_LENGTHS["medium"])

    rag_context = ""
    try:
        search_query = f"{topic} {scripture}"
        has_sources, context_text, _ = library_rag.extract_relevant_snippets(
            search_query,
            library_root=library_root,
            project_id=project_id,
            max_total_chars=3000
        )
        if has_sources and context_text:
            rag_context = context_text
    except Exception as e:
        print(f"Drama RAG warning: {e}")

    if not rag_context:
        rag_context = "مستند إلى تعاليم الكنيسة القبطية الأرثوذكسية وسير الآباء والشهداء وقصص الكتاب المقدس."

    prompt = DRAMA_PROMPT_TEMPLATE.format(
        stage_name=stage_info["name"],
        stage_tone=stage_info["tone"],
        topic=topic,
        scripture=scripture or "حسب سياق الموضوع",
        duration=duration_text,
        char_count=char_count,
        rag_context=rag_context
    )

    sys_instruction = "أنت كاتب مسرحي مسيحي قبطي أرثوذكسي محترف، تكتب نصوصاً مسرحية عميقة وشيقة ومؤثرة تخدم كنيسة المسيح ومدارس الأحد."
    response = ai_handler.call_ai_routed(prompt, system_instruction=sys_instruction)
    return response


def set_paragraph_rtl(paragraph):
    """Forces RTL alignment and bidi markers in python-docx."""
    try:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        pPr = paragraph._p.get_or_add_pPr()
        pBdr = OxmlElement('w:bidi')
        pBdr.set(qn('w:val'), '1')
        pPr.append(pBdr)
        paragraph.alignment = 2  # WD_ALIGN_PARAGRAPH.RIGHT
    except Exception:
        pass


def export_drama_to_docx(script_text, output_path, title="اسكتش مسرحي كنسي"):
    """Exports drama script text into a beautifully styled Microsoft Word document."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        raise RuntimeError("مكتبة python-docx غير مثبتة. يرجى تثبيتها عبر: pip install python-docx")

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Header Title
    title_p = doc.add_paragraph()
    set_paragraph_rtl(title_p)
    run_cross = title_p.add_run("✠ ")
    run_cross.font.size = Pt(22)
    run_cross.font.color.rgb = RGBColor(212, 175, 55) # Gold
    run_cross.font.bold = True

    run_t = title_p.add_run(f"{title}\n")
    run_t.font.name = "Arial"
    run_t.font.size = Pt(20)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(18, 61, 88) # Deep Slate Blue

    sub_p = doc.add_paragraph()
    set_paragraph_rtl(sub_p)
    run_sub = sub_p.add_run("كُتب وأُعد بواسطة: مكتبة الصليب القبطية - أستوديو المسرح والتربية الكنسية الذكية\n")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph("—" * 45)

    # Process script lines
    lines = script_text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        p = doc.add_paragraph()
        set_paragraph_rtl(p)

        if stripped.startswith("# "):
            run = p.add_run(stripped.replace("# ", ""))
            run.font.name = "Arial"
            run.font.size = Pt(17)
            run.font.bold = True
            run.font.color.rgb = RGBColor(18, 61, 88)
        elif stripped.startswith("## ") or stripped.startswith("### "):
            header_text = re.sub(r"^#+\s*", "", stripped)
            run = p.add_run(header_text)
            run.font.name = "Arial"
            run.font.size = Pt(13)
            run.font.bold = True
            run.font.color.rgb = RGBColor(180, 83, 9) # Amber
        elif stripped.startswith("- **") or stripped.startswith("* **"):
            parts = stripped.split("**")
            if len(parts) >= 3:
                r_bullet = p.add_run("• ")
                r_bullet.font.bold = True
                r_bullet.font.color.rgb = RGBColor(25, 125, 128)
                r_bold = p.add_run(parts[1] + ": ")
                r_bold.font.bold = True
                r_bold.font.color.rgb = RGBColor(30, 41, 59)
                r_rest = p.add_run("".join(parts[2:]).lstrip(": "))
                r_rest.font.name = "Arial"
                r_rest.font.size = Pt(11)
            else:
                run = p.add_run(stripped)
                run.font.name = "Arial"
                run.font.size = Pt(11)
        elif "[" in stripped and "]" in stripped and not stripped.startswith("-"):
            # Line with character action cue
            # Format action cues in gray italic
            cur_parts = re.split(r"(\[[^\]]+\])", stripped)
            for part in cur_parts:
                if part.startswith("[") and part.endswith("]"):
                    r_cue = p.add_run(part)
                    r_cue.font.name = "Arial"
                    r_cue.font.size = Pt(10)
                    r_cue.font.italic = True
                    r_cue.font.color.rgb = RGBColor(120, 113, 108) # Muted Brown/Gray
                else:
                    r_dial = p.add_run(part)
                    r_dial.font.name = "Arial"
                    r_dial.font.size = Pt(11)
                    if ":" in part:
                        r_dial.font.bold = True
                        r_dial.font.color.rgb = RGBColor(15, 23, 42)
        else:
            run = p.add_run(stripped)
            run.font.name = "Arial"
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(51, 65, 85)

    doc.save(output_path)
    return output_path


class DramaWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, stage_key, topic, scripture, duration, char_count, library_root, project_id):
        super().__init__()
        self.stage_key = stage_key
        self.topic = topic
        self.scripture = scripture
        self.duration = duration
        self.char_count = char_count
        self.library_root = library_root
        self.project_id = project_id

    def run(self):
        try:
            res = generate_church_drama_script(
                self.stage_key,
                self.topic,
                self.scripture,
                self.duration,
                self.char_count,
                self.library_root,
                self.project_id
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class ChurchDramaStudioDialog(QDialog):
    """
    Church Drama & Sketch Studio Dialog
    واجهة أستوديو الاسكتش والمسرحيات الكنسية
    """
    def __init__(self, parent=None, library_root=None, project_id=1, initial_topic=""):
        super().__init__(parent)
        self.setWindowTitle("🎭 أستوديو الاسكتش والمسرحيات الكنسية الهادفة (Church Drama Studio)")
        self.resize(1000, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self.library_root = library_root
        self.project_id = project_id
        self.initial_topic = initial_topic
        self.generated_script = ""
        self.worker_thread = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #14171F; font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif; }
            QWidget { background-color: transparent; color: #D7DAE0; font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif; }
            QLabel { font-size: 13px; color: #E2E8F0; font-weight: 500; }
            QComboBox, QLineEdit {
                background-color: #1E222A; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 7px 12px; font-size: 13px;
            }
            QComboBox:focus, QLineEdit:focus { border: 1px solid #F59E0B; }
            QGroupBox {
                border: 1px solid #334155; border-radius: 8px; margin-top: 10px;
                padding-top: 14px; font-weight: bold; color: #FBBF24;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; padding: 0 10px; }
            QTextBrowser {
                background-color: #1A1D24; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 8px; padding: 14px; font-size: 14px; line-height: 1.6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #0F172A);
                border-radius: 8px; border: 1px solid #F59E0B; padding: 6px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_icon = QLabel("🎭")
        h_icon.setStyleSheet("font-size: 32px; background: transparent;")
        h_lay.addWidget(h_icon)

        v_t = QVBoxLayout()
        lbl_title = QLabel("أستوديو الاسكتش والمسرحيات الكنسية الهادفة")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FBBF24; background: transparent;")
        lbl_sub = QLabel("توليد سيناريوهات مسرحية متكاملة لمدارس الأحد ومؤتمرات الشباب مع الديكور، الإضاءة، المؤثرات، والحوار الإخراجي.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #93C5FD; background: transparent;")
        v_t.addWidget(lbl_title)
        v_t.addWidget(lbl_sub)
        h_lay.addLayout(v_t, 1)
        layout.addWidget(header)

        # 2. Controls & Configuration Box
        ctrl_box = QGroupBox("⚙️ إعدادات العمل المسرحي المطلوب")
        ctrl_lay = QVBoxLayout(ctrl_box)
        ctrl_lay.setSpacing(10)

        # Row 1: Presets + Stages
        row1 = QHBoxLayout()
        lbl_p = QLabel("قوالب جاهزة ملهمة:")
        self.combo_presets = QComboBox()
        self.combo_presets.addItem("⚡ اختر عملاً جاهزاً أو اكتب فكرتك أدناه...", "")
        for item in DRAMA_PRESETS:
            self.combo_presets.addItem(f"🎬 {item[0]} ({item[1]})", item)
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selected)
        row1.addWidget(lbl_p)
        row1.addWidget(self.combo_presets, 1)

        lbl_stage = QLabel("المرحلة:")
        self.combo_stage = QComboBox()
        for k, v in DRAMA_STAGES.items():
            self.combo_stage.addItem(v["name"], k)
        self.combo_stage.setCurrentIndex(1) # prep
        row1.addWidget(lbl_stage)
        row1.addWidget(self.combo_stage)
        ctrl_lay.addLayout(row1)

        # Row 2: Duration + Characters
        row2 = QHBoxLayout()
        lbl_dur = QLabel("مدة العرض:")
        self.combo_duration = QComboBox()
        for k, v in DRAMA_LENGTHS.items():
            self.combo_duration.addItem(v, k)
        self.combo_duration.setCurrentIndex(1) # medium
        row2.addWidget(lbl_dur)
        row2.addWidget(self.combo_duration, 1)

        lbl_chars = QLabel("عدد الممثلين:")
        self.combo_chars = QComboBox()
        self.combo_chars.addItems(["شخصيتان (حوار ثنائي مكثف)", "3 إلى 4 شخصيات (أنسب لمدارس الأحد)", "5 إلى 6 شخصيات (عرض شامل)", "فريق تمثيل مفتوح مع كورس"])
        self.combo_chars.setCurrentIndex(1)
        row2.addWidget(lbl_chars)
        row2.addWidget(self.combo_chars)
        ctrl_lay.addLayout(row2)

        # Row 3: Topic + Scripture
        row3 = QHBoxLayout()
        lbl_topic = QLabel("الموضوع أو الفكرة:")
        self.le_topic = QLineEdit()
        self.le_topic.setPlaceholderText("اكتب فكرة المسرحية أو المشكلة الروحية (مثال: مواجهة التنمر، الرجوع لحضن الكنيسة)...")
        if self.initial_topic:
            self.le_topic.setText(self.initial_topic)
        row3.addWidget(lbl_topic)
        row3.addWidget(self.le_topic, 1)

        lbl_scrip = QLabel("الشاهد الكتابي:")
        self.le_scripture = QLineEdit()
        self.le_scripture.setPlaceholderText("اختياري (مثال: لوقا 15: 11، متى 8: 26)...")
        row3.addWidget(lbl_scrip)
        row3.addWidget(self.le_scripture)
        ctrl_lay.addLayout(row3)

        # Generate Button
        self.btn_generate = QPushButton("🚀 صياغة وتأليف النص المسرحي بالذكاء والمراجع الأرثوذكسية")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D97706);
                color: white; font-weight: bold; font-size: 13px; padding: 11px;
                border-radius: 6px; border: 1px solid #F59E0B;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #F59E0B); }
            QPushButton:disabled { background-color: #334155; color: #94A3B8; border: none; }
        """)
        self.btn_generate.clicked.connect(self.start_generation)
        ctrl_lay.addWidget(self.btn_generate)

        layout.addWidget(ctrl_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 4px; text-align: center; height: 8px; }
            QProgressBar::chunk { background-color: #F59E0B; }
        """)
        layout.addWidget(self.progress_bar)

        # 3. Output Viewer
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setPlaceholderText("سيظهر هنا السيناريو المسرحي الكامل المنسق، جاهزاً للطباعة أو الإخراج والتوزيع على الممثلين...")
        layout.addWidget(self.viewer, 1)

        # 4. Action Buttons Bar
        act_row = QHBoxLayout()

        self.btn_export_docx = QPushButton("📄 تصدير النص المسرحي إلى ملف Word (.docx) منسق للإخراج")
        self.btn_export_docx.setEnabled(False)
        self.btn_export_docx.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; color: white; font-weight: bold;
                padding: 10px 18px; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #3B82F6; }
            QPushButton:disabled { background-color: #334155; color: #64748B; }
        """)
        self.btn_export_docx.clicked.connect(self.export_docx)
        act_row.addWidget(self.btn_export_docx)

        self.btn_copy = QPushButton("📋 نسخ السيناريو كاملاً")
        self.btn_copy.setEnabled(False)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: white; font-weight: bold;
                padding: 10px 16px; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
            QPushButton:disabled { color: #64748B; }
        """)
        self.btn_copy.clicked.connect(self.copy_script_text)
        act_row.addWidget(self.btn_copy)

        act_row.addStretch()

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1E222A; color: #94A3B8;
                padding: 10px 18px; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { color: white; background-color: #334155; }
        """)
        btn_close.clicked.connect(self.accept)
        act_row.addWidget(btn_close)

        layout.addLayout(act_row)

    def on_preset_selected(self, index):
        if index <= 0:
            return
        data = self.combo_presets.itemData(index)
        if data:
            self.le_topic.setText(data[0])
            self.le_scripture.setText(data[1])

    def start_generation(self):
        topic = self.le_topic.text().strip()
        if not topic:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة فكرة أو موضوع المسرحية أولاً.")
            return

        stage_key = self.combo_stage.currentData()
        duration_key = self.combo_duration.currentData()
        char_count = self.combo_chars.currentText()
        scripture = self.le_scripture.text().strip()

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("⏳ جاري كتابة وتأليف السيناريو المسرحي واسترجاع المراجع...")
        self.progress_bar.setVisible(True)

        self.worker_thread = QThread()
        self.worker = DramaWorker(
            stage_key,
            topic,
            scripture,
            duration_key,
            char_count,
            self.library_root,
            self.project_id
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_generation_finished(self, script_text):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 صياغة وتأليف النص المسرحي بالذكاء والمراجع الأرثوذكسية")

        self.generated_script = script_text
        html = self.markdown_to_html(script_text)
        self.viewer.setHtml(html)

        self.btn_export_docx.setEnabled(True)
        self.btn_copy.setEnabled(True)

    def on_generation_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 صياغة وتأليف النص المسرحي بالذكاء والمراجع الأرثوذكسية")
        QMessageBox.critical(self, "خطأ في التأليف المسرحي", f"تعذر إتمام كتابة السيناريو:\n{err_msg}")

    def markdown_to_html(self, md_text):
        """Converts generated drama script markdown into styled HTML with cues."""
        import html
        lines = md_text.splitlines()
        html_out = ["<div style='direction: rtl; text-align: right; font-family: Cairo, Segoe UI, sans-serif; color: #E2E8F0; line-height: 1.8;'>"]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                html_out.append("<div style='height: 8px;'></div>")
                continue

            # Headers
            if stripped.startswith("# "):
                h = html.escape(stripped.replace("# ", ""))
                html_out.append(f"<h1 style='color: #FBBF24; font-size: 20px; border-bottom: 1px solid #D97706; padding-bottom: 6px; margin-top: 14px;'>🎬 {h}</h1>")
            elif stripped.startswith("## ") or stripped.startswith("### "):
                h = html.escape(re.sub(r"^#+\s*", "", stripped))
                html_out.append(f"<h2 style='color: #38BDF8; font-size: 15px; margin-top: 16px; margin-bottom: 6px; font-weight: bold;'>📌 {h}</h2>")
            elif stripped.startswith("- **") or stripped.startswith("* **"):
                parts = stripped.split("**")
                if len(parts) >= 3:
                    lbl = html.escape(parts[1])
                    val = html.escape("".join(parts[2:]).lstrip(": "))
                    html_out.append(f"<p style='margin: 4px 0;'><b style='color: #FCD34D;'>• {lbl}:</b> <span style='color: #F1F5F9;'>{val}</span></p>")
                else:
                    html_out.append(f"<p style='margin: 4px 0; color: #CBD5E1;'>{html.escape(stripped)}</p>")
            elif "[" in stripped and "]" in stripped:
                # Format character dialogue and action cues
                escaped = html.escape(stripped)
                # Highlight cues in styled spans
                formatted = re.sub(
                    r"(\[[^\]]+\])",
                    r"<span style='color: #F59E0B; font-style: italic; background-color: #292524; padding: 1px 6px; border-radius: 4px; font-size: 12px;'>\1</span>",
                    escaped
                )
                html_out.append(f"<div style='margin: 6px 0; padding: 4px 8px; background-color: #1E232D; border-right: 3px solid #3B82F6; border-radius: 4px;'>{formatted}</div>")
            else:
                html_out.append(f"<p style='margin: 4px 0; color: #CBD5E1;'>{html.escape(stripped)}</p>")

        html_out.append("</div>")
        return "".join(html_out)

    def export_docx(self):
        if not self.generated_script:
            return

        topic = self.le_topic.text().strip() or "مسرحية_كنسية"
        clean_name = re.sub(r'[\\/*?:"<>|]', "_", topic)[:35]
        default_file = f"مسرحية_{clean_name}.docx"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير السيناريو المسرحي إلى ملف Word",
            default_file,
            "مستندات Word (*.docx)"
        )

        if not save_path:
            return

        try:
            export_drama_to_docx(self.generated_script, save_path, title=topic)
            QMessageBox.information(
                self,
                "تم التصدير بنجاح",
                f"تم حفظ النص المسرحي المنسق في:\n{save_path}\n\nجاهز للطباعة والتوزيع الفوري على الممثلين وفريق الإخراج!"
            )
            # Try to open file
            try:
                os.startfile(save_path)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ الملف:\n{e}")

    def copy_script_text(self):
        if not self.generated_script:
            return
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.generated_script)
        QMessageBox.information(self, "تم النسخ", "تم نسخ السيناريو المسرحي كاملاً إلى الحافظة بنجاح.")
