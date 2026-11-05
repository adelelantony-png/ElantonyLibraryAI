# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Web & Cloud REST API
Provides conversational ChatGPT-like Research Portal, FTS5 Search,
Word (.docx) Export, Book Viewing, and Admin Management Endpoints.
"""

import os
import urllib.parse
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.database.repository import repo
from elantony.search.search_engine import search_engine
from elantony.ai.factory import get_ai_provider
from elantony.telegram.bot_service import TelegramBotEngine

# Global bot task reference
bot_task: Optional[asyncio.Task] = None
bot_engine: Optional[TelegramBotEngine] = None


def ensure_database():
    """Verifies that file_archive.db exists and is ready; downloads from Hugging Face dataset if missing."""
    db_path = Path("file_archive.db")
    if db_path.exists() and db_path.stat().st_size > 100000:
        return

    db_download_url = os.getenv(
        "DATABASE_DOWNLOAD_URL",
        "https://huggingface.co/datasets/AdelGeorg/elantony-db/resolve/main/file_archive.zip"
    ).strip()

    if db_download_url:
        logger.info(f"Database missing in cloud container. Downloading from {db_download_url}...")
        try:
            import urllib.request
            import shutil
            import zipfile
            temp_zip = Path("file_archive_temp.zip")
            req = urllib.request.Request(db_download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as response, open(temp_zip, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(".")
            temp_zip.unlink(missing_ok=True)
            logger.info("Cloud database bootstrap completed successfully.")
        except Exception as e:
            logger.warning(f"Failed to bootstrap database from {db_download_url}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages optional embedded bot worker if explicitly enabled."""
    global bot_task, bot_engine
    ensure_database()
    enable_embedded_bot = os.getenv("ENABLE_BOT_IN_API", "false").lower() == "true"
    if enable_embedded_bot and settings.telegram_bot_token:
        bot_engine = TelegramBotEngine()
        bot_task = asyncio.create_task(bot_engine.run())
        logger.info("Embedded Telegram Bot worker launched in API lifespan.")
    else:
        logger.info("API running in standalone Web mode (Telegram Bot managed by daemon service).")

    yield

    if bot_engine:
        bot_engine.stop()
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ELANTONY LIBRARY AI",
    description="Ecclesiastical Smart Library & Conversational Research Assistant",
    version="2.7.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    limit: Optional[int] = 4
    depth_mode: Optional[str] = "academic"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    turn_number: Optional[int] = None
    citations: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = None
    user_id: Optional[str] = "web"
    depth_mode: Optional[str] = "academic"


class TTSRequest(BaseModel):
    text: str
    lang: Optional[str] = "ar"
    max_chars: Optional[int] = 1200


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "بحث لاهوتي جديد"
    user_id: Optional[str] = "web"


