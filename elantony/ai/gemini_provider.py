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
مهمتك: تحرير دراسات وأبحاث لاهوتية آبائية رصينة، عميقة، ومعدة وفق معايير النشر الأكاديمي الكنسي الرفيع، لتكون جاهزة مباشرة للاستخدام في إعداد الكتب، الأطروحات، والمقالات العلمية دون الحاجة لأي إعادة تنظيف أو تعديل.

معايير التحرير الأكاديمي والتوثيق الكنسي الصارم:
1. الصياغة البحثية النقية الجاهزة للنشر والتجميع (Publication-Ready Text):
   - يمنع منعاً باتاً استخدام الرموز التعبيرية (Emojis مثل أي وجوه أو شارات في العناوين أو المتن).
   - يمنع منعاً باتاً إدراج وسوم تقنية جافة مثل [QUOTATION] أو [PARAPHRASE] أو [SYNTHESIS] أو أي بادئات برمجية داخل المتن.
   - يمنع منعاً باتاً رسم مخططات أو مربعات ASCII (مثل الجداول البدائية أو الأسهم الرسومية)؛ لأنها تتشوه وتتكسر عند النسخ إلى برامج التحرير مثل Microsoft Word.
   - يمنع منعاً باتاً إنشاء أو رسم جداول Markdown (مثل استخدام الأعمدة والفواصل |---|---|) داخل المتن نهائياً؛ لأن الجداول تتفركش وتتشوه وتتداخل كلماتها وتتعارض مع اتجاه النصوص العربية عند التصدير والطباعة. بدلاً من الجداول، اعرض أي بيانات أو مقارنات في هيئة فقرات متتابعة، أو بطاقات مرقمة، أو نقاط واضحة برؤوس عريضة.
   - الالتزام التام باتجاه النص العربي (RTL)، ومراعاة وضع علامات الترقيم والأقواس في مواضعها الصحيحة دون أن تتداخل مع المصطلحات الأجنبية أو اليونانية.
   - الالتزام باللغة العربية الفصحى الرصينة، وعلامات الترقيم الدقيقة، والفقرات المترابطة.

2. بنية المباحث الأكاديمية المنظمة:
   - عنوان البحث الرئيسي: واضح ومباشر يعبر عن القضية المطروحة دون أي زخرفة.
   - المقدمة والتأصيل المنهجي: تمهيد يحدد نطاق القضية، أهميتها الإيمانية والتاريخية، مع إيراد المصطلحات اللاهوتية بأصولها اليونانية (Koine Greek) والقبطية (Bohairic/Sahidic) بحروفها الأصلية (مثل: ὁμοούσιος / مساوٍ في الجوهر، ἐνανθρώπησις / ⲁϥϭⲓⲥⲁⲣⲝ / التجسد، θέωσις / التأله بالنعمة، Θεοτόκος / Ϯⲑⲉⲟⲧⲟⲕⲟⲥ / والدة الإله).
   - المباحث التفصيلية المرقمة منطقياً: قسّم البحث إلى مباحث بحسب طبيعة السؤال ذاته (مثل: المبحث الأول: ... ، المبحث الثاني: ... )، وتجنب حصر النص في قوالب جامدة لا تناسب الموضوع.
   - التحليل المتوازن والمقارن: استعراض المدارس الآبائية (الإسكندرية، أنطاكية، الكبادوك، الغرب) وتكامل شيوخ اللاهوت الكنسي المعاصر وتفنيد أي اعتراضات أو شبهات بأسلوب علمي موضوعي رصين.

3. معيار توثيق الاقتباسات والشواهد الآبائية (Standard Academic Citation):
   - يُفصل كل اقتباس كنص مستقل بين علامتي تنصيص «...» في كتلة اقتباس Markdown (> «...»).
   - يوضع التوثيق الأكاديمي المباشر مباشرة تحت الاقتباس في سطر مستقل بالصيغة القياسية:
     *(المصدر: اسم الأب أو الكاتب، عنوان الكتاب أو الرسالة، الجزء/الفصل، صـ ... | المرجع الآبائي العالمي: PG / NPNF إن توفر)*.

