# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Cloudflare Tunnel Auto-Healer & Watchdog Service
Continuously monitors the health of the public access tunnel.
If Cloudflare terminates the 24-hour lease or network hiccups occur,
this watchdog automatically spawns a fresh tunnel, extracts the new URL,
and updates the remote link files on all drives without any manual intervention.
"""

import os
import sys
import re
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import httpx

from elantony.core.logging import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLOUDFLARED_BIN = PROJECT_ROOT / "tools" / "cloudflared.exe"

LINK_FILES = [
    PROJECT_ROOT / "رابط_المساعد_عن_بعد.txt",
    Path(r"I:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster\رابط_المساعد_عن_بعد.txt")
]


class CloudflareTunnelWatchdog:
    """Supervises and auto-heals Cloudflare remote access tunnels 24/7."""

    def __init__(self, check_interval_sec: int = 45):
        self.check_interval = check_interval_sec
        self.current_url: Optional[str] = self._load_current_url()
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._consecutive_failures = 0

    def _load_current_url(self) -> Optional[str]:
        for lf in LINK_FILES:
            if lf.exists():
                try:
                    txt = lf.read_text(encoding="utf-8")
                    m = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", txt)
                    if m:
                        return m.group(0)
                except Exception:
                    pass
        return None

    def _save_current_url(self, url: str) -> None:
        self.current_url = url
        content = f"رابط الوصول للمساعد الذكي عن بعد:\n{url}\n\nتاريخ التحديث التلقائي: {time.ctime()}\n"
        for lf in LINK_FILES:
            try:
                lf.parent.mkdir(parents=True, exist_ok=True)
                lf.write_text(content, encoding="utf-8")
                logger.info(f"[TunnelWatchdog] Updated link file: {lf}")
            except Exception as e:
                logger.warning(f"[TunnelWatchdog] Could not write {lf}: {e}")

    def kill_existing_cloudflared(self) -> None:
        """Kills any orphaned or stuck cloudflared processes on Windows."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "cloudflared.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass

    def start_tunnel(self) -> Optional[str]:
        """Launches a fresh cloudflared tunnel and captures the generated URL."""
        if not CLOUDFLARED_BIN.exists():
            logger.error(f"[TunnelWatchdog] cloudflared.exe not found at: {CLOUDFLARED_BIN}")
            return None

        logger.info("[TunnelWatchdog] Launching fresh Cloudflare Quick Tunnel...")
        self.kill_existing_cloudflared()

        cmd = [str(CLOUDFLARED_BIN), "tunnel", "--url", "http://localhost:8000"]
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
        except Exception as e:
            logger.error(f"[TunnelWatchdog] Failed to spawn cloudflared: {e}")
            return None

        # Read output stream until public URL is detected
        new_url = None
        start_time = time.time()
        while time.time() - start_time < 30:
            line = self.process.stdout.readline()
            if not line and self.process.poll() is not None:
                break
            if line:
                m = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    new_url = m.group(0)
                    break

        if new_url:
            self._save_current_url(new_url)
            self._consecutive_failures = 0
            logger.info(f"✨ [TunnelWatchdog] Successfully established fresh tunnel: {new_url}")
            return new_url
        else:
            logger.error("[TunnelWatchdog] Timeout or failure capturing new tunnel URL from cloudflared.")
            return None

    async def is_tunnel_healthy(self) -> bool:
        """Checks if the public tunnel URL is actively responding."""
        if not self.current_url:
            return False

        health_url = f"{self.current_url}/health"
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.get(health_url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("status") == "healthy"
                return False
        except Exception:
            return False

    async def run(self) -> None:
        """Main 24/7 supervisor loop."""
        self._running = True
        logger.info("[TunnelWatchdog] Tunnel Auto-Healer supervisor loop active.")

        # Initial health probe
        if not await self.is_tunnel_healthy():
            logger.warning("[TunnelWatchdog] Initial tunnel check failed. Initiating startup...")
            self.start_tunnel()

        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                healthy = await self.is_tunnel_healthy()
                if healthy:
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1
                    logger.warning(
                        f"[TunnelWatchdog] Tunnel health check failed ({self._consecutive_failures}/2). "
                        f"Target: {self.current_url}"
                    )

                    if self._consecutive_failures >= 2:
                        logger.error("[TunnelWatchdog] Tunnel confirmed down. Triggering automatic self-healing...")
                        self.start_tunnel()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[TunnelWatchdog] Supervisor error: {e}")

    def stop(self) -> None:
        self._running = False
        self.kill_existing_cloudflared()
        logger.info("[TunnelWatchdog] Supervisor stopped.")
