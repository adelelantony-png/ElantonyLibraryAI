"""
Cross Coptic Library - Manuscript & Textual Comparison Engine
مقارن المخطوطات والترجمات النصي الذكي
Interactive scholarly textual criticism tool comparing Greek Codices (Sinaiticus, Vaticanus, Alexandrinus),
Coptic translations (Sahidic/Bohairic), Dead Sea Scrolls (Qumran), Syriac Peshitta, Latin Vulgate, and Early Church Fathers.
"""

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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QApplication,
    QGroupBox,
    QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from modules import ai_handler

CURATED_PASSAGES = [
    {
        "ref": "إشعياء 53 (سفر إشعياء وعبد الرب المتألم)",
        "scope": "العهد القديم والنبوات المسيانية",
        "question": "أصالة إشعياء 53 ومطابقة درج قمران الكبير (1QIsa) للنص العبري والسبعينية",
        "hebrew_masoretic": "مُحْتَقَرٌ وَمَخْذُولٌ مِنَ النَّاسِ، رَجُلُ أَوْجَاعٍ وَمُخْتَبِرُ الْحَزَنِ...",
        "septuagint_greek": "ἀλλὰ αὐτὸς ἐτραυματίσθη διὰ τὰς ἀνομίας ἡμῶν...",
        "qumran_1qisa": "درج إشعياء الكبير بقمران (1QIsa) يعود للقرن الثاني قبل الميلاد، متطابق بنسبة تفوق 95% حرفياً.",
        "coptic_version": "Ⲡⲉⲧⲥⲱϣ ⲟⲩⲟϩ ⲉⲧⲭⲏ ⲉⲃⲟⲗ... (النص القبطي الصعيدي والبحيري).",
        "verdict": "أعظم برهان أثري في تاريخ البشرية يثبت أصالة نبوة آلام المسيح قبل ميلاده بقرون دون أدنى تحريف."
    },
    {
        "ref": "1 تيموثاوس 3: 16 (الله ظهر في الجسد)",
        "scope": "العهد الجديد وألوهية المسيح",
        "question": "القراءة النصية: هل هي 'الله ظهر في الجسد' (ΘC) أم 'الذي ظهر' (OC)؟",
        "hebrew_masoretic": "غير متاح (عهد جديد)",
        "septuagint_greek": "Θεὸς ἐφανερώθη ἐν σαρκί (Codex Alexandrinus A, Codex Ephraemi C3, Textus Receptus)",
        "qumran_1qisa": "غير متاح",
        "coptic_version": "Ⲡⲛⲟⲩⲧⲉ ⲁϥⲟⲩⲱⲛϩ ⲉⲃⲟⲗ ϧⲉⲛ ⲟⲩⲥⲁⲣⲝ (الله ظهر في الجسد).",
        "verdict": "المخطوطة الإسكندرية A ومعظم المخطوطات البيزنطية والآباء (كيرلس الكبير ويوحنا ذهبي الفم) تؤكد قراءة 'الله'."
    },
    {
        "ref": "1 يوحنا 5: 7-8 (الفاصلة اليوحناوية والشهود الثلاثة)",
        "scope": "العقيدة والتثليث",
        "question": "الذين يشهدون في السماء هم ثلاثة: الآب والكلمة والروح القدس",
        "hebrew_masoretic": "غير متاح",
        "septuagint_greek": "ὅτι τρεῖς εἰσιν οἱ μαρτυροῦντες ἐν τῷ οὐρανῷ, ὁ Πατήρ, ὁ Λόγος, καὶ τὸ Ἅγιον Πνεῦμα...",
        "qumran_1qisa": "غير متاح",
        "coptic_version": "الشواهد اللاتينية القديمة (Itala)، واقتباسات ترتليان وقبريانوس وأثناسيوس الرسولي والقطمارس القبطي.",
        "verdict": "عقيدة التثليث ثابتة في عشرات النصوص الأخرى، والآية موثقة في التراث اللاتيني والقبطي والتقليد الكنسي."
    },
    {
        "ref": "مرقس 16: 9-20 (خاتمة إنجيل مرقس والقيامة)",
        "scope": "صحة الأناجيل وتاريخ القيامة",
        "question": "أصالة الآيات الإثنتي عشرة الأخيرة من إنجيل مرقس",
        "hebrew_masoretic": "غير متاح",
        "septuagint_greek": "Ἀναστὰς δὲ πρωῒ πρώτῃ σαββάτου... (Codex Alexandrinus, Bezae, Ephraemi)",
        "qumran_1qisa": "غير متاح",
        "coptic_version": "موجودة في جميع المخطوطات القبطية البحيرية والصعيدية بدون استثناء والقطمارس السنوي.",
        "verdict": "يشهد لها القديس إيريناؤس تلميذ بوليكاربوس تلميذ يوحنا في القرن الثاني (ضد الهرطقات 3: 10: 5)."
    }
]

class ManuscriptAnalysisWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, verse_ref):
        super().__init__()
        self.verse_ref = verse_ref

    def run(self):
        try:
            prompt = (
                f"أنت عالم لاهوت ونقد نصي ومخطوطات كتابية قبطي أرثوذكسي متبحر.\n"
                f"مطلوب إجراء دراسة مقارنة نصية رصينة للشاهد الكتابي التالي: '{self.verse_ref}'.\n\n"
                f"الهيكل الإلزامي للدراسة المقارنة:\n"
                f"1. الشاهد وسياق القضية النصية (The Textual Variant Problem).\n"
                f"2. القراءات في المخطوطات اليونانية الكبرى (السينائية א، الفاتيكانية B، الإسكندرية A، واشنطن W).\n"
                f"3. القراءات في الترجمات القبطية القديمة (الصعيدية والبحيرية) واستخدامها في طقوس الكنيسة القبطية.\n"
                f"4. القراءات في المخطوطات القديمة الأخرى (قمران للعهد القديم، السريانية البسيطة Peshitta، اللاتينية القديمة والفولجاتا).\n"
                f"5. اقتباسات الآباء الأوائل قبل مجمع نيقية (القرن الثاني والثالث).\n"
                f"6. النتيجة والتحقيق الأرثوذكسي النهائي والدفاع عن أصالة الوحي."
            )

            result = ai_handler.call_ai_routed(
                prompt,
                system_instruction="أنت خبير أكاديمي رصين في النقد النصي لمخطوطات الكتاب المقدس واللغات القديمة (اليونانية والقبطية والعبرية)."
            )

            self.finished.emit({
                "verse_ref": self.verse_ref,
                "analysis": result
            })
        except Exception as e:
            self.error.emit(str(e))

