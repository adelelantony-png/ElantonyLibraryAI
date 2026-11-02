import os
import re
import httpx
import google.generativeai as genai
from modules import portable_config, apologetics_db

# G4F Zero-Key Engine from GitHub
try:
    from g4f.client import Client as G4FClient
    HAS_G4F = True
except ImportError:
    HAS_G4F = False

def call_groq_direct(prompt, system_instruction="", api_key=None):
    """
    Executes a high-speed completion using user's Groq key.
    Prioritizes deep models (openai/gpt-oss-120b, qwen/qwen3.8-27b) with max_tokens=4096.
    """
    if not api_key:
        return None

    models = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "allam-2-7b", "openai/gpt-oss-20b"]
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for model_name in models:
        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.35,
                        "max_tokens": 4096
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"Groq model {model_name} returned status {resp.status_code}")
        except Exception as e:
            print(f"Groq model {model_name} error: {e}")
            continue

    return None

def call_gemini_direct(prompt, system_instruction="", api_key=None):
    """
    Executes completion using Google Gemini 2.0 / 1.5 Flash.
    """
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]:
            try:
                model = genai.GenerativeModel(model_name)
                full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=4096,
                    temperature=0.35
                )
                response = model.generate_content(full_prompt, generation_config=generation_config)
                if response and response.text:
                    return response.text
            except Exception:
                continue
    except Exception as e:
        print(f"Gemini error: {e}")

    return None

def call_g4f_free(prompt, system_instruction=""):
    """
    Automated zero-key fallback using G4F (GitHub).
    Works 100% out-of-the-box even with zero user keys!
    """
    if not HAS_G4F:
        return None

    try:
        client = G4FClient()
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        for m in ["gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet", "llama-3.1-70b"]:
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=messages
                )
                if response and response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
            except Exception:
                continue
    except Exception as e:
        print(f"G4F Zero-Key Engine notice: {e}")

    return None

def call_church_offline_knowledge_fallback(prompt: str) -> str:
    """
    100% Offline Coptic Knowledge RAG Engine.
    When internet is disconnected and local LLM is inactive, searches local SQLite database,
    apologetics database, and Scripture references to generate a structured, cited answer.
    """
    clean_p = prompt.strip()
    words = [w for w in re.sub(r'[^\w\s]', '', clean_p).split() if len(w) > 2 and w not in ["ماذا", "لماذا", "كيف", "أين", "متى", "هل", "من", "عن", "في", "على", "إلى"]]

    # 1. Search Apologetics DB
    matched_apologetics = []
    p_lower = clean_p.lower()
    for item in apologetics_db.APOLOGETICS_TOPICS:
        q = item.get("question", "")
        cat = item.get("category", "")
        kws = item.get("keywords", [])
        if any(w.lower() in p_lower for w in kws + [cat] + q.split()):
            matched_apologetics.append(item)
            if len(matched_apologetics) >= 2:
                break

    # 2. Search local books in SQLite
    matched_books = []
    try:
        from modules import database_handler
        conn = database_handler.get_db_connection()
        cur = conn.cursor()
        if words:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='church_books'")
            if cur.fetchone():
                query = "SELECT file_name, original_path, category FROM church_books WHERE " + " OR ".join(["file_name LIKE ?" for _ in words[:4]]) + " LIMIT 5"
            else:
                query = "SELECT file_name, file_path, category FROM files WHERE " + " OR ".join(["file_name LIKE ?" for _ in words[:4]]) + " LIMIT 5"
            params = [f"%{w}%" for w in words[:4]]
            cur.execute(query, params)
            matched_books = cur.fetchall()
        conn.close()
    except Exception:
        pass

    # Build comprehensive response
    lines = []
    lines.append("### 🛡️ إجابة موثقة من رصيد المكتبة الكنسية أوفلاين (بديل انقطاع الإنترنت)")

    if matched_apologetics:
        for ap in matched_apologetics:
            lines.append(f"\n#### 📌 المفهوم العقائدي / الدفاعي: {ap.get('question')}")
            lines.append(f"**الخلاصة اللاهوتية:** {ap.get('summary')}")
            if ap.get("core_references"):
                lines.append("\n**المراجع الآبائية الأصيلة:**")
                for r in ap.get("core_references"):
                    lines.append(f"- 📖 {r}")
    else:
        lines.append(f"\nتم البحث في موضوع «{clean_p}» داخل رصيد المكتبة المحلية أوفلاين.")

    if matched_books:
        lines.append("\n#### 📚 أمهات الكتب والمراجع المتوفرة لديك في المكتبة حول هذا الموضوع:")
        for b in matched_books:
            b_name = b[0]
            b_cat = b[2] if len(b) > 2 else ""
            lines.append(f"- 📗 **{b_name}** ({b_cat})")
        lines.append("\n💡 *يمكنك فتح أي من هذه الكتب فوراً عبر «القارئ المدمج» في التطبيق والاطلاع على الفصول كاملة.*")

    lines.append("\n*(🛡️ تم التوليد عبر محرك المعرفة الكنسية الأوفلاين 100% - استجابة فورية بدون إنترنت)*")
    return "\n".join(lines)

