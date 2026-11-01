"""
Cross Coptic Library - Neutral Science & Secular Historians Knowledge Base
(بنك أدلة العلم المحايد والآثار والمؤرخين غير المسيحيين)
Provides verified, peer-reviewed secular citations, museum artifacts, Roman/Jewish historical texts,
and cosmological/biological proofs supporting Christian theology and biblical reliability.
"""

import re

NEUTRAL_EVIDENCE_CATALOG = [
    # --- 1. علم الآثار والمتاحف العالمية ---
    {
        "category": "الآثار والنقوش القديمة",
        "title": "حجر تل القاضي (نقش تل دان - Tel Dan Stele)",
        "source": "المتحف الإسرائيلي بالقدس / اكتشاف د. أبراهام بيران (1993)",
        "field": "آثار الشرق الأدنى القديم",
        "neutral_proof": "نقش أرامي من القرن التاسع قبل الميلاد يذكر صراحة 'بيت داود' (House of David) والملك يهورام، مما أسقط ادعاءات المشككين بأن الملك داود شخصية أسطورية وأثبت وجود مملكته تاريخياً.",
        "keywords": ["داود", "الملك داود", "تاريخ", "العهد القديم", "أساطير", "تلفيق", "ملوك"]
    },
    {
        "category": "الآثار والنقوش القديمة",
        "title": "حجر بيلاطس البنطي (Pilate Stone)",
        "source": "متحف إسرائيل / اكتشاف البعثة الإيطالية بقيادة أنطونيو فروبا في قيسارية (1961)",
        "field": "آثار العصر الروماني",
        "neutral_proof": "حجر جيري نُقش عليه باللاتينية اسم بيلاطس ولقبه الرسمي: 'Pontius Pilatus, Praefectus Iudaeae' (بيلاطس البنطي حاكم اليهودية)، قاطعاً كل شكوك النقاد حول وجود بيلاطس ومحاكمته للمسيح.",
        "keywords": ["بيلاطس", "صلب المسيح", "محاكمة المسيح", "تاريخية المسيح", "الأناجيل"]
    },
    {
        "category": "الآثار والنقوش القديمة",
        "title": "أسطوانة كورش الشهيرة (Cyrus Cylinder)",
        "source": "المتحف البريطاني بلندن (غرفة 55) / عُثر عليها في بابل (1879)",
        "field": "الوثائق الإمبراطورية البابلية والفارسية",
        "neutral_proof": "مرسوم إمبراطوري طيني من الملك كورش الفارسي (539 ق.م) يأمر بإعادة الشعوب المسبيّة وإعادة بناء معابدها، وهو تطابق وثائقي مذهل مع ما دونه سفرا عزرا وإشعياء عن عودة السبي وبناء الهيكل.",
        "keywords": ["كورش", "السبي", "بابل", "عزرا", "إشعياء", "النبوات"]
    },
    {
        "category": "الآثار والنقوش القديمة",
        "title": "صندوق عظام يوسف بن قيافا (Caiaphas Ossuary)",
        "source": "سلطة الآثار في القدس (1990)",
        "field": "آثار المقابر اليهودية في القرن الأول",
        "neutral_proof": "صندوق عظام حجري مزخرف من القرن الأول الميلادي يحمل نقشاً آرامياً: 'يهوسف بار قيافا' (يوسف بن قيافا)، رئيس الكهنة الذي ترأس محاكمة السيد المسيح المذكور في الأناجيل وتاريخ يوسيفوس.",
        "keywords": ["قيافا", "رئيس الكهنة", "محاكمة المسيح", "الأناجيل"]
    },
    {
        "category": "الآثار والنقوش القديمة",
        "title": "بركة سلوام وبركة بيت حسدا",
        "source": "اكتشافات أثرية مستقلة في القدس (2004 - د. روني رايخ)",
        "field": "جغرافيا أورشليم التوراتية",
        "neutral_proof": "اكتشاف بركة سلوام الحقيقية ذات الأدراج الحجرية وبركة بيت حسدا ذات الأروقة الخمسة، مؤكداً دقة الوصف الطوبوغرافي لإنجيل يوحنا الذي كان المشككون يزعمون أنه كُتب متأخراً بعيداً عن فلسطين.",
        "keywords": ["يوحنا", "بركة سلوام", "بيت حسدا", "جغرافيا الأناجيل", "موثوقية العهد الجديد"]
    },
    {
        "category": "الآثار والنقوش القديمة",
        "title": "شهادة السير وليم أولبرايت وعمداء الآثار المحايدين",
        "source": "د. وليم أولبرايت (W.F. Albright) ود. نلسون جلوك (Nelson Glueck)",
        "field": "علم الآثار الأكاديمي المقارن",
        "neutral_proof": "إقرار عالم الآثار نلسون جلوك: 'لم يحدث قط أن ناقض اكتشاف أثري نصاً كتابياً واحداً'، وتأكيد أولبرايت أن النقد الراديكالي للقرن الثامن عشر قد سحقته الحفريات الأثرية في الشرق الأوسط.",
        "keywords": ["أولبرايت", "جلوك", "علم الآثار", "مصداقية الكتاب", "شبهات تاريخية"]
    },

    # --- 2. شهادات المؤرخين غير المسيحيين (الرومان واليهود) ---
    {
        "category": "المؤرخون غير المسيحيين",
        "title": "شهادة المؤرخ الروماني كورنيليوس تاسيتوس (Tacitus)",
        "source": "كتاب الحوليات (Annals 15:44) - كُتب حوالي 115م",
        "field": "التاريخ الروماني الإمبراطوري",
        "neutral_proof": "يوثق أعظم مؤرخي روما الوثنية أن المسيحيين اشتقوا اسمهم من 'كريستوس' (المسيح) الذي أُعدم في عهد الإمبراطور طيباريوس على يد الوالي بيلاطس البنطي، وأن هذا الإيمان انتشر في كل روما رغم الاضطهاد.",
        "keywords": ["تاسيتوس", "تاريخية المسيح", "صلب المسيح", "بيلاطس", "روما", "شبهات تاريخية"]
    },
    {
        "category": "المؤرخون غير المسيحيين",
        "title": "رسائل بليني الأصغر إلى الإمبراطور تراجان (Pliny the Younger)",
        "source": "الرسائل الرسمية الرومانية (Letters 10:96) - كُتبت 112م",
        "field": "الوثائق السياسية والقضائية الرومانية",
        "neutral_proof": "حاكم مقاطعة بيثينية الروماني يكتب للإمبراطور واصفاً المسيحيين بأنهم يجتمعون فجر يوم محدد ليرنموا معاً للمسيح 'كما لإله' (quasi deo)، ويلتزمون بقسم ألا يسرقوا ولا يزنوا ولا يخونوا الأمانة.",
        "keywords": ["بليني", "لاهوت المسيح", "عبادة المسيح المبكرة", "ألوهية المسيح", "الكنيسة الأولى"]
    },
    {
        "category": "المؤرخون غير المسيحيين",
        "title": "شهادة المؤرخ اليهودي يوسيفوس فلافيوس (Flavius Josephus)",
        "source": "كتاب عاديات اليهود (Antiquities of the Jews 18.3.3 & 20.9.1) - كُتب 93م",
        "field": "التاريخ اليهودي الهيلينستي",
        "neutral_proof": "يوثق مؤرخ اليهود وجود يسوع المعلم صانع العجائب وصلبه بأمر بيلاطس، كما يوثق في موضع آخر محاكمة 'يعقوب أخي يسوع الذي يُدعى المسيح'، بالإضافة إلى توثيق مقتل يوحنا المعمدان على يد هيرودس.",
        "keywords": ["يوسيفوس", "يوحنا المعمدان", "يعقوب", "يسوع", "تاريخية المسيح", "العهد الجديد"]
    },
    {
        "category": "المؤرخون غير المسيحيين",
        "title": "المؤرخ الروماني سويتونيوس (Suetonius)",
        "source": "سيرة القياصرة الاثني عشر (Life of Claudius 25.4) - 120م",
        "field": "تاريخ البلاط الروماني",
        "neutral_proof": "يذكر طرد الإمبراطور كلوديوس لليهود من روما بسبب اضطرابات نشأت حول شخص 'كريستوس' (Chrestus)، وهو ما يتطابق حرفياً مع ما دونه لوقا البشير في سفر أعمال الرسل (18: 2).",
        "keywords": ["سويتونيوس", "كلوديوس", "أعمال الرسل", "روما", "تاريخية العهد الجديد"]
    },
    {
        "category": "المؤرخون غير المسيحيين",
        "title": "المؤرخ الفلكي الوثني تالوس (Thallus)",
        "source": "تاريخ حوض المتوسط (حوالي 52م) كما نقله يوليوس أفريكانوس",
        "field": "التاريخ الفلكي القديم",
        "neutral_proof": "حاول تالوس تفسير الظلمة التي حدثت على الأرض وقت صلب المسيح (متى 27: 45) بزعمه أنها كسوف شمس، لكن أفريكانوس رد عليه علمياً بأنه يستحيل حدوث كسوف شمس وقت الفصح القمري (البدر).",
        "keywords": ["ظلمة الصلب", "تالوس", "صلب المسيح", "الفلك", "معجزات"]
    },

    # --- 3. الفيزياء الفلكية والكونيات (Cosmology & Fine Tuning) ---
    {
        "category": "الفيزياء الفلكية والكونيات",
        "title": "نظرية الانفجار العظيم وبداية الكون من العدم (Big Bang)",
        "source": "أرنو بنزياس وروبرت ويلسون (جائزة نوبل 1978) / إدوين هابل",
        "field": "الفيزياء الكونية المعاصرة",
        "neutral_proof": "أثبتت الملاحظات الفلكية لإشعاع الخلفية الكونية وتمدد المجرات أن الكون ليس أزلياً بل له بداية زمنية مطلقة ونقطة انطلاق من العدم (Singularity)، متطابقاً مع الإعلان الكتابي الأول: 'في البدء خلق الله'.",
        "keywords": ["أصل الكون", "بداية الكون", "العدم", "الانفجار العظيم", "الإلحاد", "أزلية المادة"]
    },
    {
        "category": "الفيزياء الفلكية والكونيات",
        "title": "اعتراف د. روبرت جاسترو (مؤسس معهد جودارد لدراسات الفضاء - ناسا)",
        "source": "كتاب 'God and the Astronomers' (دار نشر نورتون)",
        "field": "علوم الفضاء وناسا",
        "neutral_proof": "كتب جاسترو (وهو عالم لاأدري محايد): 'بالنسبة للعالم الذي عاش بإيمانه بقوة العقل، تنتهي القصة كحلم سيئ. لقد تسلق جبال الجهل وكان على وشك احتلال القمة؛ وعندما سحب نفسه فوق الصخرة الأخيرة، استقبله حشد من اللاهوتيين الذين كانوا جالسين هناك منذ قرون!'",
        "keywords": ["جاسترو", "ناسا", "الخلق", "الفلك", "الإلحاد", "العلم والدين"]
    },
    {
        "category": "الفيزياء الفلكية والكونيات",
        "title": "معادلات الضبط الدقيق لثوابت الكون (Fine-Tuning of the Universe)",
        "source": "د. روجر بنروز (جامعة أكسفورد / نوبل 2020) ود. بول ديفيز",
        "field": "الفيزياء النظرية والرياضيات الكونية",
        "neutral_proof": "أثبتت الحسابات الرياضية أن احتمالية ضبط مستوى إنتروبيا الكون عند نشأته هي 1 مقسوماً على 10 أس 10 أس 123، وهو رقم يفوق عدد ذرات الكون المنظور، مما يجعل فكرة نشأة الكون المنظم بالصدفة العشوائية مستحيلة رياضياً.",
        "keywords": ["الضبط الدقيق", "الصدفة", "قوانين الفيزياء", "روجر بنروز", "الإلحاد", "وجود الله"]
    },

    # --- 4. البيولوجيا وعلم الجينات والشفرة الوراثية ---
    {
        "category": "البيولوجيا وعلم الجينات",
        "title": "حواء الميتوكوندرية وآدم الصبغي (Mitochondrial Eve & Y-Chromosome Adam)",
        "source": "أبحاث ريبيكا كان ومارك ستونكنغ وآلان ويلسون في مجلة Nature (1987) وأبحاث جامعة ستانفورد",
        "field": "علم الوراثة الجزيئية والجينوم البشري",
        "neutral_proof": "أثبتت دراسات الحمض النووي للميتوكوندريا (mtDNA) أن جميع البشر الأحياء اليوم على كوكب الأرض ينحدرون وراثياً من أم واحدة مشتركة، مما يطابق الرؤية التوراتية بأن البشرية كلها خرجت من أصل واحد.",
        "keywords": ["حواء", "آدم", "التطور", "الجينات", "أصل البشر", "الخلق"]
    },
    {
        "category": "البيولوجيا وعلم الجينات",
        "title": "الشفرة الرقمية للـ DNA واعتراف فيلسوف الإلحاد أنتوني فلو",
        "source": "كتاب 'There Is a God' للفيلسوف أنتوني فلو بعد 50 عاماً من الدفاع عن الإلحاد",
        "field": "فلسفة العلم ونظرية المعلومات الحيوية",
        "neutral_proof": "أعلن أنتوني فلو تراجعه عن الإلحاد مؤكداً أن التعقيد الهائل لشفرة الـ DNA وملايين الأحرف الكيميائية المشفرة يستلزم وجود 'عقل مصمم وراء الوجود'، لأن المادة الصامتة لا تستطيع توليد معلومات دلالية بمفردها.",
        "keywords": ["أنتوني فلو", "DNA", "الشفرة الوراثية", "التصميم الذكي", "الإلحاد", "وجود الله"]
    },

    # --- 5. النقد النصي وتاريخ المخطوطات القديمة ---
    {
        "category": "النقد النصي وتاريخ المخطوطات",
        "title": "شهادة السير فريدريك كينيون (مدير المتحف البريطاني)",
        "source": "كتاب 'The Bible and Archaeology' & 'Our Bible and the Ancient Manuscripts'",
        "field": "علم البرديات والمخطوطات القديمة",
        "neutral_proof": "أكد كينيون أن الفاصل الزمني بين كتابة أسفار العهد الجديد وأقدم المخطوطات الباقية هو الأقصر على الإطلاق مقارنة بأي كاتب كلاسيكي آخر (مثل هوميروس أو أفلاطون أو يوليوس قيصر)، وأن موثوقية النص الكتابي وسلامته قد حُسمت نهائياً علمياً وتاريخياً.",
        "keywords": ["كينيون", "المتحف البريطاني", "تحريف", "مخطوطات", "نقد نصي", "العهد الجديد"]
    },
    {
        "category": "النقد النصي وتاريخ المخطوطات",
        "title": "مخطوطات البحر الميت (مغائر قمران - Dead Sea Scrolls)",
        "source": "الفحص بالكربون المشع وتحليل الحبر في معامل مستقلة (1947 - 1990)",
        "field": "علم الآثار ومخطوطات الشرق القديم",
        "neutral_proof": "عُثر على مخطوطات سفر إشعياء والعهد القديم تعود لما بين 250 ق.م و 68 م، وعند مقارنتها بنصوص العهد القديم المتداولة اليوم، ثبت تطابقها بنسبة تزيد عن 95%، وكانت الفروق الـ 5% مجرد هجاء لغوي طفيف لم يمس أي عقيدة أو نبوة.",
        "keywords": ["قمران", "البحر الميت", "إشعياء", "تحريف العهد القديم", "أصالة الكتاب"]
    }
]

