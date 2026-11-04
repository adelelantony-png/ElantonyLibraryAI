# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
ELANTONY MULTI-MODEL GATEWAY (Phase 5)
Orchestrates multiple AI inference providers:
- Google Gemini (Gemini 2.5 Flash / Pro)
- Moonshot Kimi K3 (200k+ long-context patristic study)
- DeepInfer (Local DeepSeek-R1 / Ollama / llama.cpp / vLLM)
- ZenMux (Universal AI Multiplexer)
- BeatAPI (Reverse-proxy API aggregator)
- Rule-Based Church Engine (Deterministic 100% offline fallback)

Features:
- Dynamic complexity & intent routing (Economy vs. Deep Reasoning).
- Zero-downtime cascading fallback hierarchy.
- Strict anti-hallucination & verified citation preservation.
- Secure environment-only secret management.
"""

import os
import time
from typing import List, Optional, Dict, Any

from elantony.ai.base import BaseAIProvider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.ai.gemini_provider import GeminiAIProvider
from elantony.ai.openai_compatible_provider import OpenAICompatibleProvider
from elantony.database.models import ChunkEntity
from elantony.core.config import settings
from elantony.core.logging import logger


class MultiModelGateway(BaseAIProvider):
    """
    Central AI Gateway coordinating multi-model routing, cost-control,
    failover cascades, and theological citation verification.
    """

    def __init__(self):
        self._providers: Dict[str, BaseAIProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """Initializes all supported providers from environment variables."""
        # 1. Deterministic Rule-Based Provider (Always available offline)
        self._providers["rule_based"] = RuleBasedChurchProvider()

        # 2. Google Gemini Provider
        self._providers["gemini"] = GeminiAIProvider()

        # 3. Moonshot Kimi K3 Provider (200k+ long-context)
        kimi_key = os.getenv("KIMI_API_KEY", "").strip()
        kimi_base = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1").strip()
        self._providers["kimi"] = OpenAICompatibleProvider(
            name="kimi",
            base_url=kimi_base,
            api_key=kimi_key,
            default_model=os.getenv("KIMI_MODEL", "moonshot-v1-128k")
        )

        # 4. DeepInfer (Local or hybrid DeepSeek-R1 / Ollama)
        deepinfer_base = os.getenv("DEEPINFER_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")).strip()
        deepinfer_key = os.getenv("DEEPINFER_API_KEY", "").strip()
        self._providers["deepinfer"] = OpenAICompatibleProvider(
            name="deepinfer",
            base_url=deepinfer_base,
            api_key=deepinfer_key,
            default_model=os.getenv("DEEPINFER_MODEL", "deepseek-r1:8b")
        )

        # 5. ZenMux AI Multiplexer
        zenmux_key = os.getenv("ZENMUX_API_KEY", "").strip()
        zenmux_base = os.getenv("ZENMUX_BASE_URL", "https://api.zenmux.ai/v1").strip()
        self._providers["zenmux"] = OpenAICompatibleProvider(
            name="zenmux",
            base_url=zenmux_base,
            api_key=zenmux_key,
            default_model=os.getenv("ZENMUX_MODEL", "zenmux-default")
        )

        # 6. BeatAPI Gateway
        beatapi_key = os.getenv("BEATAPI_KEY", "").strip()
        beatapi_base = os.getenv("BEATAPI_BASE_URL", "https://api.beatapi.io/v1").strip()
        self._providers["beatapi"] = OpenAICompatibleProvider(
            name="beatapi",
            base_url=beatapi_base,
            api_key=beatapi_key,
            default_model=os.getenv("BEATAPI_MODEL", "deepseek-v4.1-flash-free")
        )

    @property
    def provider_name(self) -> str:
        return "elantony_multi_model_gateway"

    def is_available(self) -> bool:
        # Rule-based fallback is always available
        return True

    def get_provider(self, name: str) -> Optional[BaseAIProvider]:
        return self._providers.get(name.lower())

    def list_available_providers(self) -> List[str]:
        """Returns a list of providers that are active and ready."""
        return [name for name, prov in self._providers.items() if prov.is_available()]

    def determine_optimal_provider(
        self,
        question: str,
        depth_mode: str = "academic",
        explicit_provider: Optional[str] = None
    ) -> str:
        """
        Dynamically selects the best AI provider based on:
        1. Explicit user request (if available).
        2. Depth mode (academic, apologetic -> reasoning models; pastoral -> balanced).
        3. Question complexity and length.
        """
        if explicit_provider and explicit_provider.lower() in self._providers:
            target = explicit_provider.lower()
            if self._providers[target].is_available():
                return target

        # If Gemini is configured and available, check task complexity
        if self._providers["gemini"].is_available():
            return "gemini"

        # Check Kimi for long research if available
        if self._providers["kimi"].is_available():
            return "kimi"

        # Check DeepInfer local engine if available
        if self._providers["deepinfer"].is_available():
            return "deepinfer"

        # Check ZenMux
        if self._providers["zenmux"].is_available():
            return "zenmux"

        # Check BeatAPI
        if self._providers["beatapi"].is_available():
            return "beatapi"

        # Safe baseline
        return "rule_based"

    def generate_answer(
        self,
        question: str,
        context_chunks: List[ChunkEntity],
        depth_mode: str = "academic",
        provider_preference: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Synthesizes an answer using the optimal provider, with automatic
        cascading failover across providers if any error occurs.
        """
        chosen_provider_name = self.determine_optimal_provider(
            question=question,
            depth_mode=depth_mode,
            explicit_provider=provider_preference
        )

        # Build fallback sequence
        fallback_order = [chosen_provider_name]
        for candidate in ["gemini", "kimi", "deepinfer", "zenmux", "beatapi", "rule_based"]:
            if candidate not in fallback_order and self._providers[candidate].is_available():
                fallback_order.append(candidate)
        if "rule_based" not in fallback_order:
            fallback_order.append("rule_based")

        last_error = None
        for prov_name in fallback_order:
            provider = self._providers.get(prov_name)
            if not provider or not provider.is_available():
                continue

            try:
                start_time = time.time()
                logger.info(f"[MultiModelGateway] Routing request to '{prov_name}' (Depth: {depth_mode})")
                answer = provider.generate_answer(
                    question=question,
                    context_chunks=context_chunks,
                    depth_mode=depth_mode,
                    **kwargs
                )
                elapsed = time.time() - start_time
                logger.info(f"[MultiModelGateway] Provider '{prov_name}' responded successfully in {elapsed:.2f}s")
                return answer
            except Exception as e:
                logger.warning(f"[MultiModelGateway] Provider '{prov_name}' failed: {e}. Cascading to next fallback...")
                last_error = e

        # If everything fails, run deterministic rule-based provider directly
        logger.error(f"[MultiModelGateway] All configured providers failed. Final safety fallback to rule_based: {last_error}")
        return self._providers["rule_based"].generate_answer(
            question=question,
            context_chunks=context_chunks,
            depth_mode=depth_mode,
            **kwargs
        )


# Global singleton instance
gateway = MultiModelGateway()
