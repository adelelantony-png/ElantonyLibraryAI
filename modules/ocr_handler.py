import os
import pytesseract
from PIL import Image
from PyQt5.QtCore import QSettings
import fitz  # PyMuPDF
import cv2  # OpenCV
import numpy as np

try:
    import docx
except ImportError:
    docx = None
try:
    import pptx
except ImportError:
    pptx = None


def preprocess_image_for_ocr(image):
    """
    تأخذ صورة PIL وتقوم بمعالجتها باستخدام OpenCV لتحسين دقة OCR.
    """
    # تحويل من PIL إلى OpenCV
    open_cv_image = np.array(image)
    # تحويل إلى الرمادي
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    # إزالة الضوضاء
    denoised = cv2.medianBlur(gray, 3)
    # زيادة التباين (تحويل إلى أبيض وأسود)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # تحويل من OpenCV إلى PIL مرة أخرى لإرسالها إلى Tesseract
    return Image.fromarray(thresh)


def extract_text(file_path):
    settings = QSettings("MyCompany", "ArchiveMaster")
    tesseract_path = settings.value("tesseract_path", "")
    tesseract_installed = False
    if tesseract_path and os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        tesseract_installed = True

    try:
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()

        if extension in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            if not tesseract_installed:
                return "خطأ: Tesseract OCR غير مُعد بشكل صحيح."
            img = Image.open(file_path).convert("RGB")
            processed_img = preprocess_image_for_ocr(img)
            return pytesseract.image_to_string(processed_img, lang="ara+eng")

        elif extension == ".pdf":
            if not tesseract_installed:
                return "لقراءة ملفات PDF المصورة، يجب ضبط مسار Tesseract OCR."

            try:
                with open(file_path, "rb") as f:
                    import PyPDF2

                    reader = PyPDF2.PdfReader(f, strict=False)
                    if not reader.is_encrypted:
                        text_from_pypdf2 = "".join(
                            p.extract_text() + "\n"
                            for p in reader.pages
                            if p.extract_text()
                        )
                        if len(text_from_pypdf2.strip()) > 100:
                            return text_from_pypdf2
            except Exception:
                pass

            ocr_text = ""
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                processed_img = preprocess_image_for_ocr(img)
                ocr_text += (
                    pytesseract.image_to_string(processed_img, lang="ara+eng") + "\n\n"
                )
            doc.close()
            return ocr_text

        elif extension == ".docx":
            if docx:
                return "\n".join([p.text for p in docx.Document(file_path).paragraphs])
            return "مكتبة 'python-docx' غير مثبتة."

        elif extension == ".pptx":
            if pptx:
                text_runs = [
                    shape.text
                    for slide in pptx.Presentation(file_path).slides
                    for shape in slide.shapes
                    if hasattr(shape, "text")
                ]
                return "\n---\n".join(text_runs)
            return "مكتبة 'python-pptx' غير مثبتة."

        elif extension in [
            ".txt",
            ".py",
            ".log",
            ".qss",
            ".md",
            ".html",
            ".htm",
            ".mhtml",
        ]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            return ""
    except pytesseract.TesseractNotFoundError:
        return (
            "خطأ فادح: Tesseract OCR غير مثبت أو المسار المحدد في الإعدادات غير صحيح."
        )
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return f"لا يمكن قراءة الملف. قد يكون محمياً أو تالفاً.\n\nالخطأ: {e}"


# --- الدالة الجديدة التي تمت إضافتها ---
def save_text_to_word(text_content, save_path):
    """
    تأخذ نصاً ومساراً، ثم تحفظ النص في ملف Word (.docx).
    """
    if not docx:
        return False, "مكتبة 'python-docx' غير مثبتة. لا يمكن الحفظ."

    try:
        doc = docx.Document()
        # إضافة النص مع الحفاظ على الفقرات
        for line in text_content.split("\n"):
            doc.add_paragraph(line)

        doc.save(save_path)
        return True, "تم الحفظ بنجاح!"
    except Exception as e:
        return False, f"فشل الحفظ: {e}"
