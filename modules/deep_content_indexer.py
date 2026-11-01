"""
Cross Coptic Library - Deep Content Indexing Engine (العملاق الصامت)
Progressive background indexing service that extracts text from unindexed
PDF, DOCX, and TXT volumes in the library and populates SQLite FTS5.
"""

import os
import re
import sqlite3
import time
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import fitz  # PyMuPDF

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

from modules import database_handler, smart_logger


class DeepIndexerWorker(QObject):
    progress = pyqtSignal(int, int, str)  # current, total, current_filename
    finished = pyqtSignal(int)            # total_indexed
    error = pyqtSignal(str)

    def __init__(self, root_folder_id=None, batch_size=50, max_pages_per_book=350):
        super().__init__()
        self.root_folder_id = root_folder_id
        self.batch_size = batch_size
        self.max_pages_per_book = max_pages_per_book
        self.is_running = True
        self.is_paused = False

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def run(self):
        try:
            con = database_handler.get_connection()
            cur = con.cursor()

            # Find files requiring deep text extraction
            query = """
                SELECT id, file_path, file_name, extension, size, mod_time, category 
                FROM files 
                WHERE (content IS NULL OR length(content) < 30)
                AND extension IN ('.pdf', '.docx', '.txt', '.doc')
            """
            params = []
            if self.root_folder_id:
                query += " AND root_folder_id = ?"
                params.append(self.root_folder_id)

            query += " ORDER BY size ASC"  # index smaller books first for fast instant wins
            cur.execute(query, params)
            unindexed_files = cur.fetchall()
            con.close()

            total_files = len(unindexed_files)
            if total_files == 0:
                self.progress.emit(0, 0, "كافة الكتب مفهرسة بعمق بنسبة 100%")
                self.finished.emit(0)
                return

            smart_logger.log(f"DeepIndexer: بدء الفهرسة العميقة لـ {total_files} كتاباً ومستنداً غير مفهرس...")
            
            indexed_count = 0
            batch = []

            for idx, file_row in enumerate(unindexed_files):
                if not self.is_running:
                    break

                while self.is_paused and self.is_running:
                    time.sleep(0.5)

                file_id, file_path, file_name, ext, fsize, mod_time, category = file_row
                self.progress.emit(idx + 1, total_files, file_name)

                if not os.path.exists(file_path):
                    continue

                extracted_text = self.extract_text_from_file(file_path, ext)
                if extracted_text and len(extracted_text.strip()) > 30:
                    # (name, ext, size, mod_time, category, content, path)
                    batch.append((
                        file_name,
                        ext,
                        fsize,
                        mod_time,
                        category,
                        extracted_text,
                        file_path
                    ))
                    indexed_count += 1

                if len(batch) >= self.batch_size or (idx == total_files - 1 and batch):
                    database_handler.process_file_batch(batch, is_update=True)
                    batch = []

            if batch:
                database_handler.process_file_batch(batch, is_update=True)

            smart_logger.log(f"DeepIndexer: اكتملت الفهرسة العميقة! تم إثراء {indexed_count} كتاباً بمحتواها الداخلي.")
            self.finished.emit(indexed_count)

        except Exception as e:
            smart_logger.log(f"DeepIndexer Error: {e}")
            self.error.emit(str(e))

    def extract_text_from_file(self, file_path: str, ext: str) -> str:
        """Extracts text cleanly from PDF, DOCX, or TXT."""
        ext = ext.lower()
        try:
            if ext == ".pdf":
                doc = fitz.open(file_path)
                pages_text = []
                # limit pages to prevent hanging on corrupted 3000-page dumps
                page_limit = min(len(doc), self.max_pages_per_book)
                for page_num in range(page_limit):
                    page = doc[page_num]
                    t = page.get_text()
                    if t and t.strip():
                        pages_text.append(f"[صفحة {page_num + 1}]\n{t.strip()}")
                doc.close()
                return "\n\n".join(pages_text)

            elif ext == ".docx" and HAS_DOCX:
                doc = docx.Document(file_path)
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                return "\n".join(paragraphs)

            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(250000)  # read up to 250k chars

            elif ext == ".doc":
                # Quick binary stream scan for Arabic / ascii text
                with open(file_path, "rb") as f:
                    raw = f.read(250000)
                # extract printable chunks
                clean = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b' ', raw)
                return clean.decode("utf-8", errors="ignore")

        except Exception:
            pass
        return ""
