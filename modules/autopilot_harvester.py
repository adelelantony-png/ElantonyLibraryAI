# -*- coding: utf-8 -*-
"""
ArchiveMaster - Autopilot All-Authors Gap Harvester
محرك الحاصد الآلي الشامل لكافة المؤلفين والقديسين لسد ثغرات المكتبة تلقائياً
Crawls all 82 Church Fathers / Authors from Awtar Al-Sama, compares against local 38,460+ library DB,
and downloads ONLY genuine missing gaps sequentially with pause/resume and zero-crash safeguards.
"""

import os
import sys
import time
import re
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QRadioButton,
    QButtonGroup, QGroupBox, QSpinBox, QCheckBox, QMessageBox, QFrame,
    QApplication, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QIcon

from modules import online_book_feeder


class AutopilotHarvesterWorker(QObject):
    """
    Background worker that iterates through authors, detects missing gaps,
    and downloads them sequentially into the user's library without UI freezing.
    """
    sig_status = pyqtSignal(str, str)  # message, level: info, success, gap, warning, error
    sig_author_started = pyqtSignal(int, int, str, str)  # index, total, name, url
    sig_author_scanned = pyqtSignal(int, int, str, int, int, int)  # index, total, name, total_b, existing, gaps
    sig_metrics_update = pyqtSignal(dict)
    sig_gap_discovered = pyqtSignal(dict, str)  # book_item, author_name
    sig_gap_completed = pyqtSignal(dict, str, int)  # book_item, dest_path, size
    sig_finished = pyqtSignal(dict)

    def __init__(self, authors, library_root, project_id=1, start_index=0, scope="all", auto_download=True, delay_sec=1.2):
        super().__init__()
        self.authors = authors or []
        self.library_root = library_root
        self.project_id = project_id
        self.start_index = max(0, start_index)
        self.scope = scope  # 'all', 'from_current', 'current_only'
        self.auto_download = auto_download
        self.delay_sec = max(0.5, float(delay_sec))

        self._is_paused = False
        self._is_stopped = False

    def pause(self):
        self._is_paused = True
        self.sig_status.emit("⏸️ تم تفعيل الإيقاف المؤقت للحاصد الآلي...", "warning")

    def resume(self):
        self._is_paused = False
        self.sig_status.emit("▶️ تم استئناف الحصاد الآلي...", "info")

    def stop(self):
        self._is_stopped = True
        self._is_paused = False
        self.sig_status.emit("⏹️ جاري إيقاف الحاصد الآلي وحفظ كافة البيانات المنجزة...", "error")

    def run(self):
        if not self.authors:
            self.sig_status.emit("❌ قائمة المؤلفين فارغة، تعذر بدء الحصاد.", "error")
            self.sig_finished.emit({})
            return

        # Determine authors slice
        if self.scope == "current_only":
            target_authors = [self.authors[self.start_index]] if self.start_index < len(self.authors) else []
            base_idx = self.start_index
        elif self.scope == "from_current":
            target_authors = self.authors[self.start_index:]
            base_idx = self.start_index
        else:
            target_authors = self.authors
            base_idx = 0

        total_target = len(target_authors)
        self.sig_status.emit(f"🚀 انطلاق الحاصد الآلي الشامل لمسح {total_target} مؤلفاً...", "info")

        metrics = {
            "total_authors": total_target,
            "scanned_authors": 0,
            "books_scanned": 0,
            "existing_skipped": 0,
            "gaps_found": 0,
            "gaps_downloaded": 0,
            "gaps_failed": 0,
            "total_bytes": 0
        }

        for i, author in enumerate(target_authors):
            if self._is_stopped:
                break

            while self._is_paused:
                if self._is_stopped:
                    break
                time.sleep(0.4)

            current_author_idx = i + 1
            author_name = author.get("name", "مؤلف كنسي")
            author_url = author.get("url", "")

            self.sig_author_started.emit(current_author_idx, total_target, author_name, author_url)
            self.sig_status.emit(f"\n👤 [{current_author_idx}/{total_target}] جاري فحص مؤلفات: «{author_name}» ...", "info")

            # Extract books for this author
            try:
                def _worker_log(msg):
                    # Filter verbose httpx logs
                    if "الاتصال بالرابط" in msg or "تم فتح الصفحة" in msg:
                        self.sig_status.emit(f"  {msg}", "info")

                books = online_book_feeder.crawl_and_extract_books_from_url(
                    author_url, limit=150, log_callback=_worker_log
                )
            except Exception as e:
                self.sig_status.emit(f"  ⚠️ تعذر استخراج كتب «{author_name}»: {e}", "warning")
                books = []

            total_author_books = len(books)
            existing_count = sum(1 for b in books if b.get("local_status") == "EXISTING")
            gap_books = [b for b in books if b.get("local_status") == "GAP"]
            gaps_count = len(gap_books)

            metrics["scanned_authors"] += 1
            metrics["books_scanned"] += total_author_books
            metrics["existing_skipped"] += existing_count
            metrics["gaps_found"] += gaps_count
            self.sig_metrics_update.emit(metrics)

            self.sig_author_scanned.emit(
                current_author_idx, total_target, author_name, total_author_books, existing_count, gaps_count
            )

            if total_author_books == 0:
                self.sig_status.emit(f"  ℹ️ لا توجد كتب منشورة حالياً في صفحة «{author_name}».", "info")
            elif gaps_count == 0:
                self.sig_status.emit(f"  🎉 رائع! جميع كتب «{author_name}» ({existing_count} كتاباً) متوفرة لديك بالفعل في رصيد مكتبتك أوفلاين.", "success")
            else:
                self.sig_status.emit(f"  ⭐ تم رصد {gaps_count} ثغرة مفقودة لـ «{author_name}» (من أصل {total_author_books} كتاباً).", "gap")

                # Download missing gaps if auto_download is enabled
                if self.auto_download:
                    for g_idx, gap in enumerate(gap_books):
                        if self._is_stopped:
                            break
                        while self._is_paused:
                            if self._is_stopped:
                                break
                            time.sleep(0.4)

                        b_title = gap.get("title", "كتاب غير مسمى")
                        self.sig_gap_discovered.emit(gap, author_name)
                        self.sig_status.emit(f"  📥 جاري تنزيل وتسكين الثغرة ({g_idx+1}/{gaps_count}): «{b_title}» ...", "info")

                        try:
                            ok, dest, fsize = online_book_feeder.download_and_index_candidate(
                                gap, self.library_root, project_id=self.project_id
                            )
                            if ok and dest:
                                metrics["gaps_downloaded"] += 1
                                metrics["total_bytes"] += fsize
                                self.sig_gap_completed.emit(gap, dest, fsize)
                                self.sig_status.emit(f"  ✅ تم بنجاح تسكين وفهرسة: «{b_title}» ({fsize / (1024*1024):.1f} MB)", "success")
                            else:
                                metrics["gaps_failed"] += 1
                                self.sig_status.emit(f"  ❌ تعذر إتمام تنزيل: «{b_title}»", "warning")
                        except Exception as dl_err:
                            metrics["gaps_failed"] += 1
                            self.sig_status.emit(f"  ❌ خطأ أثناء تنزيل «{b_title}»: {dl_err}", "error")

                        self.sig_metrics_update.emit(metrics)
                        # Brief polite delay between file downloads
                        time.sleep(0.8)

            # Delay between authors to prevent rate-limiting
            if i < total_target - 1 and not self._is_stopped:
                time.sleep(self.delay_sec)

        self.sig_status.emit("\n=======================================================", "info")
        if self._is_stopped:
            self.sig_status.emit("🛑 تم إيقاف الحصاد الآلي يدوياً بواسطة المستخدم.", "warning")
        else:
            self.sig_status.emit(
                f"🎉 اكتمل الحصاد الآلي بنجاح تام! تم فحص {metrics['scanned_authors']} مؤلفاً، وتخطي {metrics['existing_skipped']} كتاباً متوفراً، وسد {metrics['gaps_downloaded']} ثغرة جديدة في مكتبتك.",
                "success"
            )
        self.sig_status.emit("=======================================================", "info")

        self.sig_finished.emit(metrics)


