# -*- coding: utf-8 -*-
"""
ArchiveMaster - Hob Local AI & Offline Engine Bridge
إدارة المساعد المحلي ومحاكي الذكاء الاصطناعي الأوفلاين (Hob) والتحديث الدوري من GitHub
Works as an intelligent, 100% offline fallback when internet is disconnected.
"""

import os
import sys
import time
import json
import socket
import urllib.parse
from pathlib import Path
import httpx

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTextEdit, QLineEdit, QGroupBox, QCheckBox, QMessageBox, QFrame,
    QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl
from PyQt5.QtGui import QColor, QFont, QIcon, QDesktopServices

CONFIG_FILE = Path(__file__).parent / "hob_config.json"
GITHUB_RELEASES_API = "https://api.github.com/repos/FrigadeHQ/hob/releases/latest"

DEFAULT_ENDPOINTS = [
    "http://127.0.0.1:8080/v1",   # Standard llama.cpp / Hob bridge
    "http://127.0.0.1:11434/v1",  # Ollama local endpoint
    "http://127.0.0.1:1234/v1",   # LM Studio local endpoint
    "http://localhost:5000/v1"    # Local webUI endpoint
]


def is_internet_available(timeout: float = 1.2) -> bool:
    """
    Lightning-fast check to determine if the computer has an active internet connection.
    Attempts a socket connection to Cloudflare DNS (1.1.1.1:53) or Google DNS (8.8.8.8:53).
    """
    for host in ["1.1.1.1", "8.8.8.8"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, 53))
            s.close()
            return True
        except Exception:
            pass
    return False


