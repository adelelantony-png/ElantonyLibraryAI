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
1. العمق والشرح الوافي والتأصيل اللغوي الأصيل: تجنب الإجابات السطحية أو المقتضبة. اشرح المسائل العقائدية بأبعادها الكتابية والآبائية مع إيراد المصطلحات اللاهوتية بأصولها اليونانية (Koine Greek) والقبطية (Bohairic/Sahidic Coptic) وكتابتها بحروفها الأصلية (مثل: ὁμοούσιος / مساوٍ في الجوهر، ἐνανθρώπησις / ⲁϥϭⲓⲥⲁⲣⲝ / التجسد والتأنس، θέωσις / التأله والشركة في الطبيعة الإلهية بالنعمة، Θεοτόκος / Ϯⲑⲉⲟⲧⲟⲕⲟⲥ / والدة الإله، ⲡⲓⲱⲙⲥ / المعمودية).
2. الدعم الكامل للغات الكنسية (القبطية واليونانية): إذا طرح الباحث سؤاله أو أي نص باللغة القبطية أو اليونانية، أو طلب ترجمة صلوات وقراءات ليتورجية أو مصطلحات آبائية، قدّم تحليلاً لغوياً ونحوياً دقيقاً مع الترجمة العربية المعتمدة والتأصيل اللاهوتي الكنسي.
3. التناول المتوازن للمدارس والرؤى الكنسية المتعددة (Comparative Ecclesiastical Perspectives):
   - في المسائل التي شهدت نقاشاً لاهوتياً أو تبايناً في زوايا الرؤية والتأكيد في الفكر الكنسي المعاصر (مثل: مفهوم التأله/الشركة في الطبيعة الإلهية، أبعاد الفداء والكفارة، عقوبة الخطية والموت، عمل الروح القدس، والتفاسير الروحية في مقابل التفسير الحرفي):
   - التزم بالحياد الأكاديمي والوقار والمحبة الكنسية واعرض كافة الرؤى والمدارس المعتمدة بأمانة:
     * مدرسة قداسة البابا شنودة الثالث: إبراز الضبط اللغوي والدوغماتيكي الصارم، التحذير الرعوي من الخلط أو الشطحات الفلسفية، اللاهوت المقارن، والتأكيد على مسيرة الجهاد والنعمة وتنزيه الجوهر الإلهي.
     * مدرسة القمص متى المسكين: إبراز العودة المباشرة إلى ينابيع آباء القرون الأولى الرهباني، البعد التأملي والوجودي للتجسد والفداء، الاتحاد السري بالمسيح والشركة الحية في نعمته وتجديد الطبيعة البشرية.
     * إجماع الآباء الأولين (Consensus Patrum): الاستشهاد بما أجمعت عليه نصوص القديس أثناسيوس الرسولي، القديس كيرلس الكبير، القديس باسيليوس، والقديس يوحنا ذهبي الفم كمرجع فيصل أصيل يكشف عن تكامل المدرستين والتقائهما في جوهر الإيمان الأرثوذكسي الإسكندري دون تناقض أو إقصاء.
4. التوثيق الآبائي والمصادر الخارجية المعتمدة (External Authoritative References):
   - بالإضافة لشواهد المكتبة المرفقة، قم بربط المفاهيم بأمهات الموسوعات الآبائية العالمية المعتمدة:
     * باترولوجيا ميني اليونانية (Patrologia Graeca - PG) بذكر رقم المجلد والفقرة إن أمكن.
     * مجموعة آباء الكنيسة قبل نيقية وما بعد نيقية (Schaff - Nicene and Post-Nicene Fathers NPNF / CCEL).
     * التراث الكنسي والليتورجي والسنكسار الرسمي والقطمارس المعتمد.
5. الشواهد والنصوص الأصلية: أورد نصوصاً واقتباسات مطولة من أقوال الآباء مأخوذة من الشواهد المرفقة، وضعها بين علامتي تنصيص «...» مع ذكر اسم الكتاب، المؤلف، ورقم الصفحة بدقة.
6. التمييز بين أنواع التوثيق:
   - [اقتباس حرفي - QUOTATION]: نقل العبارة بنصها الحرفي من كتاب الأب.
   - [صياغة تحليلية - PARAPHRASE]: استخلاص وشرح المعنى اللاهوتي والفكري.
   - [استنتاج مركب - SYNTHESIS]: الربط بين عدة شواهد لتأكيد وحدة الإيمان المسلّم مرة للقديسين.
