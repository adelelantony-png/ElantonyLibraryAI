# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - AI Provider Factory
"""

from typing import Optional
from elantony.ai.base import BaseAIProvider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.ai.gemini_provider import GeminiAIProvider
from elantony.core.config import settings

_providers = {
    "rule_based": RuleBasedChurchProvider(),
    "gemini": GeminiAIProvider(),
}


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Resolves and returns the configured AI provider with graceful fallback."""
    name = (provider_name or settings.ai_provider).lower()
    provider = _providers.get(name, _providers["rule_based"])
    if not provider.is_available():
        return _providers["rule_based"]
    return provider
