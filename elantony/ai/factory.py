# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
AI Provider Factory with Multi-Model Gateway Integration
Ensures unified access to Gemini, Kimi, DeepInfer, ZenMux, BeatAPI, and RuleBased fallback.
"""

from typing import Optional
from elantony.ai.base import BaseAIProvider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.ai.gemini_provider import GeminiAIProvider
from elantony.ai.gateway import gateway, MultiModelGateway
from elantony.core.config import settings


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """
    Resolves and returns the AI provider.
    Defaults to the unified MultiModelGateway, which manages dynamic routing and cascading failover.
    Specific providers can also be requested by name ('gemini', 'kimi', 'deepinfer', 'rule_based', etc.).
    """
    if provider_name:
        name = provider_name.lower().strip()
        if name in ("gateway", "multi_model", "auto", "default"):
            return gateway
        specific = gateway.get_provider(name)
        if specific and specific.is_available():
            return specific
        return gateway

    # By default, provide the resilient Multi-Model Gateway
    return gateway