WEB_PORTAL_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✠ ELANTONY LIBRARY AI - المساعد والباحث اللاهوتي الذكي</title>
    <!-- Google Fonts: Amiri (نسخ آبائي مريح للقراءة المطولة) + Cairo (واجهات) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@400;600;700;800;900&family=Noto+Sans+Coptic&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js">
        // Mouse Drag to Pan Zoomed Image
        window.addEventListener('DOMContentLoaded', () => {
            const container = document.getElementById('refImgScrollWrap');
            if (!container) return;
            let isDown = false;
            let startX, startY, scrollLeft, scrollTop;

            container.addEventListener('mousedown', (e) => {
                if (ZOOM_LEVELS[currentZoomIndex] <= 100) return;
                isDown = true;
                container.classList.add('grabbing');
                startX = e.pageX - container.offsetLeft;
                startY = e.pageY - container.offsetTop;
                scrollLeft = container.scrollLeft;
                scrollTop = container.scrollTop;
            });
            container.addEventListener('mouseleave', () => {
                isDown = false;
                container.classList.remove('grabbing');
            });
            container.addEventListener('mouseup', () => {
                isDown = false;
                container.classList.remove('grabbing');
            });
            container.addEventListener('mousemove', (e) => {
                if (!isDown) return;
                e.preventDefault();
                const x = e.pageX - container.offsetLeft;
                const y = e.pageY - container.offsetTop;
                const walkX = (x - startX) * 1.6;
                const walkY = (y - startY) * 1.6;
                container.scrollLeft = scrollLeft - walkX;
                container.scrollTop = scrollTop - walkY;
            });
        });

    </script>
    <style>
        /* ========================================================
           ELANTONY EYE-COMFORT DESIGN SYSTEM (منظومة راحة العين)
           1. Sepia (افتراضي): ورق البرديات والمخطوطات الدافئة المريحة
           2. Dark: هدوء ليلي مخملي بدون سواد فاقع أو توهج أزرق
           3. Light: ورق كنسي صباحي هادئ بدون وهج
           ======================================================== */
        :root {
            /* النمط الافتراضي: برديات دافئة (Sepia / Parchment) */
            --bg-darker: #F5EFE6;
            --bg-sidebar: #ECE3D4;
            --bg-chat: #FAF7F2;
            --bg-bubble-ai: #FFFDF9;
            --bg-bubble-user: #E5D7C3;
            --card-border: #DBCBB5;
            --card-hover: #E8DAC6;
            --accent: #874F19;
            --accent-hover: #6B3C0F;
            --accent-light: rgba(135, 79, 25, 0.12);
            --gold: #A16207;
            --gold-light: #FEF3C7;
            --text-main: #2A2118;
            --text-sub: #705F4E;
            --text-user: #231B14;
            --quote-bg: rgba(161, 98, 7, 0.08);
            --quote-border: #A16207;
            --citation-bg: #F2E8DC;
            --input-bg: #FFFDF9;
            --nav-bg: rgba(245, 239, 230, 0.94);
            --modal-bg: #FFFDF9;
            --shadow-sm: 0 1px 3px rgba(42, 33, 24, 0.06);
            --shadow-md: 0 4px 16px rgba(42, 33, 24, 0.09);
            --font-reader: 'Amiri', 'Noto Sans Coptic', 'Segoe UI Historic', serif;
            --font-size: 16.5px;
            --line-height: 1.95;
            --radius-bubble: 14px;
        }

        /* 🌙 هدوء ليلي مخملي (Soft Slate Dark) */
        body[data-theme="dark"] {
            --bg-darker: #13161F;
            --bg-sidebar: #181C27;
            --bg-chat: #151822;
            --bg-bubble-ai: #1B202D;
            --bg-bubble-user: #27364D;
            --card-border: #283042;
            --card-hover: #222938;
            --accent: #5294E2;
            --accent-hover: #3B82F6;
            --accent-light: rgba(82, 148, 226, 0.15);
            --gold: #E5A93C;
            --gold-light: #FDE68A;
            --text-main: #D5DDE8;
            --text-sub: #8492A6;
            --text-user: #F1F5F9;
            --quote-bg: rgba(229, 169, 60, 0.08);
            --quote-border: #E5A93C;
            --citation-bg: #161B26;
            --input-bg: #181D29;
            --nav-bg: rgba(19, 22, 31, 0.92);
            --modal-bg: #181D29;
            --shadow-sm: 0 1px 4px rgba(0, 0, 0, 0.25);
            --shadow-md: 0 6px 20px rgba(0, 0, 0, 0.4);
        }

        /* ☀️ ورق كنسي صباحي ناصع (Clean Daylight Paper) */
        body[data-theme="light"] {
            --bg-darker: #EEF2F6;
            --bg-sidebar: #F4F7FA;
            --bg-chat: #FFFFFF;
            --bg-bubble-ai: #F8FAFC;
            --bg-bubble-user: #E2E8F0;
            --card-border: #CBD5E1;
            --card-hover: #E2E8F0;
            --accent: #1E40AF;
            --accent-hover: #1D4ED8;
            --accent-light: rgba(30, 64, 175, 0.1);
            --gold: #B45309;
            --gold-light: #FEF3C7;
            --text-main: #1E293B;
            --text-sub: #64748B;
            --text-user: #0F172A;
            --quote-bg: rgba(180, 83, 9, 0.06);
            --quote-border: #B45309;
            --citation-bg: #F1F5F9;
            --input-bg: #FFFFFF;
            --nav-bg: rgba(255, 255, 255, 0.94);
            --modal-bg: #FFFFFF;
            --shadow-sm: 0 1px 4px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg-darker);
            color: var(--text-main);
            font-family: 'Cairo', sans-serif;
            height: 100vh;
            display: flex;
            overflow: hidden;
            transition: background 0.25s ease, color 0.25s ease;
        }

        /* Sidebar */
        .sidebar {
            width: 290px;
            background: var(--bg-sidebar);
            border-left: 1px solid var(--card-border);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            z-index: 20;
        }
        .sidebar-header {
            padding: 16px 18px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .app-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 900;
            font-size: 15px;
            color: var(--text-main);
            letter-spacing: 0.5px;
        }
        .app-brand span { color: var(--gold); font-size: 18px; }
        .btn-new-chat {
            margin: 14px 16px;
            background: var(--accent-light);
            border: 1px dashed var(--accent);
            color: var(--accent);
            padding: 10px;
            border-radius: 9px;
            font-weight: 700;
            font-size: 13.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: 0.2s;
        }
        .btn-new-chat:hover { background: var(--accent); color: #FFF; border-style: solid; transform: translateY(-1px); }
        
        .chat-history-title {
            padding: 6px 18px;
            font-size: 11px;
            font-weight: 800;
            color: var(--text-sub);
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .chat-history {
            flex: 1;
            overflow-y: auto;
            padding: 0 12px;
        }
        .chat-history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-sub);
            cursor: pointer;
            margin-bottom: 4px;
            transition: 0.2s;
            border: 1px solid transparent;
        }
        .chat-history-item:hover {
            background: var(--card-hover);
            color: var(--text-main);
        }
        .chat-history-item.active {
            background: var(--accent-light);
            border-color: var(--accent);
            color: var(--accent);
            font-weight: 700;
        }
        .chat-item-text {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-left: 6px;
        }
        .chat-item-actions {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .btn-sess-act {
            opacity: 0;
            background: none;
            border: none;
            font-size: 12px;
            cursor: pointer;
            padding: 3px 6px;
            border-radius: 4px;
            transition: 0.2s;
            color: var(--text-sub);
        }
        .chat-history-item:hover .btn-sess-act { opacity: 0.85; }
        .btn-sess-act:hover { opacity: 1; background: var(--card-hover); color: var(--text-main); }
        .btn-sess-del:hover { background: rgba(239,68,68,0.18); color: #DC2626; }

        .sidebar-footer {
            padding: 12px 16px;
            border-top: 1px solid var(--card-border);
            font-size: 12px;
            color: var(--text-sub);
            background: var(--card-hover);
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .sidebar-footer strong { color: var(--gold); }
        .sidebar-footer a { color: var(--accent); text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; }

        /* Main Container */
        .main-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }
        .top-navbar {
            min-height: 60px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 18px;
            background: var(--nav-bg);
            backdrop-filter: blur(10px);
            gap: 10px;
            flex-wrap: wrap;
            z-index: 10;
        }
        .nav-title { font-weight: 900; font-size: 14.5px; display: flex; align-items: center; gap: 8px; color: var(--text-main); }
        .nav-title span { color: var(--gold); font-size: 18px; }

        /* Control Groups */
        .controls-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .theme-switch-group, .font-ctrl-group, .depth-selector-group {
            display: inline-flex;
            align-items: center;
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            border-radius: 9px;
            padding: 3px;
            gap: 2px;
        }
        .ctrl-label {
            font-size: 11px;
            font-weight: 800;
            color: var(--gold);
            padding: 0 6px;
        }
        .btn-ctrl {
            background: none;
            border: none;
            color: var(--text-sub);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.18s;
            font-family: 'Cairo', sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
        }
        .btn-ctrl:hover { color: var(--text-main); background: var(--card-hover); }
        .btn-ctrl.active {
            background: var(--accent);
            color: #FFF;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }
        .font-size-label {
            font-size: 11px;
            font-weight: 800;
            color: var(--gold);
            min-width: 38px;
            text-align: center;
        }

        .nav-actions { display: flex; align-items: center; gap: 6px; }
        .btn-nav {
            padding: 5px 11px;
            border-radius: 7px;
            font-weight: 700;
            font-size: 12px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: 0.2s;
            border: 1px solid transparent;
            text-decoration: none;
            font-family: 'Cairo', sans-serif;
        }
        .btn-compile { background: rgba(161, 98, 7, 0.14); border-color: var(--gold); color: var(--gold); }
        .btn-compile:hover { background: var(--gold); color: #FFF; }
        .btn-docx-nav { background: rgba(16, 185, 129, 0.14); border-color: #10B981; color: #059669; }
        .btn-docx-nav:hover { background: #10B981; color: #FFF; }

        /* Messages Window */
        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .messages-container {
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* Message Bubbles */
        .msg-row {
            display: flex;
            gap: 12px;
            width: 100%;
        }
        .msg-row.user {
            justify-content: flex-start;
            flex-direction: row-reverse;
        }
        .msg-avatar {
            width: 36px;
            height: 36px;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 15px;
            font-weight: 900;
            flex-shrink: 0;
        }
        .msg-avatar.ai { background: var(--accent); color: #FFF; box-shadow: var(--shadow-sm); }
        .msg-avatar.user { background: var(--card-border); color: var(--text-main); }

        .msg-content {
            max-width: 86%;
            display: flex;
            flex-direction: column;
        }
        .turn-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--accent-light);
            border: 1px solid var(--card-border);
            color: var(--accent);
            font-size: 11px;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 6px;
            margin-bottom: 6px;
            align-self: flex-start;
        }
        .bubble {
            padding: 20px 24px;
            border-radius: var(--radius-bubble);
            font-size: var(--font-size);
            line-height: var(--line-height);
            word-break: break-word;
            font-family: var(--font-reader);
            box-shadow: var(--shadow-sm);
        }
        .msg-row.user .bubble {
            background: var(--bg-bubble-user);
            color: var(--text-user);
            border-top-left-radius: 4px;
            border: 1px solid var(--card-border);
            font-family: 'Cairo', sans-serif;
            font-weight: 600;
        }
        .msg-row.ai .bubble {
            background: var(--bg-bubble-ai);
            color: var(--text-main);
            border: 1px solid var(--card-border);
            border-top-right-radius: 4px;
            box-shadow: var(--shadow-md);
        }

        /* Markdown Typography inside assistant bubble */
        .bubble h1, .bubble h2, .bubble h3, .bubble h4 {
            color: var(--accent);
            margin: 16px 0 8px 0;
            font-family: 'Cairo', sans-serif;
            font-weight: 800;
        }
        .bubble h2 { font-size: 1.25em; border-bottom: 1px dashed var(--card-border); padding-bottom: 6px; }
        .bubble h3 { font-size: 1.1em; }
        .bubble p { margin-bottom: 14px; }
        .bubble p:last-child { margin-bottom: 0; }
        .bubble ul, .bubble ol { margin: 8px 24px 14px 24px; }
        .bubble li { margin-bottom: 6px; }
        .bubble strong { color: var(--gold); font-weight: 700; }
        .bubble hr { border: 0; height: 1px; background: var(--card-border); margin: 16px 0; }
        .bubble blockquote {
            border-right: 4px solid var(--quote-border);
            padding: 10px 16px;
            margin: 14px 0;
            color: var(--text-main);
            background: var(--quote-bg);
            border-radius: 8px;
            font-size: 1.02em;
            line-height: 1.9;
        }

        /* Citations Box */
        .citations-section {
            margin-top: 14px;
            background: var(--citation-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px 16px;
            box-shadow: var(--shadow-sm);
        }
        .citations-header {
            font-size: 13px;
            font-weight: 800;
            color: var(--gold);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .citations-list {
            margin-top: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .citation-item {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            border-radius: 9px;
            padding: 12px 14px;
            font-size: 13px;
            box-shadow: var(--shadow-sm);
        }
        .citation-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .citation-title { font-weight: 800; color: var(--accent); font-size: 14px; font-family: 'Cairo', sans-serif; }
        .citation-badge { background: var(--accent-light); color: var(--accent); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; white-space: nowrap; }
        .citation-meta { font-size: 12px; color: var(--text-sub); margin-top: 4px; }
        .citation-excerpt { color: var(--text-main); font-size: 13px; margin-top: 8px; border-right: 3px solid var(--gold); padding: 8px 12px; border-radius: 6px; background: var(--card-hover); line-height: 1.75; font-family: var(--font-reader); }
        .citation-actions { margin-top: 10px; display: flex; gap: 8px; }
        .btn-cite-act {
            font-size: 11.5px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: 0.2s;
            font-family: 'Cairo', sans-serif;
        }
        .btn-cite-fast { background: rgba(16, 185, 129, 0.16); border: 1px solid #10B981; color: #059669; font-weight: 800; cursor: pointer; }
        .btn-cite-fast:hover { background: #10B981; color: #FFF; transform: translateY(-1px); }
        .btn-cite-view { background: var(--accent-light); border: 1px solid var(--accent); color: var(--accent); }
        .btn-cite-view:hover { background: var(--accent); color: #FFF; }
        .btn-cite-dl { background: var(--card-hover); border: 1px solid var(--card-border); color: var(--text-main); }
        .btn-cite-dl:hover { background: var(--card-border); }

        /* Hero / Empty State */
        .hero {
            text-align: center;
            margin: auto 0;
            padding: 30px 20px;
        }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--accent-light);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 13.5px;
            font-weight: 800;
            margin-bottom: 14px;
        }
        .hero h2 { font-size: 1.85rem; font-weight: 900; color: var(--text-main); margin-bottom: 8px; }
        .hero p { color: var(--text-sub); font-size: 15px; max-width: 640px; margin: 0 auto 26px auto; line-height: 1.75; }
        .prompt-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
            gap: 14px;
            max-width: 860px;
            margin: 0 auto;
        }
        .prompt-card {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            padding: 16px;
            border-radius: 12px;
            text-align: right;
            cursor: pointer;
            transition: 0.2s;
            font-size: 14px;
            color: var(--text-main);
            box-shadow: var(--shadow-sm);
        }
        .prompt-card:hover {
            border-color: var(--accent);
            background: var(--card-hover);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        /* Bottom Input Bar */
        .input-area {
            padding: 14px 20px 18px 20px;
            border-top: 1px solid var(--card-border);
            background: var(--bg-sidebar);
            transition: background 0.25s ease;
        }
        .input-box-wrapper {
            max-width: 900px;
            margin: 0 auto;
            position: relative;
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            display: flex;
            align-items: flex-end;
            padding: 8px 14px;
            transition: 0.2s;
            box-shadow: var(--shadow-sm);
        }
        .input-box-wrapper:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-light);
        }
        .chat-textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 15px;
            font-family: 'Cairo', sans-serif;
            resize: none;
            outline: none;
            max-height: 180px;
            min-height: 28px;
            line-height: 1.6;
            padding: 6px 0;
        }
        .chat-textarea::placeholder {
            color: var(--text-sub);
            opacity: 0.8;
        }
        .btn-send {
            background: var(--accent);
            color: #FFF;
            border: none;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: 0.2s;
            margin-right: 8px;
            flex-shrink: 0;
            font-size: 16px;
        }
        .btn-send:hover { background: var(--accent-hover); transform: scale(1.05); }
        .btn-send:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .input-disclaimer {
            text-align: center;
            font-size: 12px;
            color: var(--text-sub);
            margin-top: 8px;
        }

        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal-overlay.open { display: flex; }
        .modal-card {
            background: var(--modal-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            width: 100%;
            max-width: 960px;
            max-height: 88vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .modal-header {
            padding: 16px 22px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-sidebar);
        }
        .modal-title {
            font-weight: 800;
            font-size: 16px;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .modal-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .btn-modal-act {
            background: var(--accent-light);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
            font-family: 'Cairo', sans-serif;
        }
        .btn-modal-act:hover { background: var(--accent); color: #FFF; }
        .btn-modal-docx {
            background: rgba(16, 185, 129, 0.16);
            border-color: #10B981;
            color: #059669;
        }
        .btn-modal-docx:hover { background: #10B981; color: #FFF; }
        .btn-modal-close {
            background: none;
            border: none;
            color: var(--text-sub);
            font-size: 20px;
            cursor: pointer;
            padding: 4px 8px;
        }
        .btn-modal-close:hover { color: #EF4444; }
        .modal-body {
            flex: 1;
            overflow-y: auto;
            padding: 26px 30px;
            color: var(--text-main);
            font-size: var(--font-size);
            line-height: var(--line-height);
            font-family: var(--font-reader);
        }
        .modal-body h1, .modal-body h2, .modal-body h3 { color: var(--accent); margin: 16px 0 8px 0; font-family: 'Cairo', sans-serif; }
        .modal-body strong { color: var(--gold); }
        .modal-body blockquote { border-right: 4px solid var(--quote-border); padding: 8px 14px; margin: 12px 0; background: var(--quote-bg); border-radius: 6px; }

        /* Loading Dots */
        .typing-dots { display: inline-flex; gap: 4px; padding: 6px 0; }
        .typing-dots span { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: blink 1.4s infinite; }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }

        /* Enhanced Reference Viewer Modal */
        .ref-modal-card {
            max-width: 980px !important;
            width: 95vw !important;
            max-height: 94vh !important;
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            background: var(--modal-bg);
            border: 1px solid var(--card-border);
            box-shadow: 0 25px 60px rgba(0,0,0,0.4);
        }
        .ref-modal-header {
            padding: 12px 18px;
            border-bottom: 1px solid var(--card-border);
            background: var(--bg-sidebar);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }
        .ref-modal-title-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            flex: 1;
        }
        .ref-icon { font-size: 19px; flex-shrink: 0; }
        .ref-book-name {
            font-weight: 800;
            font-size: 14.5px;
            color: var(--accent);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 460px;
        }
        .ref-badge-page {
            background: var(--accent-light);
            color: var(--accent);
            border: 1px solid var(--card-border);
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 800;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .ref-badge-size {
            background: rgba(161, 98, 7, 0.12);
            color: var(--gold);
            border: 1px solid var(--gold);
            padding: 2px 7px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .btn-modal-close-ref {
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.25);
            color: #EF4444;
            font-size: 13px;
            font-weight: 800;
            cursor: pointer;
            padding: 5px 12px;
            border-radius: 7px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: 0.2s;
            flex-shrink: 0;
            font-family: 'Cairo', sans-serif;
        }
        .btn-modal-close-ref:hover {
            background: #EF4444;
            color: #FFF;
            border-color: #EF4444;
        }
        .ref-modal-toolbar {
            padding: 8px 16px;
            border-bottom: 1px solid var(--card-border);
            background: var(--bg-darker);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            flex-wrap: wrap;
        }
        .ref-nav-group, .ref-mode-group, .ref-actions-group {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
        }
        .btn-ref-nav {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 5px 11px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
            transition: 0.18s;
        }
        .btn-ref-nav:hover { background: var(--card-hover); border-color: var(--accent); }
        .ref-page-input-wrap {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 6px;
            padding: 2px 7px;
            font-size: 12px;
            font-weight: 700;
        }
        .ref-page-input-wrap input {
            width: 48px;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 12px;
            font-weight: 800;
            text-align: center;
            outline: none;
            font-family: 'Cairo', sans-serif;
        }
        .btn-ref-go {
            background: var(--accent);
            color: #FFF;
            border: none;
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
        }
        .btn-ref-go:hover { background: var(--accent-hover); }
        .ref-mode-wrap {
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 7px;
            padding: 2px;
            display: inline-flex;
            align-items: center;
            gap: 2px;
        }
        .btn-ref-mode {
            background: transparent;
            border: none;
            color: var(--text-sub);
            padding: 4px 9px;
            border-radius: 5px;
            font-size: 11.5px;
            font-weight: 700;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
            transition: 0.18s;
        }
        .btn-ref-mode.active {
            background: var(--accent);
            color: #FFF;
        }
        .btn-ref-action {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: 'Cairo', sans-serif;
            transition: 0.18s;
            cursor: pointer;
        }
        .btn-ref-action:hover {
            border-color: var(--accent);
            background: var(--card-hover);
            color: var(--accent);
        }
        .btn-ref-download {
            background: rgba(16, 185, 129, 0.13);
            border-color: #10B981;
            color: #059669;
            font-weight: 800;
        }
        .btn-ref-download:hover {
            background: #10B981;
            color: #FFF;
        }
        .ref-modal-body {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            background: var(--bg-chat);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 480px;
        }
        .ref-page-image {
            transform-origin: center top;
            transition: transform 0.15s ease-out;
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--card-border);
            display: block;
            margin: 0 auto;
        }
        .ref-zoom-group {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            border-radius: 7px;
            padding: 2px 4px;
        }
        .ref-zoom-btn {
            background: none;
            border: none;
            color: var(--text-main);
            font-size: 13px;
            font-weight: 800;
            padding: 3px 8px;
            cursor: pointer;
            border-radius: 4px;
            transition: 0.18s;
        }
        .ref-zoom-btn:hover { background: var(--card-hover); color: var(--accent); }
        .ref-zoom-badge {
            font-size: 11px;
            font-weight: 800;
            color: var(--gold);
            min-width: 38px;
            text-align: center;
        }
        .btn-ref-tool {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 700;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: 0.18s;
        }
        .btn-ref-tool:hover { border-color: var(--gold); color: var(--gold); }
        .btn-ref-tool.active {
            background: rgba(161, 98, 7, 0.15);
            border-color: var(--gold);
            color: var(--gold);
        }
        .ref-img-scroll-container {
            overflow: auto;
            max-height: 70vh;
            width: 100%;
            text-align: center;
            cursor: grab;
            user-select: none;
            padding: 6px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .ref-img-scroll-container.grabbing {
            cursor: grabbing;
        }
        .ref-modal-card.fullscreen {
            max-width: 98vw !important;
            width: 98vw !important;
            max-height: 98vh !important;
            height: 98vh !important;
            border-radius: 10px;
        }
        .ref-modal-card.fullscreen .ref-img-scroll-container {
            max-height: 84vh !important;
        }
        .ref-excerpt-drawer {
            margin-top: 10px;
            background: var(--quote-bg);
            border-right: 4px solid var(--gold);
            border-radius: 8px;
            padding: 10px 16px;
            text-align: right;
            width: 100%;
            max-width: 880px;
            font-size: 13px;
            line-height: 1.8;
            color: var(--text-main);
            box-shadow: var(--shadow-sm);
        }
        .ref-excerpt-title {
            font-size: 11.5px;
            font-weight: 800;
            color: var(--gold);
            margin-bottom: 4px;
        }

        /* External Authoritative Patristic Sources */
        .external-sources-pill-box {
            margin-top: 14px;
            padding: 10px 14px;
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ext-label {
            font-size: 11.5px;
            font-weight: 800;
            color: var(--gold);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .ext-chips-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .ext-source-chip {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: 0.18s;
            font-family: 'Cairo', sans-serif;
        }
        .ext-source-chip:hover {
            background: var(--card-hover);
            border-color: var(--gold);
            color: var(--gold);
            transform: translateY(-1px);
        }

        @media (max-width: 992px) {
            .sidebar { display: none; }
            .top-navbar { flex-direction: column; align-items: stretch; gap: 8px; padding: 10px; }
            .controls-wrapper { justify-content: center; }
            .nav-actions { justify-content: center; }
        }
    </style>
</head>
<body data-theme="sepia">
    <!-- Sidebar -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="app-brand">
                <span>✠</span> ELANTONY AI
            </div>
            <a href="https://t.me/ElantonyLibrarybot" target="_blank" title="فتح البوت الرسمي على تليجرام" style="color: var(--accent); font-size: 18px; text-decoration: none;">
                ✈️
            </a>
        </div>
        <button class="btn-new-chat" onclick="startNewChat()">
            <span>➕</span> بحث لاهوتي جديد
        </button>
        <div class="chat-history-title">📂 أبحاثك ومناقشاتك المحفوظة</div>
        <div class="chat-history" id="chatHistoryList">
            <!-- Sessions populate dynamically -->
        </div>
        <div class="sidebar-footer">
            <div>🏛️ <strong>7,200+</strong> كتاباً ومخطوطاً</div>
            <div>📜 <strong>شواهد موثقة</strong> (صفر هلوسة)</div>
            <div>📄 <strong>تصدير فوري</strong> Word (.docx)</div>
            <div style="margin-top: 6px;">
                <a href="https://t.me/ElantonyLibrarybot" target="_blank">📱 @ElantonyLibrarybot</a>
            </div>
        </div>
    </aside>

    <!-- Main Chat Container -->
    <main class="main-container">
        <!-- Top Navbar with Eye-Comfort Controls -->
        <div class="top-navbar">
            <div class="nav-title">
                <span>✠</span> المساعد والباحث اللاهوتي الذكي
            </div>

            <div class="controls-wrapper">
                <!-- Theme Switcher (أقصى راحة للعين) -->
                <div class="theme-switch-group" title="اختر نمط الإضاءة المريح لعينيك">
                    <span class="ctrl-label">🎨 المظهر:</span>
                    <button class="btn-ctrl active" id="th_sepia" onclick="setTheme('sepia')" title="ورق برديات دافئ مهدئ للعينين (الأفضل للقراءة المطولة)">📜 برديات دافئة</button>
                    <button class="btn-ctrl" id="th_dark" onclick="setTheme('dark')" title="هدوء ليلي مخملي مضاد للوهج">🌙 ليلي هادئ</button>
                    <button class="btn-ctrl" id="th_light" onclick="setTheme('light')" title="ورق كنسي صباحي هادئ">☀️ ورقي ناصع</button>
                </div>

                <!-- Font & Size Adjuster (التحكم في الخط والحجم) -->
                <div class="font-ctrl-group" title="التحكم في خط وحجم القراءة">
                    <button class="btn-ctrl" id="btnFontToggle" onclick="toggleFontFamily()" title="التبديل بين خط النسخ الآبائي وخط كايرو الحديث">🔤 نسخ آبائي</button>
                    <button class="btn-ctrl" onclick="adjustFontSize(-1)" title="تصغير الخط">A-</button>
                    <span class="font-size-label" id="fontSizeLabel">100%</span>
                    <button class="btn-ctrl" onclick="adjustFontSize(1)" title="تكبير الخط">A+</button>
                </div>

                <!-- Depth Mode Switcher -->
                <div class="depth-selector-group" title="اختر نمط وعمق الإجابة اللاهوتية">
                    <span class="ctrl-label">العمق:</span>
                    <button class="btn-ctrl active" id="depth_academic" onclick="setDepthMode('academic')">🎓 أكاديمي</button>
                    <button class="btn-ctrl" id="depth_pastoral" onclick="setDepthMode('pastoral')">🕊️ رعوي</button>
                    <button class="btn-ctrl" id="depth_apologetic" onclick="setDepthMode('apologetic')">⚖️ دفاعي</button>
                </div>
            </div>

            <div class="nav-actions">
                <button class="btn-nav btn-compile" onclick="openCompilationModal()" title="تجميع أسئلة وإجابات البحث مع الفهرس والمراجع">
                    <span>📑</span> تجميع البحث
                </button>
                <button class="btn-nav btn-docx-nav" onclick="downloadCurrentExport('docx')" title="تنزيل أطروحة البحث كاملة كملف Microsoft Word منسق">
                    <span>📄</span> Word
                </button>
            </div>
        </div>

        <!-- Messages Area -->
        <div class="messages-area" id="messagesArea">
            <div class="messages-container" id="messagesContainer">
                <!-- Hero screen when no messages -->
                <div class="hero" id="heroScreen">
                    <div class="hero-badge">✠ منظومة ELANTONY LIBRARY AI</div>
                    <h2>كيف يمكنني مساندتك في بحثك الكنسي اليوم؟</h2>
                    <p>أنا مساعدك اللاهوتي والآبائي المتخصص؛ أستحضر لك دراسات موثقة بالشواهد والصفحات من بطون أمهات الكتب الكنسية مع إمكانية تصدير البحث كاملاً كملف Word منسق.</p>
                    <div class="prompt-cards">
                        <div class="prompt-card" onclick="sendPrompt('ما مفهوم التجسد الإلهي في الفكر الآبائي عند القديس أثناسيوس الرسولي؟ اذكر المراجع وأرقام الصفحات')">
                            🎓 <strong>دراسة أكاديمية آبائية:</strong>
                            <div style="font-size: 12.5px; color: var(--text-sub); margin-top: 4px;">عقيدة تجسد الكلمة وتجديد الطبيعة مع الشواهد والصفحات</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('قارن بين إقامة السيد المسيح للموتى بسلطانه وإقامة أنبياء العهد القديم للموتى في تعليم الآباء')">
                            ⚖️ <strong>دراسة دفاعية ومقارنة:</strong>
                            <div style="font-size: 12.5px; color: var(--text-sub); margin-top: 4px;">الفارق الجوهري والسلطان الإلهي الذاتي وتفنيد الشبهات</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('كيف يعيش المؤمن حياة الصلاة الدائمة ونقاوة الفكر بحسب تعاليم القديس أنطونيوس الكبير؟')">
                            🕊️ <strong>إرشاد رعوي وروحي:</strong>
                            <div style="font-size: 12.5px; color: var(--text-sub); margin-top: 4px;">حرب الأفكار وجهاد التوبة والهدوء في الحياة اليومية</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('اشرح الأبعاد اللاهوتية والخلاصية لطقس صلاة الصلح وسر الإفخارستيا في القداس الباسيلي')">
                            ⛪ <strong>تأصيل طقسي وليتورجي:</strong>
                            <div style="font-size: 12.5px; color: var(--text-sub); margin-top: 4px;">المصالحة العظمى وقبلة المحبة والسلام والشركة الحية</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
            <div class="input-box-wrapper">
                <textarea 
                    id="chatInput" 
                    class="chat-textarea" 
                    placeholder="تفضل بكتابة سؤالك اللاهوتي هنا... (يمكنك طرح أسئلة فرعية متتابعة وتجميعها كملف Word بنقرة واحدة)"
                    rows="1"
                    onkeydown="handleKey(event)"
                    oninput="autoResize(this)"
                ></textarea>
                <button class="btn-send" id="btnSend" onclick="sendMessage()" title="إرسال السؤال">
                    ➤
                </button>
            </div>
            <div class="input-disclaimer">
                المساعد مستند بالكامل إلى نصوص المراجع الكنسية المعتمدة ومحمي بضوابط منع الهلوسة والتوثيق الحرفي.
            </div>
        </div>
    </main>

    <!-- Modal for Compiled Monograph -->
    <div class="modal-overlay" id="compileModal">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title">
                    <span>✠</span> أطروحة البحث اللاهوتية المجمعة (سؤال وتحته الإجابات)
                </div>
                <div class="modal-actions">
                    <button class="btn-modal-act btn-modal-docx" onclick="downloadCurrentExport('docx')">📄 مستند Word (.docx)</button>
                    <button class="btn-modal-act" onclick="copyCompilationText()">📋 نسخ النص</button>
                    <button class="btn-modal-act" onclick="downloadCurrentExport('markdown')">📥 (.md)</button>
                    <button class="btn-modal-act" onclick="window.print()">🖨️ طباعة</button>
                    <button class="btn-modal-close" onclick="closeCompilationModal()">✕</button>
                </div>
            </div>
            <div class="modal-body" id="compileModalBody">
                <div style="text-align: center; padding: 40px; color: var(--text-sub);">جاري تجميع البحث وتوثيق المراجع...</div>
            </div>
        </div>
    </div>

    <!-- Instant Reference Viewer Modal (فتح واستعراض المراجع في أجزاء من الثانية) -->
    <div class="modal-overlay" id="refModal">
        <div class="modal-card ref-modal-card">
            <!-- Modal Header Row 1: Title and Close -->
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">📖</span>
                    <span id="refBookName" class="ref-book-name" title="اسم المرجع">اسم المرجع</span>
                    <span class="ref-badge-page">صـ <span id="refPageNum">1</span><span id="refPageTotalSpan" style="display: none;"> / <span id="refPageTotal">--</span></span></span>
                    <span id="refSizeBadge" class="ref-badge-size"></span>
                </div>
                <button class="btn-modal-close-ref" onclick="closeRefModal()" title="إغلاق النافذة">✕ إغلاق</button>
            </div>

            <!-- Modal Header Row 2: Navigation & Action Toolbar -->
            <div class="ref-modal-toolbar">
                <!-- Page Navigation Controls -->
                <div class="ref-nav-group">
                    <button class="btn-ref-nav" onclick="stepRefPage(-1)" title="الصفحة السابقة">◀ السابقة</button>
                    <div class="ref-page-input-wrap">
                        <span>صـ</span>
                        <input type="number" id="refPageInput" min="1" value="1" onkeydown="handleRefPageKey(event)">
                        <button class="btn-ref-go" onclick="goToRefPage()" title="انتقال إلى الصفحة">ذهاب</button>
                    </div>
                    <button class="btn-ref-nav" onclick="stepRefPage(1)" title="الصفحة التالية">التالية ▶</button>
                </div>

                <!-- Zoom Controls (التحكم في تكبير وتصغير الصفحة) -->
                <div class="ref-zoom-group" title="التحكم في تكبير وتصغير صفحة المرجع">
                    <button class="ref-zoom-btn" onclick="adjustZoom(-1)" title="تصغير">🔍-</button>
                    <span id="refZoomLevel" class="ref-zoom-badge">100%</span>
                    <button class="ref-zoom-btn" onclick="adjustZoom(1)" title="تكبير">🔍+</button>
                    <button class="ref-zoom-btn" onclick="resetZoom()" title="إعادة ضبط الحجم الأصلي">↺</button>
                </div>

                <!-- Highlight & Excerpt Tools -->
                <div class="ref-mode-wrap">
                    <button id="btnToggleHighlight" class="btn-ref-tool active" onclick="toggleHighlight()" title="تفعيل/تعطيل التمييز اللوني الذهبي للنص المستخرج على الصفحة">🖍️ هاي لايت</button>
                    <button id="btnToggleExcerpt" class="btn-ref-tool" onclick="toggleExcerptDrawer()" title="عرض النص المقتبس الموثق من الصفحة">📜 النص الموثق</button>
                    <button id="btnToggleFullscreen" class="btn-ref-tool" onclick="toggleFullscreen()" title="تكبير النافذة لملء الشاشة">⛶ ملء الشاشة</button>
                </div>

                <!-- View Mode Toggle (Image vs PDF) -->
                <div class="ref-mode-wrap">
                    <button class="btn-ref-mode active" id="btnModeImg" onclick="setRefViewMode('image')" title="عرض صورة الصفحة في أجزاء من الثانية">🖼️ صورة سريعة</button>
                    <button class="btn-ref-mode" id="btnModePdf" onclick="setRefViewMode('pdf')" title="عرض صفحة الـ PDF المدمجة التفاعلية">📑 PDF تفاعلي</button>
                </div>

                <!-- Book Direct Actions -->
                <div class="ref-actions-group">
                    <a id="refDirectPdfBtn" href="#" target="_blank" class="btn-ref-action" title="فتح صفحة المرجع كملف PDF مستقل (15-30 كيلوبايت)">📄 PDF الصفحة</a>
                    <a id="refViewFullBtn" href="#" target="_blank" class="btn-ref-action" title="فتح الكتاب كاملاً في لسان جديد بالمتصفح">📖 فتح كامل بالمتصفح</a>
                    <a id="refFullBookBtn" href="#" class="btn-ref-action btn-ref-download" title="تحميل ملف الكتاب كاملاً مباشرة على جهازك">💾 تحميل الكتاب</a>
                </div>
            </div>

            <!-- Modal Body -->
            <div class="ref-modal-body" id="refModalBody">
                <div id="refLoading" style="padding: 40px 20px; color: var(--text-sub); text-align: center;">
                    <div class="typing-dots"><span></span><span></span><span></span></div>
                    <div id="refLoadingText" style="margin-top: 10px; font-weight: 700;">جاري استخراج وعرض الصفحة فوراً...</div>
                </div>
                <!-- Image Viewer with Scroll & Drag Pan -->
                <div id="refImgContainer" style="width: 100%; text-align: center;">
                    <div id="refImgScrollWrap" class="ref-img-scroll-container">
                        <img id="refPageImg" src="" alt="صفحة المرجع" class="ref-page-image" style="display: none;">
                    </div>
                    <!-- Collapsible Excerpt Drawer -->
                    <div id="refExcerptBox" class="ref-excerpt-drawer" style="display: none;">
                        <div class="ref-excerpt-title">❝ النص الموثق المستخرج من هذه الصفحة بدقة:</div>
                        <div id="refExcerptContent" class="ref-excerpt-text"></div>
                    </div>
                </div>
                <!-- Embedded PDF Viewer (Iframe) -->
                <div id="refPdfContainer" style="display: none; height: 72vh; width: 100%;">
                    <iframe id="refPdfFrame" src="" style="width: 100%; height: 100%; border: none; border-radius: 8px;"></iframe>
                </div>
            </div>
        </div>
    </div>

    <script>
        let chatMessages = [];
        let currentSessionId = null;
        let currentDepthMode = "academic";
        let rawCompiledMarkdown = "";
        let currentFont = 'amiri';
        let currentFontSizeIndex = 2; // [14, 15, 16.5, 18, 20, 22]
        const FONT_SIZES = [14, 15, 16.5, 18, 20, 22];
        const FONT_LABELS = ['85%', '92%', '100%', '110%', '122%', '135%'];

        const messagesContainer = document.getElementById('messagesContainer');
        const heroScreen = document.getElementById('heroScreen');
        const chatInput = document.getElementById('chatInput');
        const btnSend = document.getElementById('btnSend');
        const messagesArea = document.getElementById('messagesArea');
        const compileModal = document.getElementById('compileModal');
        const compileModalBody = document.getElementById('compileModalBody');

        function setTheme(theme) {
            document.body.setAttribute('data-theme', theme);
            ['sepia', 'dark', 'light'].forEach(t => {
                const btn = document.getElementById('th_' + t);
                if (btn) btn.classList.toggle('active', t === theme);
            });
            localStorage.setItem('elantony_theme', theme);
        }

        function toggleFontFamily() {
            currentFont = currentFont === 'amiri' ? 'cairo' : 'amiri';
            const readerFont = currentFont === 'amiri' ? "'Amiri', serif" : "'Cairo', sans-serif";
            document.documentElement.style.setProperty('--font-reader', readerFont);
            const btn = document.getElementById('btnFontToggle');
            if (btn) btn.textContent = currentFont === 'amiri' ? '🔤 نسخ آبائي' : '🔤 كايرو حديث';
            localStorage.setItem('elantony_font', currentFont);
        }

        function adjustFontSize(delta) {
            currentFontSizeIndex = Math.max(0, Math.min(FONT_SIZES.length - 1, currentFontSizeIndex + delta));
            document.documentElement.style.setProperty('--font-size', FONT_SIZES[currentFontSizeIndex] + 'px');
            const label = document.getElementById('fontSizeLabel');
            if (label) label.textContent = FONT_LABELS[currentFontSizeIndex];
            localStorage.setItem('elantony_font_size_idx', currentFontSizeIndex);
        }

        function setDepthMode(mode) {
            currentDepthMode = mode;
            ['academic', 'pastoral', 'apologetic'].forEach(m => {
                const btn = document.getElementById('depth_' + m);
                if (btn) btn.classList.toggle('active', m === mode);
            });
        }

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
        }

        function handleKey(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        async function loadSessions() {
            try {
                const res = await fetch('/api/sessions?user_id=web');
                if (!res.ok) return;
                const data = await res.json();
                const list = document.getElementById('chatHistoryList');
                if (!list) return;
                list.innerHTML = '';
                const sessions = data.sessions || [];

                if (sessions.length === 0) {
                    await startNewChat();
                    return;
                }

                sessions.forEach(s => {
                    const item = document.createElement('div');
                    item.className = 'chat-history-item' + (s.id === currentSessionId ? ' active' : '');
                    item.id = 'sess_' + s.id;
                    
                    const textSpan = document.createElement('span');
                    textSpan.className = 'chat-item-text';
                    textSpan.textContent = '💬 ' + (s.title || 'بحث لاهوتي');
                    textSpan.title = s.title || 'بحث لاهوتي';
                    textSpan.onclick = () => selectSession(s.id);

                    const actionsDiv = document.createElement('div');
                    actionsDiv.className = 'chat-item-actions';

                    const docxBtn = document.createElement('button');
                    docxBtn.className = 'btn-sess-act';
                    docxBtn.title = 'تنزيل كملف Word (.docx)';
                    docxBtn.textContent = '📄';
                    docxBtn.onclick = (e) => downloadSessionDocx(e, s.id);

                    const delBtn = document.createElement('button');
                    delBtn.className = 'btn-sess-act btn-sess-del';
                    delBtn.title = 'حذف المناقشة';
                    delBtn.textContent = '✕';
                    delBtn.onclick = (e) => deleteSession(e, s.id);

                    actionsDiv.appendChild(docxBtn);
                    actionsDiv.appendChild(delBtn);

                    item.appendChild(textSpan);
                    item.appendChild(actionsDiv);
                    list.appendChild(item);
                });

                if (!currentSessionId && sessions.length > 0) {
                    await selectSession(sessions[0].id);
                }
            } catch (err) {
                console.error("Error loading sessions:", err);
            }
        }

        async function selectSession(sessionId) {
            currentSessionId = sessionId;
            document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
            const activeEl = document.getElementById('sess_' + sessionId);
            if (activeEl) activeEl.classList.add('active');

            try {
                const res = await fetch('/api/sessions/' + sessionId);
                if (!res.ok) return;
                const data = await res.json();
                const messages = data.messages || [];

                chatMessages = [];
                messagesContainer.innerHTML = '';

                if (messages.length === 0) {
                    messagesContainer.appendChild(heroScreen);
                    heroScreen.style.display = 'block';
                } else {
                    if (heroScreen) heroScreen.style.display = 'none';
                    let assistantTurn = 0;
                    messages.forEach(m => {
                        chatMessages.push({ role: m.role, content: m.content });
                        let turnNum = null;
                        if (m.role === 'assistant') {
                            assistantTurn++;
                            turnNum = assistantTurn;
                        }
                        appendMessageBubble(m.role, m.content, m.citations || [], turnNum);
                    });
                }
                scrollToBottom();
            } catch (err) {
                console.error("Error selecting session:", err);
            }
        }

        async function startNewChat() {
            try {
                const res = await fetch('/api/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: 'بحث لاهوتي جديد', user_id: 'web' })
                });
                if (res.ok) {
                    const data = await res.json();
                    currentSessionId = data.session_id;
                    chatMessages = [];
                    messagesContainer.innerHTML = '';
                    messagesContainer.appendChild(heroScreen);
                    heroScreen.style.display = 'block';
                    chatInput.value = '';
                    chatInput.focus();
                    await loadSessions();
                }
            } catch (err) {
                console.error("Error creating session:", err);
            }
        }

        async function deleteSession(e, sessionId) {
            e.stopPropagation();
            if (!confirm("هل تريد بالتأكيد حذف هذه المناقشة وسجلها بالكامل؟")) return;
            try {
                const res = await fetch('/api/sessions/' + sessionId, { method: 'DELETE' });
                if (res.ok) {
                    if (currentSessionId === sessionId) {
                        currentSessionId = null;
                    }
                    await loadSessions();
                }
            } catch (err) {
                console.error("Error deleting session:", err);
            }
        }

        function downloadSessionDocx(e, sessionId) {
            e.stopPropagation();
            window.open('/api/sessions/' + sessionId + '/export?format=docx', '_blank');
        }

        function sendPrompt(text) {
            chatInput.value = text;
            sendMessage();
        }

        async function sendMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            if (heroScreen) heroScreen.style.display = 'none';

            chatMessages.push({ role: 'user', content: text });
            appendMessageBubble('user', text);
            chatInput.value = '';
            chatInput.style.height = 'auto';
            btnSend.disabled = true;

            const loadingId = appendLoadingBubble();
            scrollToBottom();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: chatMessages,
                        session_id: currentSessionId,
                        user_id: 'web',
                        depth_mode: currentDepthMode
                    })
                });

                removeLoadingBubble(loadingId);

                if (!response.ok) {
                    throw new Error('فشل معالجة السؤال من محرك الذكاء الاصطناعي');
                }

                const data = await response.json();
                const aiResponse = data.response;
                const citations = data.citations || [];
                const turnNumber = data.turn_number || null;
                if (data.session_id) currentSessionId = data.session_id;

                chatMessages.push({ role: 'assistant', content: aiResponse });
                appendMessageBubble('assistant', aiResponse, citations, turnNumber);
                
                loadSessions();

            } catch (err) {
                removeLoadingBubble(loadingId);
                appendMessageBubble('assistant', '⚠️ حدث خطأ أثناء معالجة السؤال: ' + err.message);
            } finally {
                btnSend.disabled = false;
                scrollToBottom();
                chatInput.focus();
            }
        }

        function appendMessageBubble(role, content, citations = [], turnNumber = null) {
            const row = document.createElement('div');
            row.className = `msg-row ${role === 'user' ? 'user' : 'ai'}`;

            const avatar = document.createElement('div');
            avatar.className = `msg-avatar ${role === 'user' ? 'user' : 'ai'}`;
            avatar.textContent = role === 'user' ? '👤' : '✠';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'msg-content';

            if (role === 'assistant' && turnNumber && turnNumber > 1) {
                const badge = document.createElement('div');
                badge.className = 'turn-badge';
                badge.textContent = `💬 المحور رقم ${turnNumber} في هذه المناقشة`;
                contentDiv.appendChild(badge);
            }

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            if (role === 'assistant') {
                bubble.innerHTML = marked.parse(content);
            } else {
                bubble.textContent = content;
            }

            contentDiv.appendChild(bubble);

            if (citations && citations.length > 0) {
                const citeSection = document.createElement('div');
                citeSection.className = 'citations-section';

                const citeHeader = document.createElement('div');
                citeHeader.className = 'citations-header';
                citeHeader.innerHTML = `<span>📚 الشواهد والكتب الكنسية المعتمدة (${citations.length})</span> <span>▼</span>`;
                
                const citeList = document.createElement('div');
                citeList.className = 'citations-list';

                citations.forEach((c, idx) => {
                    const item = document.createElement('div');
                    item.className = 'citation-item';
                    const pLabel = c.printed_page ? `صـ ${c.printed_page} (مطبوعة)` : `صـ ${c.page_number} (PDF)`;
                    
                    let actionsHtml = '';
                    if (c.sha256) {
                        const safeTitle = encodeURIComponent(c.book_title || 'مرجع كنسي');
                        const safeExcerpt = encodeURIComponent(c.excerpt ? c.excerpt.slice(0, 200) : '');
                        const sizeBadge = c.file_size_formatted ? ` (${c.file_size_formatted})` : '';
                        actionsHtml = `
                            <div class="citation-actions">
                                <button onclick="openInstantPageModal('${c.sha256}', ${c.page_number}, '${safeTitle}', '${safeExcerpt}')" class="btn-cite-act btn-cite-fast" title="معاينة الصفحة وتصفح الكتاب مع هاي لايت وزوم فوراً">
                                    ⚡ معاينة وتظليل (صـ ${c.page_number})
                                </button>
                                <a href="/api/books/${c.sha256}/pages/${c.page_number}/view?highlight=${safeExcerpt}" target="_blank" class="btn-cite-act btn-cite-view" title="فتح صفحة المرجع كـ PDF مستقل مظلل (15-30 كيلوبايت)">
                                    📄 PDF الصفحة (15KB)
                                </a>
                                <a href="/api/books/${c.sha256}/view#page=${c.page_number}" target="_blank" class="btn-cite-act btn-cite-view" title="تصفح الكتاب كاملاً في نافذة المتصفح">
                                    📖 تصفح كامل
                                </a>
                                <a href="/api/books/${c.sha256}/download" target="_blank" class="btn-cite-act btn-cite-dl" title="تنزيل ملف الكتاب كاملاً على جهازك">
                                    💾 تنزيل الكتاب${sizeBadge}
                                </a>
                            </div>
                        `;
                    }

                    item.innerHTML = `
                        <div class="citation-top">
                            <span class="citation-title">📖 ${idx + 1}. ${c.book_title}</span>
                            <span class="citation-badge">مرتبة التوثيق ${c.authenticity_tier || 3}</span>
                        </div>
                        <div class="citation-meta">
                            ✍️ ${c.author || 'آباء الكنيسة'} | 📄 ${pLabel}
                        </div>
                        <div class="citation-excerpt">❝ ${c.excerpt} ❞</div>
                        ${actionsHtml}
                    `;
                    citeList.appendChild(item);
                });

                const extBox = document.createElement('div');
                extBox.className = 'external-sources-pill-box';
                extBox.innerHTML = `
                    <div class="ext-label">🌐 أمهات المراجع والآبائيات الكنسية الدولية المعتمدة:</div>
                    <div class="ext-chips-row">
                        <a href="https://www.ccel.org/fathers" target="_blank" class="ext-source-chip" title="موسوعة آباء الكنيسة قبل نيقية وما بعد نيقية (38 مجلداً - فيليب شاف)">📚 Nicene & Post-Nicene Fathers (CCEL)</a>
                        <a href="https://www.newadvent.org/fathers/" target="_blank" class="ext-source-chip" title="موسوعة New Advent الآبائية الشاملة باليونانية والإنجليزية">🏛️ New Advent Fathers</a>
                        <a href="https://patristica.net/migne/" target="_blank" class="ext-source-chip" title="باترولوجيا ميني اليونانية (161 مجلداً للآباء الشرقيين)">📜 Patrologia Graeca (Migne PG)</a>
                        <a href="https://katameros.bible/" target="_blank" class="ext-source-chip" title="القطمارس والسنكسار الكنسي الليتورجي المعتمد">⛪ قطمارس وسنكسار الكنيسة</a>
                        <a href="https://st-takla.org/books" target="_blank" class="ext-source-chip" title="مكتبة وتراث الكنيسة القبطية الأرثوذكسية">📖 تراث الكنيسة القبطية</a>
                    </div>
                `;
                citeSection.appendChild(citeHeader);
                citeSection.appendChild(citeList);
                citeSection.appendChild(extBox);
                contentDiv.appendChild(citeSection);
            }

            row.appendChild(avatar);
            row.appendChild(contentDiv);
            messagesContainer.appendChild(row);
            scrollToBottom();
        }

        function appendLoadingBubble() {
            const id = 'loading_' + Date.now();
            const row = document.createElement('div');
            row.className = 'msg-row ai';
            row.id = id;

            const avatar = document.createElement('div');
            avatar.className = 'msg-avatar ai';
            avatar.textContent = '✠';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'msg-content';

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.innerHTML = '<span style="font-size: 13.5px; color: var(--text-sub); margin-left: 10px;">جاري استحضار الشواهد والتحليل اللاهوتي...</span><div class="typing-dots"><span></span><span></span><span></span></div>';

            contentDiv.appendChild(bubble);
            row.appendChild(avatar);
            row.appendChild(contentDiv);
            messagesContainer.appendChild(row);
            return id;
        }

        function removeLoadingBubble(id) {
            const el = document.getElementById(id);
            if (el) el.remove();
        }

        function scrollToBottom() {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }

        async function openCompilationModal() {
            if (!currentSessionId) {
                alert("يرجى اختيار جلسة بحث أولاً لتجميعها.");
                return;
            }
            compileModal.classList.add('open');
            compileModalBody.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-sub);">جاري استخراج وتنسيق أطروحة البحث الكاملة...</div>';

            try {
                const res = await fetch('/api/sessions/' + currentSessionId + '/compile', { method: 'POST' });
                if (!res.ok) throw new Error("تعذر استرجاع الأطروحة");
                const data = await res.json();
                rawCompiledMarkdown = data.markdown;
                compileModalBody.innerHTML = marked.parse(rawCompiledMarkdown);
            } catch (err) {
                compileModalBody.innerHTML = '<div style="color: #EF4444; text-align: center; padding: 30px;">فشل تجميع البحث: ' + err.message + '</div>';
            }
        }

        function closeCompilationModal() {
            compileModal.classList.remove('open');
        }

        let activeRefSha = null;
        let activeRefPage = 1;
        let activeRefTotalPages = 1;
        let activeRefTitle = "";
        let activeRefExcerpt = "";
        let activeRefViewMode = "image"; // "image" or "pdf"
        let currentZoomIndex = 2; // [70, 85, 100, 120, 140, 175, 210, 260]
        const ZOOM_LEVELS = [70, 85, 100, 120, 140, 175, 210, 260];
        let highlightEnabled = true;

        async function openInstantPageModal(sha, pageNum, encodedTitle, encodedExcerpt) {
            activeRefSha = sha;
            activeRefPage = parseInt(pageNum, 10) || 1;
            activeRefTitle = decodeURIComponent(encodedTitle || "مرجع كنسي");
            activeRefExcerpt = decodeURIComponent(encodedExcerpt || "");
            activeRefTotalPages = 1;
            activeRefViewMode = "image";
            resetZoom();
            
            document.getElementById('refBookName').textContent = activeRefTitle;
            document.getElementById('refPageNum').textContent = activeRefPage;
            document.getElementById('refPageInput').value = activeRefPage;
            document.getElementById('refPageTotalSpan').style.display = 'none';
            document.getElementById('refSizeBadge').textContent = '';
            
            const excerptContent = document.getElementById('refExcerptContent');
            const excerptBtn = document.getElementById('btnToggleExcerpt');
            if (excerptContent && activeRefExcerpt) {
                excerptContent.textContent = activeRefExcerpt;
                if (excerptBtn) excerptBtn.style.display = 'inline-flex';
            } else if (excerptBtn) {
                excerptBtn.style.display = 'none';
            }
            
            setRefViewMode('image');
            
            const modal = document.getElementById('refModal');
            modal.classList.add('open');
            
            renderActiveRefPage();
            
            try {
                const res = await fetch(`/api/books/${sha}/info`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.page_count) {
                        activeRefTotalPages = data.page_count;
                        document.getElementById('refPageTotal').textContent = activeRefTotalPages;
                        document.getElementById('refPageTotalSpan').style.display = 'inline';
                        document.getElementById('refPageInput').max = activeRefTotalPages;
                    }
                    if (data.file_size_formatted) {
                        document.getElementById('refSizeBadge').textContent = '💾 ' + data.file_size_formatted;
                        document.getElementById('refFullBookBtn').textContent = '💾 تحميل الكتاب (' + data.file_size_formatted + ')';
                    }
                }
            } catch (e) {
                console.warn("Could not fetch book info:", e);
            }
        }

        function adjustZoom(delta) {
            currentZoomIndex = Math.max(0, Math.min(ZOOM_LEVELS.length - 1, currentZoomIndex + delta));
            const zoomVal = ZOOM_LEVELS[currentZoomIndex];
            const badge = document.getElementById('refZoomLevel');
            if (badge) badge.textContent = zoomVal + '%';
            const img = document.getElementById('refPageImg');
            if (img) {
                img.style.transform = `scale(${zoomVal / 100})`;
            }
        }

        function resetZoom() {
            currentZoomIndex = 2; // 100%
            const badge = document.getElementById('refZoomLevel');
            if (badge) badge.textContent = '100%';
            const img = document.getElementById('refPageImg');
            if (img) {
                img.style.transform = 'scale(1)';
            }
        }

        function toggleHighlight() {
            highlightEnabled = !highlightEnabled;
            const btn = document.getElementById('btnToggleHighlight');
            if (btn) {
                btn.classList.toggle('active', highlightEnabled);
                btn.textContent = highlightEnabled ? '🖍️ هاي لايت' : '🖍️ بدون تظليل';
            }
            renderActiveRefPage();
        }

        function toggleExcerptDrawer() {
            const box = document.getElementById('refExcerptBox');
            if (box) {
                box.style.display = (box.style.display === 'none' || !box.style.display) ? 'block' : 'none';
            }
        }

        function toggleFullscreen() {
            const card = document.querySelector('.ref-modal-card');
            if (card) {
                card.classList.toggle('fullscreen');
                const isFull = card.classList.contains('fullscreen');
                const btn = document.getElementById('btnToggleFullscreen');
                if (btn) btn.textContent = isFull ? '⛶ تصغير' : '⛶ ملء الشاشة';
            }
        }

        function setRefViewMode(mode) {
            activeRefViewMode = mode;
            const btnImg = document.getElementById('btnModeImg');
            const btnPdf = document.getElementById('btnModePdf');
            const imgContainer = document.getElementById('refImgContainer');
            const pdfContainer = document.getElementById('refPdfContainer');
            
            if (mode === 'image') {
                if (btnImg) btnImg.classList.add('active');
                if (btnPdf) btnPdf.classList.remove('active');
                if (imgContainer) imgContainer.style.display = 'block';
                if (pdfContainer) pdfContainer.style.display = 'none';
            } else {
                if (btnImg) btnImg.classList.remove('active');
                if (btnPdf) btnPdf.classList.add('active');
                if (imgContainer) imgContainer.style.display = 'none';
                if (pdfContainer) pdfContainer.style.display = 'block';
            }
            renderActiveRefPage();
        }

        function renderActiveRefPage() {
            if (!activeRefSha) return;
            
            document.getElementById('refPageNum').textContent = activeRefPage;
            document.getElementById('refPageInput').value = activeRefPage;
            
            const hlParam = (highlightEnabled && activeRefExcerpt) ? `&highlight=${encodeURIComponent(activeRefExcerpt)}` : '';
            const hlParamPdf = (highlightEnabled && activeRefExcerpt) ? `?highlight=${encodeURIComponent(activeRefExcerpt)}` : '';

            document.getElementById('refDirectPdfBtn').href = `/api/books/${activeRefSha}/pages/${activeRefPage}/view${hlParamPdf}`;
            document.getElementById('refViewFullBtn').href = `/api/books/${activeRefSha}/view#page=${activeRefPage}`;
            document.getElementById('refFullBookBtn').href = `/api/books/${activeRefSha}/download`;
            
            const loading = document.getElementById('refLoading');
            const img = document.getElementById('refPageImg');
            const iframe = document.getElementById('refPdfFrame');
            
            if (activeRefViewMode === 'image') {
                loading.style.display = 'block';
                loading.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div><div style="margin-top: 10px; font-weight: 700;">جاري استخراج وعرض صـ ' + activeRefPage + ' مع التظليل الذهبي...</div>';
                img.style.display = 'none';
                
                img.onload = () => {
                    loading.style.display = 'none';
                    img.style.display = 'block';
                };
                img.onerror = () => {
                    loading.innerHTML = '<div style="color: var(--accent); padding: 20px;">ℹ️ هذه الصفحة متوفرة كـ PDF خفيف أو النص مفهرس.<br><a href="/api/books/' + activeRefSha + '/pages/' + activeRefPage + '/view' + hlParamPdf + '" target="_blank" style="color:var(--gold); font-weight:bold; display:inline-block; margin-top:10px;">📄 انقر هنا لفتح صفحة الـ PDF مباشرة (15KB)</a></div>';
                };
                img.src = `/api/books/${activeRefSha}/pages/${activeRefPage}/image?t=` + Date.now() + hlParam;
            } else {
                loading.style.display = 'none';
                iframe.src = `/api/books/${activeRefSha}/pages/${activeRefPage}/view${hlParamPdf}`;
            }
        }

        function stepRefPage(delta) {
            if (!activeRefSha) return;
            let next = activeRefPage + delta;
            if (next < 1) next = 1;
            if (activeRefTotalPages > 1 && next > activeRefTotalPages) next = activeRefTotalPages;
            activeRefPage = next;
            renderActiveRefPage();
        }

        function goToRefPage() {
            const val = parseInt(document.getElementById('refPageInput').value, 10);
            if (!isNaN(val) && val >= 1) {
                if (activeRefTotalPages > 1 && val > activeRefTotalPages) {
                    activeRefPage = activeRefTotalPages;
                } else {
                    activeRefPage = val;
                }
                renderActiveRefPage();
            }
        }

        function handleRefPageKey(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                goToRefPage();
            }
        }

        function closeRefModal() {
            const modal = document.getElementById('refModal');
            if (modal) modal.classList.remove('open');
            const img = document.getElementById('refPageImg');
            if (img) img.src = '';
            const iframe = document.getElementById('refPdfFrame');
            if (iframe) iframe.src = '';
        }

        function copyCompilationText() {
            if (!rawCompiledMarkdown) return;
            navigator.clipboard.writeText(rawCompiledMarkdown).then(() => {
                alert("تم نسخ الأطروحة البحثية بالكامل إلى الحافظة!");
            });
        }

        function downloadCurrentExport(fmt) {
            if (!currentSessionId) {
                alert("يرجى اختيار محادثة بحثية أولاً للتصدير.");
                return;
            }
            window.open('/api/sessions/' + currentSessionId + '/export?format=' + fmt, '_blank');
        }

        window.onload = () => {
            // Restore saved theme
            const savedTheme = localStorage.getItem('elantony_theme') || 'sepia';
            setTheme(savedTheme);

            // Restore saved font
            const savedFont = localStorage.getItem('elantony_font') || 'amiri';
            if (savedFont !== 'amiri') {
                currentFont = 'cairo';
                document.documentElement.style.setProperty('--font-reader', "'Cairo', sans-serif");
                const btn = document.getElementById('btnFontToggle');
                if (btn) btn.textContent = '🔤 كايرو حديث';
            }

            // Restore saved font size
            const savedSizeIdx = localStorage.getItem('elantony_font_size_idx');
            if (savedSizeIdx !== null) {
                currentFontSizeIndex = parseInt(savedSizeIdx, 10);
                document.documentElement.style.setProperty('--font-size', FONT_SIZES[currentFontSizeIndex] + 'px');
                const label = document.getElementById('fontSizeLabel');
                if (label) label.textContent = FONT_LABELS[currentFontSizeIndex];
            }

            loadSessions();
            chatInput.focus();
        };
    </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def web_portal():
    """Serves the interactive ChatGPT-like Coptic Research Portal with full Bot features."""
    return HTMLResponse(content=WEB_PORTAL_HTML)


@app.get("/health")
async def health_check():
    """Health Check Endpoint."""
    try:
        stats = repo.get_library_stats()
        db_healthy = True
    except Exception as e:
        db_healthy = False
        stats = {"error": str(e)}

    status_code = 200 if db_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_healthy else "unhealthy",
            "app": settings.app_name,
            "environment": settings.app_env,
            "database_connected": db_healthy,
            "total_books": stats.get("total_books", 0),
            "indexed_chunks": stats.get("indexed_chunks", 0)
        }
    )


@app.get("/api/stats")
async def api_stats():
    """Aggregated library statistics."""
    return repo.get_library_stats()


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), limit: int = 10):
    """Fast FTS5 search across library chunks."""
    chunks = search_engine.search_fts5(q, limit=limit)
    return {
        "query": q,
        "count": len(chunks),
        "results": [c.model_dump() for c in chunks]
    }


