# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Sliding Window Rate Limiter
Prevents spam and resource exhaustion by limiting requests per Telegram User ID.
"""

import time
from typing import Dict, List
from elantony.core.config import settings


class UserRateLimiter:
    """In-memory sliding window rate limiter per user."""

    def __init__(self, max_requests_per_minute: int = 30):
        self.max_requests = max_requests_per_minute
        self.user_timestamps: Dict[int, List[float]] = {}

    def is_allowed(self, user_id: int) -> bool:
        """
        Determines whether the user is permitted to make a new request.
        Maintains a 60-second sliding window of past request timestamps.
        """
        now = time.time()
        cutoff = now - 60.0

        if user_id not in self.user_timestamps:
            self.user_timestamps[user_id] = [now]
            return True

        # Evict timestamps older than 60 seconds
        valid_timestamps = [t for t in self.user_timestamps[user_id] if t > cutoff]

        if len(valid_timestamps) >= self.max_requests:
            self.user_timestamps[user_id] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self.user_timestamps[user_id] = valid_timestamps
        return True

    def reset_user(self, user_id: int) -> None:
        """Clears history for a specific user."""
        self.user_timestamps.pop(user_id, None)

    def cleanup_inactive_users(self) -> None:
        """Removes entries for users who have been inactive for over 5 minutes."""
        now = time.time()
        cutoff = now - 300.0
        stale_users = [
            uid for uid, stamps in self.user_timestamps.items()
            if not stamps or stamps[-1] < cutoff
        ]
        for uid in stale_users:
            del self.user_timestamps[uid]


# Default singleton instance
rate_limiter = UserRateLimiter(max_requests_per_minute=settings.rate_limit_per_minute)
