import os
import datetime
from PyQt5.QtCore import QObject, pyqtSignal


# --- كلاس خاص بإرسال الإشارات للواجهة الرسومية ---
class LoggerHandler(QObject):
    """
    هذا الكلاس مسؤول عن إرسال إشارة تحتوي على الرسالة الجديدة
    إلى أي جزء من الواجهة الرسومية يستمع لها.
    """

    message_logged = pyqtSignal(str)


# إنشاء نسخة واحدة عالمية يمكن الوصول إليها من أي مكان
handler = LoggerHandler()

# --- إعدادات المسجل ---
LOG_DIRECTORY = "logs"
LOG_FILE_PATH = ""


def initialize_logger():
    """
    تهيئ المسجل: تنشئ المجلد وملف السجل لهذه الجلسة.
    """
    global LOG_FILE_PATH
    try:
        if not os.path.exists(LOG_DIRECTORY):
            os.makedirs(LOG_DIRECTORY)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"log_{timestamp}.txt"
        LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, file_name)

        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(
                f"--- Log Session Started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
            )
            f.write(f"Log file: {LOG_FILE_PATH}\n")
            f.write("-" * 50 + "\n\n")

    except Exception as e:
        print(f"CRITICAL: Failed to initialize logger: {e}")
        LOG_FILE_PATH = ""


def log(message: str):
    """
    تسجل رسالة جديدة في الملف الخارجي وترسل إشارة للواجهة الداخلية.
    """
    if not LOG_FILE_PATH:
        return

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_message_for_file = f"[{timestamp}] {message}\n"
        log_message_for_ui = (
            f"[{timestamp.split(' ')[1]}] {message}"  # نسخة مختصرة للواجهة
        )

        # 1. الكتابة في الملف الخارجي (للأمان)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_message_for_file)

        # 2. إرسال إشارة للواجهة الرسومية (للعرض المباشر)
        handler.message_logged.emit(log_message_for_ui)

        # طباعة الرسالة في الطرفية (console) بأمان دون خطأ ترميز
        try:
            print(message)
        except Exception:
            try:
                print(message.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass

    except Exception as e:
        print(f"CRITICAL: Failed to write to log file: {e}")


# --- تهيئة المسجل تلقائيًا عند استيراد هذا الملف ---
initialize_logger()