@app.post("/api/ask")
async def api_ask(req: AskRequest):
    """Single-turn grounded RAG Q&A with depth support."""
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    chunks = search_engine.search_fts5(q, limit=req.limit or 4)
    ai_provider = get_ai_provider()
    depth_mode = req.depth_mode or "academic"
    answer = ai_provider.generate_answer(q, chunks, depth_mode=depth_mode)

    return {
        "question": q,
        "answer": answer,
        "sources": [
            {"reference": c.source_reference, "page": c.page_number, "title": c.book_title, "sha256": c.sha256}
            for c in chunks
        ]
    }


@app.get("/api/sessions")
async def list_sessions(user_id: str = "web", limit: int = 50):
    """Lists persistent discussion sessions for user."""
    sessions = repo.list_user_sessions(user_id=user_id, limit=limit)
    return {"sessions": sessions}


@app.post("/api/sessions")
async def create_new_session(req: Optional[CreateSessionRequest] = None):
    """Creates a new discussion thread."""
    title = req.title if req and req.title else "بحث لاهوتي جديد"
    user_id = req.user_id if req and req.user_id else "web"
    s_id = repo.create_session(user_id=user_id, title=title)
    return {"session_id": s_id, "title": title}


@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Retrieves session metadata and full message history."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="الجلسة غير موجودة")
    messages = repo.get_session_messages(session_id)
    return {"session": session, "messages": messages}


