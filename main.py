import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QSettings, Qt
import datetime
import traceback

from modules.ui_manager import MainWindow
from modules import themes, portable_config

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_file = "error_log.txt"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_error_message = f"--- ERROR LOG [{timestamp}] ---\n{error_message}\n"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(full_error_message)
    except Exception as e:
        print(f"Could not write to error log: {e}")

    msg = QMessageBox(); msg.setIcon(QMessageBox.Critical)
    msg.setText("An unexpected error occurred!")
    msg.setInformativeText(f"Error details saved to: {os.path.abspath(log_file)}")
    msg.setDetailedText(error_message)
    msg.setWindowTitle("Application Error"); msg.exec_()
    
    QApplication.quit()

def main():
    sys.excepthook = handle_exception
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    
    cfg = portable_config.load_portable_config()
    theme = cfg.get("theme", "Ultra Dark")
    app.setStyleSheet(themes.get_theme_qss(theme))
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()