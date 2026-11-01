from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QDialogButtonBox,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QMessageBox,
    QGroupBox,
)
from PyQt5.QtCore import Qt, QSettings
from modules import portable_config, ai_handler, themes


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ إعدادات البرنامج والسمات الفاخرة وحوض الذكاء الاصطناعي")
        self.setMinimumWidth(620)

        self.legacy_settings = QSettings("MyCompany", "ArchiveMaster")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # 1. Appearance and OCR Box
        general_group = QGroupBox("🎨 المظهر البصري الفاخر (Ultra Pro Max Themes)")
        gen_layout = QFormLayout(general_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "🌙 الوضع الليلي المهدئ للعين (Ultra Dark Dimmed)",
            "📜 ورق البردي والعاج الدافئ (Warm Parchment)"
        ])

        self.tesseract_path_edit = QLineEdit()
        browse_button = QPushButton("تصفح...")
        browse_button.clicked.connect(self.browse_tesseract_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.tesseract_path_edit)
        path_layout.addWidget(browse_button)

        gen_layout.addRow("سمة الواجهة والتصميم:", self.theme_combo)
        gen_layout.addRow("مسار Tesseract OCR:", path_layout)
        main_layout.addWidget(general_group)

        # 2. AI Key Pool Box (LiteLLM Cloud Orchestration)
        ai_group = QGroupBox("🌐 حوض مفاتيح الذكاء الاصطناعي السحابي (LiteLLM & Zero-Key)")
        ai_layout = QVBoxLayout(ai_group)

        ai_desc = QLabel(
            "💡 يعمل البرنامج تلقائياً وبالمجان عبر المحرك الذكي من GitHub حتى لو تركت الخانات فارغة!\n"
            "ويمكنك وضع مفاتيحك الخاصة لسرعة فائقة واستقرار دائم (مفتاح في كل سطر)."
        )
        ai_desc.setStyleSheet("color: #8B949E; font-size: 11px; line-height: 1.5;")
        ai_layout.addWidget(ai_desc)

        ai_form = QFormLayout()
        self.gemini_keys_edit = QTextEdit()
        self.gemini_keys_edit.setPlaceholderText("أدخل مفاتيح Google Gemini API المجانية هنا (مفتاح في كل سطر)...")
        self.gemini_keys_edit.setFixedHeight(75)

        self.groq_keys_edit = QLineEdit()
        self.groq_keys_edit.setPlaceholderText("مفتاح Groq API المجاني (للسرعة الصاروخية الاستثنائية)...")

        ai_form.addRow("مفاتيح Gemini API:", self.gemini_keys_edit)
        ai_form.addRow("مفتاح Groq API:", self.groq_keys_edit)
        ai_layout.addLayout(ai_form)

        # Test Connection button
        test_layout = QHBoxLayout()
        self.test_conn_btn = QPushButton("⚡ فحص اتصال حوض المفاتيح والمحرك التلقائي")
        self.test_conn_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2EA043;
            }
        """)
        self.test_conn_btn.clicked.connect(self.test_ai_keys)
        test_layout.addWidget(self.test_conn_btn)

        self.btn_hob_bridge = QPushButton("🖥️ إعدادات المساعد الأوفلاين (Hob Bridge) وتحديثات GitHub")
        self.btn_hob_bridge.setStyleSheet("""
            QPushButton {
                background-color: #0369A1;
                color: white;
                font-weight: bold;
                padding: 7px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #0284C7; }
        """)
        self.btn_hob_bridge.clicked.connect(self.open_hob_manager)
        test_layout.addWidget(self.btn_hob_bridge)
        test_layout.addStretch()

        self.test_status_lbl = QLabel("")
        test_layout.addWidget(self.test_status_lbl)
        ai_layout.addLayout(test_layout)

        main_layout.addWidget(ai_group)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.load_settings()

    def browse_tesseract_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف tesseract.exe", "", "Executable Files (*.exe)"
        )
        if path:
            self.tesseract_path_edit.setText(path)

    def load_settings(self):
        cfg = portable_config.load_portable_config()
        theme = cfg.get("theme", "Ultra Dark")
        if "Parchment" in theme or "Light" in theme or "ورق" in theme:
            self.theme_combo.setCurrentText("📜 ورق البردي والعاج الدافئ (Warm Parchment)")
        else:
            self.theme_combo.setCurrentText("🌙 الوضع الليلي المهدئ للعين (Ultra Dark Dimmed)")

        tesseract_path = self.legacy_settings.value("tesseract_path", "")
        self.tesseract_path_edit.setText(tesseract_path)

        gemini_keys = cfg.get("gemini_api_keys", [])
        self.gemini_keys_edit.setPlainText("\n".join(gemini_keys))

        groq_keys = cfg.get("groq_api_keys", [])
        self.groq_keys_edit.setText(", ".join(groq_keys))

    def save_settings(self):
        theme_text = self.theme_combo.currentText()
        theme = "Warm Parchment" if "ورق" in theme_text else "Ultra Dark"

        raw_gemini = self.gemini_keys_edit.toPlainText().replace(",", "\n").split("\n")
        gemini_keys = [k.strip() for k in raw_gemini if k.strip()]

        raw_groq = self.groq_keys_edit.text().replace("\n", ",").split(",")
        groq_keys = [k.strip() for k in raw_groq if k.strip()]

        # Save to portable config
        portable_config.update_api_keys(
            gemini_keys=gemini_keys,
            groq_keys=groq_keys,
            theme=theme
        )

        # Sync to legacy QSettings for backward compatibility
        self.legacy_settings.setValue("theme", theme)
        self.legacy_settings.setValue("tesseract_path", self.tesseract_path_edit.text())
        if gemini_keys:
            self.legacy_settings.setValue("gemini_api_key", gemini_keys[0])

    def open_hob_manager(self):
        from modules.hob_manager import HobManagerDialog
        dlg = HobManagerDialog(self)
        dlg.exec_()

    def test_ai_keys(self):
        self.save_settings()
        self.test_status_lbl.setText("جاري الفحص المباشر...")
        self.test_conn_btn.setEnabled(False)

        success, msg = ai_handler.test_api_keys()
        self.test_conn_btn.setEnabled(True)

        if success:
            self.test_status_lbl.setText("✅ متصل بنجاح")
            self.test_status_lbl.setStyleSheet("color: #3FB950; font-weight: bold;")
            QMessageBox.information(self, "نجاح الاتصال", msg)
        else:
            self.test_status_lbl.setText("❌ فشل الاتصال")
            self.test_status_lbl.setStyleSheet("color: #F85149; font-weight: bold;")
            QMessageBox.warning(self, "تنبيه الاتصال", msg)

    def accept(self):
        self.save_settings()
        cfg = portable_config.load_portable_config()
        theme = cfg.get("theme", "Ultra Dark")
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.setStyleSheet(themes.get_theme_qss(theme))
        super().accept()