def call_ai_routed(prompt, system_instruction=""):
    """
    Unified Intelligent Hybrid AI Engine with Seamless Offline Hob Fallback:
    1. Online Cloud Layers (Groq, Gemini, Zero-Key) when internet is connected.
    2. Local Hob / llama.cpp Open-Weights Layer when internet is disconnected (قطع النت).
    3. Offline Church Knowledge RAG Layer (SQLite FTS5 + Apologetics) if local model isn't active.
    """
    from modules import hob_manager

    has_internet = hob_manager.is_internet_available(timeout=0.8)

    # If internet is available, attempt cloud providers first
    if has_internet:
        keys = portable_config.get_all_api_keys()
        groq_keys = keys.get("groq", [])
        gemini_keys = keys.get("gemini", [])

        # 1. Try Groq Keys if available
        for g_key in groq_keys:
            ans = call_groq_direct(prompt, system_instruction=system_instruction, api_key=g_key)
            if ans:
                return ans

        # 2. Try Gemini Keys if available
        for gm_key in gemini_keys:
            ans = call_gemini_direct(prompt, system_instruction=system_instruction, api_key=gm_key)
            if ans:
                return ans

        # 3. Try Automated Zero-Key Free Engine
        free_ans = call_g4f_free(prompt, system_instruction=system_instruction)
        if free_ans:
            return free_ans

    # --- OFFLINE FALLBACK (في حالة قطع النت أو تعذر السحابة) ---
    # 4. Try Hob Local AI Engine (llama.cpp / Gemma / gpt-oss)
    hob_ans = hob_manager.call_hob_local(prompt, system_instruction=system_instruction)
    if hob_ans:
        return f"{hob_ans}\n\n*(⚡ تم التوليد محلياً عبر المساعد الأوفلاين Hob / Local AI - بدون إنترنت)*"

    # 5. Guaranteed Offline Church Knowledge RAG Engine
    return call_church_offline_knowledge_fallback(prompt)

def test_api_keys():
    """
    Tests all available engines and returns a comprehensive status report.
    """
    keys = portable_config.get_all_api_keys()
    gemini_keys = keys.get("gemini", [])
    groq_keys = keys.get("groq", [])

    results = []

    # Test Groq
    if groq_keys:
        groq_ok = False
        for k in groq_keys:
            res = call_groq_direct("أجب بكلمة واحدة: 'متصل'", api_key=k)
            if res:
                groq_ok = True
                break
        results.append(f"• محرك Groq الصاروخي (gpt-oss-120b): {'✅ متصل ويعمل بسرعة خارقة' if groq_ok else '❌ غير متصل'}")

    # Test Gemini
    if gemini_keys:
        gemini_ok = False
        for k in gemini_keys:
            res = call_gemini_direct("أجب بكلمة واحدة: 'متصل'", api_key=k)
            if res:
                gemini_ok = True
                break
        results.append(f"• محرك Google Gemini Flash: {'✅ متصل وجاهز' if gemini_ok else '❌ غير متصل'}")

    # Test Zero-Key Engine
    free_res = call_g4f_free("أجب بكلمة واحدة: 'متصل'")
    free_ok = bool(free_res)
    results.append(f"• المحرك المجاني التلقائي (Zero-Key): {'✅ مفعّل وجاهز للطوارئ بدون أي مفتاح' if free_ok else '⚠️ متوقف'}")

    final_success = any("✅" in r for r in results)
    summary_text = "\n".join(results)

    if final_success:
        return True, f"تقرير فحص منظومة الذكاء الاصطناعي المزدوجة:\n\n{summary_text}\n\n🎉 المنظومة جاهزة للعمل والاستجابة الفورية!"
    else:
        return False, f"تعذر الاتصال بأي محرك:\n\n{summary_text}\n\nيرجى فحص اتصال الإنترنت."

