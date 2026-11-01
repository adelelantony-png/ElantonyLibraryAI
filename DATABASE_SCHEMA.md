# 🗄️ ELANTONY LIBRARY AI — Database Architecture & Schema Specification

## Overview
The data architecture for **ELANTONY LIBRARY AI** is engineered for high-concurrency read throughput, full-text Arabic and Coptic linguistic search, multi-cloud storage abstraction, and strict research bookmarking.

The system currently runs on **SQLite 3 (WAL Mode)** with zero configuration overhead, and includes an automated migration path to **PostgreSQL 15+** for distributed enterprise setups.

---

## 1. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    CHURCH_BOOKS ||--o{ CHURCH_CHUNKS_FTS : "indexes into"
    CHURCH_BOOKS ||--o{ USER_BOOKMARKS : "bookmarked by users"
    
    CHURCH_BOOKS {
        int id PK
        string sha256 UK "Unique 64-character hash"
        string file_name "Title or file designation"
        string original_path "Original filesystem path"
        int file_size "Size in bytes"
        int page_count "Total pages"
        string author "Patristic author / writer"
        string publisher "Monastery or printing house"
        string edition "Publication edition or year"
        string category "Ecclesiastical classification"
        string language_detected "ara / cop / eng / gre"
        string file_format "pdf / docx / epub"
        string storage_provider "local / telegram / onedrive / unlimcloud"
        string storage_reference "Cloud Item ID / Local Path"
        string extraction_status "pending / completed / failed"
        string ocr_status "none / needed / completed"
        string indexing_status "pending / indexed"
        int has_digital_text "Boolean flag"
        float quality_score "Linguistic quality (0.0 - 100.0)"
        datetime first_seen_at
        datetime last_processed_at
    }

    CHURCH_CHUNKS_FTS {
        string sha256 UNINDEXED "Foreign reference to book"
        string book_title "Searchable book title"
        int page_number UNINDEXED "Specific page number"
        int chunk_index UNINDEXED "Chunk offset within page"
        string source_reference "Formatted citation"
        string chunk_text "Indexed textual content"
    }

    USER_BOOKMARKS {
        int id PK
        int user_id "Telegram User ID"
        string book_sha256 "Foreign reference to book"
        string book_title "Title snapshot"
        int page_number "Referenced page"
        string source_reference "Full citation string"
        string excerpt "Saved textual passage"
        datetime created_at
    }

    SEARCH_TELEMETRY {
        int id PK
        int user_id "Telegram User ID"
        string query "Searched term"
        int results_count "Matches retrieved"
        datetime created_at
    }
```

---

## 2. The 16 Core Book Attributes Specification

Every book record in `church_books` conforms to the 16 core attributes designed for ELANTONY LIBRARY AI:

| # | Attribute Name | Data Type | Default | Description |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `id` | `INTEGER` | AUTOINCREMENT | Primary surrogate key. |
| **2** | `file_name` / `title` | `TEXT` | NOT NULL | Title of the work in Arabic, Coptic, or English. |
| **3** | `author` | `TEXT` | `'غير محدد'` | Patristic father, bishop, scholar, or monastic writer. |
| **4** | `publisher` | `TEXT` | `NULL` | Monastery press, patriarchate printing house, or publisher. |
| **5** | `edition` | `TEXT` | `NULL` | Edition number, print year, or publication details. |
| **6** | `language_detected` | `TEXT` | `'ara'` | Primary language (`ara`, `cop`, `eng`, `gre`). |
| **7** | `category` | `TEXT` | `'عام'` | Ecclesiastical domain (e.g., أبائيات, لاهوت عقيدي, طقوس). |
| **8** | `file_format` | `TEXT` | `'pdf'` | Document container format (`pdf`, `docx`, `epub`). |
| **9** | `file_size` | `INTEGER` | `0` | File volume in bytes. |
| **10** | `page_count` | `INTEGER` | `0` | Total verified document pages. |
| **11** | `sha256` | `TEXT` | UNIQUE | Cryptographic fingerprint for integrity and deduplication. |
| **12** | `storage_provider` | `TEXT` | `'local'` | Storage adapter (`local`, `telegram`, `onedrive`, `unlimcloud`). |
| **13** | `storage_reference`| `TEXT` | `NULL` | File path, Telegram Document ID, or OneDrive Item ID. |
| **14** | `extraction_status` | `TEXT` | `'pending'` | Ingestion stage (`pending`, `completed`, `failed`). |
| **15** | `ocr_status` | `TEXT` | `'none'` | OCR requirement (`none`, `needed`, `in_progress`, `completed`). |
| **16** | `indexing_status` | `TEXT` | `'pending'` | Full-text FTS5 status (`pending`, `indexed`, `failed`). |

---

## 3. SQLite DDL Schema (Production Implementation)

```sql
-- 1. Main Church Books Catalog
CREATE TABLE IF NOT EXISTS church_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT UNIQUE,
    original_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mod_time TEXT,
    page_count INTEGER DEFAULT 0,
    author TEXT DEFAULT 'غير محدد',
    publisher TEXT,
    edition TEXT,
    category TEXT DEFAULT 'عام',
    language_detected TEXT DEFAULT 'ara',
    file_format TEXT DEFAULT 'pdf',
    storage_provider TEXT DEFAULT 'local',
    storage_reference TEXT,
    extraction_status TEXT DEFAULT 'pending',
    ocr_status TEXT DEFAULT 'none',
    indexing_status TEXT DEFAULT 'pending',
    has_digital_text INTEGER DEFAULT 0,
    pages_needing_ocr TEXT DEFAULT '[]',
    quality_score REAL DEFAULT 0.0,
    extracted_text_path TEXT,
    processed_text_path TEXT,
    is_duplicate_of TEXT,
    error_message TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP
);

