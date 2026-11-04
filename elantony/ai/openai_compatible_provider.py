# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Universal OpenAI-Compatible AI Provider
Supports Moonshot Kimi (K3 / 200k context), DeepInfer (Local DeepSeek-R1 / Ollama / vLLM),
ZenMux Multiplexer, and BeatAPI Aggregator.
Strictly adheres to theological citation standards and anti-hallucination protocols.
"""

from typing import List, Optional, Dict, Any
import os
import json
import httpx

from elantony.ai.base import BaseAIProvider
from elantony.database.models import ChunkEntity
from elantony.ai.gemini_provider import THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT, DEPTH_INSTRUCTIONS
from elantony.core.logging import logger


class OpenAICompatibleProvider(BaseAIProvider):
    """
    Standard OpenAI-compatible AI provider suitable for:
    - Kimi (Moonshot AI K3 / 128k-200k long context)
    - DeepInfer (Ollama, vLLM, llama.cpp, Local DeepSeek-R1)
    - ZenMux AI Multiplexer
    - BeatAPI Gateway
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: str = "default",
        timeout: float = 60.0
    ):
        self._name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.default_model = default_model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        """Checks if provider has necessary base URL and non-empty API key (if required)."""
        if not self.base_url:
            return False
        # Local engines like Ollama / local DeepInfer may not require an API key
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return True
        return bool(self.api_key and len(self.api_key) > 5)

    def _build_context_prompt(self, context_chunks: List[ChunkEntity]) -> str:
        if not context_chunks:
            return "\n[ملاحظة: لا توجد نصوص مباشرة مسترجعة من المكتبة لهذا السؤال. اعتمد على الأصول الكنسية والآبائية الثابتة مع التنويه بأن المصدر خارجي.]\n"

        prompt_parts = ["\n--- بداية الشواهد والنصوص المستخرجة من أمهات كتب المكتبة ---"]
        for idx, chunk in enumerate(context_chunks, 1):
            title = getattr(chunk, "book_title", "") or "كتاب كنسي غير معنون"
            author = getattr(chunk, "author", "") or "أحد آباء ومعلمي الكنيسة القبطية الأرثوذكسية"
            printed_page = getattr(chunk, "printed_page", None) or getattr(chunk, "page_number", "غير محدد")
            source_ref = getattr(chunk, "source_reference", f"«{title}» - ص {printed_page}")
            text_body = getattr(chunk, "chunk_text", getattr(chunk, "content", "")).strip()

            prompt_parts.append(
                f"\n[الشاهد رقم {idx}]: {source_ref}"
                f"\nالكتاب: «{title}»"
                f"\nالمؤلف / القديس: {author}"
                f"\nالصفحة: {printed_page}"
                f"\nالنص الموثق المسترجع:\n«{text_body}»\n"
            )
        prompt_parts.append("--- نهاية الشواهد والنصوص المستخرجة ---\n")
        return "\n".join(prompt_parts)

    def generate_answer(
        self,
        question: str,
        context_chunks: List[ChunkEntity],
        depth_mode: str = "academic",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generates an authoritative theological synthesis using an OpenAI-compatible endpoint.
        """
        if not self.is_available():
            raise RuntimeError(f"Provider {self._name} is not available (check base URL and API key)")

        active_model = model or self.default_model
        mode_instruction = DEPTH_INSTRUCTIONS.get(depth_mode, DEPTH_INSTRUCTIONS["academic"])
        context_text = self._build_context_prompt(context_chunks)

        user_content = (
            f"السؤال أو المسألة اللاهوتية المطلوب دراستها:\n{question}\n\n"
            f"{context_text}\n"
            f"{mode_instruction}\n\n"
            "قدم الآن الدراسة اللاهوتية الكنسية الشاملة والموثقة طبقاً للشواهد السابقة وللهيكل الأكاديمي المطلوب:"
        )

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2,  # Low temperature to strictly prevent hallucinations
            "max_tokens": 4096,
        }

        endpoint = f"{self.base_url}/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"[{self._name}] API error {response.status_code}: {response.text[:200]}")
                    raise RuntimeError(f"{self._name} returned status {response.status_code}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except Exception as e:
            logger.error(f"[{self._name}] Exception during generation: {e}")
            raise