def search_neutral_evidence(query: str, max_results: int = 3) -> list:
    """
    Searches the neutral scientific and historical evidence catalog
    for items matching the question/keywords.
    """
    query_tokens = [w.strip().lower() for w in re.split(r'[\s\W]+', query) if len(w.strip()) >= 2]
    scored = []

    for item in NEUTRAL_EVIDENCE_CATALOG:
        score = 0
        # Check keywords
        for kw in item.get("keywords", []):
            for token in query_tokens:
                if token in kw.lower() or kw.lower() in token:
                    score += 4
        # Check title and proof
        for token in query_tokens:
            if token in item["title"].lower():
                score += 3
            if token in item["neutral_proof"].lower():
                score += 1
            if token in item["field"].lower() or token in item["source"].lower():
                score += 2

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:max_results]]

def format_neutral_evidence_for_prompt(evidence_list: list) -> str:
    """
    Formats the evidence list into a clean, ready-to-inject text block for the AI prompt.
    """
    if not evidence_list:
        # Return fallback generic guidance if no direct catalog match
        return (
            "🔬 توجيه إلزامي: استشهد بالاكتشافات الأثرية في المتاحف العالمية (المتحف البريطاني، اللوفر، متحف إسرائيل)، "
            "وبشهادات المؤرخين الرومان واليهود غير المسيحيين (مثل تاسيتوس، بليني، يوسيفوس)، "
            "وبأبحاث العلوم الطبيعية (الفلك، الجينات، الفيزياء) لبيان تأييد العلم المحايد للموقف الكتابي."
        )

    blocks = []
    for item in evidence_list:
        block = (
            f"🔹 الدليل: {item['title']}\n"
            f"   المجال / المصدر الأكاديمي: {item['field']} ({item['source']})\n"
            f"   شهادة العلم والآثار: {item['neutral_proof']}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QWidget,
    QApplication
)
from PyQt5.QtCore import Qt

