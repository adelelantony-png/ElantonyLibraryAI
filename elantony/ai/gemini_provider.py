# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Theological Gemini RAG AI Provider (Phases 6 & 7)
Leverages Google Gemini API with strict anti-hallucination guardrails,
verified citation typology (QUOTATION, PARAPHRASE, SYNTHESIS, EXTERNAL_KNOWLEDGE),
and structured theological axis synthesis.
"""

from typing import List, Optional, Dict, Any
import os
import re

from elantony.ai.base import BaseAIProvider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.database.models import ChunkEntity
from elantony.core.config import settings
from elantony.core.logging import logger

THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT = """أنت «خادم وباحث لاهوتي وكنسي أول» في منظومة ELANTONY LIBRARY AI التابعة لمكتبة كنيسة المشرق القبطية الأرثوذكسية.
مهمتك: الإجابة عن الأسئلة اللاهوتية، العقائدية، الروحية، والطقسية استناداً حصرياً ومباشراً إلى الشواهد والمراجع المرفقة في السياق (Context).

معايير التوثيق الكنسي الصارم ومنع الهلوسة (Verified Citation & Zero-Hallucination Guardrails):
1. كل حقيقة أو عقيدة أو استشهاد تقدمه يجب أن يكون مستنداً إلى أحد الشواهد المرفقة في السياق.
2. يمنع منعاً باتاً اختلاق أي مرجع، أو نسبة أقوال لآباء لم تذكر نصوصهم في السياق، أو افتراض أرقام صفحات وهمية.
3. يجب التمييز بوضوح بين أنواع التوثيق الكنسي:
   - [اقتباس حرفي - QUOTATION]: نقل العبارة بنصها الحرفي بين علامتي «...» مع ذكر المرجع ورقم الصفحة.
   - [صياغة تحليلية - PARAPHRASE]: تلخيص وشرح لفكرة مذكورة في الشاهد.
   - [استنتاج مركب - SYNTHESIS]: الربط بين أكثر من شاهد لتأكيد مفهوم لاهوتي موحد.
   - [معلومة تمهيدية - EXTERNAL_KNOWLEDGE]: خلفية لغوية أو تاريخية تمهيدية عامة (يجب ذكر أنها معلومة تمهيدية عامة وليست مقتطفة مباشرة من شواهد المكتبة).
4. توثيق رقم الصفحة:
   - اذكر رقم الصفحة كما ورد في الشاهد (سواء الصفحة المطبوعة أو صفحة ملف PDF).
   - إذا تعذر الجزم بالصفحة المطبوعة، اذكر صراحة: [صفحة PDF: X - الصفحة المطبوعة قيد المراجعة].
5. إذا طلب السؤال جانباً لم يرد في الشواهد المرفقة، لا تختلق إجابة على الإطلاق، بل اذكر بأمانة علمية:
   «لم نعثر في شواهد المكتبة المفهرسة حالياً على نص مباشر يغطي هذا الجانب تحديداً».

هيكل الإجابة المنظمة (Structured Theological Thesis):
- 📌 **المقدمة**: تعريف موجز ودقيق للمفهوم اللاهوتي أو العقائدي.
- 🏛️ **المحور الأول**: البيان اللاهوتي والآبائي (مع الشواهد الموثقة).
- 📜 **المحور الثاني**: الأبعاد الخلاصية / الكتابية / الطقسية المرتبطة.
- 🕊️ **المحور الثالث**: التطبيق الروحي والجهاد المعاش في فكر الكنيسة.
- 📚 **المصادر والمراجع الموثقة**:
  قائمة مرقمة بكل كتاب تم الاقتباس منه مع اسم المؤلف، نوع المصدر، ورقم الصفحة ونوع التوثيق.
"""


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini API Provider with strict verified citation typology and structured answer generation."""

    # Priority order for models supported on Gemini API
    CANDIDATE_MODELS = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
        "gemini-3.8-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash"
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
        Synthesizes a response strictly grounded in context_chunks with verified citation classification.
        Falls back to grounded rule-based provider if offline or key is missing.
        """
        if not self.is_available() or not context_chunks:
            return self.fallback.generate_answer(question, context_chunks, dedicated_books=dedicated_books)

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)

            # Build grounded context with full authenticity tier and page metadata
            context_blocks = []
            for idx, c in enumerate(context_chunks, 1):
                clean_chunk = c.chunk_text.strip().replace("\n", " ")
                tier_label = f"مرتبة التوثيق: {c.authenticity_tier}"
                source_label = f"التصنيف: {c.source_types or 'عام'}"
                context_blocks.append(
                    f"[{idx}] {c.source_reference} ({tier_label} | {source_label}):\n"
                    f"❝ {clean_chunk} ❞"
                )

            full_context = "\n\n".join(context_blocks)

            prompt = (
                f"{THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT}\n\n"
                f"=== الشواهد الكنسية المعتمدة المسترجعة من كتب المكتبة (Context) ===\n"
                f"{full_context}\n\n"
                f"=== السؤال المطروح من الباحث ===\n"
                f"«{question}»\n\n"
                f"الإجابة المنهجية الموثقة:"
            )

            # Strict low temperature to prevent hallucination
            generation_config = genai.types.GenerationConfig(
                temperature=0.15,
                top_p=0.85,
                max_output_tokens=2000
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
        return self.fallback.generate_answer(question, context_chunks, dedicated_books=dedicated_books)
