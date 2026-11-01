"""
Cross Coptic Library - Library Audit & Gap Engine Dialog (Ultra Pro Max)
Interactive diagnostic & automated resolution tool:
1. Evaluates library against canonical benchmarks (patristics, apologetics, history, canon, liturgy, monasticism).
2. One-click instant search & download for missing books from ChristianLib, Archive.org, Coptic-Treasures, and Dr. Ghaly.
3. Automated Gap Resolution ("سد الثغرات تلقائياً") per discipline or batch across the entire library.
4. Live health score updating in real time upon downloading missing volumes.
"""

import os
import re
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QWidget,
    QScrollArea,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QFrame,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
try:
    from PyQt5 import sip
except ImportError:
    import sip

def is_valid_widget(w):
    """Safely checks if a Qt C++ widget is alive and has not been deleted by C++."""
    if w is None:
        return False
    try:
        return not sip.isdeleted(w)
    except Exception:
        return False

from modules import library_auditor, online_book_feeder

class GapResolveWorker(QObject):
    log_emitted = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, mode, key=None, library_root=None, project_id=1):
        super().__init__()
        self.mode = mode
        self.key = key
        self.library_root = library_root
        if not self.library_root or not os.path.exists(self.library_root):
            default_lib = r"I:\2021\2020\✠ Cross Coptic Library ✠"
            if os.path.exists(default_lib):
                self.library_root = default_lib
            else:
                self.library_root = os.path.abspath(os.getcwd())
        self.project_id = project_id

    def run(self):
        try:
            if self.mode == "discipline":
                count = library_auditor.auto_resolve_discipline_gaps(
                    self.key, self.library_root, project_id=self.project_id, max_books=2, log_callback=self.log_emitted.emit
                )
            else:
                count = library_auditor.auto_resolve_all_critical_gaps(
                    self.library_root, project_id=self.project_id, log_callback=self.log_emitted.emit
                )
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class SearchCandidatesWorker(QObject):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            candidates = online_book_feeder.search_online_candidates(self.query, limit=12)
            self.results_ready.emit(candidates)
        except Exception as e:
            self.error.emit(str(e))

class DownloadBookWorker(QObject):
    log_emitted = pyqtSignal(str)
    finished = pyqtSignal(bool, str, int)
    error = pyqtSignal(str)

    def __init__(self, candidate, library_root, project_id=1):
        super().__init__()
        self.candidate = candidate
        self.library_root = library_root
        if not self.library_root or not os.path.exists(self.library_root):
            default_lib = r"I:\2021\2020\✠ Cross Coptic Library ✠"
            if os.path.exists(default_lib):
                self.library_root = default_lib
            else:
                self.library_root = os.path.abspath(os.getcwd())
        self.project_id = project_id

    def run(self):
        try:
            ok, dest, size = online_book_feeder.download_and_index_candidate(
                self.candidate, self.library_root, project_id=self.project_id, log_callback=self.log_emitted.emit
            )
            self.finished.emit(ok, dest, size)
        except Exception as e:
            self.error.emit(str(e))

