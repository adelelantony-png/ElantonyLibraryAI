# -*- coding: utf-8 -*-
"""
ArchiveMaster - ChurchAI Mobile Cloud & Telegram Server
Unified FastAPI server providing:
1. Mobile-First Progressive Web App (PWA) with voice search, pulpit/lectern mode, and WhatsApp sharing.
2. REST API for library search, Q&A, page reading, and stats.
3. Asynchronous Telegram Church AI Bot long-poller (zero public IP / webhook required).
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from modules import church_ai_config, book_discovery, rag_chunker, church_ai_reporter
from elantony.telegram.handlers import TelegramHandlerService
from elantony.database.repository import repo

logger = logging.getLogger("ChurchCloud")

# Global Telegram worker handle
telegram_task: Optional[asyncio.Task] = None


class AskRequest(BaseModel):
    question: str
    limit: Optional[int] = 5


class TelegramConfig(BaseModel):
    token: str


class TelegramBotWorker:
    """Asynchronous Telegram Bot Long-Poller (zero-webhook / zero-port forwarding)."""

    def __init__(self, token: str):
        self.token = token.strip()
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.handler_service = TelegramHandlerService(self.token)
        self.running = False
        self.last_update_id = 0

    async def send_message(self, client: httpx.AsyncClient, chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Sends a message back to a Telegram chat, optionally with inline keyboard."""
        try:
            url = f"{self.api_base}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            res = await client.post(url, json=payload, timeout=10.0)
            if res.status_code != 200:
                # Retry without markdown if formatting was invalid
                payload.pop("parse_mode", None)
                await client.post(url, json=payload, timeout=10.0)
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_document(self, client: httpx.AsyncClient, chat_id: int, file_path: str, caption: str = "") -> bool:
        """Uploads and sends a local PDF or document to Telegram chat."""
        if not os.path.exists(file_path):
            await self.send_message(client, chat_id, f"⚠️ لم يتم العثور على الملف في المسار: {os.path.basename(file_path)}")
            return False

        # Telegram bot limit is 50 MB
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 50.0:
            await self.send_message(
                client, chat_id,
                f"⚠️ حجم الكتاب كبير ({size_mb:.1f} MB) ويتجاوز حد تيليجرام للأقراص المباشرة (50 MB).\n"
                f"يمكنك قراءته أو تصفحه مباشرة عبر واجهة الموبايل PWA."
            )
            return False

        try:
            url = f"{self.api_base}/sendDocument"
            file_name = os.path.basename(file_path)
            await self.send_message(client, chat_id, f"⏳ جاري رفع وإرسال: «{file_name}»...")

            with open(file_path, "rb") as f:
                files = {"document": (file_name, f, "application/pdf")}
                data = {"chat_id": str(chat_id), "caption": caption[:1024]}
                res = await client.post(url, data=data, files=files, timeout=60.0)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            await self.send_message(client, chat_id, f"❌ حدث خطأ أثناء إرسال الملف: {str(e)}")
            return False

    async def answer_callback_query(self, client: httpx.AsyncClient, callback_id: str, text: Optional[str] = None):
        """Acknowledges callback button click."""
        try:
            url = f"{self.api_base}/answerCallbackQuery"
            payload = {"callback_query_id": callback_id}
            if text:
                payload["text"] = text
            await client.post(url, json=payload, timeout=5.0)
        except Exception:
            pass

    async def handle_callback_query(self, client: httpx.AsyncClient, cb: Dict[str, Any]) -> None:
        """Handles button clicks from inline keyboards."""
        cb_id = cb.get("id")
        data = cb.get("data", "")
        chat_id = cb.get("message", {}).get("chat", {}).get("id")

        if not chat_id or not data:
            return

        await self.answer_callback_query(client, cb_id, "جاري المعالجة...")

        # Action: pdf:<sha256>
        if data.startswith("pdf:"):
            sha256 = data.split("pdf:", 1)[1]
            import sqlite3
            db_path = book_discovery.get_db_path()
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT original_path, file_name FROM church_books WHERE sha256 = ?", (sha256,))
            row = cur.fetchone()
            conn.close()

            if row:
                pdf_path, fname = row
                await self.send_document(client, chat_id, pdf_path, caption=f"📖 {fname}")
            else:
                await self.send_message(client, chat_id, "⚠️ لم يتم العثور على مسار الكتاب في قاعدة البيانات.")

        # Action: page:<sha256>:<page_num>
        elif data.startswith("page:"):
            parts = data.split(":")
            if len(parts) >= 3:
                sha256, page_num = parts[1], int(parts[2])
                cfg = church_ai_config.load_config()
                txt_file = Path(cfg["paths"]["extracted_text"]) / f"{sha256}.txt"
                if txt_file.exists():
                    with open(txt_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    pages = rag_chunker.parse_pages_from_extracted_text(content)
                    target = next((p for p in pages if p["page_num"] == page_num), None)
                    if target and target["text"].strip():
                        await self.send_message(
                            client, chat_id,
                            f"📄 *نص الصفحة {page_num}:*\n\n{target['text'][:3500]}"
                        )
                    else:
                        await self.send_message(client, chat_id, f"⚠️ الصفحة {page_num} فارغة أو قيد الـ OCR.")

    async def handle_message(self, client: httpx.AsyncClient, message: Dict[str, Any]) -> None:
        """Processes an incoming Telegram message."""
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        user_name = message.get("from", {}).get("first_name", "يا حبيب المسيح")

        if not chat_id or not text:
            return

        # 1. Command: /start or /help
        if text.startswith("/start") or text.startswith("/help"):
            stats = church_ai_reporter.get_catalog_statistics()
            welcome = (
                f"✠ *أهلاً بك {user_name} في بوت مكتبة القديس أنطونيوس الذكية* ✠\n\n"
                f"📚 *المكتبة المركزية تضم:* `{stats['total_books']}` مجلداً ({stats['total_pages']:,} صفحة).\n\n"
                f"🔍 *طريقة الاستخدام:*\n"
                f"• اكتب أي موضوع أو كلمة للبحث الفوري في نصوص وبطون أمهات الكتب.\n"
                f"• اكتب: `/book الصلاة` للبحث في أسماء الكتب وتحميلها مباشرة PDF.\n"
                f"• اكتب: `/stats` لمعرفة إحصائيات المراجع وحالة الفهرسة.\n\n"
                f"🕊️ *أرسل استفسارك الآن وسأجيبك فوراً بالشواهد مع إمكانية تحميل الكتاب PDF بنقرة واحدة!*"
            )
            await self.send_message(client, chat_id, welcome)
            return

        # 2. Command: /stats
        if text.startswith("/stats"):
            stats = church_ai_reporter.get_catalog_statistics()
            stat_msg = (
                f"📊 *إحصائيات المكتبة الكنسية المحدثة:*\n"
                f"• إجمالي الكتب المسجلة: `{stats['total_books']}`\n"
                f"• الكتب الفريدة: `{stats['unique_books']}`\n"
                f"• إجمالي الصفحات: `{stats['total_pages']:,}`\n"
                f"• الحجم الإجمالي: `{stats['total_size_mb']:,} MB`\n"
                f"• متوسط جودة الاستخراج: `{stats['average_quality_score']} / 100`"
            )
            await self.send_message(client, chat_id, stat_msg)
            return

        # 3. Command: /book <title>
        if text.startswith("/book "):
            term = text.split("/book ", 1)[1].strip()
            import sqlite3
            db_path = book_discovery.get_db_path()
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT sha256, file_name, file_size 
                FROM church_books 
                WHERE file_name LIKE ? AND is_duplicate_of IS NULL 
                LIMIT 5
            """, (f"%{term}%",))
            books = cur.fetchall()
            conn.close()

            if not books:
                await self.send_message(client, chat_id, f"⚠️ لم يتم العثور على كتب تطابق: «{term}».")
                return

            keyboard = []
            msg_lines = [f"📚 *الكتب المطابقة لـ «{term}»:*\n"]
            for idx, (sha, fname, fsize) in enumerate(books, 1):
                size_mb = fsize / (1024 * 1024)
                msg_lines.append(f"{idx}. *{fname}* ({size_mb:.1f} MB)")
                keyboard.append([{"text": f"📥 تحميل: {fname[:30]}", "callback_data": f"pdf:{sha}"}])

            await self.send_message(client, chat_id, "\n".join(msg_lines), reply_markup={"inline_keyboard": keyboard})
            return

        # 4. Command: /search or generic text query (Semantic RAG)
        query = text
        if text.startswith("/search "):
            query = text.split("/search ", 1)[1].strip()
        elif text.startswith("/ask "):
            query = text.split("/ask ", 1)[1].strip()

        # Run FTS5 semantic search
        hits = rag_chunker.search_church_rag(query, limit=3)
        if not hits:
            reply = (
                f"🔍 *نتائج البحث عن:* «{query}»\n\n"
                f"⚠️ لم يتم العثور على شواهد مباشرة بهذه الكلمات. جرب كلمات مرادفة أو أكثر تحديداً."
            )
            await self.send_message(client, chat_id, reply)
            return

        reply_parts = [f"✠ *نتائج المراجع والشواهد لـ:* «{query}»\n"]
        keyboard = []
        for idx, h in enumerate(hits, 1):
            snippet = h["chunk_text"].strip().replace("\n", " ")[:300]
            ref = h["source_reference"]
            reply_parts.append(f"*{idx}. {ref}*\n❝ {snippet}... ❞\n")
            sha = h.get("sha256")
            pnum = h.get("page_number", 1)
            btn_row = []
            if sha:
                btn_row.append({"text": f"📥 تحميل كتاب {idx} (PDF)", "callback_data": f"pdf:{sha}"})
                btn_row.append({"text": f"📄 صفحة {pnum}", "callback_data": f"page:{sha}:{pnum}"})
            if btn_row:
                keyboard.append(btn_row)

        reply_parts.append("─────────────────\n_اضغط على الأزرار بالأسفل لتحميل الكتاب كاملاً PDF أو قراءة الصفحة._")
        full_reply = "\n".join(reply_parts)
        reply_markup = {"inline_keyboard": keyboard} if keyboard else None
        await self.send_message(client, chat_id, full_reply, reply_markup=reply_markup)

    async def run(self) -> None:
        """Continuous long-polling loop."""
        self.running = True
        logger.info("Telegram Bot worker started.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            while self.running:
                try:
                    url = f"{self.api_base}/getUpdates"
                    params = {
                        "offset": self.last_update_id + 1,
                        "timeout": 20
                    }
                    res = await client.get(url, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        updates = data.get("result", [])
                        for u in updates:
                            self.last_update_id = u["update_id"]
                            if "message" in u:
                                await self.handler_service.handle_message(client, u["message"])
                            elif "callback_query" in u:
                                await self.handler_service.handle_callback_query(client, u["callback_query"])
                    elif res.status_code == 401:
                        logger.error("Invalid Telegram Bot Token. Stopping poller.")
                        break
                    else:
                        await asyncio.sleep(2.0)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Telegram polling error: {e}")
                    await asyncio.sleep(3.0)
        logger.info("Telegram Bot worker stopped.")

    def stop(self) -> None:
        self.running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages background tasks (e.g. Telegram Bot) on server startup and shutdown."""
    global telegram_task
    cfg = church_ai_config.load_config()
    tg_token = cfg.get("cloud", {}).get("telegram_bot_token", "").strip()
    enable_bot = cfg.get("cloud", {}).get("enable_telegram_bot", True)

    if tg_token and enable_bot:
        bot = TelegramBotWorker(tg_token)
        app.state.telegram_bot = bot
        telegram_task = asyncio.create_task(bot.run())
        logger.info("Started background Telegram Bot worker.")
    else:
        app.state.telegram_bot = None

    yield

    if telegram_task and not telegram_task.done():
        if app.state.telegram_bot:
            app.state.telegram_bot.stop()
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ArchiveMaster ChurchAI Cloud",
    description="Mobile-Ready Church AI & Telegram Server",
    version="3.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REST API Endpoints
# ==========================================

@app.get("/health")
async def health_check():
    """Cloud Container Health Check Endpoint (Docker / Cloud Deployments)."""
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
            "app": "ELANTONY LIBRARY AI",
            "database_connected": db_healthy,
            "total_books": stats.get("total_books", 0),
            "indexed_chunks": stats.get("indexed_chunks", 0),
            "telegram_bot_active": getattr(app.state, "telegram_bot", None) is not None
        }
    )

