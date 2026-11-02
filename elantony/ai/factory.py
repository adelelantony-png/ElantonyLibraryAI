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
    gemini = _providers["gemini"]
    if provider_name:
        name = provider_name.lower()
        provider = _providers.get(name, _providers["rule_based"])
        return provider if provider.is_available() else _providers["rule_based"]

    # Auto-detection: prioritize Gemini if API key is configured and valid
    if gemini.is_available():
        return gemini

    name = settings.ai_provider.lower()
    provider = _providers.get(name, _providers["rule_based"])
    if not provider.is_available():
        return _providers["rule_based"]
    return provider
