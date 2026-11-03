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

THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT = """أنت «باحث وخادم لاهوتي كنسي أول» في منظومة ELANTONY LIBRARY AI التابعة للكنيسة القبطية الأرثوذكسية.
مهمتك: تقديم دراسات لاهوتية آبائية عميقة، رصينة، ومستفيضة تجيب عن تساؤلات الباحثين بأسلوب أكاديمي كنسي رفيع وموثق حرفياً من أمهات كتب المكتبة المرفقة في السياق (Context).

معايير العمق الأكاديمي والتوثيق الكنسي الصارم:
1. العمق والشرح الوافي: تجنب الإجابات السطحية، المختصرة، أو المقتضبة. اشرح المسائل العقائدية بأبعادها الكتابية والآبائية والروحية مع إيراد المصطلحات اللاهوتية الأصلية (مثل: Logos, Theosis / التأله بالنعمة, Homoousios / مساوٍ في الجوهر, Enanthropeo / التجسد والتأنس الكامل).
2. الشواهد والنصوص الأصلية: أورد نصوصاً واقتباسات مطولة من أقوال الآباء (خاصة الأب المسؤول عنه كالقديس أثناسيوس أو كيرلس الكبير أو باسيليوس أو ذهبي الفم) مأخوذة من الشواهد المرفقة، وضعها بين علامتي تنصيص «...» مع ذكر اسم الكتاب، رقم المقالة/الفصل إن وجد، ورقم الصفحة بدقة.
3. التمييز بين أنواع التوثيق:
   - [اقتباس حرفي - QUOTATION]: نقل العبارة بنصها الحرفي من كتاب الأب.
   - [صياغة تحليلية - PARAPHRASE]: استخلاص وشرح المعنى اللاهوتي والفكري.
   - [استنتاج مركب - SYNTHESIS]: الربط بين عدة شواهد لتأكيد وحدة الإيمان المسلّم مرة للقديسين.
4. البناء الهيكلي الأكاديمي المعتمد:
   - 📌 **المقدمة والعقيدة الأساسية**: التعريف اللاهوتي الجامع والشامل للمفهوم في التقليد الأرثوذكسي القويم.
   - 🏛️ **المحور الأول: البيان الآبائي والنصوص الموثقة**: شواهد ونصوص الآباء المباشرة المقتبسة من الشواهد، مع شرحها لاهوتياً وفلسفياً.
   - 📜 **المحور الثاني: الأبعاد الخلاصية واللاهوتية**: أسباب التجسد، إبطال الفساد والموت، تجديد صورة الله في الإنسان، استعادة المعرفة الإلهية، والخلاص الكامل.
   - 🕊️ **المحور الثالث: التطبيق الكنسي والروحي المعاش**: كيف ينعكس هذا الإيمان في صلاة المؤمن اليومية وجهاده الروحي وسر الإفخارستيا.
   - 📚 **المصادر والمراجع الموثقة**: قائمة مرقمة بكافة المراجع المستخدمة تشمل: اسم الكتاب، المؤلف، رقم الصفحة المطبوعة ورقم صفحة الـ PDF.

تنبيه قطعي: يمنع منعاً باتاً تكرار نص هذه التعليمات، ابدأ مباشرة بتقديم الدراسة اللاهوتية المنهجية الموثقة.
"""


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini API Provider with strict verified citation typology and structured answer generation."""

    # Priority order for high-quota and active models on Gemini API
    CANDIDATE_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash"
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
                f"=== الشواهد الكنسية المعتمدة المسترجعة من كتب المكتبة (Context) ===\n"
                f"{full_context}\n\n"
                f"=== السؤال المطروح من الباحث ===\n"
                f"«{question}»\n\n"
                f"الإجابة المنهجية الموثقة:"
            )

            # Academic patristic depth configuration
            generation_config = genai.types.GenerationConfig(
                temperature=0.25,
                top_p=0.9,
                max_output_tokens=3800
            )

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 60}
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    logger.warning(f"Gemini model {model_name} error: {model_err}. Trying next...")
                    continue

        except Exception as e:
            logger.warning(f"Gemini API generation failed ({e}), using grounded rule-based fallback.")

        # Seamless fallback
        return self.fallback.generate_answer(question, context_chunks, dedicated_books=dedicated_books)

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        context_chunks: List[ChunkEntity]
    ) -> str:
        """
        Conversational assistant response: maintains multi-turn dialog memory
        while anchoring theological facts strictly in library citations.
        """
        if not self.is_available() or not messages:
            latest = messages[-1]["content"] if messages else ""
            return self.fallback.generate_answer(latest, context_chunks)

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            # Build grounded context
            context_blocks = []
            for idx, c in enumerate(context_chunks, 1):
                clean_chunk = c.chunk_text.strip().replace("\n", " ")
                context_blocks.append(f"[{idx}] {c.source_reference} (مرتبة التوثيق: {c.authenticity_tier}):\n❝ {clean_chunk} ❞")
            full_context = "\n\n".join(context_blocks)

            # Conversation turns
            dialog_lines = []
            for m in messages[:-1]:
                role_label = "الباحث" if m["role"] == "user" else "المساعد اللاهوتي"
                dialog_lines.append(f"{role_label}: {m['content']}")

            history_context = "\n".join(dialog_lines) if dialog_lines else "بداية المحادثة."
            latest_query = messages[-1]["content"] if messages else ""

            prompt = (
                f"=== الشواهد الكنسية المسترجعة من كتب المكتبة (Library Grounding) ===\n"
                f"{full_context}\n\n"
                f"=== سياق الحديث والنقاش السابق بينك وبين الباحث (Chat Context) ===\n"
                f"{history_context}\n\n"
                f"=== استفسار الباحث الحالي ===\n"
                f"الباحث: {latest_query}\n\n"
                f"المساعد اللاهوتي (إجابة موثقة تجيب مباشرة وتراعي ما تم مناقشته مسبقاً):"
            )

            generation_config = genai.types.GenerationConfig(
                temperature=0.25,
                top_p=0.9,
                max_output_tokens=3800
            )

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 60}
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    continue

        except Exception as e:
            logger.warning(f"Conversational generation error: {e}")

        latest = messages[-1]["content"] if messages else ""
        return self.fallback.generate_answer(latest, context_chunks)