class LibraryAuditDialog(QDialog):
    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.setWindowTitle("🧠 فحص وتدقيق ثغرات المكتبة الكنسية ومعالج النواقص التلقائي")
        self.resize(1020, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        self.library_root = library_root
        if not self.library_root or not os.path.exists(self.library_root):
            default_lib = r"I:\2021\2020\✠ Cross Coptic Library ✠"
            if os.path.exists(default_lib):
                self.library_root = default_lib
            else:
                self.library_root = os.path.abspath(os.getcwd())
        self.project_id = project_id

        self.current_candidates = []
        self.download_queue = []
        self.is_downloading = False
        self.total_queue_jobs = 0
        self.completed_jobs = 0
        self.successful_jobs = 0
        self.active_dl_threads = []

        self.audit_data = library_auditor.analyze_library(
            library_root=self.library_root,
            project_id=self.project_id
        )

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
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
                color: #E2E8F0;
                background-color: #1E293B;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #D4AF37;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #1E293B;
            }
            QTabBar::tab {
                background: #0B0F19;
                color: #94A3B8;
                padding: 10px 20px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-left: 2px;
            }
            QTabBar::tab:selected {
                background: #1D4ED8;
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
            QTableWidget {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #1E293B;
                color: #F8FAFC;
            }
            QHeaderView::section {
                background-color: #0B0F19;
                color: #D4AF37;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                background-color: #0F172A;
                color: #FFFFFF;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #090D16;
                color: #38BDF8;
                border: 1px solid #334155;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # 1. Header Banner
        main_layout.addWidget(self.create_header_banner())

        # 2. Tabs Widget
        self.tabs = QTabWidget()

        # Tab 1: Coverage Indicators
        self.tab_coverage = self.create_coverage_tab()
        self.tabs.addTab(self.tab_coverage, "📈 مؤشرات التغطية اللاهوتية")

        # Tab 2: Missing Books Recommendations & 1-Click Search
        self.tab_recs = self.create_recommendations_tab()
        self.tabs.addTab(self.tab_recs, "⚠️ المراجع والكتب الشاغرة (الموصى باقتنائها)")

        # Tab 3: Gap Resolver & Online Downloader
        self.tab_resolver = self.create_gap_resolver_tab()
        self.tabs.addTab(self.tab_resolver, "📥 محرك البحث وسد النواقص من الإنترنت")

        # Tab 4: Empty Folders Detection
        self.tab_empty = self.create_empty_folders_tab()
        self.tabs.addTab(self.tab_empty, f"📁 تنبيه المجلدات الفارغة ({len(self.audit_data.get('empty_folders', []))})")

        main_layout.addWidget(self.tabs, 1)

        # 3. Bottom Action Bar
        main_layout.addLayout(self.create_bottom_bar())

    def create_header_banner(self):
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0B0F19);
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(10, 8, 10, 8)

        # Info Box
        v_info = QVBoxLayout()
        title_lbl = QLabel("✝️ التقرير الذكي لسلامة وتغطية مكتبة الصليب القبطية الأرثوذكسية وسد الثغرات")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37;")
        
        self.sub_lbl = QLabel(
            f"إجمالي المراجع المفهرسة: {self.audit_data.get('total_files', 0):,} كتاباً • تقييم التغطية وفق معيار المراجع الكنسية الشاملة"
        )
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        v_info.addWidget(title_lbl)
        v_info.addWidget(self.sub_lbl)
        h_layout.addLayout(v_info, 1)

        # Quick Action Buttons in Header
        act_layout = QHBoxLayout()
        
        self.btn_auto_fill_all = QPushButton("⚡ الحاصد الآلي لسد ثغرات المؤلفين (Autopilot)")
        self.btn_auto_fill_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
                color: white;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #10B981;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_auto_fill_all.clicked.connect(self.launch_autopilot_harvester)
        act_layout.addWidget(self.btn_auto_fill_all)

        btn_go_search = QPushButton("🔍 البحث اليدوي في المستودعات")
        btn_go_search.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3B82F6; }
        """)
        btn_go_search.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        act_layout.addWidget(btn_go_search)

        btn_refresh = QPushButton("🔄 تحديث فحص المكتبة")
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        btn_refresh.clicked.connect(self.refresh_audit)
        act_layout.addWidget(btn_refresh)

        h_layout.addLayout(act_layout)

        # Health Score Badge
        score = self.audit_data.get("overall_health_score", 0)
        self.score_badge = QLabel(f"{score}%")
        self.update_score_badge_style(score)
        h_layout.addWidget(self.score_badge)

        return header_widget

    def update_score_badge_style(self, score):
        color = '#10B981' if score >= 80 else ('#F59E0B' if score >= 60 else '#EF4444')
        self.score_badge.setText(f"{score}%")
        self.score_badge.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {color};
            background-color: #0F172A;
            border: 2px solid {color};
            border-radius: 26px;
            padding: 6px 14px;
            qproperty-alignment: AlignCenter;
        """)

    def create_coverage_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        for branch_key, b in self.audit_data.get("branches", {}).items():
            pct = b.get("coverage_pct", 0)
            box = QGroupBox(b.get("title", ""))
            box_layout = QVBoxLayout(box)

            row = QHBoxLayout()
            pbar = QProgressBar()
            pbar.setValue(pct)
            pbar.setFixedHeight(20)
            pbar.setTextVisible(True)
            pbar.setFormat(f"{pct}%")

            if pct >= 80:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #10B981; border-radius: 4px; }")
            elif pct >= 60:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #F59E0B; border-radius: 4px; }")
            else:
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #EF4444; border-radius: 4px; }")

            lbl_count = QLabel(f"{b.get('covered_authors', 0)} من {b.get('total_authors', 0)} أصول متوفرة")
            lbl_count.setStyleSheet("color: #94A3B8; font-size: 11px;")

            row.addWidget(pbar, 1)
            row.addWidget(lbl_count)

            # Auto-fill button if branch has missing books
            if pct < 100:
                btn_fill = QPushButton("⚡ سد نواقص هذا التخصص")
                btn_fill.setStyleSheet("""
                    QPushButton {
                        background-color: #0284C7;
                        color: white;
                        font-weight: bold;
                        font-size: 11px;
                        padding: 4px 10px;
                        border-radius: 4px;
                    }
                    QPushButton:hover { background-color: #38BDF8; color: black; }
                """)
                btn_fill.clicked.connect(lambda ch, k=branch_key: self.start_auto_fill_discipline(k))
                row.addWidget(btn_fill)

            box_layout.addLayout(row)
            layout.addWidget(box)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_recommendations_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        for branch_key, b in self.audit_data.get("branches", {}).items():
            recs = b.get("recommendations", [])
            missing_details = [d["name"] for d in b.get("details", []) if d.get("status") == "missing"]

            if recs or missing_details:
                box = QGroupBox(b.get("title", ""))
                b_layout = QVBoxLayout(box)

                # Header action to resolve this branch
                top_row = QHBoxLayout()
                lbl_sub = QLabel(f"نسبة التغطية الحالية: {b.get('coverage_pct', 0)}% • النواقص المرصودة: {len(missing_details)}")
                lbl_sub.setStyleSheet("color: #94A3B8; font-size: 11px;")
                top_row.addWidget(lbl_sub, 1)

                btn_branch_fill = QPushButton("⚡ سد وتنزيل نواقص هذا التخصص")
                btn_branch_fill.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
                btn_branch_fill.clicked.connect(lambda ch, k=branch_key: self.start_auto_fill_discipline(k))
                top_row.addWidget(btn_branch_fill)
                b_layout.addLayout(top_row)

                # Display items
                for r in recs:
                    card = QFrame()
                    card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 6px; }")
                    c_layout = QHBoxLayout(card)
                    c_layout.setContentsMargins(8, 4, 8, 4)

                    t_lbl = QLabel(f"📖 {r}")
                    t_lbl.setStyleSheet("color: #F1F5F9; font-size: 12px; font-weight: 500;")
                    t_lbl.setWordWrap(True)
                    c_layout.addWidget(t_lbl, 1)

                    btn_search_this = QPushButton("🔍 بحث وتنزيل فوري")
                    btn_search_this.setStyleSheet("""
                        QPushButton {
                            background-color: #2563EB;
                            color: white;
                            font-weight: bold;
                            padding: 5px 12px;
                            border-radius: 4px;
                            font-size: 11px;
                        }
                        QPushButton:hover { background-color: #3B82F6; }
                    """)
                    clean_query = r.split("(")[0].replace("كتاب", "").replace("موسوعة", "").replace("مجموعة", "").strip()
                    btn_search_this.clicked.connect(lambda ch, q=clean_query: self.jump_to_search(q))
                    c_layout.addWidget(btn_search_this)

                    b_layout.addWidget(card)

                layout.addWidget(box)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_gap_resolver_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Search Bar
        search_box = QGroupBox("🔎 البحث الفوري في المستودعات الكنسية وتنزيل الكتب الناقصة أوفلاين")
        sb_layout = QVBoxLayout(search_box)
        
        row_s = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اكتب اسم الكتاب أو الصق أي رابط صفحة/موقع (مثال: https://library.awtar-alsama.com/a-41/)...")
        self.search_input.returnPressed.connect(self.on_search_clicked)
        row_s.addWidget(self.search_input, 1)

        self.btn_search = QPushButton("🔍 فحص الرابط أو البحث")
        self.btn_search.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_search.clicked.connect(self.on_search_clicked)
        row_s.addWidget(self.btn_search)

        self.btn_toggle_awtar = QPushButton("📚 دليل أوتار السماء (82 مؤلفاً)")
        self.btn_toggle_awtar.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;")
        self.btn_toggle_awtar.setToolTip("فتح مستكشف دليل مؤلفي وقديسي مكتبة أوتار السماء الـ 82")
        self.btn_toggle_awtar.clicked.connect(self.toggle_awtar_box)
        row_s.addWidget(self.btn_toggle_awtar)

        sb_layout.addLayout(row_s)

        # -------------------------------------------------------------
        # Awtar-Alsama 82-Author Navigator Box (Interactive Directory)
        # -------------------------------------------------------------
        self.awtar_box = QGroupBox("📖 دليل مؤلفي وقديسي مكتبة أوتار السماء (82 مؤلفاً) - تصفح وجلب فوري")
        self.awtar_box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #D4AF37;
                border-radius: 8px;
                margin-top: 6px;
                font-weight: bold;
                color: #FBBF24;
                background-color: #0F172A;
                padding: 10px;
            }
        """)
        awtar_layout = QVBoxLayout(self.awtar_box)
        
        row_aw = QHBoxLayout()
        lbl_sel = QLabel("اختر المؤلف / القديس:")
        lbl_sel.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        row_aw.addWidget(lbl_sel)

        self.awtar_combo = QComboBox()
        self.awtar_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                min-width: 320px;
            }
            QComboBox QAbstractItemView {
                background-color: #0F172A;
                color: white;
                selection-background-color: #0284C7;
            }
        """)
        row_aw.addWidget(self.awtar_combo, 1)

        self.btn_fetch_author_books = QPushButton("📥 جلب كافة كتب هذا المؤلف للجدول")
        self.btn_fetch_author_books.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_fetch_author_books.clicked.connect(self.on_fetch_author_clicked)
        row_aw.addWidget(self.btn_fetch_author_books)

        self.btn_autopilot_harvest = QPushButton("⚡ الحاصد الآلي لكافة المؤلفين (سد الثغرات تلقائياً) 🚀")
        self.btn_autopilot_harvest.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D97706);
                color: white;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
                border: 1px solid #F59E0B;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #F59E0B);
                border-color: #FCD34D;
            }
        """)
        self.btn_autopilot_harvest.setToolTip("يمر تلقائياً على كل مؤلف في أوتار السماء (الـ 82 مؤلفاً)، ويفحص كتبه وينزل الثغرات المفقودة فقط بدون تكرار وبدون تدخل يدوي.")
        self.btn_autopilot_harvest.clicked.connect(self.launch_autopilot_harvester)
        row_aw.addWidget(self.btn_autopilot_harvest)
        awtar_layout.addLayout(row_aw)

        # Quick filter row
        row_flt = QHBoxLayout()
        lbl_flt = QLabel("🔍 فلترة سريعة بالاسم:")
        lbl_flt.setStyleSheet("color: #94A3B8; font-size: 11px;")
        row_flt.addWidget(lbl_flt)

        self.le_author_filter = QLineEdit()
        self.le_author_filter.setPlaceholderText("اكتب جزءاً من الاسم للتصفية الفورية (مثال: شنودة، تادرس، أثناسيوس، متى، بيمن، بسيط)...")
        self.le_author_filter.setStyleSheet("background-color: #1E293B; color: white; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
        self.le_author_filter.textChanged.connect(self.filter_awtar_authors)
        row_flt.addWidget(self.le_author_filter, 1)
        awtar_layout.addLayout(row_flt)

        # Load authors catalog
        self.awtar_catalog_data = online_book_feeder.get_awtar_alsama_catalog()
        for item in self.awtar_catalog_data:
            self.awtar_combo.addItem(f"👤 {item['name']}", item['url'])

        sb_layout.addWidget(self.awtar_box)

        # Quick missing chips
        chip_layout = QHBoxLayout()
        chip_lbl = QLabel("📌 روابط وكتب موصى بها:")
        chip_lbl.setStyleSheet("color: #D4AF37; font-size: 11px; font-weight: bold;")
        chip_layout.addWidget(chip_lbl)

        quick_titles = [
            "https://library.awtar-alsama.com/1/",
            "https://library.awtar-alsama.com/a-30/",
            "https://library.awtar-alsama.com/a-41/",
            "تجسد الكلمة أثناسيوس",
            "مصباح الظلمة ابن كبر",
            "بستان الرهبان",
            "مدارس النقد والتشكيك"
        ]
        for qt in quick_titles:
            btn_chip = QPushButton(qt)
            btn_chip.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #38BDF8;
                    border: 1px solid #334155;
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #0284C7; color: white; }
            """)
            btn_chip.clicked.connect(lambda ch, q=qt: self.jump_to_search(q))
            chip_layout.addWidget(btn_chip)
        chip_layout.addStretch()
        sb_layout.addLayout(chip_layout)

        layout.addWidget(search_box)

        # 2. Results Header Bar with "Download All" & "Smart Gaps Only" Actions
        res_bar = QHBoxLayout()
        res_title = QLabel("📚 نتائج البحث والكتب المكتشفة في المستودعات الكنسية:")
        res_title.setStyleSheet("color: #D4AF37; font-weight: bold; font-size: 13px;")
        res_bar.addWidget(res_title, 1)

        self.btn_download_gaps = QPushButton("⭐ تنزيل الثغرات فقط (استبعاد المتوفر)")
        self.btn_download_gaps.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #F59E0B; }
            QPushButton:disabled { background-color: #334155; color: #94A3B8; }
        """)
        self.btn_download_gaps.clicked.connect(self.download_gaps_only)
        res_bar.addWidget(self.btn_download_gaps)

        self.btn_download_all = QPushButton("📥 تنزيل كافة النتائج المتاحة (تنزيل الكل)")
        self.btn_download_all.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #10B981; }
            QPushButton:disabled { background-color: #334155; color: #94A3B8; }
        """)
        self.btn_download_all.clicked.connect(self.download_all_candidates)
        res_bar.addWidget(self.btn_download_all)
        layout.addLayout(res_bar)

        # 3. Results Table with Local Intelligence Column
        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels([
            "📖 عنوان الكتاب المتاح",
            "🏛️ المستودع الرقمي",
            "🧠 الحالة في مكتبتك الأوفلاين",
            "📂 المجلد المستهدف بالمكتبة",
            "📄 الصيغة",
            "⚡ الإجراء"
        ])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self.results_table.setColumnWidth(5, 140)
        self.results_table.setStyleSheet("QTableWidget::item { padding: 6px; }")
        layout.addWidget(self.results_table, 1)

        # 3. Live Progress & Status Console
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #10B981; }")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.log_console = QTextEdit()
        self.log_console.setFixedHeight(90)
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("سجل عمليات البحث والتنزيل الفوري والتسكين التلقائي في قرصك الصلب...")
        layout.addWidget(self.log_console)

        return widget

    def create_empty_folders_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        empty_list = self.audit_data.get("empty_folders", [])
        if not empty_list:
            lbl = QLabel("🎉 لا توجد مجلدات فارغة، كافة المجلدات تضم كتباً وملفات مرتبة ومفهرسة!")
            lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px; padding: 20px;")
            layout.addWidget(lbl)
        else:
            hint = QLabel("⚠️ المجلدات التالية مخصصة في مكتبتك ولكنها شاغرة (0 ملفات) أو شبه فارغة، يمكنك تغذيتها فوراً:")
            hint.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 12px;")
            layout.addWidget(hint)

            for folder, count in empty_list:
                card = QFrame()
                card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 6px; }")
                c_lay = QHBoxLayout(card)
                
                f_lbl = QLabel(f"📁 /{folder}")
                f_lbl.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 12px;")
                c_lay.addWidget(f_lbl, 1)

                cnt_lbl = QLabel("فارغ تماماً (0 كتب)" if count == 0 else f"{count} ملفات فقط")
                cnt_lbl.setStyleSheet("color: #EF4444;" if count == 0 else "color: #F59E0B;")
                c_lay.addWidget(cnt_lbl)

                btn_feed = QPushButton("📥 تغذية هذا المجلد بالكتب")
                btn_feed.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
                btn_feed.clicked.connect(lambda ch, f=folder: self.jump_to_search(f))
                c_lay.addWidget(btn_feed)

                layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def create_bottom_bar(self):
        btn_box = QHBoxLayout()
        btn_copy = QPushButton("📋 نسخ تقرير التدقيق كاملاً")
        btn_copy.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 7px 14px; border-radius: 5px;")
        btn_copy.clicked.connect(self.copy_report_to_clipboard)

        btn_save = QPushButton("💾 تصدير التقرير في ملف نصي")
        btn_save.setStyleSheet("background-color: #334155; color: white; font-weight: bold; padding: 7px 14px; border-radius: 5px;")
        btn_save.clicked.connect(self.save_report_to_file)

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("background-color: #475569; color: white; font-weight: bold; padding: 7px 20px; border-radius: 5px;")
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_copy)
        btn_box.addWidget(btn_save)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        return btn_box

    # -------------------------------------------------------------
    # Interactive Actions & Search
    # -------------------------------------------------------------
    def toggle_awtar_box(self):
        self.awtar_box.setVisible(not self.awtar_box.isVisible())

    def filter_awtar_authors(self, text):
        text = text.strip().lower()
        self.awtar_combo.clear()
        for item in getattr(self, "awtar_catalog_data", []):
            if not text or text in item.get('name', '').lower():
                self.awtar_combo.addItem(f"👤 {item.get('name')}", item.get('url'))

    def on_fetch_author_clicked(self):
        url = self.awtar_combo.currentData()
        author_name = self.awtar_combo.currentText()
        if not url:
            return
        self.search_input.setText(url)
        self.log_console.append(f"📚 اختيار «{author_name}» من دليل أوتار السماء... جاري استخراج كتبه:")
        self.on_search_clicked()

    def launch_autopilot_harvester(self):
        """Launches the dedicated Autopilot Harvester across all authors."""
        from modules.autopilot_harvester import AutopilotHarvesterDialog
        dlg = AutopilotHarvesterDialog(
            parent=self,
            library_root=self.library_root,
            project_id=self.project_id,
            authors=getattr(self, "awtar_catalog_data", []),
            initial_index=max(0, self.awtar_combo.currentIndex())
        )
        dlg.exec_()

    def jump_to_search(self, query):
        self.tabs.setCurrentIndex(2) # Switch to gap resolver tab
        self.search_input.setText(query)
        self.on_search_clicked()

    def on_search_clicked(self):
        q = self.search_input.text().strip()
        if not q:
            return

        # If user pasted the master catalog URL directly:
        if q.rstrip('/') in ["https://library.awtar-alsama.com/1", "http://library.awtar-alsama.com/1"]:
            self.awtar_box.setVisible(True)
            self.log_console.append("📖 تم التعرف على «الفهرس العام لمكتبة أوتار السماء» (82 مؤلفاً). تم فتح مستكشف المؤلفين بالأعلى، اختر المؤلف واضغط «جلب كافة كتب هذا المؤلف للجدول».")
            self.awtar_combo.setFocus()
            return
        
        self.btn_search.setEnabled(False)
        self.btn_search.setText("⏳ جاري البحث...")
        self.log_console.append(f"🔍 بدء فحص المستودعات الكنسية عن: «{q}»...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()

        self.s_thread = QThread()
        self.s_worker = SearchCandidatesWorker(q)
        self.s_worker.moveToThread(self.s_thread)

        self.s_thread.started.connect(self.s_worker.run)
        self.s_worker.results_ready.connect(self.on_candidates_ready)
        self.s_worker.error.connect(self.on_search_error)

        self.s_worker.results_ready.connect(self.s_thread.quit)
        self.s_worker.results_ready.connect(self.s_worker.deleteLater)
        self.s_worker.error.connect(self.s_thread.quit)
        self.s_worker.error.connect(self.s_worker.deleteLater)
        self.s_thread.finished.connect(self.s_thread.deleteLater)

        self.s_thread.start()

    def on_candidates_ready(self, candidates):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 فحص وبحث المستودعات")
        self.progress_bar.hide()
        self.current_candidates = candidates

        existing_count = sum(1 for c in candidates if c.get("local_status") == "EXISTING")
        gaps_count = len(candidates) - existing_count

        self.btn_download_all.setEnabled(bool(candidates))
        self.btn_download_all.setText(f"📥 تنزيل كافة النتائج ({len(candidates)})")

        self.btn_download_gaps.setEnabled(bool(gaps_count > 0))
        self.btn_download_gaps.setText(f"⭐ تنزيل الثغرات فقط ({gaps_count})")

        self.results_table.setRowCount(len(candidates))
        self.log_console.append(f"🧠 الفحص الذكي: تم العثور على {len(candidates)} مرجعاً ({existing_count} متوفر لديك بالفعل، {gaps_count} ثغرة حقيقية غير متوفرة).")

        for i, c in enumerate(candidates):
            it_title = QTableWidgetItem(c.get("title", ""))
            it_title.setForeground(Qt.white)
            
            it_source = QTableWidgetItem(c.get("source_badge", ""))

            # Local library ownership intelligence
            is_existing = (c.get("local_status") == "EXISTING")
            status_text = c.get("local_badge", "⭐ ثغرة مفقودة بالمكتبة")
            it_status = QTableWidgetItem(status_text)
            if is_existing:
                it_status.setForeground(Qt.green)
                it_status.setToolTip(f"متوفر محلياً: {c.get('local_file')}")
            else:
                it_status.setForeground(Qt.yellow)
                it_status.setToolTip("هذا الكتاب غير متوفر في رصيد مكتبتك، يوصى بتنزيله لسد الثغرة.")

            it_folder = QTableWidgetItem(f"/{c.get('target_folder', '')}")
            it_folder.setForeground(Qt.cyan)
            
            it_fmt = QTableWidgetItem(c.get("format", "PDF"))
            it_fmt.setForeground(Qt.yellow)

            self.results_table.setItem(i, 0, it_title)
            self.results_table.setItem(i, 1, it_source)
            self.results_table.setItem(i, 2, it_status)
            self.results_table.setItem(i, 3, it_folder)
            self.results_table.setItem(i, 4, it_fmt)

            btn_dl = QPushButton("✅ متوفر (إعادة تنزيل)" if is_existing else "📥 تنزيل وتسكين")
            btn_dl.setStyleSheet(f"""
                QPushButton {{
                    background-color: {"#1E293B" if is_existing else "#059669"};
                    color: {"#38BDF8" if is_existing else "white"};
                    font-weight: bold;
                    font-size: 11px;
                    padding: 3px 6px;
                    border-radius: 4px;
                    border: {"1px solid #475569" if is_existing else "none"};
                }}
                QPushButton:hover {{ background-color: {"#0284C7" if is_existing else "#10B981"}; color: white; }}
            """)
            btn_dl.clicked.connect(lambda ch, idx=i, btn=btn_dl: self.enqueue_download(self.current_candidates[idx], btn, idx))
            self.results_table.setCellWidget(i, 5, btn_dl)

    def on_search_error(self, err):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 فحص وبحث المستودعات")
        self.progress_bar.hide()
        self.log_console.append(f"❌ خطأ أثناء البحث: {err}")

    # -------------------------------------------------------------
    # Crash-Proof Queue-Based Download Engine (Multi-Download & Download All)
    # -------------------------------------------------------------
    def enqueue_download(self, candidate, button, index):
        """Enqueues a candidate book into the sequential download pipeline without thread collisions."""
        if is_valid_widget(button):
            if button.text() in ["✅ تم التسكين", "⏳ في الانتظار...", "📥 جاري التنزيل..."]:
                return
            try:
                button.setEnabled(False)
                button.setText("⏳ في الانتظار...")
                button.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
            except Exception:
                pass

        self.download_queue.append((candidate, button, index))
        self.total_queue_jobs += 1
        title = candidate.get("title", "")
        if is_valid_widget(self.log_console):
            self.log_console.append(f"📋 أُضيف «{title}» إلى طابور التنزيل (الترتيب: {len(self.download_queue)} في الانتظار).")

        if not self.is_downloading:
            self.process_next_download()

    def download_gaps_only(self):
        """Enqueues only genuine missing gaps, skipping existing volumes."""
        if not self.current_candidates:
            QMessageBox.information(self, "تنبيه", "لا توجد نتائج بحث متاحة حالياً.")
            return

        enqueued_count = 0
        for i, cand in enumerate(self.current_candidates):
            if cand.get("local_status") != "EXISTING":
                try:
                    btn = self.results_table.cellWidget(i, 5)
                    if is_valid_widget(btn) and btn.text() not in ["✅ تم التسكين", "⏳ في الانتظار...", "📥 جاري التنزيل..."]:
                        btn.setEnabled(False)
                        btn.setText("⏳ في الانتظار...")
                        btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
                        self.download_queue.append((cand, btn, i))
                        self.total_queue_jobs += 1
                        enqueued_count += 1
                except Exception:
                    pass

        if enqueued_count > 0:
            if is_valid_widget(self.log_console):
                self.log_console.append(f"\n⭐ تم إدراج {enqueued_count} ثغرة مفقودة فقط في طابور التنزيل والتسكين (تم استبعاد الكتب المتوفرة لديك).")
            if not self.is_downloading:
                self.process_next_download()
        else:
            if is_valid_widget(self.log_console):
                self.log_console.append("🎉 رائع! جميع الكتب المعروضة في النتائج متوفرة لديك بالفعل في رصيد مكتبتك أوفلاين.")

    def download_all_candidates(self):
        """Adds all available search results to the download queue and downloads them sequentially."""
        if not self.current_candidates:
            QMessageBox.information(self, "تنبيه", "لا توجد نتائج بحث متاحة للتنزيل حالياً.")
            return

        enqueued_count = 0
        for i in range(len(self.current_candidates)):
            try:
                btn = self.results_table.cellWidget(i, 5)
                if is_valid_widget(btn) and btn.text() not in ["✅ تم التسكين", "⏳ في الانتظار...", "📥 جاري التنزيل..."]:
                    cand = self.current_candidates[i]
                    try:
                        btn.setEnabled(False)
                        btn.setText("⏳ في الانتظار...")
                        btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
                    except Exception:
                        pass
                    self.download_queue.append((cand, btn, i))
                    self.total_queue_jobs += 1
                    enqueued_count += 1
            except Exception:
                pass

        if enqueued_count > 0:
            if is_valid_widget(self.log_console):
                self.log_console.append(f"\n🚀 انطلاق أمر تنزيل الكل: تم إدراج {enqueued_count} كتاباً في طابور التنزيل والتسكين التلقائي.")
            if is_valid_widget(self.btn_download_all):
                try:
                    self.btn_download_all.setEnabled(False)
                    self.btn_download_all.setText(f"⏳ جاري تنزيل الطابور ({enqueued_count})...")
                except Exception:
                    pass
            if not self.is_downloading:
                self.process_next_download()
        else:
            if is_valid_widget(self.log_console):
                self.log_console.append("ℹ️ كافة الكتب والنتائج مسكنة بالفعل في مكتبتك.")

    def process_next_download(self):
        """Processes the next item in the download queue sequentially."""
        if not self.download_queue:
            self.is_downloading = False
            if is_valid_widget(self.progress_bar):
                try:
                    self.progress_bar.hide()
                except Exception:
                    pass
            if is_valid_widget(self.btn_download_all):
                try:
                    self.btn_download_all.setEnabled(True)
                    self.btn_download_all.setText("📥 تنزيل كافة النتائج المتاحة (تنزيل الكل)")
                except Exception:
                    pass
            if self.total_queue_jobs > 0:
                if is_valid_widget(self.log_console):
                    self.log_console.append(f"\n🎉 اكتمل طابور التنزيل كاملاً بنجاح! تم تسكين وفهرسة {self.successful_jobs} من {self.total_queue_jobs} كتاباً في الهارد أوفلاين.")
                self.total_queue_jobs = 0
                self.completed_jobs = 0
                self.successful_jobs = 0
                if is_valid_widget(self):
                    self.refresh_audit()
            return

        self.is_downloading = True
        candidate, button, row_index = self.download_queue.pop(0)
        title = candidate.get("title", "كتاب")

        if is_valid_widget(button):
            try:
                button.setEnabled(False)
                button.setText("📥 جاري التنزيل...")
                button.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
            except Exception:
                pass

        if is_valid_widget(self.progress_bar):
            try:
                self.progress_bar.setRange(0, max(1, self.total_queue_jobs))
                self.progress_bar.setValue(self.completed_jobs)
                self.progress_bar.show()
            except Exception:
                pass

        if is_valid_widget(self.log_console):
            self.log_console.append(f"\n[{self.completed_jobs + 1}/{self.total_queue_jobs}] ⏳ جاري تنزيل وتسكين: «{title}» ...")

        thread = QThread()
        worker = DownloadBookWorker(candidate, self.library_root, project_id=self.project_id)
        worker.moveToThread(thread)

        thread_ref = (thread, worker)
        self.active_dl_threads.append(thread_ref)

        thread.started.connect(worker.run)
        if is_valid_widget(self.log_console):
            worker.log_emitted.connect(self.log_console.append)

        def _on_finished(ok, path, size):
            self.completed_jobs += 1
            if is_valid_widget(self.progress_bar):
                try:
                    self.progress_bar.setValue(self.completed_jobs)
                except Exception:
                    pass

            if ok:
                self.successful_jobs += 1
                if is_valid_widget(button):
                    try:
                        button.setText("✅ تم التسكين")
                        button.setStyleSheet("background-color: #0F766E; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
                    except (RuntimeError, Exception):
                        pass
                if is_valid_widget(self.log_console):
                    try:
                        self.log_console.append(f"  ✅ تم بنجاح تسكين: {title} ({size:,} بايت).")
                    except Exception:
                        pass
            else:
                if is_valid_widget(button):
                    try:
                        button.setEnabled(True)
                        button.setText("❌ فشل التنزيل")
                        button.setStyleSheet("background-color: #991B1B; color: white; font-weight: bold; font-size: 11px; border-radius: 4px;")
                    except (RuntimeError, Exception):
                        pass
                if is_valid_widget(self.log_console):
                    try:
                        self.log_console.append(f"  ❌ تعذر تنزيل: {title}.")
                    except Exception:
                        pass

            try:
                thread.quit()
                thread.wait()
            except Exception:
                pass

            try:
                self.active_dl_threads.remove(thread_ref)
            except Exception:
                pass

            # Proceed to next in queue
            if is_valid_widget(self):
                self.process_next_download()

        worker.finished.connect(_on_finished)
        worker.error.connect(lambda err: self.log_console.append(f"  ❌ خطأ: {err}") if is_valid_widget(self.log_console) else None)
        thread.start()

    def closeEvent(self, event):
        """Safely terminates background tasks when closing dialog."""
        self.download_queue.clear()
        for thread_ref in list(self.active_dl_threads):
            try:
                thread, worker = thread_ref
                thread.quit()
            except Exception:
                pass
        super().closeEvent(event)

    # -------------------------------------------------------------
    # Auto-Fill Gaps (Discipline & All)
    # -------------------------------------------------------------
    def start_auto_fill_discipline(self, discipline_key):
        self.tabs.setCurrentIndex(2) # Switch to console
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.log_console.append(f"\n🚀 بدء معالجة وسد ثغرات تخصص [{discipline_key}]...")

        self.af_thread = QThread()
        self.af_worker = GapResolveWorker("discipline", key=discipline_key, library_root=self.library_root, project_id=self.project_id)
        self.af_worker.moveToThread(self.af_thread)

        self.af_thread.started.connect(self.af_worker.run)
        self.af_worker.log_emitted.connect(self.log_console.append)
        self.af_worker.finished.connect(self.on_auto_fill_done)
        self.af_worker.error.connect(lambda e: self.log_console.append(f"❌ خطأ: {e}"))

        self.af_worker.finished.connect(self.af_thread.quit)
        self.af_worker.finished.connect(self.af_worker.deleteLater)
        self.af_worker.error.connect(self.af_thread.quit)
        self.af_worker.error.connect(self.af_worker.deleteLater)
        self.af_thread.finished.connect(self.af_thread.deleteLater)

        self.af_thread.start()

    def start_auto_fill_all(self):
        self.tabs.setCurrentIndex(2)
        self.btn_auto_fill_all.setEnabled(False)
        self.btn_auto_fill_all.setText("⏳ جاري سد الثغرات...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.log_console.append("\n🛡️ انطلاق العملية الكبرى لسد كافة ثغرات ونواقص مكتبة الصليب القبطية...")

        self.af_all_thread = QThread()
        self.af_all_worker = GapResolveWorker("all", library_root=self.library_root, project_id=self.project_id)
        self.af_all_worker.moveToThread(self.af_all_thread)

        self.af_all_thread.started.connect(self.af_all_worker.run)
        self.af_all_worker.log_emitted.connect(self.log_console.append)
        self.af_all_worker.finished.connect(self.on_auto_fill_all_done)
        self.af_all_worker.error.connect(lambda e: self.log_console.append(f"❌ خطأ: {e}"))

        self.af_all_worker.finished.connect(self.af_all_thread.quit)
        self.af_all_worker.finished.connect(self.af_all_worker.deleteLater)
        self.af_all_worker.error.connect(self.af_all_thread.quit)
        self.af_all_worker.error.connect(self.af_all_worker.deleteLater)
        self.af_all_thread.finished.connect(self.af_all_thread.deleteLater)

        self.af_all_thread.start()

    def on_auto_fill_done(self, count):
        self.progress_bar.hide()
        self.log_console.append(f"🏁 اكتملت معالجة التخصص: تمت إضافة {count} كتاباً جديداً بنجاح.")
        self.refresh_audit()

    def on_auto_fill_all_done(self, count):
        self.btn_auto_fill_all.setEnabled(True)
        self.btn_auto_fill_all.setText("🚀 سد كافة الثغرات تلقائياً")
        self.progress_bar.hide()
        self.log_console.append(f"🏆 اكتملت المهمة بنجاح! تم تسكين وفهرسة {count} كتاباً ومرجعاً جديداً.")
        self.refresh_audit()

    # -------------------------------------------------------------
    # Refresh & Export
    # -------------------------------------------------------------
    def refresh_audit(self):
        self.audit_data = library_auditor.analyze_library(
            library_root=self.library_root,
            project_id=self.project_id
        )
        score = self.audit_data.get("overall_health_score", 0)
        total_files = self.audit_data.get("total_files", 0)
        self.update_score_badge_style(score)
        self.sub_lbl.setText(f"إجمالي المحتويات المفهرسة: {total_files:,} كتاباً وملفاً • تقييم التغطية وفق معيار المراجع الكنسية الشاملة")
        
        # Re-populate tab 1 & 2
        new_cov = self.create_coverage_tab()
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, new_cov, "📈 مؤشرات التغطية اللاهوتية")

        new_recs = self.create_recommendations_tab()
        self.tabs.removeTab(1)
        self.tabs.insertTab(1, new_recs, "⚠️ المراجع والكتب الشاغرة (الموصى باقتنائها)")

    def copy_report_to_clipboard(self):
        md = library_auditor.generate_audit_markdown_report(self.audit_data)
        QApplication.clipboard().setText(md)
        QMessageBox.information(self, "تم النسخ", "تم نسخ تقرير الفحص والتدقيق بالكامل إلى الحافظة.")

    def save_report_to_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير التدقيق", "تقرير_تدقيق_المكتبة_الكنسية.md", "Markdown (*.md);;Text (*.txt)")
        if path:
            md = library_auditor.generate_audit_markdown_report(self.audit_data)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            QMessageBox.information(self, "تم الحفظ", f"تم حفظ التقرير بنجاح في:\n{path}")
