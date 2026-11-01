"""
Cross Coptic Library - Soothing Eye-Care Theme Suite
Featuring the Soft Slate Medium-Contrast Theme (مريح للعين متوسط الحدة)
and Luxury Warm Parchment for optimal reading comfort without harsh darks or blinding lights.
"""

SOFT_SLATE_EYECARE_QSS = """
    /* Main Background & Geometry */
    QWidget {
        background-color: #2D3442;
        color: #E2E8F0;
        border: none;
        font-family: 'Segoe UI', 'Cairo', 'Tahoma', 'Arial', sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QDialog {
        background-color: #252B36;
    }

    /* Navigation Sidebar */
    QListWidget#SidebarList {
        background-color: #212631;
        border: none;
        border-left: 1px solid #384252;
        padding-top: 10px;
    }
    QListWidget#SidebarList::item {
        color: #A0AEC0;
        padding: 12px 16px;
        margin: 4px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 11pt;
    }
    QListWidget#SidebarList::item:hover {
        background-color: #323A48;
        color: #FFFFFF;
    }
    QListWidget#SidebarList::item:selected {
        background-color: #384252;
        color: #E5C07B;
        border-right: 4px solid #E5C07B;
    }

    /* Tabs & Panes */
    QTabWidget::pane {
        border: 1px solid #3D4758;
        background-color: #2D3442;
        border-radius: 0 0 8px 8px;
    }
    QTabBar::tab {
        background: #252B36;
        color: #94A3B8;
        border: 1px solid #3D4758;
        border-bottom: none;
        padding: 8px 18px;
        margin-left: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 600;
    }
    QTabBar::tab:selected {
        background: #2D3442;
        color: #E5C07B;
        border-bottom: 2px solid #E5C07B;
        font-weight: bold;
    }
    QTabBar::tab:!selected:hover {
        background: #323A48;
        color: #E2E8F0;
    }

    /* Modern Eye-Care Tables */
    QTableWidget {
        background-color: #2D3442;
        alternate-background-color: #323A48;
        gridline-color: #3D4758;
        selection-background-color: #3E4B5E;
        selection-color: #FFFFFF;
        border: 1px solid #3D4758;
        border-radius: 8px;
    }
    QTableWidget::item {
        padding: 6px 10px;
        border: none;
    }
    QHeaderView::section {
        background-color: #252B36;
        color: #E5C07B;
        padding: 8px 10px;
        border: none;
        border-bottom: 2px solid #475569;
        font-weight: bold;
    }

    /* Tree View */
    QTreeWidget {
        background-color: #2D3442;
        border: 1px solid #3D4758;
        border-radius: 8px;
        color: #E2E8F0;
        padding: 4px;
    }
    QTreeWidget::item:hover {
        background-color: #384252;
    }
    QTreeWidget::item:selected {
        background-color: #3E4B5E;
        color: #E5C07B;
    }

    /* Inputs & Search Boxes */
    QLineEdit {
        background-color: #232832;
        color: #FFFFFF;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 7px 12px;
        selection-background-color: #2563EB;
        font-size: 11pt;
    }
    QLineEdit:focus {
        border: 1px solid #3B82F6;
        background-color: #262C37;
    }

    /* Text Edits */
    QTextEdit {
        background-color: #252B36;
        color: #E2E8F0;
        border: 1px solid #3D4758;
        border-radius: 8px;
        padding: 10px;
        font-size: 11pt;
        line-height: 1.6;
    }

    /* Buttons */
    QPushButton {
        background-color: #384252;
        color: #E2E8F0;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 7px 16px;
        font-weight: bold;
        font-size: 10pt;
    }
    QPushButton:hover {
        background-color: #434F63;
        border-color: #60A5FA;
        color: #FFFFFF;
    }
    QPushButton:pressed {
        background-color: #252B36;
    }
    QPushButton:disabled {
        background-color: #2B323E;
        color: #64748B;
        border-color: #333C4A;
    }

    /* Group Boxes */
    QGroupBox {
        border: 1px solid #3D4758;
        border-radius: 8px;
        margin-top: 14px;
        font-weight: bold;
        color: #E5C07B;
        background-color: #29303D;
        padding: 14px 10px 10px 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top right;
        padding: 2px 10px;
        color: #E5C07B;
    }

    /* Combo & Spin Boxes */
    QComboBox {
        background-color: #252B36;
        color: #E2E8F0;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: 500;
        min-width: 100px;
    }
    QComboBox QAbstractItemView {
        background-color: #252B36;
        color: #FFFFFF;
        selection-background-color: #3E4B5E;
        border: 1px solid #475569;
    }
    QSpinBox {
        background-color: #252B36;
        color: #60A5FA;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 5px 8px;
        font-weight: bold;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        background: #252B36;
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #475569;
        min-height: 25px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #64748B;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: #252B36;
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #475569;
        min-width: 25px;
        border-radius: 5px;
    }
"""

WARM_PARCHMENT_QSS = """
    QWidget {
        background-color: #F8F6F0;
        color: #2D3748;
        font-family: 'Segoe UI', 'Cairo', 'Tahoma', 'Arial', sans-serif;
        font-size: 10pt;
    }
    QMainWindow, QDialog {
        background-color: #EFECE6;
    }
    QGroupBox {
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        margin-top: 14px;
        font-weight: bold;
        color: #B45309;
        background-color: #FFFFFF;
        padding: 14px 10px 10px 10px;
    }
    QLineEdit, QTextEdit, QTableWidget {
        background-color: #FFFFFF;
        color: #1A202C;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
    }
    QPushButton {
        background-color: #E2E8F0;
        color: #1E293B;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 7px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #CBD5E1;
    }
"""

# Compatibility Aliases for ui_manager and settings
DARK_THEME_QSS = SOFT_SLATE_EYECARE_QSS
LIGHT_THEME_QSS = WARM_PARCHMENT_QSS
ULTRA_DARK_DIMMED_QSS = SOFT_SLATE_EYECARE_QSS

THEMES_MAP = {
    "🌿 الوضع الهادئ المريح للعين (Soft Slate Eye-Care)": SOFT_SLATE_EYECARE_QSS,
    "📜 ورق البردي والعاج الدافئ (Warm Parchment)": WARM_PARCHMENT_QSS,
}

def get_theme_qss(theme_name):
    if "ورق البردي" in theme_name or "Parchment" in theme_name or "Light" in theme_name or "الفاتح" in theme_name:
        return WARM_PARCHMENT_QSS
    # Defaults to the new Eye-Care Medium Contrast Soft Slate
    return SOFT_SLATE_EYECARE_QSS
