# -*- coding: utf-8 -*-
"""
ArchiveMaster - Sunday School & Church Lesson Dialog
واجهة ورشة التربية الكنسية الذكية وإعداد دروس مدارس الأحد والمحاضرات المنبرية
مطور ومحدث بالاستفادة من منظومة الرعاية والخدمات الكنسية الذكية.
"""

import os
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextBrowser, QProgressBar,
    QFileDialog, QApplication, QGroupBox, QTabWidget, QWidget,
    QFrame, QSlider, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QIcon

from modules import sunday_school_builder

LESSON_PRESETS = [
    ("المحبة والغفران ومواجهة الإساءة", "متى 5: 38-48 (موعظة الجبل)", "spiritual_life", "primary_late"),
    ("الأمانة في القليل والصدق في كل شيء", "لوقا 16: 10 (مثل وكيل الظلم)", "bible", "primary_late"),
    ("داود وجليات: الشجاعة والإيمان يسقطان الخوف", "صموئيل الأول 17", "bible", "preparatory"),
    ("معجزة الخمس خبزات والسمكتين: روح البركة والعطاء", "يوحنا 6: 1-14", "bible", "primary_early"),
    ("القديس أثناسيوس الرسولي: الشجاعة وحفظ الإيمان", "رسالة يهوذا 1: 3", "patristics_history", "secondary_youth"),
    ("سر التوبة والاعتراف: العودة لحضن الآب", "لوقا 15 (الابن الضال)", "dogma_rite", "preparatory"),
    ("الصداقة النقية ومقاومة ضغط الأقران السلبي", "1 كورنثوس 15: 33", "spiritual_life", "preparatory"),
    ("الاستخدام المسيحي الواعي للسوشيال ميديا والشاشات", "1 كورنثوس 6: 12", "apologetics_ethics", "secondary_youth"),
    ("الصوم والصلاة: نقاء القلب وترويض الإرادة", "متى 6: 16-18", "dogma_rite", "secondary_youth"),
    ("خدمة الآخرين وغسل الأرجل بروح التواضع", "يوحنا 13: 1-17", "spiritual_life", "primary_late")
]