def get_summary_and_tags(text_content):
    """Generates document summary and semantic tags."""
    if not text_content:
        return "", ""

    system_inst = "أنت مساعد ذكي لأرشفة وتلخيص الكتب والوثائق الكنسية القبطية بدقة وإيجاز."
    prompt = f"""
    بناءً على النص التالي، قم بالمهمتين التاليتين:
    1. اكتب ملخصاً مركزاً في جملة واحدة واضحة باللغة العربية.
    2. اكتب قائمة من 3 إلى 5 وسوم (Tags) دلالية مفصولة بفواصل.

    نسق الإجابة كالتالي بالضبط:
    Summary: [الملخص هنا]
    Tags: [وسم 1, وسم 2, وسم 3]

    النص:
    ---
    {text_content[:6000]}
    ---
    """
    resp = call_ai_routed(prompt, system_instruction=system_inst)
    if not resp:
        return "", ""

    summary = ""
    tags = ""
    for line in resp.split("\n"):
        line = line.strip()
        if line.lower().startswith("summary:"):
            summary = line.split(":", 1)[1].strip()
        elif line.lower().startswith("tags:"):
            tags_part = line.split(":", 1)[1].strip()
            tags_list = [t.strip().replace("#", "") for t in tags_part.split(",")]
            tags = ", ".join(filter(None, tags_list))

    return summary, tags