@app.delete("/api/sessions/{session_id}")
async def delete_discussion_session(session_id: str):
    """Deletes discussion session and all its messages."""
    ok = repo.delete_session(session_id)
    return {"success": ok}


@app.post("/api/sessions/{session_id}/compile")
async def compile_discussion_session(session_id: str):
    """Compiles the entire discussion session into a unified research monograph."""
    res = repo.compile_session(session_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@app.get("/api/sessions/{session_id}/export")
async def export_discussion_session(session_id: str, format: str = "markdown"):
    """
    Exports compiled research monograph as a downloadable file.
    Supports formats: 'docx' (Microsoft Word), 'markdown' (.md), or 'text' (.txt).
    """
    res = repo.compile_session(session_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])

    if format == "docx":
        from elantony.services.docx_exporter import generate_session_docx
        doc_dir = settings.base_dir / "data" / "compiled_researches"
        doc_dir.mkdir(parents=True, exist_ok=True)
        docx_path = doc_dir / f"research_{session_id}.docx"
        generate_session_docx(res, str(docx_path))
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''research_{session_id}.docx"}
        )

    content = res["markdown"] if format == "markdown" else res["plain_text"]
    filename = f"research_{session_id}.md" if format == "markdown" else f"research_{session_id}.txt"
    media_type = "text/markdown; charset=utf-8" if format == "markdown" else "text/plain; charset=utf-8"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