@app.get("/api/status")
async def get_status():
    """Healthcheck and cloud status."""
    cfg = church_ai_config.load_config()
    tg_active = getattr(app.state, "telegram_bot", None) is not None
    return {
        "status": "online",
        "project": "ArchiveMaster ChurchAI",
        "version": "3.1.0",
        "telegram_bot_active": tg_active
    }


@app.get("/api/stats")
async def get_stats():
    """Aggregated church library statistics."""
    stats = church_ai_reporter.get_catalog_statistics()
    return stats


@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1), limit: int = 10):
    """Fast FTS5 search across all ecclesiastical chunks."""
    hits = rag_chunker.search_church_rag(q, limit=limit)
    return {"query": q, "total_hits": len(hits), "results": hits}


@app.post("/api/ask")
async def api_ask(req: AskRequest):
    """
    RAG Ecclesiastical Question Answering:
    Retrieves the most relevant passages and formats a coherent response with exact citations.
    """
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    hits = rag_chunker.search_church_rag(q, limit=req.limit or 5)
    if not hits:
        return {
            "answer": "لم أجد شواهد مباشرة في المراجع المفهرسة حالياً. يمكنك تجربة كلمات بحث أخرى أو التأكد من إتمام فهرسة كتب الموضوع.",
            "sources": []
        }

    # Synthesize structured theological answer
    sources = []
    excerpts_formatted = []
    for idx, h in enumerate(hits, 1):
        sources.append({
            "title": h["book_title"],
            "page": h["page_number"],
            "reference": h["source_reference"]
        })
        clean_text = h["chunk_text"].strip().replace("\n", " ")
        excerpts_formatted.append(f"• **{h['source_reference']}**: {clean_text[:220]}...")

    answer_text = (
        f"بناءً على الشواهد والفقرات المستخرجة من أمهات الكتب الكنسية:\n\n"
        + "\n\n".join(excerpts_formatted)
    )

    return {
        "question": q,
        "answer": answer_text,
        "sources": sources
    }


