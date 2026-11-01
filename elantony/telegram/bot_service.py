# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
High-Resilience Telegram Polling Engine
Features:
- Individual update exception isolation (one faulty update never halts polling).
- Adaptive timeout handling (ReadTimeout recognized as normal idle poll).
- Automatic socket cycling and connection reset on network hiccups.
- Full compatibility with Telegram Bot API 6.0+.
"""

import sys
import asyncio
from typing import Optional, Dict, Any
import httpx

from elantony.core.config import settings
from elantony.core.logging import logger
from elantony.telegram.handlers import TelegramHandlerService


class TelegramBotEngine:
    """Production-grade asynchronous long-polling bot engine."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.telegram_bot_token
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        self.handlers = TelegramHandlerService(self.token)
        self.running = False
        self.last_update_id = 0

    async def run(self) -> None:
        """Continuous resilient long-polling loop with automatic socket recreation."""
        if not self.token:
            logger.warning("Telegram Bot Token is not set. Bot worker will not start.")
            return

        self.running = True
        logger.info(f"ELANTONY Telegram Bot worker started in {settings.telegram_mode} mode.")

        # Timeout config: read timeout slightly larger than telegram server timeout (20s)
        client_timeout = httpx.Timeout(connect=10.0, read=28.0, write=10.0, pool=10.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10, keepalive_expiry=25.0)

        backoff_seconds = 1.0
        loop_counter = 0

        while self.running:
            try:
                async with httpx.AsyncClient(timeout=client_timeout, limits=limits) as client:
                    while self.running:
                        loop_counter += 1
                        try:
                            url = f"{self.api_base}/getUpdates"
                            params = {
                                "offset": self.last_update_id + 1,
                                "timeout": 20,
                                "allowed_updates": ["message", "callback_query"]
                            }
                            res = await client.get(url, params=params)

                            if res.status_code == 200:
                                backoff_seconds = 1.0  # Reset backoff
                                data = res.json()
                                updates = data.get("result", [])

                                for u in updates:
                                    self.last_update_id = u["update_id"]
                                    try:
                                        if "message" in u:
                                            await self.handlers.handle_message(client, u["message"])
                                        elif "callback_query" in u:
                                            await self.handlers.handle_callback_query(client, u["callback_query"])
                                    except Exception as handler_err:
                                        logger.error(f"Error handling update {u.get('update_id')}: {handler_err}")

                            elif res.status_code == 401:
                                logger.critical("Invalid Telegram Bot Token (HTTP 401). Stopping worker.")
                                self.running = False
                                return

                            elif res.status_code == 409:
                                logger.warning("Conflict (HTTP 409): Another instance running getUpdates. Backing off 8s.")
                                await asyncio.sleep(8.0)

                            else:
                                logger.warning(f"Telegram API HTTP {res.status_code}. Retrying in {backoff_seconds}s.")
                                await asyncio.sleep(backoff_seconds)
                                backoff_seconds = min(backoff_seconds * 1.5, 20.0)

                        except (httpx.ReadTimeout, httpx.WriteTimeout):
                            # Normal idle polling timeout when no messages arrived during 20s
                            backoff_seconds = 1.0
                            continue

                        except httpx.NetworkError as net_err:
                            logger.warning(f"Network glitch: {net_err}. Cycling socket in {backoff_seconds}s...")
                            await asyncio.sleep(backoff_seconds)
                            backoff_seconds = min(backoff_seconds * 1.5, 15.0)
                            break  # Breaks inner loop to recreate AsyncClient socket

                        except asyncio.CancelledError:
                            self.running = False
                            break

                        except Exception as poll_err:
                            logger.error(f"Unexpected polling exception: {poll_err}. Retrying in {backoff_seconds}s...")
                            await asyncio.sleep(backoff_seconds)
                            backoff_seconds = min(backoff_seconds * 1.5, 15.0)
                            break

            except asyncio.CancelledError:
                self.running = False
                break
            except Exception as client_err:
                logger.error(f"Client recreation error: {client_err}. Retrying in 3s...")
                await asyncio.sleep(3.0)

        logger.info("ELANTONY Telegram Bot worker stopped gracefully.")

    def stop(self) -> None:
        self.running = False