def apply_highlights_to_page(page, highlight_text: Optional[str] = None):
    """
    Finds and applies golden yellow highlight annotations to page for keywords in highlight_text.
    Supports Arabic, Coptic, and Greek terms safely without mutating original documents on disk.
    """
    if not highlight_text or not highlight_text.strip():
        return 0
    try:
        from elantony.search.search_engine import ARABIC_STOPWORDS
        import re
        raw_words = re.findall(r'[\w\u0621-\u064A\u0370-\u03FF\u2C80-\u2CFF]+', highlight_text)
        terms = [w for w in raw_words if len(w) >= 3 and w not in ARABIC_STOPWORDS][:12]
        
        highlighted_count = 0
        # Try phrase pairs first
        for i in range(len(terms) - 1):
            phrase = f"{terms[i]} {terms[i+1]}"
            rects = page.search_for(phrase)
            for r in rects:
                annot = page.add_highlight_annot(r)
                annot.set_colors(stroke=(1.0, 0.82, 0.15)) # Warm Patristic Gold
                annot.update()
                highlighted_count += 1
            if highlighted_count >= 12:
                break
                
        # If few phrase matches, highlight individual key theological terms
        if highlighted_count < 3:
            for t in terms:
                rects = page.search_for(t)
                for r in rects[:4]:
                    annot = page.add_highlight_annot(r)
                    annot.set_colors(stroke=(1.0, 0.84, 0.20)) # Gold Highlight
                    annot.update()
                    highlighted_count += 1
                if highlighted_count >= 16:
                    break
        return highlighted_count
    except Exception as e:
        logger.warning(f"Error applying highlights: {e}")
        return 0