class OratoricalPresentationDialog(QDialog):
    """
    Live Oratorical Presentation Mode & Countdown Timer
    شاشة الإلقاء المنبري الحي مع المؤقت التنازلي وخط مريح للعين
    """
    def __init__(self, parent=None, title="", oral_script="", full_content="", duration_minutes=25):
        super().__init__(parent)
        self.setWindowTitle(f"🎙️ شاشة الإلقاء المنبري الحي - {title}")
        self.resize(1100, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self.oral_script = oral_script or full_content
        self.full_content = full_content
        self.total_seconds = int(duration_minutes) * 60
        self.remaining_seconds = self.total_seconds
        self.is_timer_running = False
        self.current_font_size = 20

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_tick)

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #09141D; font-family: 'Cairo', 'Segoe UI', sans-serif; }
            QLabel { color: #F1F5F9; font-family: 'Cairo', 'Segoe UI', sans-serif; }
            QTextBrowser {
                background-color: #0F1F2B; color: #F8FAFC; border: 1px solid #223D52;
                border-radius: 10px; padding: 18px; line-height: 1.8;
            }
            QTabWidget::pane { border: 1px solid #223D52; background: #0F1F2B; border-radius: 8px; }
            QTabBar::tab {
                background: #142838; color: #94A3B8; padding: 10px 20px; font-weight: bold;
                border-top-left-radius: 6px; border-top-right-radius: 6px; margin-left: 2px;
            }
            QTabBar::tab:selected { background: #197D80; color: white; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Top Bar: Live Timer & Font Controls
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #0F1F2B; border: 1px solid #223D52; border-radius: 8px; padding: 6px 14px;")
        t_lay = QHBoxLayout(top_bar)

        # Timer Display
        self.lbl_timer = QLabel(self.format_time(self.remaining_seconds))
        self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: 900; color: #34D399; font-family: 'Consolas', monospace;")
        t_lay.addWidget(self.lbl_timer)

        self.btn_timer_toggle = QPushButton("▶️ بدء المؤقت")
        self.btn_timer_toggle.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        self.btn_timer_toggle.clicked.connect(self.toggle_timer)
        t_lay.addWidget(self.btn_timer_toggle)

        btn_timer_reset = QPushButton("🔄 إعادة ضبط")
        btn_timer_reset.setStyleSheet("background-color: #334155; color: white; padding: 7px 12px; border-radius: 6px;")
        btn_timer_reset.clicked.connect(self.reset_timer)
        t_lay.addWidget(btn_timer_reset)

        t_lay.addStretch()

        # Font size adjustment
        lbl_f = QLabel("حجم الخط للإلقاء:")
        lbl_f.setStyleSheet("color: #94A3B8; font-size: 12px;")
        t_lay.addWidget(lbl_f)

        btn_font_plus = QPushButton("🔍 A+")
        btn_font_plus.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-weight: bold; padding: 6px 12px; border-radius: 5px;")
        btn_font_plus.clicked.connect(lambda: self.change_font_size(2))
        t_lay.addWidget(btn_font_plus)

        btn_font_minus = QPushButton("🔍 A-")
        btn_font_minus.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-weight: bold; padding: 6px 12px; border-radius: 5px;")
        btn_font_minus.clicked.connect(lambda: self.change_font_size(-2))
        t_lay.addWidget(btn_font_minus)

        btn_close = QPushButton("خروج من شاشة الإلقاء ✕")
        btn_close.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        t_lay.addWidget(btn_close)

        layout.addWidget(top_bar)

        # 2. Main Tabs: Oral Script & Full Plan
        self.tabs = QTabWidget()

        # Tab 1: Oral Delivery Script (Primary)
        self.browser_oral = QTextBrowser()
        self.browser_oral.setHtml(self.render_oral_html())
        self.tabs.addTab(self.browser_oral, "🎙️ سيناريو الإلقاء الشفهي المباشر (جاهز للقراءة في الاجتماع)")

        # Tab 2: Full Detailed Plan
        self.browser_full = QTextBrowser()
        self.browser_full.setHtml(self.render_full_html())
        self.tabs.addTab(self.browser_full, "📖 المخطط الكنسي الكامل والشرح الآبائي")

        layout.addWidget(self.tabs, 1)

    def format_time(self, seconds):
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def toggle_timer(self):
        if self.is_timer_running:
            self.timer.stop()
            self.is_timer_running = False
            self.btn_timer_toggle.setText("▶️ استئناف")
            self.btn_timer_toggle.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")
        else:
            self.timer.start(1000)
            self.is_timer_running = True
            self.btn_timer_toggle.setText("⏸️ إيقاف مؤقت")
            self.btn_timer_toggle.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")

    def reset_timer(self):
        self.timer.stop()
        self.is_timer_running = False
        self.remaining_seconds = self.total_seconds
        self.lbl_timer.setText(self.format_time(self.remaining_seconds))
        self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: 900; color: #34D399; font-family: 'Consolas', monospace;")
        self.btn_timer_toggle.setText("▶️ بدء المؤقت")
        self.btn_timer_toggle.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;")

    def update_timer_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.lbl_timer.setText(self.format_time(self.remaining_seconds))

            # Color coding
            if self.remaining_seconds <= 60:
                self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: 900; color: #EF4444; font-family: 'Consolas', monospace;")
            elif self.remaining_seconds <= 300:
                self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: 900; color: #F59E0B; font-family: 'Consolas', monospace;")
        else:
            self.timer.stop()
            self.lbl_timer.setText("00:00 ⏰")
            self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: 900; color: #EF4444; font-family: 'Consolas', monospace;")

    def change_font_size(self, delta):
        self.current_font_size = max(14, min(36, self.current_font_size + delta))
        self.browser_oral.setHtml(self.render_oral_html())
        self.browser_full.setHtml(self.render_full_html())

    def render_oral_html(self):
        text = self.oral_script or "لم يتوفر سيناريو إلقاء شفهي منفصل."
        import html
        escaped = html.escape(text).replace("\n\n", "</p><p>").replace("\n", "<br/>")
        return f"""
        <div style="direction: rtl; text-align: right; font-family: Cairo, Segoe UI, sans-serif;
                    font-size: {self.current_font_size}px; line-height: 2.0; color: #F8FAFC;">
            <div style="background-color: #197D80; color: white; padding: 8px 14px; border-radius: 6px; font-size: 14px; font-weight: bold; margin-bottom: 16px;">
                🎙️ سيناريو الإلقاء المنبري المباشر (اقرأ بصوت واضح ومريح أمام المخدومين):
            </div>
            <p>{escaped}</p>
        </div>
        """

    def render_full_html(self):
        import html
        lines = self.full_content.splitlines()
        html_out = [f"<div style='direction: rtl; text-align: right; font-family: Cairo, Segoe UI, sans-serif; font-size: {max(13, self.current_font_size - 4)}px; line-height: 1.8; color: #E2E8F0;'>"]
        for line in lines:
            line_s = line.strip()
            if not line_s:
                html_out.append("<div style='height: 8px;'></div>")
                continue
            if line_s.startswith("# "):
                h = html.escape(line_s.replace("# ", ""))
                html_out.append(f"<h1 style='color: #FBBF24; font-size: 20px; border-bottom: 1px solid #D97706; padding-bottom: 6px;'>{h}</h1>")
            elif line_s.startswith("### ") or line_s.startswith("## "):
                h = html.escape(re.sub(r"^#+\s*", "", line_s))
                html_out.append(f"<h2 style='color: #38BDF8; font-size: 16px; margin-top: 14px;'>📌 {h}</h2>")
            elif line_s.startswith("- **") or line_s.startswith("* **"):
                parts = line_s.split("**")
                if len(parts) >= 3:
                    lbl = html.escape(parts[1])
                    val = html.escape("".join(parts[2:]).lstrip(": "))
                    html_out.append(f"<p style='margin: 4px 0;'><b style='color: #FCD34D;'>• {lbl}:</b> <span>{val}</span></p>")
                else:
                    html_out.append(f"<p style='margin: 4px 0;'>{html.escape(line_s)}</p>")
            else:
                html_out.append(f"<p style='margin: 4px 0;'>{html.escape(line_s)}</p>")
        html_out.append("</div>")
        return "".join(html_out)


class LessonWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, stage_key, topic, scripture, pillar_key, service_key, duration, depth_key, library_root, project_id):
        super().__init__()
        self.stage_key = stage_key
        self.topic = topic
        self.scripture = scripture
        self.pillar_key = pillar_key
        self.service_key = service_key
        self.duration = duration
        self.depth_key = depth_key
        self.library_root = library_root
        self.project_id = project_id

    def run(self):
        try:
            res = sunday_school_builder.generate_sunday_school_lesson(
                stage_key=self.stage_key,
                topic=self.topic,
                scripture=self.scripture,
                pillar_key=self.pillar_key,
                service_key=self.service_key,
                duration=self.duration,
                depth_key=self.depth_key,
                library_root=self.library_root,
                project_id=self.project_id
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class SundaySchoolDialog(QDialog):
    """
    Advanced Ecclesiastical Lesson Workshop Dialog
    ورشة التربية الكنسية الذكية المطورة
    """
    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.setWindowTitle("🎒 ورشة التربية الكنسية الذكية - إعداد دروس مدارس الأحد والمحاضرات المنبرية")
        self.resize(1050, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self.library_root = library_root
        self.project_id = project_id
        self.current_lesson_data = None
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
            QComboBox:focus, QLineEdit:focus { border: 1px solid #10B981; }
            QGroupBox {
                border: 1px solid #334155; border-radius: 8px; margin-top: 10px;
                padding-top: 14px; font-weight: bold; color: #34D399;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; padding: 0 10px; }
            QTextBrowser {
                background-color: #1A1D24; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 8px; padding: 14px; font-size: 14px; line-height: 1.6;
            }
            QTabWidget::pane { border: 1px solid #334155; background: #1A1D24; border-radius: 8px; }
            QTabBar::tab {
                background: #1E222A; color: #94A3B8; padding: 8px 18px; font-weight: bold;
                border-top-left-radius: 6px; border-top-right-radius: 6px; margin-left: 2px;
            }
            QTabBar::tab:selected { background: #059669; color: white; }
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
        h_icon = QLabel("🎒")
        h_icon.setStyleSheet("font-size: 32px; background: transparent;")
        h_lay.addWidget(h_icon)

        v_t = QVBoxLayout()
        lbl_title = QLabel("ورشة التربية الكنسية الذكية - إعداد الدروس والعظات الكنسية")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #34D399; background: transparent;")
        lbl_sub = QLabel("تحضير آبائي متكامل يشمل: الأهداف، التفسير الأرثوذكسي، وسيلة الإيضاح، أسئلة المناقشة، وسيناريو الإلقاء المنبري المباشر.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")
        v_t.addWidget(lbl_title)
        v_t.addWidget(lbl_sub)
        h_lay.addLayout(v_t, 1)
        layout.addWidget(header)

        # 2. Controls & Configuration Box
        ctrl_box = QGroupBox("⚙️ إعدادات الدرس ومحددات الذكاء الكنسي")
        ctrl_lay = QVBoxLayout(ctrl_box)
        ctrl_lay.setSpacing(10)

        # Row 1: Presets + Stage
        row1 = QHBoxLayout()
        lbl_pr = QLabel("قوالب جاهزة:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("⚡ اختر درساً كنسياً جاهزاً أو اكتب فكرتك...", "")
        for item in LESSON_PRESETS:
            self.preset_combo.addItem(f"📖 {item[0]} ({item[1]})", item)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        row1.addWidget(lbl_pr)
        row1.addWidget(self.preset_combo, 1)

        lbl_st = QLabel("المرحلة العمرية:")
        self.stage_combo = QComboBox()
        for k, v in sunday_school_builder.CURRICULUM_STAGES.items():
            self.stage_combo.addItem(v["name"], k)
        self.stage_combo.setCurrentIndex(2)  # primary_late
        row1.addWidget(lbl_st)
        row1.addWidget(self.stage_combo)
        ctrl_lay.addLayout(row1)

        # Row 2: Pillar + Service Type + Duration + Depth
        row2 = QHBoxLayout()
        lbl_pil = QLabel("الركيزة:")
        self.combo_pillar = QComboBox()
        for k, v in sunday_school_builder.ECCLESIASTICAL_PILLARS.items():
            self.combo_pillar.addItem(v, k)
        row2.addWidget(lbl_pil)
        row2.addWidget(self.combo_pillar, 1)

        lbl_srv = QLabel("نوع اللقاء:")
        self.combo_service = QComboBox()
        for k, v in sunday_school_builder.SERVICE_TYPES.items():
            self.combo_service.addItem(v, k)
        row2.addWidget(lbl_srv)
        row2.addWidget(self.combo_service, 1)

        lbl_dur = QLabel("المدة:")
        self.combo_duration = QComboBox()
        for k, v in sunday_school_builder.LESSON_DURATIONS.items():
            self.combo_duration.addItem(v, k)
        self.combo_duration.setCurrentIndex(1)  # 25 mins
        row2.addWidget(lbl_dur)
        row2.addWidget(self.combo_duration)

        lbl_dep = QLabel("العمق:")
        self.combo_depth = QComboBox()
        for k, v in sunday_school_builder.DEPTH_LEVELS.items():
            self.combo_depth.addItem(v, k)
        self.combo_depth.setCurrentIndex(1)  # balanced
        row2.addWidget(lbl_dep)
        row2.addWidget(self.combo_depth)
        ctrl_lay.addLayout(row2)

        # Row 3: Topic + Scripture
        row3 = QHBoxLayout()
        lbl_top = QLabel("موضوع الدرس:")
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("اكتب عنوان الدرس أو الفكرة الروحية (مثال: الأمانة وسر البركة الحقيقية)...")
        row3.addWidget(lbl_top)
        row3.addWidget(self.topic_input, 1)

        lbl_sc = QLabel("الشاهد الكتابي:")
        self.scripture_input = QLineEdit()
        self.scripture_input.setPlaceholderText("مثال: تكوين 39، متى 8: 26 (اختياري)...")
        row3.addWidget(lbl_sc)
        row3.addWidget(self.scripture_input)
        ctrl_lay.addLayout(row3)

        # Generate Button
        self.btn_generate = QPushButton("🚀 صياغة وتحضير الدرس بالذكاء والمراجع الأرثوذكسية وسيناريو الإلقاء")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
                color: white; font-weight: bold; font-size: 13px; padding: 11px;
                border-radius: 6px; border: 1px solid #34D399;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #34D399); }
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
            QProgressBar::chunk { background-color: #10B981; }
        """)
        layout.addWidget(self.progress_bar)

        # 3. Main Output Tabs: Full Plan & Oral Delivery
        self.output_tabs = QTabWidget()

        # Tab 1: Full Plan
        self.browser_full = QTextBrowser()
        self.browser_full.setOpenExternalLinks(True)
        self.browser_full.setPlaceholderText("سيظهر هنا المخطط الكنسي الكامل والشرح الآبائي وتفاصيل وسيلة الإيضاح وأسئلة المناقشة...")
        self.output_tabs.addTab(self.browser_full, "📄 المخطط الكنسي والشرح الآبائي الكامل")

        # Tab 2: Oral Delivery Script
        self.browser_oral = QTextBrowser()
        self.browser_oral.setOpenExternalLinks(True)
        self.browser_oral.setPlaceholderText("سيظهر هنا سيناريو الإلقاء الشفهي المباشر، جاهزاً ليقرأه الخادم بصوته في الاجتماع...")
        self.output_tabs.addTab(self.browser_oral, "🎙️ جاهز للإلقاء المباشر (Oral Delivery Script)")

        layout.addWidget(self.output_tabs, 1)

        # 4. Action Buttons Bar
        act_row = QHBoxLayout()

        self.btn_live_screen = QPushButton("🖥️ شاشة الإلقاء الحي والمؤقت (Presentation Mode)")
        self.btn_live_screen.setEnabled(False)
        self.btn_live_screen.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);
                color: white; font-weight: bold; padding: 10px 18px; border-radius: 6px; font-size: 12px;
                border: 1px solid #3B82F6;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #3B82F6); }
            QPushButton:disabled { background-color: #334155; color: #64748B; border: none; }
        """)
        self.btn_live_screen.clicked.connect(self.open_live_presentation)
        act_row.addWidget(self.btn_live_screen)

        self.btn_export_docx = QPushButton("📄 تصدير ملف Word (.docx)")
        self.btn_export_docx.setEnabled(False)
        self.btn_export_docx.setStyleSheet("""
            QPushButton {
                background-color: #059669; color: white; font-weight: bold;
                padding: 10px 18px; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #10B981; }
            QPushButton:disabled { background-color: #334155; color: #64748B; }
        """)
        self.btn_export_docx.clicked.connect(self.export_docx)
        act_row.addWidget(self.btn_export_docx)

        self.btn_copy = QPushButton("📋 نسخ النص")
        self.btn_copy.setEnabled(False)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: white; font-weight: bold;
                padding: 10px 16px; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
            QPushButton:disabled { color: #64748B; }
        """)
        self.btn_copy.clicked.connect(self.copy_lesson_text)
        act_row.addWidget(self.btn_copy)

        self.btn_open_drama = QPushButton("🎭 تحويل لاسكتش مسرحي")
        self.btn_open_drama.setStyleSheet("""
            QPushButton {
                background-color: #B45309; color: white; font-size: 12px; font-weight: bold;
                padding: 10px 14px; border-radius: 6px; border: 1px solid #D97706;
            }
            QPushButton:hover { background-color: #D97706; }
        """)
        self.btn_open_drama.clicked.connect(self.launch_drama_studio)
        act_row.addWidget(self.btn_open_drama)

        self.btn_open_tutor = QPushButton("🎓 مسابقة سقراطية (DeepTutor)")
        self.btn_open_tutor.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED; color: white; font-size: 12px; font-weight: bold;
                padding: 10px 14px; border-radius: 6px; border: 1px solid #8B5CF6;
            }
            QPushButton:hover { background-color: #8B5CF6; }
        """)
        self.btn_open_tutor.clicked.connect(self.launch_deeptutor)
        act_row.addWidget(self.btn_open_tutor)

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
        data = self.preset_combo.itemData(index)
        if data:
            self.topic_input.setText(data[0])
            self.scripture_input.setText(data[1])
            if len(data) > 2 and data[2]:
                idx_pil = self.combo_pillar.findData(data[2])
                if idx_pil >= 0:
                    self.combo_pillar.setCurrentIndex(idx_pil)
            if len(data) > 3 and data[3]:
                idx_st = self.stage_combo.findData(data[3])
                if idx_st >= 0:
                    self.stage_combo.setCurrentIndex(idx_st)

    def start_generation(self):
        topic = self.topic_input.text().strip()
        if not topic:
            self.show_custom_message("تنبيه", "يرجى كتابة موضوع أو فكرة الدرس أولاً.", is_error=True)
            return

        stage_key = self.stage_combo.currentData()
        pillar_key = self.combo_pillar.currentData()
        service_key = self.combo_service.currentData()
        duration_key = self.combo_duration.currentData()
        depth_key = self.combo_depth.currentData()
        scripture = self.scripture_input.text().strip()

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("⏳ جاري استرجاع المراجع وتأليف الدرس وسيناريو الإلقاء...")
        self.progress_bar.setVisible(True)

        self.worker_thread = QThread()
        self.worker = LessonWorker(
            stage_key=stage_key,
            topic=topic,
            scripture=scripture,
            pillar_key=pillar_key,
            service_key=service_key,
            duration=duration_key,
            depth_key=depth_key,
            library_root=self.library_root,
            project_id=self.project_id
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_generation_finished(self, lesson_data):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 صياغة وتحضير الدرس بالذكاء والمراجع الأرثوذكسية وسيناريو الإلقاء")

        self.current_lesson_data = lesson_data
        full_content = lesson_data.get("content", "")
        oral_script = lesson_data.get("oral_script", "")

        # Render Full Plan
        html_full = self.markdown_to_html(full_content)
        self.browser_full.setHtml(html_full)

        # Render Oral Script
        html_oral = self.markdown_to_oral_html(oral_script or full_content)
        self.browser_oral.setHtml(html_oral)

        # Enable actions
        self.btn_live_screen.setEnabled(True)
        self.btn_export_docx.setEnabled(True)
        self.btn_copy.setEnabled(True)

    def on_generation_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 صياغة وتحضير الدرس بالذكاء والمراجع الأرثوذكسية وسيناريو الإلقاء")
        self.show_custom_message("خطأ في التحضير", f"تعذر إتمام التحضير الكنسي:\n{err_msg}", is_error=True)

    def markdown_to_html(self, md_text):
        import html
        lines = md_text.splitlines()
        html_out = ["<div style='direction: rtl; text-align: right; font-family: Cairo, Segoe UI, sans-serif; color: #E2E8F0; line-height: 1.8;'>"]

        for line in lines:
            line_s = line.strip()
            if not line_s:
                html_out.append("<div style='height: 8px;'></div>")
                continue
            if line_s.startswith("# "):
                h = html.escape(line_s.replace("# ", ""))
                html_out.append(f"<h1 style='color: #FBBF24; font-size: 20px; border-bottom: 1px solid #D97706; padding-bottom: 6px; margin-top: 14px;'>{h}</h1>")
            elif line_s.startswith("### ") or line_s.startswith("## "):
                h = html.escape(re.sub(r"^#+\s*", "", line_s))
                html_out.append(f"<h2 style='color: #38BDF8; font-size: 15px; margin-top: 16px; margin-bottom: 6px; font-weight: bold;'>📌 {h}</h2>")
            elif line_s.startswith("- **") or line_s.startswith("* **"):
                parts = line_s.split("**")
                if len(parts) >= 3:
                    lbl = html.escape(parts[1])
                    val = html.escape("".join(parts[2:]).lstrip(": "))
                    html_out.append(f"<p style='margin: 4px 0;'><b style='color: #FCD34D;'>• {lbl}:</b> <span style='color: #F1F5F9;'>{val}</span></p>")
                else:
                    html_out.append(f"<p style='margin: 4px 0; color: #CBD5E1;'>{html.escape(line_s)}</p>")
            elif line_s.startswith("«") and "»" in line_s:
                html_out.append(f"<div style='margin: 8px 0; padding: 8px 12px; background-color: #1E232D; border-right: 4px solid #D97706; border-radius: 4px; font-weight: bold; color: #FDE68A; font-size: 15px;'>{html.escape(line_s)}</div>")
            else:
                html_out.append(f"<p style='margin: 4px 0; color: #CBD5E1;'>{html.escape(line_s)}</p>")

        html_out.append("</div>")
        return "".join(html_out)

    def markdown_to_oral_html(self, oral_text):
        import html
        escaped = html.escape(oral_text).replace("\n\n", "</p><p style='margin-bottom: 12px;'>").replace("\n", "<br/>")
        return f"""
        <div style="direction: rtl; text-align: right; font-family: Cairo, Segoe UI, sans-serif; font-size: 16px; line-height: 2.0; color: #F8FAFC; padding: 10px;">
            <div style="background-color: #197D80; color: white; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: bold; margin-bottom: 18px;">
                🎙️ سيناريو الإلقاء المنبري المباشر — اقرأ بثقة ومحبة أمام المخدومين:
            </div>
            <p style="margin-bottom: 12px;">{escaped}</p>
        </div>
        """

    def open_live_presentation(self):
        if not self.current_lesson_data:
            return
        dlg = OratoricalPresentationDialog(
            parent=self,
            title=self.current_lesson_data.get("topic", "الدرس"),
            oral_script=self.current_lesson_data.get("oral_script", ""),
            full_content=self.current_lesson_data.get("content", ""),
            duration_minutes=self.current_lesson_data.get("duration", 25)
        )
        dlg.exec_()

    def export_docx(self):
        if not self.current_lesson_data:
            return

        topic = self.current_lesson_data.get("topic", "درس_كنسي")
        clean_name = re.sub(r'[\\/*?:"<>|]', "_", topic)[:35]
        default_file = f"تحضير_{clean_name}.docx"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير التحضير الكنسي إلى ملف Word",
            default_file,
            "مستندات Word (*.docx)"
        )

        if not save_path:
            return

        try:
            sunday_school_builder.export_lesson_to_docx(self.current_lesson_data, save_path)
            self.show_custom_message(
                "تم التصدير بنجاح",
                f"تم حفظ التحضير الكنسي المنسق في:\n{save_path}\n\nجاهز للطباعة والمشاركة الفورية!"
            )
            try:
                os.startfile(save_path)
            except Exception:
                pass
        except Exception as e:
            self.show_custom_message("خطأ في التصدير", f"تعذر حفظ ملف Word:\n{e}", is_error=True)

    def copy_lesson_text(self):
        if not self.current_lesson_data:
            return
        clipboard = QApplication.clipboard()
        # If oral tab is active, copy oral script; otherwise copy full plan
        if self.output_tabs.currentIndex() == 1 and self.current_lesson_data.get("oral_script"):
            clipboard.setText(self.current_lesson_data.get("oral_script", ""))
            self.show_custom_message("تم النسخ", "تم نسخ سيناريو الإلقاء الشفهي المباشر إلى الحافظة! 🎙️")
        else:
            clipboard.setText(self.current_lesson_data.get("content", ""))
            self.show_custom_message("تم النسخ", "تم نسخ نص الدرس بالكامل إلى الحافظة بنجاح! 📋")

    def launch_drama_studio(self):
        topic = self.topic_input.text().strip() or (self.current_lesson_data.get("topic", "") if self.current_lesson_data else "")
        from modules.church_drama_studio import ChurchDramaStudioDialog
        dlg = ChurchDramaStudioDialog(self, library_root=self.library_root, project_id=self.project_id, initial_topic=topic)
        dlg.exec_()

    def launch_deeptutor(self):
        topic = self.topic_input.text().strip() or (self.current_lesson_data.get("topic", "") if self.current_lesson_data else "")
        from modules.deeptutor_engine import DeepTutorDialog
        dlg = DeepTutorDialog(self, initial_topic=topic)
        dlg.exec_()

    def show_custom_message(self, title, message, is_error=False):
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1E232D; color: white; font-family: Cairo, Segoe UI; }
            QLabel { color: white; font-size: 13px; }
            QPushButton { background-color: #059669; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold; }
        """)
        msg.exec_()
