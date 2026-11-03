# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - AI Provider Interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from elantony.database.models import ChunkEntity


class BaseAIProvider(ABC):
    """Abstract AI Provider for RAG synthesis and generation."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def generate_answer(self, question: str, context_chunks: List[ChunkEntity], **kwargs) -> str:
        """
        Synthesizes a response strictly grounded in the supplied context chunks.
        Must never hallucinate or invent citations.
        """
        pass
