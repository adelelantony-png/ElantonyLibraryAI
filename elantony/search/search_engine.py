# -*- coding: utf-8 -*-
"""
ArchiveMaster - ELANTONY LIBRARY AI
Advanced Theological Search Engine v2.0
Features:
- NLP query cleaning and Arabic stopword removal.
- Rich Ecclesiastical Theological Thesaurus.
- Mandatory Topic Anchor Enforcement (Zero Irrelevant False Positives).
- Dedicated Catalog Thematic Books Prioritization.
- Automatic OCR Glyph Restoration & Text Normalization via ArabicTextCleaner.
- Heuristic Chunk Quality Filtering (Anti-Spam / Anti-Garbage).
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from elantony.database.connection import get_connection
from elantony.database.models import ChunkEntity
from elantony.core.logging import logger
from elantony.core.text_cleaner import clean_theological_text, extract_coherent_sentences

ARABIC_STOPWORDS: Set[str] = {
    "هل", "ما", "ماذا", "لماذا", "كيف", "اين", "أين", "متى", "من", "كم",
    "هو", "هي", "هم", "هن", "انت", "أنت", "انا", "أنا", "نحن",
    "كان", "كانت", "كانوا", "يكون", "تكون", "في", "من", "الي", "إلى",
    "على", "عن", "مع", "حتى", "ثم", "او", "أو", "ام", "أم", "بل",
    "لا", "لم", "لن", "ليس", "ليست", "ان", "أن", "انما", "إنما",
    "هذا", "هذه", "ذلك", "تلك", "اولئك", "أولئك", "الذي", "التي",
    "الذين", "اللواتي", "كل", "جميع", "نفس", "بعض", "غير", "سواء",
    "عند", "بين", "قبل", "بعد", "فوق", "تحت", "حول", "بشأن", "قال", "قيل"
}

# Core Ecclesiastical Theological Thesaurus
THEOLOGICAL_THESAURUS: Dict[str, List[str]] = {
    "طوفان": ["طوفان", "نوح", "الفلك", "فلك نوح", "سفر التكوين", "مياه الطوفان"],
    "نوح": ["طوفان", "نوح", "الفلك", "فلك نوح", "سفر التكوين"],
    "عالمي": ["عالمي", "شامل", "كل الأرض", "المسكونة", "الجبال الشامخة", "عمومية"],
    "شامل": ["شامل", "عالمي", "كل الأرض", "المسكونة", "عمومية الطوفان"],
    "تجسد": ["تجسد", "تأنس", "الكلمة", "تجسد الكلمة", "صار جسدا", "أثناسيوس"],
    "فداء": ["فداء", "الصليب", "كفارة", "خلاص", "ذبيحة", "دم المسيح"],
    "صليب": ["صليب", "الصليب", "فداء", "كفارة", "جلجثة", "ذبيحة"],
    "معمودية": ["معمودية", "الغطاس", "ميلاد ثان", "الجرن", "التغطيس", "جرن المعمودية"],
    "افخارستيا": ["افخارستيا", "القربان", "التناول", "جسد ودم", "عشاء الرب", "الأسرار المقدسة"],
    "تناول": ["تناول", "افخارستيا", "القربان", "جسد ودم المسيح", "سر الشكر"],
    "توبة": ["توبة", "اعتراف", "نقاوة القلب", "رجوع", "دموع التوبة", "أب الاعتراف"],
    "صلاة": ["صلاة", "سهر", "هدوء", "صلاة يسوع", "مزامير", "صلاة باكر", "الأجبية", "صلاة دائمة"],
    "صوم": ["صوم", "نسك", "انقطاع", "إماتة الجسد", "الصوم الكبير", "طهارة"],
    "ثالوث": ["ثالوث", "أقانيم", "الآب والابن", "الروح القدس", "جوهر واحد", "طبيعة واحدة"],
    "قيامة": ["قيامة", "القبر الفارغ", "باكورة الراقدين", "انتصار على الموت", "حياة أبدية"],
    "روح": ["الروح القدس", "المعزي", "روح الحق", "مواهب الروح", "ثمار الروح"]
}


def extract_search_keywords(raw_query: str) -> List[str]:
    """Cleans query, strips punctuation and removes conversational stopwords."""
    clean = re.sub(r'[\'\"«».,،؛؟!\(\)\[\]\{\}:/\\_#*~`\-]', " ", raw_query).strip()
    tokens = [w.strip() for w in clean.split() if len(w.strip()) > 1]
    keywords = [w for w in tokens if w not in ARABIC_STOPWORDS]
    return keywords if keywords else tokens


def expand_theological_synonyms(keywords: List[str]) -> Tuple[List[str], List[str]]:
    """
    Expands query keywords into:
    - Primary Topic Anchors (must match at least one in every chunk).
    - Secondary Qualifiers (refines scope/aspect).
    """
    anchors: Set[str] = set()
    qualifiers: Set[str] = set()

    for kw in keywords:
        clean_stem = kw.replace("ال", "", 1) if kw.startswith("ال") and len(kw) > 3 else kw
        matched = False
        for key, syns in THEOLOGICAL_THESAURUS.items():
            if key in kw or key in clean_stem:
                matched = True
                if key in ["طوفان", "نوح", "تجسد", "فداء", "صليب", "معمودية", "افخارستيا", "ثالوث", "قيامة", "صلاة", "صوم", "توبة"]:
                    anchors.update(syns)
                    anchors.add(kw)
                else:
                    qualifiers.update(syns)
                    qualifiers.add(kw)
        if not matched:
            if len(kw) >= 3:
                qualifiers.add(kw)

    # If no recognized theological anchor, make all non-stopwords potential anchors
    if not anchors:
        anchors = set(keywords)

    return list(anchors), list(qualifiers)


def is_chunk_high_quality(text: str) -> bool:
    """Verifies that a chunk contains meaningful Arabic theological text rather than OCR noise or URLs."""
    if not text or len(text.strip()) < 50:
        return False

    # Filter out Table of Contents / Index pages (checking both raw and normalized)
    normalized_peek = text.replace("امل", "الم")
    if any(toc in normalized_peek for toc in ["فهرس الموضوعات", "فهرس المحتويات", "قائمة المحتويات", "الصفحة رقم الموضوع", "الصفحة رقم"]):
        return False

    # Filter out Table of Contents pages filled with list of page numbers
    if len(re.findall(r'\b\d{2,4}\b', text)) > 6:
        return False

    # Check for excessive URL / watermark spam
    url_matches = len(re.findall(r'www\.|\.com|\.org|http', text, re.IGNORECASE))
    if url_matches > 3:
        return False

    # Check Arabic character ratio
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(text.strip())
    if total_chars > 0 and (arabic_chars / total_chars) < 0.45:
        return False

    return True


class ChurchSearchEngine:
    """High-performance multi-tier search engine with theological thesaurus & dedicated volume priority."""

    def find_dedicated_books(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
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
            clean_kw = kw.replace("ال", "", 1) if kw.startswith("ال") and len(kw) > 3 else kw
            if len(clean_kw) < 3:
                continue

            cur.execute("""
                SELECT sha256, file_name, author, category, page_count
                FROM church_books
                WHERE (file_name LIKE ? OR file_name LIKE ?) AND is_duplicate_of IS NULL
                ORDER BY page_count DESC
                LIMIT ?
            """, (f"%{clean_kw}%", f"%{kw}%", limit))
            for b in cur.fetchall():
                if b["sha256"] not in seen_shas:
                    seen_shas.add(b["sha256"])
                    found_books.append({
                        "sha256": b["sha256"],
                        "file_name": b["file_name"],
                        "clean_title": b["file_name"].replace(".pdf", ""),
                        "author": b["author"] or "آباء ومعلمو الكنيسة",
                        "category": b["category"] or "لاهوت وعقيدة",
                        "page_count": b["page_count"] or 0
                    })
                    if len(found_books) >= limit:
                        break

        conn.close()
        return found_books

    def search_fts5(self, query: str, limit: int = 6) -> List[ChunkEntity]:
        """
        Executes multi-tier cascade search across 311,634+ indexed chunks.
        Strictly enforces Topic Anchors to eliminate irrelevant false positives,
        prioritizes dedicated thematic volumes, and restores clean Arabic text.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        anchors, qualifiers = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows: List[Dict[str, Any]] = []
        seen_refs: Set[str] = set()

        # Step 1: If dedicated books exist in the catalog, search chunks from them FIRST (page > 1)
        dedicated_books = self.find_dedicated_books(query, limit=3)
        if dedicated_books:
            for book in dedicated_books:
                b_sha = book["sha256"]
                try:
                    # Search relevant pages inside dedicated book
                    cur.execute("""
                        SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                        FROM church_chunks_fts
                        WHERE sha256 = ? AND page_number > 1
                        ORDER BY rank
                        LIMIT 2
                    """, (b_sha,))
                    for r in cur.fetchall():
                        ref = r["source_reference"]
                        if ref not in seen_refs and is_chunk_high_quality(r["chunk_text"]):
                            seen_refs.add(ref)
                            rows.append(r)
                            if len(rows) >= limit:
                                break
                except Exception as e:
                    logger.debug(f"Scoped dedicated book chunk query error: {e}")

        # Step 2: Boolean Anchor Intersection Across Entire Library
        if len(rows) < limit and anchors:
            anchor_clause = " OR ".join([f'"{a}"' for a in anchors[:6]])
            if qualifiers:
                qual_clause = " OR ".join([f'"{q}"' for q in qualifiers[:6]])
                fts_expr = f"({anchor_clause}) AND ({qual_clause})"
            else:
                fts_expr = f"({anchor_clause})"

            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ? AND page_number > 1
                    ORDER BY rank
                    LIMIT ?
                """, (fts_expr, limit * 3))
                candidate_rows = cur.fetchall()
                for cr in candidate_rows:
                    ref = cr["source_reference"]
                    if ref not in seen_refs and is_chunk_high_quality(cr["chunk_text"]):
                        seen_refs.add(ref)
                        rows.append(cr)
                        if len(rows) >= limit:
                            break
            except Exception as e:
                logger.warning(f"FTS5 Anchor Boolean Search error: {e}")

        # Step 3: High-Relevance Fallback (Anchor only - Never naked generic words)
        if len(rows) < limit and anchors:
            anchor_expr = " OR ".join([f'"{a}"' for a in anchors[:4]])
            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (anchor_expr, limit * 2))
                candidate_rows = cur.fetchall()
                for cr in candidate_rows:
                    ref = cr["source_reference"]
                    if ref not in seen_refs and is_chunk_high_quality(cr["chunk_text"]):
                        seen_refs.add(ref)
                        rows.append(cr)
                        if len(rows) >= limit:
                            break
            except Exception as e:
                logger.warning(f"FTS5 Anchor Fallback search error: {e}")

        conn.close()

        # Step 4: Clean, Normalize and Format Output Chunks
        results: List[ChunkEntity] = []
        for r in rows:
            cleaned_text = clean_theological_text(r["chunk_text"])
            if len(cleaned_text) < 40:
                continue

            clean_ref = r["source_reference"]
            # Clean book title in source_reference
            clean_title = r["book_title"].replace(".pdf", "")

            results.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=clean_title,
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=f"[كتاب: {clean_title}، ص: {r['page_number']}]",
                chunk_text=cleaned_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))

        return results

    def search_scoped_book(self, sha256: str, query: str, limit: int = 4) -> List[ChunkEntity]:
        """Scoped search within a single specific book (📖 اسأل كتابًا)."""
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        anchors, qualifiers = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows = []

        all_terms = list(set(anchors + qualifiers))
        fts_expr = " OR ".join([f'"{t}"' for t in all_terms[:6]])

        try:
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                FROM church_chunks_fts
                WHERE sha256 = ? AND church_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (sha256, fts_expr, limit))
            rows = cur.fetchall()
        except Exception:
            pass

        conn.close()

        results: List[ChunkEntity] = []
        for r in rows:
            cleaned_text = clean_theological_text(r["chunk_text"])
            clean_title = r["book_title"].replace(".pdf", "")
            results.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=clean_title,
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=f"[كتاب: {clean_title}، ص: {r['page_number']}]",
                chunk_text=cleaned_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))

        return results

    def get_patristic_quotes(self, topic: Optional[str] = None, limit: int = 4) -> List[ChunkEntity]:
        """Retrieves curated or top-ranked Patristic excerpts on a spiritual theme."""
        query_topic = topic or "الصلاة التوبة الجهاد الصوم المحبة"
        return self.search_fts5(query_topic, limit=limit)


# Singleton search engine instance
search_engine = ChurchSearchEngine()
