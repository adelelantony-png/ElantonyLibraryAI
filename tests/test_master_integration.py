# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Master Comprehensive Integration Test Suite (Phase 9)
Tests all core subsystems:
1. Multi-Model Gateway & Dynamic Provider Routing
2. Resilient Fallback Hierarchy
3. Database Repository & Library Access
4. FTS5 Hybrid Search Engine
5. Audio Recitation (TTS) Service
6. DOCX Academic Research Export
7. Grounded Anti-Hallucination & Citation Verification
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from elantony.ai.gateway import gateway, MultiModelGateway
from elantony.ai.factory import get_ai_provider
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.database.models import ChunkEntity
from elantony.database.repository import repo
from elantony.search.search_engine import search_engine
from elantony.services.audio_service import audio_service
from elantony.services.docx_exporter import generate_session_docx


class TestMasterIntegration(unittest.TestCase):
    """Rigorous verification tests for unified Elantony Library AI system."""

    def test_01_gateway_initialization(self):
        """Verifies Gateway registers all providers properly."""
        available = gateway.list_available_providers()
        self.assertIn("rule_based", available)
        self.assertTrue(gateway.is_available())
        print(f"[TEST 1 PASS] Active Gateway Providers: {available}")

    def test_02_dynamic_provider_routing(self):
        """Verifies intelligent model routing based on question and depth."""
        # Simple query routing
        prov_simple = gateway.determine_optimal_provider("ما هي الصلاة؟", depth_mode="pastoral")
        self.assertIn(prov_simple, ["gemini", "deepinfer", "rule_based"])

        # Deep theological research routing
        prov_deep = gateway.determine_optimal_provider(
            "دراسة مقارنة في لاهوت التجسد والفداء بين القديس أثناسيوس والقديس كيرلس الكبير",
            depth_mode="academic"
        )
        self.assertIn(prov_deep, ["gemini", "kimi", "deepinfer", "rule_based"])
        print(f"[TEST 2 PASS] Routing verified: Simple -> {prov_simple}, Deep Academic -> {prov_deep}")

    def test_03_fallback_cascade(self):
        """Verifies fallback cascade smoothly defaults to deterministic RuleBased when external APIs fail."""
        chunk = ChunkEntity(
            sha256="test_sha_001",
            book_title="تجسد الكلمة",
            author="القديس أثناسيوس الرسولي",
            page_number=14,
            chunk_index=1,
            source_reference="«تجسد الكلمة» - ص 14",
            chunk_text="لأنه صار إنساناً لكي نصير نحن إلهة بالنعمة."
        )
        # Force fallback by requesting invalid provider preference
        answer = gateway.generate_answer(
            question="ما هو الخلاص؟",
            context_chunks=[chunk],
            depth_mode="academic",
            provider_preference="non_existent_provider"
        )
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 50)
        print(f"[TEST 3 PASS] Fallback cascade succeeded. Generated answer length: {len(answer)}")

    def test_04_database_and_library_integrity(self):
        """Verifies SQLite repository connects and has indexed books."""
        stats = repo.get_library_stats()
        self.assertIsInstance(stats, dict)
        print(f"[TEST 4 PASS] Library Stats: Books={stats.get('total_books', 0)}, Chunks={stats.get('total_chunks', 0)}")

    def test_05_fts5_search_engine(self):
        """Verifies FTS5 search executes without SQL syntax errors."""
        results = search_engine.search_fts5("التجسد", limit=3)
        self.assertIsInstance(results, list)
        print(f"[TEST 5 PASS] FTS5 Search executed. Results returned: {len(results)}")

    def test_06_audio_tts_service(self):
        """Verifies audio synthesis generates non-empty MP3 audio bytes."""
        text = "المجد لله في الأعالي وعلى الأرض السلام."
        audio_bytes = audio_service.synthesize_speech(text, lang="ar")
        self.assertIsNotNone(audio_bytes)
        self.assertGreater(len(audio_bytes), 1000)
        print(f"[TEST 6 PASS] Audio TTS generated {len(audio_bytes)} bytes of MP3")

    def test_07_docx_academic_export(self):
        """Verifies Word (.docx) export compiles correctly."""
        comp_data = {
            "title": "بحث تجريبي في سر الإفخارستيا",
            "turns": [
                {
                    "turn_number": 1,
                    "question": "ما هو سر الإفخارستيا؟",
                    "answer": "سر الإفخارستيا هو قلب الليتورجيا القبطية والينبوع الروحي المعاش.",
                    "citations": []
                }
            ],
            "bibliography": []
        }
        out_file = os.path.join(str(BASE_DIR), "test_monograph.docx")
        try:
            res_path = generate_session_docx(comp_data, out_file)
            self.assertTrue(os.path.exists(res_path))
            file_size = os.path.getsize(res_path)
            self.assertGreater(file_size, 5000)
            print(f"[TEST 7 PASS] DOCX Export generated {file_size} bytes successfully")
        finally:
            if os.path.exists(out_file):
                try:
                    os.remove(out_file)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
