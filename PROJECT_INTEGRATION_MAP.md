# ✠ ELANTONY LIBRARY AI - خريطة الدمج والتكامل البرمجي
## PROJECT INTEGRATION MAP & COMPONENT TOPOLOGY

**تاريخ الإصدار:** 2026-11-04  
**الحالة:** مدمج ومفعل تشغيلياً (Operational & Verified)  
**المرجع:** ISO/IEC 25010 Software Architecture Standards  

---

### 1. خريطة الطوبولوجيا الهيكلية الموحدة (System Topology Map)

```mermaid
flowchart TD
    subgraph Client_Interfaces ["1. واجهات الاستخدام (Client Layer)"]
        TG["🤖 Telegram Bot (@ElantonyLibrarybot)"]
        WEB["🌐 Research Web Portal (FastAPI & Marked.js)"]
        AUDIO_CLIENT["🔊 Audio recitation client / Streamer"]
    end

    subgraph Gateway_Orchestration ["2. بوابة الذكاء الاصطناعي متعددة النماذج (AI Gateway)"]
        GW["⚡ Elantony Multi-Model Gateway (elantony/ai/gateway.py)"]
        ROUTER{"🧭 Dynamic Intent & Complexity Router"}
        CASCADE["🔄 Cascading Failover Engine"]
    end

    subgraph AI_Providers ["3. مزودو النماذج الاستدلالية (Model Providers)"]
        GEMINI["Google Gemini 2.5 (Flash / Pro)"]
        KIMI["Moonshot Kimi K3 (200k Context)"]
        DEEPINFER["DeepInfer (Local DeepSeek-R1 / Ollama)"]
        ZENMUX["ZenMux / BeatAPI Gateways"]
        RULE_BASED["Church Rule-Based Engine (100% Offline)"]
    end

    subgraph Church_RAG_Core ["4. محرك البحث والتوثيق الكنسي (RAG Core)"]
        FTS5["🔍 SQLite FTS5 Full-Text Engine"]
        VERIFIER["🛡️ Citation Verification & Anti-Hallucination Guard"]
        AUDIO_SRV["🎙️ Audio & Patristic Recitation (gTTS Service)"]
        DOCX_EXP["📑 Word Research Monograph Exporter"]
    end

    subgraph Data_Storage ["5. طبقة البيانات والتخزين (Persistence & Storage)"]
        SQLITE[("🗄️ file_archive.db (7,200 Books / WAL Mode)")]
        HF_DATASET[("☁️ Hugging Face Dataset Backup")]
        LOCAL_STORAGE["📁 Physical Library Root (I:\2021\2020\...)"]
    end

    TG --> GW
    WEB --> GW
    AUDIO_CLIENT --> AUDIO_SRV
    
    GW --> ROUTER
    ROUTER --> CASCADE
    CASCADE --> GEMINI
    CASCADE --> KIMI
    CASCADE --> DEEPINFER
    CASCADE --> ZENMUX
    CASCADE --> RULE_BASED

    GW <--> VERIFIER
    VERIFIER <--> FTS5
    FTS5 <--> SQLITE
    WEB --> DOCX_EXP
    WEB --> AUDIO_SRV
    SQLITE -.-> HF_DATASET
    SQLITE <--> LOCAL_STORAGE
```

---

### 2. جدول مطابقة الملفات والمكونات المدمجة (File Integration Mapping)

| المكون الأصلي | المصدر البرمجي | المسار الجديد في Elantony | طبيعة الدمج والتحسين |
|---|---|---|---|
| **Universal AI Gateway** | تصميم معماري جديد | `elantony/ai/gateway.py` | تنسيق وتوجيه الطلبات عبر النماذج المتعددة، والتبديل التلقائي عند التعطل. |
| **OpenAI-Compatible Adapter** | واجهات Kimi, DeepInfer, ZenMux | `elantony/ai/openai_compatible_provider.py` | محول موحد يدعم أي نموذج يتوافق مع معيار OpenAI مع فرض قوالب الاستشهاد الكنسي. |
| **Speech Recitation (TTS)** | `D:\Prog\tts` (`run_tts 2.bat`) | `elantony/services/audio_service.py` | تحويل نصوص وشواهد الآباء إلى صوت عربي مسموع بجودة نقية مع التخزين في الذاكرة. |
| **Web REST Audio Endpoint** | جديد | `elantony/web/api.py` (`/api/audio/tts`) | توفير نقطة وصول سحابية لبث الصوتيات المسموعة مباشرة إلى المتصفح وتطبيقات الهاتف. |
| **Word Monograph Exporter** | تطوير مرحلي متقدم | `elantony/services/docx_exporter.py` | تصدير الأبحاث والمسائل اللاهوتية إلى ملفات Word كاملة التنسيق باللغة العربية مع الحواشي. |
| **Anti-Hallucination Guard** | خوارزمية التوثيق الكنسي | `elantony/ai/gemini_provider.py` | تصنيف الاستشهادات إلى [اقتباس حرفي] و[صياغة تحليلية] ومنع اختلاق أي أرقام صفحات. |
| **Sermon Transcriber Bridge** | `D:\Prog\Transcriber_Project` | معزول كخدمة استدعاء اختيارية | تفريغ الملفات الصوتية عند الحاجة دون تحميل الذاكرة بنماذج Whisper الثقيلة افتراضياً. |
| **Cloud Dataset Backup** | Hugging Face Dataset API | `scripts/deploy_to_huggingface.py` | ضغط قاعدة البيانات إلى `file_archive.zip` ورفعها برابط مباشر مجاني ودائم. |

---

### 3. معالجة التضاربات والازدواجية (Conflict Resolution Matrix)

1. **إلغاء التكرار بين مزودي الذكاء الاصطناعي:**
   - *المشكلة:* احتمالية إرسال السؤال إلى عدة نماذج في نفس الوقت مما يستنزف الرصيد ويزيد زمن الاستجابة.
   - *الحل:* اعتماد `Dynamic Intent Router` الذي يرسل الطلب إلى مزود واحد فقط مختار بعناية، ولا يفعّل المزود التالي إلا إذا فشل الأول (Failover Cascade).
2. **عزل خادم التيليجرام:**
   - *المشكلة:* تعارض تشغيل Polling متعدد على نفس الـ Bot Token مما يتسبب في خطأ `Conflict: terminated by other getUpdates request`.
   - *الحل:* تشغيل البوت حصرياً عبر الـ Daemon الرئيسي (`services/permanent_assistant/daemon.py`) بينما يعمل خادم الويب `uvicorn` في وضع Standalone Web دون بدء تشغيل Polling مكرر.
3. **حماية مفاتيح الـ APIs والأسرار:**
   - *المشكلة:* تسريب التوكنات على GitHub أو في ملفات التقرير.
   - *الحل:* حظر الرفع عبر `.gitignore`، واستدعاء كافة المفاتيح حصرياً من متغيرات البيئة عبر `elantony.core.config.settings`.
