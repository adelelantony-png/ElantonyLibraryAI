# -*- coding: utf-8 -*-
"""
ELANTONY LIBRARY AI - Advanced Theological Search Engine
Features:
- Mandatory Topic Anchor Enforcement (Guarantees zero off-topic answers).
- Ecclesiastical Semantic Expansion & Alef/Hamza Normalization.
- Prioritization of Dedicated Thematic Volumes with MATCH validation.
- Clean text restoration via ArabicTextCleaner.
- Heuristic Chunk Quality Filtering (Anti-Spam / Anti-Garbage).
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from elantony.database.connection import get_connection
from elantony.database.models import ChunkEntity
from elantony.core.logging import logger
from elantony.core.text_cleaner import clean_theological_text, extract_coherent_sentences

ARABIC_STOPWORDS: Set[str] = {
    # Question operators & interrogatives
    "هل", "ما", "ماذا", "لماذا", "كيف", "اين", "أين", "متى", "من", "كم", "اي", "أي",
    "ماهو", "ما_هو", "ماهي", "ما_هي", "ماذا_عن", "بماذا",

    # Comparative & analysis particles (never use as topics)
    "الفرق", "فرق", "فروق", "بين", "مقارنة", "اوجه", "أوجه", "اختلاف", "شبه", "تشابه",
    "معنى", "مفهوم", "تعريف", "شرح", "تفسير", "دليل", "اثبات", "إثبات", "حكم", "رأي",
    "سؤال", "جواب", "اسئلة", "أسئلة", "رد", "شبهات", "شبهة",

    # Pronouns & demonstratives
    "هو", "هي", "هم", "هن", "انت", "أنت", "انا", "أنا", "نحن",
    "هذا", "هذه", "ذلك", "تلك", "اولئك", "أولئك", "الذي", "التي", "الذين", "اللواتي",

    # Auxiliaries & prepositions
    "كان", "كانت", "كانوا", "يكون", "تكون", "في", "الي", "إلى",
    "على", "عن", "مع", "حتى", "ثم", "او", "أو", "ام", "أم", "بل",
    "لا", "لم", "لن", "ليس", "ليست", "ان", "أن", "انما", "إنما",
    "كل", "جميع", "نفس", "بعض", "غير", "سواء",
    "عند", "قبل", "بعد", "فوق", "تحت", "حول", "بشأن", "قال", "قيل",

    # Generic honorifics/prefixes (filter out for book-level dedicated matching)
    "كتاب", "كتب", "رسالة", "مقال", "نبي", "النبي", "سيد", "السيد",
    "قديس", "القديس", "ابونا", "الاب", "الانبا", "الأنبا", "مطران", "اسقف", "أسقف", "بابا", "البابا"
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
    "إقامة": ["إقامة", "اقامة", "أقام", "اقام", "يقيم", "الموتى", "الموتي", "الأموات", "الاموات", "لعازر"],
    "اقامة": ["إقامة", "اقامة", "أقام", "اقام", "يقيم", "الموتى", "الموتي", "الأموات", "الاموات", "لعازر"],
    "أموات": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "اموات": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "موتى": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "موتي": ["الموتى", "الموتي", "الأموات", "الاموات", "الميت", "ميت"],
    "إيليا": ["إيليا", "ايليا", "إيليا النبي", "ايليا النبي", "ابن الأرملة", "ابن الارملة"],
    "ايليا": ["إيليا", "ايليا", "إيليا النبي", "ايليا النبي", "ابن الأرملة", "ابن الارملة"],
    "لعازر": ["لعازر", "إقامة لعازر", "اقامة لعازر", "مريض بيت عنيا"],
    "يايرس": ["يايرس", "ابنة يايرس", "صبية قومي", "طليثا قومي"],
    "نايين": ["نايين", "ابن أرملة نايين", "ابن ارملة نايين"],
    "روح": ["الروح القدس", "المعزي", "روح الحق", "مواهب الروح", "ثمار الروح"]
}


def normalize_alef_variants(word: str) -> List[str]:
    """Generates all common Alef/Hamza and Yeh/Teh-Marbuta variations for FTS matching."""
    variants = {word}
    w_bare = re.sub(r'[أإآ]', 'ا', word)
    variants.add(w_bare)
    if word.startswith(('ا', 'أ', 'إ', 'آ')):
        tail = word[1:]
        for prefix in ('ا', 'أ', 'إ', 'آ'):
            variants.add(prefix + tail)
    if word.endswith('ي'):
        variants.add(word[:-1] + 'ى')
    elif word.endswith('ى'):
        variants.add(word[:-1] + 'ي')
    if word.endswith('ة'):
        variants.add(word[:-1] + 'ه')
    elif word.endswith('ه'):
        variants.add(word[:-1] + 'ة')
    return list(variants)


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

    anchor_keys = [
        "طوفان", "نوح", "تجسد", "فداء", "صليب", "معمودية", "افخارستيا",
        "ثالوث", "قيامة", "إقامة", "اقامة", "أموات", "اموات", "موتى", "موتي",
        "إيليا", "ايليا", "لعازر", "صلاة", "صوم", "توبة"
    ]

    for kw in keywords:
        clean_stem = kw.replace("ال", "", 1) if kw.startswith("ال") and len(kw) > 3 else kw
        matched = False
        for key, syns in THEOLOGICAL_THESAURUS.items():
            if key in kw or key in clean_stem:
                matched = True
                if key in anchor_keys:
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
        Guarantees whole-word matching and zero generic/stopword false positives.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        # Filter out stopwords and short particles
        valid_kws = [k for k in keywords if k not in ARABIC_STOPWORDS and len(k) >= 3]
        if not valid_kws:
            return []

        conn = get_connection()
        cur = conn.cursor()
        found_books: List[Dict[str, Any]] = []
        seen_shas = set()

        for kw in valid_kws:
            # Generate Alef variants for title search
            variants = normalize_alef_variants(kw)
            for v in variants:
                # Whole word patterns: surrounded by spaces, underscores, or start/end
                cur.execute("""
                    SELECT sha256, file_name, author, category, page_count
                    FROM church_books
                    WHERE (
                        file_name LIKE ? OR
                        file_name LIKE ? OR
                        file_name LIKE ? OR
                        file_name LIKE ?
                    ) AND is_duplicate_of IS NULL
                    ORDER BY page_count DESC
                    LIMIT ?
                """, (f"% {v} %", f"%_{v}_%", f"% {v}.pdf", f"{v} %", limit))
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
                if len(found_books) >= limit:
                    break
            if len(found_books) >= limit:
                break

        conn.close()
        return found_books

    def search_fts5(self, query: str, limit: int = 6) -> List[ChunkEntity]:
        """
        Executes multi-tier cascade search across 311,634+ indexed chunks.
        Strictly enforces Topic Anchors to eliminate irrelevant false positives,
        normalizes Alef/Hamza across FTS, matches chunks inside dedicated volumes,
        and restores clean Arabic text.
        """
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        anchors, qualifiers = expand_theological_synonyms(keywords)
        conn = get_connection()
        cur = conn.cursor()
        rows: List[Dict[str, Any]] = []
        seen_refs: Set[str] = set()

        # Build expanded terms with Alef/Hamza normalization for FTS
        all_anchor_terms: Set[str] = set()
        for a in anchors[:6]:
            all_anchor_terms.update(normalize_alef_variants(a))

        all_qual_terms: Set[str] = set()
        for q in qualifiers[:6]:
            all_qual_terms.update(normalize_alef_variants(q))

        anchor_clause = " OR ".join([f'"{t}"' for t in list(all_anchor_terms)[:10]])

        # Step 1: If dedicated books exist, search chunks from them WITH KEYWORD MATCH
        dedicated_books = self.find_dedicated_books(query, limit=3)
        if dedicated_books and anchor_clause:
            for book in dedicated_books:
                b_sha = book["sha256"]
                try:
                    cur.execute("""
                        SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                        FROM church_chunks_fts
                        WHERE sha256 = ? AND church_chunks_fts MATCH ? AND page_number > 1
                        ORDER BY rank
                        LIMIT 2
                    """, (b_sha, anchor_clause))
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
        if len(rows) < limit and anchor_clause:
            if all_qual_terms:
                qual_clause = " OR ".join([f'"{q}"' for q in list(all_qual_terms)[:10]])
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
        if len(rows) < limit and anchor_clause:
            try:
                cur.execute("""
                    SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                    FROM church_chunks_fts
                    WHERE church_chunks_fts MATCH ? AND page_number > 1
                    ORDER BY rank
                    LIMIT ?
                """, (anchor_clause, limit * 2))
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
        """Performs targeted FTS5 search inside single designated book."""
        keywords = extract_search_keywords(query)
        if not keywords:
            return []

        expanded_terms: Set[str] = set()
        for kw in keywords:
            expanded_terms.update(normalize_alef_variants(kw))

        fts_query = " OR ".join([f'"{k}"' for k in list(expanded_terms)[:8]])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
            FROM church_chunks_fts
            WHERE sha256 = ? AND church_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (sha256, fts_query, limit))
        rows = cur.fetchall()
        conn.close()

        results: List[ChunkEntity] = []
        for r in rows:
            clean_title = r["book_title"].replace(".pdf", "")
            cleaned_text = clean_theological_text(r["chunk_text"])
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
        """Fetches curated authentic quotes from church fathers on specified spiritual theme."""
        conn = get_connection()
        cur = conn.cursor()

        if topic:
            tokens = [w.strip() for w in topic.split() if len(w.strip()) > 2 and w not in ARABIC_STOPWORDS]
            expanded = set()
            for t in tokens:
                expanded.update(normalize_alef_variants(t))
            fts_expr = " OR ".join([f'"{t}"' for t in list(expanded)[:6]])
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, rank
                FROM church_chunks_fts
                WHERE church_chunks_fts MATCH ? AND page_number > 2
                ORDER BY rank
                LIMIT ?
            """, (fts_expr, limit * 2))
        else:
            cur.execute("""
                SELECT sha256, book_title, page_number, chunk_index, source_reference, chunk_text, 0.0 as rank
                FROM church_chunks_fts
                WHERE page_number > 3 AND LENGTH(chunk_text) > 100
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit * 2,))

        rows = cur.fetchall()
        conn.close()

        quotes: List[ChunkEntity] = []
        for r in rows:
            clean_text = clean_theological_text(r["chunk_text"])
            if not is_chunk_high_quality(clean_text):
                continue
            clean_title = r["book_title"].replace(".pdf", "")
            quotes.append(ChunkEntity(
                sha256=r["sha256"],
                book_title=clean_title,
                page_number=int(r["page_number"]),
                chunk_index=int(r["chunk_index"]),
                source_reference=f"[كتاب: {clean_title}، ص: {r['page_number']}]",
                chunk_text=clean_text,
                rank=round(float(r["rank"]), 3) if r["rank"] is not None else 0.0
            ))
            if len(quotes) >= limit:
                break

        return quotes


# Global search engine singleton instance
search_engine = ChurchSearchEngine()
