# -*- coding: utf-8 -*-
"""
ArchiveMaster - Global Repository Studio & Multilingual Scout
أستوديو المستودعات الكنسية المفتوحة وزر السحر لإضافة أي موقع والاستكشاف العابر للغات
Allows adding any Orthodox repository worldwide, inspecting it automatically,
translating theological queries across languages, and permanently downloading gaps offline.
"""

import os
import sys
import re
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTextEdit, QLineEdit, QGroupBox, QCheckBox, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QWidget,
    QComboBox, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QIcon

from modules import repository_registry, multilingual_theological_expander, online_book_feeder


class MultilingualSearchWorker(QObject):
    sig_finished = pyqtSignal(list)
    sig_status = pyqtSignal(str)
    sig_error = pyqtSignal(str)

    def __init__(self, query: str, limit_per_repo: int = 5):
        super().__init__()
        self.query = query
        self.limit = limit_per_repo

    def run(self):
        try:
            results = repository_registry.search_across_all_active_repositories(
                self.query,
                active_only=True,
                limit_per_repo=self.limit,
                log_callback=self.sig_status.emit
            )
            self.sig_finished.emit(results)
        except Exception as e:
            self.sig_error.emit(str(e))


class GlobalRepositoryStudioDialog(QDialog):
    """
    Dedicated Interactive Studio for Managing Open Repositories,
    Magic URL Inspector, and Multilingual Orthodox Scouting.
    """
    def __init__(self, parent=None, library_root=None, project_id=1):
        super().__init__(parent)
        self.setWindowTitle("🌐 أستوديو المستودعات الكنسية العالمية المفتوحة (Global Repositories Studio)")
        self.resize(1080, 750)
        self.setLayoutDirection(Qt.RightToLeft)

        self.library_root = library_root or r"I:\2021\2020\✠ Cross Coptic Library ✠"
        self.project_id = project_id or 1
        self.current_results = []
        self.latest_inspection = None

        self.init_ui()
        self.refresh_repositories_table()

    def init_ui(self):
        # Apply Soft Slate Eye-Care Theme
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
            QLineEdit, QComboBox {
                background-color: #14171E;
                color: white;
                border: 1px solid #3A4454;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QTableWidget {
                background-color: #14171E;
                border: 1px solid #3A4454;
                border-radius: 6px;
                gridline-color: #2D3442;
                color: #E2E8F0;
                font-size: 12px;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background-color: #252B36;
                color: #E5C07B;
                font-weight: bold;
                font-size: 12px;
                padding: 6px;
                border: 1px solid #3A4454;
            }
            QTextEdit {
                background-color: #14171E;
                color: #CBD5E1;
                border: 1px solid #3A4454;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #3A4454;
                background-color: #1E232D;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #252B36;
                color: #94A3B8;
                font-weight: bold;
                padding: 8px 18px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #0284C7;
                color: white;
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

        # 1. Header Banner
        h_box = QHBoxLayout()
        icon_lbl = QLabel("🌐")
        icon_lbl.setStyleSheet("font-size: 32px;")
        h_box.addWidget(icon_lbl)

        v_head = QVBoxLayout()
        t_lbl = QLabel("أستوديو المستودعات الكنسية العالمية المفتوحة (Global Repositories Studio)")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E5C07B;")
        v_head.addWidget(t_lbl)

        sub_lbl = QLabel("محرك مفتوح لا يعرف حواجز المواقع أو اللغات: يتيح إضافة أي موقع كنسي، وفحصه ذاتياً، وترجمة واستخلاص كتبه وتوطينها أوفلاين.")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_head.addWidget(sub_lbl)
        h_box.addLayout(v_head, 1)

        layout.addLayout(h_box)

        # 2. Main Tabs
        self.tabs = QTabWidget()

        # Tab 1: Repositories Hub
        tab_hub = QWidget()
        v_hub = QVBoxLayout(tab_hub)

        hub_top = QHBoxLayout()
        lbl_hub_desc = QLabel("قائمة المستودعات الكنسية النشطة (العربية، اليونانية، الروسية، والإنجليزية):")
        lbl_hub_desc.setStyleSheet("color: #E2E8F0; font-weight: bold;")
        hub_top.addWidget(lbl_hub_desc, 1)

        self.btn_go_add = QPushButton("➕ إضافة مستودع جديد (زر السحر)")
        self.btn_go_add.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981); color: white;")
        self.btn_go_add.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        hub_top.addWidget(self.btn_go_add)

        self.btn_delete_repo = QPushButton("🗑️ حذف المستودع")
        self.btn_delete_repo.setStyleSheet("background-color: #991B1B; color: white;")
        self.btn_delete_repo.clicked.connect(self.delete_selected_repo)
        hub_top.addWidget(self.btn_delete_repo)

        v_hub.addLayout(hub_top)

        self.tbl_repos = QTableWidget(0, 5)
        self.tbl_repos.setHorizontalHeaderLabels(["المستودع الكنسي", "اللغة", "الرابط الأساسي", "الكتب التقديرية", "الحالة"])
        self.tbl_repos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_repos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_repos.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_repos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_repos.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        v_hub.addWidget(self.tbl_repos)

        self.tabs.addTab(tab_hub, "🏛️ المستودعات المعتمدة (8 مستودعات أساسية)")

        # Tab 2: Magic Inspector (زر السحر وفحص أي موقع)
        tab_magic = QWidget()
        v_magic = QVBoxLayout(tab_magic)

        grp_inspect = QGroupBox("✨ زر السحر: الفاحص الذكي لأي موقع أو أرشيف كنسي جديد")
        v_ins_lay = QVBoxLayout(grp_inspect)

        row_in = QHBoxLayout()
        lbl_in = QLabel("رابط الموقع أو الأرشيف:")
        row_in.addWidget(lbl_in)

        self.le_magic_url = QLineEdit()
        self.le_magic_url.setPlaceholderText("الصق أي رابط موقع أو مدونة كنسية (مثال: https://st-takla.org/books/ أو رابط ووردبريس أو مجلة كنسية)...")
        row_in.addWidget(self.le_magic_url, 1)

        self.btn_inspect = QPushButton("⚡ فحص واكتشاف هيكل الموقع ذاتياً")
        self.btn_inspect.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D97706); color: white; padding: 8px 18px;")
        self.btn_inspect.clicked.connect(self.run_magic_inspection)
        row_in.addWidget(self.btn_inspect)

        v_ins_lay.addLayout(row_in)

        # Inspection result cards
        self.card_inspect_result = QFrame()
        self.card_inspect_result.setStyleSheet("background-color: #14171E; border: 1px solid #3A4454; border-radius: 6px; padding: 10px;")
        v_res = QVBoxLayout(self.card_inspect_result)

        self.lbl_insp_title = QLabel("نتيجة الفحص الذاتي ستظهر هنا...")
        self.lbl_insp_title.setStyleSheet("color: #94A3B8; font-size: 13px;")
        v_res.addWidget(self.lbl_insp_title)

        self.txt_insp_details = QTextEdit()
        self.txt_insp_details.setReadOnly(True)
        self.txt_insp_details.setFixedHeight(120)
        v_res.addWidget(self.txt_insp_details)

        v_ins_lay.addWidget(self.card_inspect_result)

        # Add Repo Form
        row_add = QHBoxLayout()
        lbl_r_name = QLabel("اسم المستودع المقترح:")
        row_add.addWidget(lbl_r_name)

        self.le_repo_name = QLineEdit()
        self.le_repo_name.setPlaceholderText("مثال: مكتبة دير البراموس، أو مستودع الكرازة...")
        row_add.addWidget(self.le_repo_name, 1)

        self.btn_commit_add = QPushButton("✅ اعتماد وإضافة المستودع لسجل المكتبة الدائم")
        self.btn_commit_add.setEnabled(False)
        self.btn_commit_add.setStyleSheet("background-color: #059669; color: white; padding: 8px 20px;")
        self.btn_commit_add.clicked.connect(self.commit_add_repository)
        row_add.addWidget(self.btn_commit_add)

        v_ins_lay.addLayout(row_add)

        v_magic.addWidget(grp_inspect)
        v_magic.addStretch()
        self.tabs.addTab(tab_magic, "➕ زر السحر (إضافة أي موقع كنسي)")

        # Tab 3: Multilingual Discovery & Scout
        tab_scout = QWidget()
        v_scout = QVBoxLayout(tab_scout)

        grp_scout = QGroupBox("🔍 الاستكشاف والبحث اللاهوتي العابر للغات عبر كافة المستودعات")
        v_s_lay = QVBoxLayout(grp_scout)

        row_sq = QHBoxLayout()
        lbl_sq = QLabel("موضوع البحث أو اسم القديس (بالعربية):")
        row_sq.addWidget(lbl_sq)

        self.le_scout_query = QLineEdit()
        self.le_scout_query.setPlaceholderText("اكتب بالعربية (مثال: تجسد الكلمة، طبيعة المسيح، مجمع نيقية، سر التناول)...")
        row_sq.addWidget(self.le_scout_query, 1)

        self.btn_scout_search = QPushButton("🚀 انطلاق البحث العالمي المتعدد اللغات")
        self.btn_scout_search.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1); color: white; padding: 8px 20px;")
        self.btn_scout_search.clicked.connect(self.start_multilingual_search)
        row_sq.addWidget(self.btn_scout_search)

        v_s_lay.addLayout(row_sq)

        # Translation preview badges
        self.badge_frame = QFrame()
        self.badge_frame.setStyleSheet("background-color: #14171E; border: 1px solid #3A4454; border-radius: 6px; padding: 6px;")
        h_badges = QHBoxLayout(self.badge_frame)
        self.lbl_exp_en = QLabel("🇬🇧 الإنجليزية: -")
        self.lbl_exp_en.setStyleSheet("color: #38BDF8; font-size: 11px;")
        h_badges.addWidget(self.lbl_exp_en)

        self.lbl_exp_el = QLabel("🇬🇷 اليونانية: -")
        self.lbl_exp_el.setStyleSheet("color: #A3E635; font-size: 11px;")
        h_badges.addWidget(self.lbl_exp_el)

        self.lbl_exp_ru = QLabel("🇷🇺 الروسية: -")
        self.lbl_exp_ru.setStyleSheet("color: #FBBF24; font-size: 11px;")
        h_badges.addWidget(self.lbl_exp_ru)

        v_s_lay.addWidget(self.badge_frame)
        v_scout.addWidget(grp_scout)

        # Status & Progress
        self.lbl_scout_status = QLabel("جاهز للبحث عبر كافة المستودعات الأرثوذكسية العالمية.")
        self.lbl_scout_status.setStyleSheet("color: #94A3B8; font-weight: bold;")
        v_scout.addWidget(self.lbl_scout_status)

        # Results Table
        self.tbl_results = QTableWidget(0, 6)
        self.tbl_results.setHorizontalHeaderLabels(["الكتاب / المرجع", "المستودع الأصلي", "حالة التوفر بمكتبتك", "المجلد الكنسي", "الصيغة", "إجراء التنزيل"])
        self.tbl_results.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_results.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_results.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_results.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        v_scout.addWidget(self.tbl_results)

        # Bottom Actions for Scout
        row_b_scout = QHBoxLayout()
        self.btn_dl_gaps_only = QPushButton("⭐ تنزيل وسد الثغرات المفقودة فقط أوفلاين")
        self.btn_dl_gaps_only.setEnabled(False)
        self.btn_dl_gaps_only.setStyleSheet("background-color: #B45309; color: white;")
        self.btn_dl_gaps_only.clicked.connect(self.download_gaps_only)
        row_b_scout.addWidget(self.btn_dl_gaps_only)

        row_b_scout.addStretch()

        v_scout.addLayout(row_b_scout)
        self.tabs.addTab(tab_scout, "🌐 الاستكشاف العالمي وسد الثغرات")

        layout.addWidget(self.tabs)

        # Bottom Bar
        b_bar = QHBoxLayout()
        b_bar.addStretch()
        btn_close = QPushButton("إغلاق الأستوديو")
        btn_close.clicked.connect(self.accept)
        b_bar.addWidget(btn_close)
        layout.addLayout(b_bar)

    # -------------------------------------------------------------
    # Tab 1: Hub & Table Management
    # -------------------------------------------------------------
    def refresh_repositories_table(self):
        repos = repository_registry.load_repositories()
        self.tbl_repos.setRowCount(len(repos))

        for i, r in enumerate(repos):
            it_name = QTableWidgetItem(f"{r.get('badge', '')} {r.get('name', '')}")
            it_name.setForeground(QColor("#E2E8F0"))
            it_name.setData(Qt.UserRole, r.get("id"))

            it_lang = QTableWidgetItem(r.get("language_name", r.get("language", "ar")))
            it_lang.setForeground(QColor("#38BDF8"))

            it_url = QTableWidgetItem(r.get("url", ""))
            it_url.setForeground(QColor("#94A3B8"))

            it_cnt = QTableWidgetItem(r.get("book_count_est", "متعدد"))
            it_cnt.setForeground(QColor("#E5C07B"))

            is_act = r.get("active", True)
            chk_act = QCheckBox("نشط 🟢" if is_act else "معطل ⚪")
            chk_act.setChecked(is_act)
            chk_act.setStyleSheet(f"color: {'#34D399' if is_act else '#64748B'}; font-weight: bold;")
            chk_act.toggled.connect(lambda ch, r_id=r.get("id"): self.toggle_repo(r_id, ch))

            self.tbl_repos.setItem(i, 0, it_name)
            self.tbl_repos.setItem(i, 1, it_lang)
            self.tbl_repos.setItem(i, 2, it_url)
            self.tbl_repos.setItem(i, 3, it_cnt)
            self.tbl_repos.setCellWidget(i, 4, chk_act)

    def toggle_repo(self, repo_id, checked):
        repository_registry.toggle_repository_active(repo_id, checked)
        self.refresh_repositories_table()

    def delete_selected_repo(self):
        row = self.tbl_repos.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى اختيار مستودع من الجدول لحذفه.")
            return

        it = self.tbl_repos.item(row, 0)
        repo_id = it.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من رغبتك في إزالة المستودع: {it.text()}؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            repository_registry.delete_repository(repo_id)
            self.refresh_repositories_table()

    # -------------------------------------------------------------
    # Tab 2: Magic URL Inspector
    # -------------------------------------------------------------
    def run_magic_inspection(self):
        url = self.le_magic_url.text().strip()
        if not url or not url.startswith("http"):
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال رابط صالح يبدأ بـ http:// أو https://")
            return

        self.btn_inspect.setEnabled(False)
        self.lbl_insp_title.setText(f"⏳ جاري فحص المستودع واكتشاف هيكله الرقمي: {url} ...")
        QApplication.processEvents()

        report = repository_registry.inspect_repository_url(url)
        self.btn_inspect.setEnabled(True)
        self.latest_inspection = report

        if report.get("accessible"):
            self.lbl_insp_title.setText(f"✅ تم فحص المستودع بنجاح: «{report.get('title')}»")
            self.lbl_insp_title.setStyleSheet("color: #34D399; font-weight: bold;")

            details = [
                f"• نوع النظام المكتشف: {report.get('platform')}",
                f"• لغة الموقع: {report.get('language')}",
                f"• الأقسام / الروابط المكتشفة: {report.get('categories_found')}",
                f"• طريقة التنزيل: {report.get('download_method')}"
            ]
            samples = report.get("books_found_sample", [])
            if samples:
                details.append("\n📚 عينة من الكتب المكتشفة فوراً في الموقع:")
                for s in samples[:4]:
                    details.append(f"  - {s}")

            self.txt_insp_details.setPlainText("\n".join(details))
            self.le_repo_name.setText(report.get("title", "مستودع كنسي جديد"))
            self.btn_commit_add.setEnabled(True)
        else:
            self.lbl_insp_title.setText(f"❌ تعذر فحص الموقع: {report.get('error', 'خطأ في الاتصال')}")
            self.lbl_insp_title.setStyleSheet("color: #F87171; font-weight: bold;")
            self.txt_insp_details.setPlainText("تأكد من صحة الرابط ومن اتصال الإنترنت.")
            self.btn_commit_add.setEnabled(False)

    def commit_add_repository(self):
        if not self.latest_inspection or not self.latest_inspection.get("accessible"):
            return
        name = self.le_repo_name.text().strip() or self.latest_inspection.get("title", "مستودع كنسي")
        url = self.latest_inspection.get("url")
        lang = self.latest_inspection.get("language", "ar")

        repository_registry.add_custom_repository(
            name=name,
            url=url,
            language=lang,
            description=f"مستودع تم فحصه واعتماده ذاتياً ({self.latest_inspection.get('platform')})"
        )

        QMessageBox.information(
            self,
            "تمت الإضافة بنجاح",
            f"🎉 تم اعتماد وإضافة مستودع «{name}» إلى سجل المستودعات الكنسية الدائم بنجاح!\n\n"
            f"أصبح الآن مدرجاً في دورات البحث والفحص واستخلاص الثغرات الأوفلاين."
        )
        self.refresh_repositories_table()
        self.tabs.setCurrentIndex(0)

    # -------------------------------------------------------------
    # Tab 3: Multilingual Search & Gap Downloader
    # -------------------------------------------------------------
    def start_multilingual_search(self):
        query = self.le_scout_query.text().strip()
        if not query:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة موضوع أو اسم قديس للبحث عنه.")
            return

        # Show expanded translation badges immediately
        exp = multilingual_theological_expander.expand_theological_query(query)
        self.lbl_exp_en.setText(f"🇬🇧 الإنجليزية: {exp.get('en', '-')}")
        self.lbl_exp_el.setText(f"🇬🇷 اليونانية: {exp.get('el', '-')}")
        self.lbl_exp_ru.setText(f"🇷🇺 الروسية: {exp.get('ru', '-')}")

        self.btn_scout_search.setEnabled(False)
        self.lbl_scout_status.setText("⏳ جاري إطلاق البحث في كافة المستودعات الأرثوذكسية العالمية باللغات المناسبة...")
        self.tbl_results.setRowCount(0)

        self.s_thread = QThread()
        self.s_worker = MultilingualSearchWorker(query, limit_per_repo=4)
        self.s_worker.moveToThread(self.s_thread)

        self.s_thread.started.connect(self.s_worker.run)
        self.s_worker.sig_status.connect(self.lbl_scout_status.setText)
        self.s_worker.sig_finished.connect(self.on_search_finished)
        self.s_worker.sig_error.connect(self.on_search_error)

        self.s_worker.sig_finished.connect(self.s_thread.quit)
        self.s_worker.sig_finished.connect(self.s_worker.deleteLater)
        self.s_worker.sig_error.connect(self.s_thread.quit)
        self.s_worker.sig_error.connect(self.s_worker.deleteLater)
        self.s_thread.finished.connect(self.s_thread.deleteLater)

        self.s_thread.start()

    def on_search_finished(self, candidates):
        self.btn_scout_search.setEnabled(True)
        self.current_results = candidates
        self.tbl_results.setRowCount(len(candidates))

        existing_c = sum(1 for c in candidates if c.get("local_status") == "EXISTING")
        gaps_c = len(candidates) - existing_c
        self.lbl_scout_status.setText(f"✅ تم العثور على {len(candidates)} مرجعاً ({existing_c} متوفر لديك بالفعل، و {gaps_c} ثغرة جديدة غير متوفرة).")
        self.btn_dl_gaps_only.setEnabled(bool(gaps_c > 0))

        for i, c in enumerate(candidates):
            it_title = QTableWidgetItem(c.get("title", ""))
            it_title.setForeground(QColor("#FFFFFF"))

            it_source = QTableWidgetItem(c.get("source_badge", ""))

            is_exist = (c.get("local_status") == "EXISTING")
            it_status = QTableWidgetItem(c.get("local_badge", "⭐ ثغرة مفقودة"))
            it_status.setForeground(QColor("#34D399" if is_exist else "#FBBF24"))

            it_folder = QTableWidgetItem(f"/{c.get('target_folder', 'عام')}")
            it_folder.setForeground(QColor("#E5C07B"))

            it_fmt = QTableWidgetItem(c.get("format", "PDF"))
            it_fmt.setForeground(QColor("#38BDF8"))

            btn_dl = QPushButton("✅ متوفر" if is_exist else "📥 تنزيل وتوطين")
            btn_dl.setStyleSheet(f"""
                QPushButton {{
                    background-color: {"#252B36" if is_exist else "#059669"};
                    color: {"#94A3B8" if is_exist else "white"};
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: {"#384254" if is_exist else "#10B981"}; }}
            """)
            btn_dl.clicked.connect(lambda ch, idx=i, b=btn_dl: self.download_single_book(self.current_results[idx], b))

            self.tbl_results.setItem(i, 0, it_title)
            self.tbl_results.setItem(i, 1, it_source)
            self.tbl_results.setItem(i, 2, it_status)
            self.tbl_results.setItem(i, 3, it_folder)
            self.tbl_results.setItem(i, 4, it_fmt)
            self.tbl_results.setCellWidget(i, 5, btn_dl)

    def on_search_error(self, err):
        self.btn_scout_search.setEnabled(True)
        self.lbl_scout_status.setText(f"❌ حدث خطأ أثناء البحث: {err}")

    def download_single_book(self, candidate, button):
        button.setEnabled(False)
        button.setText("⏳ جاري التنزيل...")
        QApplication.processEvents()

        ok, dest, fsize = online_book_feeder.download_and_index_candidate(
            candidate, self.library_root, project_id=self.project_id
        )
        if ok and dest:
            button.setText("✅ تم التسكين أوفلاين")
            button.setStyleSheet("background-color: #047857; color: white;")
            QMessageBox.information(
                self,
                "اكتمل التسكين والتوطين",
                f"✅ تم تنزيل المرجع بنجاح وتسكينه في رصيد مكتبتك أوفلاين إلى الأبد!\n\n"
                f"• الكتاب: {candidate.get('title')}\n"
                f"• المسار: {dest}\n"
                f"• الحجم: {fsize / (1024*1024):.2f} ميجابايت\n\n"
                f"تمت الفهرسة في قاعدة البيانات أوفلاين."
            )
        else:
            button.setEnabled(True)
            button.setText("❌ فشل التحميل")

    def download_gaps_only(self):
        gaps = [c for c in self.current_results if c.get("local_status") != "EXISTING"]
        if not gaps:
            QMessageBox.information(self, "تنبيه", "جميع الكتب متوفرة لديك بالفعل.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد التنزيل",
            f"هل ترغب في تنزيل وتسكين كافة الثغرات الـ ({len(gaps)}) في مكتبتك أوفلاين دفعة واحدة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            success_c = 0
            for i, c in enumerate(self.current_results):
                if c.get("local_status") != "EXISTING":
                    btn = self.tbl_results.cellWidget(i, 5)
                    ok, dest, fsize = online_book_feeder.download_and_index_candidate(
                        c, self.library_root, project_id=self.project_id
                    )
                    if ok:
                        success_c += 1
                        if btn:
                            btn.setText("✅ تم التسكين")
                            btn.setEnabled(False)

            QMessageBox.information(
                self,
                "اكتمل تنزيل الثغرات",
                f"🎉 تم بنجاح تنزيل وتسكين {success_c} كتاباً ومرجعاً جديداً في رصيد مكتبتك أوفلاين!"
            )
