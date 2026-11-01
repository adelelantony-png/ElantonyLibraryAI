"""
Cross Coptic Library - Interactive Online Book Feeder Dialog (Ultra Pro Max)
Provides rich GUI interface for:
1. Curated Ecclesiastical Packs (Sunday School curricula, Servants preparation, Family counseling, Patristics, Apologetics)
2. Category-based feeding from CopticReads, Coptic-Treasures, and ChristianLib
3. Unified Smart Search & Download across online archives
With live log streaming, multi-threading, and auto-catalog updating.
"""

import os
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QTabWidget,
    QWidget,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from modules import online_book_feeder, library_organizer, web_intelligence

class FeederWorker(QObject):
    log_emitted = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, mode, params, library_root):
        super().__init__()
        self.mode = mode
        self.params = params
        self.library_root = library_root

    def run(self):
        try:
            downloaded = 0
            if self.mode == "curated_pack":
                pack_key = self.params.get("pack_key")
                downloaded = online_book_feeder.download_curated_pack(
                    self.library_root,
                    pack_key,
                    log_callback=self.log_emitted.emit
                )
            elif self.mode == "category":
                site = self.params.get("site")
                cat = self.params.get("category")
                max_books = self.params.get("max_books", 10)

                if site == "copticreads":
                    downloaded = online_book_feeder.sync_copticreads(
                        self.library_root,
                        max_books=max_books,
                        log_callback=self.log_emitted.emit
                    )
                elif site == "treasures":
                    downloaded = online_book_feeder.sync_coptic_treasures_category(
                        self.library_root,
                        category_slug=cat,
                        max_books=max_books,
                        log_callback=self.log_emitted.emit
                    )
                elif site == "christianlib":
                    downloaded = online_book_feeder.sync_christianlib_category(
                        self.library_root,
                        category_slug=cat,
                        max_books=max_books,
                        log_callback=self.log_emitted.emit
                    )
            elif self.mode == "search":
                query = self.params.get("query")
                max_books = self.params.get("max_books", 8)
                downloaded = online_book_feeder.search_and_download_online(
                    self.library_root,
                    query=query,
                    max_books=max_books,
                    log_callback=self.log_emitted.emit
                )
            elif self.mode == "drghaly":
                query = self.params.get("query")
                max_articles = self.params.get("max_articles", 5)
                self.log_emitted.emit(f"🔍 البحث في موسوعة د. غالي (drghaly.com) عن: «{query}»...")
                articles = web_intelligence.DrGhalyEngine.search_articles(query, limit=max_articles)
                if not articles:
                    self.log_emitted.emit("⚠️ لم يتم العثور على أبحاث مطابقة في موقع د. غالي.")
                else:
                    self.log_emitted.emit(f"📚 تم العثور على {len(articles)} بحثاً. جاري القراءة والتحويل والتسكين ككتب مرجعية...")
                    dest_dir = os.path.join(self.library_root, "03 - دراسات لاهوتية وعقائدية", "موسوعة أبحاث د. غالي للدفاعيات")
                    os.makedirs(dest_dir, exist_ok=True)
                    for idx, art in enumerate(articles, 1):
                        try:
                            self.log_emitted.emit(f"[{idx}/{len(articles)}] ⏳ قراءة وتنسيق: {art['title']}...")
                            art_data = web_intelligence.DrGhalyEngine.get_article_content(art["url"])
                            content = art_data.get("content", "")
                            if content:
                                safe_title = "".join(c for c in art["title"] if c not in r'\/:*?"<>|')[:75].strip()
                                doc_filename = f"بحث د. غالي - {safe_title}.docx"
                                doc_path = os.path.join(dest_dir, doc_filename)
                                web_intelligence.save_article_as_docx(art["title"], content, art["url"], doc_path)
                                self.log_emitted.emit(f"✅ تم حفظ وتسكين الكتاب المرجعي: {doc_filename}")
                                downloaded += 1
                        except Exception as art_err:
                            self.log_emitted.emit(f"⚠️ خطأ أثناء حفظ {art['title']}: {art_err}")

            # Update Excel catalog after feeding
            if downloaded > 0:
                self.log_emitted.emit("📊 جاري تحديث فهرس الإكسيل الشامل بالكتب الجديدة...")
                try:
                    library_organizer.update_library_excel_catalog(self.library_root)
                    self.log_emitted.emit("✅ تم تحديث فهرس الإكسيل بنجاح!")
                except Exception as ex:
                    self.log_emitted.emit(f"ملاحظة فهرس الإكسيل: {ex}")

            self.finished.emit(downloaded)
        except Exception as e:
            self.error.emit(str(e))