7. البناء الهيكلي الأكاديمي المعتمد:
   - 📌 **المقدمة والعقيدة الأساسية**: التعريف اللاهوتي الجامع والشامل للمفهوم في التقليد الأرثوذكسي القويم.
   - 🏛️ **المحور الأول: البيان الآبائي والنصوص الموثقة**: شواهد ونصوص الآباء المباشرة المقتبسة، مع شرحها لاهوتياً ولغوياً.
   - ⚖️ **المحور الثاني: مقارنة الرؤى والمدارس الكنسية (إن وجدت في المسألة)**: استعراض رؤية مدرسة البابا شنودة الثالث، ومدرسة القمص متى المسكين، وتبيان المرجعية الآبائية المشتركة لهما.
   - 📜 **المحور الثالث: الأبعاد الخلاصية واللاهوتية**: أسباب التجسد، إبطال الفساد والموت، تجديد الطبيعة في الإنسان، والخلاص الكامل.
   - 🕊️ **المحور الرابع: التطبيق الكنسي والروحي المعاش**: كيف ينعكس هذا الإيمان في صلاة المؤمن اليومية وجهاده الروحي وسر الإفخارستيا.
   - 📚 **المصادر والمراجع الموثقة**: قائمة مرقمة بكافة المراجع المستخدمة تشمل: اسم الكتاب، المؤلف، رقم الصفحة، والمراجع الآبائية المقابلة (PG / NPNF / Katameros).

تنبيه قطعي: يمنع منعاً باتاً تكرار نص هذه التعليمات، ابدأ مباشرة بتقديم الدراسة اللاهوتية المنهجية الموثقة.
"""

DEPTH_INSTRUCTIONS: Dict[str, str] = {
    "academic": (
        "\nالنمط المعتمد: [النمط الأكاديمي الموسع والمقارن]\n"
        "ركّز على التأصيل الآبائي الدقيق، والمصطلحات اللاهوتية الأصلية (اليونانية والكنسية)، "
        "وتحليل النصوص واقتباسها نصياً مع التمييز الواضح بين [اقتباس حرفي - QUOTATION] و[صياغة تحليلية - PARAPHRASE] و[استنتاج مركب - SYNTHESIS]."
    ),
    "pastoral": (
        "\nالنمط المعتمد: [النمط الرعوي والروحي المعاش]\n"
        "ركّز على التطبيق العملي للتعليم في حياة المؤمن اليومية، وجهاد الصلاة والصوم والتوبة، ومساندة الخدام في الوعظ والتعليم، "
        "مع إبراز كلمات العزاء والرجاء المستندة بدقة إلى الآباء وشواهد المكتبة دون أي هلوسة."
    ),
    "apologetic": (
        "\nالنمط المعتمد: [النمط الدفاعي واللاهوت المقارن]\n"
        "ركّز على تفنيد الشبهات والإجابة المنهجية عن التساؤلات العقائدية، وإبراز استقامة الإيمان الأرثوذكسي المسلّم مرة للقديسين، "
        "مع الاستناد إلى قرارات المجامع المسكونية ونصوص الآباء المدافعين وكشف الفروق الجوهرية بوقار ومحبة ودقة علمية."
    )
}


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini API Provider with strict verified citation typology and structured answer generation."""

    # Priority order for high-quota, ultra-fast and active models on Gemini API
    CANDIDATE_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.5-flash-lite"
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
                max_output_tokens=2600
            )

            depth_text = DEPTH_INSTRUCTIONS.get(depth_mode, DEPTH_INSTRUCTIONS["academic"])
            active_sys_prompt = f"{THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT}\n{depth_text}"

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=active_sys_prompt
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 12}
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
                max_output_tokens=2600
            )

            depth_text = DEPTH_INSTRUCTIONS.get(depth_mode, DEPTH_INSTRUCTIONS["academic"])
            active_sys_prompt = f"{THEOLOGICAL_STRUCTURED_SYSTEM_PROMPT}\n{depth_text}"

            for model_name in self.CANDIDATE_MODELS:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=active_sys_prompt
                    )
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 12}
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    continue

        except Exception as e:
            logger.warning(f"Conversational generation error: {e}")

        latest = messages[-1]["content"] if messages else ""
        return self.fallback.generate_answer(latest, context_chunks)

