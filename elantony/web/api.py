# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Web & Cloud REST API
Provides conversational ChatGPT-like Research Portal, FTS5 Search,
and Admin Management Endpoints.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages optional embedded bot worker if explicitly enabled."""
    global bot_task, bot_engine
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
    version="2.5.0",
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


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[str] = "default"


WEB_PORTAL_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✠ ELANTONY LIBRARY AI - المساعد الذكي لمكتبة القديس أنطونيوس</title>
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
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --radius-bubble: 16px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background: var(--bg-darker); color: var(--text-main); height: 100vh; display: flex; overflow: hidden; }

        /* Sidebar */
        .sidebar {
            width: 280px;
            background: var(--bg-sidebar);
            border-left: 1px solid var(--card-border);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            z-index: 20;
        }
        .sidebar-header {
            padding: 18px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .app-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 800;
            font-size: 16px;
            color: #FFF;
        }
        .app-brand span { color: var(--gold); }
        .btn-new-chat {
            margin: 14px 18px;
            background: rgba(59, 130, 246, 0.15);
            border: 1px dashed var(--accent);
            color: #60A5FA;
            padding: 10px;
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
        .btn-new-chat:hover { background: var(--accent); color: #FFF; border-style: solid; }
        .chat-history {
            flex: 1;
            overflow-y: auto;
            padding: 0 14px;
        }
        .chat-history-item {
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-sub);
            cursor: pointer;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            transition: 0.2s;
        }
        .chat-history-item:hover, .chat-history-item.active {
            background: rgba(255,255,255,0.06);
            color: #FFF;
        }
        .sidebar-footer {
            padding: 16px;
            border-top: 1px solid var(--card-border);
            font-size: 12px;
            color: var(--text-sub);
            background: rgba(0,0,0,0.2);
        }
        .sidebar-footer a { color: #60A5FA; text-decoration: none; font-weight: 600; }

        /* Main Container */
        .main-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }
        .top-navbar {
            height: 60px;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(8px);
        }
        .nav-title { font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 8px; }
        .live-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(34, 197, 94, 0.15); color: #4ADE80; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
        .live-dot { width: 8px; height: 8px; background: #22C55E; border-radius: 50%; animation: pulse 2s infinite; }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

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
            max-width: 82%;
            display: flex;
            flex-direction: column;
        }
        .bubble {
            padding: 16px 20px;
            border-radius: var(--radius-bubble);
            font-size: 15px;
            line-height: 1.7;
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

        /* Markdown formatting inside assistant bubble */
        .bubble h1, .bubble h2, .bubble h3, .bubble h4 { color: #60A5FA; margin: 12px 0 6px 0; }
        .bubble ul, .bubble ol { margin: 8px 24px; }
        .bubble li { margin-bottom: 4px; }
        .bubble strong { color: #F59E0B; }
        .bubble blockquote { border-right: 3px solid var(--gold); padding-right: 12px; margin: 8px 0; color: #CBD5E1; font-style: italic; }

        /* Citations Box */
        .citations-section {
            margin-top: 10px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 12px;
        }
        .citations-header {
            font-size: 13px;
            font-weight: 700;
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
            gap: 8px;
        }
        .citation-item {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 13px;
        }
        .citation-title { font-weight: 700; color: #93C5FD; display: flex; justify-content: space-between; }
        .citation-badge { background: rgba(245, 158, 11, 0.2); color: var(--gold); padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .citation-excerpt { color: #94A3B8; font-size: 12px; margin-top: 6px; border-right: 2px solid var(--accent); padding-right: 8px; }

        /* Hero / Empty State */
        .hero {
            text-align: center;
            margin: auto 0;
            padding: 40px 20px;
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
            font-weight: 700;
            margin-bottom: 16px;
        }
        .hero h2 { font-size: 2rem; font-weight: 800; color: #FFF; margin-bottom: 8px; }
        .hero p { color: var(--text-sub); font-size: 15px; max-width: 600px; margin: 0 auto 28px auto; }
        .prompt-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 14px;
            max-width: 800px;
            margin: 0 auto;
        }
        .prompt-card {
            background: var(--bg-bubble-ai);
            border: 1px solid var(--card-border);
            padding: 14px 16px;
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
            padding: 16px 20px;
            border-top: 1px solid var(--card-border);
            background: var(--bg-sidebar);
        }
        .input-box-wrapper {
            max-width: 900px;
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
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
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
            min-height: 24px;
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
        }
        .btn-send:hover { background: var(--accent-hover); }
        .btn-send:disabled { background: #334155; cursor: not-allowed; opacity: 0.6; }
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

        @media (max-width: 768px) {
            .sidebar { display: none; }
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
        </div>
        <button class="btn-new-chat" onclick="startNewChat()">
            <span>➕</span> محادثة جديدة
        </button>
        <div class="chat-history" id="chatHistoryList">
            <!-- Sessions populate dynamically -->
        </div>
        <div class="sidebar-footer">
            <div>🏛️ <strong>3,639</strong> كتاباً مفهرساً</div>
            <div>🤖 <strong>Gemini 2.5 Flash</strong> (صفر هلوسة)</div>
            <div style="margin-top: 8px;">
                <a href="https://t.me/ElantonyLibrarybot" target="_blank">📱 فتح بوت التيليجرام</a>
            </div>
        </div>
    </aside>

    <!-- Main Chat Container -->
    <main class="main-container">
        <!-- Top Navbar -->
        <div class="top-navbar">
            <div class="nav-title">
                <span>✠</span> رفيق وباحث مكتبة القديس أنطونيوس
            </div>
            <div class="live-badge">
                <div class="live-dot"></div>
                متصل بالمكتبة الدائمة
            </div>
        </div>

        <!-- Messages Area -->
        <div class="messages-area" id="messagesArea">
            <div class="messages-container" id="messagesContainer">
                <!-- Hero screen when no messages -->
                <div class="hero" id="heroScreen">
                    <div class="hero-badge">✠ المكتبة القبطية الأرثوذكسية الذكية</div>
                    <h2>كيف يمكنني مساعدتك في بحثك الكنسي اليوم؟</h2>
                    <p>أنا رفيقك البحثي المتخصص؛ أستحضر لك إجابات موثقة بالصفحة والمجلد من بطون 3,639 كتاباً ومرجعاً كنسياً بدون أي هلوسة.</p>
                    <div class="prompt-cards">
                        <div class="prompt-card" onclick="sendPrompt('ما هو مفهوم التجسد الإلهي عند القديس أثناسيوس الرسولي؟')">
                            📜 <strong>التجسد عند أثناسيوس</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">عقيدة تجسد الكلمة وتجديد الطبيعة</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('قارن بين إقامة السيد المسيح للموتى وإقامة إيليا النبي للموتى في تعليم الآباء')">
                            ⚖️ <strong>اللاهوت المقارن للقيامة</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">الفارق اللاهوتي والسلطان الذاتي</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('ما هي تعاليم القديس أنطونيوس كوكب البرية عن الصلاة الدائمة ونقاوة الفكر؟')">
                            🕊️ <strong>روحيات آباء البرية</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">حرب الأفكار وجهاد التوبة والهدوء</div>
                        </div>
                        <div class="prompt-card" onclick="sendPrompt('شرح طقس صلاة الصلح في القداس الباسيلي وأبعادها اللاهوتية')">
                            ⛪ <strong>طقوس ولتورجيا الكنيسة</strong>
                            <div style="font-size: 12px; color: var(--text-sub); margin-top: 4px;">المصالحة العظمى وقبلة المحبة والسلام</div>
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
                    placeholder="تفضل بكتابة سؤالك اللاهوتي أو طلبك البحثي هنا... (اضغط Enter للإرسال)"
                    rows="1"
                    onkeydown="handleKey(event)"
                    oninput="autoResize(this)"
                ></textarea>
                <button class="btn-send" id="btnSend" onclick="sendMessage()">
                    ➤
                </button>
            </div>
            <div class="input-disclaimer">
                المساعد مستند بالكامل إلى نصوص المراجع الكنسية المعتمدة ومحمي بضوابط التحقق الصارم من الاقتباس.
            </div>
        </div>
    </main>

    <script>
        let chatMessages = [];
        const messagesContainer = document.getElementById('messagesContainer');
        const heroScreen = document.getElementById('heroScreen');
        const chatInput = document.getElementById('chatInput');
        const btnSend = document.getElementById('btnSend');
        const messagesArea = document.getElementById('messagesArea');

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

        function startNewChat() {
            chatMessages = [];
            messagesContainer.innerHTML = '';
            messagesContainer.appendChild(heroScreen);
            heroScreen.style.display = 'block';
            chatInput.value = '';
            chatInput.focus();
        }

        function sendPrompt(text) {
            chatInput.value = text;
            sendMessage();
        }

        async function sendMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            if (heroScreen) heroScreen.style.display = 'none';

            // 1. Append User Message
            chatMessages.push({ role: 'user', content: text });
            appendMessageBubble('user', text);
            chatInput.value = '';
            chatInput.style.height = 'auto';
            btnSend.disabled = true;

            // 2. Append Typing Indicator
            const loadingId = appendLoadingBubble();
            scrollToBottom();

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: chatMessages })
                });

                removeLoadingBubble(loadingId);

                if (!response.ok) {
                    throw new Error('فشل الاتصال بمحرك الذكاء الاصطناعي');
                }

                const data = await response.json();
                const aiResponse = data.response;
                const citations = data.citations || [];

                chatMessages.push({ role: 'assistant', content: aiResponse });
                appendMessageBubble('assistant', aiResponse, citations);
                saveSessionHistory(text);

            } catch (err) {
                removeLoadingBubble(loadingId);
                appendMessageBubble('assistant', '⚠️ حدث خطأ أثناء معالجة السؤال: ' + err.message);
            } finally {
                btnSend.disabled = false;
                scrollToBottom();
                chatInput.focus();
            }
        }

        function appendMessageBubble(role, content, citations = []) {
            const row = document.createElement('div');
            row.className = `msg-row ${role === 'user' ? 'user' : 'ai'}`;

            const avatar = document.createElement('div');
            avatar.className = `msg-avatar ${role === 'user' ? 'user' : 'ai'}`;
            avatar.textContent = role === 'user' ? '👤' : '✠';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'msg-content';

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            if (role === 'assistant') {
                bubble.innerHTML = marked.parse(content);
            } else {
                bubble.textContent = content;
            }

            contentDiv.appendChild(bubble);

            // Append Citations section if available
            if (citations && citations.length > 0) {
                const citeSection = document.createElement('div');
                citeSection.className = 'citations-section';

                const citeHeader = document.createElement('div');
                citeHeader.className = 'citations-header';
                citeHeader.innerHTML = `<span>📚 الشواهد والمراجع المعتمدة (${citations.length})</span> <span>▼</span>`;
                
                const citeList = document.createElement('div');
                citeList.className = 'citations-list';

                citations.forEach((c, idx) => {
                    const item = document.createElement('div');
                    item.className = 'citation-item';
                    const pLabel = c.printed_page ? `صـ ${c.printed_page} (مطبوعة)` : `صـ ${c.page_number} (PDF)`;
                    item.innerHTML = `
                        <div class="citation-title">
                            <span>📖 ${idx + 1}. ${c.book_title}</span>
                            <span class="citation-badge">Tier ${c.authenticity_tier || 3}</span>
                        </div>
                        <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">
                            ✍️ ${c.author || 'آباء الكنيسة'} | 📄 ${pLabel}
                        </div>
                        <div class="citation-excerpt">❝ ${c.excerpt} ❞</div>
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
                        <span style="font-size: 12px; color: #94A3B8; margin-right: 8px;">جاري فحص المراجع وصياغة الإجابة الموثقة...</span>
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

        function saveSessionHistory(firstQuery) {
            try {
                let history = JSON.parse(localStorage.getItem('elantony_chat_sessions') || '[]');
                if (!history.includes(firstQuery)) {
                    history.unshift(firstQuery);
                    if (history.length > 20) history.pop();
                    localStorage.setItem('elantony_chat_sessions', JSON.stringify(history));
                    renderHistory();
                }
            } catch (e) {}
        }

        function renderHistory() {
            const list = document.getElementById('chatHistoryList');
            if (!list) return;
            try {
                const history = JSON.parse(localStorage.getItem('elantony_chat_sessions') || '[]');
                list.innerHTML = '';
                history.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'chat-history-item';
                    div.textContent = '💬 ' + item;
                    div.onclick = () => sendPrompt(item);
                    list.appendChild(div);
                });
            } catch (e) {}
        }

        window.onload = () => {
            renderHistory();
            chatInput.focus();
        };
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def web_portal():
    """Serves the interactive ChatGPT-like Coptic Research Portal."""
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
    """Single-turn grounded RAG Q&A."""
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    chunks = search_engine.search_fts5(q, limit=req.limit or 4)
    ai_provider = get_ai_provider()
    answer = ai_provider.generate_answer(q, chunks)

    return {
        "question": q,
        "answer": answer,
        "sources": [
            {"reference": c.source_reference, "page": c.page_number, "title": c.book_title}
            for c in chunks
        ]
    }


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """
    Multi-turn Conversational AI Endpoint.
    Maintains dialogue history while anchoring answers strictly in library citations.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="قائمة الرسائل فارغة")

    latest_msg = req.messages[-1].content.strip()
    if not latest_msg:
        raise HTTPException(status_code=400, detail="الاستفسار فارغ")

    # 1. Retrieve library context
    chunks = search_engine.search_fts5(latest_msg, limit=5)
    ai_provider = get_ai_provider()

    # 2. Conversational reasoning with past dialogue turns
    raw_history = [{"role": m.role, "content": m.content} for m in req.messages]
    if hasattr(ai_provider, "generate_chat_response"):
        answer = ai_provider.generate_chat_response(raw_history, chunks)
    else:
        answer = ai_provider.generate_answer(latest_msg, chunks)

    # 3. Format citations
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
            "excerpt": c.chunk_text[:300]
        })

    return {
        "response": answer,
        "citations": citations
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
