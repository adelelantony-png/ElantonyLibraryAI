# 🚀 ELANTONY LIBRARY AI — 24/7 Cloud Deployment Guide

## Overview
This guide provides complete instructions for deploying **ELANTONY LIBRARY AI** (`@ElantonyLibrarybot`) to an autonomous, high-availability cloud environment that runs 24 hours a day, 7 days a week, completely independent of personal hardware.

---

## 1. Hosting Architecture & Free-Tier Comparison

To run 24/7 with zero to negligible cost while managing 7,200 books (~50 GB) and OCR/RAG workloads, here is the technical evaluation of viable cloud providers:

| Provider & Tier | Specifications | Cost | Storage Suitability | Recommended Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Oracle Cloud Always Free (ARM Ampere)** | 4 OCPUs, 24 GB RAM, 200 GB NVMe Storage | **$0 / month (Free Forever)** | **Exceptional (200 GB fits entire library)** | 🥇 **Primary Recommendation** |
| **Hetzner Cloud (CPX21)** | 3 AMD vCPUs, 4 GB RAM, 80 GB NVMe | ~€5.40 / month | High (80 GB fits active library) | 🥈 **Best Low-Cost Commercial VPS** |
| **Contabo Cloud VPS S** | 4 vCPUs, 8 GB RAM, 50 GB NVMe / 200 GB SSD | ~$5.50 / month | Exceptional (Large storage) | 🥈 **Best Cost-Per-Gigabyte VPS** |
| **Render / Fly.io / Railway** | 0.5–1 vCPU, 512 MB–1 GB RAM | Free / $5 / month | Low (Ephemeral / Persistent disk paid per GB) | ⚠️ **Suitable for Web API only, not full 50 GB local PDF archive** |

> [!TIP]
> **Recommended Strategy:**
> Deploy the application container on **Oracle Cloud Always Free** or a **Hetzner / Contabo VPS**. Store the authoritative PDF master archive on **Microsoft OneDrive (1 TB)**, streaming or caching accessed files to the server's local disk as needed.

---

## 2. Prerequisites & Server Setup

### OS & Base Packages (Ubuntu 22.04 / 24.04 LTS)
Connect to your remote cloud server via SSH:
```bash
ssh ubuntu@YOUR_SERVER_IP
```

Update system and install foundational dependencies:
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl wget tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng libgl1 poppler-utils sqlite3
```

Install Docker & Docker Compose:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and log back in for docker group to take effect
```

---

## 3. Deployment Method A: Docker Compose (Recommended)

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/YOUR_ORGANIZATION/ArchiveMaster.git /opt/elantony-ai
cd /opt/elantony-ai

# Copy production environment configuration
cp .env.example .env
nano .env
```

Ensure your `.env` contains:
```ini
APP_ENV=production
APP_NAME="ELANTONY LIBRARY AI"
APP_PORT=8000
APP_HOST=0.0.0.0

# Telegram Bot Credentials (Stored securely)
TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN
TELEGRAM_MODE=polling

# Security & Access Control
ALLOWED_TELEGRAM_USERS=12345678,87654321
ADMIN_TELEGRAM_USERS=12345678
RATE_LIMIT_PER_MINUTE=30

# Storage
DEFAULT_STORAGE_PROVIDER=local
ONEDRIVE_ROOT_FOLDER=ElantonyLibrary
```

### Step 2: Build & Start Container
```bash
docker compose build --no-cache
docker compose up -d
```

### Step 3: Verify Container Health
```bash
docker compose ps
docker compose logs -f church-ai
curl -s http://localhost:8000/health | jq .
```
Expected output:
```json
{
  "status": "healthy",
  "app_name": "ELANTONY LIBRARY AI",
  "environment": "production",
  "telegram_mode": "polling",
  "storage_provider": "local"
}
```

---

## 4. Deployment Method B: Native Systemd Service (Low Overhead)

If running directly on the Linux host without Docker:

### Step 1: Setup Python Virtual Environment
```bash
sudo mkdir -p /opt/elantony-ai
cd /opt/elantony-ai
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Create Systemd Service File
```bash
sudo nano /etc/systemd/system/elantony.service
```
Insert the following configuration:
```ini
[Unit]
Description=Elantony Library AI Telegram Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/elantony-ai
EnvironmentFile=/opt/elantony-ai/.env
ExecStart=/opt/elantony-ai/venv/bin/python -m modules.church_cloud_server
Restart=always
RestartSec=10
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

### Step 3: Enable & Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable elantony.service
sudo systemctl start elantony.service
sudo systemctl status elantony.service
```

---

## 5. Automated Health Monitoring & Alerting

### Uptime Monitoring (Zero-Cost via UptimeRobot / Cron)
1. **Free UptimeRobot Account:** Add an HTTP(s) monitor pointing to:
   `http://YOUR_SERVER_IP:8000/health` (Interval: every 5 minutes).
2. **Local Watchdog Cron Job:**
   Add to `crontab -e`:
   ```bash
   */10 * * * * curl -sSf http://localhost:8000/health > /dev/null || systemctl restart elantony.service
   ```

---

## 6. Database Backup & Disaster Recovery

SQLite databases running in WAL mode require safe snapshotting before remote replication.

### Create Backup Script (`scripts/backup_database.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/opt/elantony-ai/Backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Safe SQLite snapshot
sqlite3 /opt/elantony-ai/file_archive.db ".backup '$BACKUP_DIR/file_archive_$TIMESTAMP.db'"

# Keep only last 14 backups locally
find "$BACKUP_DIR" -type f -name "*.db" -mtime +14 -delete

echo "Backup completed: file_archive_$TIMESTAMP.db"
```
Make executable and schedule in cron:
```bash
chmod +x /opt/elantony-ai/scripts/backup_database.sh
# Run nightly at 3:00 AM
0 3 * * * /opt/elantony-ai/scripts/backup_database.sh
```

---

## 7. Troubleshooting Guide

| Issue | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Telegram Conflict: 409** | Two bot polling instances running simultaneously. | Ensure local development script is terminated before cloud startup (`pkill -f church_cloud_server`). |
| **High Memory / OOM during OCR** | Simultaneous processing of large scanned PDFs. | Limit OCR worker concurrency to 1–2 workers via `MAX_OCR_WORKERS=2` in `.env`. |
| **Port 8000 Binding Error** | Another process is occupying port 8000. | Check active ports with `sudo lsof -i :8000` or adjust `APP_PORT=8080` in `.env`. |
| **Arabic Text Garbled in Logs** | System locale not configured for UTF-8. | Run `sudo locale-gen en_US.UTF-8` and set `LANG=en_US.UTF-8` in `/etc/environment`. |
