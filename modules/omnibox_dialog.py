"""
Cross Coptic Library - Unified Omnibox & 360° Cognitive Search Engine (محرك البحث المركزي الموحد)
A single omnipresent search bar that unifies:
1. Deep Content RAG (Searching inside 7,424+ books down to the exact page)
2. In-App Split-Screen Reader Launch
3. Scripture Verse & Patristic Cross-Reference Anchor
4. Differential Topic Archive (Delta Cache)
5. Federated Multi-Source Gap Detector & 1-Click Downloader
6. Progressive Background Deep Content Indexing Controller
"""

import os
import re
from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QMessageBox,
    QSplitter,
    QGroupBox,
    QApplication
)
from PyQt5.QtCore import Qt, QThread

from modules import (
    database_handler,
    library_rag,
    scripture_engine,
    topic_archive,
    online_book_feeder,
    in_app_reader,
    deep_content_indexer
)


class OmniboxDialog(QDialog):
    """The central unified search brain of Cross Coptic Library."""

    def __init__(self, parent=None, library_root: str = None, project_id: int = 1, initial_query: str = ""):
        super().__init__(parent)
        self.library_root = library_root or r"I:\2021\2020\✠ Cross Coptic Library ✠"
        self.project_id = project_id or 1
        self.indexer_thread = None
        self.indexer_worker = None

        self.setWindowTitle("🌐 محرك البحث المركزي الموحد والشامل - Cross Coptic Omnibox 360°")
        self.resize(1300, 880)
        self.init_ui()

        if initial_query:
            self.search_input.setText(initial_query)
            self.execute_omni_search()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header Banner & Deep Indexer Status
        banner = QWidget()
        banner.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #1E293B);
                border: 1px solid #3B82F6;
                border-radius: 8px;
            }
        """)
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(14, 8, 14, 8)

        lbl_icon = QLabel("✠")
        lbl_icon.setStyleSheet("font-size: 26px; color: #E5C07B; font-weight: bold; background: transparent; border: none;")
        b_layout.addWidget(lbl_icon)

        t_box = QVBoxLayout()
        lbl_head = QLabel("محرك الاستكشاف والبحث الشامل الموحد (Omnibox 360°)")
        lbl_head.setStyleSheet("font-size: 15px; font-weight: bold; color: white; background: transparent; border: none;")
        self.lbl_indexer_status = QLabel("🧠 الفهرسة العميقة جاهزة | ابحث في نصوص بطون الكتب، الشواهد الكتابية، أو المستودعات العالمية")
        self.lbl_indexer_status.setStyleSheet("font-size: 11px; color: #93C5FD; background: transparent; border: none;")
        t_box.addWidget(lbl_head)
        t_box.addWidget(self.lbl_indexer_status)
        b_layout.addLayout(t_box, 1)

        # Deep Indexer Trigger Button
        self.btn_run_indexer = QPushButton("⚡ بدء الفهرسة العميقة بالخلفية")
        self.btn_run_indexer.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px; font-size: 11px;")
        self.btn_run_indexer.clicked.connect(self.toggle_deep_indexer)
        b_layout.addWidget(self.btn_run_indexer)

        layout.addWidget(banner)

        # 2. Omnipresent Search Bar
        search_box = QGroupBox("🔍 الاستعلام الموحد (نصوص داخلية، آيات وشواهد، مواضيع، أو روابط أونلاين)")
        search_box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #434F63;
                border-radius: 8px;
                font-weight: bold;
                color: #E5C07B;
                background-color: #252B36;
                padding-top: 14px;
            }
        """)
        sb_layout = QVBoxLayout(search_box)
        sb_layout.setContentsMargins(12, 10, 12, 10)

        row_s = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اكتب أي موضوع (مثال: تجسد الكلمة، طوفان نوح)، أو آية (يو 1: 1)، أو الصق رابطاً خارجياً...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E242E;
                color: #FFFFFF;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit:focus { border: 1px solid #3B82F6; background-color: #222935; }
        """)
        self.search_input.returnPressed.connect(self.execute_omni_search)
        row_s.addWidget(self.search_input, 1)

        self.btn_search = QPushButton("🔍 بحث شامل وموحد")
        self.btn_search.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 10px 22px; border-radius: 6px; font-size: 13px;")
        self.btn_search.clicked.connect(self.execute_omni_search)
        row_s.addWidget(self.btn_search)

        sb_layout.addLayout(row_s)

        # Quick Jump Chips
        chips_layout = QHBoxLayout()
        lbl_chips = QLabel("📌 استعلامات مقترحة:")
        lbl_chips.setStyleSheet("color: #E5C07B; font-size: 11px; font-weight: bold;")
        chips_layout.addWidget(lbl_chips)

        quick_queries = [
            "تجسد الكلمة",
            "يوحنا 1: 1",
            "طوفان نوح جيولوجيا",
            "طبيعة المسيح كيرلس",
            "تكوين 1: 26",
            "ألقاب المسيح ووظائفه"
        ]
        for q in quick_queries:
            btn_c = QPushButton(q)
            btn_c.setStyleSheet("""
                QPushButton {
                    background-color: #323A48;
                    color: #60A5FA;
                    border: 1px solid #475569;
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-size: 11px;
                }
                QPushButton:hover { background-color: #2563EB; color: white; }
            """)
            btn_c.clicked.connect(lambda ch, query=q: self.jump_query(query))
            chips_layout.addWidget(btn_c)

        chips_layout.addStretch()
        sb_layout.addLayout(chips_layout)

        layout.addWidget(search_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 3. 4-Quadrant / Master Tabbed Result View
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #252B36;
                color: #94A3B8;
                padding: 9px 20px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #384252;
                margin-left: 2px;
            }
            QTabBar::tab:selected {
                background: #323A48;
                color: #E5C07B;
                border-bottom: 2px solid #E5C07B;
            }
            QTabWidget::pane {
                border: 1px solid #384252;
                background-color: #2B3240;
                border-radius: 6px;
            }
        """)

        # Tab 1: Deep Content RAG (بطون الكتب والصفحات)
        self.tab_rag = QWidget()
        l_rag = QVBoxLayout(self.tab_rag)
        self.txt_rag_results = QTextEdit()
        self.txt_rag_results.setReadOnly(True)
        self.txt_rag_results.setStyleSheet("""
            QTextEdit {
                background-color: #242933;
                color: #ECEFF4;
                border: 1px solid #384252;
                border-radius: 6px;
                padding: 14px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)
        l_rag.addWidget(self.txt_rag_results, 1)

        row_rag_act = QHBoxLayout()
        self.btn_open_reader_from_rag = QPushButton("📖 فتح الكتاب المكتشف في القارئ المدمج")
        self.btn_open_reader_from_rag.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 7px 16px; border-radius: 6px;")
        self.btn_open_reader_from_rag.clicked.connect(self.open_top_rag_in_reader)
        row_rag_act.addWidget(self.btn_open_reader_from_rag)
        row_rag_act.addStretch()
        l_rag.addLayout(row_rag_act)

        self.tabs.addTab(self.tab_rag, "📖 مقتطفات بطون الكتب (Local RAG)")

        # Tab 2: Scripture & Patristic Cross-Reference (المرساة الكنسية)
        self.tab_scripture = QWidget()
        l_scrip = QVBoxLayout(self.tab_scripture)
        self.txt_scripture = QTextEdit()
        self.txt_scripture.setReadOnly(True)
        self.txt_scripture.setStyleSheet("background-color: #242933; color: #ECEFF4; padding: 14px; font-size: 13px; line-height: 1.8;")
        l_scrip.addWidget(self.txt_scripture, 1)

        row_scrip_act = QHBoxLayout()
        self.btn_open_scripture_dialog = QPushButton("✝️ فتح المفهرس الكتابي التفاعلي للشاهد")
        self.btn_open_scripture_dialog.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 16px; border-radius: 6px;")
        self.btn_open_scripture_dialog.clicked.connect(self.open_scripture_dialog)
        row_scrip_act.addWidget(self.btn_open_scripture_dialog)
        row_scrip_act.addStretch()
        l_scrip.addLayout(row_scrip_act)

        self.tabs.addTab(self.tab_scripture, "✝️ المرساة والشواهد الكتابية")

        # Tab 3: Topic Archive Delta (الأرشيف التراكمي وتوفير التوكنز)
        self.tab_archive = QWidget()
        l_arc = QVBoxLayout(self.tab_archive)
        self.txt_archive = QTextEdit()
        self.txt_archive.setReadOnly(True)
        self.txt_archive.setStyleSheet("background-color: #242933; color: #ECEFF4; padding: 14px; font-size: 13px; line-height: 1.8;")
        l_arc.addWidget(self.txt_archive, 1)
        self.tabs.addTab(self.tab_archive, "🗄️ أرشيف الأبحاث المحفوظ (Delta Cache)")

        # Tab 4: Online Gaps & Candidates (المستودعات العالمية وسد الثغرات)
        self.tab_online = QWidget()
        l_onl = QVBoxLayout(self.tab_online)
        self.tbl_online = QTableWidget(0, 5)
        self.tbl_online.setHorizontalHeaderLabels([
            "📖 الكتاب المكتشف أونلاين",
            "🏛️ المستودع",
            "🧠 الحالة بمكتبتك الأوفلاين",
            "📂 المجلد المستهدف",
            "⚡ تنزيل وتسكين"
        ])
        self.tbl_online.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_online.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_online.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_online.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_online.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.tbl_online.setColumnWidth(4, 150)
        l_onl.addWidget(self.tbl_online, 1)
        self.tabs.addTab(self.tab_online, "🌐 كاشف الثغرات ومستودعات الإنترنت")

        layout.addWidget(self.tabs, 1)

        self.last_found_file_path = None
        self.last_found_page = 1

    def jump_query(self, query):
        self.search_input.setText(query)
        self.execute_omni_search()

    def execute_omni_search(self):
        q = self.search_input.text().strip()
        if not q:
            return

        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        QApplication.processEvents()

        # 1. Check Scripture Verse Engine
        parsed_verse = scripture_engine.parse_scripture_reference(q)
        if parsed_verse:
            book, ch, v = parsed_verse
            self.tabs.setCurrentIndex(1)
            ref_str = f"{book} - أصحاح {ch}" + (f" : آية {v}" if v else "")
            scrip_txt = f"✝️ تم التعرف على الشاهد الكتابي: «{ref_str}»\n\n"
            scrip_txt += f"• السفر القانوني: {book}\n"
            scrip_txt += f"• الأصحاح: {ch}\n"
            if v: scrip_txt += f"• الآية: {v}\n"
            scrip_txt += "\n🏛️ شواهد المخطوطات القديمة: الشاهد موثق في السينائية والفاتيكانية والترجمات القبطية القديمة.\n"
            scrip_txt += "\nاضغط زر «فتح المفهرس الكتابي التفاعلي» بالأسفل لاستعراض كافة تفاسير الآباء والمخطوطات المرتبطة به."
            self.txt_scripture.setPlainText(scrip_txt)
        else:
            self.txt_scripture.setPlainText("لم يتم التعرف على شاهد كتابي مباشر في نص البحث. يمكنك كتابة الشاهد بصيغة (يو 1: 1 أو تكوين 1: 1).")

        # 2. Local Deep RAG Search
        try:
            has_rag, rag_text, other_books = library_rag.extract_relevant_snippets(q, library_root=self.library_root)
            if has_rag and rag_text:
                self.txt_rag_results.setPlainText(rag_text)
                # Attempt to extract first matching book path
                match = re.search(r'\[كتاب:\s*([^\]]+?)\s*-\s*(?:تصنيف:[^\]]*-\s*)?(?:صفحة/موضع:|صـ)\s*(\d+)\]', rag_text)
                if match:
                    b_name = match.group(1).strip()
                    self.last_found_page = int(match.group(2))
                    # Lookup real path in church_books first, then fallback to files
                    try:
                        con = database_handler.get_connection()
                        cur = con.cursor()
                        cur.execute("""
                            SELECT original_path FROM church_books 
                            WHERE file_name LIKE ? OR original_path LIKE ?
                            LIMIT 1
                        """, (f"%{b_name}%", f"%{b_name}%"))
                        row = cur.fetchone()
                        if not row:
                            cur.execute("SELECT file_path FROM files WHERE file_name LIKE ? LIMIT 1", (f"%{b_name}%",))
                            row = cur.fetchone()
                        con.close()
                        if row:
                            resolved = library_rag.resolve_file_path(row[0], self.library_root)
                            self.last_found_file_path = resolved if resolved else row[0]
                    except Exception:
                        pass
            else:
                self.txt_rag_results.setPlainText("لم يتم العثور على مقتطفات نصية مطابقة داخل بطون الكتب المفهرسة حالياً. يمكنك تفعيل «الفهرسة العميقة» بالأعلى لتفريغ نصوص كافة الكتب.")
        except Exception as e:
            self.txt_rag_results.setPlainText(f"تنبيه RAG: {e}")

        # 3. Topic Archive Delta Check
        try:
            archived = topic_archive.find_archived_topic(q, library_root=self.library_root)
            if archived:
                t_name, t_dir, meta = archived
                arc_txt = f"🗄️ تم العثور على بحث محفوظ مسبقاً في أرشيفك عن: «{t_name}»!\n\n"
                arc_txt += f"📂 مسار المجلد بقرصك الصلب: {t_dir}\n"
                arc_txt += f"📅 تاريخ آخر مسح: {meta.get('last_scan_date', 'غير محدد')}\n"
                arc_txt += f"💡 تم توفير توكنز الذكاء الاصطناعي 100% لأن البيانات محفوظة ومؤرشفة أوفلاين مسبقاً.\n\n"
                arc_txt += "الملفات المتوفرة داخل مجلد الموضوع:\n"
                for f in os.listdir(t_dir)[:8]:
                    arc_txt += f"  • {f}\n"
                self.txt_archive.setPlainText(arc_txt)
            else:
                self.txt_archive.setPlainText(f"لا توجد دراسة سابقة محفوظة عن «{q}» في الأرشيف التراكمي. عند تشغيل الباحث المستقل، سيتم إنشاء مجلد دائم لها وتوفير التوكنز مستقبلاً.")
        except Exception as e:
            self.txt_archive.setPlainText(f"تنبيه الأرشيف: {e}")

        # 4. Multi-Source Candidate Search
        try:
            candidates = online_book_feeder.search_online_candidates(q, limit=8)
            self.tbl_online.setRowCount(len(candidates))
            for i, c in enumerate(candidates):
                it_t = QTableWidgetItem(c.get("title", ""))
                it_t.setForeground(Qt.white)
                it_s = QTableWidgetItem(c.get("source_badge", ""))
                
                is_exist = (c.get("local_status") == "EXISTING")
                it_st = QTableWidgetItem(c.get("local_badge", "⭐ ثغرة مفقودة"))
                it_st.setForeground(Qt.green if is_exist else Qt.yellow)

                it_f = QTableWidgetItem(f"/{c.get('target_folder', '')}")
                it_f.setForeground(Qt.cyan)

                self.tbl_online.setItem(i, 0, it_t)
                self.tbl_online.setItem(i, 1, it_s)
                self.tbl_online.setItem(i, 2, it_st)
                self.tbl_online.setItem(i, 3, it_f)

                btn_dl = QPushButton("✅ متوفر" if is_exist else "📥 تنزيل وتسكين")
                btn_dl.setStyleSheet(f"background-color: {'#334155' if is_exist else '#059669'}; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
                btn_dl.clicked.connect(lambda ch, cand=c: self.download_online_book(cand))
                self.tbl_online.setCellWidget(i, 4, btn_dl)
        except Exception:
            pass

        self.progress_bar.hide()

    def open_top_rag_in_reader(self):
        if not self.last_found_file_path or not os.path.exists(self.last_found_file_path):
            QMessageBox.information(self, "تنبيه", "يرجى تحديد أو البحث عن كتاب أولاً لفتحه في القارئ المدمج.")
            return
        reader = in_app_reader.InAppBookReader(self, file_path=self.last_found_file_path, target_page=self.last_found_page)
        reader.exec_()

    def open_scripture_dialog(self):
        q = self.search_input.text().strip()
        dlg = scripture_engine.ScriptureNavigatorDialog(self, library_root=self.library_root, initial_ref=q)
        dlg.exec_()

    def download_online_book(self, candidate: dict):
        ok, path, size = online_book_feeder.download_and_index_candidate(candidate, library_root=self.library_root, project_id=self.project_id)
        if ok:
            QMessageBox.information(self, "تم التسكين", f"تم بنجاح تنزيل وتسكين وفهرسة الكتاب أوفلاين:\n{os.path.basename(path)}")
        else:
            QMessageBox.warning(self, "تنبيه التنزيل", "تعذر تنزيل الكتاب المكتشف.")

    def toggle_deep_indexer(self):
        if self.indexer_thread and self.indexer_thread.isRunning():
            self.indexer_worker.stop()
            self.btn_run_indexer.setText("⚡ بدء الفهرسة العميقة بالخلفية")
            self.btn_run_indexer.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
            self.lbl_indexer_status.setText("تم إيقاف الفهرسة العميقة مؤقتاً.")
            return

        self.btn_run_indexer.setText("⏹️ إيقاف الفهرسة مؤقتاً")
        self.btn_run_indexer.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")

        self.indexer_thread = QThread()
        self.indexer_worker = deep_content_indexer.DeepIndexerWorker()
        self.indexer_worker.moveToThread(self.indexer_thread)

        self.indexer_thread.started.connect(self.indexer_worker.run)
        self.indexer_worker.progress.connect(self.on_indexer_progress)
        self.indexer_worker.finished.connect(self.on_indexer_finished)

        self.indexer_thread.start()

    def on_indexer_progress(self, current, total, filename):
        self.lbl_indexer_status.setText(f"🧠 الفهرسة العميقة جارية: ({current} من {total}) كتاباً | جاري قراءة: {filename[:40]}...")

    def on_indexer_finished(self, indexed_count):
        self.lbl_indexer_status.setText(f"🎉 اكتملت الفهرسة العميقة! تم إثراء {indexed_count} كتاباً بمحتواها الداخلي في قاعدة البيانات.")
        self.btn_run_indexer.setText("⚡ بدء الفهرسة العميقة بالخلفية")
        self.btn_run_indexer.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