class ManuscriptComparatorDialog(QDialog):
    def __init__(self, parent=None, initial_ref=None):
        super().__init__(parent)
        self.setWindowTitle("📜 مقارن المخطوطات والترجمات النصي الذكي (Manuscript Comparator)")
        self.resize(1050, 750)
        self.setLayoutDirection(Qt.RightToLeft)
        self.initial_ref = initial_ref
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #E2E8F0;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QLabel {
                font-size: 13px;
                color: #CBD5E1;
            }
            QLineEdit, QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QTableWidget {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #0B0F19;
                color: #D4AF37;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header Banner
        h_box = QHBoxLayout()
        v_titles = QVBoxLayout()
        t = QLabel("📜 مقارن المخطوطات والترجمات الأثرية الذكي")
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #D4AF37;")
        d = QLabel("فحص ومقارنة شواهد النقد النصي عبر المخطوطات الكبرى (السينائية، الفاتيكانية، الإسكندرية، قمران، والقبطية)")
        d.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_titles.addWidget(t)
        v_titles.addWidget(d)
        h_box.addLayout(v_titles, 1)
        layout.addLayout(h_box)

        # Top Control Row
        ctrl_box = QGroupBox("🔍 اختيار الشاهد أو كتابة آية مخصصة")
        ctrl_box.setStyleSheet("QGroupBox { border: 1px solid #3B82F6; border-radius: 6px; font-weight: bold; color: #60A5FA; padding-top: 10px; }")
        c_layout = QHBoxLayout(ctrl_box)

        c_layout.addWidget(QLabel("شواهد وقضايا نقدية بارزة:"))
        self.passage_combo = QComboBox()
        self.passage_combo.setMinimumWidth(320)
        for p in CURATED_PASSAGES:
            self.passage_combo.addItem(p["ref"], p)
        self.passage_combo.currentIndexChanged.connect(self.on_passage_selected)
        c_layout.addWidget(self.passage_combo)

        c_layout.addWidget(QLabel("أو شاهد مخصص:"))
        self.custom_verse_input = QLineEdit()
        self.custom_verse_input.setPlaceholderText("مثال: يوحنا 1: 1 أو مزمور 22: 16...")
        c_layout.addWidget(self.custom_verse_input, 1)

        self.btn_analyze = QPushButton("🚀 مقارنة وتحليل نصي ذكي")
        self.btn_analyze.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; padding: 7px 16px; border-radius: 6px;")
        self.btn_analyze.clicked.connect(self.start_textual_analysis)
        c_layout.addWidget(self.btn_analyze)

        layout.addWidget(ctrl_box)

        # Splitter: Table View / Detailed Textual Criticism Output
        splitter = QSplitter(Qt.Vertical)

        # Table: Curated / Key Comparative Data
        self.comp_table = QTableWidget(4, 2)
        self.comp_table.setHorizontalHeaderLabels(["المصدر الأثري / المخطوطة", "النص والشاهد التاريخي المقابل"])
        self.comp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.comp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.comp_table.verticalHeader().setVisible(False)
        self.comp_table.setStyleSheet("QTableWidget::item { padding: 8px; }")
        splitter.addWidget(self.comp_table)

        # Textual Commentary & Patristic Consensus
        self.analysis_display = QTextEdit()
        self.analysis_display.setReadOnly(True)
        self.analysis_display.setStyleSheet("QTextEdit { background-color: #0B0F19; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 12px; font-size: 13px; line-height: 1.7; }")
        self.analysis_display.setPlaceholderText("سيظهر هنا التحقيق النقدي الشامل، وشهادة المخطوطات اليونانية والقبطية وأقوال الآباء...")
        splitter.addWidget(self.analysis_display)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Footer Actions
        f_box = QHBoxLayout()
        self.btn_copy = QPushButton("📋 نسخ التحقيق النصي كاملاً")
        self.btn_copy.setStyleSheet("background-color: #334155; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.btn_copy.clicked.connect(self.copy_analysis)
        f_box.addWidget(self.btn_copy)

        f_box.addStretch()

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("background-color: #1E293B; color: #94A3B8; padding: 8px 16px; border-radius: 6px;")
        btn_close.clicked.connect(self.accept)
        f_box.addWidget(btn_close)
        layout.addLayout(f_box)

        self.on_passage_selected(0)

    def on_passage_selected(self, index):
        data = self.passage_combo.currentData()
        if not data:
            return

        self.comp_table.setRowCount(5)
        rows = [
            ("📜 النص اليوناني / المخطوطات الكبرى", data.get("septuagint_greek", "")),
            ("🇪🇬 الترجمات القبطية (صعيدي وبحيري)", data.get("coptic_version", "")),
            ("🏺 قمران ومخطوطات العهد القديم", data.get("qumran_1qisa", "")),
            ("📖 النص العبري الماسوري / اللاتيني", data.get("hebrew_masoretic", "")),
            ("⚖️ التحقيق والنتيجة الأرثوذكسية", data.get("verdict", ""))
        ]

        for i, (title, val) in enumerate(rows):
            item_t = QTableWidgetItem(title)
            item_t.setForeground(Qt.yellow)
            item_v = QTableWidgetItem(val)
            self.comp_table.setItem(i, 0, item_t)
            self.comp_table.setItem(i, 1, item_v)

        # Initial analysis preview
        html = (
            f"<h3 style='color: #E5C07B;'>قضية الشاهد: {data['ref']}</h3>"
            f"<p style='color: #38BDF8;'><b>التصنيف:</b> {data['scope']}</p>"
            f"<div style='background-color: #1E293B; padding: 10px; border-radius: 6px; margin: 8px 0;'>"
            f"<b>التحقيق الأثري والنصي:</b><br>{data['verdict']}"
            f"</div>"
            f"<p style='color: #94A3B8;'>اضغط «مقارنة وتحليل نصي ذكي» أعلاه لتوليد دراسة نقدية متعمقة بالذكاء الاصطناعي مدعومة بمقتطفات الآباء والمخطوطات.</p>"
        )
        self.analysis_display.setHtml(html)

    def start_textual_analysis(self):
        custom = self.custom_verse_input.text().strip()
        ref = custom if custom else self.passage_combo.currentText()

        self.btn_analyze.setEnabled(False)
        self.analysis_display.setHtml("<div style='color: #38BDF8; text-align: center; padding: 25px;'>⏳ جاري استدعاء مخطوطات السينائية، الفاتيكانية، الترجمات القبطية وقمران وتحليل الشاهد...</div>")

        self.thread = QThread()
        self.worker = ManuscriptAnalysisWorker(ref)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_analysis_finished(self, res):
        self.btn_analyze.setEnabled(True)
        text = res.get("analysis", "")
        formatted_html = self.format_markdown(res.get("verse_ref", "الشاهد"), text)
        self.analysis_display.setHtml(formatted_html)

    def on_analysis_error(self, err):
        self.btn_analyze.setEnabled(True)
        self.analysis_display.setPlainText(f"❌ خطأ: {err}")

    def format_markdown(self, title, text):
        lines = text.splitlines()
        html = [f"<h2 style='color: #E5C07B; border-bottom: 2px solid #E5C07B; padding-bottom: 6px;'>📜 دراسة نقدية مقارنة: {title}</h2>"]
        for line in lines:
            line = line.strip()
            if not line:
                html.append("<br>")
                continue
            if line.startswith("### "):
                html.append(f"<h3 style='color: #38BDF8; margin-top: 14px;'>{line[4:]}</h3>")
            elif line.startswith("## "):
                html.append(f"<h2 style='color: #60A5FA; margin-top: 16px;'>{line[3:]}</h2>")
            elif line.startswith("- ") or line.startswith("* "):
                html.append(f"<div style='margin-right: 15px;'>🔹 {line[2:]}</div>")
            else:
                html.append(f"<p style='margin: 4px 0;'>{line}</p>")
        return "".join(html)

    def copy_analysis(self):
        text = self.analysis_display.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "تم النسخ", "تم نسخ التحقيق النصي المقارن إلى الحافظة! 📋")