-- Fast Indexing
CREATE INDEX IF NOT EXISTS idx_church_books_sha ON church_books(sha256);
CREATE INDEX IF NOT EXISTS idx_church_books_status ON church_books(extraction_status);
CREATE INDEX IF NOT EXISTS idx_church_books_category ON church_books(category);
CREATE INDEX IF NOT EXISTS idx_church_books_author ON church_books(author);

-- 2. Virtual Full-Text Search Table (FTS5 with Unicode61 Tokenizer)
CREATE VIRTUAL TABLE IF NOT EXISTS church_chunks_fts USING fts5(
    sha256 UNINDEXED,
    book_title,
    page_number UNINDEXED,
    chunk_index UNINDEXED,
    source_reference,
    chunk_text,
    tokenize = 'unicode61'
);

-- 3. User Saved Researches & Bookmarks (أبحاثي المحفوظة)
CREATE TABLE IF NOT EXISTS user_bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_sha256 TEXT NOT NULL,
    book_title TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    source_reference TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);

-- 4. Search Telemetry
CREATE TABLE IF NOT EXISTS search_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query TEXT NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. SQLite Optimization Settings (PRAGMA)

When opening connections in `elantony/database/connection.py`, the following high-performance flags are enforced:

```sql
PRAGMA journal_mode = WAL;          -- Concurrent multi-reader, single-writer
PRAGMA synchronous = NORMAL;         -- 2-3x speedup with safe persistence
PRAGMA cache_size = -64000;          -- 64 MB in-memory page cache
PRAGMA busy_timeout = 5000;          -- 5-second backoff on write locks
PRAGMA foreign_keys = ON;            -- Referential integrity enforcement
```

---

## 5. Enterprise PostgreSQL Migration Path (Cloud Ready)

For high-concurrency environments deploying a managed database (e.g., Supabase, AWS RDS, Neon):

```sql
-- PostgreSQL 15+ Schema
CREATE TABLE church_books (
    id BIGSERIAL PRIMARY KEY,
    sha256 VARCHAR(64) UNIQUE NOT NULL,
    original_path TEXT NOT NULL,
    file_name VARCHAR(512) NOT NULL,
    file_size BIGINT NOT NULL,
    mod_time TIMESTAMP WITH TIME ZONE,
    page_count INTEGER DEFAULT 0,
    author VARCHAR(256) DEFAULT 'غير محدد',
    publisher VARCHAR(256),
    edition VARCHAR(128),
    category VARCHAR(128) DEFAULT 'عام',
    language_detected VARCHAR(16) DEFAULT 'ara',
    file_format VARCHAR(16) DEFAULT 'pdf',
    storage_provider VARCHAR(32) DEFAULT 'local',
    storage_reference TEXT,
    extraction_status VARCHAR(32) DEFAULT 'pending',
    ocr_status VARCHAR(32) DEFAULT 'none',
    indexing_status VARCHAR(32) DEFAULT 'pending',
    has_digital_text BOOLEAN DEFAULT FALSE,
    pages_needing_ocr JSONB DEFAULT '[]'::jsonb,
    quality_score REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE church_chunks (
    id BIGSERIAL PRIMARY KEY,
    sha256 VARCHAR(64) REFERENCES church_books(sha256) ON DELETE CASCADE,
    book_title VARCHAR(512) NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    source_reference VARCHAR(512) NOT NULL,
    chunk_text TEXT NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('arabic', chunk_text)) STORED
);
CREATE INDEX idx_church_chunks_fts ON church_chunks USING gin(search_vector);
```