def load_hob_config() -> dict:
    default_cfg = {
        "installed_version": "v0.2.1",
        "custom_endpoint": "http://127.0.0.1:8080/v1",
        "auto_fallback_offline": True,
        "periodic_update_check": True,
        "last_update_check_time": 0,
        "cached_latest_release": None
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def save_hob_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving Hob config: {e}")


def check_hob_latest_release(force: bool = False) -> dict:
    """
    Checks GitHub for the latest Hob release (e.g. v0.2.1).
    Uses caching to avoid exhausting GitHub rate limits.
    """
    cfg = load_hob_config()
    now = time.time()
    
    # 24-hour cache unless forced
    if not force and cfg.get("cached_latest_release") and (now - cfg.get("last_update_check_time", 0) < 86400):
        return cfg["cached_latest_release"]

    if not is_internet_available(timeout=1.0):
        return cfg.get("cached_latest_release") or {
            "version": cfg.get("installed_version", "v0.2.1"),
            "name": f"Hob {cfg.get('installed_version', 'v0.2.1')}",
            "is_update_available": False,
            "offline": True
        }

    try:
        headers = {"User-Agent": "ArchiveMaster-CopticLibrary/2.0"}
        with httpx.Client(timeout=8.0, headers=headers) as client:
            resp = client.get(GITHUB_RELEASES_API)
            if resp.status_code == 200:
                data = resp.json()
                tag = data.get("tag_name", "v0.2.1")
                name = data.get("name", f"Hob {tag}")
                html_url = data.get("html_url", "https://github.com/FrigadeHQ/hob/releases")
                published_at = data.get("published_at", "")
                
                win_installer_url = ""
                for asset in data.get("assets", []):
                    a_name = asset.get("name", "").lower()
                    if a_name.endswith(".exe") and "win" in a_name:
                        win_installer_url = asset.get("browser_download_url", "")
                        break

                current_ver = cfg.get("installed_version", "v0.2.1").lstrip("v")
                remote_ver = tag.lstrip("v")

                is_newer = False
                try:
                    c_parts = [int(x) for x in current_ver.split(".") if x.isdigit()]
                    r_parts = [int(x) for x in remote_ver.split(".") if x.isdigit()]
                    is_newer = r_parts > c_parts
                except Exception:
                    is_newer = (remote_ver != current_ver)

                res = {
                    "version": tag,
                    "name": name,
                    "html_url": html_url,
                    "download_url": win_installer_url or html_url,
                    "published_at": published_at,
                    "is_update_available": is_newer,
                    "offline": False
                }
                cfg["last_update_check_time"] = now
                cfg["cached_latest_release"] = res
                save_hob_config(cfg)
                return res
    except Exception as e:
        print(f"Hob update check error: {e}")

    return cfg.get("cached_latest_release") or {
        "version": cfg.get("installed_version", "v0.2.1"),
        "name": f"Hob {cfg.get('installed_version', 'v0.2.1')}",
        "is_update_available": False,
        "error": True
    }


def ping_local_endpoint(endpoint: str, timeout: float = 1.0) -> tuple:
    """
    Pings a local AI endpoint to see if Hob / llama.cpp / Ollama is currently running.
    Returns (is_active: bool, latency_ms: float, model_name: str)
    """
    t0 = time.time()
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (8080 if "8080" in endpoint else 11434)

    # First fast socket probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
    except Exception:
        return False, 0.0, ""

    # Next check models endpoint
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{base_url}/v1/models")
            dt = (time.time() - t0) * 1000
            if r.status_code == 200:
                data = r.json()
                models = data.get("data", [])
                m_name = models[0].get("id", "local-model") if models else "local-model"
                return True, dt, m_name
    except Exception:
        pass

    return True, (time.time() - t0) * 1000, "local-model"


def call_hob_local(prompt: str, system_instruction: str = "", endpoint: str = None, timeout: float = 60.0) -> str:
    """
    Executes completion against the local Hob / llama.cpp / Ollama engine offline.
    Uses standard OpenAI-compatible API format (POST /v1/chat/completions).
    """
    cfg = load_hob_config()
    target_endpoints = [endpoint] if endpoint else [cfg.get("custom_endpoint")] + DEFAULT_ENDPOINTS

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    for ep in target_endpoints:
        if not ep:
            continue
        clean_ep = ep.rstrip("/")
        if not clean_ep.endswith("/chat/completions"):
            if clean_ep.endswith("/v1"):
                url = f"{clean_ep}/chat/completions"
            else:
                url = f"{clean_ep}/v1/chat/completions"
        else:
            url = clean_ep

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    url,
                    json={
                        "model": "local",
                        "messages": messages,
                        "temperature": 0.35,
                        "max_tokens": 3000
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices and choices[0].get("message", {}).get("content"):
                        return choices[0]["message"]["content"]
        except Exception:
            continue

    return None


class HobManagerDialog(QDialog):
    """
    GUI Manager for Hob Local AI & Offline Fallback Engine.
    Shows connection status, installed version, checks GitHub updates, and tests local model.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖥️ مدير الذكاء الاصطناعي الأوفلاين والمساعد المحلي (Hob Bridge)")
        self.resize(760, 520)
        self.setLayoutDirection(Qt.RightToLeft)

        self.cfg = load_hob_config()
        self.init_ui()
        self.check_status_async()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1E232D;
                color: #E2E8F0;
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
            }
            QGroupBox {
                background-color: #252B36;
                border: 1px solid #3A4454;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                font-size: 13px;
                color: #E5C07B;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 10px;
            }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QLineEdit {
                background-color: #14171E;
                color: white;
                border: 1px solid #3A4454;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #14171E;
                color: #CBD5E1;
                border: 1px solid #3A4454;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton {
                background-color: #2D3442;
                color: white;
                border: 1px solid #3A4454;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #384254; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header
        h_box = QHBoxLayout()
        icon_lbl = QLabel("🖥️")
        icon_lbl.setStyleSheet("font-size: 32px;")
        h_box.addWidget(icon_lbl)

        v_title = QVBoxLayout()
        t_lbl = QLabel("المساعد المحلي الأوفلاين 100% (Hob Local AI Engine)")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E5C07B;")
        v_title.addWidget(t_lbl)

        sub_lbl = QLabel("يعمل كبديل ذكي وفوري في حالة انقطاع الإنترنت، لتشغيل النماذج مفتوحة المصدر (Gemma / gpt-oss) محلياً بأعلى خصوصية.")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        v_title.addWidget(sub_lbl)
        h_box.addLayout(v_title, 1)
        layout.addLayout(h_box)

        # Status Cards Row
        cards_layout = QHBoxLayout()

        # Card 1: Internet Status
        self.card_net = self._create_card("🌐 حالة الإنترنت", "جاري الفحص...", "#38BDF8")
        cards_layout.addWidget(self.card_net)

        # Card 2: Hob Engine Status
        self.card_hob = self._create_card("🖥️ المحرك المحلي (Hob)", "جاري الفحص...", "#F59E0B")
        cards_layout.addWidget(self.card_hob)

        # Card 3: Version Status
        self.card_ver = self._create_card("📦 الإصدار الحالي", self.cfg.get("installed_version", "v0.2.1"), "#34D399")
        cards_layout.addWidget(self.card_ver)

        layout.addLayout(cards_layout)

        # Group 1: Configuration
        grp_cfg = QGroupBox("⚙️ إعدادات المحاكي المحلي ونقاط الاتصال")
        v_cfg = QVBoxLayout(grp_cfg)

        row_ep = QHBoxLayout()
        lbl_ep = QLabel("رابط نقطة الاتصال المحلية (Local Endpoint):")
        row_ep.addWidget(lbl_ep)

        self.le_endpoint = QLineEdit()
        self.le_endpoint.setText(self.cfg.get("custom_endpoint", "http://127.0.0.1:8080/v1"))
        self.le_endpoint.setPlaceholderText("http://127.0.0.1:8080/v1 أو http://127.0.0.1:11434/v1")
        row_ep.addWidget(self.le_endpoint, 1)

        self.btn_test_local = QPushButton("⚡ اختبار الاستجابة المحلية")
        self.btn_test_local.setStyleSheet("background-color: #059669; color: white;")
        self.btn_test_local.clicked.connect(self.test_local_endpoint)
        row_ep.addWidget(self.btn_test_local)
        v_cfg.addLayout(row_ep)

        self.chk_fallback = QCheckBox("🔄 التبديل التلقائي إلى Hob فور رصد انقطاع الإنترنت (Smart Auto-Fallback)")
        self.chk_fallback.setChecked(self.cfg.get("auto_fallback_offline", True))
        self.chk_fallback.setStyleSheet("color: #38BDF8; font-weight: bold;")
        v_cfg.addWidget(self.chk_fallback)

        self.chk_updates = QCheckBox("🔔 الفحص الدوري لتحديثات Hob الجديدة من GitHub أوتوماتيكياً")
        self.chk_updates.setChecked(self.cfg.get("periodic_update_check", True))
        v_cfg.addWidget(self.chk_updates)

        layout.addWidget(grp_cfg)

        # Group 2: Update & Releases from GitHub
        grp_update = QGroupBox("🚀 التحديث الدوري والإصدارات الجديدة (GitHub Releases)")
        v_upd = QVBoxLayout(grp_update)

        h_upd_act = QHBoxLayout()
        self.lbl_update_status = QLabel("جاري التحقق من توفر إصدارات جديدة لبرنامج Hob...")
        self.lbl_update_status.setStyleSheet("color: #CBD5E1; font-size: 12px;")
        h_upd_act.addWidget(self.lbl_update_status, 1)

        self.btn_check_now = QPushButton("🔄 فحص التحديثات الآن")
        self.btn_check_now.clicked.connect(self.check_updates_now)
        h_upd_act.addWidget(self.btn_check_now)

        self.btn_download_hob = QPushButton("📥 تنزيل Hob للويندوز (.exe)")
        self.btn_download_hob.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D97706); color: white;")
        self.btn_download_hob.clicked.connect(self.open_hob_download)
        h_upd_act.addWidget(self.btn_download_hob)

        v_upd.addLayout(h_upd_act)

        self.txt_hob_log = QTextEdit()
        self.txt_hob_log.setReadOnly(True)
        self.txt_hob_log.setFixedHeight(90)
        v_upd.addWidget(self.txt_hob_log)

        layout.addWidget(grp_update)

        # Bottom Buttons
        b_box = QHBoxLayout()
        self.btn_save = QPushButton("💾 حفظ الإعدادات")
        self.btn_save.setStyleSheet("background-color: #059669; color: white; padding: 8px 24px;")
        self.btn_save.clicked.connect(self.save_and_close)
        b_box.addWidget(self.btn_save)

        b_box.addStretch()

        self.btn_close = QPushButton("إغلاق")
        self.btn_close.clicked.connect(self.accept)
        b_box.addWidget(self.btn_close)

        layout.addLayout(b_box)

    def _create_card(self, title, init_val, accent_color):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #252B36;
                border: 1px solid #3A4454;
                border-right: 4px solid {accent_color};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94A3B8; font-size: 11px;")
        v.addWidget(lbl_t)

        lbl_v = QLabel(init_val)
        lbl_v.setObjectName("metric_val")
        lbl_v.setStyleSheet(f"color: {accent_color}; font-size: 14px; font-weight: bold;")
        v.addWidget(lbl_v)
        return frame

    def _set_card_val(self, frame, text, color=None):
        lbl = frame.findChild(QLabel, "metric_val")
        if lbl:
            lbl.setText(str(text))
            if color:
                lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")

    def check_status_async(self):
        # 1. Internet Check
        has_net = is_internet_available(timeout=0.8)
        if has_net:
            self._set_card_val(self.card_net, "🟢 متصل بالسحابة", "#34D399")
        else:
            self._set_card_val(self.card_net, "🔴 منقطع (وضع الأوفلاين)", "#F87171")

        # 2. Local Engine Check
        ep = self.le_endpoint.text().strip()
        is_up, lat, model = ping_local_endpoint(ep, timeout=0.6)
        if is_up:
            self._set_card_val(self.card_hob, f"🟢 نشط ({lat:.0f} ms)", "#34D399")
            self.txt_hob_log.append(f"✅ المحرك المحلي يستجيب بنجاح على {ep} (الموديل: {model}).")
        else:
            self._set_card_val(self.card_hob, "⚠️ غير مشغل حالياً", "#F59E0B")
            self.txt_hob_log.append(f"ℹ️ المحاكي المحلي غير مشغل حالياً على {ep}. سيعتمد النظام على محرك المعرفة الكنسية الأوفلاين الداخلي FTS5 في حالة انقطاع النت.")

        # 3. Check releases
        self.check_updates_now(show_msg=False)

    def test_local_endpoint(self):
        ep = self.le_endpoint.text().strip()
        is_up, lat, model = ping_local_endpoint(ep, timeout=1.5)
        if is_up:
            self._set_card_val(self.card_hob, f"🟢 نشط ({lat:.0f} ms)", "#34D399")
            QMessageBox.information(
                self,
                "نجاح الاتصال المحلي",
                f"✅ تم الاتصال بنجاح بمحاكي الذكاء الاصطناعي المحلي!\n\n"
                f"• العنوان: {ep}\n"
                f"• سرعة الاستجابة: {lat:.1f} ميلي ثانية\n"
                f"• النموذج النشط: {model}\n\n"
                f"المحاكي جاهز للعمل كبديل فوري في حالة قطع النت دون الحاجة للسحابة."
            )
        else:
            self._set_card_val(self.card_hob, "❌ تعذر الاتصال", "#F87171")
            QMessageBox.warning(
                self,
                "تنبيه",
                f"تعذر الاتصال بالمحاكي المحلي على:\n{ep}\n\n"
                f"تأكد من تشغيل تطبيق Hob أو llama.cpp أو Ollama على جهازك أولاً."
            )

    def check_updates_now(self, show_msg=True):
        self.lbl_update_status.setText("⏳ جاري فحص مستودع GitHub...")
        QApplication.processEvents()

        rel = check_hob_latest_release(force=True)
        tag = rel.get("version", "v0.2.1")
        is_new = rel.get("is_update_available", False)

        if is_new:
            self.lbl_update_status.setText(f"🎉 يتوفر إصدار أحدث من Hob: {tag} (أنت تستخدم: {self.cfg.get('installed_version')})")
            self.lbl_update_status.setStyleSheet("color: #34D399; font-weight: bold;")
            self.btn_download_hob.setText(f"📥 ترقية وتنزيل {tag} الآن")
            if show_msg:
                QMessageBox.information(
                    self,
                    "تحديث متوفر لـ Hob",
                    f"🎉 تم رصد إصدار جديد لبرنامج Hob على GitHub: {tag}\n\n"
                    f"اضغط على زر «تنزيل Hob للويندوز» لتحميل التحديث الجديد وتثبيته مباشرة."
                )
        else:
            self.lbl_update_status.setText(f"✅ أنت تستخدم أحدث إصدار معتمد من Hob ({tag}).")
            self.lbl_update_status.setStyleSheet("color: #CBD5E1;")

    def open_hob_download(self):
        rel = self.cfg.get("cached_latest_release") or {}
        dl_url = rel.get("download_url") or "https://github.com/FrigadeHQ/hob/releases"
        QDesktopServices.openUrl(QUrl(dl_url))

    def save_and_close(self):
        self.cfg["custom_endpoint"] = self.le_endpoint.text().strip()
        self.cfg["auto_fallback_offline"] = self.chk_fallback.isChecked()
        self.cfg["periodic_update_check"] = self.chk_updates.isChecked()
        save_hob_config(self.cfg)
        QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات المحاكي المحلي والمساعد الأوفلاين بنجاح.")
        self.accept()