class NeutralScienceViewerDialog(QDialog):
    """
    Interactive Viewer Dialog for Servants and Researchers
    to browse the Neutral Science, Archaeology & Secular Historians catalog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔬 بنك أدلة العلم المحايد والآثار والمؤرخين غير المسيحيين")
        self.resize(880, 640)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #14171F;
                font-family: 'Segoe UI', 'Cairo', Tahoma, sans-serif;
            }
            QWidget {
                background-color: transparent;
                color: #D7DAE0;
            }
            QLabel {
                font-size: 13px;
                color: #E2E8F0;
                font-weight: 500;
            }
            QLineEdit, QComboBox {
                background-color: #1E222A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #10B981;
            }
            QListWidget {
                background-color: #101217;
                border: 1px solid #282C34;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 12px;
                margin: 2px 0;
                border-radius: 4px;
                color: #CBD5E1;
                font-size: 12.5px;
            }
            QListWidget::item:hover {
                background-color: #1E222A;
                color: #34D399;
            }
            QListWidget::item:selected {
                background-color: #065F46;
                color: #FFFFFF;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #0E1015;
                color: #F8FAFC;
                border: 1px solid #252830;
                border-radius: 8px;
                padding: 14px;
                font-size: 13px;
                line-height: 1.8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header description
        lbl_head = QLabel("🏛️ براهين محايدة ومكتشفات أثرية ومخطوطات موثقة بالمتاحف العالمية والأبحاث المحكمة")
        lbl_head.setStyleSheet("color: #E5C07B; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_head)

        splitter = QSplitter(Qt.Horizontal)

        # Left Panel (List & Filters)
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(8)

        # Category Filter
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("🌐 جميع مجالات العلم والتوثيق", "")
        cats = sorted(list(set(item["category"] for item in NEUTRAL_EVIDENCE_CATALOG)))
        for c in cats:
            self.cat_combo.addItem(c, c)
        self.cat_combo.currentIndexChanged.connect(self.filter_items)
        lp_layout.addWidget(self.cat_combo)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث سريع (اسم عالم، أثر، متحف، مخطوطة)...")
        self.search_input.textChanged.connect(self.filter_items)
        lp_layout.addWidget(self.search_input)

        # List Widget
        self.items_list = QListWidget()
        self.items_list.itemClicked.connect(self.on_item_clicked)
        lp_layout.addWidget(self.items_list, 1)

        splitter.addWidget(left_panel)

        # Right Panel (Detail Display)
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(8)

        self.detail_display = QTextEdit()
        self.detail_display.setReadOnly(True)
        rp_layout.addWidget(self.detail_display, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # Footer Actions
        footer = QHBoxLayout()
        self.btn_copy = QPushButton("📋 نسخ الدليل العلمي")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 7px 18px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_copy.clicked.connect(self.copy_current)
        footer.addWidget(self.btn_copy)

        footer.addStretch(1)

        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #1E222A;
                color: #94A3B8;
                font-size: 13px;
                padding: 7px 18px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            QPushButton:hover { background-color: #2D323B; color: white; }
        """)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        layout.addLayout(footer)

        self.populate_list()

    def populate_list(self):
        self.items_list.clear()
        selected_cat = self.cat_combo.currentData()
        q = self.search_input.text().strip().lower()

        for item in NEUTRAL_EVIDENCE_CATALOG:
            if selected_cat and item["category"] != selected_cat:
                continue
            if q:
                match = (
                    q in item["title"].lower() or
                    q in item["source"].lower() or
                    q in item["neutral_proof"].lower() or
                    any(q in kw.lower() for kw in item.get("keywords", []))
                )
                if not match:
                    continue

            icon = "🏛️" if "الآثار" in item["category"] else "📜" if "المؤرخون" in item["category"] else "🌌" if "الكونيات" in item["category"] else "🧬" if "الجينات" in item["category"] else "🔍"
            list_item = QListWidgetItem(f"{icon} {item['title']}")
            list_item.setData(Qt.UserRole, item)
            self.items_list.addItem(list_item)

        if self.items_list.count() > 0:
            self.items_list.setCurrentRow(0)
            self.on_item_clicked(self.items_list.item(0))

    def filter_items(self):
        self.populate_list()

    def on_item_clicked(self, list_item):
        if not list_item:
            return
        item = list_item.data(Qt.UserRole)
        html = [
            f"<div style='font-family: Segoe UI, Tahoma; color: #E2E8F0; line-height: 1.8;'>",
            f"<h2 style='color: #10B981; border-bottom: 2px solid #059669; padding-bottom: 6px; margin-bottom: 8px;'>{item['title']}</h2>",
            f"<p style='color: #E5C07B; font-weight: bold; margin: 4px 0;'>المجال: {item['field']} | التصنيف: {item['category']}</p>",
            f"<p style='color: #38BDF8; font-size: 12px; margin: 4px 0;'><strong>المصدر والمتحف / التوثيق:</strong> {item['source']}</p>",
            f"<div style='background-color: #101217; border-right: 4px solid #10B981; padding: 14px; margin: 14px 0; border-radius: 4px;'>",
            f"<h4 style='color: #34D399; margin: 0 0 8px 0;'>🔬 شهادة العلم والآثار المحايدة:</h4>",
            f"<p style='font-size: 13.5px; line-height: 1.8; margin: 0;'>{item['neutral_proof']}</p>",
            f"</div>",
            f"<p style='color: #94A3B8; font-size: 11.5px;'>الكلمات المفتاحية: {', '.join(item.get('keywords', []))}</p>",
            f"</div>"
        ]
        self.detail_display.setHtml("".join(html))

    def copy_current(self):
        item = self.items_list.currentItem()
        if not item:
            return
        data = item.data(Qt.UserRole)
        text = f"{data['title']}\nالمصدر: {data['source']}\nشهادة العلم والآثار:\n{data['neutral_proof']}"
        QApplication.clipboard().setText(text)