@app.get("/api/page")
async def api_get_page(sha256: str, page: int):
    """Retrieves full text of a specific book page from extracted files."""
    cfg = church_ai_config.load_config()
    txt_file = Path(cfg["paths"]["extracted_text"]) / f"{sha256}.txt"
    if not txt_file.exists():
        raise HTTPException(status_code=404, detail="Book text not found")

    with open(txt_file, "r", encoding="utf-8") as f:
        content = f.read()

    pages = rag_chunker.parse_pages_from_extracted_text(content)
    target = next((p for p in pages if p["page_num"] == page), None)
    if not target:
        raise HTTPException(status_code=404, detail="Page not found")

    return {"sha256": sha256, "page": page, "text": target["text"]}


@app.post("/api/config/telegram")
async def update_telegram_token(cfg_req: TelegramConfig):
    """Updates Telegram bot token live from the mobile web UI."""
    token = cfg_req.token.strip()
    cfg = church_ai_config.load_config()
    cfg.setdefault("cloud", {})["telegram_bot_token"] = token
    church_ai_config.save_config(cfg)
    return {"success": True, "message": "Telegram token saved. Restart server to activate."}


# ==========================================
# Mobile PWA Web Application
# ==========================================

@app.get("/manifest.json")
async def get_manifest():
    """PWA manifest for 'Add to Home Screen' functionality."""
    return JSONResponse({
        "name": "ArchiveMaster - المكتبة الكنسية",
        "short_name": "ChurchAI",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#1e293b",
        "icons": [
            {
                "src": "https://img.icons8.com/color/192/orthodox-cross.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "https://img.icons8.com/color/512/orthodox-cross.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })


@app.get("/sw.js")
async def get_service_worker():
    """Minimal PWA service worker."""
    js = """
    self.addEventListener('install', (e) => {
        self.skipWaiting();
    });
    self.addEventListener('fetch', (e) => {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    });
    """
    return HTMLResponse(content=js, media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
async def get_mobile_app():
    """Renders the comprehensive Mobile-First Church PWA."""
    html_content = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>✠ المكتبة الكنسية الذكية | ChurchAI</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e293b">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-card: #1e293b;
            --bg-elevated: #334155;
            --accent: #38bdf8;
            --accent-gold: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #475569;
            --success: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
        body { background: var(--bg-primary); color: var(--text-main); min-height: 100vh; padding-bottom: 75px; }
        
        /* Top App Bar */
        .header {
            position: sticky; top: 0; z-index: 50;
            background: rgba(30, 41, 59, 0.95);
            backdrop-filter: blur(8px);
            padding: 12px 16px;
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid var(--border);
        }
        .header-title { display: flex; align-items: center; gap: 8px; font-weight: bold; font-size: 1.1rem; color: var(--accent-gold); }
        .pill { background: rgba(16, 185, 129, 0.15); color: var(--success); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; display: flex; align-items: center; gap: 5px; }

        /* Container */
        .container { padding: 16px; max-width: 768px; margin: 0 auto; }

        /* Tabs Navigation */
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.2s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

        /* Search & Ask Box */
        .search-container { position: relative; margin-bottom: 16px; }
        .search-input {
            width: 100%; padding: 14px 45px 14px 45px;
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; color: var(--text-main); font-size: 1rem;
            outline: none; transition: border 0.2s;
        }
        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2); }
        .search-icon { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }
        .voice-btn { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--accent); font-size: 1.1rem; cursor: pointer; padding: 4px; }
        .voice-btn.recording { color: #ef4444; animation: pulse 1s infinite; }
        @keyframes pulse { 0% { transform: translateY(-50%) scale(1); } 50% { transform: translateY(-50%) scale(1.2); } 100% { transform: translateY(-50%) scale(1); } }

        /* Cards & Results */
        .result-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; padding: 14px; margin-bottom: 12px;
            transition: transform 0.15s ease;
        }
        .result-card:active { transform: scale(0.99); }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .ref-tag { background: rgba(56, 189, 248, 0.15); color: var(--accent); font-size: 0.8rem; font-weight: bold; padding: 3px 8px; border-radius: 6px; }
        .card-text { font-size: 0.95rem; line-height: 1.6; color: #cbd5e1; margin-bottom: 12px; }
        .card-actions { display: flex; gap: 8px; justify-content: flex-end; }
        .action-btn {
            background: var(--bg-elevated); border: none; color: var(--text-main);
            padding: 6px 12px; border-radius: 8px; font-size: 0.8rem;
            display: flex; align-items: center; gap: 6px; cursor: pointer;
        }
        .action-btn.whatsapp { background: #059669; color: white; }

        /* Bottom Tab Bar */
        .tab-bar {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(30, 41, 59, 0.98);
            border-top: 1px solid var(--border);
            display: flex; justify-content: space-around;
            padding: 8px 0; z-index: 50;
        }
        .tab-item {
            background: none; border: none; color: var(--text-muted);
            display: flex; flex-direction: column; align-items: center;
            gap: 4px; font-size: 0.75rem; cursor: pointer; flex: 1;
        }
        .tab-item.active { color: var(--accent); }
        .tab-item i { font-size: 1.2rem; }

        /* Lectern Mode */
        .lectern-box {
            background: #020617; border: 2px solid var(--accent-gold);
            border-radius: 16px; padding: 20px; margin-top: 10px;
        }
        .lectern-text { font-size: 1.4rem; line-height: 1.9; color: #fef08a; font-family: "Amiri", "Traditional Arabic", serif; }

        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; text-align: center; }
        .stat-val { font-size: 1.5rem; font-weight: bold; color: var(--accent-gold); }
        .stat-lbl { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
    </style>
</head>
<body>

    <!-- Header -->
    <header class="header">
        <div class="header-title">
            <i class="fa-solid fa-cross"></i>
            <span>ChurchAI Cloud</span>
        </div>
        <div class="pill" id="livePill">
            <i class="fa-solid fa-wifi"></i>
            <span>متصل</span>
        </div>
    </header>

    <!-- Main Container -->
    <main class="container">

        <!-- Tab 1: Instant Search -->
        <section id="tabSearch" class="tab-content active">
            <div class="search-container">
                <i class="fa-solid fa-magnifying-glass search-icon"></i>
                <input type="text" id="searchInput" class="search-input" placeholder="ابحث في بطون أمهات الكتب والشواهد..." onkeyup="handleSearchKey(event)">
                <button class="voice-btn" id="voiceBtn" onclick="toggleVoiceSearch()" title="بحث صوتي">
                    <i class="fa-solid fa-microphone"></i>
                </button>
            </div>
            <div id="searchResults">
                <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
                    <i class="fa-solid fa-book-open" style="font-size: 2.5rem; margin-bottom: 12px; color: var(--accent);"></i>
                    <p>اكتب أو انطق ما تبحث عنه للوصول المباشر لرقم الصفحة والاقتباس الكنسي.</p>
                </div>
            </div>
        </section>

        <!-- Tab 2: Ask AI (Q&A) -->
        <section id="tabAsk" class="tab-content">
            <div class="search-container">
                <i class="fa-solid fa-hands-praying search-icon" style="color: var(--accent-gold);"></i>
                <input type="text" id="askInput" class="search-input" placeholder="اطرح سؤالاً لاهوتياً أو كنسياً..." onkeyup="handleAskKey(event)">
                <button class="voice-btn" onclick="askQuestion()">
                    <i class="fa-solid fa-paper-plane"></i>
                </button>
            </div>
            <div id="askResultArea">
                <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
                    <i class="fa-solid fa-dove" style="font-size: 2.5rem; margin-bottom: 12px; color: var(--accent-gold);"></i>
                    <p>مساعد لاهوتي مدرب على كتب المكتبة يجيبك مع الشواهد الدقيقة.</p>
                </div>
            </div>
        </section>

        <!-- Tab 3: Pulpit / Lectern Mode -->
        <section id="tabLectern" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="color: var(--accent-gold);"><i class="fa-solid fa-candle-holder"></i> وضع المنبر والعظات</h3>
                <button class="action-btn" onclick="toggleWakeLock()"><i class="fa-solid fa-sun"></i> إبقاء الشاشة مضاءة</button>
            </div>
            <div class="lectern-box">
                <div class="lectern-text" id="lecternContent">
                    ✠ اختر أي اقتباس أو شاهد من نتائج البحث واضغط على «عرض على المنبر» لقراءته بوضوح تام وخط عريض أثناء إلقاء كلمتك أو الخدمة.
                </div>
            </div>
        </section>

        <!-- Tab 4: Cloud & Telegram Settings -->
        <section id="tabSettings" class="tab-content">
            <h3 style="margin-bottom: 12px; color: var(--accent);"><i class="fa-solid fa-chart-pie"></i> إحصائيات المكتبة</h3>
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card"><div class="stat-val" id="stBooks">-</div><div class="stat-lbl">إجمالي الكتب</div></div>
                <div class="stat-card"><div class="stat-val" id="stPages">-</div><div class="stat-lbl">إجمالي الصفحات</div></div>
            </div>

            <div class="result-card" style="margin-top: 20px;">
                <h4 style="color: #38bdf8; margin-bottom: 10px;"><i class="fa-brands fa-telegram"></i> ربط بوت تيليجرام</h4>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 10px;">
                    أدخل رمز التوكن (Bot Token) من BotFather لتفعيل البوت الخاص بك في ثوانٍ دون أي إعدادات خارجية.
                </p>
                <input type="text" id="tgTokenInput" class="search-input" style="padding: 10px; margin-bottom: 10px;" placeholder="123456789:ABCdefGhIJKlmNoP...">
                <button class="action-btn" onclick="saveTelegramToken()" style="background: var(--accent); width: 100%; justify-content: center;">
                    <i class="fa-solid fa-floppy-disk"></i> حفظ التوكن
                </button>
            </div>
        </section>

    </main>

    <!-- Bottom Tab Navigation -->
    <nav class="tab-bar">
        <button class="tab-item active" onclick="switchTab('tabSearch', this)">
            <i class="fa-solid fa-magnifying-glass"></i>
            <span>البحث</span>
        </button>
        <button class="tab-item" onclick="switchTab('tabAsk', this)">
            <i class="fa-solid fa-hands-praying"></i>
            <span>اسأل</span>
        </button>
        <button class="tab-item" onclick="switchTab('tabLectern', this)">
            <i class="fa-solid fa-book-bible"></i>
            <span>المنبر</span>
        </button>
        <button class="tab-item" onclick="switchTab('tabSettings', this); loadStats();">
            <i class="fa-solid fa-gear"></i>
            <span>الإعدادات</span>
        </button>
    </nav>

    <script>
        // Tab switching
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-item').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
        }

        // Search trigger
        function handleSearchKey(e) {
            if (e.key === 'Enter') triggerSearch();
        }

        async function triggerSearch() {
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;
            const resArea = document.getElementById('searchResults');
            resArea.innerHTML = '<div style="text-align: center; padding: 30px;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent);"></i></div>';

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=10`);
                const data = await res.json();
                if (!data.results || data.results.length === 0) {
                    resArea.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 30px;">لم يتم العثور على شواهد مطابقة.</div>';
                    return;
                }
                let html = '';
                data.results.forEach((r, idx) => {
                    const snippet = r.chunk_text.replace(/"/g, '&quot;');
                    html += `
                    <div class="result-card">
                        <div class="card-header">
                            <span class="ref-tag">${r.source_reference}</span>
                        </div>
                        <div class="card-text">${r.chunk_text}</div>
                        <div class="card-actions">
                            <button class="action-btn" onclick="sendToLectern('${r.source_reference}', \`${snippet}\`)"><i class="fa-solid fa-candle-holder"></i> للمنبر</button>
                            <button class="action-btn" onclick="copyQuote('${r.source_reference}', \`${snippet}\`)"><i class="fa-solid fa-copy"></i> نسخ</button>
                            <button class="action-btn whatsapp" onclick="shareWhatsApp('${r.source_reference}', \`${snippet}\`)"><i class="fa-brands fa-whatsapp"></i> واتساب</button>
                        </div>
                    </div>`;
                });
                resArea.innerHTML = html;
            } catch (err) {
                resArea.innerHTML = `<div style="color: #ef4444; padding: 20px;">خطأ في الاتصال: ${err.message}</div>`;
            }
        }

        // Ask AI
        function handleAskKey(e) {
            if (e.key === 'Enter') askQuestion();
        }

        async function askQuestion() {
            const q = document.getElementById('askInput').value.trim();
            if (!q) return;
            const area = document.getElementById('askResultArea');
            area.innerHTML = '<div style="text-align: center; padding: 30px;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--accent-gold);"></i><p style="margin-top: 10px; color: var(--text-muted);">جاري استخراج الشواهد الآبائية...</p></div>';

            try {
                const res = await fetch('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: q, limit: 4 })
                });
                const data = await res.json();
                let html = `
                <div class="result-card" style="border-color: var(--accent-gold);">
                    <h4 style="color: var(--accent-gold); margin-bottom: 8px;">✠ الإجابة والشواهد:</h4>
                    <div class="card-text" style="white-space: pre-line;">${data.answer}</div>
                    <div class="card-actions" style="margin-top: 12px;">
                        <button class="action-btn whatsapp" onclick="shareWhatsApp('سؤال: ${q}', \`${data.answer.replace(/"/g, '&quot;')}\`)"><i class="fa-brands fa-whatsapp"></i> مشاركة بالكامل</button>
                    </div>
                </div>`;
                area.innerHTML = html;
            } catch (err) {
                area.innerHTML = `<div style="color: #ef4444; padding: 20px;">تعذر استخراج الإجابة: ${err.message}</div>`;
            }
        }

        // Voice Search via Web Speech API
        function toggleVoiceSearch() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('المتصفح لا يدعم الإدخال الصوتي المباشر.');
                return;
            }
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRec();
            recognition.lang = 'ar-EG';
            const btn = document.getElementById('voiceBtn');
            btn.classList.add('recording');

            recognition.onresult = function(event) {
                const text = event.results[0][0].transcript;
                document.getElementById('searchInput').value = text;
                btn.classList.remove('recording');
                triggerSearch();
            };
            recognition.onerror = function() {
                btn.classList.remove('recording');
            };
            recognition.onend = function() {
                btn.classList.remove('recording');
            };
            recognition.start();
        }

        // Share & Copy utilities
        function copyQuote(ref, text) {
            const formatted = `❝ ${text} ❞\n📌 ${ref}`;
            navigator.clipboard.writeText(formatted).then(() => {
                alert('تم نسخ الاقتباس والشاهد بنجاح!');
            });
        }

        function shareWhatsApp(ref, text) {
            const formatted = `❝ ${text} ❞\n📌 ${ref}`;
            const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(formatted)}`;
            window.open(url, '_blank');
        }

        function sendToLectern(ref, text) {
            document.getElementById('lecternContent').innerHTML = `
                <div style="font-size: 1rem; color: var(--accent); margin-bottom: 10px;">${ref}</div>
                ❝ ${text} ❞
            `;
            switchTab('tabLectern', document.querySelectorAll('.tab-item')[2]);
        }

        // Screen WakeLock for pulpit mode
        let wakeLock = null;
        async function toggleWakeLock() {
            if ('wakeLock' in navigator) {
                try {
                    wakeLock = await navigator.wakeLock.request('screen');
                    alert('تم تفعيل وضع إبقاء الشاشة مضاءة على المنبر.');
                } catch (err) {
                    alert('تعذر تفعيل قفل الشاشة.');
                }
            } else {
                alert('خاصية إبقاء الشاشة غير مدعومة في هذا المتصفح.');
            }
        }

        // Stats loader
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('stBooks').innerText = data.total_books;
                document.getElementById('stPages').innerText = Number(data.total_pages).toLocaleString();
            } catch (e) {}
        }

        // Telegram token saver
        async function saveTelegramToken() {
            const token = document.getElementById('tgTokenInput').value.trim();
            if (!token) return;
            try {
                const res = await fetch('/api/config/telegram', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token })
                });
                const data = await res.json();
                alert(data.message);
            } catch (err) {
                alert('فشل حفظ التوكن: ' + err.message);
            }
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
