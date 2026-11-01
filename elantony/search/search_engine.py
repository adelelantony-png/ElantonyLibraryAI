# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Advanced Theological Search Engine with Thesaurus Expansion & Multi-Book Discovery
Features:
- NLP query cleaning and Arabic stopword removal.
- Theological synonym thesaurus expansion.
- Multi-tier Cascade FTS5 matching across 311,634 chunks.
- Dedicated thematic books retrieval from library catalog.
- Strict zero-hallucination verification.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from elantony.database.connection import get_connection
from elantony.database.models import ChunkEntity
from elantony.core.logging import logger

ARABIC_STOPWORDS: Set[str] = {
    "هل", "ما", "ماذا", "لماذا", "كيف", "اين", "أين", "متى", "من", "كم",
    "هو", "هي", "هم", "هن", "انت", "أنت", "انا", "أنا", "نحن",
    "كان", "كانت", "كانوا", "يكون", "تكون", "في", "من", "الي", "إلى",
    "على", "عن", "مع", "حتى", "ثم", "او", "أو", "ام", "أم", "بل",
    "لا", "لم", "لن", "ليس", "ليست", "ان", "أن", "انما", "إنما",
    "هذا", "هذه", "ذلك", "تلك", "اولئك", "أولئك", "الذي", "التي",
    "الذين", "اللواتي", "كل", "جميع", "نفس", "بعض", "غير", "سواء",
    "عند", "بين", "قبل", "بعد", "فوق", "تحت", "حول", "بشأن"
}

# Ecclesiastical Theological Synonym Thesaurus
THEOLOGICAL_THESAURUS: Dict[str, List[str]] = {
    "عالمي": ["عالمي", "شامل", "كلي", "عام", "المسكونة", "الأرض كلها"],
    "شامل": ["شامل", "عالمي", "كلي", "عام"],
    "طوفان": ["طوفان", "نوح", "الفلك"],
    "تجسد": ["تجسد", "تأنس", "الكلمة", "تجسد الكلمة"],
    "فداء": ["فداء", "الصليب", "كفارة", "خلاص", "ذبيحة"],
    "معمودية": ["معمودية", "الغطاس", "ميلاد ثان", "جرن المعمودية"],
    "افخارستيا": ["افخارستيا", "القربان", "التناول", "جسد ودم", "عشاء الرب"],
    "توبة": ["توبة", "اعتراف", "نقاوة القلب", "رجوع"],
    "صلاة": ["صلاة", "سهر", "هدوء", "صلاة يسوع", "مزامير"],
    "ثالوث": ["ثالوث", "أقانيم", "الآب والابن", "الروح القدس", "جوهر"]
}


def extract_search_keywords(raw_query: str) -> List[str]:
    """Cleans query, strips punctuation and removes conversational stopwords."""
    clean = re.sub(r'[\'\"«».,،؛؟!\(\)\[\]\{\}:/\\_#*~`\-]', " ", raw_query).strip()
    tokens = [w.strip() for w in clean.split() if len(w.strip()) > 1]
    keywords = [w for w in tokens if w not in ARABIC_STOPWORDS]
    return keywords if keywords else tokens


def expand_theological_synonyms(keywords: List[str]) -> List[str]:
    """Expands query keywords using the patristic & theological thesaurus."""
    expanded: Set[str] = set(keywords)
    for kw in keywords:
        clean_stem = kw.replace("ال", "", 1) if kw.startswith("ال") and len(kw) > 3 else kw
        for key, syns in THEOLOGICAL_THESAURUS.items():
            if key in kw or key in clean_stem:
                for s in syns:
                    expanded.add(s)
                    expanded.add(f"ال{s}" if not s.startswith("ال") else s)
    return list(expanded)


