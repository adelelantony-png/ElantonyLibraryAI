from modules.library_audit_dialog import LibraryAuditDialog
from modules.online_feeder_dialog import OnlineFeederDialog
from modules.apologetics_hub_dialog import ApologeticsHubDialog, ApologeticsHubWidget, TopicArchiveWidget, GhalySettlerWidget
from modules import topic_archive
import sys
import os
import datetime
import shutil
import re
import webbrowser
import json
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QInputDialog,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QTreeView,
    QFileSystemModel,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QAction,
    QDialog,
    QStackedWidget,
    QDialogButtonBox,
    QGroupBox,
    QGridLayout,
)
from PyQt5.QtCore import (
    Qt,
    QDir,
    QDateTime,
    QThread,
    pyqtSignal,
    QSettings,
    QObject,
    QUrl,
)
from PyQt5.QtGui import QIcon, QPixmap, QImage, QCursor
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import docx

from modules import smart_logger
from modules import apologetics_db
from modules import (
    database_handler,
    worker,
    duplicate_finder,
    ocr_handler,
    themes,
    ai_handler,
    library_organizer,
    library_rag,
    library_auditor,
    portable_config,
)
from modules.settings_dialog import SettingsDialog
from modules.rule_dialog import RuleDialog
from modules import organizer_engine, renaming_engine
from modules import translator

import fitz  # PyMuPDF


def format_size(size_bytes):
    if size_bytes is None or size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math

    try:
        if size_bytes < 1:
            return "0 B"
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    except (ValueError, OverflowError):
        return "0 B"


# --- WORKER & HELPER CLASSES ---


class DuplicateFinderWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        try:
            smart_logger.log("DuplicateFinderWorker: Starting duplicate scan...")
            duplicate_groups = duplicate_finder.find_duplicates(self.file_paths)
            smart_logger.log(
                f"DuplicateFinderWorker: Scan complete. Found {len(duplicate_groups)} groups."
            )
            self.finished.emit(duplicate_groups)
        except Exception as e:
            smart_logger.log(f"!! DuplicateFinderWorker Error: {e}")
            self.finished.emit([])


class ScanOptionsDialog(QDialog):
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan Options")
        layout = QVBoxLayout(self)
        self.checkboxes = {}
        for category in categories:
            if category == "الكل":
                continue
            checkbox = QCheckBox(category)
            checkbox.setChecked(True)
            self.checkboxes[category] = checkbox
            layout.addWidget(checkbox)
        layout.addSpacing(15)
        self.deep_scan_checkbox = QCheckBox("إجراء فحص عميق للمحتوى (أبطأ)")
        self.deep_scan_checkbox.setChecked(False)
        layout.addWidget(self.deep_scan_checkbox)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_categories(self):
        return [
            category
            for category, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def is_deep_scan_enabled(self):
        return self.deep_scan_checkbox.isChecked()


class SuggestionWorker(QObject):
    finished = pyqtSignal(list)

    def __init__(self, root_folder_id):
        super().__init__()
        self.root_folder_id = root_folder_id

    def run(self):
        smart_logger.log("Smart Organizer: Generating organization plan...")
        suggestions = organizer_engine.generate_organization_plan(
            self.root_folder_id, log_callback=smart_logger.log
        )
        self.finished.emit(suggestions)


class TranslationWorker(QObject):
    finished = pyqtSignal(str)

    def __init__(self, text, target_lang):
        super().__init__()
        self.text = text
        self.target_lang = target_lang

    def run(self):
        if not self.text:
            self.finished.emit("")
            return
        try:
            translated_text = translator.GoogleTranslator(
                source="auto", target=self.target_lang
            ).translate(self.text)
            self.finished.emit(translated_text)
        except Exception as e:
            smart_logger.log(f"!! Translation failed: {e}")
            self.finished.emit(f"Translation failed: \n{e}")


class AIWorker(QObject):
    finished_file = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.is_running = True

    def analyze_single_file(self, file_path):
        if not self.is_running:
            return None
            
        file_id = database_handler.get_file_id(file_path)
        if not file_id:
            return None

        try:
            database_handler.update_file_ai_status(file_id, "processing")
            self.finished_file.emit(file_path)

            smart_logger.log(f"AI: Analyzing {os.path.basename(file_path)}...")
            raw_text = ocr_handler.extract_text(file_path)
            if isinstance(raw_text, str) and raw_text.strip():
                if "Tesseract OCR" in raw_text:
                    smart_logger.log(
                        f"AI: Skipped {os.path.basename(file_path)} - {raw_text}"
                    )
                    database_handler.update_file_ai_status(file_id, "failed")
                    return None
                summary, tags = ai_handler.get_summary_and_tags(raw_text)
                database_handler.update_file_with_ai_data(file_id, summary, tags)
                
                database_handler.update_file_ai_status(file_id, "completed")
                smart_logger.log(
                    f"AI: Analysis complete for {os.path.basename(file_path)}"
                )
                return file_path
            else:
                smart_logger.log(
                    f"AI: No text content to analyze in {os.path.basename(file_path)}"
                )
                database_handler.update_file_ai_status(file_id, "failed")
                return None
        except Exception as e:
            smart_logger.log(
                f"!! AI: Error analyzing file {os.path.basename(file_path)}: {e}"
            )
            if file_id:
                database_handler.update_file_ai_status(file_id, "failed")
            return None

    def run(self):
        smart_logger.log(
            f"AI: Starting parallel analysis for {len(self.file_paths)} file(s)..."
        )
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.analyze_single_file, path): path
                for path in self.file_paths
            }
            for future in futures:
                if not self.is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    smart_logger.log("AI analysis was cancelled by the user.")
                    for file_path in self.file_paths:
                        file_id = database_handler.get_file_id(file_path)
                        if file_id:
                            details = database_handler.get_file_details_for_ai(file_path)
                            if details and details[-1] == 'processing':
                                database_handler.update_file_ai_status(file_id, 'pending')
                    break
                result_path = future.result()
                if result_path:
                    self.finished_file.emit(result_path)
        smart_logger.log("AI: All smart analysis operations are complete.")
        self.finished_all.emit()

    def stop(self):
        self.is_running = False


class ChurchAssistantWorker(QObject):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, question, context_text="", depth_mode="scholar"):
        super().__init__()
        self.question = question
        self.context_text = context_text
        self.depth_mode = depth_mode

    def run(self):
        try:
            smart_logger.log(f"ChurchAssistant: Processing question (depth={self.depth_mode}): {self.question[:60]}...")
            answer = ai_handler.ask_church_assistant(self.question, self.context_text, depth_mode=self.depth_mode)
            self.response_ready.emit(answer)
        except Exception as e:
            smart_logger.log(f"!! ChurchAssistant Error: {e}")
            self.error_occurred.emit(str(e))


class LibraryTaskWorker(QObject):
    task_finished = pyqtSignal(str, bool)

    def __init__(self, task_type, directory):
        super().__init__()
        self.task_type = task_type
        self.directory = directory

    def run(self):
        try:
            if self.task_type == "settle":
                books, temp = library_organizer.settle_loose_files(self.directory, log_callback=smart_logger.log)
                msg = f"اكتمل التسكين والترتيب بنجاح:\n• تم تسكين {books} كتاب في مجلداتها المخصصة.\n• تم نقل {temp} ملف مؤقت إلى مجلد المهملات المؤقتة."
                self.task_finished.emit(msg, True)
            elif self.task_type == "excel":
                count = library_organizer.update_library_excel_catalog(self.directory, log_callback=smart_logger.log)
                msg = f"تم تحديث وبناء فهرس الإكسيل التفاعلي بنجاح!\nإجمالي الكتب والملفات المفهرسة: {count} ملف."
                self.task_finished.emit(msg, True)
        except Exception as e:
            smart_logger.log(f"!! LibraryTaskWorker Error: {e}")
            self.task_finished.emit(f"حدث خطأ أثناء تنفيذ العملية:\n{str(e)}", False)


class DataLoaderWorker(QObject):
    finished = pyqtSignal(object, object)

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

    def run(self):
        categorized_data, all_files_data = (
            database_handler.get_categorized_files_with_details(self.project_id)
        )
        self.finished.emit(categorized_data, all_files_data)


class DropEnabledTreeView(QTreeView):
    files_moved = pyqtSignal()

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        dest_index = self.indexAt(event.pos())
        if not dest_index.isValid():
            return
        dest_path = self.model().filePath(dest_index)
        if not os.path.isdir(dest_path):
            dest_path = os.path.dirname(dest_path)
        source_paths = self.main_window.get_selected_file_paths_from_active_table()
        for source_path in source_paths:
            if not source_path or not os.path.exists(source_path):
                continue
            file_name = os.path.basename(source_path)
            new_dest_path = os.path.join(dest_path, file_name)
            if (
                source_path == new_dest_path
                or os.path.dirname(source_path) == dest_path
            ):
                continue
            if os.path.exists(new_dest_path):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(f"The file '{file_name}' already exists.")
                msg_box.setInformativeText("What would you like to do?")
                overwrite_btn = msg_box.addButton("Replace", QMessageBox.YesRole)
                rename_btn = msg_box.addButton("Auto-Rename", QMessageBox.ActionRole)
                skip_btn = msg_box.addButton("Skip", QMessageBox.NoRole)
                msg_box.exec_()
                if msg_box.clickedButton() == skip_btn:
                    continue
                elif msg_box.clickedButton() == rename_btn:
                    base, ext = os.path.splitext(file_name)
                    i = 1
                    while os.path.exists(new_dest_path):
                        new_dest_path = os.path.join(dest_path, f"{base} ({i}){ext}")
                        i += 1
            try:
                self.main_window.release_previewed_file(source_path)
                shutil.move(source_path, new_dest_path)
                database_handler.update_file_path(source_path, new_dest_path)
                file_id = database_handler.get_file_id(new_dest_path)
                if file_id:
                    database_handler.log_user_action(file_id, "move", dest_path)
                smart_logger.log(f"Moved '{file_name}' to '{dest_path}'")
            except Exception as e:
                smart_logger.log(f"!! Failed to move file {file_name}: {e}")
        self.files_moved.emit()


class RulesManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rule Manager")
        self.setGeometry(200, 200, 800, 500)
        layout = QVBoxLayout(self)
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(5)
        self.rules_table.setHorizontalHeaderLabels(
            ["Condition", "Value", "Action", "Destination/Value", "Priority"]
        )
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.rules_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rules_table)
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add New Rule")
        edit_button = QPushButton("Edit Selected Rule")
        delete_button = QPushButton("Delete Selected Rule")
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)
        add_button.clicked.connect(self.add_rule)
        edit_button.clicked.connect(self.edit_rule)
        delete_button.clicked.connect(self.delete_rule)
        self.load_rules()

    def load_rules(self):
        self.rules_table.setRowCount(0)
        rules = database_handler.get_all_rules()
        for rule in rules:
            row_pos = self.rules_table.rowCount()
            self.rules_table.insertRow(row_pos)
            (
                rule_id,
                condition_type,
                condition_value,
                action_type,
                action_value,
                priority,
            ) = rule
            self.rules_table.setItem(row_pos, 0, QTableWidgetItem(condition_type))
            self.rules_table.setItem(row_pos, 1, QTableWidgetItem(condition_value))
            self.rules_table.setItem(row_pos, 2, QTableWidgetItem(action_type))
            self.rules_table.setItem(row_pos, 3, QTableWidgetItem(action_value))
            self.rules_table.setItem(row_pos, 4, QTableWidgetItem(str(priority)))
            self.rules_table.item(row_pos, 0).setData(Qt.UserRole, rule_id)

    def add_rule(self):
        dialog = RuleDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_rule_data()
            database_handler.add_rule(**data)
            self.load_rules()

    def edit_rule(self):
        current_row = self.rules_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select a rule to edit.")
            return
        rule_id = self.rules_table.item(current_row, 0).data(Qt.UserRole)
        rule_data = {
            "condition_type": self.rules_table.item(current_row, 0).text(),
            "condition_value": self.rules_table.item(current_row, 1).text(),
            "action_type": self.rules_table.item(current_row, 2).text(),
            "action_value": self.rules_table.item(current_row, 3).text(),
            "priority": int(self.rules_table.item(current_row, 4).text()),
        }
        dialog = RuleDialog(rule_data, self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_rule_data()
            database_handler.update_rule(rule_id, **new_data)
            self.load_rules()

    def delete_rule(self):
        current_row = self.rules_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select a rule to delete.")
            return
        rule_id = self.rules_table.item(current_row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this rule?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            database_handler.delete_rule(rule_id)
            self.load_rules()


class RenamingAssistantDialog(QDialog):
    def __init__(self, main_window, root_folder_id):
        super().__init__(main_window)
        self.main_window = main_window
        self.root_folder_id = root_folder_id
        self.setWindowTitle("Smart Renaming Assistant")
        self.setGeometry(150, 150, 1000, 700)
        self.worker_thread = None
        self.suggestion_worker = None
        layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        self.find_button = QPushButton("🔍 Find Files to Rename")
        self.apply_button = QPushButton("✅ Apply Selected Changes")
        self.apply_button.setEnabled(False)
        top_layout.addWidget(self.find_button)
        top_layout.addStretch()
        top_layout.addWidget(self.apply_button)
        self.rename_table = QTableWidget()
        self.rename_table.setColumnCount(3)
        self.rename_table.setHorizontalHeaderLabels(
            ["Current Name", "Suggested Name (Editable)", "Path"]
        )
        header = self.rename_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addLayout(top_layout)
        layout.addWidget(self.rename_table)
        self.find_button.clicked.connect(self.find_files)
        self.apply_button.clicked.connect(self.apply_changes)
        self.rename_table.currentItemChanged.connect(self.on_item_selected)

    def find_files(self):
        self.rename_table.setRowCount(0)
        self.find_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        smart_logger.log("Renaming Assistant: Starting search for files...")
        
        self.worker_thread = QThread()
        self.suggestion_worker = RenameSuggestionWorker(self.root_folder_id)
        self.suggestion_worker.moveToThread(self.worker_thread)
        
        self.suggestion_worker.suggestion_ready.connect(self.add_suggestion_to_table)
        self.suggestion_worker.finished.connect(self.on_finding_finished)
        self.worker_thread.started.connect(self.suggestion_worker.run)
        
        self.worker_thread.start()

    def add_suggestion_to_table(self, original_path, original_name, suggested_name):
        row_pos = self.rename_table.rowCount()
        self.rename_table.insertRow(row_pos)
        current_name_item = QTableWidgetItem(original_name)
        current_name_item.setData(Qt.UserRole, original_path)
        current_name_item.setFlags(current_name_item.flags() & ~Qt.ItemIsEditable)
        suggested_name_item = QTableWidgetItem(suggested_name)
        path_item = QTableWidgetItem(os.path.dirname(original_path))
        path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
        self.rename_table.setItem(row_pos, 0, current_name_item)
        self.rename_table.setItem(row_pos, 1, suggested_name_item)
        self.rename_table.setItem(row_pos, 2, path_item)
        self.rename_table.scrollToBottom()

    def on_finding_finished(self, count):
        smart_logger.log(
            f"Renaming Assistant: Search complete. Found {count} files to suggest names for."
        )
        self.find_button.setEnabled(True)
        if count > 0:
            self.apply_button.setEnabled(True)
            
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.suggestion_worker = None

    def on_item_selected(self, current_item, previous_item):
        if not current_item:
            return
        row = current_item.row()
        path_item = self.rename_table.item(row, 0)
        if path_item:
            full_path = path_item.data(Qt.UserRole)
            self.main_window.update_details_panel_with_path(full_path)

    def apply_changes(self):
        rename_list = []
        for row in range(self.rename_table.rowCount()):
            old_path = self.rename_table.item(row, 0).data(Qt.UserRole)
            suggested_name = self.rename_table.item(row, 1).text().strip()
            if suggested_name:
                rename_list.append((old_path, suggested_name))
        if not rename_list:
            QMessageBox.warning(self, "No Changes", "There are no new names to apply.")
            return
        reply = QMessageBox.question(
            self,
            "Confirm Rename",
            f"Are you sure you want to rename {len(rename_list)} files?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            renamed_count = 0
            failed_items = []
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            for old_path, new_base_name in rename_list:
                try:
                    self.main_window.rename_file(old_path, new_base_name)
                    renamed_count += 1
                except Exception as e:
                    failed_items.append(f"{os.path.basename(old_path)}: {e}")
                    smart_logger.log(
                        f"!! Failed to rename {os.path.basename(old_path)}: {e}"
                    )
            QApplication.restoreOverrideCursor()
            
            QMessageBox.information(self, "Rename Complete", f"Successfully renamed {renamed_count} files.\nFailed to rename {len(failed_items)} files.")
            self.close()

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            smart_logger.log("Closing Renaming Assistant: Stopping worker thread...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if self.suggestion_worker:
                self.suggestion_worker.stop()
            self.worker_thread.quit()
            self.worker_thread.wait() # Wait indefinitely until the thread finishes
            QApplication.restoreOverrideCursor()
        event.accept()


class RenameSuggestionWorker(QObject):
    suggestion_ready = pyqtSignal(str, str, str)
    finished = pyqtSignal(int)

    def __init__(self, root_folder_id):
        super().__init__()
        self.root_folder_id = root_folder_id
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        files_to_rename = renaming_engine.find_files_to_rename(self.root_folder_id)
        count = 0
        if not self.is_running:
            self.finished.emit(0)
            return

        for file_path, file_name in files_to_rename:
            if not self.is_running:
                smart_logger.log("RenameSuggestionWorker was stopped.")
                break
            suggested_name = renaming_engine.suggest_new_name(file_path)
            if suggested_name:
                self.suggestion_ready.emit(file_path, file_name, suggested_name)
                count += 1
        self.finished.emit(count)


class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        sort_column = self.treeWidget().sortColumn()
        self_data = self.data(sort_column, Qt.UserRole)
        other_data = other.data(sort_column, Qt.UserRole)
        if self_data is None or other_data is None:
            return self.text(sort_column).lower() < other.text(sort_column).lower()
        try:
            if sort_column in [1, 2]:
                return self_data < other_data
        except TypeError:
            pass
        return self.text(sort_column).lower() < other.text(sort_column).lower()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        smart_logger.log("Application starting...")
        self.setWindowTitle("برنامج الأرشفة الذكي - ArchiveMaster")
        self.setWindowIcon(QIcon("app_icon.png"))
        self.setGeometry(100, 100, 1600, 900)
        database_handler.initialize_database()
        self.projects = {}
        self.current_project_id = None
        self.current_working_directory = None
        self.all_files_data = []
        self.worker_thread = None
        self.scan_worker = None
        self.suggestion_thread = None
        self.suggestion_worker = None
        self.ai_worker_thread = None
        self.ai_worker = None
        self.data_loader_thread = None
        self.dup_thread = None
        self.dup_worker = None
        self.church_assistant_thread = None
        self.church_assistant_worker = None
        self.library_task_thread = None
        self.library_task_worker = None
        self.currently_selected_file_path = None
        self.preview_doc = None
        self.preview_current_page = 0
        self.source_text_edit_for_translation = None
        self.categories = [
            "الكل",
            "📄 PDF",
            "📄 مستندات Word",
            "🖥️ عروض تقديمية",
            "📊 جداول بيانات",
            "📝 ملفات نصية",
            "🌐 صفحات ويب",
            "🗜️ ملفات مضغوطة",
            "🎬 فيديو",
            "🎵 صوت",
            "🖼️ صور",
        ]
        self.setup_ui()
        self.load_projects()
        smart_logger.handler.message_logged.connect(self.append_to_internal_log)
        smart_logger.log("UI setup complete. Application is ready.")

    def append_to_internal_log(self, message):
        self.log_text_area.append(message)
        self.log_text_area.verticalScrollBar().setValue(self.log_text_area.verticalScrollBar().maximum())

    def closeEvent(self, event):
        smart_logger.log("Close event triggered.")
        
        def is_alive(t):
            if not t:
                return False
            try:
                return bool(t.isRunning())
            except (RuntimeError, Exception):
                return False

        threads_running = False
        if is_alive(self.worker_thread):
            try: self.scan_worker.stop()
            except Exception: pass
            threads_running = True
        if is_alive(self.suggestion_thread):
            threads_running = True
        if is_alive(self.ai_worker_thread):
            try: self.ai_worker.stop()
            except Exception: pass
            threads_running = True
        if is_alive(self.dup_thread):
            threads_running = True
        if is_alive(self.church_assistant_thread):
            threads_running = True
        if is_alive(self.library_task_thread):
            threads_running = True

        if threads_running:
            reply = QMessageBox.question(
                self,
                "تأكيد الخروج",
                "هناك عمليات تعمل في الخلفية. هل تريد الخروج الآن؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                smart_logger.log("User chose to exit while threads are running.")
                QApplication.setOverrideCursor(Qt.WaitCursor)
                for t in [self.worker_thread, self.suggestion_thread, self.ai_worker_thread, self.dup_thread, self.church_assistant_thread, self.library_task_thread]:
                    if is_alive(t):
                        try:
                            t.quit()
                            t.wait(1000)
                        except Exception:
                            pass
                QApplication.restoreOverrideCursor()
                event.accept()
            else:
                smart_logger.log("User canceled exit.")
                event.ignore()
        else:
            smart_logger.log("Application closing normally.")
            event.accept()


    # --- MODERN DASHBOARD & PANEL MANAGEMENT ---

    def create_kpi_card(self, title, main_val, sub_val, border_col, text_col):
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #1E293B;
                border: 1px solid {border_col};
                border-radius: 10px;
            }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(4)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; font-weight: 600; border: none; background: transparent;")
        
        v_lbl = QLabel(main_val)
        v_lbl.setObjectName("KPIValue")
        v_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {text_col}; border: none; background: transparent;")
        
        s_lbl = QLabel(sub_val)
        s_lbl.setObjectName("KPISub")
        s_lbl.setStyleSheet("font-size: 11px; color: #64748B; border: none; background: transparent;")
        
        l.addWidget(t_lbl)
        l.addWidget(v_lbl)
        l.addWidget(s_lbl)
        return card

    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # 1. Header Banner
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 16, 12)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #0F172A);
                border-radius: 10px;
                border: 1px solid #3B82F6;
            }
        """)
        
        cross_lbl = QLabel("✠")
        cross_lbl.setStyleSheet("font-size: 32px; color: #D4AF37; font-weight: bold; background: transparent; border: none;")
        
        t_layout = QVBoxLayout()
        t_layout.setSpacing(4)
        main_title = QLabel("مكتبة الصليب القبطية الأرثوذكسية - المركز الرقمي الذكي")
        main_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF; background: transparent; border: none;")
        self.dash_status_lbl = QLabel("النسخة المطورة | نظام الفهرسة والتسكين التلقائي والمساعد اللاهوتي والدفاعي")
        self.dash_status_lbl.setStyleSheet("font-size: 12px; color: #93C5FD; background: transparent; border: none;")
        t_layout.addWidget(main_title)
        t_layout.addWidget(self.dash_status_lbl)
        
        h_layout.addWidget(cross_lbl)
        h_layout.addLayout(t_layout, 1)
        layout.addWidget(header)

        # 2. KPI Cards Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self.card_books = self.create_kpi_card("📚 إجمالي الكتب والمخطوطات", "7,200+", "مرجع كنسي أصيل مفهرس", "#1E3A8A", "#60A5FA")
        self.card_size = self.create_kpi_card("📄 الصفحات والفقرات المفهرسة", "+1,800,000", "صفحة FTS5 صفر هلوسة", "#065F46", "#34D399")
        self.card_cats = self.create_kpi_card("📂 التصنيفات الآبائية والكنسية", "38", "قسماً لاهوتياً معتمداً", "#831843", "#F472B6")
        self.card_ai = self.create_kpi_card("⚡ محرك البحث والذكاء", "متصل وجاهز", "ELANTONY AI Engine", "#78350F", "#FBBF24")

        kpi_row.addWidget(self.card_books)
        kpi_row.addWidget(self.card_size)
        kpi_row.addWidget(self.card_cats)
        kpi_row.addWidget(self.card_ai)
        layout.addLayout(kpi_row)

        # 3. Master Operational Hubs (الأركان التشغيلية الـ 4 المعتمدة)
        actions_group = QGroupBox("🏛️ مراكز التشغيل والأبحاث الكنسية الأربعة")
        actions_layout = QGridLayout(actions_group)
        actions_layout.setContentsMargins(14, 16, 14, 14)
        actions_layout.setSpacing(14)

        # Hub 1: ELANTONY AI Hub (بوابة الأبحاث اللاهوتية والذكاء الاصطناعي)
        btn_hub_ai = QPushButton("🏛️ 1. بوابة الأبحاث اللاهوتية والذكاء الاصطناعي\n(ELANTONY AI Monograph && Research Portal)")
        btn_hub_ai.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #78350F, stop:1 #9A3412);
                color: #FFFFFF; padding: 18px 14px; font-size: 13.5px; font-weight: bold; border-radius: 8px; border: 1px solid #F59E0B;
                text-align: center;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9A3412, stop:1 #B45309); border-color: #FDE68A; }
        """)
        btn_hub_ai.setToolTip("بوابة الأبحاث اللاهوتية الذكية الكاملة: حوار آبائي، تصدير أطروحات Word، نمط طباعة A4، وضع القراءة والتركيز، وفهرسة الشواهد الموثقة صفر هلوسة.")
        btn_hub_ai.clicked.connect(self.launch_elantony_ai_portal)

        # Hub 2: Omnibox & Patristic Reader (محرك الاستكشاف الشامل والمستعرض الآبائي)
        btn_hub_reader = QPushButton("🔍 2. محرك الاستكشاف الشامل والمستعرض الآبائي\n(Omnibox 360° && Patristic Reader)")
        btn_hub_reader.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);
                color: #FFFFFF; padding: 18px 14px; font-size: 13.5px; font-weight: bold; border-radius: 8px; border: 1px solid #38BDF8;
                text-align: center;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #3B82F6); border-color: #BAE6FD; }
        """)
        btn_hub_reader.setToolTip("البحث الفوري الشامل في بطون وعناوين الـ 7,200+ كتاب ومخطوط، وقراءة صفحات PDF بدقة عالية واستخراج التوثيقات الحرفية.")
        btn_hub_reader.clicked.connect(lambda: self.show_omnibox_dialog())

        # Hub 3: Apologetics Fortress (منصة الدفاعيات وموسوعة الرد على الشبهات)
        btn_hub_apologetics = QPushButton("🛡️ 3. منصة الدفاعيات وموسوعة الرد على الشبهات\n(Apologetics Fortress && Theological Defense)")
        btn_hub_apologetics.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E40AF, stop:1 #1D4ED8);
                color: #FFFFFF; padding: 18px 14px; font-size: 13.5px; font-weight: bold; border-radius: 8px; border: 1px solid #60A5FA;
                text-align: center;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #3B82F6); border-color: #BFDBFE; }
        """)
        btn_hub_apologetics.setToolTip("موسوعة الدفاعيات والردود العلمية واللاهوتية الموثقة على الشبهات وأرشيف الأبحاث التراكمي ومقارنة المخطوطات.")
        btn_hub_apologetics.clicked.connect(self.show_apologetics_hub_dialog)

        # Hub 4: Library Ingestion & Maintenance (مركز إضافة الكتب وصيانة الفهرسة والتسكين)
        btn_hub_maintenance = QPushButton("📥 4. مركز إضافة الكتب وصيانة الفهرسة والتسكين\n(Library Ingestion, OCR && Maintenance)")
        btn_hub_maintenance.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #065F46, stop:1 #0D9488);
                color: #FFFFFF; padding: 18px 14px; font-size: 13.5px; font-weight: bold; border-radius: 8px; border: 1px solid #34D399;
                text-align: center;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0D9488, stop:1 #10B981); border-color: #A7F3D0; }
        """)
        btn_hub_maintenance.setToolTip("إضافة كتب جديدة للمكتبة، الفحص التلقائي، استخراج النصوص بالـ OCR، وتحديث الفهرس التفاعلي والبيان الحي.")
        btn_hub_maintenance.clicked.connect(self.show_library_maintenance_hub)

        actions_layout.addWidget(btn_hub_ai, 0, 0)
        actions_layout.addWidget(btn_hub_reader, 0, 1)
        actions_layout.addWidget(btn_hub_apologetics, 1, 0)
        actions_layout.addWidget(btn_hub_maintenance, 1, 1)

        layout.addWidget(actions_group)

        # 4. Overview Information Box
        info_group = QGroupBox("ℹ️ دليل النظام والمكتبة الرقمية")
        info_layout = QVBoxLayout(info_group)
        info_lbl = QLabel(
            "• المكتبة مقسمة بانتظام وتضم كافة التخصصات الكنسية المعتمدة (آبائيات، عقيدة، طقوس، تاريخ، تفاسير، وألحان).\n"
            "• تضم المنظومة أكثر من 7,200 كتاب ومخطوط كنسي موثق ومفهرس حرفياً في محرك FTS5 (صفر هلوسة).\n"
            "• لبدء حوار بحثي وتوليد أطروحات Word أو طباعة A4، اضغط على زر 'بوابة الأبحاث اللاهوتية ELANTONY AI'."
        )
        info_lbl.setStyleSheet("color: #CBD5E1; font-size: 12px; line-height: 1.8;")
        info_layout.addWidget(info_lbl)
        layout.addWidget(info_group)

        layout.addStretch()
        return page

    def create_portal_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B18, stop:1 #2D241E);
                border: 1px solid #78350F;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(14)

        t_lbl = QLabel("🏛️ بوابة الأبحاث اللاهوتية والذكاء الاصطناعي — ELANTONY AI")
        t_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #F59E0B; background: transparent; border: none;")
        h_layout.addWidget(t_lbl)

        desc_lbl = QLabel(
            "المنظومة المتقدمة لبناء الأطروحات وصياغة الدراسات الآبائية الموثقة بالشواهد والصفحات من بطون أمهات الكتب الكنسية:\n"
            "• دعم 3 ثيمات مريحة للعين: 📜 برديات دافئة | 🌙 ليلي هادئ | ☀️ ورقي ناصع.\n"
            "• تصدير فوري بنقرة واحدة كملف Word منسق ومفهرس بالكامل.\n"
            "• نمط المعاينة والطباعة النشرية A4 لطباعة البحث كاملاً فوراً.\n"
            "• وضع القراءة والتركيز (Focus Reading Mode) لقراءة هادئة ومريحة.\n"
            "• توثيق حرفي مع فتح صفحة الـ PDF الأصلية بتظليل ذهبي على النص المستشهد به."
        )
        desc_lbl.setStyleSheet("font-size: 13px; color: #E2E8F0; line-height: 1.8; background: transparent; border: none;")
        h_layout.addWidget(desc_lbl)

        btn_launch = QPushButton("🚀 فتح بوابة الأبحاث اللاهوتية الكاملة (http://localhost:8000/)")
        btn_launch.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #78350F, stop:1 #9A3412);
                color: #FFFFFF; padding: 14px 24px; font-size: 14px; font-weight: bold; border-radius: 8px; border: 1px solid #F59E0B;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9A3412, stop:1 #B45309);
                border-color: #FDE68A;
            }
        """)
        btn_launch.clicked.connect(self.launch_elantony_ai_portal)
        h_layout.addWidget(btn_launch)

        layout.addWidget(header)
        layout.addStretch()
        return page

    def launch_elantony_ai_portal(self):
        """Launches ELANTONY AI Research Portal at http://localhost:8000/."""
        import webbrowser
        import urllib.request
        server_ready = False
        try:
            res = urllib.request.urlopen("http://localhost:8000/", timeout=1.5)
            if res.status == 200:
                server_ready = True
        except Exception:
            pass

        if not server_ready:
            smart_logger.log("Starting ELANTONY AI background web server...")
            import subprocess
            cmd = [sys.executable, "-m", "uvicorn", "elantony.web.api:app", "--host", "0.0.0.0", "--port", "8000"]
            subprocess.Popen(cmd, cwd=portable_config.get_app_dir(), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            import time
            time.sleep(1.2)

        webbrowser.open("http://localhost:8000/")
        self.statusBar().showMessage("تم فتح بوابة الأبحاث اللاهوتية الذكية (ELANTONY AI) في المتصفح بنجاح.", 6000)

    def update_kpi_metrics(self):
        if not hasattr(self, "card_books"):
            return
        b_count = 3639
        p_count = 377026
        try:
            conn = database_handler.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), SUM(page_count) FROM church_books WHERE is_duplicate_of IS NULL")
            row = cur.fetchone()
            if row and row[0]:
                b_count = row[0]
                if row[1]:
                    p_count = row[1]
            conn.close()
        except Exception as e:
            smart_logger.log(f"Notice reading church KPI metrics: {e}")

        lbl_b = self.card_books.findChild(QLabel, "KPIValue")
        if lbl_b:
            lbl_b.setText("7,200+")
        sub_b = self.card_books.findChild(QLabel, "KPISub")
        if sub_b:
            sub_b.setText(f"{b_count:,} مجلداً كنسياً مفهرساً")

        lbl_s = self.card_size.findChild(QLabel, "KPIValue")
        if lbl_s:
            lbl_s.setText("+1,800,000")
        sub_s = self.card_size.findChild(QLabel, "KPISub")
        if sub_s:
            sub_s.setText(f"{p_count:,} صـ في FTS5 صفر هلوسة")

        lbl_c = self.card_cats.findChild(QLabel, "KPIValue")
        if lbl_c:
            lbl_c.setText("38")
        sub_c = self.card_cats.findChild(QLabel, "KPISub")
        if sub_c:
            sub_c.setText("تصنيفاً لاهوتياً معتمداً")

        if hasattr(self, "dash_status_lbl"):
            self.dash_status_lbl.setText(f"المكتبة الكنسية المعتمدة | 7,200+ مرجعاً موثقاً و 38 تصنيفاً لاهوتياً وآبائياً")

    def create_all_panels(self):
        self.content_stack = QStackedWidget()
        self.tabs = self.content_stack
        self.file_tables = {}

        # 0. Dashboard Page
        self.dashboard_page = self.create_dashboard_page()
        self.content_stack.addWidget(self.dashboard_page)

        # 1. ELANTONY AI Portal Hub
        self.portal_page = self.create_portal_page()
        self.content_stack.addWidget(self.portal_page)

        # 2. Books & Documents Hub
        self.books_tab_widget = QTabWidget()
        book_categories = ["📄 PDF", "📄 مستندات Word", "🖥️ عروض تقديمية", "📊 جداول بيانات", "📝 ملفات نصية"]
        for tab_name in book_categories:
            tbl = self.create_file_table()
            self.books_tab_widget.addTab(tbl, tab_name)
            self.file_tables[tab_name] = tbl
        self.content_stack.addWidget(self.books_tab_widget)

        # 3. Apologetics Hub
        church_tab = self.create_church_assistant_tab()
        self.content_stack.addWidget(church_tab)

        # 4. Search & OCR Hub
        self.search_tab_widget = QTabWidget()
        search_tab = self.create_search_tab()
        ocr_tab = self.create_ocr_tab()
        self.search_tab_widget.addTab(search_tab, "🔍 البحث الشامل في الفهرس")
        self.search_tab_widget.addTab(ocr_tab, "📄 استخراج النصوص (OCR)")
        self.content_stack.addWidget(self.search_tab_widget)

        # 5. Tools & Maintenance Hub
        self.tools_tab_widget = QTabWidget()
        organizer_tab = self.create_organizer_tab()
        dup_tab = self.create_duplicates_tab()
        smart_org_tab = self.create_smart_organize_tab()
        log_tab = self.create_log_tab()
        self.tools_tab_widget.addTab(organizer_tab, "🗂️ تنظيم الملفات")
        self.tools_tab_widget.addTab(dup_tab, "👯 الملفات المكررة")
        self.tools_tab_widget.addTab(smart_org_tab, "🤖 التنظيم الذكي")
        self.tools_tab_widget.addTab(log_tab, "📜 سجل النشاط")
        self.tools_tab_widget.currentChanged.connect(self.on_tools_tab_changed)
        self.content_stack.addWidget(self.tools_tab_widget)

    def on_sidebar_changed(self, row):
        if hasattr(self, "content_stack"):
            self.content_stack.setCurrentIndex(row)
            if row == 0:
                self.update_kpi_metrics()
            elif row == 1:
                self.launch_elantony_ai_portal()
            if row == 0:
                self.update_kpi_metrics()

    def switch_sidebar_to(self, index):
        if hasattr(self, "sidebar"):
            self.sidebar.setCurrentRow(index)

    def on_tools_tab_changed(self, index):
        if hasattr(self, "tools_tab_widget") and self.tools_tab_widget.tabText(index) == "👯 الملفات المكررة":
            self.load_duplicates_cache()

    def setup_ui(self):
        self.create_menu_bar()
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Top Bar Header
        top_bar_widget = QWidget()
        top_bar_widget.setStyleSheet("""
            QWidget {
                background-color: #090D16;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        top_bar_layout = QHBoxLayout(top_bar_widget)
        top_bar_layout.setContentsMargins(12, 6, 12, 6)
        top_bar_layout.setSpacing(10)

        cross_title = QLabel("✠ مكتبة الصليب القبطية")
        cross_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #D4AF37; border: none; background: transparent;")
        top_bar_layout.addWidget(cross_title)

        top_bar_layout.addSpacing(15)
        lbl_proj = QLabel("المشروع:")
        lbl_proj.setStyleSheet("font-weight: bold; color: #CBD5E1; border: none; background: transparent;")
        top_bar_layout.addWidget(lbl_proj)

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(220)
        add_project_button = QPushButton("➕ إضافة مشروع")
        self.analyze_button = QPushButton("🔄 فحص وتحديث")
        self.analyze_button.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        
        self.settle_button = QPushButton("📥 تسكين الوارد")
        self.settle_button.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        self.settle_button.setToolTip("تسكين الكتب والملفات الجديدة المتناثرة في المجلد الرئيسي إلى أقسامها الكنسية تلقائياً")
        self.settle_button.clicked.connect(self.run_settle_files)
        self.settle_button.setEnabled(False)

        self.update_excel_button = QPushButton("📊 تحديث الإكسيل")
        self.update_excel_button.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold;")
        self.update_excel_button.setToolTip("إعادة بناء وتحديث فهرس الإكسيل التفاعلي المبوب لكل أقسام المكتبة")
        self.update_excel_button.clicked.connect(self.run_update_excel)
        self.update_excel_button.setEnabled(False)

        refresh_button = QPushButton("🔄 تحديث العرض")

        self.cancel_button = QPushButton("❌ إلغاء العملية")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_ai_analysis)

        top_bar_layout.addWidget(self.project_combo, 1)
        top_bar_layout.addWidget(add_project_button)
        top_bar_layout.addWidget(self.analyze_button)
        top_bar_layout.addWidget(self.settle_button)
        top_bar_layout.addWidget(self.update_excel_button)
        top_bar_layout.addWidget(refresh_button)
        top_bar_layout.addWidget(self.cancel_button)

        main_layout.addWidget(top_bar_widget)

        # 2. Main Body with Splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Sidebar Navigation
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SidebarList")
        self.sidebar.setFixedWidth(210)
        self.sidebar.setFocusPolicy(Qt.NoFocus)

        sidebar_items = [
            ("🏠 الرئيسية والمؤشرات", "لوحة الإحصائيات الشاملة والمراكز التشغيلية"),
            ("🏛️ بوابة الأبحاث الذكية AI", "بوابة الأبحاث اللاهوتية الذكية وصياغة الأطروحات A4 / Word"),
            ("📚 الكتب والمستندات المفهرسة", "استعراض والبحث في الـ 7,200+ كتاب ومخطوط كنسي"),
            ("🛡️ موسوعة الدفاعيات والردود", "استوديو تفنيد الشبهات والأرشيف الدفاعي التراكمي"),
            ("🔍 البحث الشامل والـ OCR", "محرك الاستكشاف العميق واستخراج نصوص الصور"),
            ("🛠️ صيانة المكتبة وتسكين الوارد", "إضافة كتب جديدة، فحص التكرارات، وتحديث الفهارس"),
        ]

        for title, tooltip in sidebar_items:
            item = QListWidgetItem(title)
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)

        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)

        # Center Content Container
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        center_layout.addWidget(self.progress_bar)

        self.create_all_panels()
        center_layout.addWidget(self.content_stack, 1)

        self.create_details_panel()

        main_splitter.addWidget(self.sidebar)
        main_splitter.addWidget(center_container)
        main_splitter.addWidget(self.details_panel)
        main_splitter.setSizes([210, 1050, 340])

        main_layout.addWidget(main_splitter, 1)

        # Connections
        add_project_button.clicked.connect(self.add_new_project)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        self.analyze_button.clicked.connect(self.start_analysis_thread)
        self.analyze_button.setEnabled(False)
        refresh_button.clicked.connect(self.load_data_from_db)

        self.sidebar.setCurrentRow(0)

    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == "👯 الملفات المكررة":
            self.load_duplicates_cache()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("ملف")
        add_project_action = QAction("إضافة مشروع جديد...", self)
        add_project_action.triggered.connect(self.add_new_project)
        file_menu.addAction(add_project_action)

        update_path_action = QAction("تحديث مسار المشروع...", self)
        update_path_action.triggered.connect(self.update_project_path)
        file_menu.addAction(update_path_action)
        
        settings_action = QAction("الإعدادات...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        exit_action = QAction("خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tools_menu = menu_bar.addMenu("أدوات")
        rules_action = QAction("إدارة قواعد التنظيم", self)
        rules_action.triggered.connect(self.open_rules_manager)
        tools_menu.addAction(rules_action)
        
        smart_organize_action = QAction("تنفيذ التنظيم الذكي", self)
        smart_organize_action.triggered.connect(self.generate_suggestions)
        tools_menu.addAction(smart_organize_action)
        
        tools_menu.addSeparator()
        
        rename_assistant_action = QAction("مساعد إعادة التسمية الذكي", self)
        rename_assistant_action.triggered.connect(self.open_renaming_assistant)
        tools_menu.addAction(rename_assistant_action)
        
        tools_menu.addSeparator()
        settle_action = QAction("📥 تسكين وترتيب الوارد للمجلدات الكنسية", self)
        settle_action.triggered.connect(self.run_settle_files)
        tools_menu.addAction(settle_action)

        excel_action = QAction("📊 تحديث فهرس الإكسيل التفاعلي المبوب", self)
        excel_action.triggered.connect(self.run_update_excel)
        tools_menu.addAction(excel_action)

        tools_menu.addSeparator()
        rebuild_index_action = QAction("إعادة بناء فهرس البحث السريع", self)
        rebuild_index_action.triggered.connect(self.rebuild_search_index)
        tools_menu.addAction(rebuild_index_action)

        help_menu = menu_bar.addMenu("مساعدة")
        about_action = QAction("حول البرنامج", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    def rebuild_search_index(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "لا يوجد مشروع", "يرجى اختيار مشروع أولاً.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد إعادة بناء الفهرس",
            "هذه العملية ستقوم بإعادة بناء فهرس البحث السريع. قد تستغرق بعض الوقت للمشاريع الكبيرة. هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            smart_logger.log("User started FTS index rebuild.")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            success = database_handler.rebuild_fts_index()
            QApplication.restoreOverrideCursor()
            if success:
                QMessageBox.information(self, "اكتمل", "تمت إعادة بناء فهرس البحث بنجاح.")
                smart_logger.log("FTS index rebuild completed successfully.")
            else:
                QMessageBox.critical(self, "خطأ", "حدث خطأ أثناء إعادة بناء الفهرس. راجع السجل للمزيد من التفاصيل.")
                smart_logger.log("!! FTS index rebuild failed.")
                
    def update_project_path(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "لا يوجد مشروع", "يرجى اختيار مشروع لتحديث مساره.")
            return
        
        current_project_name = self.project_combo.currentText()
        old_path = self.projects[self.current_project_id]
        
        new_path = QFileDialog.getExistingDirectory(self, f"اختر الموقع الجديد للمشروع '{current_project_name}'", os.path.dirname(old_path))
        
        if new_path and new_path != old_path:
            reply = QMessageBox.question(self, 'تأكيد تحديث المسار', 
                                         f"هل أنت متأكد أنك تريد تحديث مسار المشروع من:\n{old_path}\nإلى:\n{new_path}؟",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                success = database_handler.update_root_folder_path(self.current_project_id, old_path, new_path)
                QApplication.restoreOverrideCursor()

                if success:
                    smart_logger.log("تم تحديث مسار المشروع بنجاح. جاري إعادة تحميل المشاريع.")
                    QMessageBox.information(self, "نجاح", "تم تحديث مسار المشروع بنجاح.")
                    self.load_projects()
                else:
                    smart_logger.log("!! فشل تحديث مسار المشروع في قاعدة البيانات.")
                    QMessageBox.critical(self, "خطأ", "حدث خطأ أثناء تحديث مسار المشروع.")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            smart_logger.log("Settings saved.")
            settings = QSettings("MyCompany", "ArchiveMaster")
            theme = settings.value("theme", "Dark")
            app_instance = QApplication.instance()
            if app_instance:
                app_instance.setStyleSheet(themes.get_theme_qss(theme))

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "حول برنامج الأرشفة الذكي",
            "<h2>ArchiveMaster</h2><p>برنامج لإدارة وأرشفة الملفات بشكل ذكي.</p>",
        )

    def open_rules_manager(self):
        dialog = RulesManager(self)
        dialog.exec_()

    def open_renaming_assistant(self):
        if not self.current_project_id:
            QMessageBox.warning(
                self, "لا يوجد مشروع", "يرجى اختيار أو إضافة مشروع أولاً."
            )
            return
        dialog = RenamingAssistantDialog(self, self.current_project_id)
        dialog.exec_()

    def add_new_project(self):
        folder_path = QFileDialog.getExistingDirectory(self, "اختر مجلد مشروع جديد")
        if folder_path and folder_path not in self.projects.values():
            dialog = ScanOptionsDialog(self.categories, self)
            if dialog.exec_() == QDialog.Accepted:
                allowed_categories = dialog.get_selected_categories()
                if not allowed_categories:
                    return
                project_id = database_handler.add_root_folder(folder_path)
                self.load_projects()
                index = self.project_combo.findData(project_id)
                if index != -1:
                    self.project_combo.setCurrentIndex(index)
                self.start_analysis_thread(allowed_categories)
        elif folder_path in self.projects.values():
            QMessageBox.information(
                self, "مشروع موجود", "هذا المجلد موجود بالفعل كـ مشروع."
            )

    def on_project_changed(self):
        if self.project_combo.count() == 0:
            self.clear_all_views()
            return
        self.current_project_id = self.project_combo.currentData()
        if self.current_project_id is not None:
            self.current_working_directory = self.projects[self.current_project_id]
            smart_logger.log(
                f"Switched to project: {os.path.basename(self.current_working_directory)}"
            )
            self.load_data_from_db()
            self.analyze_button.setEnabled(True)
            self.settle_button.setEnabled(True)
            self.update_excel_button.setEnabled(True)
            self.load_duplicates_cache()

    def load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.projects = {
            id: path for id, path in database_handler.get_all_root_folders()
        }
        if self.projects:
            for id, path in self.projects.items():
                self.project_combo.addItem(os.path.basename(path) + f" [{path}]", id)
            self.project_combo.blockSignals(False)
            self.on_project_changed()
        else:
            self.project_combo.blockSignals(False)
            self.clear_all_views()
            self.analyze_button.setEnabled(False)
            self.settle_button.setEnabled(False)
            self.update_excel_button.setEnabled(False)

    def clear_all_views(self):
        for table in self.file_tables.values():
            table.setRowCount(0)
        if hasattr(self, "organizer_table"):
            self.organizer_table.setRowCount(0)
        if hasattr(self, "search_results_table"):
            self.search_results_table.setRowCount(0)
        if hasattr(self, "duplicates_tree"):
            self.duplicates_tree.clear()
        if hasattr(self, "suggestions_tree"):
            self.suggestions_tree.clear()
        if hasattr(self, "organizer_tree_view"):
            self.organizer_tree_view.setRootIndex(self.organizer_fs_model.index(""))
        self.all_files_data = []
        self.details_panel.setVisible(False)
        smart_logger.log("All views cleared. Please select or add a project.")

    def create_all_tabs(self):
        self.create_organizer_tab()
        self.file_tables = {}
        for tab_name in self.categories[1:]:
            table_widget = self.create_file_table()
            self.tabs.addTab(table_widget, tab_name)
            self.file_tables[tab_name] = table_widget
        self.create_search_tab()
        self.create_duplicates_tab()
        self.create_smart_organize_tab()
        self.create_ocr_tab()
        self.create_church_assistant_tab()
        self.create_log_tab()

    def create_log_tab(self):
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self.log_text_area = QTextEdit()
        self.log_text_area.setReadOnly(True)
        log_layout.addWidget(self.log_text_area)
        return log_tab

    def create_search_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        options_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "ابحث بالاسم، أو #وسم، أو بالملخص الذكي..."
        )
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(
            ["بحث بالاسم والمسار فقط", "بحث متقدم (بالملخص)"]
        )
        self.search_category_combo = QComboBox()
        self.search_category_combo.addItems(self.categories)
        search_button = QPushButton("🔍 بحث")
        options_layout.addWidget(self.search_input, 1)
        options_layout.addWidget(self.search_type_combo)
        options_layout.addWidget(self.search_category_combo)
        options_layout.addWidget(search_button)
        self.search_results_table = QTableWidget()
        self.search_results_table.setColumnCount(7)
        self.search_results_table.setHorizontalHeaderLabels(
            [
                "اسم الملف",
                "نوع الملف",
                "الحجم",
                "تاريخ التعديل",
                "المجلد",
                "الوسوم",
                "الملخص الذكي",
            ]
        )
        header = self.search_results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.search_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.search_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_results_table.itemDoubleClicked.connect(self.handle_item_action)
        self.search_results_table.itemSelectionChanged.connect(
            self.on_selection_changed
        )
        search_button.clicked.connect(self.perform_search)
        layout.addLayout(options_layout)
        layout.addWidget(self.search_results_table)
        return tab

    def create_smart_organize_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        top_layout = QHBoxLayout()
        suggest_button = QPushButton("🔍 اقتراح خطة تنظيم")
        self.apply_button = QPushButton("✅ تطبيق التغييرات المحددة")
        self.apply_button.setEnabled(False)
        top_layout.addWidget(suggest_button)
        top_layout.addStretch()
        top_layout.addWidget(self.apply_button)
        self.suggestions_tree = QTreeWidget()
        self.suggestions_tree.setHeaderLabels(
            ["تنفيذ؟", "الملف", "الإجراء المقترح", "التفاصيل"]
        )
        header = self.suggestions_tree.header()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.suggestions_tree.itemSelectionChanged.connect(self.on_suggestion_selected)
        layout.addLayout(top_layout)
        layout.addWidget(self.suggestions_tree)
        suggest_button.clicked.connect(self.generate_suggestions)
        self.apply_button.clicked.connect(self.apply_selected_changes)
        return tab

    def create_duplicates_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        button_layout = QHBoxLayout()

        self.find_duplicates_button = QPushButton("البحث عن الملفات المكررة")
        self.keep_newest_button = QPushButton("تحديد الكل ما عدا الأحدث")
        self.keep_oldest_button = QPushButton("تحديد الكل ما عدا الأقدم")
        self.delete_selected_button = QPushButton("❌ حذف النسخ المحددة")

        button_layout.addWidget(self.find_duplicates_button)
        button_layout.addStretch()
        button_layout.addWidget(self.keep_newest_button)
        button_layout.addWidget(self.keep_oldest_button)
        button_layout.addWidget(self.delete_selected_button)

        self.duplicates_tree = QTreeWidget()
        self.duplicates_tree.setHeaderLabels(
            ["الملف / المسار", "الحجم", "تاريخ التعديل"]
        )
        self.duplicates_tree.setColumnWidth(0, 500)
        self.duplicates_tree.setColumnWidth(1, 120)
        self.duplicates_tree.setColumnWidth(2, 150)

        self.duplicates_tree.setSortingEnabled(True)
        self.duplicates_tree.sortByColumn(0, Qt.AscendingOrder)
        self.duplicates_tree.setContextMenuPolicy(Qt.CustomContextMenu)

        layout.addLayout(button_layout)
        layout.addWidget(self.duplicates_tree)
        return tab

        self.find_duplicates_button.clicked.connect(self.find_and_display_duplicates)
        self.delete_selected_button.clicked.connect(self.delete_selected_duplicates)
        self.keep_newest_button.clicked.connect(
            lambda: self.select_duplicate_files(keep="newest")
        )
        self.keep_oldest_button.clicked.connect(
            lambda: self.select_duplicate_files(keep="oldest")
        )
        self.duplicates_tree.itemSelectionChanged.connect(
            self.on_duplicate_item_selected
        )
        self.duplicates_tree.itemDoubleClicked.connect(
            self.on_duplicate_item_double_clicked
        )
        self.duplicates_tree.customContextMenuRequested.connect(
            self.show_duplicate_file_context_menu
        )

    def create_details_panel(self):
        self.details_panel = QWidget()
        details_layout = QVBoxLayout(self.details_panel)
        title_bar_layout = QHBoxLayout()
        self.selected_file_label = QLabel("لم يتم تحديد أي ملف")
        self.selected_file_label.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 5px;"
        )
        close_preview_button = QPushButton("X")
        close_preview_button.setFixedSize(24, 24)
        close_preview_button.clicked.connect(
            lambda: self.details_panel.setVisible(False)
        )
        title_bar_layout.addWidget(self.selected_file_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(close_preview_button)
        details_layout.addLayout(title_bar_layout)

        self.ai_summary_widget = QWidget()
        ai_layout = QVBoxLayout(self.ai_summary_widget)
        self.ai_summary_label = QLabel("<b>الملخص الذكي:</b>")
        self.ai_summary_text = QTextEdit()
        self.ai_summary_text.setReadOnly(True)
        self.ai_summary_text.setMaximumHeight(80)
        ai_layout.addWidget(self.ai_summary_label)
        ai_layout.addWidget(self.ai_summary_text)
        self.ai_summary_widget.setVisible(False)
        details_layout.addWidget(self.ai_summary_widget)

        preview_label = QLabel("معاينة الملف:")
        details_layout.addWidget(preview_label)
        
        self.preview_stack = QStackedWidget()
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.text_preview_edit = QTextEdit()
        self.text_preview_edit.setReadOnly(True)
        self.text_preview_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_preview_edit.customContextMenuRequested.connect(
            self.show_text_edit_context_menu
        )
        self.excel_preview_table = QTableWidget()
        self.excel_preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.external_preview_widget = QWidget()
        ext_layout = QVBoxLayout(self.external_preview_widget)
        ext_layout.addStretch()
        ext_label = QLabel(
            "لا يمكن عرض هذا الملف مباشرة.\nيمكنك فتحه في برنامجه الافتراضي."
        )
        ext_label.setAlignment(Qt.AlignCenter)
        self.open_external_button = QPushButton("🌐 فتح في المتصفح")
        self.open_external_button.clicked.connect(self.open_current_file_externally)
        ext_layout.addWidget(ext_label)
        ext_layout.addWidget(self.open_external_button)
        ext_layout.addStretch()
        
        no_preview_label = QLabel("لا توجد معاينة متاحة.")
        no_preview_label.setObjectName("no_preview_label")
        no_preview_label.setAlignment(Qt.AlignCenter)

        self.preview_stack.addWidget(self.image_preview_label)
        self.preview_stack.addWidget(self.text_preview_edit)
        self.preview_stack.addWidget(self.excel_preview_table)
        self.preview_stack.addWidget(self.external_preview_widget)
        self.preview_stack.addWidget(no_preview_label)
        
        details_layout.addWidget(self.preview_stack)
        self.pdf_nav_widget = QWidget()
        pdf_nav_layout = QHBoxLayout(self.pdf_nav_widget)
        self.prev_page_button = QPushButton("< السابق")
        self.next_page_button = QPushButton("التالي >")
        self.page_label = QLabel("صفحة 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        pdf_nav_layout.addWidget(self.prev_page_button)
        pdf_nav_layout.addWidget(self.page_label)
        pdf_nav_layout.addWidget(self.next_page_button)
        self.prev_page_button.clicked.connect(self.prev_pdf_page)
        self.next_page_button.clicked.connect(self.next_pdf_page)
        details_layout.addWidget(self.pdf_nav_widget)

        self.suggested_tags_widget = QWidget()
        sug_tags_layout = QVBoxLayout(self.suggested_tags_widget)
        sug_tags_label = QLabel("<b>وسوم مقترحة من AI:</b>")
        self.suggested_tags_layout = QHBoxLayout()
        sug_tags_layout.addWidget(sug_tags_label)
        sug_tags_layout.addLayout(self.suggested_tags_layout)
        sug_tags_layout.addStretch()
        self.suggested_tags_widget.setVisible(False)
        details_layout.addWidget(self.suggested_tags_widget)

        tags_group_label = QLabel("الوسوم (Tags):")
        details_layout.addWidget(tags_group_label)
        self.tags_list_widget = QListWidget()
        self.tags_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tags_list_widget.customContextMenuRequested.connect(
            self.show_tag_context_menu
        )
        add_tag_layout = QHBoxLayout()
        self.add_tag_input = QLineEdit()
        self.add_tag_input.setPlaceholderText("أضف وسماً جديداً...")
        add_tag_button = QPushButton("إضافة")
        add_tag_button.clicked.connect(self.add_tag_to_selected_file)
        add_tag_layout.addWidget(self.add_tag_input)
        add_tag_layout.addWidget(add_tag_button)
        details_layout.addWidget(self.tags_list_widget)
        details_layout.addLayout(add_tag_layout)
        details_layout.setStretchFactor(self.preview_stack, 1)
        self.details_panel.setVisible(False)

    def create_file_table(self):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["", "اسم الملف", "نوع الملف", "الحجم", "تاريخ التعديل", "المجلد"]
        )
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        table.setDragEnabled(True)
        table.setDragDropMode(QAbstractItemView.DragOnly)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSortingEnabled(True)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_file_context_menu)
        table.itemDoubleClicked.connect(self.handle_item_action)
        table.itemSelectionChanged.connect(self.on_selection_changed)
        return table

    def create_organizer_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        self.tree_view_checkbox = QCheckBox("إظهار شجرة المجلدات")
        self.tree_view_checkbox.setChecked(True)
        main_layout.addWidget(self.tree_view_checkbox)
        splitter = QSplitter(Qt.Horizontal)
        self.organizer_table = self.create_file_table()
        self.organizer_fs_model = QFileSystemModel()
        self.organizer_fs_model.setRootPath(QDir.rootPath())
        self.organizer_tree_view = DropEnabledTreeView(self)
        self.organizer_tree_view.setModel(self.organizer_fs_model)
        self.organizer_tree_view.setRootIndex(
            self.organizer_fs_model.index(QDir.rootPath())
        )
        self.organizer_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.organizer_tree_view.customContextMenuRequested.connect(
            self.show_folder_context_menu
        )
        self.organizer_tree_view.files_moved.connect(self.load_data_from_db)
        self.tree_view_checkbox.toggled.connect(self.organizer_tree_view.setVisible)
        splitter.addWidget(self.organizer_table)
        splitter.addWidget(self.organizer_tree_view)
        splitter.setSizes([800, 500])
        main_layout.addWidget(splitter)
        return tab

    def create_ocr_tab(self):
        tab = QWidget()
        ocr_layout = QVBoxLayout(tab)
        top_button_layout = QHBoxLayout()
        select_file_button = QPushButton("📄 اختر صورة أو PDF لتحليل النص")
        self.save_ocr_button = QPushButton("💾 حفظ النص في ملف Word")
        self.save_ocr_button.setEnabled(False)
        top_button_layout.addWidget(select_file_button)
        top_button_layout.addStretch()
        top_button_layout.addWidget(self.save_ocr_button)
        self.ocr_text_area = QTextEdit()
        self.ocr_text_area.setReadOnly(True)
        self.ocr_text_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ocr_text_area.customContextMenuRequested.connect(
            self.show_text_edit_context_menu
        )
        select_file_button.clicked.connect(self.perform_ocr_on_demand)
        self.save_ocr_button.clicked.connect(self.save_ocr_text)
        ocr_layout.addLayout(top_button_layout)
        ocr_layout.addWidget(self.ocr_text_area)
        return tab

    def save_ocr_text(self):
        text_to_save = self.ocr_text_area.toPlainText()
        if not text_to_save.strip():
            QMessageBox.warning(self, "لا يوجد نص", "لا يوجد نص للحفظ.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ ملف Word", "", "Word Documents (*.docx)"
        )
        if file_path:
            if not file_path.lower().endswith(".docx"):
                file_path += ".docx"
            success, message = ocr_handler.save_text_to_word(text_to_save, file_path)
            if success:
                QMessageBox.information(
                    self, "تم الحفظ", f"تم حفظ الملف بنجاح في:\n{file_path}"
                )
                smart_logger.log(f"OCR text saved to Word file: {file_path}")
            else:
                QMessageBox.critical(self, "خطأ في الحفظ", message)
                smart_logger.log(f"!! Failed to save OCR text to Word: {message}")

    def populate_table(self, table, files_data, search_term=""):
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        table.setRowCount(0)
        table.setRowCount(len(files_data))

        status_icons = {
            "completed": "🤖",
            "processing": "⏳",
            "failed": "❌",
            "pending": "⚪"
        }

        for row_position, row_data in enumerate(files_data):
            file_path, file_name, size, mod_time, extension, ai_status = row_data[:6]

            status_item = QTableWidgetItem(status_icons.get(ai_status, "⚪"))
            status_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_position, 0, status_item)

            base_name, _ = os.path.splitext(file_name)
            name_item = QTableWidgetItem(base_name)
            name_item.setData(Qt.UserRole, file_path)

            table.setItem(row_position, 1, name_item)
            table.setItem(row_position, 2, QTableWidgetItem(extension))
            table.setItem(row_position, 3, QTableWidgetItem(format_size(size)))
            table.setItem(
                row_position,
                4,
                QTableWidgetItem(
                    datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                ),
            )
            table.setItem(
                row_position,
                5,
                QTableWidgetItem(os.path.basename(os.path.dirname(file_path))),
            )

            if table == self.search_results_table:
                summary = row_data[6] if len(row_data) > 6 else ""
                tags = row_data[7] if len(row_data) > 7 else ""
                table.setItem(row_position, 6, QTableWidgetItem(tags))
                table.setItem(row_position, 7, QTableWidgetItem(summary))

        table.setSortingEnabled(True)
        table.setUpdatesEnabled(True)

    def start_analysis_thread(self, allowed_categories=None):
        is_deep_scan = False
        if not isinstance(allowed_categories, list):
            if not self.current_project_id:
                QMessageBox.warning(self, "لا يوجد مشروع", "يرجى اختيار مشروع أولاً.")
                return
            dialog = ScanOptionsDialog(self.categories, self)
            if dialog.exec_() == QDialog.Accepted:
                allowed_categories = dialog.get_selected_categories()
                is_deep_scan = dialog.is_deep_scan_enabled()
                if not allowed_categories:
                    return
            else:
                return

        try:
            if self.worker_thread and self.worker_thread.isRunning():
                smart_logger.log("Scan operation already running.")
                return
        except (RuntimeError, Exception):
            self.worker_thread = None
            self.scan_worker = None

        if not self.current_project_id:
            QMessageBox.warning(self, "خطأ", "يرجى اختيار مشروع أولاً.")
            return

        db_mod_times = database_handler.get_mod_times_for_project(
            self.current_project_id
        )
        if is_deep_scan:
            smart_logger.log("Deep scan requested: checking and re-verifying all project files.")
            db_mod_times = {}

        scan_type_str = "عميق (شامل)" if is_deep_scan else "ذكي"
        smart_logger.log(
            f"بدء الفحص الـ {scan_type_str} لمشروع '{self.project_combo.currentText()}' (التصنيفات: {', '.join(allowed_categories)})"
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.analyze_button.setEnabled(False)

        # إنشاء نسخة احتياطية تلقائية لقاعدة البيانات قبل بدء الفحص أو التعديل (Auto-Backup M3)
        try:
            bck_path = database_handler.backup_database()
            if bck_path:
                smart_logger.log(f"تم تأمين نسخة احتياطية لقاعدة البيانات: {os.path.basename(bck_path)}")
        except Exception as e:
            smart_logger.log(f"تنبيه النسخ الاحتياطي: {e}")

        self.worker_thread = QThread()
        self.scan_worker = worker.ScanWorker(
            self.current_working_directory,
            db_mod_times,
            allowed_categories,
            self.current_project_id,
        )
        self.scan_worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.progress.connect(self.update_progress)
        self.worker_thread.start()

    def load_data_from_db(self):
        if not self.current_project_id:
            self.clear_all_views()
            return

        smart_logger.log(
            f"Loading data for project: {self.project_combo.currentText()}..."
        )
        self.tabs.setEnabled(False)
        self.analyze_button.setEnabled(False)

        self.data_loader_thread = QThread()
        self.data_loader_worker = DataLoaderWorker(self.current_project_id)
        self.data_loader_worker.moveToThread(self.data_loader_thread)

        self.data_loader_thread.started.connect(self.data_loader_worker.run)
        self.data_loader_worker.finished.connect(self.on_data_loaded)
        self.data_loader_worker.finished.connect(self.data_loader_thread.quit)
        self.data_loader_worker.finished.connect(self.data_loader_worker.deleteLater)
        self.data_loader_thread.finished.connect(self.data_loader_thread.deleteLater)
        self.data_loader_thread.start()

    def on_data_loaded(self, categorized_files_data, all_files_data):
        self.all_files_data = all_files_data

        for table in self.file_tables.values():
            table.setRowCount(0)
        if hasattr(self, "organizer_table"):
            self.organizer_table.setRowCount(0)

        for category, data in categorized_files_data.items():
            if category in self.file_tables:
                self.populate_table(self.file_tables[category], data)
        if hasattr(self, "organizer_table"):
            self.populate_table(self.organizer_table, self.all_files_data)

        if self.current_working_directory and hasattr(self, "organizer_fs_model"):
            self.organizer_tree_view.setRootIndex(
                self.organizer_fs_model.index(self.current_working_directory)
            )

        smart_logger.log(f"Loaded {len(self.all_files_data)} file records.")
        self.update_kpi_metrics()
        self.tabs.setEnabled(True)
        self.analyze_button.setEnabled(True)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_scan_finished(self):
        smart_logger.log("Scan process finished. Refreshing data from DB.")
        self.progress_bar.setVisible(False)
        if self.worker_thread:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait()
            except Exception as e:
                smart_logger.log(f"Notice on worker thread wait: {e}")
            self.worker_thread = None
            self.scan_worker = None
        self.load_data_from_db()
        try:
            self.find_and_display_duplicates()
        except Exception as e:
            smart_logger.log(f"Notice on duplicate scan trigger: {e}")

    def on_suggestion_thread_finished(self):
        smart_logger.log(
            "Suggestion thread has finished and its variables have been cleaned up."
        )
        self.suggestion_thread = None
        self.suggestion_worker = None

    def generate_suggestions(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "لا يوجد مشروع", "يرجى اختيار مشروع أولاً.")
            return
        if self.suggestion_thread and self.suggestion_thread.isRunning():
            smart_logger.log("Suggestion generation is already running.")
            return

        smart_logger.log("Generating smart organization plan...")
        self.apply_button.setEnabled(False)
        self.suggestions_tree.clear()
        QApplication.processEvents()

        self.suggestion_thread = QThread()
        self.suggestion_worker = SuggestionWorker(self.current_project_id)
        self.suggestion_worker.moveToThread(self.suggestion_thread)

        self.suggestion_thread.started.connect(self.suggestion_worker.run)
        self.suggestion_worker.finished.connect(self.suggestion_thread.quit)
        self.suggestion_worker.finished.connect(self.display_suggestions)
        self.suggestion_thread.finished.connect(self.suggestion_worker.deleteLater)
        self.suggestion_thread.finished.connect(self.suggestion_thread.deleteLater)
        self.suggestion_thread.finished.connect(self.on_suggestion_thread_finished)

        self.suggestion_thread.start()

    def display_suggestions(self, suggestions):
        if not suggestions:
            smart_logger.log(
                "No organization suggestions found based on current rules."
            )
            self.apply_button.setEnabled(False)
            return

        for suggestion in suggestions:
            item = QTreeWidgetItem(
                self.suggestions_tree,
                [
                    "",
                    os.path.basename(suggestion["file_path"]),
                    suggestion["action_type"],
                    suggestion["action_value"],
                ],
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            item.setData(0, Qt.UserRole, suggestion)

        self.apply_button.setEnabled(True)
        smart_logger.log(f"Generated {len(suggestions)} organization suggestions.")
        self.tabs.setCurrentWidget(self.suggestions_tree.parent().parent())

    def get_full_path_from_table_item(self, item):
        if not item:
            return None
        return item.tableWidget().item(item.row(), 1).data(Qt.UserRole)

    def get_active_table(self):
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QTableWidget):
            return current_widget
        if hasattr(current_widget, "findChild") and isinstance(
            current_widget.findChild(QTableWidget), QTableWidget
        ):
            return current_widget.findChild(QTableWidget)
        return None

    def get_selected_file_paths_from_active_table(self):
        active_table = self.get_active_table()
        if not active_table:
            return []
        selected_paths = []
        unique_rows = {item.row() for item in active_table.selectedItems()}
        for row in unique_rows:
            full_path = self.get_full_path_from_table_item(active_table.item(row, 1))
            if full_path:
                selected_paths.append(full_path)
        return selected_paths

    def perform_search(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "لا يوجد مشروع", "يرجى اختيار مشروع للبحث فيه.")
            return
        search_term = self.search_input.text().strip()
        category = self.search_category_combo.currentText()
        if not search_term:
            return
        QApplication.processEvents()
        if search_term.startswith("#"):
            tag_name = search_term[1:].replace("_", " ")
            smart_logger.log(
                f"Searching by tag: '{tag_name}' in category '{category}'..."
            )
            found_files_data = database_handler.search_by_tag(
                tag_name, category, self.current_project_id
            )
        else:
            search_type = self.search_type_combo.currentIndex()
            smart_logger.log(
                f"Searching for: '{search_term}' ({self.search_type_combo.currentText()}) in category '{category}'..."
            )
            if search_type == 0:
                found_files_data = database_handler.search_files_by_name(
                    search_term, category, self.current_project_id
                )
            else:
                found_files_data = database_handler.search_files_by_content(
                    search_term, category, self.current_project_id
                )
        self.populate_table(self.search_results_table, found_files_data, search_term)
        smart_logger.log(f"Found {len(found_files_data)} search results.")

    def find_and_display_duplicates(self):
        try:
            if self.dup_thread is not None and self.dup_thread.isRunning():
                smart_logger.log("Duplicate scan is already in progress.")
                return
        except (RuntimeError, Exception):
            self.dup_thread = None
            self.dup_worker = None

        if not self.all_files_data:
            smart_logger.log("Notice: No file records loaded yet to scan duplicates.")
            return

        if hasattr(self, "find_duplicates_button"):
            self.find_duplicates_button.setEnabled(False)
            self.find_duplicates_button.setText("...جاري البحث")
        if hasattr(self, "duplicates_tree"):
            self.duplicates_tree.clear()
        QApplication.setOverrideCursor(Qt.WaitCursor)

        all_file_paths = [data[0] for data in self.all_files_data if data and len(data) > 0]

        self.dup_thread = QThread()
        self.dup_worker = DuplicateFinderWorker(all_file_paths)
        self.dup_worker.moveToThread(self.dup_thread)

        self.dup_thread.started.connect(self.dup_worker.run)
        self.dup_worker.finished.connect(self.on_duplicates_found)
        self.dup_worker.finished.connect(self.dup_thread.quit)
        self.dup_worker.finished.connect(self.dup_worker.deleteLater)
        self.dup_thread.finished.connect(self.dup_thread.deleteLater)
        self.dup_thread.finished.connect(self.on_dup_thread_finished)

        self.dup_thread.start()

    def on_dup_thread_finished(self):
        self.dup_thread = None
        self.dup_worker = None

    def on_duplicates_found(self, duplicate_groups):
        try:
            self.save_duplicates_cache(duplicate_groups)
            self.populate_duplicates_tree(duplicate_groups)
        except Exception as e:
            smart_logger.log(f"Error displaying duplicates: {e}")
        finally:
            QApplication.restoreOverrideCursor()
            if hasattr(self, "find_duplicates_button"):
                self.find_duplicates_button.setEnabled(True)
                self.find_duplicates_button.setText("إعادة البحث عن المكررات")

    def save_duplicates_cache(self, duplicate_groups):
        if not self.current_working_directory:
            return
        cache_file = os.path.join(
            self.current_working_directory, "duplicates_cache.json"
        )
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(duplicate_groups, f)
            smart_logger.log(f"Duplicates cache saved to {cache_file}")
        except Exception as e:
            smart_logger.log(f"!! Could not save duplicates cache: {e}")

    def load_duplicates_cache(self):
        if not self.current_working_directory:
            return
        cache_file = os.path.join(
            self.current_working_directory, "duplicates_cache.json"
        )

        if os.path.exists(cache_file):
            smart_logger.log(f"Loading duplicates from cache: {cache_file}")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_groups = json.load(f)

                verified_groups = []
                for group in cached_groups:
                    verified_group = [path for path in group if os.path.exists(path)]
                    if len(verified_group) > 1:
                        verified_groups.append(verified_group)

                self.populate_duplicates_tree(verified_groups)
                smart_logger.log(
                    f"Loaded and verified {len(verified_groups)} duplicate groups from cache."
                )
                self.find_duplicates_button.setText("إعادة البحث عن المكررات")
            except Exception as e:
                smart_logger.log(f"!! Could not load or parse duplicates cache: {e}")
                self.duplicates_tree.clear()
        else:
            smart_logger.log("No duplicates cache found for this project.")
            self.duplicates_tree.clear()

    def populate_duplicates_tree(self, duplicate_groups):
        self.duplicates_tree.clear()
        self.duplicates_tree.setSortingEnabled(False)

        if not duplicate_groups:
            placeholder = QTreeWidgetItem(
                self.duplicates_tree, ["لا توجد ملفات مكررة حاليًا", "", ""]
            )

        for group in duplicate_groups:
            parent_item = SortableTreeWidgetItem(
                self.duplicates_tree,
                [os.path.basename(group[0]), f"{len(group)} نسخ", ""],
            )
            parent_item.setData(1, Qt.UserRole, None)
            parent_item.setData(2, Qt.UserRole, None)

            for file_path in group:
                try:
                    stat = os.stat(file_path)
                    mod_time = stat.st_mtime
                    size = stat.st_size

                    child_item = SortableTreeWidgetItem(parent_item)
                    child_item.setText(0, file_path)
                    child_item.setText(1, format_size(size))
                    child_item.setText(
                        2,
                        datetime.datetime.fromtimestamp(mod_time).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    )

                    child_item.setData(1, Qt.UserRole, size)
                    child_item.setData(2, Qt.UserRole, mod_time)

                    child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                    child_item.setCheckState(0, Qt.Unchecked)
                except FileNotFoundError:
                    continue
            parent_item.setExpanded(True)
        self.duplicates_tree.setSortingEnabled(True)

    def delete_selected_duplicates(self):
        files_to_delete = []
        root = self.duplicates_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item.checkState(0) == Qt.Checked:
                    files_to_delete.append(file_item.text(0))

        if not files_to_delete:
            QMessageBox.information(
                self, "لا يوجد تحديد", "يرجى تحديد النسخ التي تريد حذفها أولاً."
            )
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف {len(files_to_delete)} ملف بشكل نهائي؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            deleted_count = 0
            failed_count = 0
            QApplication.setOverrideCursor(Qt.WaitCursor)
            for path in files_to_delete:
                try:
                    self.release_previewed_file(path)
                    os.remove(path)
                    database_handler.delete_file_record(path)
                    deleted_count += 1
                except Exception as e:
                    failed_count += 1
                    smart_logger.log(f"!! Failed to delete file {path}: {e}")
            QApplication.restoreOverrideCursor()

            summary_message = f"اكتمل الحذف.\n\n- تم حذف {deleted_count} ملف بنجاح."
            if failed_count > 0:
                summary_message += (
                    f"\n- فشل حذف {failed_count} ملف (راجع السجل للتفاصيل)."
                )
            QMessageBox.information(self, "اكتمل الحذف", summary_message)

            smart_logger.log(
                f"Deleted {deleted_count} duplicate files. Failed to delete {failed_count}."
            )
            self.load_data_from_db()
            self.load_duplicates_cache()

    def select_duplicate_files(self, keep="newest"):
        root = self.duplicates_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            children = [group_item.child(j) for j in range(group_item.childCount())]
            if not children:
                continue

            if keep == "newest":
                keeper = max(children, key=lambda item: item.data(2, Qt.UserRole))
            else:
                keeper = min(children, key=lambda item: item.data(2, Qt.UserRole))

            for item in children:
                if item == keeper:
                    item.setCheckState(0, Qt.Unchecked)
                else:
                    item.setCheckState(0, Qt.Checked)

    def on_duplicate_item_selected(self):
        selected_items = self.duplicates_tree.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]
        if selected_item.parent() is not None:
            file_path = selected_item.text(0)
            self.update_details_panel_with_path(file_path)

    def on_duplicate_item_double_clicked(self, item, column):
        if item.parent() is not None:
            file_path = item.text(0)
            self.open_file(file_path)

    def show_duplicate_file_context_menu(self, position):
        selected_items = self.duplicates_tree.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]
        if selected_item.parent() is not None:
            file_path = selected_item.text(0)
            self.show_context_menu_for_path(
                file_path, self.duplicates_tree.viewport().mapToGlobal(position)
            )

    def show_context_menu_for_path(self, full_path, global_pos):
        if not full_path or not os.path.exists(full_path):
            smart_logger.log(
                f"!! Context menu error: File no longer exists at path: {full_path}"
            )
            QMessageBox.warning(self, "خطأ", "الملف لم يعد موجوداً على القرص.")
            self.load_data_from_db()
            return

        menu = QMenu()
        open_action = menu.addAction("📂 فتح الملف")
        open_folder_action = menu.addAction("📁 فتح مجلد الملف")
        menu.addSeparator()
        ai_action = menu.addAction("🤖 تحليل بالذكاء الاصطناعي")
        menu.addSeparator()
        rename_action = menu.addAction("✏️ إعادة تسمية")
        delete_action = menu.addAction("❌ حذف")

        action = menu.exec_(global_pos)

        if action == open_action:
            self.open_file(full_path)
        elif action == open_folder_action:
            self.open_file_location(full_path)
        elif action == rename_action:
            self.rename_file(full_path)
        elif action == delete_action:
            self.delete_file(full_path)
        elif action == ai_action:
            self.start_ai_analysis_for_paths([full_path])

    def perform_ocr_on_demand(self):
        self.save_ocr_button.setEnabled(False)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف لتحليل نصه", "", "Files (*.png *.jpg *.jpeg *.pdf)"
        )
        if not file_path:
            return

        smart_logger.log(f"Performing OCR on demand for: {file_path}")
        QApplication.processEvents()
        extracted_text = ocr_handler.extract_text(file_path)
        self.ocr_text_area.setPlainText(extracted_text)
        smart_logger.log("OCR on demand complete.")

        if extracted_text and not extracted_text.startswith("خطأ"):
            self.save_ocr_button.setEnabled(True)

    def handle_item_action(self, item):
        full_path = self.get_full_path_from_table_item(item)
        if full_path:
            self.open_file(full_path)

    def on_selection_changed(self):
        active_table = self.get_active_table()
        if not active_table:
            return
        selected_items = active_table.selectedItems()
        if not selected_items:
            self.details_panel.setVisible(False)
            return
        item = selected_items[0]
        full_path = self.get_full_path_from_table_item(item)
        self.update_details_panel_with_path(full_path)

    def update_details_panel_with_path(self, full_path):
        if not full_path or not os.path.exists(full_path):
            self.details_panel.setVisible(False)
            return
        self.currently_selected_file_path = full_path
        self.selected_file_label.setText(os.path.basename(full_path))
        details = database_handler.get_file_details_for_ai(full_path)
        if not details:
            self.details_panel.setVisible(False)
            return
            
        file_id, _, ai_summary, suggested_tags, _ = details
        tags = database_handler.get_tags_for_file(file_id)
        self.tags_list_widget.clear()
        for tag_id, tag_name in tags:
            item = QListWidgetItem(tag_name)
            item.setData(Qt.UserRole, tag_id)
            self.tags_list_widget.addItem(item)
        self.update_preview(full_path, ai_summary, suggested_tags)
        self.details_panel.setVisible(True)

    def populate_excel_preview(self, df):
        self.excel_preview_table.clear()
        if df.empty:
            return
        
        self.excel_preview_table.setRowCount(df.shape[0])
        self.excel_preview_table.setColumnCount(df.shape[1])
        self.excel_preview_table.setHorizontalHeaderLabels(df.columns.astype(str))
        
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item_data = df.iat[row, col]
                item = QTableWidgetItem(str(item_data) if pd.notna(item_data) else "")
                self.excel_preview_table.setItem(row, col, item)
        
        self.excel_preview_table.resizeColumnsToContents()

    def update_preview(self, file_path, ai_summary=None, suggested_tags=None):
        self.pdf_nav_widget.setVisible(False)
        if self.preview_doc:
            self.preview_doc.close()
            self.preview_doc = None

        if ai_summary:
            self.ai_summary_label.setText("<b>الملخص الذكي:</b>")
            self.ai_summary_text.setPlainText(ai_summary)
            self.ai_summary_widget.setVisible(True)
        else:
            self.ai_summary_widget.setVisible(False)

        for i in reversed(range(self.suggested_tags_layout.count())):
            widget = self.suggested_tags_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        if suggested_tags:
            for tag in suggested_tags.split(","):
                tag = tag.strip()
                if tag:
                    btn = QPushButton(tag)
                    btn.clicked.connect(lambda _, t=tag: self.add_suggested_tag(t))
                    self.suggested_tags_layout.addWidget(btn)
            self.suggested_tags_widget.setVisible(True)
        else:
            self.suggested_tags_widget.setVisible(False)

        no_preview_widget = self.findChild(QLabel, "no_preview_label")
        
        try:
            extension = os.path.splitext(file_path)[1].lower()

            if extension in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_preview_label.setPixmap(scaled_pixmap)
                self.preview_stack.setCurrentWidget(self.image_preview_label)

            elif extension == ".pdf":
                self.preview_doc = fitz.open(file_path)
                self.preview_current_page = 0
                self.render_pdf_page()
                self.pdf_nav_widget.setVisible(True)

            elif extension == '.docx':
                try:
                    doc = docx.Document(file_path)
                    full_text = "\n".join([para.text for para in doc.paragraphs])
                    self.text_preview_edit.setPlainText(full_text)
                    self.preview_stack.setCurrentWidget(self.text_preview_edit)
                except Exception as e:
                    self.text_preview_edit.setPlainText(f"لا يمكن معاينة الملف (قد يكون محمياً بكلمة مرور):\n{e}")
                    self.preview_stack.setCurrentWidget(self.text_preview_edit)

            elif extension in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(file_path, nrows=100)
                    self.populate_excel_preview(df)
                    self.preview_stack.setCurrentWidget(self.excel_preview_table)
                except Exception as e:
                    self.text_preview_edit.setPlainText(f"لا يمكن معاينة ملف Excel:\n{e}")
                    self.preview_stack.setCurrentWidget(self.text_preview_edit)

            elif extension in [".txt", ".py", ".log", ".qss", ".md"]:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.text_preview_edit.setPlainText(f.read(8192))
                self.preview_stack.setCurrentWidget(self.text_preview_edit)

            elif extension in [".html", ".htm", ".mhtml", ".doc", ".pptx"]:
                self.preview_stack.setCurrentWidget(self.external_preview_widget)

            else:
                self.preview_stack.setCurrentWidget(no_preview_widget)
        except Exception as e:
            smart_logger.log(f"!! Failed to create preview for {file_path}: {e}")
            if no_preview_widget:
                self.preview_stack.setCurrentWidget(no_preview_widget)


    def render_pdf_page(self):
        if not self.preview_doc:
            return
        total_pages = len(self.preview_doc)
        if not (0 <= self.preview_current_page < total_pages):
            return
        page = self.preview_doc.load_page(self.preview_current_page)
        pix = page.get_pixmap()
        img = QImage(
            pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(img)
        scaled_pixmap = pixmap.scaled(
            self.image_preview_label.width(),
            self.image_preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_preview_label.setPixmap(scaled_pixmap)
        self.preview_stack.setCurrentWidget(self.image_preview_label)
        self.page_label.setText(f"صفحة {self.preview_current_page + 1} / {total_pages}")
        self.prev_page_button.setEnabled(self.preview_current_page > 0)
        self.next_page_button.setEnabled(self.preview_current_page < total_pages - 1)

    def prev_pdf_page(self):
        if self.preview_doc and self.preview_current_page > 0:
            self.preview_current_page -= 1
            self.render_pdf_page()

    def next_pdf_page(self):
        if self.preview_doc and self.preview_current_page < len(self.preview_doc) - 1:
            self.preview_current_page += 1
            self.render_pdf_page()

    def add_tag_to_selected_file(self):
        if not self.currently_selected_file_path:
            QMessageBox.warning(self, "خطأ", "يرجى تحديد ملف أولاً.")
            return
        tag_name = self.add_tag_input.text().strip()
        if not tag_name:
            return
        file_id = database_handler.get_file_id(self.currently_selected_file_path)
        if file_id:
            tag_id = database_handler.add_tag(tag_name)
            database_handler.link_tag_to_file(file_id, tag_id)
            database_handler.log_user_action(file_id, "tag", tag_name)
            smart_logger.log(f"Tag '{tag_name}' added to file.")
            self.add_tag_input.clear()
            self.update_details_panel_with_path(self.currently_selected_file_path)

    def add_suggested_tag(self, tag_to_add):
        if not self.currently_selected_file_path:
            return
        self.add_tag_input.setText(tag_to_add)
        self.add_tag_to_selected_file()

    def show_tag_context_menu(self, position):
        selected_item = self.tags_list_widget.currentItem()
        if not selected_item:
            return
        menu = QMenu()
        remove_action = menu.addAction("❌ إزالة الوسم")
        action = menu.exec_(self.tags_list_widget.mapToGlobal(position))
        if action == remove_action:
            tag_id = selected_item.data(Qt.UserRole)
            file_id = database_handler.get_file_id(self.currently_selected_file_path)
            if file_id and tag_id is not None:
                database_handler.unlink_tag_from_file(file_id, tag_id)
                smart_logger.log(f"Tag '{selected_item.text()}' removed from file.")
                self.update_details_panel_with_path(self.currently_selected_file_path)

    def show_text_edit_context_menu(self, position):
        text_edit = self.sender()
        self.source_text_edit_for_translation = text_edit
        menu = QMenu()
        copy_action = menu.addAction("نسخ")
        copy_action.triggered.connect(text_edit.copy)
        if text_edit.textCursor().hasSelection():
            translate_action = menu.addAction("ترجمة النص المحدد")
            translate_action.triggered.connect(self.show_translation_dialog)
        menu.exec_(text_edit.viewport().mapToGlobal(position))

    def show_translation_dialog(self):
        if not self.source_text_edit_for_translation:
            return
        selected_text = (
            self.source_text_edit_for_translation.textCursor().selectedText()
        )
        if selected_text:
            dialog = TranslationDialog(selected_text, self)
            dialog.exec_()

    def show_file_context_menu(self, position):
        table = self.sender()
        selected_items = table.selectedItems()
        if not selected_items:
            return

        full_path = self.get_full_path_from_table_item(selected_items[0])
        self.show_context_menu_for_path(
            full_path, table.viewport().mapToGlobal(position)
        )

    def open_file_location(self, file_path):
        try:
            if sys.platform == "win32":
                os.startfile(os.path.dirname(file_path))
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", "-R", file_path])
            else:
                import subprocess
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
        except Exception as e:
            smart_logger.log(f"!! Failed to open file location: {e}")

    def show_folder_context_menu(self, position):
        tree_view = self.sender()
        index = tree_view.indexAt(position)
        if not index.isValid():
            return
        folder_path = self.organizer_fs_model.filePath(index)
        if not os.path.isdir(folder_path):
            return
        menu = QMenu()
        rename_action = menu.addAction("✏️ إعادة تسمية المجلد")
        action = menu.exec_(tree_view.viewport().mapToGlobal(position))
        if action == rename_action:
            self.rename_selected_folder(folder_path)

    def rename_selected_folder(self, old_path):
        if old_path.rstrip('/\\') == self.current_working_directory.rstrip('/\\'):
            QMessageBox.warning(self, "خطأ", "لا يمكن إعادة تسمية مجلد المشروع الرئيسي من هنا. استخدم 'ملف -> تحديث مسار المشروع' بدلاً من ذلك.")
            return

        dir_name = os.path.dirname(old_path)
        old_folder_name = os.path.basename(old_path)
        new_folder_name, ok = QInputDialog.getText(
            self, "إعادة تسمية مجلد", "الاسم الجديد:", text=old_folder_name
        )
        if ok and new_folder_name and new_folder_name != old_folder_name:
            new_path = os.path.join(dir_name, new_folder_name)
            
            if os.path.exists(new_path):
                QMessageBox.critical(self, "خطأ", f"لا يمكن إعادة تسمية المجلد، '{new_folder_name}' موجود بالفعل.")
                return

            try:
                os.rename(old_path, new_path)
                smart_logger.log(f"Renamed folder on disk: {old_folder_name} to {new_folder_name}")
                
                QApplication.setOverrideCursor(Qt.WaitCursor)
                success = database_handler.update_folder_and_children_paths(old_path, new_path, self.current_project_id)
                QApplication.restoreOverrideCursor()

                if success:
                    smart_logger.log(f"Successfully updated database for folder rename.")
                    self.load_data_from_db() 
                else:
                    smart_logger.log(f"!! Failed to update database for folder rename.")
                    QMessageBox.critical(self, "خطأ في قاعدة البيانات", "تمت إعادة تسمية المجلد على القرص، ولكن فشل تحديث قاعدة البيانات. الرجاء إجراء فحص وتحديث للمشروع لإصلاح المسارات.")

            except Exception as e:
                QApplication.restoreOverrideCursor()
                smart_logger.log(f"!! Failed to rename folder: {e}")
                QMessageBox.critical(self, "خطأ", f"فشل في إعادة تسمية المجلد: {e}")

    def release_previewed_file(self, file_path_to_release):
        if (
            self.preview_doc
            and self.currently_selected_file_path == file_path_to_release
        ):
            self.preview_doc.close()
            self.preview_doc = None
            self.details_panel.setVisible(False)
            QApplication.processEvents()

    def open_file(self, full_path):
        self.release_previewed_file(full_path)
        try:
            os.startfile(full_path)
        except Exception as e:
            smart_logger.log(f"!! Error opening file {full_path}: {e}")

    def rename_file(self, old_path, new_base_name=None):
        self.release_previewed_file(old_path)
        dir_name = os.path.dirname(old_path)
        old_file_name_with_ext = os.path.basename(old_path)
        base_name, extension = os.path.splitext(old_file_name_with_ext)
        
        final_new_name = new_base_name
        if final_new_name is None:
            new_base_name_input, ok = QInputDialog.getText(
                self, "إعادة تسمية ملف", "الاسم الجديد (بدون امتداد):", text=base_name
            )
            if not (ok and new_base_name_input.strip() and new_base_name_input != base_name):
                return
            final_new_name = new_base_name_input.strip()

        new_path = os.path.join(dir_name, final_new_name + extension)
        
        if os.path.abspath(old_path).lower() != os.path.abspath(new_path).lower() and os.path.exists(new_path):
            QMessageBox.critical(self, "خطأ في إعادة تسمية", f"لا يمكن إعادة تسمية، الملف '{os.path.basename(new_path)}' موجود بالفعل.")
            if new_base_name is not None:
                raise FileExistsError(f"File '{os.path.basename(new_path)}' already exists.")
            return

        try:
            os.rename(old_path, new_path)
            database_handler.update_file_path(old_path, new_path)
            smart_logger.log(
                f"Renamed {old_file_name_with_ext} to {os.path.basename(new_path)}"
            )
            self.load_data_from_db()
        except Exception as e:
            smart_logger.log(f"!! Failed to rename file: {e}")
            QMessageBox.critical(self, "خطأ", f"فشل في إعادة تسمية الملف: {e}")
            raise e

    def delete_file(self, full_path):
        self.release_previewed_file(full_path)
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف الملف التالي بشكل نهائي؟\n{full_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(full_path)
                database_handler.delete_file_record(full_path)
                smart_logger.log(f"Deleted file: {full_path}")
                self.load_data_from_db()
            except Exception as e:
                smart_logger.log(f"!! Failed to delete file: {e}")
                QMessageBox.critical(self, "خطأ", f"فشل في حذف الملف: {e}")

    def apply_selected_changes(self):
        actions_to_execute = []
        root = self.suggestions_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.Checked:
                actions_to_execute.append(item.data(0, Qt.UserRole))
        if not actions_to_execute:
            QMessageBox.warning(
                self, "لا يوجد تحديد", "يرجى تحديد إجراء واحد على الأقل لتنفيذه."
            )
            return
        reply = QMessageBox.question(
            self,
            "تأكيد التنفيذ",
            f"هل أنت متأكد من تنفيذ {len(actions_to_execute)} إجراء؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            smart_logger.log(
                f"Executing {len(actions_to_execute)} organization actions..."
            )
            for action in actions_to_execute:
                try:
                    if action["action_type"] == "نقل إلى مجلد":
                        source_path = action["file_path"]
                        if not os.path.exists(source_path):
                            smart_logger.log(
                                f"!! Warning: Source file no longer exists, skipping: {source_path}"
                            )
                            continue
                        dest_folder = action["action_value"]
                        if not os.path.exists(dest_folder):
                            os.makedirs(dest_folder)
                        file_name = os.path.basename(source_path)
                        dest_path = os.path.join(dest_folder, file_name)
                        self.release_previewed_file(source_path)
                        shutil.move(source_path, dest_path)
                        database_handler.update_file_path(source_path, dest_path)
                        database_handler.log_user_action(
                            action["file_id"], "move", dest_folder
                        )
                        smart_logger.log(f"Moved '{file_name}' to '{dest_path}'")
                    elif action["action_type"] == "إضافة وسم":
                        tag_name = action["action_value"]
                        file_id = action["file_id"]
                        tag_id = database_handler.add_tag(tag_name)
                        database_handler.link_tag_to_file(file_id, tag_id)
                        database_handler.log_user_action(file_id, "tag", tag_name)
                        smart_logger.log(
                            f"Added tag '{tag_name}' to file '{os.path.basename(action['file_path'])}'"
                        )
                except Exception as e:
                    smart_logger.log(
                        f"!! Failed to execute action on file {os.path.basename(action['file_path'])}: {e}"
                    )
            smart_logger.log("Smart organization complete. Refreshing data...")
            self.load_data_from_db()
            self.suggestions_tree.clear()
            self.apply_button.setEnabled(False)

    def on_suggestion_selected(self):
        selected_items = self.suggestions_tree.selectedItems()
        if not selected_items:
            return
        suggestion_data = selected_items[0].data(0, Qt.UserRole)
        if suggestion_data and "file_path" in suggestion_data:
            self.update_details_panel_with_path(suggestion_data["file_path"])

    def open_current_file_externally(self):
        if self.currently_selected_file_path:
            self.open_file(self.currently_selected_file_path)

    def start_ai_analysis_for_paths(self, paths):
        if not paths:
            QMessageBox.warning(
                self, "لا يوجد تحديد", "يرجى تحديد ملف واحد على الأقل لتحليله."
            )
            return
        if self.ai_worker_thread and self.ai_worker_thread.isRunning():
            smart_logger.log("AI analysis is already running.")
            return

        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("❌ إلغاء العملية")

        self.ai_worker_thread = QThread()
        self.ai_worker = AIWorker(paths)
        self.ai_worker.moveToThread(self.ai_worker_thread)
        self.ai_worker.finished_file.connect(self.load_data_from_db)
        self.ai_worker.finished_all.connect(self.on_ai_analysis_finished)
        self.ai_worker_thread.started.connect(self.ai_worker.run)
        self.ai_worker_thread.start()

    def start_ai_analysis(self):
        selected_paths = self.get_selected_file_paths_from_active_table()
        self.start_ai_analysis_for_paths(selected_paths)

    def on_ai_analysis_finished(self):
        smart_logger.log("AI analysis finished. Refreshing UI...")
        self.cancel_button.setVisible(False)
        self.load_data_from_db()
        if self.ai_worker_thread:
            self.ai_worker_thread.quit()
            self.ai_worker_thread.wait()
            self.ai_worker_thread = None
            self.ai_worker = None

    def cancel_ai_analysis(self):
        if self.ai_worker_thread and self.ai_worker_thread.isRunning():
            smart_logger.log("User requested to cancel AI analysis.")
            self.ai_worker.stop()
            self.cancel_button.setText("...جاري الإلغاء")
            self.cancel_button.setEnabled(False)


    # --- CHURCH ASSISTANT & LIBRARY MANAGEMENT EXTENSIONS ---


    def on_apologetics_cat_changed(self, index):
        cat = self.apologetics_cat_combo.currentText()
        questions = apologetics_db.get_questions_by_category(cat)
        self.apologetics_q_combo.clear()
        for q in questions:
            self.apologetics_q_combo.addItem(q["question"])

    def ask_selected_apologetics(self):
        q = self.apologetics_q_combo.currentText()
        if q:
            if hasattr(self, 'church_master_subtabs'):
                self.church_master_subtabs.setCurrentIndex(1)
                if hasattr(self, 'apologetics_hub_widget'):
                    self.apologetics_hub_widget.set_question(q)
            else:
                if hasattr(self, 'church_depth_combo'):
                    self.church_depth_combo.setCurrentIndex(1)
                self.fill_church_question(q)
                self.send_church_question()

    def create_church_assistant_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header Banner
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 6, 8, 6)
        
        banner_title = QLabel("✝️ 🛡️ المنصة اللاهوتية والدفاعية الموحدة (المساعد الكنسي وحصن الإيمان)")
        banner_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #D4AF37;")
        banner_desc = QLabel("حوار لاهوتي تفاعلي، تفنيد الشبهات بالـ 6 أركان، استدعاء مراجع د. غالي وتكلا حياً، والأرشيف التراكمي الموفر للتوكنز")
        banner_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")
        
        v_titles = QVBoxLayout()
        v_titles.addWidget(banner_title)
        v_titles.addWidget(banner_desc)
        header_layout.addLayout(v_titles, 1)

        self.audit_church_btn = QPushButton("🧠 تدقيق ثغرات المكتبة")
        self.audit_church_btn.setStyleSheet("background-color: #7C3AED; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; font-size: 12px;")
        self.audit_church_btn.clicked.connect(self.show_library_audit_dialog)
        header_layout.addWidget(self.audit_church_btn)

        self.btn_ai_portal_header = QPushButton("🏛️ بوابة أبحاث ELANTONY AI")
        self.btn_ai_portal_header.setStyleSheet("background-color: #9A3412; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; font-size: 12px;")
        self.btn_ai_portal_header.clicked.connect(self.launch_elantony_ai_portal)
        header_layout.addWidget(self.btn_ai_portal_header)

        self.btn_apol_header = QPushButton("🛡️ استوديو الدفاعيات")
        self.btn_apol_header.setStyleSheet("background-color: #1D4ED8; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; font-size: 12px;")
        self.btn_apol_header.clicked.connect(lambda: self.church_master_subtabs.setCurrentIndex(1))
        header_layout.addWidget(self.btn_apol_header)

        self.btn_archive_header = QPushButton("🗄️ أرشيف الأبحاث")
        self.btn_archive_header.setStyleSheet("background-color: #0F766E; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; font-size: 12px;")
        self.btn_archive_header.clicked.connect(lambda: self.church_master_subtabs.setCurrentIndex(2))
        header_layout.addWidget(self.btn_archive_header)

        self.clear_chat_button = QPushButton("🗑️ مسح المحادثة")
        self.clear_chat_button.clicked.connect(self.clear_church_chat)
        header_layout.addWidget(self.clear_chat_button)
        
        layout.addWidget(header_widget)

        # Master Subtabs for Unified Apologetics & Church Assistant
        self.church_master_subtabs = QTabWidget()
        self.church_master_subtabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #111827;
            }
            QTabBar::tab {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 12px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background-color: #1D4ED8;
                color: #FFFFFF;
            }
        """)

        # Subtab 1: Interactive Chat Mode (حوار كنسي تفاعلي سريع)
        chat_tab_page = QWidget()
        chat_layout = QVBoxLayout(chat_tab_page)
        chat_layout.setContentsMargins(8, 8, 8, 8)
        chat_layout.setSpacing(8)

        # Depth Selector & Quick doubts row
        top_ctrls_box = QWidget()
        top_ctrls_layout = QHBoxLayout(top_ctrls_box)
        top_ctrls_layout.setContentsMargins(0, 0, 0, 0)
        top_ctrls_layout.setSpacing(8)

        depth_lbl = QLabel("العمق اللاهوتي:")
        depth_lbl.setStyleSheet("font-weight: bold; color: #CBD5E1; font-size: 12px;")
        self.church_depth_combo = QComboBox()
        self.church_depth_combo.addItem("📜 بحث لاهوتي أكاديمي موسع", "scholar")
        self.church_depth_combo.addItem("🛡️ تفنيد دفاعي للشبهات", "apologetic")
        self.church_depth_combo.addItem("⚡ إيجاز سريع ومباشر للخدام", "brief")
        self.church_depth_combo.setStyleSheet("background-color: #1E293B; color: #F8FAFC; border: 1px solid #3B82F6; border-radius: 5px; padding: 4px 8px; font-size: 12px;")
        top_ctrls_layout.addWidget(depth_lbl)
        top_ctrls_layout.addWidget(self.church_depth_combo)

        top_ctrls_layout.addSpacing(15)
        top_ctrls_layout.addWidget(QLabel("شبهات شائعة:"))
        self.apologetics_cat_combo = QComboBox()
        self.apologetics_cat_combo.setMinimumWidth(140)
        self.apologetics_cat_combo.addItems(apologetics_db.get_all_categories())
        self.apologetics_cat_combo.currentIndexChanged.connect(self.on_apologetics_cat_changed)
        top_ctrls_layout.addWidget(self.apologetics_cat_combo)

        self.apologetics_q_combo = QComboBox()
        self.apologetics_q_combo.setMinimumWidth(280)
        top_ctrls_layout.addWidget(self.apologetics_q_combo, 1)

        self.ask_apologetics_btn = QPushButton("🚀 دراسة الشبهة في الاستوديو")
        self.ask_apologetics_btn.setStyleSheet("background-color: #1D4ED8; color: white; font-weight: bold; padding: 5px 12px; border-radius: 4px;")
        self.ask_apologetics_btn.clicked.connect(self.ask_selected_apologetics)
        top_ctrls_layout.addWidget(self.ask_apologetics_btn)

        chat_layout.addWidget(top_ctrls_box)
        self.on_apologetics_cat_changed(0)

        # Chat display area
        self.church_chat_display = QTextEdit()
        self.church_chat_display.setReadOnly(True)
        self.church_chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        chat_layout.addWidget(self.church_chat_display, 1)

        # Smart Intent Detection Alert Banner
        self.apologetics_intent_banner = QWidget()
        self.apologetics_intent_banner.setVisible(False)
        self.apologetics_intent_banner.setStyleSheet("background-color: #78350F; border: 1px solid #F59E0B; border-radius: 6px; padding: 4px 10px;")
        intent_layout = QHBoxLayout(self.apologetics_intent_banner)
        intent_layout.setContentsMargins(6, 4, 6, 4)
        intent_lbl = QLabel("💡 رصدنا شبهة دفاعية: هل ترغب في دراستها وتفنيدها ببحث موثق من 6 أركان وتسكينها في أرشيفك الدائم؟")
        intent_lbl.setStyleSheet("color: #FEF3C7; font-weight: bold; font-size: 12px;")
        intent_layout.addWidget(intent_lbl, 1)

        btn_intent_switch = QPushButton("🚀 فتح واستكمال البحث في استوديو الـ 6 أركان")
        btn_intent_switch.setStyleSheet("background-color: #D97706; color: white; font-weight: bold; padding: 4px 12px; border-radius: 4px; font-size: 11px;")
        btn_intent_switch.clicked.connect(self.switch_intent_to_apologetics_studio)
        intent_layout.addWidget(btn_intent_switch)

        chat_layout.addWidget(self.apologetics_intent_banner)

        # Bottom Input and options
        bottom_box = QWidget()
        bottom_layout = QVBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        opts_layout = QHBoxLayout()
        self.church_search_library_cb = QCheckBox("📚 الاستعانة بكتب ومراجع المكتبة المفهرسة لتدعيم الإجابة")
        self.church_search_library_cb.setChecked(True)
        self.church_status_lbl = QLabel("جاهز لتلقي الأسئلة والبحث")
        self.church_status_lbl.setStyleSheet("color: #94A3B8; font-style: italic;")
        opts_layout.addWidget(self.church_search_library_cb)
        opts_layout.addStretch()
        opts_layout.addWidget(self.church_status_lbl)
        bottom_layout.addLayout(opts_layout)

        input_layout = QHBoxLayout()
        self.church_question_input = QLineEdit()
        self.church_question_input.setPlaceholderText("اكتب سؤالك اللاهوتي أو الكنسي هنا، ثم اضغط Enter أو إرسال...")
        self.church_question_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                color: #FFFFFF;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
        """)
        self.church_question_input.returnPressed.connect(self.send_church_question)
        self.church_question_input.textChanged.connect(self.on_church_input_text_changed)

        self.church_send_button = QPushButton("🚀 إرسال السؤال")
        self.church_send_button.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94A3B8;
            }
        """)
        self.church_send_button.clicked.connect(self.send_church_question)

        input_layout.addWidget(self.church_question_input, 1)
        input_layout.addWidget(self.church_send_button)
        bottom_layout.addLayout(input_layout)

        chat_layout.addWidget(bottom_box)

        # Subtab 2: Full Apologetics Studio (استوديو الـ 6 أركان وبنك العلم)
        self.apologetics_hub_widget = ApologeticsHubWidget(
            self,
            library_root=self.current_working_directory,
            project_id=self.current_project_id
        )
        self.apologetics_hub_widget.topicArchived.connect(self.on_topic_archived_refresh)

        # Subtab 3: Smart Topic Research Archive (أرشيف الأبحاث التراكمي وتوفير التوكنز)
        self.topic_archive_widget = TopicArchiveWidget(
            self,
            library_root=self.current_working_directory
        )

        # Subtab 4: Dr. Ghaly Bulk Settler (تسكين أبحاث د. غالي أوفلاين ككتب)
        self.ghaly_settler_widget = GhalySettlerWidget(
            self,
            library_root=self.current_working_directory,
            project_id=self.current_project_id
        )

        # Assemble All Subtabs into Master Widget
        self.church_master_subtabs.addTab(chat_tab_page, "💬 حوار كنسي ذكي ومراجع")
        self.church_master_subtabs.addTab(self.apologetics_hub_widget, "🛡️ استوديو تفنيد الشبهات")
        self.church_master_subtabs.addTab(self.topic_archive_widget, "🗄️ أرشيف الأبحاث التراكمي")
        self.church_master_subtabs.addTab(self.ghaly_settler_widget, "📥 تسكين أبحاث د. غالي أوفلاين")

        layout.addWidget(self.church_master_subtabs, 1)

        # Welcome message in Chat
        self.append_church_chat("system", "✝️ مرحباً بك في المنصة اللاهوتية والدفاعية الموحدة لمكتبة الصليب القبطية الأرثوذكسية.<br>يمكنك الحوار الكنسي التفاعلي السريع، أو التبديل لاستوديو الدفاعيات لصياغة أبحاث موثقة بالـ 6 أركان، ومراجعة أرشيف أبحاثك التراكمي المحفوظ محلياً.")

        return tab

    def on_church_input_text_changed(self, text):
        t = text.lower()
        keywords = ["شبهة", "شبهات", "تطور", "داروين", "طوفان", "نوح", "صلب", "قيامة", "تحريف", "تناقض", "الحاد", "إلحاد", "عمر الارض", "عمر الأرض", "تثليث", "الوهية", "ألوهية", "مخطوطات"]
        if any(k in t for k in keywords) and len(text.strip()) >= 5:
            self.apologetics_intent_banner.setVisible(True)
        else:
            self.apologetics_intent_banner.setVisible(False)

    def switch_intent_to_apologetics_studio(self):
        q = self.church_question_input.text().strip()
        if q and hasattr(self, 'church_master_subtabs') and hasattr(self, 'apologetics_hub_widget'):
            self.church_master_subtabs.setCurrentIndex(1)
            self.apologetics_hub_widget.set_question(q)
            self.apologetics_intent_banner.setVisible(False)

    def on_topic_archived_refresh(self, topic_name):
        if hasattr(self, 'topic_archive_widget'):
            self.topic_archive_widget.load_archived_topics()


    def append_church_chat(self, sender, text):
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        if sender == "user":
            html = f"""
            <div style="margin: 10px 0; text-align: right;">
                <div style="display: inline-block; background-color: #1E3A8A; color: #FFFFFF; padding: 10px 14px; border-radius: 10px; max-width: 85%; text-align: right;">
                    <div style="font-size: 11px; color: #93C5FD; margin-bottom: 4px; font-weight: bold;">👤 الباحث ({now_str})</div>
                    <div style="font-size: 13px;">{text}</div>
                </div>
            </div>
            """
        elif sender == "system":
            html = f"""
            <div style="margin: 8px 0; text-align: center;">
                <span style="background-color: #1E293B; color: #CBD5E1; padding: 6px 16px; border-radius: 12px; font-size: 12px; border: 1px solid #334155;">
                    {text}
                </span>
            </div>
            """
        else: # assistant
            # Highlight local library references, external references, and enrichment alerts
            lines = text.split('\n')
            formatted_lines = []
            for l in lines:
                l_str = l.strip()
                if '📖' in l_str or '[مراجع متوفرة' in l_str or 'مراجع من مكتبتك' in l_str:
                    formatted_lines.append(f'<div style="background-color: #064E3B; border-right: 4px solid #10B981; padding: 6px 10px; margin: 4px 0; border-radius: 4px; color: #D1FAE5; font-weight: bold;">{l_str}</div>')
                elif '⚠️' in l_str or '[تنبيه إثراء' in l_str or 'تغذية المكتبة' in l_str or 'كتب يُنصح باقتنائها' in l_str:
                    formatted_lines.append(f'<div style="background-color: #78350F; border-right: 4px solid #F59E0B; padding: 6px 10px; margin: 4px 0; border-radius: 4px; color: #FEF3C7; font-weight: bold;">{l_str}</div>')
                elif '🌐' in l_str or '[المراجع الكنسية' in l_str:
                    formatted_lines.append(f'<div style="background-color: #1E293B; border-right: 4px solid #38BDF8; padding: 6px 10px; margin: 4px 0; border-radius: 4px; color: #BAE6FD; font-weight: bold;">{l_str}</div>')
                else:
                    formatted_lines.append(l_str)
            
            formatted_text = '<br>'.join(formatted_lines)
            html = f"""
            <div style="margin: 10px 0; text-align: right;">
                <div style="display: inline-block; background-color: #1E293B; color: #F1F5F9; padding: 14px 18px; border-radius: 10px; border-left: 4px solid #D4AF37; max-width: 92%; text-align: right;">
                    <div style="font-size: 12px; font-weight: bold; color: #D4AF37; margin-bottom: 8px;">✝️ المساعد الكنسي واللاهوتي والدفاعي ({now_str})</div>
                    <div style="font-size: 13px; line-height: 1.7;">{formatted_text}</div>
                </div>
            </div>
            """
        self.church_chat_display.append(html)
        self.church_chat_display.verticalScrollBar().setValue(
            self.church_chat_display.verticalScrollBar().maximum()
        )

    def fill_church_question(self, text):
        self.church_question_input.setText(text)
        self.church_question_input.setFocus()

    def show_library_audit_dialog(self):
        dialog = LibraryAuditDialog(self, library_root=self.current_working_directory, project_id=self.current_project_id or 1)
        dialog.exec_()

    def show_autopilot_harvester(self):
        from modules.autopilot_harvester import AutopilotHarvesterDialog
        dialog = AutopilotHarvesterDialog(
            self,
            library_root=self.current_working_directory,
            project_id=self.current_project_id or 1
        )
        dialog.exec_()

    def show_hob_manager(self):
        from modules.hob_manager import HobManagerDialog
        dlg = HobManagerDialog(self)
        dlg.exec_()

    def show_global_repository_studio(self):
        from modules.global_repository_studio import GlobalRepositoryStudioDialog
        dlg = GlobalRepositoryStudioDialog(
            self,
            library_root=self.current_working_directory,
            project_id=self.current_project_id or 1
        )
        dlg.exec_()

    def show_online_feeder_dialog(self):
        dialog = OnlineFeederDialog(self, library_root=self.current_working_directory)
        dialog.exec_()

    def show_omnibox_dialog(self, initial_query=""):
        from modules.omnibox_dialog import OmniboxDialog
        dlg = OmniboxDialog(self, library_root=self.current_working_directory, project_id=self.current_project_id or 1, initial_query=initial_query)
        dlg.exec_()

    def show_in_app_reader(self, file_path=None):
        from modules.in_app_reader import InAppBookReader
        target = file_path or self.currently_selected_file_path
        if not target or not os.path.exists(target):
            target, _ = QFileDialog.getOpenFileName(
                self,
                "اختر كتاباً أو مرجعاً لفتحه في القارئ المدمج",
                self.current_working_directory or "",
                "المستندات والكتب (*.pdf *.docx *.txt *.doc)"
            )
            if not target:
                return
        reader = InAppBookReader(self, file_path=target, target_page=1)
        reader.exec_()


    def show_mobile_cloud_dialog(self):
        from modules.mobile_hub_dialog import MobileHubDialog
        dlg = MobileHubDialog(self)
        dlg.exec_()

    def show_scripture_navigator(self):
        from modules.scripture_engine import ScriptureNavigatorDialog
        dlg = ScriptureNavigatorDialog(self, library_root=self.current_working_directory)
        dlg.exec_()

    def show_apologetics_hub_dialog(self):
        self.switch_sidebar_to(3)
        if hasattr(self, "church_master_subtabs"):
            self.church_master_subtabs.setCurrentIndex(1)

    def clear_church_chat(self):
        self.church_chat_display.clear()
        self.append_church_chat("system", "تم مسح المحادثة. يمكنك الآن طرح استفسارات جديدة.")

    def send_church_question(self):
        question = self.church_question_input.text().strip()
        if not question:
            return
            
        self.append_church_chat("user", question)
        self.church_question_input.clear()
        self.church_question_input.setEnabled(False)
        self.church_send_button.setEnabled(False)
        self.church_status_lbl.setText("جاري إعداد الإجابة والبحث في المراجع الكنسية...")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        depth_mode = "scholar"
        if hasattr(self, "church_depth_combo"):
            depth_mode = self.church_depth_combo.currentData() or "scholar"

        context_info = ""
        if self.church_search_library_cb.isChecked():
            try:
                self.church_status_lbl.setText("جاري استخراج المقتطفات والتوثيق من كتب ومراجع المكتبة...")
                QApplication.processEvents()
                has_src, context_info, source_books = library_rag.extract_relevant_snippets(
                    question,
                    library_root=self.current_working_directory,
                    project_id=self.current_project_id
                )
                smart_logger.log(f"ChurchAssistant RAG: found {len(source_books)} matching sources.")
            except Exception as e:
                smart_logger.log(f"ChurchAssistant RAG note: {e}")

        self.church_assistant_thread = QThread()
        self.church_assistant_worker = ChurchAssistantWorker(question, context_info, depth_mode=depth_mode)
        self.church_assistant_worker.moveToThread(self.church_assistant_thread)

        self.church_assistant_thread.started.connect(self.church_assistant_worker.run)
        self.church_assistant_worker.response_ready.connect(self.on_church_assistant_response)
        self.church_assistant_worker.error_occurred.connect(self.on_church_assistant_error)
        
        self.church_assistant_worker.response_ready.connect(self.church_assistant_thread.quit)
        self.church_assistant_worker.response_ready.connect(self.church_assistant_worker.deleteLater)
        self.church_assistant_worker.error_occurred.connect(self.church_assistant_thread.quit)
        self.church_assistant_worker.error_occurred.connect(self.church_assistant_worker.deleteLater)
        self.church_assistant_thread.finished.connect(self.church_assistant_thread.deleteLater)
        self.church_assistant_thread.finished.connect(self._reset_church_thread)

        self.church_assistant_thread.start()


    def _reset_church_thread(self):
        self.church_assistant_thread = None
        self.church_assistant_worker = None

    def _reset_lib_thread(self):
        self.library_task_thread = None
        self.library_task_worker = None

    def on_church_assistant_response(self, answer):
        QApplication.restoreOverrideCursor()
        self.append_church_chat("assistant", answer)
        self.church_question_input.setEnabled(True)
        self.church_send_button.setEnabled(True)
        self.church_question_input.setFocus()
        self.church_status_lbl.setText("جاهز لتلقي الأسئلة والبحث")

    def on_church_assistant_error(self, err_msg):
        QApplication.restoreOverrideCursor()
        self.append_church_chat("assistant", f"⚠️ تعذر الاستعلام: {err_msg}")
        self.church_question_input.setEnabled(True)
        self.church_send_button.setEnabled(True)
        self.church_question_input.setFocus()
        self.church_status_lbl.setText("حدث خطأ أثناء الاستعلام")

    def run_settle_files(self):
        if not self.current_working_directory or not os.path.isdir(self.current_working_directory):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد مشروع ساري أولاً.")
            return

        reply = QMessageBox.question(
            self,
            "تسكين وترتيب الملفات الواردة",
            f"هل تريد فحص المجلد الرئيسي للمشروع:\n{self.current_working_directory}\nوتسكين الكتب الجديدة في مجلداتها الكنسية الصحيحة تلقائياً؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.settle_button.setEnabled(False)
        self.update_excel_button.setEnabled(False)
        self.analyze_button.setEnabled(False)

        self.library_task_thread = QThread()
        self.library_task_worker = LibraryTaskWorker("settle", self.current_working_directory)
        self.library_task_worker.moveToThread(self.library_task_thread)

        self.library_task_thread.started.connect(self.library_task_worker.run)
        self.library_task_worker.task_finished.connect(self.on_library_task_finished)
        self.library_task_worker.task_finished.connect(self.library_task_thread.quit)
        self.library_task_worker.task_finished.connect(self.library_task_worker.deleteLater)
        self.library_task_thread.finished.connect(self.library_task_thread.deleteLater)
        self.library_task_thread.finished.connect(self._reset_lib_thread)

        self.library_task_thread.start()

    def run_update_excel(self):
        if not self.current_working_directory or not os.path.isdir(self.current_working_directory):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد مشروع ساري أولاً.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.settle_button.setEnabled(False)
        self.update_excel_button.setEnabled(False)
        self.analyze_button.setEnabled(False)

        self.library_task_thread = QThread()
        self.library_task_worker = LibraryTaskWorker("excel", self.current_working_directory)
        self.library_task_worker.moveToThread(self.library_task_thread)

        self.library_task_thread.started.connect(self.library_task_worker.run)
        self.library_task_worker.task_finished.connect(self.on_library_task_finished)
        self.library_task_worker.task_finished.connect(self.library_task_thread.quit)
        self.library_task_worker.task_finished.connect(self.library_task_worker.deleteLater)
        self.library_task_thread.finished.connect(self.library_task_thread.deleteLater)
        self.library_task_thread.finished.connect(self._reset_lib_thread)

        self.library_task_thread.start()


    def show_library_maintenance_hub(self):
        """Unified Maintenance, Excel, Audit, and Manifest Hub."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        dlg = QDialog(self)
        dlg.setWindowTitle("⚡ مركز صيانة وترتيب وفهرسة المكتبة والبيان الحي")
        dlg.resize(520, 320)
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.setStyleSheet("background-color: #1E232D; color: white;")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("عمليات إدارة وصيانة المكتبة وقاعدة البيانات:")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #E5C07B;")
        lay.addWidget(lbl)

        btn_s = QPushButton("📥 تسكين وترتيب الوارد الجديد فوراً في مجلداته")
        btn_s.setStyleSheet("background-color: #059669; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        btn_s.clicked.connect(lambda: (dlg.accept(), self.run_settle_files()))
        lay.addWidget(btn_s)

        btn_e = QPushButton("📊 فتح وتحديث فهرس الإكسيل التفاعلي الشامل")
        btn_e.setStyleSheet("background-color: #2563EB; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        btn_e.clicked.connect(lambda: (dlg.accept(), self.run_update_excel()))
        lay.addWidget(btn_e)

        btn_a = QPushButton("🧠 كاشف ثغرات ونواقص المكتبة وتوصيات الإثراء")
        btn_a.setStyleSheet("background-color: #7C3AED; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        btn_a.clicked.connect(lambda: (dlg.accept(), self.show_library_audit_dialog()))
        lay.addWidget(btn_a)

        btn_h = QPushButton("🖥️ إدارة محرك الذكاء الأوفلاين المحلي وتحديثات Hob")
        btn_h.setStyleSheet("background-color: #0369A1; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        btn_h.clicked.connect(lambda: (dlg.accept(), self.show_hob_manager()))
        lay.addWidget(btn_h)

        btn_m = QPushButton("📋 فتح وثيقة النظام الحية (PROJECT_SYSTEM_MANIFEST.md)")
        btn_m.setStyleSheet("background-color: #334155; color: #38BDF8; padding: 9px; font-weight: bold; border-radius: 6px; border: 1px solid #475569;")
        btn_m.clicked.connect(lambda: (dlg.accept(), self.open_system_manifest()))
        lay.addWidget(btn_m)

        dlg.exec_()

    def open_system_manifest(self):
        """Updates and opens the PROJECT_SYSTEM_MANIFEST.md in the default viewer."""
        try:
            from modules import system_manifest
            manifest_path = system_manifest.auto_update_manifest()
            import os
            os.startfile(manifest_path)
        except Exception as e:
            QMessageBox.information(self, "وثيقة النظام الحية", f"تم تحديث الوثيقة في:\nPROJECT_SYSTEM_MANIFEST.md\n({e})")

    def on_library_task_finished(self, message, is_success):
        self.progress_bar.setVisible(False)
        self.settle_button.setEnabled(True)
        self.update_excel_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        if is_success:
            QMessageBox.information(self, "تمت العملية بنجاح", message)
            self.load_data_from_db()
        else:
            QMessageBox.critical(self, "خطأ", message)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        settings = QSettings("MyCompany", "ArchiveMaster")
        theme = settings.value("theme", "Dark")
        if theme == "Dark":
            try:
                from modules import themes
                app.setStyleSheet(themes.DARK_THEME_QSS)
            except (ImportError, AttributeError):
                print("Could not load dark theme. Please check themes.py.")

        main_win = MainWindow()
        main_win.show()
        sys.exit(app.exec_())
    except Exception as e:
        smart_logger.log(f"!!!!!!!!!!!!! FATAL APPLICATION ERROR !!!!!!!!!!!!!")
        smart_logger.log(f"An unhandled exception occurred: {e}")
        import traceback

        smart_logger.log(traceback.format_exc())
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"A critical error occurred and was logged. Please check the log file in the 'logs' directory.\n\nError: {e}",
        )
        sys.exit(1)
