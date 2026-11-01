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
