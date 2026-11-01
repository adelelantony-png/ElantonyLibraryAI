# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Data Models & Entities
Defines strongly typed schemas for books, text chunks, bookmarks, and search logs.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BookEntity(BaseModel):
    """
    Core Book Metadata Entity.
    Matches the 16 standard specifications defined for ELANTONY LIBRARY AI.
    """
    book_id: Optional[int] = None
    title: str = Field(..., description="Book title in Arabic / Coptic / English")
    author: str = Field(default="غير محدد", description="Patristic father, bishop, or modern author")
    publisher: Optional[str] = Field(default=None, description="Publishing house or monastery")
    edition: Optional[str] = Field(default=None, description="Edition number or year")
    language: str = Field(default="ara", description="ara / cop / eng / gre / rus")
    category: str = Field(default="عام", description="Ecclesiastical category")
    file_format: str = Field(default="pdf", description="pdf / docx / epub")
    file_size: int = Field(default=0, description="Size in bytes")
    page_count: int = Field(default=0, description="Total page count")
    sha256: str = Field(..., description="Unique 64-char cryptographic hash")
    storage_provider: str = Field(default="local", description="local / telegram_channel / onedrive / unlimcloud")
    storage_reference: str = Field(default="", description="Path or cloud identifier (File ID / Item ID)")
    processing_status: str = Field(default="pending", description="pending / partial / completed / failed")
    ocr_status: str = Field(default="none", description="none / needed / in_progress / completed")
    indexing_status: str = Field(default="pending", description="pending / indexed / failed")
    quality_score: float = Field(default=0.0, description="Linguistic quality index 0.0 - 100.0")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChunkEntity(BaseModel):
    """Text Chunk for RAG and FTS5 Indexing."""
    sha256: str
    book_title: str
    page_number: int
    chunk_index: int
    source_reference: str
    chunk_text: str
    rank: Optional[float] = None


class UserBookmarkEntity(BaseModel):
    """User Saved Researches & Bookmarks (أبحاثي المحفوظة)."""
    bookmark_id: Optional[int] = None
    user_id: int
    book_sha256: str
    book_title: str
    page_number: int
    source_reference: str
    excerpt: str
    created_at: Optional[datetime] = None