@app.get("/api/books/{sha256}/pages/{page_number}/view")
async def get_book_single_page_pdf(sha256: str, page_number: int, highlight: Optional[str] = None):
    """
    Ultra-fast single-page PDF streaming (15-30 KB instead of 100 MB).
    Loads in ~0.1s directly on targeted page with optional golden text highlighting.
    """
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في المكتبة")
    file_path = book.get("original_path") or book.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ملف الكتاب غير متوفر على القرص")

    try:
        import fitz
        doc = fitz.open(file_path)
        page_idx = max(0, min(page_number - 1, len(doc) - 1))
        single_doc = fitz.open()
        single_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        if highlight:
            apply_highlights_to_page(single_doc[0], highlight)
        pdf_bytes = single_doc.tobytes()
        clean_name = os.path.splitext(os.path.basename(file_path))[0]
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=page_{page_number}.pdf; filename*=UTF-8''{urllib.parse.quote(clean_name)}_p{page_number}.pdf"}
        )
    except Exception as e:
        logger.error(f"Error extracting single page PDF for {sha256} p.{page_number}: {e}")
        return FileResponse(path=file_path, media_type="application/pdf")


@app.get("/api/books/{sha256}/pages/{page_number}/image")
async def get_book_page_image(sha256: str, page_number: int, highlight: Optional[str] = None):
    """
    Renders the exact book page as an ultra-fast, high-res JPG image (~18 KB).
    Renders in ~0.15s with golden yellow highlight annotations for extracted citations.
    """
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في المكتبة")
    file_path = book.get("original_path") or book.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ملف الكتاب غير متوفر على القرص")

    try:
        import fitz
        doc = fitz.open(file_path)
        page_idx = max(0, min(page_number - 1, len(doc) - 1))
        page = doc.load_page(page_idx)
        if highlight:
            apply_highlights_to_page(page, highlight)
        pix = page.get_pixmap(dpi=140)
        jpg_bytes = pix.tobytes("jpg")
        return Response(
            content=jpg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except Exception as e:
        logger.error(f"Error rendering page image for {sha256} p.{page_number}: {e}")
        raise HTTPException(status_code=500, detail="تعذر استخراج صورة الصفحة")


@app.get("/api/books/{sha256}/info")
async def get_book_info(sha256: str):
    """Returns book metadata including title, author, total pages, and file size."""
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في سجلات المكتبة")
    
    file_path = book.get("original_path") or book.get("file_path")
    file_size = book.get("file_size") or 0
    if not file_size and file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        
    size_mb = round(file_size / (1024 * 1024), 1) if file_size else 0
    size_str = f"{size_mb} MB" if size_mb >= 1 else (f"{round(file_size / 1024)} KB" if file_size else "")

    page_count = book.get("page_count") or 0
    if not page_count and file_path and os.path.exists(file_path):
        try:
            import fitz
            with fitz.open(file_path) as d:
                page_count = len(d)
        except Exception:
            page_count = 1

    return {
        "sha256": sha256,
        "title": book.get("file_name") or os.path.basename(file_path or "مرجع كنسي"),
        "author": book.get("author") or "آباء الكنيسة",
        "page_count": max(1, page_count),
        "file_size": file_size,
        "file_size_formatted": size_str,
        "authenticity_tier": book.get("authenticity_tier", 3)
    }


@app.get("/api/books/{sha256}/view")
async def view_book_file(sha256: str):
    """Streams full book PDF for in-browser viewing (inline)."""
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في سجلات المكتبة")

    file_path = book.get("original_path") or book.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ملف الكتاب غير متوفر على القرص المحلي")

    filename = os.path.basename(file_path)
    encoded_name = urllib.parse.quote(filename)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}"
        }
    )