class OnlineFeederDialog(QDialog):
    def __init__(self, parent=None, library_root=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 منظومة التغذية الرقمية المباشرة وجلب الكتب الكنسية (Ultra Pro Max)")
        self.resize(960, 700)
        self.setLayoutDirection(Qt.RightToLeft)
        self.library_root = library_root
        self.worker_thread = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #14171F;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #D7DAE0;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QLabel {
                font-size: 13px;
                color: #E2E8F0;
                background-color: transparent;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #1E222A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
            QComboBox QAbstractItemView {
                background-color: #1E222A;
                color: #F8FAFC;
                selection-background-color: #282C34;
                selection-color: #E5C07B;
                border: 1px solid #334155;
            }
            QGroupBox {
                background-color: #181B22;
                border: 1px solid #2D323B;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 14px;
                font-weight: bold;
                color: #E5C07B;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: 14px;
                padding: 0 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(False)
        self.tabs.setLayoutDirection(Qt.RightToLeft)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2D323B;
                background: #181B22;
                border-radius: 8px;
                padding: 14px;
            }
            QTabBar::tab {
                background: #101217;
                color: #8B949E;
                padding: 0 14px;
                height: 38px;
                border: 1px solid #2D323B;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QTabBar::tab:selected {
                background: #181B22;
                color: #E5C07B;
                border-bottom: 3px solid #E5C07B;
            }
            QTabBar::tab:hover:!selected {
                background: #1C1F27;
                color: #E2E8F0;
            }
        """)

        # Tab 1: Curated Packs
        self.tab_packs = QWidget()
        self.setup_packs_tab()
        self.tabs.addTab(self.tab_packs, "باقات النهضة الكنسية الجاهزة")

        # Tab 2: Categorized Crawling
        self.tab_categories = QWidget()
        self.setup_categories_tab()
        self.tabs.addTab(self.tab_categories, "التغذية بالأقسام والمصادر")

        # Tab 3: Unified Smart Search
        self.tab_search = QWidget()
        self.setup_search_tab()
        self.tabs.addTab(self.tab_search, "البحث الذكي والتنزيل الفوري")

        # Tab 4: Dr. Ghaly Encyclopedia
        self.tab_drghaly = QWidget()
        self.setup_drghaly_tab()
        self.tabs.addTab(self.tab_drghaly, "موسوعة د. غالي (Holy_Bible_1)")

        main_layout.addWidget(self.tabs, 0)

        # Live Log Console
        log_group = QGroupBox("📜 سجل المتابعة والتحميل والتسكين المباشر")
        log_layout = QVBoxLayout(log_group)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #0E1015;
                color: #38BDF8;
                border: 1px solid #252830;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                line-height: 1.6;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_display)
        main_layout.addWidget(log_group, 1)

        # Footer Buttons
        footer_layout = QHBoxLayout()
        self.lbl_status = QLabel("جاهز للعمل")
        self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold;")
        footer_layout.addWidget(self.lbl_status, 1)

        btn_close = QPushButton("إغلاق النافذة")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                padding: 6px 18px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        main_layout.addLayout(footer_layout)

    def setup_packs_tab(self):
        self.tab_packs.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.tab_packs)
        layout.setSpacing(10)

        lbl = QLabel("اختر باقة تخصصية جاهزة ليقوم النظام بتنزيل كتبها وتسكينها في مجلداتها المحددة تلقائياً:")
        lbl.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 500;")
        layout.addWidget(lbl)

        self.pack_combo = QComboBox()
        self.pack_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                font-weight: bold;
                background-color: #14171F;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
            }
        """)
        for k, v in online_book_feeder.CURATED_PACKS.items():
            self.pack_combo.addItem(f"{v['title']} ({len(v['books'])} كتب)", k)
        self.pack_combo.currentIndexChanged.connect(self.on_pack_changed)
        layout.addWidget(self.pack_combo)

        self.lbl_pack_desc = QLabel()
        self.lbl_pack_desc.setWordWrap(True)
        self.lbl_pack_desc.setStyleSheet("color: #94A3B8; font-style: italic; padding: 4px 0; font-size: 12px;")
        layout.addWidget(self.lbl_pack_desc)
        self.on_pack_changed(0)

        self.btn_pack_dl = QPushButton("🚀 بدء تنزيل وتسكين الباقة المختارة")
        self.btn_pack_dl.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                padding: 6px 18px;
                border: 1px solid #10B981;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #10B981; }
            QPushButton:disabled { background-color: #374151; border-color: #374151; color: #9CA3AF; }
        """)
        self.btn_pack_dl.clicked.connect(self.start_pack_download)
        layout.addWidget(self.btn_pack_dl)

    def on_pack_changed(self, idx):
        pack_key = self.pack_combo.currentData()
        if pack_key in online_book_feeder.CURATED_PACKS:
            pack = online_book_feeder.CURATED_PACKS[pack_key]
            self.lbl_pack_desc.setText(f"📌 {pack['desc']}")

    def setup_categories_tab(self):
        self.tab_categories.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.tab_categories)
        layout.setSpacing(10)

        row1 = QHBoxLayout()
        lbl_s = QLabel("الموقع المصدر:")
        lbl_s.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: bold;")
        row1.addWidget(lbl_s)
        self.cat_site_combo = QComboBox()
        self.cat_site_combo.addItem("🌟 مشروع الكنوز القبطية (Coptic-Treasures)", "treasures")
        self.cat_site_combo.addItem("📚 مكتبة الكتب المسيحية (ChristianLib)", "christianlib")
        self.cat_site_combo.addItem("📖 مكتبة الكتب القبطية (Coptic Reads)", "copticreads")
        self.cat_site_combo.currentIndexChanged.connect(self.on_cat_site_changed)
        row1.addWidget(self.cat_site_combo, 1)

        lbl_c = QLabel("عدد الكتب:")
        lbl_c.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: bold;")
        row1.addWidget(lbl_c)
        self.cat_count_spin = QSpinBox()
        self.cat_count_spin.setRange(1, 100)
        self.cat_count_spin.setValue(10)
        row1.addWidget(self.cat_count_spin)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.lbl_cat = QLabel("القسم التخصصي:")
        self.lbl_cat.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: bold;")
        row2.addWidget(self.lbl_cat)
        self.cat_choice_combo = QComboBox()
        row2.addWidget(self.cat_choice_combo, 1)
        layout.addLayout(row2)

        self.btn_cat_dl = QPushButton("🚀 بدء الجلب والتسكين للقسم المحدد")
        self.btn_cat_dl.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                padding: 6px 18px;
                border: 1px solid #3B82F6;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3B82F6; }
            QPushButton:disabled { background-color: #374151; border-color: #374151; color: #9CA3AF; }
        """)
        self.btn_cat_dl.clicked.connect(self.start_category_download)
        layout.addWidget(self.btn_cat_dl)

        self.on_cat_site_changed(0)

    def on_cat_site_changed(self, idx):
        site = self.cat_site_combo.currentData()
        self.cat_choice_combo.clear()

        if site == "treasures":
            self.lbl_cat.show()
            self.cat_choice_combo.show()
            self.cat_choice_combo.addItem("🎒 مناهج التربية الكنسية (Sunday School Curriculums)", "sunday-school-curriculums")
            self.cat_choice_combo.addItem("💡 خدمة مدارس الأحد والتربية (Sunday School Service)", "sunday-school-service")
            self.cat_choice_combo.addItem("🕊️ الأسرة المسيحية والمشورة (Christian Family)", "the-christian-family")
            self.cat_choice_combo.addItem("📜 أقوال الآباء والباترولوجي (Patrology)", "patrology")
            self.cat_choice_combo.addItem("🛡️ العقيدة واللاهوت (Doctrine)", "doctrine")
            self.cat_choice_combo.addItem("⛪ قوانين الكنيسة (Church Canon)", "church-canon")
            self.cat_choice_combo.addItem("🕯️ الطقوس القبطية (Coptic Rites)", "coptic-rites-ritual-theology")
            self.cat_choice_combo.addItem("📖 الكتاب المقدس وتفاسيره (Bible)", "bible")
            self.cat_choice_combo.addItem("🏛️ تاريخ الكنيسة (History)", "history")
        elif site == "christianlib":
            self.lbl_cat.show()
            self.cat_choice_combo.show()
            self.cat_choice_combo.addItem("🎒 التربية والخدمة (مناهج وكتب)", "التربية-و-الخدمة-تحميل-pdf")
            self.cat_choice_combo.addItem("🧑‍🤝‍🧑 كتب الشباب والشبابيات", "شبابيات")
            self.cat_choice_combo.addItem("💡 الإعداد للخدمة", "الاعداد-للخدمة")
            self.cat_choice_combo.addItem("🛡️ اللاهوت الدفاعي (Apologetics)", "دفاعيات-apologetics")
            self.cat_choice_combo.addItem("📜 أقوال الآباء (آبائيات)", "ابائيات")
            self.cat_choice_combo.addItem("⛪ كتب لاهوت وعقيدة مسيحية", "كتب-لاهوت-وعقيدة-مسيحية-pdf")
            self.cat_choice_combo.addItem("🕊️ المقبلين على الزواج والمتزوجين", "المقبلين-على-الزواج-و-المتزوجين")
            self.cat_choice_combo.addItem("🏛️ تاريخ الكنيسة", "تاريخ-الكنيسة")
        else: # copticreads
            self.lbl_cat.hide()
            self.cat_choice_combo.hide()

    def setup_search_tab(self):
        self.tab_search.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.tab_search)
        layout.setSpacing(10)

        lbl = QLabel("اكتب كلمة البحث (مثال: أثناسيوس، مدارس الأحد، الإلحاد، الأنبا موسى، كيرلس الكبير):")
        lbl.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 500;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("أدخل كلمة أو موضوع البحث هنا...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                font-size: 13px;
                background-color: #14171F;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
        """)
        row.addWidget(self.search_input, 1)

        lbl_max = QLabel("الحد الأقصى:")
        lbl_max.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: bold;")
        row.addWidget(lbl_max)
        self.search_count_spin = QSpinBox()
        self.search_count_spin.setRange(1, 30)
        self.search_count_spin.setValue(8)
        row.addWidget(self.search_count_spin)
        layout.addLayout(row)

        self.btn_search_dl = QPushButton("🔍 بحث فوري وتنزيل وتسكين النتائج")
        self.btn_search_dl.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                padding: 6px 18px;
                border: 1px solid #F59E0B;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #F59E0B; }
            QPushButton:disabled { background-color: #374151; border-color: #374151; color: #9CA3AF; }
        """)
        self.btn_search_dl.clicked.connect(self.start_search_download)
        layout.addWidget(self.btn_search_dl)

    def setup_drghaly_tab(self):
        self.tab_drghaly.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.tab_drghaly)
        layout.setSpacing(10)

        # Info Box
        info_box = QGroupBox("🏛️ موسوعة وأبحاث د. غالي الدفاعية (drghaly.com - Holy_Bible_1)")
        ib_layout = QVBoxLayout(info_box)
        lbl_info = QLabel(
            "بحث فوري في أكثر من 16,000 مقال وبحث دفاعي ونصي وعلمي للدكتور غالي، "
            "مع تحويلها آلياً إلى كتب ومراجع Word (.docx) منسقة بالصليب وتسكينها مباشرة في قسم "
            "«03 - دراسات لاهوتية وعقائدية / موسوعة أبحاث د. غالي» وتكشيفها في مكتبتك."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.6;")
        ib_layout.addWidget(lbl_info)
        layout.addWidget(info_box)

        # Search Controls
        lbl_search = QLabel("اكتب موضوع أو شبهة للبحث عنها في أبحاث د. غالي:")
        lbl_search.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 500;")
        layout.addWidget(lbl_search)

        row = QHBoxLayout()
        self.drghaly_input = QLineEdit()
        self.drghaly_input.setPlaceholderText("مثال: النقد النصي، عمر الأرض، الرد على التطور، الثالوث، مخطوطات...")
        row.addWidget(self.drghaly_input, 1)

        lbl_max = QLabel("عدد الأبحاث:")
        lbl_max.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: bold;")
        row.addWidget(lbl_max)
        self.drghaly_count_spin = QSpinBox()
        self.drghaly_count_spin.setRange(1, 15)
        self.drghaly_count_spin.setValue(5)
        row.addWidget(self.drghaly_count_spin)
        layout.addLayout(row)

        # Quick preset buttons row
        presets_box = QGroupBox("⚡ مواضيع جاهزة شائعة في موسوعة د. غالي:")
        pb_layout = QHBoxLayout(presets_box)
        pb_layout.setSpacing(6)
        
        quick_presets = [
            ("النقد النصي والمخطوطات", "النقد النصي"),
            ("الرد على التطور والداروينية", "التطور"),
            ("الثالوث والتوحيد", "الثالوث"),
            ("صلب المسيح وقيامته", "صلب المسيح"),
            ("أصالة نبوات العهد القديم", "نبوات المسيح")
        ]
        for label, term in quick_presets:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E222A;
                    color: #38BDF8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #282C34;
                    color: #E5C07B;
                }
            """)
            btn.clicked.connect(lambda checked, t=term: self.drghaly_input.setText(t))
            pb_layout.addWidget(btn)
            
        layout.addWidget(presets_box)

        self.btn_drghaly_dl = QPushButton("📥 جلب وتسكين أبحاث د. غالي ككتب مرجعية في المكتبة")
        self.btn_drghaly_dl.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                padding: 6px 18px;
                border: 1px solid #38BDF8;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #0369A1; }
            QPushButton:disabled { background-color: #374151; border-color: #374151; color: #9CA3AF; }
        """)
        self.btn_drghaly_dl.clicked.connect(self.start_drghaly_download)
        layout.addWidget(self.btn_drghaly_dl)

    def append_log(self, text):
        self.log_display.append(text)
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )

    def set_ui_busy(self, busy=True):
        self.tabs.setEnabled(not busy)
        self.btn_pack_dl.setEnabled(not busy)
        self.btn_cat_dl.setEnabled(not busy)
        self.btn_search_dl.setEnabled(not busy)
        self.btn_drghaly_dl.setEnabled(not busy)
        if busy:
            self.lbl_status.setText("⏳ جاري العمل والتنزيل المباشر...")
            self.lbl_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        else:
            self.lbl_status.setText("جاهز للعمل")
            self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold;")

    def show_custom_message(self, title, message, is_error=False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setLayoutDirection(Qt.RightToLeft)
        if is_error:
            msg.setIcon(QMessageBox.Critical)
            btn_color = "#DC2626"
            btn_hover = "#B91C1C"
        else:
            msg.setIcon(QMessageBox.Information)
            btn_color = "#059669"
            btn_hover = "#10B981"

        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: #14171F;
                border: 1px solid #334155;
                border-radius: 8px;
            }}
            QLabel {{
                color: #F8FAFC !important;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
                font-size: 13px;
                font-weight: 500;
                min-width: 320px;
                padding: 10px;
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {btn_color};
                color: #FFFFFF !important;
                border: none;
                border-radius: 6px;
                padding: 7px 24px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        msg.exec_()

    def start_pack_download(self):
        if not self.library_root:
            self.show_custom_message("تنبيه", "يرجى فتح وتحديد مجلد مكتبتك أولاً.", is_error=True)
            return

        pack_key = self.pack_combo.currentData()
        self.set_ui_busy(True)
        self.append_log(f"\n--- بدء تنزيل الباقة: {self.pack_combo.currentText()} ---")

        self._launch_worker("curated_pack", {"pack_key": pack_key})

    def start_category_download(self):
        if not self.library_root:
            self.show_custom_message("تنبيه", "يرجى فتح وتحديد مجلد مكتبتك أولاً.", is_error=True)
            return

        site = self.cat_site_combo.currentData()
        cat = self.cat_choice_combo.currentData()
        max_b = self.cat_count_spin.value()

        self.set_ui_busy(True)
        self.append_log(f"\n--- بدء تغذية القسم: {self.cat_choice_combo.currentText()} ({max_b} كتب) ---")

        self._launch_worker("category", {"site": site, "category": cat, "max_books": max_b})

    def start_search_download(self):
        if not self.library_root:
            self.show_custom_message("تنبيه", "يرجى فتح وتحديد مجلد مكتبتك أولاً.", is_error=True)
            return

        q = self.search_input.text().strip()
        if not q:
            self.show_custom_message("تنبيه", "يرجى إدخال كلمة البحث أولاً.", is_error=True)
            return

        max_b = self.search_count_spin.value()
        self.set_ui_busy(True)
        self.append_log(f"\n--- بدء البحث والتنزيل الفوري عن: «{q}» ({max_b} كتب) ---")

        self._launch_worker("search", {"query": q, "max_books": max_b})

    def start_drghaly_download(self):
        if not self.library_root:
            self.show_custom_message("تنبيه", "يرجى فتح وتحديد مجلد مكتبتك أولاً.", is_error=True)
            return

        q = self.drghaly_input.text().strip()
        if not q:
            self.show_custom_message("تنبيه", "يرجى إدخال كلمة أو موضوع البحث في أبحاث د. غالي أولاً.", is_error=True)
            return

        max_a = self.drghaly_count_spin.value()
        self.set_ui_busy(True)
        self.append_log(f"\n--- بدء جلب أبحاث د. غالي عن: «{q}» ({max_a} أبحاث) وتسكينها في المكتبة ---")

        self._launch_worker("drghaly", {"query": q, "max_articles": max_a})

    def _launch_worker(self, mode, params):
        self.worker_thread = QThread()
        self.worker = FeederWorker(mode, params, self.library_root)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_emitted.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_finished(self, count):
        self.set_ui_busy(False)
        self.append_log(f"\n🎉 تمت العملية بنجاح! تم استيراد وتسكين وفهرسة {count} كتاباً في مكتبتك.")
        self.show_custom_message(
            "اكتملت العملية",
            f"تم جلب وتسكين {count} كتاباً جديداً وفهرستها في مكتبتك بنجاح! ✅"
        )

    def on_error(self, err_msg):
        self.set_ui_busy(False)
        self.append_log(f"\n❌ حدث خطأ: {err_msg}")
        self.show_custom_message("خطأ", f"حدث خطأ أثناء العملية: {err_msg}", is_error=True)
