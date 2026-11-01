# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Theological Gemini RAG AI Provider
Leverages Google Gemini API (Free tier / Pay-as-you-go) with strict
anti-hallucination prompt guardrails and automatic model fallback.
"""

from typing import List, Optional, Dict, Any
import os

from elantony.ai.base import BaseAIProvider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.database.models import ChunkEntity
from elantony.core.config import settings
from elantony.core.logging import logger

THEOLOGICAL_SYSTEM_PROMPT = """أنت «خادم وباحث لاهوتي وكنسي» في منظومة ELANTONY LIBRARY AI التابعة لمكتبة كنيسة المشرق القبطية الأرثوذكسية.
مهمتك: الإجابة عن الأسئلة اللاهوتية، العقائدية، الروحية، والطقسية استناداً حصرياً ومباشراً إلى نصوص المراجع والشواهد الآبائية المرفقة في السياق أدناه.

القواعد الصارمة لمنع الهلوسة (Zero-Hallucination Guardrails):
1. كل معلومة أو تعليم تقدمه يجب أن يكون مستنداً إلى أحد الشواهد المرفقة في السياق.
2. يمنع منعاً باتاً اختلاق أي مراجع، أو نسب أقوال لآباء لم تذكر نصوصهم في السياق، أو افتراض أرقام صفحات غير موجودة.
3. وثق دائماً المرجع ورقم الصفحة بصيغة دقيقة: [اسم الكتاب، ص: X].
4. رتب إجابتك بتنسيق كنسي وقور وواضح:
   - 📌 **الخلاصة والشرح اللاهوتي / الروحي**: إيضاح المفهوم بأسلوب كنسي عميق مستخلص من النصوص.
   - 📖 **شواهد بطون أمهات الكتب**: اقتباس العبارات الآبائية الجوهرية مع توثيق اسم السفر/الكتاب ورقم الصفحة.
   - ✨ **التدريب والتطبيق الروحي**: كيف يعيش المؤمن هذا التعليم في جهاده اليومي وحياته مع الله.
5. إذا لم تحتوِ الشواهد المرفقة على إجابة كافية ومباشرة، قل بأمانة علمية وروحية:
   «لم أعثر في المراجع المفهرسة حالياً على نصوص مباشرة تغطي هذه المسألة بدقة كاملة، ويرجى البحث بكلمات أخرى أو الرجوع للمراجع المتخصصة».
"""


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini API Provider with strict anti-hallucination guardrails and multi-model fallback."""

    # Priority order for models supported on Gemini API
    CANDIDATE_MODELS = [
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.fallback = RuleBasedChurchProvider()

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def generate_answer(
        self,
        question: str,
        context_chunks: List[ChunkEntity],
        dedicated_books: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Synthesizes a response strictly grounded in context_chunks.
        Falls back to grounded rule-based provider if offline or key is missing.
        """
        if not self.is_available() or not context_chunks:
            return self.fallback.generate_answer(question, context_chunks, dedicated_books=dedicated_books)

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)

            # Build grounded context
            context_blocks = []
            for idx, c in enumerate(context_chunks, 1):
                clean_chunk = c.chunk_text.strip().replace("\n", " ")
                context_blocks.append(f"[{idx}] {c.source_reference}:\n❝ {clean_chunk} ❞")

            full_context = "\n\n".join(context_blocks)

            prompt = (
                f"{THEOLOGICAL_SYSTEM_PROMPT}\n\n"
                f"=== الشواهد الكنسية المسترجعة من كتب المكتبة (Context) ===\n"
                f"{full_context}\n\n"
                f"=== السؤال المطروح من الباحث ===\n"
                f"«{question}»\n\n"
                f"الإجابة الموثقة الكنسية:"
            )

            # Try candidate models with graceful fallback
            generation_config = genai.types.GenerationConfig(
                temperature=0.2,       # Low temperature prevents hallucination
                top_p=0.9,
                max_output_tokens=1500
            )

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt, generation_config=generation_config)
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    logger.warning(f"Gemini model {model_name} error: {model_err}. Trying next...")
                    continue

        except Exception as e:
            logger.warning(f"Gemini API generation failed ({e}), using grounded rule-based fallback.")

        # Seamless fallback
        return self.fallback.generate_answer(question, context_chunks)
