# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Web & Cloud REST API
Provides cloud health checks, Mobile PWA routes, and search endpoints.
"""

import asyncio
from typing import Dict, Any, Optional
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
    """Manages Telegram Bot worker on application startup and shutdown."""
    global bot_task, bot_engine
    if settings.telegram_bot_token:
        bot_engine = TelegramBotEngine()
        bot_task = asyncio.create_task(bot_engine.run())
        logger.info("Telegram Bot worker launched in background task.")
    else:
        logger.info("No Telegram Bot token provided; running in web-only mode.")

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
    description="Ecclesiastical Smart Library & RAG Cloud Platform",
    version="2.0.0",
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



WEB_PORTAL_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✠ ELANTONY LIBRARY AI - المكتبة القبطية الأرثوذكسية الذكية</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0B0F19;
            --bg-card: #151D2E;
            --bg-card-hover: #1E293B;
            --accent: #3B82F6;
            --accent-hover: #2563EB;
            --gold: #F59E0B;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --border: #334155;
            --radius: 12px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); line-height: 1.6; min-height: 100vh; padding: 24px 16px; }
        .container { max-width: 960px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 32px; padding: 20px 0; }
        .logo-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(59, 130, 246, 0.15); border: 1px solid var(--accent); color: var(--accent); padding: 6px 16px; border-radius: 9999px; font-size: 14px; font-weight: 700; margin-bottom: 16px; }
        h1 { font-size: 2.2rem; font-weight: 800; margin-bottom: 8px; color: #FFF; }
        .subtitle { color: var(--text-sub); font-size: 1.1rem; max-width: 650px; margin: 0 auto 16px auto; }
        .stats-bar { display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; margin-top: 16px; }
        .stat-item { background: var(--bg-card); border: 1px solid var(--border); padding: 8px 18px; border-radius: 8px; font-size: 13px; color: var(--text-sub); }
        .stat-item strong { color: var(--gold); font-size: 15px; }

        .search-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 24px; }
        .input-group { display: flex; gap: 10px; margin-bottom: 14px; }
        .search-input { flex: 1; background: #0F172A; border: 1px solid var(--border); color: #FFF; padding: 14px 18px; border-radius: 8px; font-size: 16px; outline: none; transition: 0.2s; }
        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
        .btn-search { background: var(--accent); color: #FFF; border: none; padding: 0 28px; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer; transition: 0.2s; }
        .btn-search:hover { background: var(--accent-hover); }

        .pills { display: flex; gap: 8px; flex-wrap: wrap; }
        .pill { background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--text-sub); padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: 0.2s; }
        .pill:hover { background: rgba(59, 130, 246, 0.2); border-color: var(--accent); color: #FFF; }

        .results { margin-top: 24px; }
        .result-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; margin-bottom: 14px; transition: 0.2s; }
        .result-card:hover { border-color: var(--accent); background: var(--bg-card-hover); }
        .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px; }
        .book-title { font-weight: 700; color: #60A5FA; font-size: 16px; }
        .page-badge { background: rgba(245, 158, 11, 0.15); color: var(--gold); border: 1px solid rgba(245, 158, 11, 0.3); padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .snippet-text { color: #CBD5E1; font-size: 14px; line-height: 1.7; border-right: 3px solid var(--accent); padding-right: 12px; }

        .bot-banner { text-align: center; margin-top: 40px; padding: 24px; background: rgba(59, 130, 246, 0.08); border: 1px dashed var(--accent); border-radius: var(--radius); }
        .btn-bot { display: inline-block; background: #0088cc; color: white; padding: 10px 24px; border-radius: 8px; text-decoration: none; font-weight: 700; margin-top: 12px; transition: 0.2s; }
        .btn-bot:hover { background: #0077b5; }
        .loading { display: none; text-align: center; padding: 24px; color: var(--text-sub); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-badge">✠ ELANTONY LIBRARY AI</div>
            <h1>المكتبة القبطية الأرثوذكسية الذكية</h1>
            <p class="subtitle">محرك البحث المعرفي والذكاء الاصطناعي التوليدي عبر 3,656 كتاباً ومئات الآلاف من المقتطفات الآبائية الموثقة</p>
            <div class="stats-bar" id="statsBar">
                <div class="stat-item">📚 إجمالي الكتب: <strong>3,656</strong></div>
                <div class="stat-item">📑 المقاطع المفهرسة: <strong id="chunkCount">311,634+</strong></div>
                <div class="stat-item">⛪ التراث: <strong>قبطي أرثوذكسي أصيل</strong></div>
            </div>
        </header>

        <div class="search-container">
            <div class="input-group">
                <input type="text" id="searchInput" class="search-input" placeholder="ابحث في بطون الكتب أو اسأل سؤالاً لاهوتياً (مثال: طوفان نوح، تجسد الكلمة)..." autofocus>
                <button class="btn-search" onclick="performSearch()">بحث</button>
            </div>
            <div class="pills">
                <span style="font-size: 12px; color: var(--text-sub); align-self: center;">أمثلة سريعة:</span>
                <span class="pill" onclick="quickSearch('طوفان نوح هل كان عالميا')">طوفان نوح</span>
                <span class="pill" onclick="quickSearch('تجسد الكلمة اثناسيوس')">تجسد الكلمة</span>
                <span class="pill" onclick="quickSearch('سر الافخارستيا والتناول')">سر الافخارستيا</span>
                <span class="pill" onclick="quickSearch('أقوال الآباء عن الصلاة الدائمة')">الصلاة الدائمة</span>
                <span class="pill" onclick="quickSearch('تفسير رسالة رومية')">تفاسير العهد الجديد</span>
            </div>
        </div>

        <div class="loading" id="loadingIndicator">
            ⏳ جاري البحث في فهارس المكتبة الشاملة...
        </div>

        <div class="results" id="resultsContainer"></div>

        <div class="bot-banner">
            <h3>🤖 تود الوصول لكامل المكتبة عبر تيليجرام 24/7؟</h3>
            <p style="color: var(--text-sub); font-size: 14px; margin-top: 4px;">تحدث مع المساعد الذكي، وتصفح الفهرس التفاعلي، واقرأ الكتب على هاتفك مباشرة.</p>
            <a href="https://t.me/ElantonyLibrarybot" target="_blank" class="btn-bot">💬 فتح البوت في تيليجرام @ElantonyLibrarybot</a>
        </div>
    </div>

    <script>
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                if (res.ok) {
                    const data = await res.json();
                    if (data.indexed_chunks) {
                        document.getElementById('chunkCount').innerText = Number(data.indexed_chunks).toLocaleString() + '+';
                    }
                }
            } catch(e) {}
        }
        loadStats();

        function quickSearch(q) {
            document.getElementById('searchInput').value = q;
            performSearch();
        }

        document.getElementById('searchInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') performSearch();
        });

        async function performSearch() {
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;

            const container = document.getElementById('resultsContainer');
            const loading = document.getElementById('loadingIndicator');

            container.innerHTML = '';
            loading.style.display = 'block';

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=8`);
                loading.style.display = 'none';

                if (!res.ok) throw new Error('Search failed');
                const data = await res.json();

                if (!data.results || data.results.length === 0) {
                    container.innerHTML = `
                        <div class="result-card" style="text-align: center; color: var(--text-sub);">
                            🔍 لم يتم العثور على مقاطع نصية مباشرة تطابق بحثك. جرب كلمات بديلة أو مرادفات لاهوتية.
                        </div>`;
                    return;
                }

                data.results.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'result-card';
                    card.innerHTML = `
                        <div class="result-header">
                            <span class="book-title">📖 ${item.book_title || 'مرجع كنسي'}</span>
                            <span class="page-badge">صـ ${item.page_number || '1'}</span>
                        </div>
                        <div class="snippet-text">"${item.chunk_text}"</div>
                    `;
                    container.appendChild(card);
                });
            } catch (err) {
                loading.style.display = 'none';
                container.innerHTML = `<div class="result-card" style="color: #EF4444;">حدث خطأ أثناء البحث: ${err.message}</div>`;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def web_portal():
    """Serves the interactive Arabic Mobile & Web search portal."""
    return HTMLResponse(content=WEB_PORTAL_HTML)


@app.get("/health")
async def health_check():
    """Cloud Container Health Check Endpoint (Docker / Kubernetes / Cloud Providers)."""
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
            "indexed_chunks": stats.get("indexed_chunks", 0),
            "telegram_worker_active": bool(bot_task and not bot_task.done())
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
    """Grounded RAG Q&A."""
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



@app.get("/api/v1/admin/dashboard")
async def admin_dashboard():
    """Returns comprehensive administrative metrics, tier breakdown, and source distribution."""
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
