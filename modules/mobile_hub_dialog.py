# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Mobile Hub & Telegram Dialog
Desktop UI dialog displaying live server status, QR code for instant mobile Wi-Fi access,
and direct links to Telegram Bot (@ElantonyLibrarybot).
"""

import os
import sys
import socket
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QDesktopServices

import qrcode
from modules import church_ai_config, church_ai_reporter


def get_local_ip() -> str:
    """Gets local network IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


class MobileHubDialog(QDialog):
    """Dialog for managing Mobile PWA and Telegram server from desktop GUI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✠ خادم الجوال وبوت تيليجرام | ChurchAI Cloud")
        self.resize(720, 520)
        self.setMinimumSize(650, 480)
        self.setLayoutDirection(Qt.RightToLeft)

        # Style matching Soft Slate Eye-Care theme
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 10px;
                margin-top: 12px;
                font-weight: bold;
                color: #38bdf8;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #475569;
                border-radius: 8px;
                color: #f8fafc;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QPushButton#btnTelegram {
                background-color: #0284c7;
                border-color: #38bdf8;
                color: white;
            }
            QPushButton#btnTelegram:hover {
                background-color: #0369a1;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header
        header_layout = QHBoxLayout()
        title_label = QLabel("✠ خادم الجوال وتطبيق تيليجرام الكنسي")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #f59e0b;")

        self.status_pill = QLabel("● السيرفر قيد التشغيل")
        self.status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid #10b981;
            border-radius: 12px;
            padding: 4px 12px;
            font-weight: bold;
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_pill)
        main_layout.addLayout(header_layout)

        # 2. Content: 2 columns (QR Code on Left, Info on Right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left Column: QR Code Box
        qr_group = QGroupBox("📱 الدخول السريع عبر كاميرا الجوال")
        qr_vbox = QVBoxLayout(qr_group)
        qr_vbox.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(210, 210)
        self.qr_label.setStyleSheet("background-color: white; border-radius: 8px; padding: 5px;")
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_vbox.addWidget(self.qr_label)

        qr_tip = QLabel("وجه كاميرا الجوال نحو الرمز للدخول الفوري\nإلى المكتبة عبر شبكة الواي فاي")
        qr_tip.setAlignment(Qt.AlignCenter)
        qr_tip.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 5px;")
        qr_vbox.addWidget(qr_tip)
        content_layout.addWidget(qr_group, 4)

        # Right Column: Details & Telegram Bot
        info_vbox = QVBoxLayout()

        # Network info box
        net_group = QGroupBox("🌐 بيانات الشبكة والاتصال")
        net_grid = QGridLayout(net_group)

        self.local_ip = get_local_ip()
        self.mobile_url = f"http://{self.local_ip}:8000"

        net_grid.addWidget(QLabel("رابط الجوال (Wi-Fi):"), 0, 0)
        self.lbl_url = QLabel(f"<a href='{self.mobile_url}' style='color: #38bdf8;'>{self.mobile_url}</a>")
        self.lbl_url.setOpenExternalLinks(True)
        self.lbl_url.setFont(QFont("Consolas", 10, QFont.Bold))
        net_grid.addWidget(self.lbl_url, 0, 1)

        net_grid.addWidget(QLabel("المنفذ المحلي:"), 1, 0)
        lbl_port = QLabel("8000 (FastAPI Core)")
        lbl_port.setStyleSheet("color: #cbd5e1;")
        net_grid.addWidget(lbl_port, 1, 1)

        info_vbox.addWidget(net_group)

        # Telegram bot box
        tg_group = QGroupBox("🤖 بوت تيليجرام الكنسي")
        tg_vbox = QVBoxLayout(tg_group)

        tg_desc = QLabel("البوت متصل بالذكاء الاصطناعي والمكتبة الآبائية،\nويرد بالشواهد مع إمكانية إرسال كتب الـ PDF.")
        tg_desc.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        tg_vbox.addWidget(tg_desc)

        btn_tg = QPushButton("💬 فتح المحادثة مع @ElantonyLibrarybot")
        btn_tg.setObjectName("btnTelegram")
        btn_tg.setCursor(Qt.PointingHandCursor)
        btn_tg.clicked.connect(self.open_telegram)
        tg_vbox.addWidget(btn_tg)

        info_vbox.addWidget(tg_group)
        content_layout.addLayout(info_vbox, 6)
        main_layout.addLayout(content_layout)

        # 3. Footer Stats & Actions
        footer_layout = QHBoxLayout()

        stats = church_ai_reporter.get_catalog_statistics()
        self.lbl_stats = QLabel(f"📚 المراجع المفهرسة: {stats['total_books']} مجلداً ({stats['total_pages']:,} صفحة)")
        self.lbl_stats.setStyleSheet("color: #f59e0b; font-weight: bold;")
        footer_layout.addWidget(self.lbl_stats)

        footer_layout.addStretch()

        btn_copy_url = QPushButton("📋 نسخ الرابط")
        btn_copy_url.clicked.connect(self.copy_url)
        footer_layout.addWidget(btn_copy_url)

        btn_close = QPushButton("إغلاق")
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        main_layout.addLayout(footer_layout)

        # Generate and show QR Code
        self.generate_qr_code()

    def generate_qr_code(self):
        """Generates QR code for mobile URL and displays it."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=6,
                border=2,
            )
            qr.add_data(self.mobile_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="white")

            qr_path = Path(church_ai_config.BASE_DIR) / "reports" / "church_wifi_qr.png"
            qr_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(qr_path))

            pixmap = QPixmap(str(qr_path))
            scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(scaled_pixmap)
        except Exception as e:
            self.qr_label.setText(f"QR Error: {e}")

    def open_telegram(self):
        """Opens Telegram Bot URL in default browser or desktop app."""
        QDesktopServices.openUrl(QUrl("https://t.me/ElantonyLibrarybot"))

    def copy_url(self):
        """Copies the local mobile URL to clipboard."""
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.mobile_url)
        QMessageBox.information(self, "تم النسخ", f"تم نسخ الرابط إلى الحافظة:\n{self.mobile_url}")
