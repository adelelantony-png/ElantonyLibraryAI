# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Security & Authorization Layer
Enforces Telegram User ID whitelisting, administrative role checks,
and text input sanitization to prevent injection vulnerabilities.
"""

import re
from typing import Optional
from elantony.core.config import settings


def is_user_authorized(user_id: int) -> bool:
    """
    Checks if a Telegram user is authorized to use the library bot.
    If the whitelist is configured, only listed users (and admins) are allowed.
    If empty, allows access in development mode.
    """
    if not settings.allowed_telegram_user_ids and not settings.admin_telegram_user_ids:
        # Open access in initial bootstrap/development mode
        return True

    return (
        user_id in settings.allowed_telegram_user_ids
        or user_id in settings.admin_telegram_user_ids
    )


def is_user_admin(user_id: int) -> bool:
    """Checks if a Telegram user has administrative privileges."""
    if not settings.admin_telegram_user_ids:
        # Open administrative privileges in local deployment or development mode
        return True

    return user_id in settings.admin_telegram_user_ids


def sanitize_user_input(text: str, max_length: int = 500) -> str:
    """
    Sanitizes incoming textual queries:
    - Truncates excessive input lengths to prevent buffer/DOS attacks.
    - Strips NULL bytes and harmful control characters.
    - Preserves Arabic, Coptic, and standard punctuation.
    """
    if not text:
        return ""

    # Truncate to max length
    clean = text[:max_length]

    # Remove NULL and control characters except newline and tab
    clean = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean)

    # Clean extreme multiple spaces
    clean = re.sub(r'[ \t]{2,}', ' ', clean)

    return clean.strip()


def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """Returns a securely masked representation of a token or password."""
    if not secret:
        return "***NOT_SET***"
    if len(secret) <= visible_chars * 2:
        return "***REDACTED***"
    return f"{secret[:visible_chars]}...***...{secret[-visible_chars:]}"
