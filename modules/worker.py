import os
from PyQt5.QtCore import QObject, pyqtSignal
from modules import ocr_handler, keyword_extractor, database_handler, smart_logger


class ScanWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, directory, db_mod_times, allowed_categories, root_folder_id):
        super().__init__()
        self.directory = directory
        self.db_mod_times = db_mod_times
        self.allowed_categories = allowed_categories
        self.root_folder_id = root_folder_id
        self.is_running = True

    def run(self):
        smart_logger.log("ScanWorker: Starting fast scan process...")
        db_files_set = set(self.db_mod_times.keys())
        try:
            disk_files_gen = (
                os.path.join(r, f)
                for r, d, files in os.walk(self.directory)
                for f in files
                if not f.startswith("~$")
            )
        except Exception as e:
            smart_logger.log(f"!! ScanWorker: Error walking directory: {e}")
            self.finished.emit()
            return

        files_to_add = []
        files_to_update = []

        for file_path in disk_files_gen:
            if not self.is_running:
                break
            category = self.categorize_file(os.path.splitext(file_path)[1].lower())
            if (
                "الكل" not in self.allowed_categories
                and category not in self.allowed_categories
            ):
                continue
            try:
                disk_mod_time = os.stat(file_path).st_mtime
                if file_path not in db_files_set:
                    files_to_add.append(file_path)
                elif disk_mod_time > self.db_mod_times.get(file_path, 0):
                    files_to_update.append(file_path)
            except (FileNotFoundError, OSError):
                continue

        total_to_process = len(files_to_add) + len(files_to_update)
        processed_count = 0

        if files_to_add:
            smart_logger.log(
                f"ScanWorker: Found {len(files_to_add)} new files to index..."
            )
            processed_count = self.process_and_commit(
                files_to_add,
                is_update=False,
                total_files=total_to_process,
                start_count=processed_count,
            )

        if files_to_update and self.is_running:
            smart_logger.log(
                f"ScanWorker: Found {len(files_to_update)} modified files to re-index..."
            )
            self.process_and_commit(
                files_to_update,
                is_update=True,
                total_files=total_to_process,
                start_count=processed_count,
            )

        current_disk_files_set = {
            os.path.join(r, f)
            for r, d, files in os.walk(self.directory)
            for f in files
            if not f.startswith("~$")
        }
        deleted_files = list(db_files_set - current_disk_files_set)
        if deleted_files and self.is_running:
            smart_logger.log(
                f"ScanWorker: Found {len(deleted_files)} deleted files to remove from DB..."
            )
            database_handler.delete_records_by_path(deleted_files)

        if self.is_running:
            self.progress.emit(100)
            smart_logger.log("ScanWorker: Scan completed successfully.")
        else:
            smart_logger.log("ScanWorker: Scan was stopped by user.")

        self.finished.emit()

    def process_and_commit(self, file_list, is_update, total_files, start_count):
        batch = []
        batch_size = 500  # يمكن زيادة حجم الدفعة لأن المعالجة سريعة الآن

        for idx, file_path in enumerate(file_list):
            if not self.is_running:
                break

            # --- التعديل هنا ---
            # تم استدعاء دالة المعالجة السريعة
            file_data = self.process_single_file_fast(file_path, is_update)
            if file_data:
                batch.append(file_data)

            if len(batch) >= batch_size or (idx == len(file_list) - 1 and batch):
                database_handler.process_file_batch(batch, is_update)
                # لا نطبع سجل لكل دفعة لتسريع العملية أكثر
                batch = []

            if total_files > 0:
                progress_percentage = int(((start_count + idx + 1) / total_files) * 100)
                self.progress.emit(progress_percentage)

        return start_count + len(file_list)

    def process_single_file_fast(self, file_path, is_update):
        """
        نسخة سريعة جدًا من الدالة، تقوم فقط بجمع البيانات الوصفية للملف
        بدون استخراج نصوص أو كلمات رئيسية.
        """
        try:
            file = os.path.basename(file_path)
            extension = os.path.splitext(file)[1].lower()
            file_category = self.categorize_file(extension)
            stat = os.stat(file_path)

            # اترك حقول المحتوى فارغة ليتم ملؤها لاحقًا عند الحاجة
            content = ""

            if is_update:
                # (name, ext, size, mod_time, category, content, path)
                return (
                    file,
                    extension,
                    stat.st_size,
                    stat.st_mtime,
                    file_category,
                    content,
                    file_path,
                )
            else:
                # (root_id, path, name, ext, size, mod_time, category, content)
                return (
                    self.root_folder_id,
                    file_path,
                    file,
                    extension,
                    stat.st_size,
                    stat.st_mtime,
                    file_category,
                    content,
                )
        except Exception as e:
            smart_logger.log(
                f"!! ScanWorker: Error processing file metadata {file_path}: {e}"
            )
            return None

    def categorize_file(self, extension):
        if extension in [".pdf"]:
            return "📄 PDF"
        if extension in [".doc", ".docx", ".docm", ".dot", ".dotx", ".rtf"]:
            return "📄 مستندات Word"
        if extension in [".ppt", ".pptx", ".pptm", ".pps", ".ppsx"]:
            return "🖥️ عروض تقديمية"
        if extension in [".xls", ".xlsx", ".xlsm", ".xlsb", ".csv"]:
            return "📊 جداول بيانات"
        if extension in [".txt", ".md", ".log"]:
            return "📝 ملفات نصية"
        if extension in [".zip", ".rar", ".7z", ".tar", ".gz"]:
            return "🗜️ ملفات مضغوطة"
        if extension in [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]:
            return "🎬 فيديو"
        if extension in [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"]:
            return "🎵 صوت"
        if extension in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".tiff",
            ".webp",
            ".svg",
        ]:
            return "🖼️ صور"
        if extension in [".html", ".htm", ".mhtml"]:
            return "🌐 صفحات ويب"
        return "ملفات أخرى"

    def stop(self):
        smart_logger.log("ScanWorker: Stop signal received.")
        self.is_running = False
