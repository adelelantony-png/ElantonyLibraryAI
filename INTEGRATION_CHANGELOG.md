# ✠ ELANTONY LIBRARY AI - سجل التغييرات والدمج البرمجي
## INTEGRATION CHANGELOG & AUDIT LOG

**الإصدار:** 3.0.0  
**التاريخ:** 2026-11-04  
**نوع الترقية:** Enterprise Multi-Model & Multimodal Upgrade  

---

### [الإصدار 3.0.0] - 2026-11-04

#### 🚀 المكونات والملفات الجديدة (New Additions)
- `elantony/ai/gateway.py`:
  - إنشاء **Elantony Multi-Model Gateway** المنسق للموديلات المتعددة (Gemini, Kimi, DeepInfer, ZenMux, BeatAPI, Rule-Based).
  - دعم التوجيه الديناميكي بحسب صعوبة المسألة (Dynamic Complexity Routing).
  - تفعيل نظام التعاقب التلقائي (Cascading Failover) عند حدوث أي انقطاع في الشبكة أو نفاد الحصص.
- `elantony/ai/openai_compatible_provider.py`:
  - بناء محول معتمد وموحد للنماذج المتوافقة مع معيار OpenAI API.
  - تطبيق قيود التوثيق الكنسي والأصالة ومنع الهلوسة على كافة النماذج الخارجية.
- `elantony/services/audio_service.py`:
  - دمج خدمة تلاوة ونطق أقوال الآباء والصلوات صوتياً بجودة نقية مستخلصة من مشروع `D:\Prog\tts`.
  - معالجة النصوص وتجريدها من الرموز لتوفير صوت ناعم ومريح للأذن.
- `tests/test_master_integration.py`:
  - إنشاء حزمة اختبارات تكاملية شاملة تضم 7 اختبارات تفصيلية تغطي كل مكونات البوابة، والتوجيه، والبحث، والصوت، وتصدير Word، وقاعدة البيانات.
- `scripts/deploy_to_huggingface.py`:
  - سكريبت أتمتة ضغط ورفع قاعدة البيانات على Hugging Face Datasets برابط دائم.

#### 🔧 الملفات المعدلة والمطورة (Modified Files)
- `elantony/ai/factory.py`:
  - ترقية وظيفة `get_ai_provider()` لتعتمد على `MultiModelGateway` افتراضياً مع الحفاظ على التوافق التام مع استدعاء النماذج القديمة بالاسم.
- `elantony/web/api.py`:
  - إضافة نقطة الوصول الصوتية `@app.post("/api/audio/tts")` للبث الحي للصوت بصيغة MP3.
  - دعم أنماط العمق اللاهوتي الثلاثة (`academic`, `pastoral`, `apologetic`).
  - دعم تصدير الجلسات البحثية مباشرة كملفات Word (`.docx`).
  - توفير نقاط عرض وتنزيل ملفات الـ PDF الأصلية للكتب المسترجعة (`/api/books/{sha256}/view`).
- `elantony/telegram/handlers.py` و `keyboards.py`:
  - ربط اختيارات العمق اللاهوتي داخل البوت لضمان تطابق التجربة تماماً مع واجهة الويب.

#### 🛡️ الحماية والأمان (Security & Reliability)
- عدم حفظ أو تضمين أي مفاتيح API داخل شفرة المشروع (Zero Hardcoded Secrets).
- الحفاظ التام والكامل على بنية قاعدة البيانات الأصلية وملفات الكتب (7,200 كتاب / ~50GB).
- حصر معالجة تليجرام في نسخة واحدة مفردة لمنع أي تضارب Polling.