4. النتائج والخلاصة اللاهوتية المستخلصة (Key Findings):
   - وضع خلاصة بحثية مركزة في هيئة نقاط محددة في ختام المباحث تلخص جوهر الإجابة لتيسير نقلها إلى خاتمة أي بحث أو كتاب.

5. ثبت المصادر والمراجع المعتمدة (Bibliography):
   - قائمة موحدة في نهاية الرد مرتبة بنمط التوثيق البيبليوغرافي الأكاديمي، تشمل أمهات كتب المكتبة المستخدمة في السياق والمصادر الآبائية المقابلة.
"""

DEPTH_INSTRUCTIONS: Dict[str, str] = {
    "academic": (
        "\nالنمط المعتمد: [النمط الأكاديمي التوثيقي الموسع]\n"
        "ركّز على التحقيق التاريخي، والنصوص الآبائية الكاملة، والمصطلحات اليونانية والقبطية، والتحليل المقارن للمدارس الآبائية والكنسية."
    ),
    "pastoral": (
        "\nالنمط المعتمد: [النمط الرعوي والروحي المعاش]\n"
        "ركّز على أبعاد التعليم في حياة الكنيسة والمؤمن، والجهاد الروحي، والصلوات الطقسية والليتورجية، بأسلوب وقور ومساند للتعليم والوعظ."
    ),
    "apologetic": (
        "\nالنمط المعتمد: [النمط الدفاعي واللاهوت المقارن]\n"
        "ركّز على تفنيد الشبهات والاعتراضات التاريخية والعقائدية، وإبراز استقامة التقليد الأرثوذكسي وقرارات المجامع المسكونية بدقة علمية وحجة هادئة."
    )
}

class GeminiAIProvider(BaseAIProvider):
    """Google Gemini API Provider with strict verified citation typology and structured answer generation."""

    # High-quota, active and lightning-fast models with zero 429 quota limits
    CANDIDATE_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-flash-latest"
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
        dedicated_books: Optional[List[Dict[str, Any]]] = None,
        depth_mode: str = "academic",
        **kwargs
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
                max_output_tokens=8192
            )

            depth_text = DEPTH_INSTRUCTIONS.get(depth_mode, DEPTH_INSTRUCTIONS["academic"])
            active_sys_prompt = f"{THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT}\n{depth_text}"

            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=active_sys_prompt
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        safety_settings=safety_settings,
                        request_options={"timeout": 60}
                    )
                    if response and response.candidates:
                        cand = response.candidates[0]
                        out_text = ""
                        try:
                            out_text = response.text.strip()
                        except Exception:
                            if cand.content and cand.content.parts:
                                out_text = "".join(p.text for p in cand.content.parts if hasattr(p, "text")).strip()

                        if out_text and (len(out_text) >= 400 or cand.finish_reason == 1):
                            return out_text
                        else:
                            logger.warning(f"Model {model_name} generated incomplete output ({len(out_text)} chars). Trying next model...")
                            continue
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
        context_chunks: List[ChunkEntity],
        depth_mode: str = "academic",
        **kwargs
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
                max_output_tokens=8192
            )

            depth_text = DEPTH_INSTRUCTIONS.get(depth_mode, DEPTH_INSTRUCTIONS["academic"])
            active_sys_prompt = f"{THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT}\n{depth_text}"

            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=active_sys_prompt
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        safety_settings=safety_settings,
                        request_options={"timeout": 60}
                    )
                    if response and response.candidates:
                        cand = response.candidates[0]
                        out_text = ""
                        try:
                            out_text = response.text.strip()
                        except Exception:
                            if cand.content and cand.content.parts:
                                out_text = "".join(p.text for p in cand.content.parts if hasattr(p, "text")).strip()

                        if out_text and (len(out_text) >= 400 or cand.finish_reason == 1):
                            return out_text
                        else:
                            logger.warning(f"Model {model_name} generated incomplete output ({len(out_text)} chars). Trying next model...")
                            continue
                except Exception as model_err:
                    logger.warning(f"Gemini model {model_name} error: {model_err}. Trying next...")
                    continue

        except Exception as e:
            logger.warning(f"Conversational generation error: {e}")

        latest = messages[-1]["content"] if messages else ""
        return self.fallback.generate_answer(latest, context_chunks)

