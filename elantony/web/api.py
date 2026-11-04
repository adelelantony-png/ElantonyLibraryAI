# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Web & Cloud REST API
Provides conversational ChatGPT-like Research Portal, FTS5 Search,
Word (.docx) Export, Book Viewing, and Admin Management Endpoints.
"""

import os
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
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-darker: #090D16;
            --bg-sidebar: #0F172A;
            --bg-chat: #131D31;
            --bg-bubble-ai: #1E293B;
            --bg-bubble-user: #2563EB;
            --card-border: #334155;
            --accent: #3B82F6;
            --accent-hover: #1D4ED8;
            --gold: #F59E0B;
            --gold-light: #FDE68A;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --radius-bubble: 16px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background: var(--bg-darker); color: var(--text-main); height: 100vh; display: flex; overflow: hidden; }

        /* Sidebar */
        .sidebar {
            width: 300px;
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
            font-size: 16px;
            color: #FFF;
            letter-spacing: 0.5px;
        }
        .app-brand span { color: var(--gold); }
        .btn-new-chat {
            margin: 14px 18px;
            background: rgba(59, 130, 246, 0.15);
            border: 1px dashed var(--accent);
            color: #60A5FA;
            padding: 11px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 14px;
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
            padding: 0 14px;
        }
        .chat-history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 9px 12px;
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-sub);
            cursor: pointer;
            margin-bottom: 4px;
            transition: 0.2s;
            border: 1px solid transparent;
        }
        .chat-history-item:hover, .chat-history-item.active {
            background: rgba(255,255,255,0.08);
            color: #FFF;
            border-color: rgba(255,255,255,0.1);
        }
        .chat-history-item.active {
            background: rgba(59, 130, 246, 0.15);
            border-color: var(--accent);
            color: #93C5FD;
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
        .chat-history-item:hover .btn-sess-act { opacity: 0.8; }
        .btn-sess-act:hover { opacity: 1; background: rgba(255,255,255,0.12); color: #FFF; }
        .btn-sess-del:hover { background: rgba(239,68,68,0.25); color: #EF4444; }

        .sidebar-footer {
            padding: 14px 18px;
            border-top: 1px solid var(--card-border);
            font-size: 12px;
            color: var(--text-sub);
            background: rgba(0,0,0,0.25);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .sidebar-footer strong { color: var(--gold); }
        .sidebar-footer a { color: #60A5FA; text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }

        /* Main Container */
        .main-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }
        .top-navbar {
            min-height: 62px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 20px;
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(10px);
            gap: 12px;
            flex-wrap: wrap;
        }
        .nav-title { font-weight: 800; font-size: 15px; display: flex; align-items: center; gap: 8px; color: #FFF; }
        .nav-title span { color: var(--gold); }

        /* Depth Selector */
        .depth-selector-group {
            display: flex;
            align-items: center;
            background: #090D16;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 3px;
            gap: 2px;
        }
        .depth-label {
            font-size: 11px;
            font-weight: 800;
            color: var(--gold);
            padding: 0 8px;
        }
        .btn-depth {
            background: none;
            border: none;
            color: var(--text-sub);
            padding: 5px 10px;
            border-radius: 7px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn-depth:hover { color: #FFF; background: rgba(255,255,255,0.05); }
        .btn-depth.active {
            background: var(--accent);
            color: #FFF;
            box-shadow: 0 2px 6px rgba(37,99,235,0.4);
        }

        .nav-actions { display: flex; align-items: center; gap: 8px; }
        .btn-nav {
            padding: 6px 13px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 12px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: 0.2s;
            border: 1px solid transparent;
            text-decoration: none;
        }
        .btn-compile { background: rgba(245, 158, 11, 0.15); border-color: var(--gold); color: #FBBF24; }
        .btn-compile:hover { background: var(--gold); color: #000; }
        .btn-docx-nav { background: rgba(16, 185, 129, 0.15); border-color: #10B981; color: #34D399; }
        .btn-docx-nav:hover { background: #10B981; color: #000; }
        .btn-export-nav { background: rgba(59, 130, 246, 0.15); border-color: var(--accent); color: #60A5FA; }
        .btn-export-nav:hover { background: var(--accent); color: #FFF; }

        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.82);
            backdrop-filter: blur(6px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal-overlay.open { display: flex; }
        .modal-card {
            background: #0F172A;
            border: 1px solid var(--card-border);
            border-radius: 16px;
            width: 100%;
            max-width: 980px;
            max-height: 88vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 25px 50px rgba(0,0,0,0.7);
            overflow: hidden;
        }
        .modal-header {
            padding: 16px 22px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #131D31;
        }
        .modal-title {
            font-weight: 800;
            font-size: 16px;
            color: var(--gold);
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
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid var(--accent);
            color: #93C5FD;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn-modal-act:hover { background: var(--accent); color: #FFF; }
        .btn-modal-docx {
            background: rgba(16, 185, 129, 0.2);
            border-color: #10B981;
            color: #6EE7B7;
        }
        .btn-modal-docx:hover { background: #10B981; color: #000; }
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
            font-size: 15px;
            line-height: 1.85;
        }
        .modal-body h1, .modal-body h2, .modal-body h3 { color: #60A5FA; margin: 16px 0 8px 0; }
        .modal-body strong { color: var(--gold); }
        .modal-body blockquote { border-right: 4px solid var(--gold); padding-right: 14px; margin: 12px 0; color: #CBD5E1; font-style: italic; background: rgba(255,255,255,0.02); padding: 8px 14px; border-radius: 4px; }

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
            max-width: 920px;
            margin: 0 auto;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 22px;
        }

        /* Message Bubbles */
        .msg-row {
            display: flex;
            gap: 14px;
            width: 100%;
        }
        .msg-row.user {
            justify-content: flex-start;
            flex-direction: row-reverse;
        }
        .msg-avatar {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: 900;
            flex-shrink: 0;
        }
        .msg-avatar.ai { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFF; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }
        .msg-avatar.user { background: #475569; color: #FFF; }

        .msg-content {
            max-width: 86%;
            display: flex;
            flex-direction: column;
        }
        .turn-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: var(--gold);
            font-size: 11px;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 6px;
            margin-bottom: 6px;
            align-self: flex-start;
        }
        .bubble {
            padding: 18px 22px;
            border-radius: var(--radius-bubble);
            font-size: 15px;
            line-height: 1.8;
            word-break: break-word;
        }
        .msg-row.user .bubble {
            background: var(--bg-bubble-user);
            color: #FFF;
            border-top-left-radius: 4px;
        }
        .msg-row.ai .bubble {
            background: var(--bg-bubble-ai);
            color: var(--text-main);
            border: 1px solid var(--card-border);
            border-top-right-radius: 4px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        }

        /* Markdown inside assistant */
        .bubble h1, .bubble h2, .bubble h3, .bubble h4 { color: #60A5FA; margin: 14px 0 6px 0; }
        .bubble ul, .bubble ol { margin: 8px 24px; }
        .bubble li { margin-bottom: 4px; }
        .bubble strong { color: #F59E0B; }
        .bubble hr { border: 0; height: 1px; background: var(--card-border); margin: 16px 0; }
        .bubble blockquote { border-right: 3px solid var(--gold); padding-right: 12px; margin: 8px 0; color: #CBD5E1; font-style: italic; background: rgba(255,255,255,0.02); padding: 6px 12px; border-radius: 4px; }

        /* Citations Box */
        .citations-section {
            margin-top: 12px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px 14px;
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
            margin-top: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .citation-item {
            background: rgba(30, 41, 59, 0.85);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
        }
        .citation-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .citation-title { font-weight: 800; color: #93C5FD; font-size: 13px; }
        .citation-badge { background: rgba(245, 158, 11, 0.2); color: var(--gold); padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; white-space: nowrap; }
        .citation-meta { font-size: 12px; color: #94A3B8; margin-top: 4px; }
        .citation-excerpt { color: #CBD5E1; font-size: 12px; margin-top: 8px; border-right: 2px solid var(--accent); padding-right: 10px; line-height: 1.6; }
        .citation-actions { margin-top: 8px; display: flex; gap: 8px; }
        .btn-cite-act {
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: 0.2s;
        }
        .btn-cite-view { background: rgba(59, 130, 246, 0.15); border: 1px solid var(--accent); color: #93C5FD; }
        .btn-cite-view:hover { background: var(--accent); color: #FFF; }
        .btn-cite-dl { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15); color: #CBD5E1; }
        .btn-cite-dl:hover { background: rgba(255, 255, 255, 0.15); color: #FFF; }

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
            background: rgba(59, 130, 246, 0.12);
            border: 1px solid var(--accent);
            color: #60A5FA;
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 800;
            margin-bottom: 14px;
        }
        .hero h2 { font-size: 2rem; font-weight: 900; color: #FFF; margin-bottom: 8px; }
        .hero p { color: var(--text-sub); font-size: 15px; max-width: 640px; margin: 0 auto 26px auto; line-height: 1.7; }
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
            color: #CBD5E1;
        }
        .prompt-card:hover {
            border-color: var(--accent);
            background: #253349;
            transform: translateY(-2px);
            color: #FFF;
        }

        /* Bottom Input Bar */
        .input-area {
            padding: 14px 20px 18px 20px;
            border-top: 1px solid var(--card-border);
            background: var(--bg-sidebar);
        }
        .input-box-wrapper {
            max-width: 920px;
            margin: 0 auto;
            position: relative;
            background: #0F172A;
            border: 1px solid var(--card-border);
            border-radius: 14px;
            display: flex;
            align-items: flex-end;
            padding: 8px 14px;
            transition: 0.2s;
        }
        .input-box-wrapper:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }
        .chat-textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: #FFF;
            font-size: 15px;
            resize: none;
            outline: none;
            max-height: 180px;
            min-height: 26px;
            line-height: 1.5;
            padding: 6px 0;
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
        .btn-send:disabled { background: #334155; cursor: not-allowed; opacity: 0.6; transform: none; }
        .input-disclaimer {
            text-align: center;
            font-size: 12px;
            color: var(--text-sub);
            margin-top: 8px;
        }

        /* Loading Dots */
        .typing-dots { display: inline-flex; gap: 4px; padding: 6px 0; }
        .typing-dots span { width: 6px; height: 6px; background: #60A5FA; border-radius: 50%; animation: blink 1.4s infinite; }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }

        @media (max-width: 820px) {
            .sidebar { display: none; }
            .top-navbar { flex-direction: column; align-items: stretch; }
            .depth-selector-group { justify-content: center; }
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="app-brand">
                <span>✠</span> ELANTONY AI
            </div>
            <a href="https://t.me/ElantonyLibrarybot" target="_blank" title="فتح البوت الرسمي على تليجرام" style="color: #60A5FA; font-size: 18px; text-decoration: none;">
                ✈️
            </a>
        </div>
        <button class="btn-new-chat" onclick="startNewChat()">
            <span>➕</span> محادثة بحثية جديدة
        </button>
        <div class="chat-history-title">📂 أبحاثك ومناقشاتك المحفوظة</div>
        <div class="chat-history" id="chatHistoryList">
            <!-- Sessions populate dynamically -->
        </div>
        <div class="sidebar-footer">
            <div>🏛️ <strong>3,656</strong> كتاباً مفهرساً</div>
            <div>🧠 <strong>Gemini 3.5 / 2.5 Flash</strong> (صفر هلوسة)</div>
            <div>📄 <strong>تصدير فوري</strong> Word (.docx)</div>
            <div style="margin-top: 6px;">
                <a href="https://t.me/ElantonyLibrarybot" target="_blank">📱 @ElantonyLibrarybot</a>
            </div>
        </div>
    </aside>

    <!-- Main Chat Container -->
    <main class="main-container">
        <!-- Top Navbar -->
        <div class="top-navbar">
            <div class="nav-title">
                <span>✠</span> المساعد والباحث اللاهوتي الذكي
            </div>

            <!-- Depth Mode Switcher -->
            <div class="depth-selector-group" title="اختر نمط وعمق الإجابة اللاهوتية">
                <span class="depth-label">النمط:</span>
                <button class="btn-depth active" id="depth_academic" onclick="setDepthMode('academic')">🎓 أكاديمي موسع</button>
                <button class="btn-depth" id="depth_pastoral" onclick="setDepthMode('pastoral')">🕊️ رعوي روحي</button>
                <button class="btn-depth" id="depth_apologetic" onclick="setDepthMode('apologetic')">⚖️ دفاعي مقارن</button>
            </div>

            <div class="nav-actions">
                <button class="btn-nav btn-compile" onclick="openCompilationModal()" title="تجميع أسئلة وإجابات البحث مع الفهرس والمراجع">
                    <span>📑</span> تجميع البحث
                </button>
                <button class="btn-nav btn-docx-nav" onclick="downloadCurrentExport('docx')" title="تنزيل أطروحة البحث كاملة كملف Microsoft Word منسق">
                    <span>📄</span> تنزيل Word
                </button>
                <button class="btn-nav btn-export-nav" onclick="downloadCurrentExport('markdown')" title="تصدير كملف Markdown">
                    <span>📥</span> .md
                </button>
            </div>
        </div>

        <!-- Messages Area -->
        <div class="messages-area" id="messagesArea">
            <div class="messages-container" id="messagesContainer">
                <!-- Hero screen when no messages -->
                <div class="hero" id="heroScreen">
                    <div class="hero-badge">✠ منظومة ELANTONY LIBRARY الذكية</div>
                    <h2>كيف يمكنني مساندتك في بحثك الكنسي اليوم؟</h2>
                    <p>أنا مساعدك اللاهوتي والآبائي المتخصص؛ أستحضر لك دراسات موثقة بالشواهد والصفحات من بطون أمهات الكتب الكنسية المفهرسة مع حفظ سياق النقاش وإمكانية تصدير البحث كاملاً كملف Word.</p>
                    <div class="prompt-cards">
                        <div class="prompt-card" onclick="sendPrompt('ما مفهوم التجسد الإلهي في الفكر الآبائي عند القديس أثناسيوس الرسولي؟ اذكر المراجع وأرقام الصفحات')">
                            🎓 <strong>دراسة أكاديمية آبائية:</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">عقيدة تجسد الكلمة وتجديد الطبيعة مع الشواهد والصفحات</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('قارن بين إقامة السيد المسيح للموتى بسلطانه وإقامة أنبياء العهد القديم للموتى في تعليم الآباء')">
                            ⚖️ <strong>دراسة دفاعية ومقارنة:</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">الفارق الجوهري والسلطان الإلهي الذاتي وتفنيد الشبهات</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('كيف يعيش المؤمن حياة الصلاة الدائمة ونقاوة الفكر بحسب تعاليم القديس أنطونيوس الكبير؟')">
                            🕊️ <strong>إرشاد رعوي وروحي:</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">حرب الأفكار وجهاد التوبة والهدوء في الحياة اليومية</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('اشرح الأبعاد اللاهوتية والخلاصية لطقس صلاة الصلح وسر الإفخارستيا في القداس الباسيلي')">
                            ⛪ <strong>تأصيل طقسي وليتورجي:</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">المصالحة العظمى وقبلة المحبة والسلام والشركة الحية</div>
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
                    placeholder="تفضل بكتابة سؤالك اللاهوتي هنا... (يمكنك طرح أسئلة فرعية متتابعة وتجميعها في ملف Word بنقرة واحدة)"
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
                    <button class="btn-modal-act btn-modal-docx" onclick="downloadCurrentExport('docx')">📄 تنزيل مستند Word (.docx)</button>
                    <button class="btn-modal-act" onclick="copyCompilationText()">📋 نسخ النص</button>
                    <button class="btn-modal-act" onclick="downloadCurrentExport('markdown')">📥 تنزيل (.md)</button>
                    <button class="btn-modal-act" onclick="window.print()">🖨️ طباعة</button>
                    <button class="btn-modal-close" onclick="closeCompilationModal()">✕</button>
                </div>
            </div>
            <div class="modal-body" id="compileModalBody">
                <div style="text-align: center; padding: 40px; color: #94A3B8;">جاري تجميع البحث وتوثيق المراجع...</div>
            </div>
        </div>
    </div>

    <script>
        let chatMessages = [];
        let currentSessionId = null;
        let currentDepthMode = "academic";
        let rawCompiledMarkdown = "";

        const messagesContainer = document.getElementById('messagesContainer');
        const heroScreen = document.getElementById('heroScreen');
        const chatInput = document.getElementById('chatInput');
        const btnSend = document.getElementById('btnSend');
        const messagesArea = document.getElementById('messagesArea');
        const compileModal = document.getElementById('compileModal');
        const compileModalBody = document.getElementById('compileModalBody');

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
                
                // Refresh sessions silently to reflect updated title
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

            // Citations Box with direct book page links
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
                        actionsHtml = `
                            <div class="citation-actions">
                                <a href="/api/books/${c.sha256}/view#page=${c.page_number}" target="_blank" class="btn-cite-act btn-cite-view">
                                    📖 فتح الكتاب (صـ ${c.page_number})
                                </a>
                                <a href="/api/books/${c.sha256}/download" target="_blank" class="btn-cite-act btn-cite-dl">
                                    💾 تنزيل PDF
                                </a>
                            </div>
                        `;
                    }

                    item.innerHTML = `
                        <div class="citation-top">
                            <span class="citation-title">📖 ${idx + 1}. ${c.book_title}</span>
                            <span class="citation-badge">Tier ${c.authenticity_tier || 3}</span>
                        </div>
                        <div class="citation-meta">
                            ✍️ ${c.author || 'آباء الكنيسة'} | 📄 ${pLabel}
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

            row.appendChild(avatar);
            row.appendChild(contentDiv);
            messagesContainer.appendChild(row);
            scrollToBottom();
        }

        function appendLoadingBubble() {
            const id = 'loading_' + Date.now();
            const row = document.createElement('div');
            row.id = id;
            row.className = 'msg-row ai';
            row.innerHTML = `
                <div class="msg-avatar ai">✠</div>
                <div class="msg-content">
                    <div class="bubble">
                        <div class="typing-dots">
                            <span></span><span></span><span></span>
                        </div>
                        <span style="font-size: 13px; color: #94A3B8; margin-right: 8px;">جاري فحص المراجع واستخلاص الأقوال والتحليل الآبائي...</span>
                    </div>
                </div>
            `;
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
                alert("لا توجد محادثة نشطة لتجميعها حالياً.");
                return;
            }
            compileModal.classList.add('open');
            compileModalBody.innerHTML = '<div style="text-align: center; padding: 40px; color: #94A3B8;"><div class="typing-dots"><span></span><span></span><span></span></div><br>جاري تجميع البحث واستخراج الفهرس وتوثيق المراجع...</div>';

            try {
                const res = await fetch('/api/sessions/' + currentSessionId + '/compile', { method: 'POST' });
                if (!res.ok) throw new Error('فشل تجميع البحث');
                const data = await res.json();
                rawCompiledMarkdown = data.markdown;
                compileModalBody.innerHTML = marked.parse(data.markdown);
            } catch (err) {
                compileModalBody.innerHTML = '<div style="color: #EF4444; padding: 20px;">⚠️ تعذر تجميع البحث: ' + err.message + '</div>';
            }
        }

        function closeCompilationModal() {
            compileModal.classList.remove('open');
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
            loadSessions();
            chatInput.focus();
        };
    </script>
</body>
</html>
"""


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


@app.get("/api/books/{sha256}/view")
@app.get("/api/books/{sha256}/download")
async def get_book_file(sha256: str, download: bool = False):
    """Streams book PDF for browser viewing or direct download."""
    book = repo.get_book_by_sha(sha256)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود في سجلات المكتبة")

    file_path = book.get("original_path") or book.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ملف الكتاب غير متوفر على القرص المحلي")

    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline"
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

    # 3. Format citations with sha256 for live book viewer
    citations = []
    for c in chunks:
        citations.append({
            "book_title": c.book_title,
            "page_number": c.page_number,
            "printed_page": c.printed_page,
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
