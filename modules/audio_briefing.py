"""
Cross Coptic Library - Audio Briefing & Theological Podcast Generator
الموجز الصوتي الذكي «اسمع البحث»
Generates high-fidelity Arabic voice briefings (.mp3) from theological and apologetic treatises
using Edge-TTS Neural Arabic Voices (ar-EG-ShakirNeural / ar-EG-SalmaNeural) for servants on the go.
"""

import os
import re
import asyncio
import edge_tts
from modules import ai_handler

DEFAULT_VOICE = "ar-EG-ShakirNeural" # Dignified Egyptian Arabic male voice
ALTERNATIVE_VOICE = "ar-EG-SalmaNeural"

def generate_voice_script(topic: str, treatise_content: str) -> str:
    """
    Synthesizes a fluent, dignified 2-3 minute spoken audio script in classical Arabic.
    """
    prompt = (
        f"أنت راوٍ ومذيع لاهوتي مسيحي قبطي أرثوذكسي رصين.\n"
        f"قم بصياغة نص صوتي موجز ومحكم (مدة الإلقاء حوالي 2 إلى 3 دقائق) "
        f"ليُقرأ صوتياً لتلخيص البحث التالي حول موضوع: '{topic}'.\n\n"
        f"الهيكل المطلوب للنص المسموع:\n"
        f"1. الافتتاحية: 'باسم الآب والابن والروح القدس، الإله الواحد، آمين. موجز بحث دفاعي من مكتبة الصليب القبطية الأرثوذكسية حول: {topic}'.\n"
        f"2. صلب الشبهة ومنشؤها المغلوط في فقرة موجزة.\n"
        f"3. شهادة العلم والآثار المحايدة والمؤرخين غير المسيحيين.\n"
        f"4. الشاهد الكتابي والبرهان العقلي السليم.\n"
        f"5. إجماع الآباء القديسين.\n"
        f"6. الخاتمة والدعوة لمراجعة البحث الكامل في المكتبة.\n\n"
        f"النص المراد تلخيصه:\n{treatise_content[:3500]}\n\n"
        f"اكتب فقط النص الذي سيُنطق باللغة العربية الفصحى دون أي تعليقات جانبية أو تنسيقات markdown معقدة."
    )

    try:
        script = ai_handler.call_ai_routed(
            prompt,
            system_instruction="أنت مذيع لاهوتي مسيحي قبطي أرثوذكسي محترف يصيغ نصوصاً إذاعية فصيحة وسلسة للإلقاء الصوتي."
        )
        # Strip any residual markdown
        script = re.sub(r'[*#_`~]', '', script).strip()
    except Exception as ex:
        # Fallback script
        script = (
            f"باسم الآب والابن والروح القدس، الإله الواحد، آمين. "
            f"موجز بحث دفاعي من مكتبة الصليب القبطية الأرثوذكسية حول {topic}. "
            f"يقدم هذا البحث تفنيداً علمياً وتاريخياً وكتابياً متكاملاً يستند إلى أحدث اكتشافات الآثار والمؤرخين المحايدين، "
            f"بالإضافة إلى إجماع آباء الكنيسة الجامعة وتفسير النصوص في سياقها الأصلي الصحيح. "
            f"يمكنكم الاطلاع على الدراسة الموثقة بالكامل والمراجع عبر ملف الوورد المحفوظ في أرشيف مكتبتكم."
        )

    return script

async def text_to_speech_async(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    """Uses edge_tts to generate the MP3 audio file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate="+0%", pitch="+0Hz")
    await communicate.save(output_path)
    return output_path

def generate_audio_briefing(topic: str, treatise_content: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Synchronous wrapper to generate audio briefing MP3.
    Returns path to the generated MP3 file.
    """
    script = generate_voice_script(topic, treatise_content)
    asyncio.run(text_to_speech_async(script, output_path, voice=voice))
    return output_path
