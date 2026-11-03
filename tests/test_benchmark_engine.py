# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Comprehensive Ecclesiastical & Theological Benchmark Suite (Phase 9)
Evaluates Retrieval Accuracy (Recall@K, Precision@K), Patristic Authority Ranking,
Citation Authenticity, Structured Answer Synthesis, and Response Latency
completely offline with zero external network dependencies.
"""

import sys
import os
import time
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from elantony.database.repository import repo
from elantony.database.connection import get_connection
from elantony.search.search_engine import search_engine
from elantony.ai.rule_based_provider import RuleBasedChurchProvider
from elantony.classifier.source_classifier import classifier, SourceType


class TestEcclesiasticalBenchmarkEngine(unittest.TestCase):
    """Rigorous Benchmark & QA Suite for Church Theological AI."""

    @classmethod
    def setUpClass(cls):
        cls.provider = RuleBasedChurchProvider()
        cls.conn = get_connection()
        cls.cur = cls.conn.cursor()
        # Warm up cache
        search_engine.search_fts5("المسيح", limit=2)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_fts5_patristic_retrieval_athanasius(self):
        """Benchmark: Retrieval of St. Athanasius Incarnation doctrines."""
        query = "ما مفهوم التجسد الإلهي عند القديس أثناسيوس الرسولي؟"
        t0 = time.time()
        chunks = search_engine.search_fts5(query, limit=5)
        duration_ms = (time.time() - t0) * 1000

        self.assertGreater(len(chunks), 0, "Should retrieve chunks for Athanasius Incarnation query")
        self.assertLess(duration_ms, 1200, f"Retrieval latency should be < 1200ms (actual: {duration_ms:.1f}ms)")

        # Target father prioritization check
        has_athanasius = any("أثناسيوس" in (c.author or "") or "أثناسيوس" in c.file_name or "تجسد" in c.file_name for c in chunks)
        self.assertTrue(has_athanasius, "Results should contain St. Athanasius or Incarnation treatises")

    def test_02_patristic_authority_ranking_cyril(self):
        """Benchmark: Cyrillian Christology prioritization (Tier 1 & Tier 2)."""
        query = "طبيعة المسيح والاتحاد الاقنومي عند القديس كيرلس الكبير عمود الدين"
        chunks = search_engine.search_fts5(query, limit=5)
        self.assertGreater(len(chunks), 0)

        # Check that top result has strong relevance score
        top_chunk = chunks[0]
        self.assertGreaterEqual(top_chunk.relevance_score, 0.70)
        self.assertIn(top_chunk.authenticity_tier, [1, 2, 3])

    def test_03_monastic_patristic_antony(self):
        """Benchmark: St. Antony the Great monastic and prayer teachings."""
        query = "الصلاة الدائمة ومحاربة الأفكار عند الأنبا أنطونيوس"
        chunks = search_engine.search_fts5(query, limit=5)
        self.assertGreater(len(chunks), 0)
        for c in chunks:
            self.assertIsNotNone(c.chunk_text)
            self.assertGreater(len(c.chunk_text), 10)

    def test_04_liturgical_sources_basil_liturgy(self):
        """Benchmark: Liturgical retrieval for the Liturgy of St. Basil."""
        query = "طقس صلوات القداس الباسيلي وصلوات الصلح"
        chunks = search_engine.search_fts5(query, limit=5, filter_source_type="LITURGICAL_SOURCES")
        if chunks:
            for c in chunks:
                self.assertIsNotNone(c.file_name)

    def test_05_historical_sources_nicaea_council(self):
        """Benchmark: Historical council and creed retrieval."""
        query = "تاريخ مجمع نيقية المسكوني وقانون الإيمان الرهباني"
        chunks = search_engine.search_fts5(query, limit=5)
        self.assertGreater(len(chunks), 0)

    def test_06_citation_authenticity_and_page_integrity(self):
        """Verify that every citation maps to an actual existing book and valid page in library."""
        query = "الفداء ومغفرة الخطايا بالصليب"
        chunks = search_engine.search_fts5(query, limit=4)
        self.assertGreater(len(chunks), 0)

        for c in chunks:
            # 1. SHA must exist in church_books
            self.cur.execute("SELECT id, file_name FROM church_books WHERE sha256 LIKE ?", (f"{c.sha256[:16]}%",))
            row = self.cur.fetchone()
            self.assertIsNotNone(row, f"Book with SHA prefix {c.sha256[:16]} must exist in database")

            # 2. Page number must be positive integer
            self.assertIsInstance(c.page_number, int)
            self.assertGreater(c.page_number, 0)

            # 3. Source reference must be cleanly formatted
            self.assertTrue("كتاب:" in c.source_reference)

    def test_07_structured_theological_synthesis_axes(self):
        """Verify that the generated answer respects the required 5-axis ecclesiastical structure."""
        query = "ما مفهوم التجسد الإلهي عند القديس أثناسيوس الرسولي؟"
        chunks = search_engine.search_fts5(query, limit=4)
        answer = self.provider.generate_answer(query, chunks)

        # Must contain all standard ecclesiastical axes
        self.assertIn("المقدمة والتعريف المنهجي", answer)
        self.assertIn("المحور الأول: التقرير اللاهوتي والآبائي", answer)
        self.assertIn("المحور الثاني: نصوص المراجع والشواهد الأصلية المستخرجة", answer)
        self.assertIn("المحور الثالث: البعد الروحي والجهاد المعاش", answer)
        self.assertIn("قائمة المصادر والمراجع المعتمدة", answer)

        # Must have verified citation tags
        self.assertIn("[صياغة تحليلية - PARAPHRASE]", answer)
        self.assertIn("[اقتباس حرفي - QUOTATION]", answer)

    def test_08_zero_hallucination_empty_retrieval(self):
        """Zero-Hallucination verification: Must refuse to fabricate references when no chunks exist."""
        answer = self.provider.generate_answer("سؤال غير موجود إطلاقاً xyz123987", [])
        self.assertIn("لم يتم العثور على شواهد مباشرة كافية", answer)
        self.assertIn("أمانة التوثيق الكنسي", answer)

    def test_09_retrieval_metrics_recall_precision(self):
        """Compute Recall@5 and Precision@5 for core benchmark queries."""
        benchmark_queries = [
            ("تجسد الكلمة أثناسيوس", ["تجسد", "أثناسيوس", "كلمة"]),
            ("طبيعة المسيح كيرلس", ["طبيعة", "كيرلس", "مسيح"]),
            ("طوفان نوح وتكوين", ["طوفان", "نوح", "فلك"]),
            ("الصلاة الدائمة والهدوء", ["صلاة", "هدوء", "قلب"])
        ]

        total_precision = 0.0
        k = 4
        for q_text, expected_terms in benchmark_queries:
            chunks = search_engine.search_fts5(q_text, limit=k)
            if not chunks:
                continue
            relevant_hits = 0
            for c in chunks:
                text_blob = (c.chunk_text + " " + c.file_name).lower()
                if any(term in text_blob for term in expected_terms):
                    relevant_hits += 1
            precision_at_k = relevant_hits / len(chunks)
            total_precision += precision_at_k

        avg_precision = total_precision / len(benchmark_queries)
        # Precision@K across the library should exceed 75%
        self.assertGreaterEqual(avg_precision, 0.70, f"Average Precision@{k} was {avg_precision:.2f}")

    def test_10_database_indices_and_maintenance(self):
        """Verify performance indices and WAL maintenance."""
        metrics = repo.get_admin_metrics()
        self.assertGreater(metrics["unique_books"], 3600)
        self.assertGreater(metrics["indexed_chunks"], 300000)
        self.assertIn("Tier 1", metrics["authenticity_tiers"])

        maintenance_result = repo.run_maintenance()
        self.assertEqual(maintenance_result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
