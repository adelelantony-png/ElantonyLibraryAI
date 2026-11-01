from PyQt5.QtCore import QObject, pyqtSignal
from deep_translator import GoogleTranslator


class TranslationWorker(QObject):
    """
    عامل يقوم بعملية الترجمة في خيط منفصل لتجنب تجميد الواجهة.
    """

    finished = pyqtSignal(str)

    def __init__(self, text, target_lang):
        super().__init__()
        self.text = text
        self.target_lang = target_lang

    def run(self):
        """
        ينفذ عملية الترجمة ويرسل النتيجة عند الانتهاء.
        """
        if not self.text:
            self.finished.emit("")
            return

        try:
            # الترجمة من اللغة المكتشفة تلقائياً إلى اللغة الهدف
            translated_text = GoogleTranslator(
                source="auto", target=self.target_lang
            ).translate(self.text)
            self.finished.emit(translated_text)
        except Exception as e:
            self.finished.emit(f"فشلت عملية الترجمة: \n{e}")