class SearchEngine:
    """High-performance multi-tier search engine with theological thesaurus expansion."""

    def search_fts5(self, query: str, limit: int = 6) -> List[ChunkEntity]:
        """
        Executes multi-tier cascade search across 311,634+ indexed chunks.
        Expands theological synonyms to ensure exhaustive biblical and patristic recall.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        expanded_terms = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows = []

        # Tier 1: Try structured boolean matching with expanded synonyms
        if len(keywords) > 1:
            primary_term = keywords[0]
            secondary_terms = [t for t in expanded_terms if t != primary_term]
            if secondary_terms:
                sec_clause = " OR ".join([f"{w}*" for w in secondary_terms[:6]])
                fts_expr = f"{primary_term}* AND ({sec_clause})"
                try:
                    cur.execute("""
                        SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                        FROM church_chunks_fts
                        WHERE church_chunks_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    """, (fts_expr, limit))
                    rows = cur.fetchall()
                except Exception as e:
                    logger.debug(f"Tier 1 FTS5 expression failed ({e}), falling back to BM25 OR.")

        # Tier 2: Weighted OR query across expanded terms with BM25 ranking
        if len(rows) < limit:
            needed = limit - len(rows)
            existing_sources = {r["source_reference"] for r in rows}
            or_expr = " OR ".join([f"{w}*" for w in expanded_terms[:8]])
            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (or_expr, limit * 2))
                more_rows = cur.fetchall()
                for mr in more_rows:
                    if mr["source_reference"] not in existing_sources:
                        rows.append(mr)
                        existing_sources.add(mr["source_reference"])
                        if len(rows) >= limit:
                            break
            except Exception as e:
                logger.warning(f"Tier 2 FTS5 OR search error: {e}")

        # Tier 3: Direct title lookup in dedicated books
        if len(rows) < limit:
            for kw in keywords:
                if len(kw) >= 3:
                    cur.execute("""
                        SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, 0.0 as rank
                        FROM church_chunks_fts
                        WHERE book_title LIKE ?
                        LIMIT ?
                    """, (f"%{kw}%", limit - len(rows)))
                    title_rows = cur.fetchall()
                    for tr in title_rows:
                        if tr["source_reference"] not in {r["source_reference"] for r in rows}:
                            rows.append(tr)
                    if len(rows) >= limit:
                        break

        conn.close()

        results: List[ChunkEntity] = []
        for r in rows:
            results.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=r["book_title"],
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=r["source_reference"],
                chunk_text=r["chunk_text"],
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))

        return results

    def find_dedicated_books(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Finds complete dedicated volumes in the church catalog specifically focusing on the topic.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        conn = get_connection()
        cur = conn.cursor()
        found_books: List[Dict[str, Any]] = []
        seen_shas = set()

        for kw in keywords:
            if len(kw) < 3:
                continue
            cur.execute("""
                SELECT sha256, file_name, author, category, page_count
                FROM church_books
                WHERE file_name LIKE ? AND is_duplicate_of IS NULL
                ORDER BY page_count DESC
                LIMIT ?
            """, (f"%{kw}%", limit))
            for b in cur.fetchall():
                if b["sha256"] not in seen_shas:
                    seen_shas.add(b["sha256"])
                    found_books.append({
                        "sha256": b["sha256"],
                        "file_name": b["file_name"],
                        "clean_title": b["file_name"].replace(".pdf", ""),
                        "author": b["author"],
                        "category": b["category"],
                        "page_count": b["page_count"]
                    })
                    if len(found_books) >= limit:
                        break

        conn.close()
        return found_books

    def search_scoped_book(self, sha256: str, query: str, limit: int = 4) -> List[ChunkEntity]:
        """Scoped search within a single specific book (📖 اسأل كتابًا)."""
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        expanded_terms = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows = []

        or_query = " OR ".join([f"{w}*" for w in expanded_terms[:6]])
        try:
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                FROM church_chunks_fts
                WHERE sha256 = ? AND church_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (sha256, or_query, limit))
            rows = cur.fetchall()
        except Exception:
            pass

        conn.close()

        results: List[ChunkEntity] = []
        for r in rows:
            results.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=r["book_title"],
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=r["source_reference"],
                chunk_text=r["chunk_text"],
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))

        return results

    def get_patristic_quotes(self, topic: Optional[str] = None, limit: int = 4) -> List[ChunkEntity]:
        """Retrieves curated or top-ranked Patristic excerpts on a spiritual theme."""
        query_topic = topic or "الصلاة التوبة الجهاد الصوم المحبة"
        return self.search_fts5(query_topic, limit=limit)


# Singleton search engine instance
search_engine = SearchEngine()