@app.get("/api/books/{sha256}/download")
async def download_book_file(sha256: str):
    """Directly triggers native file download on the client device (attachment)."""
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في سجلات المكتبة")

    file_path = book.get("original_path") or book.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ملف الكتاب غير متوفر على القرص المحلي")

    filename = os.path.basename(file_path)
    encoded_name = urllib.parse.quote(filename)
    ascii_fallback = f"book_{sha256[:10]}.pdf"
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment",
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_name}',
            "Content-Length": str(os.path.getsize(file_path)),
            "Cache-Control": "public, max-age=3600"
        }
    )


@app.post("/api/audio/tts")
async def api_audio_tts(req: TTSRequest):
    """Generates MP3 audio for patristic quotes or liturgical prayers."""
    from elantony.services.audio_service import audio_service
    if not audio_service.is_available():
        raise HTTPException(status_code=503, detail="خدمة تحويل النصوص إلى صوت غير متوفرة حالياً")
    audio_bytes = audio_service.synthesize_speech(req.text, lang=req.lang or "ar", max_chars=req.max_chars or 1200)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="فشل توليد الصوت للنص المدخل")
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=patristic_quote.mp3"}
    )


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """
    Multi-turn Conversational AI Endpoint.
    Maintains dialogue history while anchoring answers strictly in library citations.
    Supports theological depth modes: 'academic', 'pastoral', 'apologetic'.
    Saves conversation to persistent database session.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="قائمة الرسائل فارغة")

    latest_msg = req.messages[-1].content.strip()
    if not latest_msg:
        raise HTTPException(status_code=400, detail="الاستفسار فارغ")

    user_id = req.user_id or "web"
    session_id = req.session_id
    if not session_id or session_id == "default":
        session_info = repo.get_or_create_active_session(user_id)
        session_id = session_info["id"]

    # 1. Retrieve library context
    chunks = search_engine.search_fts5(latest_msg, limit=6)
    ai_provider = get_ai_provider()
    depth_mode = req.depth_mode or "academic"

    # 2. Conversational reasoning with past dialogue turns
    raw_history = [{"role": m.role, "content": m.content} for m in req.messages]
    if hasattr(ai_provider, "generate_chat_response"):
        answer = ai_provider.generate_chat_response(raw_history, chunks, depth_mode=depth_mode)
    else:
        answer = ai_provider.generate_answer(latest_msg, chunks, depth_mode=depth_mode)

    # 3. Format citations with sha256 and metadata for live book viewer
    citations = []
    for c in chunks:
        book_info = repo.get_book_by_sha(c.sha256) if c.sha256 else None
        p_count = book_info.get("page_count") if book_info else 0
        f_size = book_info.get("file_size") if book_info else 0
        size_mb = round(f_size / (1024 * 1024), 1) if f_size else 0
        size_str = f"{size_mb} MB" if size_mb >= 1 else (f"{round(f_size / 1024)} KB" if f_size else "")

        citations.append({
            "book_title": c.book_title,
            "page_number": c.page_number,
            "printed_page": c.printed_page,
            "page_count": p_count or 1,
            "file_size_formatted": size_str,
            "source_reference": c.source_reference,
            "author": c.author,
            "source_types": c.source_types,
            "authenticity_tier": c.authenticity_tier,
            "relevance_score": c.relevance_score,
            "sha256": c.sha256,
            "excerpt": c.chunk_text[:300]
        })

    # Turn number in discussion
    turn_number = (len(raw_history) // 2) + 1

    # 4. Save to persistent discussion session
    try:
        repo.add_chat_message(session_id, "user", latest_msg)
        repo.add_chat_message(session_id, "assistant", answer, citations)

        # Update session title if default
        sess = repo.get_session(session_id)
        if sess and sess.get("title") in ["بحث لاهوتي جديد", "محادثة جديدة"]:
            clean_title = latest_msg.split("\n")[0][:45]
            repo.update_session_title(session_id, clean_title)
    except Exception as save_err:
        logger.warning(f"Error saving chat message to session {session_id}: {save_err}")

    return {
        "response": answer,
        "citations": citations,
        "session_id": session_id,
        "turn_number": turn_number
    }


@app.get("/api/v1/admin/dashboard")
async def admin_dashboard():
    """Returns administrative metrics and source distribution."""
    metrics = repo.get_admin_metrics()
    ai_provider = get_ai_provider()
    return {
        "status": "success",
        "library_metrics": metrics,
        "ai_engine": {
            "provider": ai_provider.provider_name,
            "available": ai_provider.is_available()
        },
        "system": {
            "app_env": settings.app_env,
            "rate_limit_per_minute": settings.rate_limit_per_minute
        }
    }


@app.post("/api/v1/admin/maintenance")
async def admin_run_maintenance():
    """Triggers WAL checkpoint, FTS5 index optimization, and PRAGMA optimize."""
    result = repo.run_maintenance()
    return result
