# ==============================================================================
# ELANTONY LIBRARY AI - Multi-Stage Production Dockerfile
# Optimized for Hugging Face Spaces (24/7 Free CPU), Koyeb, Render & Local Docker.
# ==============================================================================

# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    python -m pip install --prefix=/install -r requirements.txt && \
    python -m pip install --prefix=/install fastapi uvicorn httpx python-dotenv qrcode pydantic

# Stage 2: Final Lightweight Runtime
FROM python:3.11-slim AS runtime

# Install runtime dependencies: Tesseract OCR + Arabic/English language packs + OpenCV dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Configure user 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_PORT=7860 \
    APP_HOST=0.0.0.0

WORKDIR $HOME/app

# Copy application codebase
COPY --chown=user:user . $HOME/app

# Ensure directories for storage, logs, and database exist with correct permissions
RUN mkdir -p $HOME/app/extracted_text $HOME/app/processed_text $HOME/app/reports $HOME/app/logs $HOME/app/books/local $HOME/app/database

# Expose cloud ports (7860 for Hugging Face, 8000 for standard Docker)
EXPOSE 7860
EXPOSE 8000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/health || curl -f http://localhost:8000/health || exit 1

# Launch the unified ELANTONY Cloud & Telegram Server
CMD ["python", "scripts/run_cloud_bot.py"]
