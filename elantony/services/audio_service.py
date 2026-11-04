# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Audio & Patristic Recitation Service (Phase 7 Integration)
Extracted and synthesized from local reference projects:
- D:\\Prog\\tts (gTTS Arabic voice generation)
- D:\\Prog\\Transcriber_Project (Whisper & FFmpeg sermon audio extraction)

Features:
- High-quality Arabic speech synthesis for patristic quotes and liturgical texts.
- Memory-buffered audio generation (zero temporary disk pollution).
- Safe fallback if audio hardware or network is unreachable.
"""

import io
import os
import re
from typing import Optional
from elantony.core.logging import logger

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class ChurchAudioService:
    """Service for liturgical text-to-speech recitation and audio processing."""

    def __init__(self):
        self.enabled = GTTS_AVAILABLE

    def is_available(self) -> bool:
        return self.enabled

    def clean_text_for_speech(self, text: str) -> str:
        """Strips markdown markers, emojis, and citation headers for smooth speech flow."""
        # Remove emojis and special formatting
        cleaned = re.sub(r"[#*_~`«»❝❞\[\]\(\)\{\}\<\>]", " ", text)
        cleaned = re.sub(r"[^\w\s\.\,\;\:\?\!ء-ي]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def synthesize_speech(self, text: str, lang: str = "ar", max_chars: int = 1200) -> Optional[bytes]:
        """
        Synthesizes spoken Arabic audio for a theological text or patristic quote.
        Returns MP3 audio bytes, or None if service is unavailable.
        """
        if not self.enabled:
            logger.warning("[AudioService] gTTS is not installed. Audio synthesis skipped.")
            return None

        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return None

        # Truncate to avoid excessive generation time
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars].rsplit(".", 1)[0] + "."

        try:
            tts = gTTS(text=clean_text, lang=lang, slow=False)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            audio_bytes = buffer.read()
            logger.info(f"[AudioService] Synthesized {len(audio_bytes)} bytes of audio for text ({len(clean_text)} chars)")
            return audio_bytes
        except Exception as e:
            logger.error(f"[AudioService] Error generating speech: {e}")
            return None


# Global service instance
audio_service = ChurchAudioService()
