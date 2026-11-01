# ⛪ ELANTONY LIBRARY AI (مكتبة الأنبا أنطونيوس الذكية)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-38%2F38%20passed-brightgreen.svg)]()
[![Bot](https://img.shields.io/badge/Telegram-@ElantonyLibrarybot-blue?logo=telegram)](https://t.me/ElantonyLibrarybot)

**ELANTONY LIBRARY AI** is an enterprise-grade ecclesiastical AI and digital library management platform engineered to catalog, index, and query over **7,200 theological and patristic volumes (~50 GB)**. 

Accessible via Telegram (`@ElantonyLibrarybot`), the platform delivers grounded theological answers, precise book citations, multi-format digital search, and cloud storage streaming with zero hallucinations.

---

## 🌟 Key Capabilities

1. **🏛️ Master 9-Section Telegram Interface:**
   - `🤖 المساعد الذكي`: Grounded theological Q&A with strict citations.
   - `📚 البحث في المكتبة`: Instant full-text FTS5 search across all indexed books.
   - `📖 اسأل كتابًا`: Scoped question-answering confined to a specific chosen volume.
   - `⛪ أقوال الآباء`: Curated patristic excerpts on prayer, asceticism, and virtues.
   - `🔍 البحث حسب المؤلف`: Filter by fathers (Athanasius, Cyril, Shenouda III, Antony, Jerome, Matta El-Meskeen).
   - `📂 تصفح التصنيفات`: Browse dogmatics, patristics, bible commentaries, and liturgy.
   - `📑 أبحاثي المحفوظة`: Personal user bookmarks and saved research excerpts.
   - `⚙️ الإعدادات`: User preferences, rate limit telemetry, and system stats.
   - `ℹ️ حول المكتبة`: Library history, technical specifications, and credits.

2. **🛡️ Zero-Hallucination Grounded AI:**
   - Every answer is synthesized directly from verified textual chunks.
   - Strict citation requirements: `[كتاب]`, `[المؤلف]`, `[رقم الصفحة]`, and `[النص الأصلي]`.
   - Refusal to fabricate when sources do not contain evidence.

3. **☁️ Multi-Cloud Storage Architecture:**
   - **Local Storage:** High-speed direct disk I/O.
   - **Microsoft OneDrive (1 TB):** Streaming on-demand book distribution.
   - **Telegram Private Channel:** Distributed CDN storage with zero hosting overhead.
   - **UnlimCloud Adapter:** Auxiliary storage gateway.

4. **⚡ High-Performance Search & Database:**
   - SQLite 3 running in **WAL mode** (Write-Ahead Logging) with `PRAGMA synchronous = NORMAL`.
   - **FTS5** (Full-Text Search 5) with `unicode61` tokenizer supporting Arabic diacritics and Coptic script.

5. **🔒 Security & DoS Protection:**
   - Telegram Bot Token isolated in `.env` (sanitized `.env.example`, gitignored).
   - In-memory sliding-window rate limiter per user.
   - User ID whitelisting and role-based administrative access control.

---

## 📁 Project Architecture

```
ArchiveMaster/
├── elantony/                     # Core Modular Monolith Package
│   ├── core/                    # Config, Security, Rate Limiter, Logging
│   ├── database/                # SQLite WAL Connection, Models, Repository
│   ├── storage/                 # Local, Telegram Channel, OneDrive Adapters
│   ├── search/                  # FTS5 Full-Text & Scoped Search Engine
│   ├── ai/                      # Grounded Rule-Based & Gemini AI Providers
│   ├── telegram/                # Keyboards, Action Handlers, Long Poller
│   └── web/                     # FastAPI App & Health Check (/health)
├── books/                       # Local PDF volumes and manifests
├── config/                      # Configuration templates
├── database/                    # Database storage artifacts
├── scripts/                     # Automation and cloud startup scripts
├── tests/                       # Automated test suite (38 passing tests)
├── Dockerfile                   # Multi-stage production container
├── docker-compose.yml           # Multi-service cloud compose stack
├── ARCHITECTURE.md              # Architectural design document
├── PROJECT_AUDIT_REPORT.md      # Comprehensive 13-dimension codebase audit
├── DEVELOPMENT_ROADMAP.md       # Phased roadmap to 7,200 books
├── SECURITY_REPORT.md           # Threat model & token isolation report
├── DEPLOYMENT_GUIDE.md          # 24/7 autonomous cloud hosting guide
├── DATABASE_SCHEMA.md           # 16-attribute schema & ERD specification
└── .env.example                 # Sanitized environment template
```

---

## 🚀 Quickstart Guide

### 1. Local Development (Windows / Linux)
```bash
# Clone the repository
git clone https://github.com/YOUR_ORGANIZATION/ArchiveMaster.git
cd ArchiveMaster

# Configure environment
cp .env.example .env
# Edit .env and insert your TELEGRAM_BOT_TOKEN

# Install dependencies
pip install -r requirements.txt

# Run the test suite
pytest tests/

# Launch the operational server & bot
python -m modules.church_cloud_server
```

### 2. Cloud Deployment (Docker Compose)
```bash
# Build and start in background
docker compose up -d --build

# Verify container health
curl -s http://localhost:8000/health
```

---

## 🧪 Testing

The platform includes full coverage across core configuration, security sanitization, rate limiting, database operations, storage adapters, search engines, and keyboards:

```bash
pytest tests/ -v
```
Output:
```
======================= 38 passed, 7 warnings in 4.11s ========================
```

---

## 📜 Documentation Index
- [Detailed System Architecture](ARCHITECTURE.md)
- [Comprehensive Audit Report](PROJECT_AUDIT_REPORT.md)
- [Development Roadmap](DEVELOPMENT_ROADMAP.md)
- [Security & Threat Model](SECURITY_REPORT.md)
- [24/7 Cloud Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Database Schema & ERD](DATABASE_SCHEMA.md)
