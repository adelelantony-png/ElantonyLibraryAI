from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QHBoxLayout,
    QFileDialog,
    QSpinBox,
    QLabel,
)


class RuleDialog(QDialog):
    def __init__(self, rule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة/تعديل قاعدة تنظيم")
        self.setMinimumWidth(500)

        # --- إنشاء عناصر الواجهة ---
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # الشرط
        self.condition_type = QComboBox()
        self.condition_type.addItems(
            [
                "المفهوم الرئيسي يحتوي على",
                "اسم الملف يحتوي على",
                "نوع الملف هو",
                "يحمل الوسم",
            ]
        )
        self.condition_value = QLineEdit()
        form_layout.addRow("إذا كان:", self.condition_type)
        form_layout.addRow("القيمة:", self.condition_value)

        # الإجراء
        self.action_type = QComboBox()
        self.action_type.addItems(["نقل إلى مجلد", "إضافة وسم"])
        self.action_value = QLineEdit()
        browse_button = QPushButton("...")
        browse_button.setFixedWidth(30)
        browse_button.clicked.connect(self.browse_folder)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.action_value)
        action_layout.addWidget(browse_button)

        form_layout.addRow("قم بـ:", self.action_type)
        form_layout.addRow("إلى/بالقيمة:", action_layout)

        # الأولوية
        self.priority = QSpinBox()
        self.priority.setRange(0, 100)
        form_layout.addRow("الأولوية (الأعلى أولاً):", self.priority)

        layout.addLayout(form_layout)

        # أزرار الحفظ والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # إذا كان هناك بيانات لتعديل قاعدة موجودة
        if rule_data:
            self.condition_type.setCurrentText(rule_data["condition_type"])
            self.condition_value.setText(rule_data["condition_value"])
            self.action_type.setCurrentText(rule_data["action_type"])
            self.action_value.setText(rule_data["action_value"])
            self.priority.setValue(rule_data["priority"])

    def browse_folder(self):
        """يفتح نافذة لاختيار مجلد الوجهة."""
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد الهدف")
        if folder:
            self.action_value.setText(folder)

    def get_rule_data(self):
        """يعيد البيانات التي أدخلها المستخدم في شكل قاموس."""
        return {
            "condition_type": self.condition_type.currentText(),
            "condition_value": self.condition_value.text(),
            "action_type": self.action_type.currentText(),
            "action_value": self.action_value.text(),
            "priority": self.priority.value(),
        }
