"""
Cross Coptic Library - Coptic Apologetics Hub & Smart Topic Archive
منصة حصن الإيمان، استوديو تفنيد الشبهات، ومحرك الأرشيف التراكمي الموفر للتوكنز
Connects directly to the user's local library, patristic heritage, Dr. Ghaly's Encyclopedia,
St-Takla.org, neutral science & secular historians database, and local differential disk archive.
"""

import os
import re
import datetime
import subprocess
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QProgressBar,
    QFileDialog,
    QApplication,
    QMessageBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

from modules import ai_handler, library_rag, apologetics_db, web_intelligence, neutral_science_db, topic_archive, presentation_generator, audio_briefing, topic_visualizers, manuscript_comparator

APOLOGETICS_PROMPT_TEMPLATE = """
أنت عالم لاهوت وباحث دفاعي قبطي أرثوذكسي متبحر.
مطلوب منك صياغة رد لاهوتي دفاعي وعقلي وتاريخي متكامل ومفحم على الشبهة أو التساؤل التالي:

🎯 موضوع البحث والدفاع:
- القسم: {category}
- نص التساؤل / الشبهة: {question}

📚 مقتطفات مراجع مسترجعة من مكتبة الكنيسة المحلية:
{rag_context}

🌐 أبحاث دفاعية ونقدية مسترجعة حياً من موسوعة د. غالي (Holy_Bible_1) وموقع تكلا والويب:
{ghaly_context}

🔬 بنك أدلة العلم والآثار والمؤرخين غير المسيحيين المحايدين:
{neutral_science_context}

⚖️ الهيكل الإلزامي للرد الدفاعي الأرثوذكسي (الـ 6 أركان الكاملة):
### 1. صلب الشبهة ومنشؤها وخلفيتها التاريخية (The Core Objection & Its Context)
(بيان الفكرة المشككة بإنصاف ودقة لتفكيك منطلقاتها الفلسفية أو التاريخية المغلوطة).

### 2. رأي العلم والمؤرخين والآثار المحايدة (شهادات غير المسيحيين والمتاحف العالمية)
(عنصر إلزامي ومحوري: تفنيد الشبهة حصراً بأقوال وبحوث العلماء والباحثين غير المسيحيين، والمؤرخين الرومان واليهود القدامى مثل تاسيتوس ويوسيفوس وبليني، ومقتنيات المتاحف العالمية كالمتحف البريطاني واللوفر، وقوانين الفيزياء الفلكية والبيولوجيا التي تشهد وتؤكد صحة الموقف الكتابي والتاريخي بحيادية تامة).

### 3. التحقيق الكتابي والشواهد التفسيرية (Biblical & Exegetical Proofs)
(شواهد دقيقة مع الرد على أي تحريف أو اجتزاء للنصوص من سياقها الصحيح).

### 4. البرهان العقلي والمنطقي والفلسفي (Logical & Philosophical Refutation)
(تفنيد الشبهة بالعقل المجرد والبراهين المنطقية المعاصرة مع الاستفادة من براهين د. غالي العلمية والنصية بلغة تناسب شباب اليوم).

### 5. إجماع آباء الكنيسة وسياق التقليد الأرثوذكسي (Patristic Consensus & Holy Tradition)
(أقوال الآباء القديسين: أثناسيوس، كيرلس الكبير، ذهبي الفم، أغسطينوس، باسيليوس مع ذكر أسماء كتاباتهم).

### 6. مراجع وأبحاث للتعمق والبحث
(مراجع من مكتبة الصليب القبطية، أبحاث د. غالي، موقع تكلا، والأوراق العلمية والمتاحف للرجوع والتوثيق).
"""

class ApologeticsWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, category, question, library_root, project_id, include_ghaly_web=True, check_archive_first=True, force_refresh=False):
        super().__init__()
        self.category = category
        self.question = question
        self.library_root = library_root
        self.project_id = project_id
        self.include_ghaly_web = include_ghaly_web
        self.check_archive_first = check_archive_first
        self.force_refresh = force_refresh

    def run(self):
        try:
            # 0. Check local topic archive first (Token Saving Engine)
            if self.check_archive_first and not self.force_refresh:
                found, manifest, folder_path = topic_archive.find_archived_topic(self.question, self.library_root)
                if found and manifest.get("full_treatise_text"):
                    topic_archive.record_token_saving(folder_path)
                    docx_file = os.path.join(folder_path, manifest.get("treatise_file", ""))
                    self.finished.emit({
                        "category": manifest.get("category", self.category),
                        "question": manifest.get("topic", self.question),
                        "content": manifest.get("full_treatise_text", ""),
                        "ghaly_sources": manifest.get("sources", []),
                        "neutral_sources": [],
                        "from_archive": True,
                        "folder_path": folder_path,
                        "docx_path": docx_file if os.path.exists(docx_file) else "",
                        "last_updated": manifest.get("last_updated", ""),
                        "created_at": manifest.get("created_at", ""),
                        "tokens_saved": manifest.get("tokens_saved_estimate", 3500)
                    })
                    return

            # 1. Search RAG context in local church library
            rag_context = ""
            try:
                search_query = f"{self.question} لاهوت دفاعي عقيدة"
                has_sources, context_text, source_books = library_rag.extract_relevant_snippets(
                    search_query,
                    library_root=self.library_root,
                    project_id=self.project_id,
                    max_total_chars=3500
                )
                if has_sources and context_text:
                    rag_context = context_text
            except Exception as ex:
                print(f"Apologetics Local RAG error: {ex}")

            if not rag_context:
                rag_context = "مستند إلى التراث الدفاعي القبطي الأرثوذكسي وأمهات كتب الدفاعيات."

            # 2. Search Dr. Ghaly's Encyclopedia & St-Takla Web RAG if enabled
            ghaly_context = ""
            combined_sources = []
            if self.include_ghaly_web:
                try:
                    has_ghaly, g_ctx, g_srcs = web_intelligence.DrGhalyEngine.search_and_get_top_context(
                        self.question,
                        max_articles=2,
                        max_chars_per_article=2000
                    )
                    if has_ghaly and g_ctx:
                        ghaly_context += g_ctx + "\n"
                        combined_sources.extend(g_srcs)
                except Exception as ex_ghaly:
                    print(f"DrGhaly RAG error: {ex_ghaly}")

                try:
                    has_takla, t_ctx, t_srcs = web_intelligence.StTaklaEngine.search_and_get_top_context(
                        self.question,
                        max_articles=1,
                        max_chars_per_article=1500
                    )
                    if has_takla and t_ctx:
                        ghaly_context += "\n" + t_ctx
                        combined_sources.extend(t_srcs)
                except Exception as ex_takla:
                    print(f"StTakla RAG error: {ex_takla}")

            if not ghaly_context:
                ghaly_context = "الاعتماد على الأصول الكنسية والآبائية وموسوعة الكنيسة القبطية."

            # 3. Retrieve Neutral Science & Secular Historians Evidence
            neutral_evidence_context = ""
            neutral_sources = []
            try:
                neutral_sources = neutral_science_db.search_neutral_evidence(self.question, max_results=3)
                neutral_evidence_context = neutral_science_db.format_neutral_evidence_for_prompt(neutral_sources)
            except Exception as ex_ns:
                print(f"Neutral Science DB error: {ex_ns}")

            if not neutral_evidence_context:
                neutral_evidence_context = "استند إلى أحدث البراهين الأثرية والعلمية المحايدة والمؤرخين غير المسيحيين كـ تاسيتوس ويوسيفوس والمتاحف العالمية."

            # 4. Craft Prompt
            prompt = APOLOGETICS_PROMPT_TEMPLATE.format(
                category=self.category,
                question=self.question,
                rag_context=rag_context,
                ghaly_context=ghaly_context,
                neutral_science_context=neutral_evidence_context
            )

            # 5. Request from AI
            system_instruction = "أنت مدافع لاهوتي قبطي أرثوذكسي تستند إلى الكتاب المقدس وأقوال الآباء والعلم والآثار المحايدة والمنطق العقلي الرصين."
            response = ai_handler.call_ai_routed(prompt, system_instruction=system_instruction)

            # 6. Save newly researched topic into disk archive and index it
            saved_folder, saved_docx = "", ""
            try:
                saved_folder, saved_docx = topic_archive.save_researched_topic(
                    topic=self.question,
                    category=self.category,
                    treatise_content=response,
                    sources=combined_sources,
                    library_root=self.library_root,
                    project_id=self.project_id
                )
            except Exception as ex_arch:
                print(f"Topic archive saving warning: {ex_arch}")

            self.finished.emit({
                "category": self.category,
                "question": self.question,
                "content": response,
                "ghaly_sources": combined_sources,
                "neutral_sources": neutral_sources,
                "from_archive": False,
                "folder_path": saved_folder,
                "docx_path": saved_docx,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        except Exception as e:
            self.error.emit(str(e))

class TopicUpdateWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, folder_path, topic_name, library_root=None):
        super().__init__()
        self.folder_path = folder_path
        self.topic_name = topic_name
        self.library_root = library_root

    def run(self):
        try:
            # Query online for newest articles
            online_articles = []
            try:
                g_arts = web_intelligence.DrGhalyEngine.search_articles(self.topic_name, limit=4)
                for a in g_arts:
                    online_articles.append({
                        "id": f"ghaly_{a['id']}",
                        "title": a["title"],
                        "url": a["url"],
                        "snippet": a["title"]
                    })
            except Exception as e:
                print(f"DrGhaly update check error: {e}")

            try:
                t_arts = web_intelligence.StTaklaEngine.search_articles(self.topic_name, limit=3)
                for a in t_arts:
                    online_articles.append({
                        "id": a["id"],
                        "title": a["title"],
                        "url": a["url"],
                        "snippet": a.get("snippet", a["title"])
                    })
            except Exception as e:
                print(f"StTakla update check error: {e}")

            has_updates, msg, updated_text = topic_archive.check_and_update_topic(
                self.folder_path,
                online_articles,
                library_root=self.library_root
            )

            self.finished.emit({
                "has_updates": has_updates,
                "message": msg,
                "updated_text": updated_text,
                "folder_path": self.folder_path
            })
        except Exception as e:
            self.error.emit(str(e))

class GhalySettlerWorker(QObject):
    progress = pyqtSignal(int, int, str, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query, output_dir=None, max_articles=15, project_id=1):
        super().__init__()
        self.query = query
        self.output_dir = output_dir
        self.max_articles = max_articles
        self.project_id = project_id

    def run(self):
        try:
            def cb(idx, total, title, fpath):
                self.progress.emit(idx, total, title, fpath)

            saved = web_intelligence.OfflineLibrarySettler.settle_ghaly_research(
                query=self.query,
                output_dir=self.output_dir,
                max_articles=self.max_articles,
                progress_callback=cb,
                project_id=self.project_id
            )
            self.finished.emit(saved)
        except Exception as e:
            self.error.emit(str(e))

class ApologeticsHubWidget(QWidget):
    """
    الاستوديو الدفاعي الكامل - مدمج داخل شاشة المساعد الكنسي أو كأداة مستقلة.
    """
    topicArchived = pyqtSignal(str)

    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.library_root = library_root
        self.project_id = project_id
        self.current_treatise = None
        self.worker_thread = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header Info Banner
        header_box = QWidget()
        h_layout = QHBoxLayout(header_box)
        h_layout.setContentsMargins(0, 0, 0, 0)

        t_lbl = QLabel("🛡️ استوديو تفنيد الشبهات والأبحاث الأرثوذكسية (حصن الإيمان)")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        d_lbl = QLabel("صياغة أبحاث موثقة بالـ 6 أركان، العلم المحايد، موسوعة د. غالي، والتسكين التلقائي في الأرشيف")
        d_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")

        v_head = QVBoxLayout()
        v_head.addWidget(t_lbl)
        v_head.addWidget(d_lbl)
        h_layout.addLayout(v_head, 1)

        self.btn_neutral_bank = QPushButton("🔬 بنك أدلة العلم والمؤرخين المحايدين")
        self.btn_neutral_bank.setStyleSheet("background-color: #065F46; color: #A7F3D0; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #10B981;")
        self.btn_neutral_bank.clicked.connect(self.show_neutral_science_bank)
        h_layout.addWidget(self.btn_neutral_bank)

        layout.addWidget(header_box)

        # Splitter: Left (Questions index) / Right (Active research)
        splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel: Index ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        left_box = QGroupBox("📚 فهرس الشبهات والتساؤلات الشائعة")
        left_box.setStyleSheet("QGroupBox { border: 1px solid #334155; border-radius: 6px; margin-top: 6px; font-weight: bold; color: #93C5FD; padding-top: 10px; }")
        b_layout = QVBoxLayout(left_box)

        b_layout.addWidget(QLabel("تصنيف الشبهات:"))
        self.cat_filter_combo = QComboBox()
        self.cat_filter_combo.addItem("🌐 جميع التصنيفات الدفاعية", "")
        for cat in apologetics_db.get_all_categories():
            self.cat_filter_combo.addItem(cat, cat)
        self.cat_filter_combo.currentIndexChanged.connect(self.filter_topics)
        b_layout.addWidget(self.cat_filter_combo)

        b_layout.addWidget(QLabel("بحث سريع:"))
        self.search_filter_input = QLineEdit()
        self.search_filter_input.setPlaceholderText("ابحث في الشبهات...")
        self.search_filter_input.textChanged.connect(self.filter_topics)
        b_layout.addWidget(self.search_filter_input)

        self.topic_list = QListWidget()
        self.topic_list.setStyleSheet("""
            QListWidget {
                background-color: #1E222A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2D323B;
            }
            QListWidget::item:selected {
                background-color: #1D4ED8;
                color: #FFFFFF;
                border-radius: 4px;
            }
        """)
        self.topic_list.itemClicked.connect(self.on_topic_clicked)
        b_layout.addWidget(self.topic_list, 1)

        left_layout.addWidget(left_box)
        splitter.addWidget(left_panel)

        # --- Right Panel: Action & Output ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Active Question & Options Box
        q_box = QGroupBox("🎯 صياغة وتوثيق البحث الدفاعي")
        q_box.setStyleSheet("QGroupBox { border: 1px solid #3B82F6; border-radius: 6px; margin-top: 6px; font-weight: bold; color: #60A5FA; padding-top: 10px; }")
        q_box_layout = QVBoxLayout(q_box)

        self.active_q_label = QLabel("اختر سؤالاً من الفهرس أو اكتب تساؤلك أدناه:")
        self.active_q_label.setWordWrap(True)
        self.active_q_label.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold;")
        q_box_layout.addWidget(self.active_q_label)

        self.custom_q_input = QLineEdit()
        self.custom_q_input.setPlaceholderText("أو اكتب أي شبهة / تساؤل خاص للرد عليه بالـ 6 أركان...")
        self.custom_q_input.setStyleSheet("background-color: #1E222A; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 7px 12px;")
        q_box_layout.addWidget(self.custom_q_input)

        opts_row = QHBoxLayout()
        self.chk_check_archive = QCheckBox("🗄️ التحقق من الأرشيف المحلي أولاً (توفير التوكنز 0 Tokens)")
        self.chk_check_archive.setChecked(True)
        self.chk_check_archive.setStyleSheet("color: #10B981; font-weight: bold;")
        opts_row.addWidget(self.chk_check_archive)

        self.chk_include_ghaly = QCheckBox("🌐 دمج أبحاث د. غالي وموقع تكلا حياً")
        self.chk_include_ghaly.setChecked(True)
        self.chk_include_ghaly.setStyleSheet("color: #38BDF8; font-weight: bold;")
        opts_row.addWidget(self.chk_include_ghaly)
        opts_row.addStretch()
        q_box_layout.addLayout(opts_row)

        btn_action_row = QHBoxLayout()
        self.btn_generate = QPushButton("🚀 صياغة وتفنيد البحث الدفاعي بالـ 6 أركان")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2563EB; }
            QPushButton:disabled { background-color: #374151; color: #9CA3AF; }
        """)
        self.btn_generate.clicked.connect(self.start_generation)
        btn_action_row.addWidget(self.btn_generate, 2)

        self.btn_force_refresh = QPushButton("🔄 إعادة التوليد والفحص الشامل (تجاوز الأرشيف)")
        self.btn_force_refresh.setStyleSheet("background-color: #334155; color: #E2E8F0; font-size: 12px; font-weight: bold; padding: 8px 12px; border-radius: 6px;")
        self.btn_force_refresh.clicked.connect(lambda: self.start_generation(force_refresh=True))
        btn_action_row.addWidget(self.btn_force_refresh, 1)

        q_box_layout.addLayout(btn_action_row)

        # Archive Alert Banner
        self.archive_alert_banner = QWidget()
        self.archive_alert_banner.setVisible(False)
        self.archive_alert_banner.setStyleSheet("background-color: #064E3B; border: 1px solid #10B981; border-radius: 6px; padding: 6px 10px;")
        alert_layout = QHBoxLayout(self.archive_alert_banner)
        alert_layout.setContentsMargins(6, 4, 6, 4)
        self.archive_alert_lbl = QLabel("📌 مسترجع من الأرشيف المحلي (0 توكن مستهلكة)")
        self.archive_alert_lbl.setStyleSheet("color: #D1FAE5; font-weight: bold; font-size: 12px;")
        alert_layout.addWidget(self.archive_alert_lbl, 1)

        self.btn_diff_update = QPushButton("🔄 فحص المراجع الجديدة فقط (تحديث تفاضلي)")
        self.btn_diff_update.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_diff_update.clicked.connect(self.trigger_differential_update)
        alert_layout.addWidget(self.btn_diff_update)

        self.btn_open_folder = QPushButton("📂 فتح مجلد الأرشيف")
        self.btn_open_folder.setStyleSheet("background-color: #1E293B; color: #CBD5E1; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        self.btn_open_folder.clicked.connect(self.open_current_folder)
        alert_layout.addWidget(self.btn_open_folder)

        q_box_layout.addWidget(self.archive_alert_banner)
        right_layout.addWidget(q_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid #334155; border-radius: 4px; height: 12px; background-color: #1E222A; } QProgressBar::chunk { background-color: #38BDF8; }")
        right_layout.addWidget(self.progress_bar)

        # Treatise text display
        self.treatise_display = QTextEdit()
        self.treatise_display.setReadOnly(True)
        self.treatise_display.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 14px;
                font-size: 13px;
                line-height: 1.7;
            }
        """)
        right_layout.addWidget(self.treatise_display, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Bottom Bar Actions (All 6 Enhancements Included)
        foot_layout = QHBoxLayout()
        
        self.btn_export_docx = QPushButton("📄 ملف Word (.docx)")
        self.btn_export_docx.setEnabled(False)
        self.btn_export_docx.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_export_docx.clicked.connect(self.export_docx)
        foot_layout.addWidget(self.btn_export_docx)

        self.btn_export_pptx = QPushButton("📊 عرض PowerPoint (.pptx)")
        self.btn_export_pptx.setEnabled(False)
        self.btn_export_pptx.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_export_pptx.clicked.connect(self.generate_pptx_slides)
        foot_layout.addWidget(self.btn_export_pptx)

        self.btn_audio = QPushButton("🎧 الموجز الصوتي (.mp3)")
        self.btn_audio.setEnabled(False)
        self.btn_audio.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_audio.clicked.connect(self.generate_audio_briefing_action)
        foot_layout.addWidget(self.btn_audio)

        self.btn_matrix = QPushButton("📋 مصفوفة الردود السريعة")
        self.btn_matrix.setEnabled(False)
        self.btn_matrix.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_matrix.clicked.connect(self.show_debate_matrix)
        foot_layout.addWidget(self.btn_matrix)

        self.btn_mindmap = QPushButton("🧠 الخريطة الذهنية")
        self.btn_mindmap.setEnabled(False)
        self.btn_mindmap.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_mindmap.clicked.connect(self.show_mind_map)
        foot_layout.addWidget(self.btn_mindmap)

        self.btn_manuscript = QPushButton("📜 مقارن المخطوطات")
        self.btn_manuscript.setStyleSheet("background-color: #0D9488; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_manuscript.clicked.connect(self.show_manuscript_comparator)
        foot_layout.addWidget(self.btn_manuscript)

        self.btn_copy = QPushButton("📋 نسخ النص")
        self.btn_copy.setEnabled(False)
        self.btn_copy.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 7px 12px; border-radius: 5px;")
        self.btn_copy.clicked.connect(self.copy_treatise_text)
        foot_layout.addWidget(self.btn_copy)

        foot_layout.addStretch()
        layout.addLayout(foot_layout)

        self.populate_topics()

    def populate_topics(self):
        self.topic_list.clear()
        selected_cat = self.cat_filter_combo.currentData()
        query = self.search_filter_input.text().strip().lower()

        for item in apologetics_db.APOLOGETICS_TOPICS:
            cat = item["category"]
            q = item["question"]

            if selected_cat and cat != selected_cat:
                continue

            if query:
                match = query in q.lower() or query in item.get("summary", "").lower()
                if not match and any(query in kw.lower() for kw in item.get("keywords", [])):
                    match = True
                if not match:
                    continue

            list_item = QListWidgetItem(f"🛡️ {q}")
            list_item.setData(Qt.UserRole, item)
            self.topic_list.addItem(list_item)

        if self.topic_list.count() > 0:
            self.topic_list.setCurrentRow(0)
            self.on_topic_clicked(self.topic_list.item(0))

    def filter_topics(self):
        self.populate_topics()

    def on_topic_clicked(self, item):
        if not item:
            return
        data = item.data(Qt.UserRole)
        self.active_q_label.setText(f"📌 {data['question']}")
        self.custom_q_input.setText("")
        self.archive_alert_banner.setVisible(False)

        # Quick check if already archived locally to show notification immediately!
        found, manifest, f_path = topic_archive.find_archived_topic(data["question"], self.library_root)
        if found:
            self.archive_alert_lbl.setText(f"📌 تم العثور على بحث كامل محفوظ مسبقاً في أرشيفك المحلي (تاريخ: {manifest.get('last_updated', '')}) - جاهز بـ 0 توكنز!")
            self.archive_alert_banner.setVisible(True)
            self.current_folder_path = f_path
            self.current_docx_path = os.path.join(f_path, manifest.get("treatise_file", ""))
        else:
            self.current_folder_path = None
            self.current_docx_path = None

        initial_html = [
            f"<div style='font-family: Segoe UI, Tahoma; color: #E2E8F0; line-height: 1.8;'>",
            f"<h2 style='color: #E5C07B; border-bottom: 2px solid #E5C07B; padding-bottom: 6px;'>{data['question']}</h2>",
            f"<p style='color: #38BDF8; font-weight: bold;'>القسم الدفاعي: {data['category']}</p>",
            f"<div style='background-color: #1E222A; border-right: 4px solid #38BDF8; padding: 12px; margin: 10px 0;'>",
            f"<strong>💡 خلاصة المفهوم الأرثوذكسي:</strong><br>{data['summary']}",
            f"</div>",
            f"<h3 style='color: #60A5FA; margin-top: 14px;'>📚 المراجع الأساسية المعتمدة:</h3><ul>"
        ]
        for ref in data.get("core_references", []):
            initial_html.append(f"<li>{ref}</li>")
        initial_html.append("</ul>")

        initial_html.append(f"<h3 style='color: #34D399; margin-top: 14px;'>🏛️ كتب موصى بها من مكتبتك القبطية:</h3><ul>")
        for en in data.get("suggested_library_enrichment", []):
            initial_html.append(f"<li>{en}</li>")
        initial_html.append("</ul>")

        if found:
            initial_html.append("<div style='text-align: center; margin-top: 20px; color: #34D399; font-weight: bold;'>💡 اضغط «صياغة وتفنيد البحث» لعرض البحث المحفوظ فوراً من الأرشيف دون استهلاك أي نقاط.</div>")
        else:
            initial_html.append("<div style='text-align: center; margin-top: 20px; color: #94A3B8;'>اضغط <strong>«صياغة وتفنيد البحث الدفاعي»</strong> لتوليد دراسة موثقة من 6 أركان وتسكينها في أرشيفك الدائم.</div>")

        initial_html.append("</div>")
        self.treatise_display.setHtml("".join(initial_html))

    def start_generation(self, force_refresh=False):
        custom_q = self.custom_q_input.text().strip()
        current_item = self.topic_list.currentItem()

        if custom_q:
            question = custom_q
            category = "تساؤل دفاعي مخصص"
        elif current_item:
            data = current_item.data(Qt.UserRole)
            question = data["question"]
            category = data["category"]
        else:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار شبهة من الفهرس أو كتابة تساؤل خاص أولاً.")
            return

        self.btn_generate.setEnabled(False)
        self.btn_force_refresh.setEnabled(False)
        self.progress_bar.setVisible(True)

        include_ghaly = self.chk_include_ghaly.isChecked()
        check_archive = self.chk_check_archive.isChecked()

        self.treatise_display.setHtml("<div style='color: #38BDF8; font-weight: bold; text-align: center; padding: 25px;'>⏳ جاري فحص الأرشيف واسترجاع المراجع وتفنيد الشبهة بالـ 6 أركان...</div>")

        self.worker_thread = QThread()
        self.worker = ApologeticsWorker(
            category=category,
            question=question,
            library_root=self.library_root,
            project_id=self.project_id,
            include_ghaly_web=include_ghaly,
            check_archive_first=check_archive,
            force_refresh=force_refresh
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_generation_finished(self, data):
        self.btn_generate.setEnabled(True)
        self.btn_force_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_treatise = data
        self.btn_export_docx.setEnabled(True)
        self.btn_export_pptx.setEnabled(True)
        self.btn_audio.setEnabled(True)
        self.btn_matrix.setEnabled(True)
        self.btn_mindmap.setEnabled(True)
        self.btn_copy.setEnabled(True)

        self.current_folder_path = data.get("folder_path")
        self.current_docx_path = data.get("docx_path")

        from_archive = data.get("from_archive", False)
        if from_archive:
            self.archive_alert_lbl.setText(f"📌 تم استرجاع البحث فوراً من الأرشيف المحلي (تاريخ: {data.get('last_updated', '')}) - تم توفير ~3500 توكن! (0 Tokens)")
            self.archive_alert_banner.setVisible(True)
        else:
            self.archive_alert_lbl.setText(f"💾 تم حفظ وتسكين البحث بنجاح في أرشيف مكتبتك الدائم!")
            self.archive_alert_banner.setVisible(True)
            self.topicArchived.emit(data["question"])

        content = data.get("content", "")
        ghaly_sources = data.get("ghaly_sources", [])
        formatted_html = self.markdown_to_html(data["question"], content, ghaly_sources=ghaly_sources)
        self.treatise_display.setHtml(formatted_html)

    def on_generation_error(self, err_msg):
        self.btn_generate.setEnabled(True)
        self.btn_force_refresh.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.treatise_display.setPlainText(f"❌ حدث خطأ أثناء التوليد: {err_msg}")

    def trigger_differential_update(self):
        if not hasattr(self, "current_folder_path") or not self.current_folder_path or not os.path.exists(self.current_folder_path):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد أو حفظ الموضوع أولاً.")
            return

        topic_q = self.current_treatise.get("question", "") if self.current_treatise else self.active_q_label.text().replace("📌 ", "")
        self.progress_bar.setVisible(True)
        self.btn_diff_update.setEnabled(False)

        self.update_thread = QThread()
        self.update_worker = TopicUpdateWorker(
            folder_path=self.current_folder_path,
            topic_name=topic_q,
            library_root=self.library_root
        )
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self.on_diff_update_finished)
        self.update_worker.error.connect(self.on_diff_update_error)

        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_worker.error.connect(self.update_thread.quit)
        self.update_worker.error.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)

        self.update_thread.start()

    def on_diff_update_finished(self, res):
        self.progress_bar.setVisible(False)
        self.btn_diff_update.setEnabled(True)
        msg = res.get("message", "")
        updated_text = res.get("updated_text", "")
        if res.get("has_updates", False) and updated_text:
            if self.current_treatise:
                self.current_treatise["content"] = updated_text
            self.treatise_display.setHtml(self.markdown_to_html(self.current_treatise.get("question", "بحث محدث"), updated_text))
            QMessageBox.information(self, "تحديث الأرشيف", msg)
        else:
            QMessageBox.information(self, "فحص الأرشيف", msg)

    def on_diff_update_error(self, err):
        self.progress_bar.setVisible(False)
        self.btn_diff_update.setEnabled(True)
        QMessageBox.warning(self, "خطأ في التحديث", f"تعذر استكمال الفحص التفاضلي: {err}")

    def open_current_folder(self):
        if hasattr(self, "current_folder_path") and self.current_folder_path and os.path.exists(self.current_folder_path):
            try:
                os.startfile(self.current_folder_path)
            except Exception as ex:
                QMessageBox.warning(self, "تنبيه", f"تعذر فتح المجلد: {ex}")

    def show_neutral_science_bank(self):
        from modules.neutral_science_db import NeutralScienceViewerDialog
        dialog = NeutralScienceViewerDialog(self)
        dialog.exec_()

    def set_question(self, q_text):
        """Sets a question from external caller (e.g. Church Assistant tab) and triggers generation."""
        self.custom_q_input.setText(q_text)
        self.active_q_label.setText(f"📌 {q_text}")
        self.start_generation()

    def markdown_to_html(self, question, text, ghaly_sources=None):
        lines = text.splitlines()
        html = [
            f"<div style='font-family: Segoe UI, Tahoma; line-height: 1.8; color: #E2E8F0;'>",
            f"<h2 style='color: #E5C07B; border-bottom: 2px solid #E5C07B; padding-bottom: 6px; margin-bottom: 14px;'>🛡️ {question}</h2>"
        ]
        for line in lines:
            line = line.strip()
            if not line:
                html.append("<br>")
                continue
            if line.startswith("### "):
                title = line[4:].strip()
                if "العلم" in title or "المحايد" in title or "الآثار" in title:
                    html.append(f"<div style='background-color: #064E3B; border-right: 4px solid #10B981; padding: 10px 14px; margin-top: 18px; border-radius: 4px;'><h3 style='color: #A7F3D0; margin: 0;'>🔬 {title}</h3></div>")
                elif "ملحق التحديثات" in title:
                    html.append(f"<div style='background-color: #1E3A8A; border-right: 4px solid #38BDF8; padding: 10px 14px; margin-top: 18px; border-radius: 4px;'><h3 style='color: #BAE6FD; margin: 0;'>🔄 {title}</h3></div>")
                else:
                    html.append(f"<h3 style='color: #38BDF8; border-bottom: 1px solid #334155; padding-bottom: 4px; margin-top: 14px;'>{title}</h3>")
            elif line.startswith("## "):
                title = line[3:].strip()
                html.append(f"<h2 style='color: #60A5FA; border-bottom: 1px solid #3B82F6; padding-bottom: 4px; margin-top: 16px;'>{title}</h2>")
            elif line.startswith("- ") or line.startswith("* "):
                bullet = line[2:].strip()
                html.append(f"<div style='margin-right: 15px;'>🔹 {bullet}</div>")
            elif line.startswith("═") or line.startswith("─"):
                html.append("<hr style='border: 0; border-top: 1px solid #334155; margin: 15px 0;'>")
            else:
                html.append(f"<p style='margin: 4px 0;'>{line}</p>")

        if ghaly_sources:
            html.append("<div style='margin-top: 24px; padding: 14px; background-color: #101217; border: 1px solid #2D323B; border-radius: 8px;'>")
            html.append("<h4 style='color: #E5C07B; margin: 0 0 8px 0;'>🌐 أبحاث ومراجع موثقة مرتبطة:</h4>")
            html.append("<ul style='margin: 0; padding-right: 20px;'>")
            for s in ghaly_sources:
                html.append(f"<li style='margin-bottom: 6px;'><a href='{s.get('url', '#')}' style='color: #38BDF8; text-decoration: none;'>{s.get('title', 'مرجع')}</a></li>")
            html.append("</ul></div>")

        html.append("</div>")
        return "".join(html)

    def generate_pptx_slides(self):
        if not self.current_treatise:
            return
        folder = self.current_treatise.get("folder_path")
        topic = self.current_treatise.get("question", "بحث")
        category = self.current_treatise.get("category", "دفاعيات")
        content = self.current_treatise.get("content", "")
        sources = self.current_treatise.get("ghaly_sources", [])

        if folder and os.path.exists(folder):
            try:
                pptx_path = topic_archive.save_pptx_for_topic(folder)
                QMessageBox.information(self, "تم توليد العرض بنجاح", f"تم إنشاء وتسكين عرض البوربوينت (.pptx) في: {pptx_path}")
                os.startfile(pptx_path)
                return
            except Exception as e:
                print(f"Topic pptx save warning: {e}")

        # Fallback export dialog
        save_path, _ = QFileDialog.getSaveFileName(self, "حفظ عرض PowerPoint", f"عرض_{topic[:25]}.pptx".replace(" ", "_"), "PowerPoint (*.pptx)")
        if save_path:
            presentation_generator.create_slide_deck(topic, category, content, sources=sources, output_path=save_path)
            QMessageBox.information(self, "تم التصدير بنجاح", f"تم حفظ العرض في: {save_path}")
            os.startfile(save_path)

    def generate_audio_briefing_action(self):
        if not self.current_treatise:
            return
        folder = self.current_treatise.get("folder_path")
        topic = self.current_treatise.get("question", "بحث")
        content = self.current_treatise.get("content", "")

        self.btn_audio.setEnabled(False)
        self.progress_bar.setVisible(True)

        try:
            if folder and os.path.exists(folder):
                mp3_path = topic_archive.save_audio_for_topic(folder)
            else:
                save_path, _ = QFileDialog.getSaveFileName(self, "حفظ الموجز الصوتي", f"موجز_{topic[:25]}.mp3".replace(" ", "_"), "Audio MP3 (*.mp3)")
                if not save_path:
                    self.btn_audio.setEnabled(True)
                    self.progress_bar.setVisible(False)
                    return
                mp3_path = audio_briefing.generate_audio_briefing(topic, content, save_path)

            self.btn_audio.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "اكتمل توليد الصوت", f"تم إنشاء الموجز الصوتي الذكي بنجاح: {mp3_path}")
            os.startfile(mp3_path)
        except Exception as ex:
            self.btn_audio.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.warning(self, "خطأ في الصوت", f"تعذر توليد الموجز الصوتي: {ex}")

    def show_debate_matrix(self):
        if not self.current_treatise:
            return
        topic = self.current_treatise.get("question", "")
        content = self.current_treatise.get("content", "")
        dialog = topic_visualizers.DebateMatrixDialog(topic, content, self)
        dialog.exec_()

    def show_mind_map(self):
        if not self.current_treatise:
            return
        topic = self.current_treatise.get("question", "")
        content = self.current_treatise.get("content", "")
        dialog = topic_visualizers.MindMapViewerDialog(topic, content, self)
        dialog.drillDownRequested.connect(self.set_question)
        dialog.exec_()

    def show_manuscript_comparator(self):
        ref = self.current_treatise.get("question", "") if self.current_treatise else ""
        dialog = manuscript_comparator.ManuscriptComparatorDialog(self, initial_ref=ref)
        dialog.exec_()

    def export_docx(self):
        if not self.current_treatise:
            return

        default_name = f"بحث_دفاعي_{self.current_treatise['question'][:30]}.docx"
        clean_name = "".join(c for c in default_name if c not in '\\/*?:"<>|').replace(' ', '_')
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ البحث الدفاعي بصيغة Word",
            clean_name,
            "Word Documents (*.docx)"
        )
        if not save_path:
            return

        try:
            topic_archive.generate_topic_docx(
                title=self.current_treatise["question"],
                category=self.current_treatise.get("category", "دفاعيات"),
                content=self.current_treatise["content"],
                sources=self.current_treatise.get("ghaly_sources", []),
                output_path=save_path,
                created_at=self.current_treatise.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d"))
            )
            QMessageBox.information(self, "تم التصدير بنجاح", f"تم حفظ البحث الدفاعي المنسق بالصليب في:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ الملف: {e}")

    def copy_treatise_text(self):
        if not self.current_treatise:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.current_treatise.get("content", ""))
        QMessageBox.information(self, "تم النسخ", "تم نسخ نص البحث كاملاً إلى الحافظة! 📋")


