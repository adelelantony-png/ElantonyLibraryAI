# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Web & Cloud REST API
Provides conversational ChatGPT-like Research Portal, FTS5 Search,
Word (.docx) Export, Book Viewing, and Admin Management Endpoints.
"""

import os
import re
import json
import urllib.parse
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.database.repository import repo
from elantony.database.connection import get_connection
from elantony.search.search_engine import search_engine
from elantony.ai.factory import get_ai_provider
from elantony.telegram.bot_service import TelegramBotEngine
from elantony.core.text_cleaner import clean_citation_excerpt

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
    topic_mode: Optional[str] = "auto"


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
    topic_mode: Optional[str] = "continue"


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
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@400;600;700;800;900&family=Noto+Sans+Coptic:wght@400;700&family=Noto+Serif:ital,wght@0,400;0,700;1,400&family=Gentium+Plus:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        // Mouse Drag to Pan Zoomed Image
        window.addEventListener('DOMContentLoaded', () => {
            const container = document.getElementById('refImgScrollWrap');
            if (!container) return;
            let isDown = false;
            let startX, startY, scrollLeft, scrollTop;

            container.addEventListener('mousedown', (e) => {
                if (typeof currentZoomIndex !== 'undefined' && ZOOM_LEVELS[currentZoomIndex] <= 100) return;
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
        html, body {
            overflow-x: hidden !important;
            max-width: 100vw !important;
            width: 100% !important;
        }
        body {
            background: var(--bg-darker);
            color: var(--text-main);
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
            height: 100vh;
            display: flex;
            overflow: hidden;
            transition: background 0.25s ease, color 0.25s ease;
        }

        
        html, body {
            overflow-x: hidden !important;
            max-width: 100vw !important;
            width: 100vw !important;
            margin: 0 !important;
            padding: 0 !important;
            position: relative !important;
        }
        .main-container {
            flex: 1;
            min-width: 0 !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }
        .btn-top-preview {
            background: #7c2d12 !important;
            color: #ffffff !important;
            border: 1px solid #7c2d12 !important;
            font-weight: 800 !important;
            padding: 6px 14px !important;
            border-radius: 8px !important;
            font-size: 13px !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            box-shadow: 0 2px 6px rgba(124, 45, 18, 0.35) !important;
            transition: all 0.2s ease !important;
            white-space: nowrap !important;
            flex-shrink: 0 !important;
        }
        .btn-top-preview:hover {
            background: #991b1b !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 10px rgba(124, 45, 18, 0.45) !important;
        }
        .chat-tabs-bar {
            background: var(--bg-sidebar);
            border-bottom: 1px solid var(--card-border);
            padding: 6px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            min-width: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
            z-index: 5;
            box-sizing: border-box !important;
        }
        .chat-tabs-scroll {
            display: flex;
            align-items: center;
            gap: 6px;
            overflow: hidden !important;
            flex: 1;
            min-width: 0 !important;
            direction: rtl;
            justify-content: flex-start;
            flex-wrap: nowrap;
        }
        .chat-tab-chip {
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            color: var(--text-sub);
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
            max-width: 180px;
            min-width: 80px;
            flex-shrink: 1;
            transition: 0.18s ease;
            overflow: hidden;
        }
        .chat-tab-chip .tab-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
        }

        /* Sidebar */
        .sidebar {
            width: 290px;
            min-width: 290px;
            max-width: 290px;
            flex-shrink: 0;
            background: var(--bg-sidebar);
            border-left: 1px solid var(--card-border);
            display: flex;
            flex-direction: column;
            transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1), min-width 0.3s ease, margin 0.3s ease, opacity 0.25s ease;
            z-index: 20;
            overflow: hidden;
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
            direction: rtl;
            text-align: right;
            unicode-bidi: isolate;
        }
        .chat-item-text bdi, .tab-text bdi {
            unicode-bidi: isolate;
            direction: rtl;
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
            min-width: 0 !important;
            max-width: 100%;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
            overflow: hidden;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
        .citation-title { font-weight: 800; color: var(--accent); font-size: 14px; font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif; }
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .btn-cite-primary {
            background: linear-gradient(135deg, #B8860B 0%, #D4AF37 100%);
            border: 1px solid #B8860B;
            color: #FFFFFF !important;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(184, 134, 11, 0.25);
            padding: 6px 14px;
            font-size: 12.5px;
        }
        .btn-cite-primary:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(184, 134, 11, 0.35);
        }
        .btn-cite-fast { background: rgba(16, 185, 129, 0.16); border: 1px solid #10B981; color: #059669; font-weight: 800; cursor: pointer; }
        .btn-cite-fast:hover { background: #10B981; color: #FFF; transform: translateY(-1px); }
        .btn-cite-view { background: var(--accent-light); border: 1px solid var(--accent); color: var(--accent); }
        .btn-cite-view:hover { background: var(--accent); color: #FFF; }
        .btn-cite-dl { background: var(--card-hover); border: 1px solid var(--card-border); color: var(--text-main); }
        .btn-cite-dl:hover { background: var(--card-border); }

        /* Message Action Buttons Bar */
        .msg-actions-bar {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            align-items: center;
            flex-wrap: wrap;
            padding-top: 8px;
            border-top: 1px dashed var(--card-border);
        }
        .btn-msg-act {
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-sub);
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .btn-msg-act:hover {
            background: var(--card-hover);
            color: var(--accent);
            border-color: var(--accent);
        }

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
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            max-width: 820px;
            margin: 0 auto;
        }
        @media (max-width: 680px) {
            .prompt-cards {
                grid-template-columns: 1fr;
            }
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
        .modal-body h1, .modal-body h2, .modal-body h3 { color: var(--accent); margin: 16px 0 8px 0; font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif; }
        .modal-body strong { color: var(--gold); }
        .modal-body blockquote { border-right: 4px solid var(--quote-border); padding: 8px 14px; margin: 12px 0; background: var(--quote-bg); border-radius: 6px; }

        /* Nested Sub-questions Tree & Badges */
        .sess-count-badge {
            font-size: 10px;
            background: var(--accent-light);
            color: var(--accent);
            padding: 1px 7px;
            border-radius: 10px;
            font-weight: 700;
            white-space: nowrap;
            margin-right: 4px;
            flex-shrink: 0;
        }
        .sess-subq-tree {
            margin: 4px 6px 6px 14px;
            padding-right: 10px;
            border-right: 2px solid rgba(217, 119, 6, 0.3);
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .subq-tree-item {
            font-size: 11px;
            color: var(--text-sub);
            padding: 3px 6px;
            border-radius: 5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: 0.15s ease;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .subq-tree-item:hover {
            background: var(--card-hover);
            color: var(--accent);
        }
        .subq-num {
            font-weight: 800;
            color: var(--accent);
            flex-shrink: 0;
        }
        .subq-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Topic Sub-questions Pills Bar (Top of Chat) */
        .topic-subq-bar {
            background: var(--bg-card);
            border-bottom: 1px solid var(--card-border);
            padding: 6px 18px;
            display: flex;
            align-items: center;
            gap: 8px;
            overflow-x: auto;
            font-size: 11.5px;
            scrollbar-width: none;
            z-index: 4;
        }
        .topic-subq-bar::-webkit-scrollbar { display: none; }
        .subq-pill {
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 3px 10px;
            border-radius: 12px;
            cursor: pointer;
            white-space: nowrap;
            font-weight: 600;
            transition: 0.15s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .subq-pill:hover {
            border-color: var(--accent);
            color: var(--accent);
        }

        /* Dynamic Topic Tabs Bar */
        .chat-tabs-bar {
            background: var(--bg-sidebar);
            border-bottom: 1px solid var(--card-border);
            padding: 6px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            min-width: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
            z-index: 5;
            transition: background 0.25s ease;
        }
        .chat-tabs-scroll {
            display: flex;
            align-items: center;
            gap: 6px;
            overflow-x: auto;
            flex: 1;
            min-width: 0 !important;
            direction: rtl;
            justify-content: flex-start;
            scrollbar-width: none;
        }
        .chat-tabs-scroll::-webkit-scrollbar { display: none; }
        .chat-tab-chip {
            background: var(--bg-darker);
            border: 1px solid var(--card-border);
            color: var(--text-sub);
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            white-space: nowrap;
            max-width: 240px;
            transition: 0.18s ease;
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .chat-tab-chip:hover {
            background: var(--card-hover);
            color: var(--text-main);
        }
        .chat-tab-chip.active {
            background: var(--accent);
            color: #FFF;
            border-color: var(--accent);
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }
        .chat-tab-chip .tab-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .chat-tab-chip .tab-close-btn {
            background: none;
            border: none;
            color: inherit;
            opacity: 0.6;
            font-size: 13px;
            padding: 0 2px;
            cursor: pointer;
            line-height: 1;
            border-radius: 3px;
        }
        .chat-tab-chip .tab-close-btn:hover {
            opacity: 1;
            background: rgba(0,0,0,0.15);
        }
        .btn-new-tab {
            background: var(--accent-light);
            border: 1px dashed var(--accent);
            color: var(--accent);
            padding: 5px 11px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            white-space: nowrap;
            transition: 0.18s;
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .btn-new-tab:hover {
            background: var(--accent);
            color: #FFF;
            border-style: solid;
        }
        .topic-toast {
            position: fixed;
            top: 64px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: #FFF;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 12.5px;
            font-weight: 800;
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 8px;
            animation: fadeInDown 0.3s ease;
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        @keyframes fadeInDown {
            from { opacity: 0; transform: translate(-50%, -10px); }
            to { opacity: 1; transform: translate(-50%, 0); }
        }

        /* Loading Dots */
        .typing-dots { display: inline-flex; gap: 4px; padding: 6px 0; }
        .typing-dots span { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: blink 1.4s infinite; }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }

        
        /* Scholar Profile Pill */
        .scholar-profile-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--card-hover);
            border: 1px solid var(--card-border);
            padding: 4px 11px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
            color: var(--accent);
        }
        .scholar-profile-pill:hover {
            background: var(--accent-light);
            border-color: var(--accent);
        }
        .scholar-edit-icon { font-size: 11px; opacity: 0.7; }

        /* Admin Console Modal & Buttons */
        .btn-sidebar-admin {
            width: 100%;
            background: rgba(161, 98, 7, 0.12);
            border: 1px dashed var(--gold);
            color: var(--accent);
            padding: 7px 10px;
            border-radius: 8px;
            font-size: 11.5px;
            font-weight: 800;
            cursor: pointer;
            margin-top: 6px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: 0.2s;
            font-family: 'Cairo', sans-serif;
        }
        .btn-sidebar-admin:hover {
            background: var(--gold);
            color: #FFF;
        }
        .admin-modal-card {
            max-width: 960px !important;
            width: 92vw !important;
            max-height: 92vh !important;
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            background: var(--modal-bg);
            border: 1px solid var(--card-border);
            box-shadow: 0 25px 60px rgba(0,0,0,0.4);
        }
        .admin-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .admin-stat-card {
            background: var(--bg-sidebar);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .admin-stat-icon { font-size: 26px; }
        .admin-stat-val { font-size: 22px; font-weight: 900; color: var(--accent); }
        .admin-stat-lbl { font-size: 12px; color: var(--text-sub); }
        
        .admin-section-title {
            font-size: 15px;
            font-weight: 800;
            color: var(--accent);
            margin: 16px 0 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .scholar-card-item {
            background: var(--bg-chat);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 10px;
            transition: 0.2s;
        }
        .scholar-card-item:hover { border-color: var(--gold); }
        .scholar-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 8px;
        }
        .scholar-card-name { font-weight: 800; font-size: 14px; color: var(--accent); }
        .scholar-card-badge {
            background: var(--accent-light);
            color: var(--accent);
            border: 1px solid var(--card-border);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
        }
        .scholar-queries-list {
            margin-top: 8px;
            padding-right: 14px;
            border-right: 2px solid var(--card-border);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .scholar-query-row {
            font-size: 12.5px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .scholar-query-time { font-size: 11px; color: var(--text-sub); flex-shrink: 0; }

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
            flex-wrap: nowrap;
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
            display: inline-flex;
            align-items: center;
            gap: 4px;
            direction: ltr;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .btn-modal-close-ref:hover {
            background: #EF4444;
            color: #FFF;
            border-color: #EF4444;
        }
        .ref-modal-toolbar {
            padding: 8px 14px;
            border-bottom: 1px solid var(--card-border);
            background: var(--bg-darker);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            flex-wrap: nowrap;
            overflow-x: auto;
            scrollbar-width: thin;
        }
        .ref-modal-toolbar::-webkit-scrollbar {
            height: 4px;
        }
        .ref-modal-toolbar::-webkit-scrollbar-thumb {
            background: var(--card-border);
            border-radius: 4px;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
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

        
        /* Topic Flow Controller (Manual vs Auto Session Branching) */
        .topic-flow-toolbar {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 6px;
            margin-bottom: 8px;
            padding: 0 4px;
            flex-wrap: wrap;
        }
        .topic-flow-label {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-sub);
            margin-left: 4px;
        }
        .topic-mode-pill {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            color: var(--text-sub);
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.16s ease;
            font-family: inherit;
        }
        .topic-mode-pill:hover {
            border-color: var(--gold);
            color: var(--text-main);
        }
        .topic-mode-pill.active {
            background: var(--accent);
            border-color: var(--accent);
            color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
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
            font-family: 'Cairo', 'Noto Sans Coptic', 'Gentium Plus', 'Noto Serif', 'Segoe UI Historic', Arial, sans-serif;
        }
        .ext-source-chip:hover {
            background: var(--card-hover);
            border-color: var(--gold);
            color: var(--gold);
            transform: translateY(-1px);
        }

        .btn-toggle-sidebar {
            display: inline-flex !important;
            align-items: center;
            gap: 7px;
            padding: 6px 12px;
            background: var(--bg-card);
            border: 1px solid var(--accent);
            border-radius: 8px;
            color: var(--accent);
            font-weight: 700;
            font-size: 12.5px;
            cursor: pointer;
            transition: all 0.2s ease;
            flex-shrink: 0;
        }
        .btn-toggle-sidebar:hover {
            background: var(--accent);
            color: #fff;
        }
        /* Clean desktop collapse: width 0, zero residual sliver */
        body.sidebar-collapsed .sidebar {
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            opacity: 0 !important;
            pointer-events: none !important;
            visibility: hidden !important;
            overflow: hidden !important;
        }
        .mobile-sidebar-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.55);
            z-index: 998;
            backdrop-filter: blur(2px);
        }
        .mobile-sidebar-overlay.active {
            display: block;
        }

        @media (max-width: 992px) {
            .sidebar {
                position: fixed !important;
                right: 0 !important;
                top: 0 !important;
                bottom: 0 !important;
                width: 320px !important;
                min-width: 320px !important;
                max-width: 85vw !important;
                z-index: 1000 !important;
                box-shadow: -5px 0 25px rgba(0,0,0,0.4) !important;
                transform: translateX(100%) !important;
                display: flex !important;
                transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                margin: 0 !important;
            }
            .sidebar.mobile-open {
                transform: translateX(0) !important;
            }
            .top-navbar { flex-direction: column; align-items: stretch; gap: 8px; padding: 10px; }
            .controls-wrapper { justify-content: center; }
            .nav-actions { justify-content: center; }
        }
    
        /* Upload Modal Dropzone */
        .upload-dropzone {
            border: 2px dashed var(--accent);
            border-radius: 10px;
            padding: 30px 20px;
            text-align: center;
            background: rgba(217, 119, 6, 0.04);
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .upload-dropzone:hover, .upload-dropzone.dragover {
            background: rgba(217, 119, 6, 0.12);
            border-color: #f59e0b;
            transform: scale(1.01);
        }
        .sidebar-search-box {
            width: 100%;
            padding: 7px 10px;
            border-radius: 6px;
            border: 1px solid var(--card-border);
            background: var(--bg-darker);
            color: var(--text-main);
            font-size: 12px;
            font-family: inherit;
            outline: none;
            transition: border 0.2s;
        }
        .sidebar-search-box:focus { border-color: var(--accent); }
        .sess-count-badge {
            background: rgba(146, 64, 14, 0.12);
            color: var(--accent);
            font-size: 10px;
            padding: 1px 6px;
            border-radius: 10px;
            font-weight: 700;
            margin-right: 4px;
        }
        .sess-subq-tree {
            margin: 4px 10px 4px 4px;
            padding-right: 8px;
            border-right: 2px solid var(--gold);
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .subq-tree-item {
            font-size: 11px;
            color: var(--text-sub);
            padding: 3px 6px;
            border-radius: 4px;
            cursor: pointer;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: 0.15s;
        }
        .subq-tree-item:hover { background: var(--bg-darker); color: var(--accent); }
        .subq-num { font-weight: 700; color: var(--accent); font-size: 10px; }
        .btn-cite-fav {
            background: transparent;
            border: 1px solid rgba(202, 138, 4, 0.4);
            color: #ca8a04;
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 11px;
            cursor: pointer;
            font-family: inherit;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 3px;
            transition: 0.2s;
        }
        .btn-cite-fav:hover, .btn-cite-fav.active { background: #ca8a04; color: #FFF; }
        .btn-cite-split {
            background: rgba(59, 130, 246, 0.12);
            border-color: #3b82f6;
            color: #2563eb;
        }
        .btn-cite-split:hover { background: #2563eb; color: #FFF; }
        .turn-highlight-pulse { animation: pulseTurn 1.8s ease; }
        @keyframes pulseTurn {
            0% { box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.6); }
            70% { box-shadow: 0 0 0 12px rgba(217, 119, 6, 0); }
            100% { box-shadow: 0 0 0 0 rgba(217, 119, 6, 0); }
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
            <div style="display:flex; align-items:center; gap:8px;">
                <button onclick="loadSessions()" title="تحديث قائمة الأبحاث" style="background:none; border:none; cursor:pointer; font-size:15px; padding:2px;" class="btn-refresh-sessions">🔄</button>
                <a href="https://t.me/ElantonyLibrarybot" target="_blank" title="فتح البوت الرسمي على تليجرام" style="color: var(--accent); font-size: 18px; text-decoration: none;">
                    ✈️
                </a>
                <button onclick="closeMobileSidebar()" class="btn-mobile-close" title="إغلاق القائمة" style="display:none; background:none; border:none; font-size:18px; cursor:pointer; color:var(--text-sub); margin-right:4px;">✕</button>
            </div>
        </div>
        <!-- Scholar Profile / Isolation Space -->
        <div class="scholar-profile-card" style="margin: 0 16px 10px; padding: 8px 12px; background: var(--bg-darker); border: 1px solid var(--card-border); border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; cursor: pointer;" onclick="editScholarProfile()" title="انقر لتعديل اسمك أو صفتك البحثية">
                <span style="font-size: 16px;">👤</span>
                <div style="overflow: hidden;">
                    <div id="scholarNameDisplay" style="font-size: 12px; font-weight: 700; color: var(--text-main); white-space: nowrap; text-overflow: ellipsis;">باحث لاهوتي</div>
                    <div style="font-size: 10px; color: var(--text-sub);">ملف بحثي مستقل 🔒</div>
                </div>
            </div>
            <button class="btn-admin-icon" onclick="openAdminConsole()" title="لوحة إشراف المدير العام (Admin PIN: 2026)" style="background: none; border: none; font-size: 16px; cursor: pointer; opacity: 0.7; padding: 2px;">
                🛡️
            </button>
        </div>

        <div style="display:flex; flex-direction:column; gap:6px; margin: 0 16px 10px;">
            <button class="btn-new-chat" onclick="startNewChat()" style="margin:0;">
                <span>➕</span> بحث لاهوتي جديد
            </button>
            <button class="btn-ctrl" onclick="openUploadBookModal()" style="padding: 7px 12px; font-size: 12px; font-weight: 700; background: rgba(14, 165, 233, 0.1); border-color: #0284c7; color: #0284c7;">
                <span>📥</span> إضافة كتاب للمكتبة
            </button>
        </div>

        <div style="padding: 0 16px 6px;">
            <input type="text" id="sidebarSearchInput" placeholder="🔍 بحث في أبحاثك..." oninput="filterSidebarSessions(this.value)" class="sidebar-search-box">
        </div>

                <div style="display:flex; align-items:center; justify-content:space-between; padding: 6px 16px;">
            <div class="chat-history-title" style="padding:0;">📂 أبحاثك المحفوظة</div>
            <button class="btn-ctrl" id="btnSidebarMergeToggle" onclick="toggleSidebarMergeMode()" style="padding:3px 9px; font-size:11.5px; background:rgba(217,119,6,0.15); color:#d97706; border-color:#d97706; font-weight:800; display:inline-flex; align-items:center; gap:4px;" title="تحديد عدة أبحاث لدمجها في بحث واحد">
                <span>🗂️</span> دمج أبحاث
            </button>
        </div>

        <!-- Sticky Sidebar Merge Panel (يظهر عند تفعيل وضع الدمج) -->
        <div id="sidebarMergePanel" style="display:none; background:var(--bg-darker); border:1px solid var(--accent); border-radius:8px; padding:10px; margin: 0 14px 8px; box-shadow:var(--shadow-sm);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:12px; font-weight:800; color:var(--accent);">
                    ☑️ اختر أبحاثاً للدمج (<span id="sidebarMergeCount">0</span> محددة)
                </span>
                <button onclick="toggleSidebarMergeMode(false)" style="background:none; border:none; cursor:pointer; font-size:13px; color:var(--text-sub); padding:1px 4px;" title="إلغاء وضع الدمج">✕</button>
            </div>
            <div style="font-size:10.5px; color:var(--text-sub); margin-bottom:6px;">
                ضع علامة [✔] أمام الأبحاث المراد ضمها، واكتب عنواناً مجمعاً:
            </div>
            <input type="text" id="sidebarMergeTitleInput" placeholder="عنوان الأطروحة المجمعة (اختياري)..." style="width:100%; box-sizing:border-box; padding:6px 8px; font-size:11.5px; border:1px solid var(--card-border); border-radius:5px; margin-bottom:8px; background:var(--bg-chat); color:var(--text-main); font-family:inherit;">
            <label style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-main); margin-bottom:8px; cursor:pointer; user-select:none;">
                <input type="checkbox" id="sidebarMergeDeleteSources" checked style="width:15px; height:15px; cursor:pointer;">
                <span>🗑️ مسح الأبحاث القديمة بعد الدمج (تنظيف السجل)</span>
            </label>
            <button id="btnExecuteSidebarMerge" onclick="executeSidebarMerge()" class="btn-ctrl" style="width:100%; background:#7c2d12; color:#fff; border-color:#7c2d12; font-weight:800; padding:7px; font-size:12px; cursor:pointer; justify-content:center;">
                📑 دمج الأبحاث المحددة
            </button>
        </div>
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
        <div class="mobile-sidebar-overlay" id="mobileOverlay" onclick="closeMobileSidebar()"></div>
        <div class="top-navbar">
            <div style="display:flex; align-items:center; gap:10px;">
                <button class="btn-toggle-sidebar" id="btnToggleSidebar" onclick="toggleSidebar()" title="إظهار / إخفاء قائمة الأبحاث">
                    📂 سجل الأبحاث
                </button>
                <div class="nav-title">
                    <span>✠</span> المساعد والباحث اللاهوتي الذكي
                </div>
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
                <button class="btn-top-preview" onclick="previewCurrentMonograph()" title="معاينة وطباعة الأطروحة بنمط النشر الأكاديمي وبجودة A4 الفائقة (Ctrl + P)">
                    <span>🖨️</span> معاينة وطباعة الأطروحة (A4)
                </button>
                <button class="btn-nav btn-reset-nav" onclick="clearBotMemory()" title="تفريغ ذاكرة البوت ومسح سياق الأسئلة السابقة تماماً للبدء بصفحة بيضاء" style="background: rgba(239, 68, 68, 0.14); border-color: #ef4444; color: #dc2626; font-weight: 800;">
                    <span>🧹</span> سؤال جديد (تفريغ)
                </button>
                <button class="btn-nav btn-docx-nav" onclick="downloadCurrentExport('docx')" title="تنزيل أطروحة البحث كاملة كملف Microsoft Word منسق">
                    <span>📄</span> Word
                </button>
                <button class="btn-nav btn-fav-nav" onclick="openScholarNotebookModal()" title="كشكول الباحث ومفضلة الشواهد وتدوين الهوامش" style="background: rgba(234, 179, 8, 0.15); border-color: #ca8a04; color: #a16207; font-weight: 700;">
                    <span>⭐</span> الكشكول (<span id="notebookBadge">0</span>)
                </button>
                <button class="btn-nav btn-share-nav" onclick="openShareModal()" title="مشاركة رابط هذا البحث والمراجع مع أي شخص لفتحه وتصفحه" style="background: rgba(16, 185, 129, 0.14); border-color: #10b981; color: #047857; font-weight: 700;">
                    <span>🔗</span> مشاركة
                </button>
                <button class="btn-nav btn-upload-nav" onclick="openUploadBookModal()" title="رفع وإضافة كتاب جديد للمكتبة مع فهرسته فورياً" style="background: rgba(14, 165, 233, 0.14); border-color: #0284c7; color: #0369a1; font-weight: 700;">
                    <span>📥</span> إضافة كتاب
                </button>
                <button class="btn-nav btn-admin-nav" onclick="openAdminConsole()" title="لوحة إشراف المدير العام ومتابعة أبحاث كل المستخدمين (PIN: 2026)" style="background: rgba(217, 119, 6, 0.12); border-color: #d97706; color: #d97706; font-weight: 800;">
                    <span>🛡️</span> الإشراف
                </button>
            </div>
        </div>

        <!-- Dynamic Topic Tabs Bar (تبويبات الموضوعات الذكية التلقائية) -->
        <div class="chat-tabs-bar" id="chatTabsBar">
            <div class="chat-tabs-scroll" id="chatTabsList">
                <!-- Dynamically populated from active sessions -->
            </div>
            <button class="btn-new-tab" onclick="startNewChat()" title="فتح موضوع لاهوتي جديد مستقل في تبويب جديد">
                <span>➕</span> موضوع جديد
            </button>
        </div>

        <!-- Topic Sub-questions Breadcrumb Navigator (فهرس الأسئلة المتسلسلة داخل نفس الموضوع) -->
        <div class="topic-subq-bar" id="topicSubqBar" style="display: none;">
            <!-- Dynamically populated from active discussion questions -->
        </div>

        <!-- Prominent Monograph Action Header (دائماً ظاهر وواضح للمعاينة والطباعة) -->
        <div class="active-session-header" id="activeSessionHeader" style="display:flex; align-items:center; justify-content:space-between; padding:8px 16px; background:var(--bg-card); border-bottom:1px solid var(--card-border); gap:10px; flex-wrap:wrap; z-index:4;">
            <div style="display:flex; align-items:center; gap:8px; overflow:hidden;">
                <span style="font-size:16px;">📖</span>
                <span id="currentSessionTitleDisplay" style="font-weight:800; font-size:14px; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:320px;">بحث لاهوتي</span>
                <button class="btn-ctrl" onclick="renameSession(event, currentSessionId, document.getElementById('currentSessionTitleDisplay').textContent)" style="padding:2px 8px; font-size:11px;" title="تعديل عنوان البحث">✏️ تعديل العنوان</button>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <button class="btn-ctrl" onclick="previewCurrentMonograph()" style="background:#7c2d12; color:#fff; border-color:#7c2d12; font-weight:800; padding:6px 14px; font-size:12.5px; box-shadow:0 2px 5px rgba(124,45,18,0.25);" title="معاينة وطباعة الأطروحة بنمط النشر A4 المعتمد">
                    🖨️ معاينة وطباعة الأطروحة
                </button>
                <button class="btn-ctrl" onclick="downloadCurrentSessionDocx()" style="background:rgba(2,132,199,0.12); color:#0284c7; border-color:#0284c7; font-weight:700; padding:6px 12px; font-size:12px;" title="تنزيل البحث كملف Word">
                    📄 ملف Word
                </button>
                <button class="btn-ctrl" onclick="startNewChat()" style="background:rgba(239,68,68,0.1); color:#dc2626; border-color:#ef4444; font-weight:700; padding:6px 12px; font-size:12px;" title="تفريغ الذاكرة وبدء بحث جديد">
                    🧹 تفريغ الذاكرة
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
            <div class="topic-flow-toolbar">
                <span class="topic-flow-label">مسار الحوار:</span>
                <button type="button" class="topic-mode-pill active" id="btnModeContinue" onclick="setTopicMode('continue')" title="إدراج هذا السؤال كسؤال متسلسل في نفس موضوع وبحث التبويب الحالي (افتراضي)">🔗 استكمال في نفس المبحث</button>
                <button type="button" class="topic-mode-pill" id="btnModeNew" onclick="setTopicMode('new')" title="فتح تبويب ومبحث مستقل وجديد كلياً في القائمة الجانبية">➕ فتح بحث مستقل جديد</button>
                <button type="button" class="topic-mode-pill" id="btnModeAuto" onclick="setTopicMode('auto')" title="تصنيف ذكي: استكمال نفس المبحث إذا كان متصلاً أو فتح موضوع جديد إذا اختلف">⚡ ذكي تلقائي</button>
                <button type="button" class="topic-mode-pill" onclick="clearBotMemory()" title="تفريغ ذاكرة البوت ومسح سياق الأسئلة السابقة للبدء بصفحة بيضاء" style="background:rgba(239, 68, 68, 0.12); border-color:#ef4444; color:#dc2626; font-weight:700; margin-right:auto;">🧹 تفريغ الذاكرة</button>
            </div>
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
                <div style="display:flex; flex-direction:column; gap:8px;">
                    <div class="modal-title">
                        <span>✠</span> أطروحة البحث اللاهوتية المجمعة
                    </div>
                    <!-- Mode switch tabs -->
                    <div style="display:flex; gap:8px;">
                        <button id="btnTabCompileCurrent" class="btn-ctrl active" onclick="switchCompileTab('current')" style="padding:5px 12px; font-weight:700;">
                            📑 تجميع أسئلة البحث الحالي
                        </button>
                        <button id="btnTabCompileMerge" class="btn-ctrl" onclick="switchCompileTab('merge')" style="padding:5px 12px; font-weight:700; background:rgba(217,119,6,0.12); color:#d97706; border-color:#d97706;">
                            🗂️ دمج عدة أبحاث سابقة في بحث واحد
                        </button>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn-modal-act btn-modal-docx" onclick="downloadCurrentExport('docx')">📄 مستند Word (.docx)</button>
                    <button class="btn-modal-act" onclick="copyCompilationText()">📋 نسخ النص</button>
                    <button class="btn-modal-act" onclick="previewCurrentMonograph()">🖨️ معاينة وطباعة</button>
                    <button class="btn-modal-close" onclick="closeCompilationModal()">✕</button>
                </div>
            </div>
            <div class="modal-body" id="compileModalBody">
                <div style="text-align: center; padding: 40px; color: var(--text-sub);">جاري تجميع البحث وتوثيق المراجع...</div>
            </div>
            <!-- Merge Previous Sessions Container -->
            <div class="modal-body" id="mergeModalBody" style="display:none; padding:18px;">
                <div style="margin-bottom:14px; font-size:13.5px; color:var(--text-sub);">
                    اختر موضوعين أو أكثر من أبحاثك السابقة لدمجها تلقائياً في <strong>أطروحة لاهوتية موحدة</strong> مع فهرس شامل وقائمة مراجع مدمجة:
                </div>
                <div id="mergeSessionsList" style="max-height:280px; overflow-y:auto; border:1px solid var(--card-border); border-radius:8px; padding:10px; background:var(--bg-darker); margin-bottom:14px;">
                    <!-- Dynamically populated checkboxes -->
                </div>
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <input type="text" id="mergeNewTitleInput" placeholder="عنوان الأطروحة المجمعة الجديدة (اختياري)..." style="flex:1; min-width:240px; padding:8px 12px; border:1px solid var(--card-border); border-radius:6px; font-family:inherit; background:var(--bg-chat); color:var(--text-main);">
                    <label style="display:inline-flex; align-items:center; gap:6px; font-size:11.5px; color:var(--text-main); cursor:pointer;">
                        <input type="checkbox" id="modalMergeDeleteSources" checked style="width:15px; height:15px; cursor:pointer;">
                        <span>🗑️ مسح الأبحاث الأصلية بعد الدمج</span>
                    </label>
                    <button onclick="executeMergeSelectedSessions()" class="btn-ctrl" style="background:#7c2d12; color:#fff; border-color:#7c2d12; font-weight:800; padding:8px 18px; cursor:pointer;" id="btnExecuteMerge">
                        📑 دمج وتجميع الأبحاث المحددة
                    </button>
                </div>
            </div>
        </div>
    </div>

    
    <!-- Admin Scholar Telemetry & Activity Console Modal -->
    <div class="modal-overlay" id="adminConsoleModal">
        <div class="modal-card admin-modal-card">
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">🔐</span>
                    <span class="ref-book-name" style="color:var(--accent);">لوحة الإشراف المركزي ومتابعة الباحثين (Admin Console)</span>
                    <span class="ref-badge-page">مشرف النظام</span>
                </div>
                <button class="btn-modal-close-ref" onclick="closeAdminConsole()">✕ إغلاق</button>
            </div>
            <div class="modal-body" style="padding: 20px; overflow-y: auto; background: var(--bg-chat);">
                <!-- Metrics Summary Cards -->
                <div class="admin-stats-grid">
                    <div class="admin-stat-card">
                        <span class="admin-stat-icon">👥</span>
                        <div>
                            <div class="admin-stat-val" id="adminTotalScholars">--</div>
                            <div class="admin-stat-lbl">إجمالي الباحثين النشطين</div>
                        </div>
                    </div>
                    <div class="admin-stat-card">
                        <span class="admin-stat-icon">💬</span>
                        <div>
                            <div class="admin-stat-val" id="adminTotalQueries">--</div>
                            <div class="admin-stat-lbl">إجمالي الأسئلة اللاهوتية</div>
                        </div>
                    </div>
                    <div class="admin-stat-card">
                        <span class="admin-stat-icon">📚</span>
                        <div>
                            <div class="admin-stat-val">7,200+</div>
                            <div class="admin-stat-lbl">الكتب والآبائيات المفهرسة</div>
                        </div>
                    </div>
                </div>

                <!-- Tabs: Per Scholar vs Live Stream -->
                <div style="display:flex; gap:8px; margin-bottom:15px; border-bottom:1px solid var(--card-border); padding-bottom:8px;">
                    <button id="btnAdminTabScholars" class="btn-ref-tool active" onclick="switchAdminSubTab('scholars')">👥 ملفات الباحثين وما بحثوا عنه</button>
                    <button id="btnAdminTabStream" class="btn-ref-tool" onclick="switchAdminSubTab('stream')">⚡ البث الحي لجميع الأسئلة</button>
                    <button class="btn-ref-tool" onclick="refreshAdminData()" style="margin-right:auto;">🔄 تحديث فوري</button>
                </div>

                <!-- Scholars List Container -->
                <div id="adminScholarsContainer">
                    <div style="text-align:center; padding:30px; color:var(--text-sub);">جاري استدعاء سجل نشاط الباحثين...</div>
                </div>

                <!-- Live Stream Container -->
                <div id="adminStreamContainer" style="display:none;"></div>
            </div>
        </div>
    </div>


    <!-- Instant Reference Viewer Modal (فتح واستعراض المراجع في أجزاء من الثانية) -->
    <div class="modal-overlay" id="refModal">
        <div class="modal-card ref-modal-card">
            <!-- Modal Header Row 1: Title, Page Badge and Window Controls -->
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">📖</span>
                    <span id="refBookName" class="ref-book-name" title="اسم المرجع">اسم المرجع</span>
                    <span class="ref-badge-page"><span style="direction:rtl; font-weight:700;">صـ</span><span id="refPageNum" style="font-weight:800;">1</span><span id="refPageTotalSpan" style="display: none;"> / <span id="refPageTotal">--</span></span></span>
                    <span id="refSizeBadge" class="ref-badge-size"></span>
                </div>
                <div style="display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0;">
                    <button id="btnToggleFullscreen" class="btn-ref-tool" onclick="toggleFullscreen()" title="تكبير النافذة لملء الشاشة">⛶ ملء الشاشة</button>
                    <button class="btn-modal-close-ref" onclick="closeRefModal()" title="إغلاق النافذة">✕ إغلاق</button>
                </div>
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

                <!-- View Mode Toggle (Image vs Single PDF vs Full Book) -->
                <div class="ref-mode-wrap">
                    <button class="btn-ref-mode active" id="btnModeImg" onclick="setRefViewMode('image')" title="عرض صورة الصفحة الأصلية في أجزاء من الثانية مع التظليل والزوم">🖼️ صورة سريعة</button>
                    <button class="btn-ref-mode" id="btnModePdf" onclick="setRefViewMode('pdf')" title="عرض صفحة الـ PDF المدمجة المستقلة والمظللة">📑 PDF الصفحة</button>
                    <button class="btn-ref-mode" id="btnModeFull" onclick="setRefViewMode('full')" title="تصفح الكتاب كاملاً وقراءته تفاعلياً داخل هذه النافذة دون تنزيل">📖 تصفح الكتاب كاملاً</button>
                </div>

                <!-- Book Direct Actions -->
                <div class="ref-actions-group">
                    <a id="refDirectPdfBtn" href="#" target="_blank" class="btn-ref-action" title="فتح صفحة المرجع كملف PDF مستقل (15-30 كيلوبايت)">📄 PDF الصفحة</a>
                    <a id="refViewFullBtn" href="#" target="_blank" class="btn-ref-action" title="فتح الكتاب كاملاً في لسان جديد مستقل بالمتصفح">↗ نافذة مستقلة</a>
                    <a id="refFullBookBtn" href="#" class="btn-ref-action btn-ref-download" title="تحميل ملف الكتاب كاملاً مباشرة على جهازك">💾 تنزيل الكتاب</a>
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
        // Scholar Identity & User Isolation
        // Scholar Identity & Unified Multi-Device Persistence
        let currentUserId = localStorage.getItem('elantony_user_id') || 'scholar_master';
        let currentUserName = localStorage.getItem('elantony_user_name') || 'باحث لاهوتي';
        localStorage.setItem('elantony_user_id', currentUserId);
        localStorage.setItem('elantony_user_name', currentUserName);
        try {
            document.cookie = "elantony_user_id=" + encodeURIComponent(currentUserId) + "; path=/; max-age=315360000; SameSite=Lax";
        } catch(e) {}

        let adminPinCache = sessionStorage.getItem('elantony_admin_pin') || '';

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

                function escapeHtml(text) {
            if (!text) return '';
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
        }

        function toggleSidebar() {
            if (window.innerWidth <= 992) {
                const sidebar = document.querySelector('.sidebar');
                const overlay = document.getElementById('mobileOverlay');
                if (sidebar) sidebar.classList.toggle('mobile-open');
                if (overlay) overlay.classList.toggle('active');
            } else {
                document.body.classList.toggle('sidebar-collapsed');
                const isCollapsed = document.body.classList.contains('sidebar-collapsed');
                localStorage.setItem('elantony_sidebar_collapsed', isCollapsed ? '1' : '0');
            }
        }

        function toggleMobileSidebar() { toggleSidebar(); }

        function closeMobileSidebar() {
            if (window.innerWidth <= 992) {
                const sidebar = document.querySelector('.sidebar');
                const overlay = document.getElementById('mobileOverlay');
                if (sidebar) sidebar.classList.remove('mobile-open');
                if (overlay) overlay.classList.remove('active');
            }
        }

        
        let isSidebarMergeMode = false;

        function toggleSidebarMergeMode(forceState) {
            isSidebarMergeMode = forceState !== undefined ? forceState : !isSidebarMergeMode;
            const panel = document.getElementById('sidebarMergePanel');
            const toggleBtn = document.getElementById('btnSidebarMergeToggle');
            if (panel) panel.style.display = isSidebarMergeMode ? 'block' : 'none';
            if (toggleBtn) {
                toggleBtn.style.background = isSidebarMergeMode ? 'var(--accent)' : 'rgba(217,119,6,0.15)';
                toggleBtn.style.color = isSidebarMergeMode ? '#FFF' : '#d97706';
            }
            loadSessions();
        }

        function updateSidebarMergeCount() {
            const checked = document.querySelectorAll('.sidebar-merge-chk:checked');
            const cntSpan = document.getElementById('sidebarMergeCount');
            if (cntSpan) cntSpan.textContent = checked.length;
        }

        async function executeSidebarMerge() {
            const checked = Array.from(document.querySelectorAll('.sidebar-merge-chk:checked')).map(el => el.value);
            if (checked.length < 2) {
                alert("يرجى اختيار بحثين على الأقل بوضع علامة [✔] في المربعات لدمجهما معاً في أطروحة واحدة.");
                return;
            }

            const titleInput = document.getElementById('sidebarMergeTitleInput');
            const customTitle = titleInput ? titleInput.value.trim() : '';
            const delSourcesChk = document.getElementById('sidebarMergeDeleteSources');
            const deleteSources = delSourcesChk ? delSourcesChk.checked : true;
            const btn = document.getElementById('btnExecuteSidebarMerge');
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳ جاري الدمج والتوثيق...';
            }

            try {
                const res = await fetch('/api/sessions/merge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_ids: checked,
                        title: customTitle || null,
                        delete_sources: deleteSources
                    })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "فشل دمج الأبحاث");
                }

                const data = await res.json();
                toggleSidebarMergeMode(false);
                showTopicToast("✨ تم دمج " + data.merged_sessions_count + " أبحاث بنجاح في أطروحة واحدة: «" + data.title + "»");

                await loadSessions();
                await selectSession(data.session_id);
            } catch(err) {
                alert("تعذر دمج الأبحاث: " + err.message);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '📑 دمج الأبحاث المحددة';
                }
            }
        }

        async function renameSession(e, sessionId, currentTitle) {
            if (e) e.stopPropagation();
            const safeCurrent = currentTitle || 'بحث لاهوتي';
            const newTitle = prompt("أدخل اسماً أو عنواناً مخصصاً لهذا البحث اللاهوتي:", safeCurrent);
            if (newTitle && newTitle.trim() && newTitle.trim() !== safeCurrent) {
                try {
                    const res = await fetch('/api/sessions/' + sessionId + '/title', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle.trim() })
                    });
                    if (res.ok) {
                        showTopicToast("✨ تم تعديل عنوان البحث إلى: «" + newTitle.trim() + "»");
                        await loadSessions();
                    }
                } catch(err) {
                    console.error("Error renaming session:", err);
                }
            }
        }

        async function loadSessions() {
            try {
                // 1. Check if a shared session is requested via URL (?session=... or ?share=...)
                const urlParams = new URLSearchParams(window.location.search);
                const sharedSessId = urlParams.get('session') || urlParams.get('share');
                const sharedTurn = urlParams.get('turn');

                if (sharedSessId && (!currentSessionId || currentSessionId !== sharedSessId)) {
                    await selectSession(sharedSessId);
                    if (sharedTurn) {
                        setTimeout(() => jumpToQuestion(parseInt(sharedTurn, 10)), 700);
                    }
                }

                // 2. Fetch the user's personal session history
                const res = await fetch('/api/sessions?all=true&user_id=' + encodeURIComponent(currentUserId));
                if (!res.ok) return;
                const data = await res.json();
                const list = document.getElementById('chatHistoryList');
                if (!list) return;
                list.innerHTML = '';
                const sessions = data.sessions || [];

                if (sessions.length === 0 && !sharedSessId && !currentSessionId) {
                    await startNewChat();
                    return;
                }

                sessions.forEach(s => {
                    const item = document.createElement('div');
                    item.className = 'chat-history-item' + (s.id === currentSessionId ? ' active' : '');
                    item.id = 'sess_' + s.id;
                    
                    // Main Session Header Row
                    const headerRow = document.createElement('div');
                    headerRow.style.display = 'flex';
                    headerRow.style.alignItems = 'center';
                    headerRow.style.justifyContent = 'space-between';
                    headerRow.style.width = '100%';

                    const textSpan = document.createElement('span');
                    textSpan.className = 'chat-item-text';
                    const safeSessTitle = escapeHtml(s.title || 'بحث لاهوتي');
                    const qCount = s.questions_count || 1;
                    const isTg = s.user_id && /^\d+$/.test(s.user_id);
                    const originBadge = isTg ? '<span class="sess-origin-badge" style="background:rgba(0,136,204,0.18);color:#0088cc;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;margin-left:4px;">📱 تليجرام</span>' : '';
                    const countBadge = `<span class="sess-count-badge">${qCount} ${qCount > 1 ? 'أسئلة' : 'سؤال'}</span>`;
                    textSpan.innerHTML = `<span style="flex-shrink:0;">💬</span> <bdi dir="auto">${safeSessTitle}</bdi> ${originBadge} ${countBadge}`;
                    textSpan.title = s.title || 'بحث لاهوتي';
                    textSpan.onclick = () => selectSession(s.id);

                    const actionsDiv = document.createElement('div');
                    actionsDiv.className = 'chat-item-actions';

                    const renameBtn = document.createElement('button');
                    renameBtn.className = 'btn-sess-act';
                    renameBtn.title = 'تعديل وتسمية هذا البحث';
                    renameBtn.textContent = '✏️';
                    renameBtn.onclick = (e) => renameSession(e, s.id, s.title);

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

                    actionsDiv.appendChild(renameBtn);
                    actionsDiv.appendChild(docxBtn);
                    actionsDiv.appendChild(delBtn);

                    headerRow.appendChild(textSpan);
                    headerRow.appendChild(actionsDiv);
                    item.appendChild(headerRow);

                    // If merge mode is active, prepend checkbox
                    if (isSidebarMergeMode) {
                        const chk = document.createElement('input');
                        chk.type = 'checkbox';
                        chk.className = 'sidebar-merge-chk';
                        chk.value = s.id;
                        chk.style.width = '16px';
                        chk.style.height = '16px';
                        chk.style.cursor = 'pointer';
                        chk.style.marginLeft = '8px';
                        chk.style.flexShrink = '0';
                        chk.onclick = (e) => {
                            e.stopPropagation();
                            updateSidebarMergeCount();
                        };
                        headerRow.prepend(chk);
                    }

                    list.appendChild(item);
                });

                // Populate Dynamic Tabs Bar (clean tabs: show active session + sessions with actual research questions)
                const tabsList = document.getElementById('chatTabsList');
                if (tabsList) {
                    tabsList.innerHTML = '';
                    const meaningfulSessions = sessions.filter(s => s.id === currentSessionId || (s.questions_count && s.questions_count > 0) || (s.title && s.title !== 'بحث لاهوتي جديد'));
                    const tabsToRender = (meaningfulSessions.length > 0 ? meaningfulSessions : sessions).slice(0, 4);
                    tabsToRender.forEach(s => {
                        const tab = document.createElement('div');
                        tab.className = 'chat-tab-chip' + (s.id === currentSessionId ? ' active' : '');
                        tab.id = 'tab_' + s.id;
                        tab.onclick = () => selectSession(s.id);
                        tab.title = s.title || 'بحث لاهوتي';

                        const icon = document.createElement('span');
                        icon.className = 'tab-icon';
                        icon.textContent = '💬';

                        const text = document.createElement('span');
                        text.className = 'tab-text';
                        text.innerHTML = '<bdi dir="auto">' + escapeHtml(s.title || 'بحث لاهوتي') + '</bdi>';

                        const tabEditBtn = document.createElement('button');
                        tabEditBtn.className = 'tab-close-btn';
                        tabEditBtn.style.color = 'var(--accent)';
                        tabEditBtn.style.fontSize = '11px';
                        tabEditBtn.style.marginRight = '2px';
                        tabEditBtn.textContent = '✏️';
                        tabEditBtn.title = 'تعديل اسم هذا البحث';
                        tabEditBtn.onclick = (e) => renameSession(e, s.id, s.title);

                        const closeBtn = document.createElement('button');
                        closeBtn.className = 'tab-close-btn';
                        closeBtn.textContent = '✕';
                        closeBtn.title = 'حذف هذا الموضوع';
                        closeBtn.onclick = (e) => deleteSession(e, s.id);

                        text.ondblclick = (e) => renameSession(e, s.id, s.title);

                        tab.appendChild(icon);
                        tab.appendChild(text);
                        tab.appendChild(tabEditBtn);
                        tab.appendChild(closeBtn);
                        tabsList.appendChild(tab);
                    });
                }

                if (!currentSessionId && sessions.length > 0) {
                    await selectSession(sessions[0].id);
                }
            } catch (err) {
                console.error("Error loading sessions:", err);
            }
        }

        async function selectSession(sessionId) {
            closeMobileSidebar();
            currentSessionId = sessionId;
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, '', window.location.pathname + '?session=' + encodeURIComponent(sessionId));
            }
            document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.chat-tab-chip').forEach(el => el.classList.remove('active'));
            const activeEl = document.getElementById('sess_' + sessionId);
            if (activeEl) activeEl.classList.add('active');
            const activeTab = document.getElementById('tab_' + sessionId);
            if (activeTab) {
                activeTab.classList.add('active');
            }
            // Strict window lock: zero horizontal offset
            window.scrollTo({ left: 0, behavior: 'instant' });
            document.documentElement.scrollLeft = 0;
            document.body.scrollLeft = 0;

            try {
                const res = await fetch('/api/sessions/' + sessionId);
                if (!res.ok) {
                    showTopicToast("⚠️ تعذر العثور على جلسة البحث المطلوبة");
                    return;
                }
                const data = await res.json();
                const sessionInfo = data.session || { id: sessionId, title: 'بحث تمت مشاركته' };
                const titleDisp = document.getElementById('currentSessionTitleDisplay');
                if (titleDisp) titleDisp.textContent = sessionInfo.title || 'بحث لاهوتي';
                const messages = data.messages || [];

                // If not in tabs bar, add dynamic tab for this shared session!
                if (!document.getElementById('tab_' + sessionId)) {
                    const tabsList = document.getElementById('chatTabsList');
                    if (tabsList) {
                        const tab = document.createElement('div');
                        tab.className = 'chat-tab-chip active';
                        tab.id = 'tab_' + sessionId;
                        tab.innerHTML = `<span class="tab-icon">🔗</span><span class="tab-text"><bdi dir="auto">${escapeHtml(sessionInfo.title || 'بحث تمت مشاركته')}</bdi></span>`;
                        tab.onclick = () => selectSession(sessionId);
                        tabsList.prepend(tab);
                    }
                }

                chatMessages = [];
                messagesContainer.innerHTML = '';

                userMsgCounter = 0;
                if (messages.length === 0) {
                    messagesContainer.appendChild(heroScreen);
                    heroScreen.style.display = 'block';
                    const subqBar = document.getElementById('topicSubqBar');
                    if (subqBar) subqBar.style.display = 'none';
                } else {
                    if (heroScreen) heroScreen.style.display = 'none';
                    let assistantTurn = 0;
                    const userQueries = [];
                    messages.forEach(m => {
                        chatMessages.push({ role: m.role, content: m.content });
                        let turnNum = null;
                        if (m.role === 'assistant') {
                            assistantTurn++;
                            turnNum = assistantTurn;
                        } else if (m.role === 'user') {
                            userQueries.push(m.content);
                        }
                        appendMessageBubble(m.role, m.content, m.citations || [], turnNum);
                    });

                    // Render Sub-questions Navigation Bar at top of chat
                    const subqBar = document.getElementById('topicSubqBar');
                    if (subqBar) {
                        if (userQueries.length > 1) {
                            subqBar.style.display = 'flex';
                            subqBar.innerHTML = `<span style="font-weight:700; color:var(--accent); flex-shrink:0;">📍 أسئلة هذا المبحث (${userQueries.length}):</span>`;
                            userQueries.forEach((qText, qIdx) => {
                                const pill = document.createElement('div');
                                pill.className = 'subq-pill';
                                pill.title = qText;
                                pill.innerHTML = `<span>س${qIdx+1}:</span> <span>${escapeHtml(qText.substring(0, 32))}${qText.length > 32 ? '...' : ''}</span>`;
                                pill.onclick = () => jumpToQuestion(qIdx + 1);
                                subqBar.appendChild(pill);
                            });
                        } else {
                            subqBar.style.display = 'none';
                        }
                    }
                }
                scrollToBottom();
            } catch (err) {
                console.error("Error selecting session:", err);
            }
        }

        
        function showTopicToast(message) {
            let toast = document.getElementById('topicToast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'topicToast';
                toast.className = 'topic-toast';
                document.body.appendChild(toast);
            }
            toast.textContent = message;
            toast.style.display = 'flex';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 4000);
        }

        
        function updateTopicSubqBar() {
            const subqBar = document.getElementById('topicSubqBar');
            if (!subqBar) return;
            const userQueries = [];
            chatMessages.forEach(m => {
                if (m.role === 'user') userQueries.push(m.content);
            });
            if (userQueries.length > 1) {
                subqBar.style.display = 'flex';
                subqBar.innerHTML = `<span style="font-weight:700; color:var(--accent); flex-shrink:0;">📍 أسئلة هذا المبحث (${userQueries.length}):</span>`;
                userQueries.forEach((qText, qIdx) => {
                    const pill = document.createElement('div');
                    pill.className = 'subq-pill';
                    pill.title = qText;
                    pill.innerHTML = `<span>س${qIdx+1}:</span> <span>${escapeHtml(qText.substring(0, 32))}${qText.length > 32 ? '...' : ''}</span>`;
                    pill.onclick = () => jumpToQuestion(qIdx + 1);
                    subqBar.appendChild(pill);
                });
            } else {
                subqBar.style.display = 'none';
            }
        }

        function jumpToQuestion(qIndex) {
            const el = document.getElementById('user_msg_' + qIndex);
            if (el) {
                const area = document.getElementById('messagesArea');
                if (area) {
                    area.scrollTo({ top: el.offsetTop - 20, behavior: 'smooth' });
                }
                el.style.transition = 'box-shadow 0.3s ease';
                el.style.boxShadow = '0 0 0 3px var(--accent)';
                setTimeout(() => { el.style.boxShadow = 'none'; }, 2000);
            }
        }

        async function selectSessionAndJump(sessionId, qIndex) {
            if (currentSessionId !== sessionId) {
                await selectSession(sessionId);
            }
            setTimeout(() => {
                jumpToQuestion(qIndex);
            }, 150);
        }

        
        async function clearBotMemory() {
            if (chatMessages && chatMessages.length > 0) {
                if (!confirm("هل تريد بالتأكيد تفريغ ذاكرة البوت ومسح أي أسئلة وسياقات سابقة للبدء بصفحة بيضاء تماماً؟")) {
                    return;
                }
            }
            await startNewChat();
            showTopicToast("✨ تم تفريغ ذاكرة البوت بنجاح! الذاكرة الآن نقية ومستعدة لسؤالك الجديد.");
        }

        function downloadCurrentSessionDocx() {
            if (!currentSessionId) {
                alert("يرجى اختيار جلسة بحث أولاً لتنزيل ملف Word.");
                return;
            }
            window.open('/api/sessions/' + currentSessionId + '/export?format=docx', '_blank');
        }

        function previewCurrentMonograph() {
            if (!currentSessionId) {
                alert("يرجى اختيار جلسة بحث أولاً للمعاينة والطباعة.");
                return;
            }
            window.open('/api/sessions/' + currentSessionId + '/preview', '_blank');
        }
async function startNewChat() {
            // Lazy start: Clear the screen without polluting the database with empty sessions!
            currentSessionId = null;
            chatMessages = [];
            messagesContainer.innerHTML = '';
            if (heroScreen) {
                heroScreen.style.display = 'block';
                messagesContainer.appendChild(heroScreen);
            }
            const titleDisp = document.getElementById('currentSessionTitleDisplay');
            if (titleDisp) titleDisp.textContent = 'بحث لاهوتي جديد';
            chatInput.value = '';
            chatInput.focus();
            document.querySelectorAll('.chat-history-item').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.chat-tab-chip').forEach(el => el.classList.remove('active'));
            showTopicToast("✨ تم تفريغ الشاشة.. اكتب سؤالك وسيبدأ التوثيق فوراً دون جلسات فارغة.");
        }

        async function deleteSession(e, sessionId) {
            e.stopPropagation();
            if (!confirm("هل تريد بالتأكيد حذف هذه المناقشة وسجلها بالكامل؟")) return;
            try {
                const res = await fetch('/api/sessions/' + sessionId, { method: 'DELETE' });
                if (res.ok) {
                    if (currentSessionId === sessionId) {
                        currentSessionId = null;
                        chatMessages = [];
                        messagesContainer.innerHTML = '';
                        if (heroScreen) {
                            messagesContainer.appendChild(heroScreen);
                            heroScreen.style.display = 'block';
                        }
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

                let currentTopicMode = 'continue';

        function setTopicMode(mode) {
            currentTopicMode = mode;
            ['btnModeAuto', 'btnModeContinue', 'btnModeNew'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.remove('active');
            });
            if (mode === 'auto') {
                const el = document.getElementById('btnModeAuto');
                if (el) el.classList.add('active');
            } else if (mode === 'continue') {
                const el = document.getElementById('btnModeContinue');
                if (el) el.classList.add('active');
            } else if (mode === 'new') {
                const el = document.getElementById('btnModeNew');
                if (el) el.classList.add('active');
            }
        }

        function sendPrompt(text) {
            chatInput.value = text;
            sendMessage();
        }

        
        function retryLastQuestion() {
            if (chatMessages && chatMessages.length > 0) {
                const lastUserIdx = chatMessages.findLastIndex ? chatMessages.findLastIndex(m => m.role === 'user') : -1;
                if (lastUserIdx !== -1) {
                    const lastText = chatMessages[lastUserIdx].content;
                    const input = document.getElementById('chatInput');
                    if (input) input.value = lastText;
                    // remove last assistant error row
                    const rows = document.querySelectorAll('.msg-row');
                    if (rows.length > 0) rows[rows.length - 1].remove();
                    sendMessage();
                }
            }
        }

        async function sendMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            const lower = text.toLowerCase();
            if (['/reset', '/clear', '/new', 'تصفير', 'تصفير الذاكرة', 'مسح الذاكرة', 'مسح', 'reset', 'clear', 'ابدأ من جديد'].includes(lower)) {
                chatInput.value = '';
                await startNewChat();
                showTopicToast("✨ تم تصفير الذاكرة وبدء جلسة جديدة بنجاح!");
                return;
            }

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
                        user_id: currentUserId,
                        depth_mode: currentDepthMode,
                        topic_mode: currentTopicMode
                    })
                });

                removeLoadingBubble(loadingId);

                if (!response.ok) {
                    let errDetail = 'فشل معالجة السؤال من محرك الذكاء الاصطناعي';
                    try {
                        const errJson = await response.json();
                        if (errJson && errJson.detail) errDetail = errJson.detail;
                    } catch (_) {}
                    throw new Error(errDetail);
                }

                const data = await response.json();
                const aiResponse = data.response;
                const citations = data.citations || [];
                const turnNumber = data.turn_number || null;
                const isNewTopic = data.is_new_topic || false;

                if (isNewTopic && data.session_id !== currentSessionId) {
                    currentSessionId = data.session_id;
                    showTopicToast("✨ تم فتح تبويب وموضوع جديد تلقائياً: «" + (data.topic_title || "موضوع جديد") + "»");
                    chatMessages = [{ role: 'user', content: text }, { role: 'assistant', content: aiResponse }];
                    messagesContainer.innerHTML = '';
                    appendMessageBubble('user', text);
                    appendMessageBubble('assistant', aiResponse, citations, 1);
                    await loadSessions();
                } else {
                    if (data.session_id) currentSessionId = data.session_id;
                    chatMessages.push({ role: 'assistant', content: aiResponse });
                    appendMessageBubble('assistant', aiResponse, citations, turnNumber);
                    await loadSessions();
                }

            } catch (err) {
                removeLoadingBubble(loadingId);
                if (chatMessages.length > 0 && chatMessages[chatMessages.length - 1].role === 'user') {
                    chatMessages.pop();
                }
                appendMessageBubble('assistant', '⚠️ حدث خطأ أثناء معالجة السؤال: ' + err.message + ' <button onclick="retryLastQuestion()" style="margin-right:10px; padding:3px 10px; border-radius:6px; cursor:pointer; background:var(--gold-church); color:#fff; border:none;">🔄 إعادة المحاولة</button>');
            } finally {
                btnSend.disabled = false;
                scrollToBottom();
                chatInput.focus();
            }
        }

        
        function resolveCitationAuthor(c) {
            let a = (c.author || '').trim();
            if (a && a !== 'غير محدد' && a !== 'غير معروف' && a !== 'مجهول') return a;
            let t = (c.book_title || '').replace(/\.pdf$/i, '').trim();
            for (const sep of [' - ', ' – ', ' — ', ' _ ']) {
                if (t.includes(sep)) {
                    const parts = t.split(sep).map(p => p.trim()).filter(Boolean);
                    if (parts.length >= 2 && parts[parts.length - 1].length >= 3 && isNaN(parts[parts.length - 1])) {
                        return parts[parts.length - 1];
                    }
                }
            }
            return 'آباء ومعلمو الكنيسة';
        }

        let userMsgCounter = 0;
        function appendMessageBubble(role, content, citations = [], turnNumber = null) {
            const row = document.createElement('div');
            row.className = `msg-row ${role === 'user' ? 'user' : 'ai'}`;
            if (role === 'user') {
                userMsgCounter++;
                row.id = 'user_msg_' + userMsgCounter;
            }

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
                        const resolvedAuthor = resolveCitationAuthor(c);
                        actionsHtml = `
                            <div class="citation-actions" style="flex-wrap: wrap; gap: 8px;">
                                <button onclick="openInstantPageModal('${c.sha256}', ${c.page_number}, '${safeTitle}', '${safeExcerpt}')" class="btn-cite-act btn-cite-primary" title="قراءة وتصفح الكتاب مباشرة في القارئ السريع مع التظليل الذهبي">
                                    📖 قراءة وتصفح الكتاب (صـ ${c.page_number})
                                </button>
                                <button onclick="openSynopticSplitView('${c.sha256}', ${c.page_number}, '${safeTitle}', '${safeExcerpt}')" class="btn-cite-act btn-cite-split" title="مقارنة متزامنة مع شاهد آخر جنباً إلى جنب">
                                    ⚖️ مقارنة متزامنة
                                </button>
                                <a href="/api/books/${c.sha256}/pages/${c.page_number}/view?highlight=${safeExcerpt}" target="_blank" class="btn-cite-act btn-cite-view" title="فتح صفحة المرجع كـ PDF مستقل مظلل (15KB)">
                                    📄 PDF الصفحة (15KB)
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
                            <div style="display:flex; align-items:center; gap:6px;">
                                <button class="btn-cite-fav" onclick='toggleSaveCitation(${JSON.stringify(c).replace(/'/g, "&#39;")})' title="إضافة الشاهد إلى كشكول الباحث والمفضلة">⭐ حفظ</button>
                                <span class="citation-badge">${c.authenticity_tier === 1 ? "نص كتابي مقدس" : (c.authenticity_tier === 2 ? "شاهد آبائي أصيل" : "دراسة لاهوتية معتمدة")}</span>
                            </div>
                        </div>
                        <div class="citation-meta">
                            ✍️ ${resolveCitationAuthor(c)} | 📄 ${pLabel}
                        </div>
                        <div class="citation-excerpt">❝ ${c.excerpt} ❞</div>
                        ${actionsHtml}
                    `;
                    citeList.appendChild(item);
                });

                citeSection.appendChild(citeHeader);
                citeSection.appendChild(citeList);
                contentDiv.appendChild(citeSection);
            }

            if (role === 'assistant') {
                const turnActions = document.createElement('div');
                turnActions.className = 'msg-actions-bar';
                turnActions.innerHTML = `
                    <button class="btn-msg-act" onclick="previewCurrentMonograph()" style="color:#7c2d12; font-weight:800; border:1px solid #7c2d12; background:rgba(124,45,18,0.08);" title="معاينة وطباعة الأطروحة بنمط النشر A4">
                        <span>🖨️</span> معاينة وطباعة الأطروحة
                    </button>
                    <button class="btn-msg-act" onclick="copyTurnMarkdown(this)" title="نسخ نص هذا المبحث كاملاً">
                        <span>📋</span> نسخ النص
                    </button>
                    <button class="btn-msg-act" onclick="exportSingleTurnDocx(${turnNumber || 1})" title="تصدير هذا المبحث تحديداً كملف Word مستقل">
                        <span>📄</span> تصدير Word للمبحث
                    </button>
                    <button class="btn-msg-act" onclick="exportSingleTurnPdf(${turnNumber || 1})" title="تصدير هذا المبحث تحديداً كملف PDF عالي الجودة">
                        <span>📕</span> تصدير PDF للمبحث
                    </button>
                    <button class="btn-msg-act" onclick="openCompilationModal()" title="تجميع هذا البحث مع سائر المحاور في أطروحة كاملة وتصديرها">
                        <span>📑</span> تجميع الأطروحة
                    </button>
                    <button class="btn-msg-act" onclick="openShareModal(${turnNumber || 'null'})" title="مشاركة رابط هذا المبحث والمراجع للتحقق منها">
                        <span>🔗</span> مشاركة
                    </button>
                `;
                contentDiv.appendChild(turnActions);
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

        
        let currentCompileTab = 'current';

        async function switchCompileTab(tabName) {
            currentCompileTab = tabName;
            const btnCurrent = document.getElementById('btnTabCompileCurrent');
            const btnMerge = document.getElementById('btnTabCompileMerge');
            const bodyCompile = document.getElementById('compileModalBody');
            const bodyMerge = document.getElementById('mergeModalBody');

            if (tabName === 'current') {
                btnCurrent.classList.add('active');
                btnCurrent.style.background = 'var(--accent)';
                btnCurrent.style.color = '#FFF';
                btnMerge.classList.remove('active');
                btnMerge.style.background = 'rgba(217,119,6,0.12)';
                btnMerge.style.color = '#d97706';
                bodyCompile.style.display = 'block';
                bodyMerge.style.display = 'none';
            } else {
                btnMerge.classList.add('active');
                btnMerge.style.background = 'var(--accent)';
                btnMerge.style.color = '#FFF';
                btnCurrent.classList.remove('active');
                btnCurrent.style.background = 'none';
                btnCurrent.style.color = 'var(--text-sub)';
                bodyCompile.style.display = 'none';
                bodyMerge.style.display = 'block';
                await loadMergeSessionsList();
            }
        }

        async function loadMergeSessionsList() {
            const container = document.getElementById('mergeSessionsList');
            if (!container) return;
            container.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-sub);">جاري استرجاع قائمة الأبحاث السابقة...</div>';

            try {
                const res = await fetch('/api/sessions?all=true');
                if (!res.ok) throw new Error("تعذر جلب الأبحاث");
                const data = await res.json();
                const sessions = data.sessions || [];

                if (sessions.length === 0) {
                    container.innerHTML = '<div style="text-align:center; padding:20px;">لا توجد أبحاث سابقة مسجلة للدمج.</div>';
                    return;
                }

                container.innerHTML = '';
                sessions.forEach(s => {
                    const row = document.createElement('label');
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.style.gap = '10px';
                    row.style.padding = '8px 10px';
                    row.style.cursor = 'pointer';
                    row.style.borderBottom = '1px solid var(--card-border)';
                    row.style.borderRadius = '6px';
                    row.style.transition = 'background 0.15s ease';
                    row.onmouseover = () => row.style.background = 'var(--card-hover)';
                    row.onmouseout = () => row.style.background = 'transparent';

                    const isCurrent = s.id === currentSessionId;
                    row.innerHTML = `
                        <input type="checkbox" class="merge-checkbox" value="${s.id}" ${isCurrent ? 'checked' : ''} style="width:16px; height:16px; cursor:pointer;">
                        <span style="font-weight:700; color:var(--text-main); flex:1;">${escapeHtml(s.title || 'بحث لاهوتي')}</span>
                        <span style="font-size:11px; color:var(--text-sub);">${s.questions_count || s.message_count || 0} أسئلة/محاور</span>
                    `;
                    container.appendChild(row);
                });
            } catch(err) {
                container.innerHTML = '<div style="color:#ef4444; padding:15px; text-align:center;">فشل جلب الأبحاث: ' + err.message + '</div>';
            }
        }

        async function executeMergeSelectedSessions() {
            const checked = Array.from(document.querySelectorAll('.merge-checkbox:checked')).map(el => el.value);
            if (checked.length < 2) {
                alert("يرجى اختيار بحثين على الأقل لدمجهما في أطروحة واحدة.");
                return;
            }

            const customTitle = document.getElementById('mergeNewTitleInput').value.trim();
            const modalDelChk = document.getElementById('modalMergeDeleteSources');
            const deleteSources = modalDelChk ? modalDelChk.checked : true;
            const btn = document.getElementById('btnExecuteMerge');
            btn.disabled = true;
            btn.textContent = '⏳ جاري الدمج والتوثيق...';

            try {
                const res = await fetch('/api/sessions/merge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_ids: checked,
                        title: customTitle || null,
                        delete_sources: deleteSources
                    })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "فشل دمج الأبحاث");
                }

                const data = await res.json();
                closeCompilationModal();
                showTopicToast("✨ تم دمج " + data.merged_sessions_count + " أبحاث بنجاح في أطروحة واحدة: «" + data.title + "»");

                // Select the new merged session
                await loadSessions();
                await selectSession(data.session_id);
            } catch(err) {
                alert("تعذر دمج الأبحاث: " + err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '📑 دمج وتجميع الأبحاث المحددة';
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
            const btnFull = document.getElementById('btnModeFull');
            const imgContainer = document.getElementById('refImgContainer');
            const pdfContainer = document.getElementById('refPdfContainer');
            
            if (btnImg) btnImg.classList.toggle('active', mode === 'image');
            if (btnPdf) btnPdf.classList.toggle('active', mode === 'pdf');
            if (btnFull) btnFull.classList.toggle('active', mode === 'full');

            if (mode === 'image') {
                if (imgContainer) imgContainer.style.display = 'block';
                if (pdfContainer) pdfContainer.style.display = 'none';
            } else {
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
            } else if (activeRefViewMode === 'pdf') {
                loading.style.display = 'none';
                iframe.src = `/api/books/${activeRefSha}/pages/${activeRefPage}/view${hlParamPdf}`;
            } else if (activeRefViewMode === 'full') {
                loading.style.display = 'none';
                iframe.src = `/api/books/${activeRefSha}/view#page=${activeRefPage}`;
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

        function openShareModal(turnNumber = null) {
            if (!currentSessionId) {
                alert("يرجى اختيار أو بدء بحث أولاً لمشاركته.");
                return;
            }
            const activeTab = document.getElementById('tab_' + currentSessionId);
            const title = activeTab ? activeTab.querySelector('.tab-text').textContent.trim() : 'بحث لاهوتي موثق';
            
            let url = window.location.origin + '/?session=' + encodeURIComponent(currentSessionId);
            if (turnNumber) {
                url += '&turn=' + turnNumber;
            }
            
            const titleEl = document.getElementById('shareModalSubject');
            if (titleEl) titleEl.textContent = title;

            const input = document.getElementById('shareUrlInput');
            if (input) input.value = url;
            
            const modal = document.getElementById('shareModal');
            if (modal) modal.classList.add('open');
        }

        function closeShareModal() {
            const modal = document.getElementById('shareModal');
            if (modal) modal.classList.remove('open');
        }

        function copyShareUrl() {
            const input = document.getElementById('shareUrlInput');
            if (!input || !input.value) return;
            navigator.clipboard.writeText(input.value).then(() => {
                showTopicToast("✅ تم نسخ رابط مشاركة البحث والمراجع إلى الحافظة!");
            }).catch(() => {
                input.select();
                document.execCommand('copy');
                showTopicToast("✅ تم نسخ الرابط!");
            });
        }

        function shareViaWhatsApp() {
            const input = document.getElementById('shareUrlInput');
            const url = input ? input.value : window.location.href;
            const titleEl = document.getElementById('shareModalSubject');
            const title = titleEl ? titleEl.textContent : 'بحث لاهوتي موثق';
            const msg = `✠ بحث لاهوتي موثق من مكتبة القديس أنطونيوس:
«${title}»

📖 افتح البحث وتصفح المراجع الأصلية والصفحات الموثقة عبر الرابط:
${url}`;
            window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(msg), '_blank');
        }

        function shareViaTelegram() {
            const input = document.getElementById('shareUrlInput');
            const url = input ? input.value : window.location.href;
            const titleEl = document.getElementById('shareModalSubject');
            const title = titleEl ? titleEl.textContent : 'بحث لاهوتي موثق';
            const text = encodeURIComponent("✠ بحث لاهوتي موثق بالشواهد والصفحات: «" + title + "»");
            window.open('https://t.me/share/url?url=' + encodeURIComponent(url) + '&text=' + text, '_blank');
        }

                function exportSingleTurnDocx(turnIdx) {
            if (!currentSessionId) {
                alert("يرجى اختيار جلسة بحث أولاً.");
                return;
            }
            window.open('/api/sessions/' + currentSessionId + '/turns/' + (turnIdx || 1) + '/export?format=docx', '_blank');
        }

        function exportSingleTurnPdf(turnIdx) {
            if (!currentSessionId) {
                alert("يرجى اختيار جلسة بحث أولاً.");
                return;
            }
            window.open('/api/sessions/' + currentSessionId + '/turns/' + (turnIdx || 1) + '/export?format=pdf', '_blank');
        }

        function copyTurnMarkdown(btn) {
            const contentDiv = btn.closest('.msg-content');
            if (!contentDiv) return;
            const bubble = contentDiv.querySelector('.bubble');
            if (!bubble) return;
            const textToCopy = bubble.innerText || bubble.textContent;
            navigator.clipboard.writeText(textToCopy).then(() => {
                showTopicToast("✅ تم نسخ نص الإجابة إلى الحافظة!");
            }).catch(() => {
                showTopicToast("⚠️ تعذر النسخ المباشر.");
            });
        }

        
        // Scholar Profile & Admin Telemetry Console Functions
        function initScholarProfileUI() {
            const disp = document.getElementById('scholarNameDisplay');
            if (disp) disp.textContent = currentUserName;
            
            // Sync with backend profile table
            fetch('/api/scholar/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: currentUserId, display_name: currentUserName })
            }).catch(e => console.warn(e));
        }

        async function editScholarProfile() {
            const newName = prompt("أدخل اسمك أو صفتك (سيظهر في ملف بحثك الشخصي):", currentUserName);
            if (newName && newName.trim()) {
                currentUserName = newName.trim();
                localStorage.setItem('elantony_user_name', currentUserName);
                const disp = document.getElementById('scholarNameDisplay');
                if (disp) disp.textContent = currentUserName;

                await fetch('/api/scholar/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: currentUserId, display_name: currentUserName })
                });
                showTopicToast("✨ تم تحديث اسم ملفك الشخصي: «" + currentUserName + "»");
            }
        }

        let adminCachedData = null;

        async function openAdminConsole() {
            if (!adminPinCache) {
                const pin = prompt("🔐 أدخل الرمز السري للإشراف العام (Admin PIN):");
                if (!pin) return;
                adminPinCache = pin.trim();
                sessionStorage.setItem('elantony_admin_pin', adminPinCache);
            }

            const modal = document.getElementById('adminConsoleModal');
            if (modal) modal.classList.add('open');
            await refreshAdminData();
        }

        function closeAdminConsole() {
            const modal = document.getElementById('adminConsoleModal');
            if (modal) modal.classList.remove('open');
        }

        async function refreshAdminData() {
            try {
                const res = await fetch('/api/admin/scholars_activity?pin=' + encodeURIComponent(adminPinCache));
                if (!res.ok) {
                    sessionStorage.removeItem('elantony_admin_pin');
                    adminPinCache = '';
                    alert("⛔ رمز الإشراف غير صحيح أو تم رفض الصلاحية.");
                    closeAdminConsole();
                    return;
                }
                adminCachedData = await res.json();
                renderAdminDashboard(adminCachedData);
            } catch (err) {
                console.error("Admin fetch error:", err);
            }
        }

        function renderAdminDashboard(data) {
            document.getElementById('adminTotalScholars').textContent = data.total_scholars || 0;
            document.getElementById('adminTotalQueries').textContent = data.total_questions || 0;

            // Render Scholars
            const container = document.getElementById('adminScholarsContainer');
            if (!container) return;
            container.innerHTML = '';

            if (!data.scholars || data.scholars.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-sub);">لا يوجد مستخدمون حتى الآن.</div>';
            } else {
                data.scholars.forEach(s => {
                    const card = document.createElement('div');
                    card.className = 'scholar-card-item';
                    
                    let queriesHtml = '';
                    if (s.recent_queries && s.recent_queries.length > 0) {
                        queriesHtml = '<div class="scholar-queries-list">';
                        s.recent_queries.forEach(q => {
                            queriesHtml += `
                                <div class="scholar-query-row">
                                    <span>❓ <bdi dir="auto">${escapeHtml(q.content)}</bdi></span>
                                    <span class="scholar-query-time">${q.created_at || ''}</span>
                                </div>
                            `;
                        });
                        queriesHtml += '</div>';
                    } else {
                        queriesHtml = '<div style="font-size:12px; color:var(--text-sub); margin-top:6px;">لم يطرح أسئلة بعد في الجلسات الحالية.</div>';
                    }

                    card.innerHTML = `
                        <div class="scholar-card-header">
                            <div>
                                <span class="scholar-card-name">👤 ${escapeHtml(s.display_name)}</span>
                                <span style="font-size:11px; color:var(--text-sub); margin-right:8px;">(${s.user_id})</span>
                            </div>
                            <div>
                                <span class="scholar-card-badge">💬 ${s.query_count} أسئلة</span>
                                <span class="scholar-card-badge" style="margin-right:5px;">📁 ${s.session_count} أبحاث</span>
                                <button class="btn-ref-tool" onclick="inspectScholarSessions('${s.user_id}')" style="margin-right:8px; padding:3px 8px; font-size:11px;" title="فتح وعرض سجل أبحاث هذا الباحث">👁️ معاينة أبحاثه</button>
                            </div>
                        </div>
                        <div style="font-size:11px; color:var(--text-sub);">آخر نشاط: ${s.last_active || 'غير محدد'}</div>
                        ${queriesHtml}
                    `;
                    container.appendChild(card);
                });
            }

            // Render Live Stream
            const streamBox = document.getElementById('adminStreamContainer');
            if (streamBox && data.live_stream) {
                streamBox.innerHTML = '';
                data.live_stream.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'scholar-card-item';
                    row.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <span style="font-weight:700; color:var(--accent);">👤 ${escapeHtml(item.display_name || item.user_id)}</span>
                            <span style="font-size:11px; color:var(--text-sub);">${item.created_at}</span>
                        </div>
                        <div style="font-size:13px; font-weight:600;"><bdi dir="auto">💬 ${escapeHtml(item.content)}</bdi></div>
                        <div style="font-size:11px; color:var(--gold); margin-top:3px;">الموضوع: ${escapeHtml(item.session_title || 'عام')}</div>
                    `;
                    streamBox.appendChild(row);
                });
            }
        }

        function switchAdminSubTab(tab) {
            const btnS = document.getElementById('btnAdminTabScholars');
            const btnL = document.getElementById('btnAdminTabStream');
            const boxS = document.getElementById('adminScholarsContainer');
            const boxL = document.getElementById('adminStreamContainer');
            if (tab === 'scholars') {
                if (btnS) btnS.classList.add('active');
                if (btnL) btnL.classList.remove('active');
                if (boxS) boxS.style.display = 'block';
                if (boxL) boxL.style.display = 'none';
            } else {
                if (btnS) btnS.classList.remove('active');
                if (btnL) btnL.classList.add('active');
                if (boxS) boxS.style.display = 'none';
                if (boxL) boxL.style.display = 'block';
            }
        }

        async function inspectScholarSessions(targetUid) {
            if (!confirm("هل تريد استعراض واجهة المحادثات والتبويبات الخاصة بهذا الباحث؟")) return;
            currentUserId = targetUid;
            closeAdminConsole();
            await loadSessions();
            showTopicToast("👁️ يتم الآن استعراض أبحاث ومناقشات الباحث: " + targetUid);
        }


        window.onload = () => {
            // Always open sidebar by default on desktop; clear any collapsed state
            document.body.classList.remove('sidebar-collapsed');
            localStorage.removeItem('elantony_sidebar_collapsed');
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

            initScholarProfileUI();
            loadSessions();
            chatInput.focus();
        };
    </script>

    <!-- Research Share Modal (نافذة مشاركة البحث والتحقق من المراجع) -->
    <div class="modal-overlay" id="shareModal">
        <div class="modal-card" style="max-width: 620px;">
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">🔗</span>
                    <span class="ref-book-name" style="color:var(--accent);">مشاركة البحث اللاهوتي الموثق</span>
                    <span class="ref-badge-page">Verified Patristic Link</span>
                </div>
                <button class="btn-modal-close-ref" onclick="closeShareModal()">✕ إغلاق</button>
            </div>
            <div class="modal-body" style="padding: 22px; background: var(--bg-chat);">
                <div style="font-size: 14.5px; font-weight: 700; color: var(--accent); margin-bottom: 8px;" id="shareModalSubject">
                    بحث لاهوتي موثق
                </div>
                <div style="font-size: 13.5px; color: var(--text-sub); line-height: 1.8; margin-bottom: 16px;">
                    يمكنك إرسال هذا الرابط إلى أي شخص ليتمكن فوراً (دون الحاجة لتسجيل دخول أو برامج إضافية) من:
                    <ul style="margin: 8px 0 0 16px; padding: 0; list-style-type: '✓ ';">
                        <li>قراءة صلب الدراسة اللاهوتية وفهرس الأسئلة المتفرعة.</li>
                        <li>الاطلاع على جميع الشواهد الآبائية والكنسية المعتمدة.</li>
                        <li><strong>فتح وقراءة الصفحات الأصلية للكتب والمخطوطات</strong> مع التظليل الذهبي لموضع الاقتباس في القارئ السريع.</li>
                        <li>تنزيل أطروحة البحث كاملة بصيغة <b>Microsoft Word</b> أو <b>PDF</b>.</li>
                    </ul>
                </div>

                <label style="display:block; font-size: 12px; font-weight:700; color:var(--text-sub); margin-bottom: 6px;">رابط فتح ومراجعة هذا البحث:</label>
                <div style="display: flex; gap: 8px; margin-bottom: 18px;">
                    <input type="text" id="shareUrlInput" readonly style="flex:1; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--card-border); background: var(--input-bg); color: var(--text-main); font-family: monospace; font-size: 13px;" onclick="this.select()">
                    <button class="btn-primary" onclick="copyShareUrl()" style="white-space: nowrap; padding: 0 18px; font-weight: 700; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer;">📋 نسخ الرابط</button>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                    <button onclick="shareViaWhatsApp()" class="btn-cite-act" style="background: #25D366; color: white !important; border: none; font-weight: 700; padding: 10px; justify-content: center; border-radius: 8px; cursor: pointer;">
                        📱 واتساب
                    </button>
                    <button onclick="shareViaTelegram()" class="btn-cite-act" style="background: #0088cc; color: white !important; border: none; font-weight: 700; padding: 10px; justify-content: center; border-radius: 8px; cursor: pointer;">
                        ✈️ تليجرام
                    </button>
                    <button onclick="downloadCurrentExport('docx')" class="btn-cite-act" style="background: var(--bg-bubble-user); color: var(--text-main); border: 1px solid var(--card-border); font-weight: 700; padding: 10px; justify-content: center; border-radius: 8px; cursor: pointer;">
                        📄 تحميل Word
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- 1. Web Drag & Drop Book Uploader Modal -->
    <div class="modal-overlay" id="uploadBookModal">
        <div class="modal-card" style="max-width: 580px;">
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">📥</span>
                    <span class="ref-book-name" style="color:var(--accent);">إضافة وفهرسة كتاب جديد في المكتبة</span>
                    <span class="ref-badge-page">Instant FTS5 Ingestion</span>
                </div>
                <button class="btn-modal-close-ref" onclick="closeUploadBookModal()">✕ إغلاق</button>
            </div>
            <div class="modal-body" style="padding: 24px; background: var(--bg-chat);">
                <div id="uploadDropzone" class="upload-dropzone" onclick="document.getElementById('bookFileInput').click()" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleFileDrop(event)">
                    <div style="font-size: 38px; margin-bottom: 8px;">📚</div>
                    <div style="font-weight: 700; font-size: 15px; color: var(--text-main); margin-bottom: 4px;">اسحب وأفلت ملف الكتاب بصيغة PDF هنا</div>
                    <div style="font-size: 12px; color: var(--text-sub);">أو انقر لاختيار الملف من جهازك (يدعم كافة المخطوطات والكتب الكنسية)</div>
                    <input type="file" id="bookFileInput" accept=".pdf" style="display:none;" onchange="onBookFileSelected(this)">
                </div>
                <div id="selectedFileInfo" style="display:none; margin-top: 14px; padding: 10px 14px; background: var(--bg-darker); border-radius: 8px; border: 1px solid var(--card-border); font-size: 13px;">
                    <span style="color: var(--accent); font-weight: 700;">الملف المختار:</span> <span id="selectedFileName">--</span> (<span id="selectedFileSize">--</span>)
                </div>
                <div style="margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div>
                        <label style="display:block; font-size: 12px; font-weight: 700; color: var(--text-sub); margin-bottom: 4px;">المؤلف أو الأب (اختياري)</label>
                        <input type="text" id="uploadAuthorInput" placeholder="مثال: البابا أثناسيوس الرسولي" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--card-border); background: var(--bg-card); color: var(--text-main); font-family: inherit; font-size: 12px;">
                    </div>
                    <div>
                        <label style="display:block; font-size: 12px; font-weight: 700; color: var(--text-sub); margin-bottom: 4px;">التصنيف الكنسي (اختياري)</label>
                        <select id="uploadCategorySelect" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid var(--card-border); background: var(--bg-card); color: var(--text-main); font-family: inherit; font-size: 12px;">
                            <option value="PATRISTICS">آبائيات (Patristics)</option>
                            <option value="THEOLOGICAL_STUDIES">دراسات لاهوتية وعقيدة</option>
                            <option value="BIBLICAL_STUDIES">كتاب مقدس وتفاسير</option>
                            <option value="LITURGICAL">ليتورجيات وطقوس</option>
                            <option value="CHURCH_HISTORY">تاريخ كنسي وسير</option>
                            <option value="CANON_LAW">قوانين ومجامع كنسية</option>
                        </select>
                    </div>
                </div>
                <div id="uploadProgressBarWrap" style="display:none; margin-top: 18px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                        <span id="uploadProgressStatus" style="font-weight: 700; color: var(--accent);">جاري الرفع واستخراج الصفحات...</span>
                        <span id="uploadProgressPct" style="font-weight: 700;">0%</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: var(--bg-darker); border-radius: 4px; overflow: hidden;">
                        <div id="uploadProgressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #d97706, #10b981); transition: width 0.3s;"></div>
                    </div>
                </div>
                <div id="uploadResultCard" style="display:none; margin-top: 16px; padding: 14px; border-radius: 8px; font-size: 13px;"></div>
                <div style="margin-top: 20px; display: flex; justify-content: flex-end; gap: 8px;">
                    <button class="btn-ctrl" onclick="closeUploadBookModal()">إلغاء</button>
                    <button id="btnStartUpload" class="btn-nav btn-compile" onclick="startBookUpload()" style="padding: 8px 16px; font-size: 13px;">
                        <span>🚀</span> بدء الرفع والفهرسة الفورية
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- 2. Scholar Research Notebook & Marginalia Modal -->
    <div class="modal-overlay" id="scholarNotebookModal">
        <div class="modal-card" style="max-width: 820px;">
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">⭐</span>
                    <span class="ref-book-name" style="color:var(--gold);">كشكول الباحث ومفضلة الشواهد الكنسية</span>
                    <span class="ref-badge-page" id="notebookItemsCountBadge">0 شواهد محفوظة</span>
                </div>
                <div style="display: flex; gap: 6px;">
                    <button class="btn-cite-act" onclick="exportNotebookDocx()" title="تصدير الشواهد والهوامش إلى ملف Word">📄 تصدير الكشكول</button>
                    <button class="btn-modal-close-ref" onclick="closeScholarNotebookModal()">✕ إغلاق</button>
                </div>
            </div>
            <div class="modal-body" style="padding: 20px; overflow-y: auto; max-height: 70vh; background: var(--bg-chat);">
                <div id="notebookListContainer">
                    <div style="text-align: center; padding: 40px; color: var(--text-sub);">جاري تحميل كشكول الباحث...</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 3. Synoptic Patristic Split-View (العرض الآبائي المقارن المتزامن) -->
    <div class="modal-overlay" id="synopticCompareModal">
        <div class="modal-card" style="max-width: 96vw; width: 96vw; height: 92vh; display: flex; flex-direction: column;">
            <div class="ref-modal-header">
                <div class="ref-modal-title-wrap">
                    <span class="ref-icon">⚖️</span>
                    <span class="ref-book-name" style="color:var(--accent);">العرض الآبائي المقارن المتزامن (Synoptic Patristic Split-View)</span>
                    <span class="ref-badge-page">مقارنة نصين جنبًا إلى جنب</span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <button class="btn-ctrl" onclick="toggleSyncScroll()" id="btnSyncScroll">🔄 تمرير متزامن: مفعل</button>
                    <button class="btn-modal-close-ref" onclick="closeSynopticCompareModal()">✕ إغلاق</button>
                </div>
            </div>
            <div class="modal-body" style="flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px; background: var(--bg-darker); overflow: hidden;">
                <!-- Left Pane: Primary Text -->
                <div class="synoptic-pane" id="synopticPaneLeft" style="display: flex; flex-direction: column; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--card-border); overflow: hidden;">
                    <div style="padding: 10px 14px; background: var(--bg-darker); border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 13px; color: var(--text-main);" id="synopticLeftTitle">الشاهد الأول: --</span>
                        <div style="display: flex; gap: 4px;">
                            <button class="btn-ctrl" onclick="changeSynopticPage('left', -1)">◀</button>
                            <span id="synopticLeftPageBadge" style="font-size: 12px; padding: 2px 6px; font-weight: 700;">صـ 1</span>
                            <button class="btn-ctrl" onclick="changeSynopticPage('left', 1)">▶</button>
                        </div>
                    </div>
                    <div class="synoptic-content" id="synopticLeftBody" style="flex: 1; overflow-y: auto; padding: 16px; font-family: 'Amiri', serif; font-size: 16px; line-height: 1.8;">
                        جاري تحميل النص الأول...
                    </div>
                </div>

                <!-- Right Pane: Comparative Text -->
                <div class="synoptic-pane" id="synopticPaneRight" style="display: flex; flex-direction: column; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--card-border); overflow: hidden;">
                    <div style="padding: 10px 14px; background: var(--bg-darker); border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 13px; color: var(--text-main);" id="synopticRightTitle">الشاهد الثاني / النص المقارن: --</span>
                        <div style="display: flex; gap: 4px;">
                            <button class="btn-ctrl" onclick="changeSynopticPage('right', -1)">◀</button>
                            <span id="synopticRightPageBadge" style="font-size: 12px; padding: 2px 6px; font-weight: 700;">صـ 1</span>
                            <button class="btn-ctrl" onclick="changeSynopticPage('right', 1)">▶</button>
                        </div>
                    </div>
                    <div class="synoptic-content" id="synopticRightBody" style="flex: 1; overflow-y: auto; padding: 16px; font-family: 'Amiri', serif; font-size: 16px; line-height: 1.8;">
                        اختر شاهداً من القائمة للمقارنة أو انتظر التحميل...
                    </div>
                </div>
            </div>
        </div>
    </div>

<script>

        // ==========================================
        // JavaScript for Uploader, Notebook, Synoptic View & Sidebar Filter
        // ==========================================
        let selectedUploadFile = null;
        let scholarNotebookItems = [];
        let synopticLeftData = null;
        let synopticRightData = null;
        let isSyncScrollActive = true;

        function openUploadBookModal() {
            const m = document.getElementById('uploadBookModal');
            if (m) m.classList.add('active');
            resetUploadForm();
        }

        function closeUploadBookModal() {
            const m = document.getElementById('uploadBookModal');
            if (m) m.classList.remove('active');
        }

        function resetUploadForm() {
            selectedUploadFile = null;
            document.getElementById('bookFileInput').value = '';
            document.getElementById('selectedFileInfo').style.display = 'none';
            document.getElementById('uploadProgressBarWrap').style.display = 'none';
            document.getElementById('uploadResultCard').style.display = 'none';
            document.getElementById('uploadProgressBar').style.width = '0%';
            document.getElementById('uploadAuthorInput').value = '';
            document.getElementById('uploadCategorySelect').value = 'PATRISTICS';
        }

        function handleDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            document.getElementById('uploadDropzone').classList.add('dragover');
        }

        function handleDragLeave(e) {
            e.preventDefault();
            e.stopPropagation();
            document.getElementById('uploadDropzone').classList.remove('dragover');
        }

        function handleFileDrop(e) {
            e.preventDefault();
            e.stopPropagation();
            document.getElementById('uploadDropzone').classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const f = e.dataTransfer.files[0];
                if (f.name.toLowerCase().endsWith('.pdf')) {
                    applySelectedFile(f);
                } else {
                    alert('يرجى اختيار ملف PDF فقط.');
                }
            }
        }

        function onBookFileSelected(input) {
            if (input.files && input.files.length > 0) {
                applySelectedFile(input.files[0]);
            }
        }

        function applySelectedFile(f) {
            selectedUploadFile = f;
            document.getElementById('selectedFileName').textContent = f.name;
            const sizeMb = (f.size / (1024 * 1024)).toFixed(1);
            document.getElementById('selectedFileSize').textContent = sizeMb >= 1 ? sizeMb + ' MB' : Math.round(f.size / 1024) + ' KB';
            document.getElementById('selectedFileInfo').style.display = 'block';
        }

        async function startBookUpload() {
            if (!selectedUploadFile) {
                alert('يرجى اختيار ملف PDF أولاً.');
                return;
            }

            const author = document.getElementById('uploadAuthorInput').value.trim();
            const category = document.getElementById('uploadCategorySelect').value;

            const wrap = document.getElementById('uploadProgressBarWrap');
            const bar = document.getElementById('uploadProgressBar');
            const status = document.getElementById('uploadProgressStatus');
            const pct = document.getElementById('uploadProgressPct');
            const resCard = document.getElementById('uploadResultCard');

            wrap.style.display = 'block';
            bar.style.width = '35%';
            pct.textContent = '35%';
            status.textContent = 'جاري رفع الملف إلى الخادم...';
            resCard.style.display = 'none';

            const formData = new FormData();
            formData.append('file', selectedUploadFile);
            if (author) formData.append('author', author);
            if (category) formData.append('category', category);

            try {
                bar.style.width = '65%';
                pct.textContent = '65%';
                status.textContent = 'جاري المعالجة الرقمية واستخراج الصفحات والفهرسة الفورية...';

                const response = await fetch('/api/books/upload', {
                    method: 'POST',
                    body: formData
                });

                bar.style.width = '100%';
                pct.textContent = '100%';

                const result = await response.json();
                if (response.ok && result.success) {
                    status.textContent = 'تمت الفهرسة بنجاح!';
                    resCard.style.display = 'block';
                    resCard.style.background = 'rgba(16, 185, 129, 0.15)';
                    resCard.style.border = '1px solid #10b981';
                    resCard.style.color = '#065f46';
                    resCard.innerHTML = `
                        <div style="font-weight:700; margin-bottom: 6px;">🎉 تم إضافة وفهرسة الكتاب بنجاح!</div>
                        <div>📖 <strong>العنوان:</strong> ${result.book_title || selectedUploadFile.name}</div>
                        <div>📄 <strong>الصفحات المفهرسة:</strong> ${result.pages_extracted || result.page_count || 'تم بنجاح'}</div>
                        <div>🔍 <strong>المقاطع المستخرجة:</strong> ${result.chunks_indexed || 'مفهرس في FTS5'}</div>
                        <div style="margin-top: 10px;">
                            <button class="btn-nav btn-compile" onclick="closeUploadBookModal(); askNewQuery('ابحث في كتاب ' + '${result.book_title || selectedUploadFile.name}');">
                                🔍 ابحث في هذا الكتاب فوراً
                            </button>
                        </div>
                    `;
                } else {
                    status.textContent = 'فشلت المعالجة';
                    resCard.style.display = 'block';
                    resCard.style.background = 'rgba(239, 68, 68, 0.12)';
                    resCard.style.border = '1px solid #ef4444';
                    resCard.style.color = '#991b1b';
                    resCard.textContent = 'خطأ: ' + (result.error || result.detail || 'تعذر استكمال فهرسة الكتاب');
                }
            } catch (err) {
                status.textContent = 'حدث خطأ في الاتصال';
                resCard.style.display = 'block';
                resCard.style.background = 'rgba(239, 68, 68, 0.12)';
                resCard.style.border = '1px solid #ef4444';
                resCard.style.color = '#991b1b';
                resCard.textContent = 'خطأ شبكة أثناء رفع الملف: ' + err.message;
            }
        }

        async function openScholarNotebookModal() {
            const m = document.getElementById('scholarNotebookModal');
            if (m) m.classList.add('active');
            await loadScholarNotebook();
        }

        function closeScholarNotebookModal() {
            const m = document.getElementById('scholarNotebookModal');
            if (m) m.classList.remove('active');
        }

        async function loadScholarNotebook() {
            const cont = document.getElementById('notebookListContainer');
            try {
                const res = await fetch('/api/scholar/notebook?user_id=' + encodeURIComponent(currentUserId));
                if (!res.ok) throw new Error('فشل جلب الشواهد');
                const data = await res.json();
                scholarNotebookItems = data.items || [];
                renderScholarNotebook();
            } catch (err) {
                if (cont) cont.innerHTML = '<div style="color:var(--text-sub); text-align:center; padding:30px;">' + err.message + '</div>';
            }
        }

        function renderScholarNotebook() {
            const cont = document.getElementById('notebookListContainer');
            const badge = document.getElementById('notebookItemsCountBadge');
            const navBadge = document.getElementById('notebookBadge');
            if (badge) badge.textContent = scholarNotebookItems.length + ' شواهد محفوظة';
            if (navBadge) navBadge.textContent = scholarNotebookItems.length;

            if (!cont) return;

            if (scholarNotebookItems.length === 0) {
                cont.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-sub);">
                        <div style="font-size: 32px; margin-bottom: 8px;">⭐</div>
                        <div style="font-weight: 700; margin-bottom: 4px;">كشكول الباحث فارغ حالياً</div>
                        <div style="font-size: 12px;">انقر على زر "⭐ حفظ" على أي شاهد كنسي أثناء البحث لحفظه هنا مع تدوين تأملاتك وهوامشك الخاصة.</div>
                    </div>
                `;
                return;
            }

            cont.innerHTML = '';
            scholarNotebookItems.forEach(item => {
                const card = document.createElement('div');
                card.style.background = 'var(--bg-card)';
                card.style.border = '1px solid var(--card-border)';
                card.style.borderRadius = '8px';
                card.style.padding = '14px';
                card.style.marginBottom = '12px';

                const pLabel = item.printed_page ? `صـ ${item.printed_page} (مطبوعة)` : `صـ ${item.page_number}`;
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: var(--accent); font-size: 14px;">📖 ${item.book_title}</span>
                        <div style="display:flex; gap:6px;">
                            <button class="btn-cite-act btn-cite-fast" onclick="openInstantPageModal('${item.sha256}', ${item.page_number}, '${encodeURIComponent(item.book_title)}', '${encodeURIComponent(item.excerpt || '')}')">⚡ تصفح</button>
                            <button class="btn-sess-act btn-sess-del" onclick="deleteNotebookItem(${item.id})" title="حذف من الكشكول">✕</button>
                        </div>
                    </div>
                    <div style="font-size: 12px; color: var(--text-sub); margin-bottom: 8px;">
                        ✍️ ${item.author || 'آباء الكنيسة'} | 📄 ${pLabel} | 🕒 ${item.created_at || ''}
                    </div>
                    <div style="font-size: 13px; line-height: 1.6; color: var(--text-main); margin-bottom: 8px; font-family: 'Amiri', serif;">
                        ❝ ${item.excerpt || ''} ❞
                    </div>
                    ${item.notes ? `<div style="background: rgba(217, 119, 6, 0.08); padding: 8px; border-radius: 6px; font-size: 12px; color: var(--text-main);"><strong>📝 هامش وتأمل الباحث:</strong> ${item.notes}</div>` : ''}
                `;
                cont.appendChild(card);
            });
        }

        async function toggleSaveCitation(c) {
            const note = prompt('أضف هامشاً أو تأملاً شخصياً لهذا الشاهد (اختياري):', '');
            if (note === null) return;

            try {
                const res = await fetch('/api/scholar/notebook', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: currentUserId,
                        book_title: c.book_title,
                        author: c.author,
                        page_number: c.page_number,
                        printed_page: c.printed_page,
                        sha256: c.sha256,
                        excerpt: c.excerpt,
                        notes: note
                    })
                });
                if (res.ok) {
                    alert('⭐ تم حفظ الشاهد في كشكول الباحث بنجاح!');
                    await loadScholarNotebook();
                }
            } catch (e) {
                alert('فشل حفظ الشاهد: ' + e.message);
            }
        }

        async function deleteNotebookItem(id) {
            if (!confirm('هل تريد حذف هذا الشاهد من كشكولك؟')) return;
            try {
                await fetch('/api/scholar/notebook/' + id, { method: 'DELETE' });
                scholarNotebookItems = scholarNotebookItems.filter(x => x.id !== id);
                renderScholarNotebook();
            } catch (e) {
                alert('تعذر الحذف: ' + e.message);
            }
        }

        function exportNotebookDocx() {
            if (scholarNotebookItems.length === 0) {
                alert('الكشكول فارغ.');
                return;
            }
            let text = `✠ كشكول الباحث ومفضلة الشواهد الكنسية ✠\n\n`;
            scholarNotebookItems.forEach((it, idx) => {
                text += `[${idx+1}] ${it.book_title} صـ ${it.printed_page || it.page_number} (المؤلف: ${it.author})\n`;
                text += `النص: ❝ ${it.excerpt} ❞\n`;
                if (it.notes) text += `الهامش: ${it.notes}\n`;
                text += `---------------------------------------\n\n`;
            });
            const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = "scholar_notebook.txt";
            link.click();
        }

        async function openSynopticSplitView(sha, pageNum, encTitle, encExcerpt) {
            const m = document.getElementById('synopticCompareModal');
            if (m) m.classList.add('active');

            synopticLeftData = { sha, pageNum: parseInt(pageNum, 10), title: decodeURIComponent(encTitle), excerpt: decodeURIComponent(encExcerpt) };
            document.getElementById('synopticLeftTitle').textContent = synopticLeftData.title;
            document.getElementById('synopticLeftPageBadge').textContent = 'صـ ' + synopticLeftData.pageNum;

            await loadSynopticText('left', synopticLeftData.sha, synopticLeftData.pageNum, synopticLeftData.excerpt);
            loadSynopticRightDefault();
        }

        function closeSynopticCompareModal() {
            const m = document.getElementById('synopticCompareModal');
            if (m) m.classList.remove('active');
        }

        async function loadSynopticText(pane, sha, pageNum, excerpt) {
            const targetEl = document.getElementById(pane === 'left' ? 'synopticLeftBody' : 'synopticRightBody');
            targetEl.innerHTML = '<div style="text-align:center; padding:30px; color:var(--text-sub);">جاري استحضار النص من أصل الكتاب...</div>';

            try {
                const res = await fetch(`/api/books/${sha}/pages/${pageNum}/view?highlight=${encodeURIComponent(excerpt || '')}`);
                if (res.ok) {
                    targetEl.innerHTML = `
                        <div style="margin-bottom: 12px; padding: 10px; background: rgba(217, 119, 6, 0.08); border-radius: 6px; font-size: 14px;">
                            <strong>الشاهد المستخرج:</strong> ❝ ${escapeHtml(excerpt || '')} ❞
                        </div>
                        <iframe src="/api/books/${sha}/pages/${pageNum}/view?highlight=${encodeURIComponent(excerpt || '')}" style="width:100%; height:75vh; border:none; border-radius: 6px;"></iframe>
                    `;
                } else {
                    targetEl.textContent = 'تعذر تحميل الصفحة المحددة.';
                }
            } catch (e) {
                targetEl.textContent = 'خطأ في جلب النص: ' + e.message;
            }
        }

        function loadSynopticRightDefault() {
            const rightBody = document.getElementById('synopticRightBody');
            rightBody.innerHTML = `
                <div style="padding: 20px; text-align: center;">
                    <div style="font-size: 28px; margin-bottom: 8px;">⚖️</div>
                    <div style="font-weight: 700; margin-bottom: 8px; color: var(--accent);">اختر الشاهد المقابل للمقارنة المباشرة:</div>
                    <div id="synopticCitationsPicker" style="display: flex; flex-direction: column; gap: 8px; text-align: right; max-height: 60vh; overflow-y: auto;">
                    </div>
                </div>
            `;

            const picker = document.getElementById('synopticCitationsPicker');
            if (window.lastLoadedCitations && window.lastLoadedCitations.length > 0) {
                window.lastLoadedCitations.forEach((c, idx) => {
                    const row = document.createElement('div');
                    row.style.padding = '8px 12px';
                    row.style.background = 'var(--bg-card)';
                    row.style.border = '1px solid var(--card-border)';
                    row.style.borderRadius = '6px';
                    row.style.cursor = 'pointer';
                    row.innerHTML = `<strong>${idx+1}. ${c.book_title}</strong> (صـ ${c.printed_page || c.page_number}) - ${c.author || ''}`;
                    row.onclick = () => {
                        synopticRightData = { sha: c.sha256, pageNum: c.page_number, title: c.book_title, excerpt: c.excerpt };
                        document.getElementById('synopticRightTitle').textContent = c.book_title;
                        document.getElementById('synopticRightPageBadge').textContent = 'صـ ' + c.page_number;
                        loadSynopticText('right', c.sha256, c.page_number, c.excerpt);
                    };
                    picker.appendChild(row);
                });
            } else {
                picker.innerHTML = '<div style="color:var(--text-sub); font-size:12px;">قم بإجراء بحث لعرض الشواهد المتاحة للمقارنة أو افتح كتاباً آخر.</div>';
            }
        }

        function toggleSyncScroll() {
            isSyncScrollActive = !isSyncScrollActive;
            const btn = document.getElementById('btnSyncScroll');
            if (btn) btn.textContent = isSyncScrollActive ? '🔄 تمرير متزامن: مفعل' : '⏸️ تمرير منفصل';
        }

        function changeSynopticPage(pane, delta) {
            const data = pane === 'left' ? synopticLeftData : synopticRightData;
            if (!data) return;
            data.pageNum = Math.max(1, data.pageNum + delta);
            document.getElementById(pane === 'left' ? 'synopticLeftPageBadge' : 'synopticRightPageBadge').textContent = 'صـ ' + data.pageNum;
            loadSynopticText(pane, data.sha, data.pageNum, '');
        }

        function filterSidebarSessions(val) {
            const q = (val || '').toLowerCase().trim();
            const items = document.querySelectorAll('#chatHistoryList .chat-history-item');
            items.forEach(it => {
                const text = it.textContent.toLowerCase();
                it.style.display = text.includes(q) ? 'block' : 'none';
            });
        }

        function selectSessionAndJump(sessId, turnIdx) {
            selectSession(sessId).then(() => {
                setTimeout(() => {
                    const target = document.getElementById('turn_' + turnIdx);
                    if (target) {
                        const area = document.getElementById('messagesArea');
                        if (area) {
                            area.scrollTo({ top: target.offsetTop - 20, behavior: 'smooth' });
                        }
                        target.classList.add('turn-highlight-pulse');
                        setTimeout(() => target.classList.remove('turn-highlight-pulse'), 2000);
                    }
                }, 400);
            });
        }

        // Initialize notebook badge count on startup
        document.addEventListener('DOMContentLoaded', () => {
            loadScholarNotebook().catch(() => {});
        });

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

    chunks = search_engine.search_fts5(q, limit=req.limit or 10)
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
async def list_sessions(user_id: Optional[str] = "scholar_master", limit: int = 50, all: bool = True):
    """Lists persistent discussion sessions for user or entire library."""
    sessions = repo.list_user_sessions(user_id=user_id, limit=limit, all_sessions=all)
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

class UpdateTitleRequest(BaseModel):
    title: str

@app.put("/api/sessions/{session_id}/title")
async def update_discussion_title(session_id: str, req: UpdateTitleRequest):
    """Updates the title of a discussion session."""
    clean_title = req.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="العنوان لا يمكن أن يكون فارغاً")
    repo.update_session_title(session_id, clean_title)
    return {"success": True, "session_id": session_id, "title": clean_title}




class MergeSessionsRequest(BaseModel):
    session_ids: List[str]
    title: Optional[str] = None
    user_id: Optional[str] = "scholar_master"
    delete_sources: bool = True


@app.post("/api/sessions/merge")
async def merge_discussion_sessions(req: MergeSessionsRequest):
    """Merges multiple previous discussion sessions into a single comprehensive master session."""
    if not req.session_ids or len(req.session_ids) < 2:
        raise HTTPException(status_code=400, detail="يجب تحديد جلستي بحث على الأقل للدمج")
    
    result = repo.merge_sessions(
        session_ids=req.session_ids,
        target_title=req.title,
        user_id=req.user_id or "scholar_master",
        delete_sources=req.delete_sources
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/sessions/{session_id}/compile")
async def compile_discussion_session(session_id: str):
    """Compiles the entire discussion session into a unified research monograph."""
    res = repo.compile_session(session_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res



@app.get("/api/sessions/{session_id}/preview")
async def preview_session_monograph(session_id: str):
    """
    Renders the session as a stunning, publication-grade ecclesiastical HTML monograph
    mirroring the exact Web Portal aesthetic, ready for direct viewing and printing (Ctrl+P).
    """
    res = repo.compile_session(session_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    from elantony.services.html_exporter import generate_session_html
    html_out = generate_session_html(res)
    return Response(content=html_out.encode("utf-8"), media_type="text/html; charset=utf-8")

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

    if format == "pdf":
        from elantony.services.pdf_exporter import generate_session_pdf
        doc_dir = settings.base_dir / "data" / "compiled_researches"
        doc_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = doc_dir / f"research_{session_id}.pdf"
        generate_session_pdf(res, str(pdf_path))
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''research_{session_id}.pdf"}
        )

    content = res["markdown"] if format == "markdown" else res["plain_text"]
    filename = f"research_{session_id}.md" if format == "markdown" else f"research_{session_id}.txt"
    media_type = "text/markdown; charset=utf-8" if format == "markdown" else "text/plain; charset=utf-8"

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )



@app.get("/api/sessions/{session_id}/turns/{turn_idx}/export")
async def export_single_turn(session_id: str, turn_idx: int, format: str = "docx"):
    """
    Exports a single discussion turn/axis as an independent, beautifully formatted research paper (.docx).
    """
    res = repo.compile_session(session_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])

    turns = res.get("turns", [])
    if not turns or turn_idx < 1 or turn_idx > len(turns):
        raise HTTPException(status_code=404, detail="المبحث المطلوب غير موجود")

    target_turn = turns[turn_idx - 1]
    turn_citations = target_turn.get("citations", [])

    # Filter bibliography specifically for this turn
    turn_biblio = []
    seen_books = set()
    for c in turn_citations:
        b_title = (c.get("book_title") or "مرجع كنسي").replace(".pdf", "")
        if b_title not in seen_books:
            seen_books.add(b_title)
            p_val = c.get("printed_page") or c.get("page_number")
            turn_biblio.append({
                "title": b_title,
                "author": c.get("author", "آباء الكنيسة"),
                "pages_cited": f"صـ {p_val}" if p_val else "كامل المرجع",
                "tier": c.get("authenticity_tier", 3)
            })

    single_comp = {
        "title": target_turn.get("question", f"المبحث {turn_idx}"),
        "turns": [target_turn],
        "bibliography": turn_biblio,
        "turns_count": 1
    }

    if format == "docx":
        from elantony.services.docx_exporter import generate_session_docx
        doc_dir = settings.base_dir / "data" / "compiled_researches"
        doc_dir.mkdir(parents=True, exist_ok=True)
        docx_path = doc_dir / f"turn_{session_id}_{turn_idx}.docx"
        generate_session_docx(single_comp, str(docx_path))
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''turn_{turn_idx}_{session_id[:6]}.docx"}
        )

    if format == "pdf":
        from elantony.services.pdf_exporter import generate_session_pdf
        doc_dir = settings.base_dir / "data" / "compiled_researches"
        doc_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = doc_dir / f"turn_{session_id}_{turn_idx}.pdf"
        generate_session_pdf(single_comp, str(pdf_path))
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''turn_{turn_idx}_{session_id[:6]}.pdf"}
        )

    # Fallback to plain markdown
    md_content = f"# {target_turn.get('question', '')}\n\n{target_turn.get('answer', '')}"
    return Response(
        content=md_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''turn_{turn_idx}.md"}
    )


def apply_highlights_to_page(page, highlight_text: Optional[str] = None):
    """
    Finds and applies golden yellow highlight annotations to page for keywords in highlight_text.
    Supports Arabic, Coptic, and Greek terms safely without mutating original documents on disk.
    Resilient against zero-width rects, OCR text layout, and pure image scanned pages.
    """
    if not highlight_text or not highlight_text.strip():
        return 0
    try:
        from elantony.search.search_engine import ARABIC_STOPWORDS
        import re
        import fitz

        raw_words = re.findall(r'[\w\u0621-\u064A\u0370-\u03FF\u2C80-\u2CFF]+', highlight_text)
        terms = [w for w in raw_words if len(w) >= 3 and w not in ARABIC_STOPWORDS][:14]
        if not terms:
            return 0
        
        highlighted_count = 0
        
        def safe_add_annot(rect, color=(1.0, 0.82, 0.15)):
            nonlocal highlighted_count
            if rect.width >= 2.0 and rect.height >= 2.0 and not rect.is_empty and not rect.is_infinite:
                try:
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=color) # Warm Patristic Gold
                    annot.update()
                    highlighted_count += 1
                    return True
                except Exception:
                    pass
            return False

        # Check if page has digital text or is a scanned image
        page_text = page.get_text()
        tp = None
        if len(page_text.strip()) < 15:
            candidate_dirs = [
                r"D:\Prog\ArchiveMasterFinal\tessdata",
                r"D:\Prog\ArchiveMasterFinal\tesseract\tessdata",
                os.path.join(str(settings.base_dir), "tessdata")
            ]
            tessdata_dir = next((p for p in candidate_dirs if os.path.exists(p)), None)
            if tessdata_dir:
                try:
                    tp = page.get_textpage_ocr(language='ara+eng', tessdata=tessdata_dir, dpi=140)
                except Exception:
                    tp = None

        # 1. Search for phrase pairs
        for i in range(len(terms) - 1):
            phrase = f"{terms[i]} {terms[i+1]}"
            rects = page.search_for(phrase, textpage=tp) if tp else page.search_for(phrase)
            for r in rects:
                safe_add_annot(r)
            if highlighted_count >= 10:
                break
                
        # 2. Search for individual terms
        if highlighted_count < 4:
            for t in terms:
                rects = page.search_for(t, textpage=tp) if tp else page.search_for(t)
                for r in rects[:4]:
                    safe_add_annot(r)
                if 'ـ' in t:
                    norm_rects = page.search_for(t.replace('ـ', ''), textpage=tp) if tp else page.search_for(t.replace('ـ', ''))
                    for r in norm_rects[:3]:
                        safe_add_annot(r)
                if highlighted_count >= 16:
                    break

        # 3. Fallback: Page words bbox matching
        if highlighted_count < 3:
            page_words = page.get_text("words", textpage=tp) if tp else page.get_text("words")
            if page_words:
                norm_terms = {t.replace('ـ', '').strip('.,;:!?()[]{}«»"\'') for t in terms}
                for w in page_words:
                    w_text = w[4].replace('ـ', '').strip('.,;:!?()[]{}«»"\'')
                    if len(w_text) >= 3:
                        for nt in norm_terms:
                            if nt == w_text or (len(w_text) >= 4 and (nt in w_text or w_text in nt)):
                                bbox = fitz.Rect(w[0], w[1], w[2], w[3])
                                safe_add_annot(bbox)
                                break
                    if highlighted_count >= 20:
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

    doc = None
    try:
        import fitz
        doc = fitz.open(file_path)
        page_idx = max(0, min(page_number - 1, len(doc) - 1))
        page = doc.load_page(page_idx)
        if highlight:
            apply_highlights_to_page(page, highlight)
        pix = page.get_pixmap(dpi=140, annots=True)
        jpg_bytes = pix.tobytes("jpg")
        return Response(
            content=jpg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except Exception as e:
        logger.error(f"Error rendering page image for {sha256} p.{page_number}: {e}")
        raise HTTPException(status_code=500, detail="تعذر استخراج صورة الصفحة")
    finally:
        if doc:
            try:
                doc.close()
            except Exception:
                pass


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


@app.api_route("/api/books/{sha256}/view", methods=["GET", "HEAD"])
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


@app.api_route("/api/books/{sha256}/download", methods=["GET", "HEAD"])
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


def check_topic_continuity(prev_title: str, prev_messages: List[Dict[str, Any]], new_query: str) -> Tuple[bool, str]:
    """
    Determines whether new_query continues the current theological topic (same discussion or sub-question branch)
    or represents a completely new subject that deserves a separate tab/session.
    
    Uses Theological Domain Categorization and compares against user queries only (excluding AI essays)
    to ensure topics like 'إقامة الموتى' vs 'صلب المسيح' vs 'طوفان نوح' are cleanly separated into tabs.
    """
    if not prev_messages:
        return True, "first_turn"

    q_norm = new_query.strip().lower()

    # 1. Sub-question and Follow-up prefixes
    FOLLOWUP_PREFIXES = [
        "وضح اكثر", "وضح أكثر", "اشرح لي اكثر", "اشرح لي أكثر", "ماذا عن", "وماذا عن",
        "لا اقصد", "لا أقصد", "اقصد", "أقصد", "بمعنى اخر", "بمعنى آخر", "هل هذا يعني",
        "هل تقصد", "ولكن كيف", "لكن كيف", "طب و", "طب بالنسبه", "وما الدليل", "ما الدليل",
        "عايز اعرف", "أريد أن أعرف", "هل ينطبق", "وبالنسبة لـ", "وبالنسبه ل", "ما رأيك في"
    ]
    for p in FOLLOWUP_PREFIXES:
        if q_norm.startswith(p) or f" {p} " in q_norm:
            return True, f"followup_prefix:{p}"

    # 2. Referential Pronouns
    PRONOUNS = [" هذا ", " هذه ", " ذلك ", " تلك ", " هؤلاء ", " عنه ", " عنها ", " فيه ", " فيها ", " منه ", " منها ", " به ", " بها ", " له ", " لها "]
    padded_q = f" {q_norm} "
    for pron in PRONOUNS:
        if pron in padded_q:
            return True, f"referential_pronoun:{pron.strip()}"

    # 3. Canonical Theological Domain Categorization
    THEOLOGICAL_DOMAINS = {
        "CRUCIFIXION_PASSION": {
            "صلب", "الصلب", "المصلوب", "الصليب", "صليب", "الجلجثة", "الجمعة العظيمة", "آلام المسيح", "اسبوع الالام", "أسبوع الآلام",
            "بيلاطس", "باراباس", "قيافا", "حنانيا", "المحاكمة", "اللص اليمين", "طريق الالام", "الدفن", "القبر",
            "زلزال", "تزلزلت", "الشمس", "أظلمت", "ظلمة", "كسوف", "انشقاق", "انشق", "حجاب الهيكل", "الصخور", "تفتحت القبور", "الآيات الكونية"
        },
        "RESURRECTION_MIRACLES": {
            "إقامة", "اقامة", "أقام", "اقام", "يقيم", "الموتى", "الموتي", "الأموات", "الاموات",
            "لعازر", "يايرس", "طليثا قومي", "نايين", "أرملة نايين", "معجزات", "معجزة", "إيليا", "اليشع"
        },
        "CHRIST_RESURRECTION": {
            "قيامة", "القيامة", "قام", "الباكورة", "القبر الفارغ", "أحد القيامة", "الظهورات", "توما", "المجدلية", "عمواس"
        },
        "INCARNATION_CHRISTOLOGY": {
            "تجسد", "التجسد", "الكلمة المتجسد", "التأنس", "تأنس", "صار جسدا", "سر التجسد", "عمانوئيل",
            "طبيعة المسيح", "ميافيزيس", "كيرلس", "أثناسيوس", "نسطور", "أفسس", "خلقيدونية"
        },
        "THEOSIS": {
            "تأله", "التأله", "شريك الطبيعة الإلهية", "الاتحاد بالله", "theosis", "ثيؤسيس", "نعمة التبني"
        },
        "TRINITY": {
            "ثالوث", "الثالوث", "الأقانيم", "أقنوم", "الآب والابن", "الروح القدس", "الجوهر الإلهي", "هومواوسيوس", "الولادة الأزلية", "الانبثاق"
        },
        "SACRAMENTS": {
            "أسرار", "اسرار", "معمودية", "المعمودية", "إفخارستيا", "افخارستيا", "القربان", "التناول", "ميرون", "الميرون", "اعتراف", "توبة", "كهنوت"
        },
                "CANON_SCRIPTURE": {
            "قانونية", "القانونية", "الاسفار", "الأسفار", "طوبيا", "يهوديت", "سيراخ", "يشوع بن سيراخ",
            "المكابيين", "حكمة سليمان", "باروخ", "تتمة دانيال", "تتمة استير", "صلاة منسى", "العهد القديم"
        },
        "CREATION_FLOOD": {
            "طوفان", "الطوفان", "نوح", "فلك نوح", "الخلق", "الخليقة", "آدم وحواء", "السقوط", "تكوين", "سفر التكوين"
        }
    }

    GENERIC_NOISE = {
        'مفهوم', 'فكر', 'اقوال', 'أقوال', 'الموضوع', 'موضوع', 'المراجع', 'مراجع', 'شرح', 'تفسير',
        'قديس', 'القديس', 'انبا', 'الأنبا', 'بابا', 'البابا', 'حول', 'هذا', 'هذه', 'ذلك', 'تلك',
        'ما', 'هو', 'هي', 'عن', 'هل', 'كيف', 'ماذا', 'لماذا', 'اين', 'أين', 'متى', 'كم', 'من', 'في',
        'على', 'إلى', 'الي', 'مع', 'هكذا', 'وهكذا', 'مثل', 'كذلك', 'اثبت', 'يثبت', 'اثبات', 'أثبت',
        'تطابق', 'يطابق', 'مطابقة', 'الحدث', 'حدث', 'احداث', 'أحداث', 'العلم', 'العلمي', 'علميا', 'علم',
        'حقيقة', 'امر', 'أمر', 'شأن', 'نوع', 'وجود', 'بين', 'ايضا', 'أيضا', 'اريد', 'أريد', 'ابحث',
        'أبحث', 'اعطني', 'أعطني', 'توضيح', 'بيان', 'رأي', 'راي', 'موقف', 'نظرة', 'بخصوص', 'بشأن',
        'المسيح', 'السيد', 'الله', 'الرب', 'الإله', 'العهد', 'القديم', 'الجديد', 'الكتاب', 'المقدس'
    }

    def detect_domains(text: str) -> Set[str]:
        text_clean = re.sub(r'[^\w\s]', ' ', text).lower()
        words = set(text_clean.split())
        matched = set()
        for domain, kws in THEOLOGICAL_DOMAINS.items():
            for kw in kws:
                kw_clean = kw.lower()
                if kw_clean in words or f" {kw_clean} " in f" {text_clean} ":
                    matched.add(domain)
                    break
        return matched

    # 4. Compare only user questions and thread title (Never AI encyclopedic essays)
    prev_user_queries = [m.get("content", "") for m in prev_messages if m.get("role") == "user"]
    prev_context = " ".join([prev_title or ""] + prev_user_queries)

    prev_domains = detect_domains(prev_context)
    new_domains = detect_domains(new_query)

    if prev_domains and new_domains:
        common = prev_domains.intersection(new_domains)
        if common:
            return True, f"domain_affinity:{common}"
        else:
            return False, f"distinct_domain:{new_domains}_vs_{prev_domains}"

    # 5. Fallback: substantive keyword overlap on user text only
    prev_clean = re.sub(r'[^\w\s]', ' ', prev_context).lower()
    prev_words = {w for w in prev_clean.split() if len(w) >= 3 and w not in GENERIC_NOISE}
    
    new_clean = re.sub(r'[^\w\s]', ' ', new_query).lower()
    new_words = {w for w in new_clean.split() if len(w) >= 3 and w not in GENERIC_NOISE}

    overlap = prev_words.intersection(new_words)
    if len(overlap) >= 1:
        return True, f"user_keyword_overlap:{overlap}"

    return False, "distinct_theological_topic"


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """
    Multi-turn Conversational AI Endpoint.
    Supports intelligent auto-session splitting for distinct theological topics.
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
    is_new_topic = False
    new_topic_title = None

    topic_mode = getattr(req, "topic_mode", "continue") or "continue"

    if not session_id or session_id == "default":
        session_info = repo.get_or_create_active_session(user_id)
        session_id = session_info["id"]
    else:
        sess = repo.get_session(session_id)
        if not sess:
            session_id = repo.create_session(user_id=user_id, title=latest_msg.split("\n")[0][:45].strip(), session_id=session_id)
            is_new_topic = True
            sess = repo.get_session(session_id)
        if sess:
            if topic_mode == "new":
                new_topic_title = latest_msg.split("\n")[0][:45].strip()
                new_sess_id = repo.create_session(user_id=user_id, title=new_topic_title)
                logger.info(f"[TopicSwitch] Manual User Choice (new). Created new session {new_sess_id} for '{new_topic_title}'.")
                session_id = new_sess_id
                is_new_topic = True
            elif topic_mode == "continue":
                is_new_topic = False
                logger.info(f"[TopicSwitch] Manual User Choice (continue). Keeping in session {session_id}.")
            else:
                existing_messages = repo.get_session_messages(session_id)
                if existing_messages:
                    is_same, reason = check_topic_continuity(sess.get("title", ""), existing_messages, latest_msg)
                    if not is_same:
                        new_topic_title = latest_msg.split("\n")[0][:45].strip()
                        new_sess_id = repo.create_session(user_id=user_id, title=new_topic_title)
                        logger.info(f"[TopicSwitch] Detected distinct topic ({reason}). Created new session {new_sess_id} for '{new_topic_title}'.")
                        session_id = new_sess_id
                        is_new_topic = True

    # 1. Retrieve library context
    chunks = search_engine.search_fts5(latest_msg, limit=12)
    ai_provider = get_ai_provider()
    depth_mode = req.depth_mode or "academic"

    # 2. Conversational reasoning with past dialogue turns
    if is_new_topic:
        raw_history = [{"role": "user", "content": latest_msg}]
    else:
        raw_history = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        if hasattr(ai_provider, "generate_chat_response"):
            answer = ai_provider.generate_chat_response(raw_history, chunks, depth_mode=depth_mode)
        else:
            answer = ai_provider.generate_answer(latest_msg, chunks, depth_mode=depth_mode)
    except Exception as ai_err:
        logger.error(f"[ChatAPI] AI Generation exception: {ai_err}. Falling back to RuleBasedChurchProvider...")
        try:
            from elantony.ai.rule_based_provider import RuleBasedChurchProvider
            fallback_provider = RuleBasedChurchProvider()
            answer = fallback_provider.generate_answer(latest_msg, chunks, depth_mode=depth_mode)
        except Exception as fb_err:
            logger.error(f"[ChatAPI] Rule-based fallback also failed: {fb_err}")
            answer = "⚠️ تعذر توليد الشرح الإنشائي بسبب انقطاع الاتصال الخارجي المؤقت، ولكن تم استخراج الشواهد الآبائية والكنسية المعتمدة وتوثيقها أدناه بنجاح لدراستك الموثقة." 

    # 3. Format citations with sha256 and metadata for live book viewer
    citations = []
    for c in chunks:
        book_info = repo.get_book_by_sha(c.sha256) if c.sha256 else None
        p_count = book_info.get("page_count") if book_info else 0
        f_size = book_info.get("file_size") if book_info else 0
        size_mb = round(f_size / (1024 * 1024), 1) if f_size else 0
        size_str = f"{size_mb} MB" if size_mb >= 1 else (f"{round(f_size / 1024)} KB" if f_size else "")

        # Author fallback resolution
        resolved_author = c.author
        if not resolved_author or resolved_author in ["غير محدد", "غير معروف", "مجهول"]:
            clean_t = (c.book_title or "").replace(".pdf", "")
            for sep in [" - ", " – ", " — "]:
                if sep in clean_t:
                    parts = [p.strip() for p in clean_t.split(sep)]
                    if len(parts) >= 2:
                        resolved_author = parts[-1]
                        break
        if not resolved_author or resolved_author in ["غير محدد", "غير معروف", "مجهول"]:
            resolved_author = "آباء ومعلمو الكنيسة"

        cleaned_excerpt = clean_citation_excerpt(c.chunk_text, 320)

        citations.append({
            "book_title": c.book_title,
            "page_number": c.page_number,
            "printed_page": c.printed_page,
            "page_count": p_count or 1,
            "file_size_formatted": size_str,
            "source_reference": c.source_reference,
            "author": resolved_author,
            "source_types": c.source_types,
            "authenticity_tier": c.authenticity_tier,
            "relevance_score": c.relevance_score,
            "sha256": c.sha256,
            "excerpt": cleaned_excerpt
        })

    # Turn number in discussion
    turn_number = 1 if is_new_topic else ((len(raw_history) // 2) + 1)

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

    current_sess_info = repo.get_session(session_id)
    resolved_title = current_sess_info.get("title") if current_sess_info else (new_topic_title or "بحث لاهوتي")

    return {
        "response": answer,
        "citations": citations,
        "session_id": session_id,
        "is_new_topic": is_new_topic,
        "topic_title": resolved_title,
        "turn_number": turn_number
    }



class ScholarProfileRequest(BaseModel):
    user_id: str
    display_name: Optional[str] = "باحث لاهوتي"


@app.post("/api/scholar/profile")
async def update_scholar_profile(req: ScholarProfileRequest):
    """Registers or updates scholar display name and touch timestamp."""
    repo.register_or_touch_scholar(req.user_id, req.display_name)
    return {"status": "ok", "user_id": req.user_id, "display_name": req.display_name}


@app.get("/api/admin/scholars_activity")
async def get_scholars_activity(pin: Optional[str] = Query(None), x_admin_pin: Optional[str] = Header(None)):
    """
    Master Admin Super-View: Lists all distinct scholars, their questions,
    discussions, and global activity. Protected by admin PIN (default: 2026).
    """
    admin_pin = os.getenv("ADMIN_PORTAL_PIN", "2026").strip()
    provided = pin or x_admin_pin or ""
    if provided != admin_pin:
        raise HTTPException(status_code=403, detail="رمز الإشراف غير صحيح. مصرح للأدمن فقط.")
    return repo.get_all_scholars_activity()


@app.get("/api/admin/scholars/{target_user_id}/sessions")
async def get_scholar_sessions_admin(target_user_id: str, pin: Optional[str] = Query(None), x_admin_pin: Optional[str] = Header(None)):
    """Allows Admin to inspect any specific scholar's discussion threads."""
    admin_pin = os.getenv("ADMIN_PORTAL_PIN", "2026").strip()
    provided = pin or x_admin_pin or ""
    if provided != admin_pin:
        raise HTTPException(status_code=403, detail="رمز الإشراف غير صحيح. مصرح للأدمن فقط.")
    sessions = repo.list_user_sessions(user_id=target_user_id, limit=50)
    return {"user_id": target_user_id, "sessions": sessions}


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


# ==========================================
# Feature 1: Web Drag & Drop Book Uploader
# ==========================================
from fastapi import UploadFile, File, Form
from services.permanent_assistant.ingestion_pipeline import auto_ingestor

@app.post("/api/books/upload")
async def upload_book_file(
    file: UploadFile = File(...),
    author: Optional[str] = Form(None),
    category: Optional[str] = Form(None)
):
    """
    Autonomous Web Book Uploader:
    Saves uploaded PDF book, performs SHA-256 integrity check,
    extracts pages, classifies ecclesiastical tier, and indexes into FTS5.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف بصيغة PDF فقط")

    dest_dir = Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\الكتب المضافة حديثاً")
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        dest_dir = settings.base_dir / "data" / "uploaded_books"
        dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / file.filename
    content = await file.read()
    with open(dest_file, "wb") as f:
        f.write(content)

    # Ingest book into system FTS5 database
    res = auto_ingestor.ingest_pdf(dest_file, forced=True)

    if res.get("success") and (author or category):
        sha = res.get("sha256")
        if sha:
            try:
                conn = get_connection()
                cur = conn.cursor()
                if author:
                    cur.execute("UPDATE church_books SET author = ? WHERE sha256 = ?", (author, sha))
                if category:
                    cur.execute("UPDATE church_books SET source_types = ? WHERE sha256 = ?", (json.dumps([category], ensure_ascii=False), sha))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"Failed to update metadata for uploaded book: {e}")

    return res


# ==========================================
# Feature 3: Scholar Research Notebook
# ==========================================
class NotebookItem(BaseModel):
    user_id: Optional[str] = "web"
    book_title: str
    author: Optional[str] = "آباء الكنيسة"
    page_number: Optional[int] = 1
    printed_page: Optional[str] = None
    sha256: Optional[str] = None
    excerpt: Optional[str] = None
    notes: Optional[str] = ""

@app.get("/api/scholar/notebook")
async def get_scholar_notebook(user_id: str = "web"):
    """Retrieves all bookmarked citations and scholar marginalia."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, book_title, author, page_number, printed_page, sha256, excerpt, notes, created_at
        FROM scholar_notebook
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"items": rows}

@app.post("/api/scholar/notebook")
async def add_scholar_notebook_item(item: NotebookItem):
    """Saves a citation bookmark with researcher notes into scholar notebook."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scholar_notebook (user_id, book_title, author, page_number, printed_page, sha256, excerpt, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (item.user_id or "web", item.book_title, item.author, item.page_number, item.printed_page, item.sha256, item.excerpt, item.notes or ""))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "id": item_id}

@app.delete("/api/scholar/notebook/{item_id}")
async def delete_scholar_notebook_item(item_id: int):
    """Deletes a citation bookmark from the notebook."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scholar_notebook WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"success": True}