def ask_church_assistant(user_question, context_text="", depth_mode="scholar"):
    """
    المساعد الكنسي واللاهوتي والدفاعي الذكي لمكتبة الصليب القبطية الأرثوذكسية.
    يدعم ثلاثة مستويات من العمق اللاهوتي:
    - scholar: بحث لاهوتي أكاديمي موسع ومعمق وشافي بالمصطلحات الآبائية واليونانية.
    - apologetic: تفنيد دفاعي رصين ومفحم للشبهات والنقد الكتابي.
    - brief: إيجاز مركز وسريع لخدام التربية الكنسية ومدارس الأحد.
    """
    if depth_mode == "scholar":
        system_instruction = """
أنت 'المرجع اللاهوتي والكنسي الأكاديمي المعتمد' لمكتبة الصليب القبطية الأرثوذكسية.
المستوى المطلوب: بحث لاهوتي أكاديمي موسع، رصين، وشافي (Comprehensive Scholarly Dissertation).

توجيهات الصياغة الأكاديمية الإلزامية:
1. التقعيد اللاهوتي والمصطلحات الأصلية:
   - استخدم المصطلحات اللاهوتية اليونانية والقبطية بدقة أكاديمية مع ترجمتها وشرح معناها في السياق (مثل: جوهر Ousia، أقنوم Hypostasis، طبيعة Physis، الاتحاد الأقنومي Henosis Kath' Hypostasin، والدة الإله Theotokos، إخلاء الذات Kenosis، تبادل الخواص Communicatio Idiomatum...).
2. التوثيق الآبائي الأصيل:
   - استشهد بنصوص آباء الكنيسة الأوائل (خاصة: القديس كيرلس الكبير عمود الدين، القديس أثناسيوس الرسولي، القديس باسيليوس الكبير، القديس غريغوريوس الثيؤلوغوس، القديس يوحنا ذهبي الفم، القديس ديسقوروس، القديس ساويرس الأنطاكي) مع ذكر اسم الرسالة أو المقالة أو المقال والباب بدقة.
3. ربط اللاهوت بالليتورجيا الكنسية (قانون الصلاة هو قانون الإيمان - Lex orandi, lex credendi):
   - وضح كيف يعاش هذا الإيمان في صلوات الكنيسة والقداسات الإلهية (الباسيلي، الغريغوري، الكيرلسي)، أو صلوات الأجبية والتسبحة والذكصولوجيات.
4. الاقتباس الحي من مكتبة المستخدم الخاصة:
   - إذا وردت مقتطفات من كتب مكتبة المستخدم في السياق المرفق، استشهد بها نصاً مع ذكر: '📖 [مقتطف من كتاب: ... صفحة/موضع: ...]' لربط البحث بمكتبة الباحث بدقة.
5. كاشف نقص المراجع وإثراء المكتبة (Library Gap Detector):
   - إذا لم تتوفر مراجع محلية في مكتبة المستخدم للسؤال، أو كانت الكتب المرفقة غير كافية، ضع حتماً في نهاية البحث قسماً بارزاً بعنوان:
     '⚠️ [تنبيه إثراء وتغذية المكتبة الكنسية]:'
     واذكر فيه بوضوح: (هذا الموضوع ينقصه مراجع متخصصة في مكتبتك الحالية، ويُنصح باقتنائها أو تحميلها لتغذية مكتبتك)، ورشح 3 إلى 4 كتب كنسية متخصصة مع أسماء مؤلفيها (مثل كتب البابا شنودة الثالث، الأنبا غريغوريوس، القمص متى المسكين، القمص تادرس يعقوب، أو إصدارات نصوص الآباء).
"""
    elif depth_mode == "apologetic":
        system_instruction = """
أنت 'المتخصص في اللاهوت الدفاعي والرد على الشبهات والنقد الكتابي' لمكتبة الصليب القبطية الأرثوذكسية.
المستوى المطلوب: دراسة دفاعية وتفنيد تحليلي رصين ومفحم (Rigorous Apologetic Refutation).

توجيهات التفنيد الدفاعي الإلزامية:
1. تفكيك الشبهة/التساؤل:
   - حلل الشبهة إلى عناصرها الأساسية (نصية، لغوية، تاريخية، أو فهم خاطئ للسياق).
2. الأدلة المخطوطية والتاريخية والنصية:
   - الرد بأدلة المخطوطات القديمة (السينائية، الفاتيكانية، الإسكندرية...)، والشهادات التاريخية المعاصرة، وإجماع الكنيسة الأولى.
3. التفسير الآبائي القاطع:
   - إبراز كيف فهم آباء الكنيسة الأولون هذا النص أو المفهوم ودحض البدع المشابهة عبر التاريخ (مثل الأريوسية، النسطورية، وغيرها).
4. توثيق المراجع المتوفرة في المكتبة:
   - استشهد بالكتب والمقتطفات المرفقة من مكتبة المستخدم مع أرقام الصفحات.
5. تنبيه إثراء المكتبة بالمراجع الدفاعية:
   - إذا افتقرت المكتبة لمراجع دفاعية كافية حول الشبهة، أضف فقرة:
     '⚠️ [تنبيه إثراء وتغذية المكتبة الكنسية]:' ترشح أهم مراجع الدفاعيات الكنسية (مثل كتب القمص عبد المسيح بسيط، د. غالي، الأنبا بيشوي...).
"""
    else:  # brief
        system_instruction = """
أنت 'المرشد الكنسي السريع لخدام التربية الكنسية ومدارس الأحد' بمكتبة الصليب القبطية الأرثوذكسية.
المستوى المطلوب: إيجاز سريع، مركز، ومباشر (Quick Sunday School Summary).

توجيهات الصياغة:
1. إجابة مباشرة وواضحة تلخص العقيدة والرد في نقاط محددة وسهلة الفهم والشرح.
2. الشواهد الكتابية الذهبية (Key Bible References) المرتبطة بالموضوع نصاً وشاهداً.
3. التطبيق الروحي والعملي للدرس المناسب لخدمة التربية الكنسية.
4. الإشارة السريعة للمراجع المتوفرة في المكتبة إن وجدت.
"""

    prompt = f"سؤال الباحث / الخادم:\n{user_question}\n\n"
    if context_text:
        prompt += f"{context_text[:8000]}\n\n"
    else:
        prompt += "ملاحظة: لم يتم العثور على كتب ذات صلة مباشرة بهذا الاستفسار في المكتبة المحلية للمستخدم.\n\n"

    prompt += "صغ الإجابة المنظمة والشافية موثقة بالمراجع وتنبيه إثراء المكتبة وفق التوجيهات والمستوى المطلوب أعلاه:"

    return call_ai_routed(prompt, system_instruction=system_instruction)