class AutopilotHarvesterDialog(QDialog):
    """
    Dedicated Interactive Dashboard for the Autopilot All-Authors Gap Harvester.
    """
    def __init__(self, parent=None, library_root=None, project_id=1, authors=None, initial_index=0):
        super().__init__(parent)
        self.setWindowTitle("🤖 الحاصد الآلي الشامل لمكتبة أوتار السماء (82 مؤلفاً) - Autopilot Gap Harvester")
        self.resize(1020, 740)
        self.setLayoutDirection(Qt.RightToLeft)

        # Resolve library root with canonical fallback
        if not library_root or not os.path.exists(library_root):
            default_path = r"I:\2021\2020\✠ Cross Coptic Library ✠"
            if os.path.exists(default_path):
                self.library_root = default_path
            else:
                self.library_root = os.path.abspath(os.getcwd())
        else:
            self.library_root = library_root

        self.project_id = project_id or 1
        self.authors = authors or online_book_feeder.get_awtar_alsama_catalog()
        self.initial_index = max(0, min(initial_index, len(self.authors) - 1)) if self.authors else 0

        self.worker = None
        self.thread = None
        self.is_running = False
        self.is_paused = False

        self.harvested_books = []

        self.init_ui()

    def init_ui(self):
        # Apply Soft Slate Eye-Care styling
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
            QLabel {
                color: #E2E8F0;
                font-size: 13px;
            }
            QRadioButton {
                color: #CBD5E1;
                font-size: 13px;
                spacing: 6px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QProgressBar {
                background-color: #1A1F26;
                border: 1px solid #3A4454;
                border-radius: 6px;
                text-align: center;
                color: #F8FAFC;
                font-weight: bold;
                font-size: 12px;
                height: 22px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
                border-radius: 5px;
            }
            QTableWidget {
                background-color: #1A1F26;
                border: 1px solid #3A4454;
                border-radius: 6px;
                gridline-color: #2D3442;
                color: #E2E8F0;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 5px;
            }
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
                border: 1px solid #3A4454;
                border-radius: 6px;
                color: #CBD5E1;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Header Banner
        h_layout = QHBoxLayout()
        header_icon = QLabel("🤖")
        header_icon.setStyleSheet("font-size: 32px;")
        h_layout.addWidget(header_icon)

        title_v = QVBoxLayout()
        title_lbl = QLabel("الحاصد الآلي الشامل لكافة المؤلفين والقديسين (Autopilot Gap Harvester)")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #E5C07B;")
        title_v.addWidget(title_lbl)

        sub_lbl = QLabel(
            "يمر تلقائياً على كافة المؤلفين الـ 82 في مكتبة أوتار السماء، يقارن محتواهم برصيد مكتبتك، وينزل ويسكن الثغرات المفقودة فقط دون تكرار."
        )
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_v.addWidget(sub_lbl)
        h_layout.addLayout(title_v, 1)

        layout.addLayout(h_layout)

        # 2. Options and Scope Configuration Box
        scope_box = QGroupBox("⚙️ إعدادات ونطاق الحصاد الآلي")
        scope_layout = QVBoxLayout(scope_box)

        row_radio = QHBoxLayout()
        self.radio_all = QRadioButton(f"🌐 فحص كافة المؤلفين الـ {len(self.authors)} بالكامل (دورة شاملة)")
        self.radio_all.setChecked(True)
        row_radio.addWidget(self.radio_all)

        init_author_name = self.authors[self.initial_index].get("name", "") if self.authors else ""
        self.radio_from_current = QRadioButton(f"➡️ البدء من المؤلف الحالي «{init_author_name}» حتى النهاية")
        row_radio.addWidget(self.radio_from_current)

        self.radio_current_only = QRadioButton(f"👤 المؤلف المحدد حالياً فقط («{init_author_name}»)")
        row_radio.addWidget(self.radio_current_only)

        scope_layout.addLayout(row_radio)

        row_opts = QHBoxLayout()
        self.chk_auto_download = QCheckBox("📥 تنزيل وتسكين الثغرات المكتشفة تلقائياً في المكتبة فوراً (Autopilot)")
        self.chk_auto_download.setChecked(True)
        self.chk_auto_download.setStyleSheet("color: #34D399; font-weight: bold; font-size: 12px;")
        row_opts.addWidget(self.chk_auto_download)

        row_opts.addSpacing(20)
        lbl_delay = QLabel("⏱️ مهلة الأمان بين المؤلفين:")
        row_opts.addWidget(lbl_delay)

        self.spn_delay = QSpinBox()
        self.spn_delay.setRange(1, 10)
        self.spn_delay.setValue(2)
        self.spn_delay.setSuffix(" ثانية")
        self.spn_delay.setStyleSheet("background-color: #1A1F26; color: white; padding: 4px; border: 1px solid #3A4454; border-radius: 4px;")
        row_opts.addWidget(self.spn_delay)

        row_opts.addStretch()

        dest_lbl = QLabel(f"📂 المجلد المستهدف: {os.path.basename(self.library_root)}")
        dest_lbl.setToolTip(self.library_root)
        dest_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        row_opts.addWidget(dest_lbl)

        scope_layout.addLayout(row_opts)
        layout.addWidget(scope_box)

        # 3. Control Action Bar
        act_layout = QHBoxLayout()

        self.btn_start = QPushButton("▶️ انطلاق الحصاد الآلي الآن")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 9px 24px;
                border-radius: 6px;
                border: 1px solid #34D399;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #34D399);
            }
            QPushButton:disabled {
                background-color: #2D3442;
                color: #64748B;
                border: 1px solid #3A4454;
            }
        """)
        self.btn_start.clicked.connect(self.start_harvest)
        act_layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸️ إيقاف مؤقت")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #B45309;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 9px 18px;
                border-radius: 6px;
                border: 1px solid #F59E0B;
            }
            QPushButton:hover { background-color: #D97706; }
            QPushButton:disabled { background-color: #2D3442; color: #64748B; border: 1px solid #3A4454; }
        """)
        self.btn_pause.clicked.connect(self.toggle_pause)
        act_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹️ إيقاف نهائي وحفظ")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #991B1B;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 9px 18px;
                border-radius: 6px;
                border: 1px solid #EF4444;
            }
            QPushButton:hover { background-color: #DC2626; }
            QPushButton:disabled { background-color: #2D3442; color: #64748B; border: 1px solid #3A4454; }
        """)
        self.btn_stop.clicked.connect(self.stop_harvest)
        act_layout.addWidget(self.btn_stop)

        act_layout.addStretch()

        self.lbl_status = QLabel("جاهز لبدء الحصاد التلقائي")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 12px;")
        act_layout.addWidget(self.lbl_status)

        layout.addLayout(act_layout)

        # 4. Metric Statistics Cards
        cards_layout = QHBoxLayout()

        self.card_authors = self._create_metric_card("👥 المؤلفون المفحوصون", "0 / 82", "#38BDF8")
        cards_layout.addWidget(self.card_authors)

        self.card_books = self._create_metric_card("📚 الكتب المفحوصة", "0", "#E2E8F0")
        cards_layout.addWidget(self.card_books)

        self.card_skipped = self._create_metric_card("⏭️ متوفر محلياً (تخطي)", "0", "#A3E635")
        cards_layout.addWidget(self.card_skipped)

        self.card_gaps = self._create_metric_card("⭐ ثغرات تم سدها", "0", "#F59E0B")
        cards_layout.addWidget(self.card_gaps)

        layout.addLayout(cards_layout)

        # 5. Dual Progress Bar
        self.progress_authors = QProgressBar()
        self.progress_authors.setFormat("المؤلفين: %v من %m (%p%)")
        self.progress_authors.setValue(0)
        layout.addWidget(self.progress_authors)

        # 6. Tabular / Log Split Section
        body_layout = QHBoxLayout()

        # Left: Live Harvested Gaps Table
        table_v = QVBoxLayout()
        tbl_lbl = QLabel("📋 الثغرات المحصودة في هذه الجلسة (تم تنزيلها وتسكينها):")
        tbl_lbl.setStyleSheet("color: #E5C07B; font-weight: bold; font-size: 12px;")
        table_v.addWidget(tbl_lbl)

        self.table_gaps = QTableWidget(0, 4)
        self.table_gaps.setHorizontalHeaderLabels(["الكتاب", "المؤلف", "المجلد الكنسي", "الحجم"])
        self.table_gaps.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_gaps.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_gaps.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_gaps.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table_v.addWidget(self.table_gaps)
        body_layout.addLayout(table_v, 5)

        # Right: Live Terminal Log
        log_v = QVBoxLayout()
        log_top = QHBoxLayout()
        log_lbl = QLabel("🖥️ سجل الأنشطة الحية:")
        log_lbl.setStyleSheet("color: #E5C07B; font-weight: bold; font-size: 12px;")
        log_top.addWidget(log_lbl)

        btn_clear = QPushButton("مسح السجل")
        btn_clear.setStyleSheet("background-color: #252B36; color: #94A3B8; font-size: 10px; padding: 2px 8px; border-radius: 3px;")
        btn_clear.clicked.connect(lambda: self.log_console.clear())
        log_top.addWidget(btn_clear)
        log_v.addLayout(log_top)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        log_v.addWidget(self.log_console)
        body_layout.addLayout(log_v, 6)

        layout.addLayout(body_layout)

        # Initial log notice
        self.append_log(f"🌿 تم تهيئة الحاصد الآلي. إجمالي قاعدة بيانات المؤلفين: {len(self.authors)} مؤلفاً وقديساً.", "#38BDF8")
        self.append_log(f"📁 مكتبة الرصيد المحلي: {self.library_root}", "#94A3B8")
        self.append_log("💡 اضغط «انطلاق الحصاد الآلي الآن» للبدء التلقائي بدون تدخل يدوي.", "#E5C07B")

    def _create_metric_card(self, title, init_val, accent_color):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #252B36;
                border: 1px solid #3A4454;
                border-right: 4px solid {accent_color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94A3B8; font-size: 11px;")
        v.addWidget(lbl_t)

        lbl_v = QLabel(init_val)
        lbl_v.setObjectName("metric_val")
        lbl_v.setStyleSheet(f"color: {accent_color}; font-size: 18px; font-weight: bold;")
        v.addWidget(lbl_v)

        return frame

    def _set_card_value(self, card_widget, text):
        lbl = card_widget.findChild(QLabel, "metric_val")
        if lbl:
            lbl.setText(str(text))

    def append_log(self, text, color=None):
        if color:
            html = f"<div style='color: {color}; margin: 2px 0;'>{text}</div>"
            self.log_console.append(html)
        else:
            self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # -----------------------------------------------------------------
    # Execution & Control
    # -----------------------------------------------------------------
    def start_harvest(self):
        if self.is_running:
            return

        scope = "all"
        if self.radio_from_current.isChecked():
            scope = "from_current"
        elif self.radio_current_only.isChecked():
            scope = "current_only"

        auto_dl = self.chk_auto_download.isChecked()
        delay = self.spn_delay.value()

        self.is_running = True
        self.is_paused = False

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏸️ إيقاف مؤقت")
        self.btn_stop.setEnabled(True)

        self.radio_all.setEnabled(False)
        self.radio_from_current.setEnabled(False)
        self.radio_current_only.setEnabled(False)
        self.chk_auto_download.setEnabled(False)
        self.spn_delay.setEnabled(False)

        # Launch background thread
        self.thread = QThread()
        self.worker = AutopilotHarvesterWorker(
            authors=self.authors,
            library_root=self.library_root,
            project_id=self.project_id,
            start_index=self.initial_index,
            scope=scope,
            auto_download=auto_dl,
            delay_sec=delay
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.sig_status.connect(self.on_worker_status)
        self.worker.sig_author_started.connect(self.on_author_started)
        self.worker.sig_author_scanned.connect(self.on_author_scanned)
        self.worker.sig_metrics_update.connect(self.on_metrics_update)
        self.worker.sig_gap_discovered.connect(self.on_gap_discovered)
        self.worker.sig_gap_completed.connect(self.on_gap_completed)
        self.worker.sig_finished.connect(self.on_harvest_finished)

        self.worker.sig_finished.connect(self.thread.quit)
        self.worker.sig_finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def toggle_pause(self):
        if not self.is_running or not self.worker:
            return

        if not self.is_paused:
            self.worker.pause()
            self.is_paused = True
            self.btn_pause.setText("▶️ استئناف")
            self.lbl_status.setText("⏸️ متوقف مؤقتاً")
        else:
            self.worker.resume()
            self.is_paused = False
            self.btn_pause.setText("⏸️ إيقاف مؤقت")
            self.lbl_status.setText("▶️ جاري الحصاد...")

    def stop_harvest(self):
        if not self.is_running or not self.worker:
            return
        reply = QMessageBox.question(
            self,
            "تأكيد الإيقاف",
            "هل ترغب في إيقاف الحصاد الآلي الآن؟\n(سيتم حفظ كافة الكتب والثغرات التي تم تنزيلها وتسكينها بأمان)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.worker.stop()
            self.btn_stop.setEnabled(False)
            self.lbl_status.setText("⏹️ جاري إيقاف العملية...")

    # -----------------------------------------------------------------
    # Worker Callbacks
    # -----------------------------------------------------------------
    def on_worker_status(self, msg, level):
        color_map = {
            "info": "#CBD5E1",
            "success": "#34D399",
            "gap": "#FBBF24",
            "warning": "#F59E0B",
            "error": "#F87171"
        }
        self.append_log(msg, color_map.get(level, "#CBD5E1"))

    def on_author_started(self, idx, total, name, url):
        self.progress_authors.setMaximum(total)
        self.progress_authors.setValue(idx - 1)
        self.lbl_status.setText(f"👤 فحص المؤلف ({idx}/{total}): {name}")
        self._set_card_value(self.card_authors, f"{idx} / {total}")

    def on_author_scanned(self, idx, total, name, total_b, existing, gaps):
        self.progress_authors.setValue(idx)

    def on_metrics_update(self, metrics):
        self._set_card_value(self.card_authors, f"{metrics.get('scanned_authors', 0)} / {metrics.get('total_authors', 0)}")
        self._set_card_value(self.card_books, f"{metrics.get('books_scanned', 0):,}")
        self._set_card_value(self.card_skipped, f"{metrics.get('existing_skipped', 0):,}")
        self._set_card_value(self.card_gaps, f"{metrics.get('gaps_downloaded', 0):,}")

    def on_gap_discovered(self, gap_item, author_name):
        pass

    def on_gap_completed(self, gap_item, dest_path, fsize):
        row = self.table_gaps.rowCount()
        self.table_gaps.insertRow(row)

        title = gap_item.get("title", "")
        author = gap_item.get("author", "") or os.path.basename(os.path.dirname(dest_path))
        folder = gap_item.get("target_folder", "") or "أبائيات"
        size_mb = f"{fsize / (1024 * 1024):.1f} MB"

        it_title = QTableWidgetItem(f"✅ {title}")
        it_title.setForeground(QColor("#34D399"))

        it_author = QTableWidgetItem(author)
        it_author.setForeground(QColor("#38BDF8"))

        it_folder = QTableWidgetItem(f"/{folder}")
        it_folder.setForeground(QColor("#E5C07B"))

        it_size = QTableWidgetItem(size_mb)
        it_size.setForeground(QColor("#CBD5E1"))

        self.table_gaps.setItem(row, 0, it_title)
        self.table_gaps.setItem(row, 1, it_author)
        self.table_gaps.setItem(row, 2, it_folder)
        self.table_gaps.setItem(row, 3, it_size)

        self.table_gaps.scrollToBottom()

    def on_harvest_finished(self, summary):
        self.is_running = False
        self.is_paused = False

        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸️ إيقاف مؤقت")
        self.btn_stop.setEnabled(False)

        self.radio_all.setEnabled(True)
        self.radio_from_current.setEnabled(True)
        self.radio_current_only.setEnabled(True)
        self.chk_auto_download.setEnabled(True)
        self.spn_delay.setEnabled(True)

        downloaded = summary.get("gaps_downloaded", 0)
        scanned = summary.get("scanned_authors", 0)
        self.lbl_status.setText(f"🎉 اكتمل الحصاد! تم سد {downloaded} ثغرة بنجاح.")

        QMessageBox.information(
            self,
            "اكتمل الحصاد الآلي",
            f"🎉 تم الانتهاء من دورة الحصاد الآلي بنجاح!\n\n"
            f"👤 المؤلفون المفحوصون: {scanned}\n"
            f"📚 إجمالي الكتب التي تم مراجعتها: {summary.get('books_scanned', 0):,}\n"
            f"⏭️ كتب متوفرة لديك تم تخطيها: {summary.get('existing_skipped', 0):,}\n"
            f"⭐ الثغرات التي تم تنزيلها وتسكينها في مكتبتك: {downloaded:,}\n\n"
            f"تمت الفهرسة في قاعدة البيانات أوفلاين وتسكين الملفات في مساراتها المحددة."
        )

    def closeEvent(self, event):
        if self.is_running:
            reply = QMessageBox.question(
                self,
                "إغلاق النافذة",
                "الحاصد الآلي يعمل حالياً في الخلفية. هل ترغب في إيقافه وإغلاق النافذة؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.worker:
                    self.worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