class TopicArchiveWidget(QWidget):
    """
    مستعرض أرشيف الأبحاث التراكمي ومحرك التحديث التفاضلي
    يعرض جميع الموضوعات المحفوظة محلياً، عدد التوكنز الموفرة، ويمكّن من فحص المستجدات فقط.
    """
    def __init__(self, parent=None, library_root=None):
        super().__init__(parent)
        self.library_root = library_root
        self.current_topic_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header Info
        head_widget = QWidget()
        h_box = QHBoxLayout(head_widget)
        h_box.setContentsMargins(0, 0, 0, 0)

        v_t = QVBoxLayout()
        t = QLabel("🗄️ أرشيف الأبحاث والدفاعيات التراكمي (ذاكرة المكتبة الموفرة للتوكنز)")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        d = QLabel("كل موضوع يتم بحثه يُسكن محلياً كملف Word وفهرس، وعند البحث مستقبلاً يتم البحث عما هو أحدث فقط لتوفير التوكنز")
        d.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_t.addWidget(t)
        v_t.addWidget(d)
        h_box.addLayout(v_t, 1)

        self.btn_refresh_archive = QPushButton("🔄 تحديث قائمة الأرشيف")
        self.btn_refresh_archive.setStyleSheet("background-color: #1E293B; color: #CBD5E1; font-weight: bold; padding: 6px 14px; border-radius: 6px; border: 1px solid #334155;")
        self.btn_refresh_archive.clicked.connect(self.load_archived_topics)
        h_box.addWidget(self.btn_refresh_archive)

        layout.addWidget(head_widget)

        # Splitter: List on right/left and Preview on other
        splitter = QSplitter(Qt.Horizontal)

        # List Panel
        list_panel = QWidget()
        list_panel.setMinimumWidth(340)
        lp_layout = QVBoxLayout(list_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(6)

        search_box = QLineEdit()
        search_box.setPlaceholderText("بحث في الموضوعات المؤرشفة...")
        search_box.setStyleSheet("background-color: #1E222A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 6px 10px;")
        search_box.textChanged.connect(self.filter_archive_list)
        self.search_archive_input = search_box
        lp_layout.addWidget(search_box)

        self.archive_list = QListWidget()
        self.archive_list.setStyleSheet("""
            QListWidget {
                background-color: #1E222A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2D323B;
            }
            QListWidget::item:selected {
                background-color: #065F46;
                color: #FFFFFF;
                border-radius: 4px;
            }
        """)
        self.archive_list.itemClicked.connect(self.on_archive_item_clicked)
        lp_layout.addWidget(self.archive_list, 1)

        splitter.addWidget(list_panel)

        # Preview Panel
        prev_panel = QWidget()
        prev_layout = QVBoxLayout(prev_panel)
        prev_layout.setContentsMargins(0, 0, 0, 0)
        prev_layout.setSpacing(8)

        # Metadata banner
        self.meta_box = QGroupBox("📌 بيانات وتفاصيل الموضوع الموثق")
        self.meta_box.setStyleSheet("QGroupBox { border: 1px solid #059669; border-radius: 6px; font-weight: bold; color: #34D399; padding-top: 10px; }")
        mb_layout = QVBoxLayout(self.meta_box)

        self.topic_title_lbl = QLabel("اختر موضوعاً من القائمة لعرضه فوراً بدون استهلاك أي نقاط")
        self.topic_title_lbl.setStyleSheet("color: #E5C07B; font-size: 14px; font-weight: bold;")
        self.topic_title_lbl.setWordWrap(True)
        mb_layout.addWidget(self.topic_title_lbl)

        self.topic_stats_lbl = QLabel("")
        self.topic_stats_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        mb_layout.addWidget(self.topic_stats_lbl)

        action_row1 = QHBoxLayout()
        self.btn_diff_check = QPushButton("🔄 فحص التحديثات الجديدة فقط")
        self.btn_diff_check.setEnabled(False)
        self.btn_diff_check.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_diff_check.clicked.connect(self.run_differential_update)
        action_row1.addWidget(self.btn_diff_check)

        self.btn_open_word = QPushButton("📄 ملف Word")
        self.btn_open_word.setEnabled(False)
        self.btn_open_word.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_open_word.clicked.connect(self.open_word_file)
        action_row1.addWidget(self.btn_open_word)

        self.btn_open_pptx = QPushButton("📊 عرض PowerPoint")
        self.btn_open_pptx.setEnabled(False)
        self.btn_open_pptx.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_open_pptx.clicked.connect(self.open_or_gen_pptx)
        action_row1.addWidget(self.btn_open_pptx)

        self.btn_open_audio = QPushButton("🎧 الموجز الصوتي (.mp3)")
        self.btn_open_audio.setEnabled(False)
        self.btn_open_audio.setStyleSheet("background-color: #7C3AED; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_open_audio.clicked.connect(self.open_or_gen_audio)
        action_row1.addWidget(self.btn_open_audio)

        self.btn_open_dir = QPushButton("📂 فتح المجلد")
        self.btn_open_dir.setEnabled(False)
        self.btn_open_dir.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
        self.btn_open_dir.clicked.connect(self.open_topic_folder)
        action_row1.addWidget(self.btn_open_dir)

        action_row1.addStretch()
        mb_layout.addLayout(action_row1)

        action_row2 = QHBoxLayout()
        self.btn_toggle_star = QPushButton("⭐ رادار الترقب")
        self.btn_toggle_star.setEnabled(False)
        self.btn_toggle_star.setStyleSheet("background-color: #1E293B; color: #F59E0B; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px; border: 1px solid #F59E0B;")
        self.btn_toggle_star.clicked.connect(self.toggle_star_status)
        action_row2.addWidget(self.btn_toggle_star)

        self.btn_archive_matrix = QPushButton("📋 مصفوفة الردود")
        self.btn_archive_matrix.setEnabled(False)
        self.btn_archive_matrix.setStyleSheet("background-color: #1E293B; color: #60A5FA; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px; border: 1px solid #3B82F6;")
        self.btn_archive_matrix.clicked.connect(self.show_archive_matrix)
        action_row2.addWidget(self.btn_archive_matrix)

        self.btn_archive_mindmap = QPushButton("🧠 الخريطة الذهنية")
        self.btn_archive_mindmap.setEnabled(False)
        self.btn_archive_mindmap.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px; border: 1px solid #0284C7;")
        self.btn_archive_mindmap.clicked.connect(self.show_archive_mindmap)
        action_row2.addWidget(self.btn_archive_mindmap)

        self.btn_archive_manuscript = QPushButton("📜 مقارن المخطوطات")
        self.btn_archive_manuscript.setStyleSheet("background-color: #1E293B; color: #34D399; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 11px; border: 1px solid #059669;")
        self.btn_archive_manuscript.clicked.connect(self.show_archive_manuscript)
        action_row2.addWidget(self.btn_archive_manuscript)

        action_row2.addStretch()
        mb_layout.addLayout(action_row2)

        prev_layout.addWidget(self.meta_box)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 0)
        self.prog_bar.setVisible(False)
        self.prog_bar.setStyleSheet("QProgressBar { border: 1px solid #334155; border-radius: 4px; height: 12px; background-color: #1E222A; } QProgressBar::chunk { background-color: #10B981; }")
        prev_layout.addWidget(self.prog_bar)

        self.archive_text_preview = QTextEdit()
        self.archive_text_preview.setReadOnly(True)
        self.archive_text_preview.setStyleSheet("QTextEdit { background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.7; }")
        prev_layout.addWidget(self.archive_text_preview, 1)

        splitter.addWidget(prev_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.load_archived_topics()

    def load_archived_topics(self):
        self.archive_list.clear()
        topics = topic_archive.list_all_archived_topics(self.library_root)
        self.all_topics = topics
        query = self.search_archive_input.text().strip().lower()

        for t in topics:
            t_name = t.get("topic", "")
            cat = t.get("category", "")
            if query and query not in t_name.lower() and query not in cat.lower():
                continue

            last_u = t.get("last_updated", "").split(" ")[0]
            savings = t.get("tokens_saved_estimate", 0)
            item = QListWidgetItem(f"📁 {t_name}\n   📅 {last_u} | 💎 توفير: ~{savings:,} توكن")
            item.setData(Qt.UserRole, t)
            self.archive_list.addItem(item)

        if self.archive_list.count() > 0:
            self.archive_list.setCurrentRow(0)
            self.on_archive_item_clicked(self.archive_list.item(0))

    def filter_archive_list(self):
        self.load_archived_topics()

    def on_archive_item_clicked(self, item):
        if not item:
            return
        t_data = item.data(Qt.UserRole)
        self.current_topic_data = t_data

        topic_name = t_data.get("topic", "")
        self.topic_title_lbl.setText(f"📁 {topic_name}")
        self.topic_stats_lbl.setText(
            f"التصنيف: {t_data.get('category', 'دفاعيات')}  |  "
            f"تاريخ التوثيق: {t_data.get('created_at', '')}  |  "
            f"آخر تحديث: {t_data.get('last_updated', '')}  |  "
            f"الإصدار: v{t_data.get('version', 1)}  |  "
            f"المراجع المفهرسة: {len(t_data.get('sources', []))} مرجع  |  "
            f"💎 إجمالي التوكنز الموفرة: {t_data.get('tokens_saved_estimate', 0):,} Token"
        )

        self.btn_diff_check.setEnabled(True)
        self.btn_open_word.setEnabled(bool(t_data.get("docx_full_path") and os.path.exists(t_data["docx_full_path"])))
        self.btn_open_pptx.setEnabled(True)
        self.btn_open_audio.setEnabled(True)
        self.btn_open_dir.setEnabled(bool(t_data.get("folder_path") and os.path.exists(t_data["folder_path"])))
        self.btn_toggle_star.setEnabled(True)
        self.btn_archive_matrix.setEnabled(True)
        self.btn_archive_mindmap.setEnabled(True)
        is_starred = t_data.get("watchlist", False)
        self.btn_toggle_star.setText("⭐ في رادار الترقب (مفعل)" if is_starred else "☆ إضافة لرادار الترقب")

        text = t_data.get("full_treatise_text", "")
        self.archive_text_preview.setPlainText(text)

    def run_differential_update(self):
        if not self.current_topic_data:
            return

        folder_path = self.current_topic_data.get("folder_path")
        topic_name = self.current_topic_data.get("topic")

        self.prog_bar.setVisible(True)
        self.btn_diff_check.setEnabled(False)

        self.thread = QThread()
        self.worker = TopicUpdateWorker(folder_path, topic_name, self.library_root)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_diff_finished)
        self.worker.error.connect(self.on_diff_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_diff_finished(self, res):
        self.prog_bar.setVisible(False)
        self.btn_diff_check.setEnabled(True)
        QMessageBox.information(self, "فحص الأرشيف", res.get("message", ""))
        self.load_archived_topics()

    def on_diff_error(self, err):
        self.prog_bar.setVisible(False)
        self.btn_diff_check.setEnabled(True)
        QMessageBox.warning(self, "خطأ", f"تعذر استكمال الفحص: {err}")

    def open_word_file(self):
        if self.current_topic_data and self.current_topic_data.get("docx_full_path"):
            p = self.current_topic_data["docx_full_path"]
            if os.path.exists(p):
                os.startfile(p)

    def toggle_star_status(self):
        if not self.current_topic_data:
            return
        folder = self.current_topic_data.get("folder_path")
        if folder and os.path.exists(folder):
            new_state = topic_archive.toggle_watchlist_topic(folder)
            self.current_topic_data["watchlist"] = new_state
            self.btn_toggle_star.setText("⭐ في رادار الترقب (مفعل)" if new_state else "☆ إضافة لرادار الترقب")
            self.load_archived_topics()
            msg = "تمت إضافة الموضوع إلى رادار الترقب الدوري! ⭐" if new_state else "تمت إزالة الموضوع من رادار الترقب."
            QMessageBox.information(self, "رادار الترقب", msg)

    def open_or_gen_pptx(self):
        if not self.current_topic_data:
            return
        folder = self.current_topic_data.get("folder_path")
        slug = self.current_topic_data.get("slug", "بحث")
        pptx_name = self.current_topic_data.get("pptx_file", f"عرض_تقديمي_{slug}.pptx")
        pptx_path = os.path.join(folder, pptx_name)

        if os.path.exists(pptx_path):
            os.startfile(pptx_path)
            return

        self.prog_bar.setVisible(True)
        try:
            p_path = topic_archive.save_pptx_for_topic(folder)
            self.prog_bar.setVisible(False)
            self.current_topic_data["pptx_file"] = os.path.basename(p_path)
            QMessageBox.information(self, "تم توليد العرض", f"تم توليد عرض البوربوينت (.pptx) بنجاح في: {p_path}")
            os.startfile(p_path)
        except Exception as ex:
            self.prog_bar.setVisible(False)
            QMessageBox.warning(self, "خطأ", f"تعذر إنشاء العرض: {ex}")

    def open_or_gen_audio(self):
        if not self.current_topic_data:
            return
        folder = self.current_topic_data.get("folder_path")
        slug = self.current_topic_data.get("slug", "بحث")
        audio_name = self.current_topic_data.get("audio_file", f"ملخص_صوتي_{slug}.mp3")
        audio_path = os.path.join(folder, audio_name)

        if os.path.exists(audio_path):
            os.startfile(audio_path)
            return

        self.prog_bar.setVisible(True)
        try:
            a_path = topic_archive.save_audio_for_topic(folder)
            self.prog_bar.setVisible(False)
            self.current_topic_data["audio_file"] = os.path.basename(a_path)
            QMessageBox.information(self, "اكتمل الصوت", f"تم إنشاء الموجز الصوتي الذكي بنجاح: {a_path}")
            os.startfile(a_path)
        except Exception as ex:
            self.prog_bar.setVisible(False)
            QMessageBox.warning(self, "خطأ في الصوت", f"تعذر إنشاء الموجز الصوتي: {ex}")

    def show_archive_matrix(self):
        if not self.current_topic_data:
            return
        topic = self.current_topic_data.get("topic", "")
        content = self.current_topic_data.get("full_treatise_text", "")
        dialog = topic_visualizers.DebateMatrixDialog(topic, content, self)
        dialog.exec_()

    def show_archive_mindmap(self):
        if not self.current_topic_data:
            return
        topic = self.current_topic_data.get("topic", "")
        content = self.current_topic_data.get("full_treatise_text", "")
        dialog = topic_visualizers.MindMapViewerDialog(topic, content, self)
        dialog.exec_()

    def show_archive_manuscript(self):
        ref = self.current_topic_data.get("topic", "") if self.current_topic_data else ""
        dialog = manuscript_comparator.ManuscriptComparatorDialog(self, initial_ref=ref)
        dialog.exec_()

    def open_topic_folder(self):
        if self.current_topic_data and self.current_topic_data.get("folder_path"):
            p = self.current_topic_data["folder_path"]
            if os.path.exists(p):
                os.startfile(p)


class GhalySettlerWidget(QWidget):
    """
    محرك التسكين الأوفلاين لأبحاث د. غالي في المكتبة (I:\...):
    تحميل الأبحاث وتوليدها ككتب Word منسقة بالصليب وفهرستها في SQLite أوفلاين.
    """
    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.library_root = library_root
        self.project_id = project_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header Info
        t = QLabel("📥 محرك التسكين الأوفلاين لأبحاث د. غالي وموسوعات الدفاعيات")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        d = QLabel("جلب وتسكين أبحاث د. غالي وتوليدها ككتب Word منسقة بالصليب داخل قرصك الصلب I:\ وفهرستها أوفلاين 100% مدى الحياة")
        d.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(t)
        layout.addWidget(d)

        form_box = QGroupBox("⚙️ إعدادات الجلب والتسكين الأوفلاين")
        form_box.setStyleSheet("QGroupBox { border: 1px solid #3B82F6; border-radius: 6px; font-weight: bold; color: #60A5FA; padding-top: 12px; }")
        f_layout = QVBoxLayout(form_box)

        # Category / Search selector
        f_layout.addWidget(QLabel("اختر أو اكتب القسم المطلوب تسكينه في مكتبتك:"))
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.addItems([
            "سلسلة النقد النصي لمخطوطات العهد الجديد",
            "الرد على التطور الدارويني والشبهات البيولوجية",
            "عمر الأرض وحسابات الأنساب الكتابية",
            "جيولوجيا الطوفان وفلك نوح",
            "ألوهية السيد المسيح والنبوات في العهد القديم",
            "الرد على شبهات سفر دانيال والنقاد",
            "الصلب والقيامة وشهادات التاريخ والآثار",
            "أصالة رسائل بولس الرسول والرد على النقاد"
        ])
        f_layout.addWidget(self.cat_combo)

        row_cfg = QHBoxLayout()
        row_cfg.addWidget(QLabel("عدد الأبحاث المراد تسكينها:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 40)
        self.count_spin.setValue(10)
        row_cfg.addWidget(self.count_spin)

        row_cfg.addSpacing(20)
        row_cfg.addWidget(QLabel("مسار الحفظ في مكتبتك:"))
        default_dir = web_intelligence.OfflineLibrarySettler.get_default_ghaly_settle_dir(self.library_root)
        self.dir_lbl = QLabel(default_dir)
        self.dir_lbl.setStyleSheet("color: #34D399; font-weight: bold;")
        row_cfg.addWidget(self.dir_lbl, 1)

        f_layout.addLayout(row_cfg)

        self.btn_settle = QPushButton("📥 جلب وتسكين أبحاث د. غالي ككتب مرجعية في المكتبة (أوفلاين)")
        self.btn_settle.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: 1px solid #10B981;
            }
            QPushButton:hover { background-color: #10B981; }
            QPushButton:disabled { background-color: #374151; color: #9CA3AF; }
        """)
        self.btn_settle.clicked.connect(self.start_settling)
        f_layout.addWidget(self.btn_settle)

        layout.addWidget(form_box)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(False)
        self.prog_bar.setStyleSheet("QProgressBar { border: 1px solid #334155; border-radius: 4px; height: 14px; text-align: center; } QProgressBar::chunk { background-color: #10B981; }")
        layout.addWidget(self.prog_bar)

        # Live log
        self.settle_log = QTextEdit()
        self.settle_log.setReadOnly(True)
        self.settle_log.setStyleSheet("QTextEdit { background-color: #0F172A; color: #E2E8F0; border: 1px solid #334155; border-radius: 6px; padding: 10px; font-size: 12px; }")
        self.settle_log.setPlaceholderText("سجل تسكين الكتب والأبحاث سيظهر هنا...")
        layout.addWidget(self.settle_log, 1)

    def start_settling(self):
        query = self.cat_combo.currentText().strip()
        if not query:
            return

        count = self.count_spin.value()
        self.btn_settle.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.settle_log.append(f"🚀 بدء جلب أبحاث: '{query}' ({count} بحث)...")

        self.thread = QThread()
        self.worker = GhalySettlerWorker(
            query=query,
            output_dir=self.dir_lbl.text(),
            max_articles=count,
            project_id=self.project_id
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_settle_progress)
        self.worker.finished.connect(self.on_settle_finished)
        self.worker.error.connect(self.on_settle_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_settle_progress(self, idx, total, title, fpath):
        pct = int((idx / max(total, 1)) * 100)
        self.prog_bar.setValue(pct)
        self.settle_log.append(f"✅ [{idx}/{total}] تم تسكين وتوليد: {title}\n    📂 {fpath}")

    def on_settle_finished(self, saved_files):
        self.btn_settle.setEnabled(True)
        self.prog_bar.setValue(100)
        msg = f"🎉 اكتمل التسكين بنجاح! تم حفظ وتوليد {len(saved_files)} كتاباً مرجعياً في مكتبتك وفهرستها أوفلاين في قاعدة البيانات."
        self.settle_log.append(f"\n{msg}\n")
        QMessageBox.information(self, "اكتمل التسكين الأوفلاين", msg)

    def on_settle_error(self, err):
        self.btn_settle.setEnabled(True)
        self.prog_bar.setVisible(False)
        self.settle_log.append(f"❌ خطأ: {err}")
        QMessageBox.critical(self, "خطأ في التسكين", f"تعذر استكمال العملية: {err}")


class ApologeticsHubDialog(QDialog):
    """Wrapper dialog for standalone viewing when launched separately."""
    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.setWindowTitle("🛡️ منصة حصن الإيمان - موسوعة الدفاعيات والرد على الشبهات المعاصرة")
        self.resize(980, 740)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.hub_widget = ApologeticsHubWidget(self, library_root=library_root, project_id=project_id)
        layout.addWidget(self.hub_widget)
