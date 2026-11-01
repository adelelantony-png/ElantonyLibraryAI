"""
Cross Coptic Library - Intelligent Local RAG (Retrieval-Augmented Generation)
High-performance semantic and keyword snippet extraction from local Patristic,
Theological, Apologetic, and Church books (.pdf, .docx, .doc, .txt, .html).
"""

import os
import re
import sqlite3
import fitz
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

DB_NAME = "file_archive.db"

# Arabic Stop Words
STOP_WORDS = {
    'ما', 'ماذا', 'كيف', 'متى', 'أين', 'لماذا', 'من', 'عن', 'على', 'في', 'إلى', 'مع', 'هذا', 'هذه',
    'الذي', 'التي', 'اللذين', 'اللتين', 'الذين', 'اللواتي', 'هو', 'هي', 'هم', 'هن', 'أنت', 'أنتم',
    'نحن', 'أنا', 'كان', 'كانت', 'يكون', 'يكونون', 'ذلك', 'تلك', 'هناك', 'هنا', 'كل', 'بعض', 'غير',
    'سواء', 'عند', 'بين', 'حول', 'نحو', 'خلال', 'قد', 'لقد', 'إذا', 'إن', 'لو', 'لولا', 'أما', 'أو',
    'ثم', 'بل', 'لكن', 'حيث', 'بينما', 'حتى', 'فإن', 'وإن', 'ولكن', 'وما', 'وهو', 'وهي'
}

def normalize_arabic(text):
    """Normalizes Arabic text for flexible matching."""
    if not text:
        return ""
    # Strip tashkeel & tatweel
    text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
    # Unify alef forms
    text = re.sub(r'[إأآٱ]', 'ا', text)
    # Unify teh marbuta and heh
    text = re.sub(r'ة', 'ه', text)
    # Unify yaa and alef maqsura
    text = re.sub(r'ى', 'ي', text)
    return text.lower().strip()

def extract_keywords(query):
    """Extracts clean theological and topic keywords from user query."""
    clean = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', query)
    tokens = [w.strip() for w in clean.split() if len(w.strip()) > 2]
    keywords = [w for w in tokens if w not in STOP_WORDS]
    # Keep original order, remove duplicates
    seen = set()
    unique_kw = []
    for k in keywords:
        norm = normalize_arabic(k)
        if norm not in seen and len(norm) > 2:
            seen.add(norm)
            unique_kw.append(k)
    return unique_kw

def extract_from_doc_binary(file_path):
    """
    Extracts text chunks from classic Microsoft Word .doc binary files (OLE CFBF).
    Works without Microsoft Word or COM automation.
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Extract UTF-16LE strings (standard in Word 97-2003)
        u_texts = [s.decode('utf-16le', errors='ignore') for s in re.findall(b'(?:[\x20-\x7e\xa0-\xff][\x00-\x06]){6,}', data)]
        ar_texts = [t.strip() for t in u_texts if any('\u0600' <= c <= '\u06ff' for c in t) and len(t.strip()) > 15]

        # Extract CP1256 strings if any
        cp_texts = []
        for s in re.findall(b'[\xc0-\xff\x20-\x7e]{8,}', data):
            try:
                dec = s.decode('cp1256', errors='ignore').strip()
                if any('\u0600' <= c <= '\u06ff' for c in dec) and len(dec) > 15:
                    cp_texts.append(dec)
            except Exception:
                pass

        return ar_texts + cp_texts
    except Exception as e:
        return []

def extract_from_docx(file_path):
    """Extracts non-empty paragraphs from .docx documents."""
    if not HAS_DOCX:
        return []
    try:
        doc = docx.Document(file_path)
        paragraphs = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if len(txt) > 20:
                paragraphs.append(txt)
        return paragraphs
    except Exception:
        return []

def extract_from_pdf(file_path, max_pages=60):
    """Extracts text pages from PDF documents via PyMuPDF (fitz)."""
    pages_text = []
    try:
        doc = fitz.open(file_path)
        total = min(len(doc), max_pages)
        for pno in range(total):
            txt = doc[pno].get_text()
            if len(txt.strip()) > 30:
                pages_text.append((pno + 1, txt.strip()))
    except Exception:
        pass
    return pages_text

def extract_from_txt(file_path):
    """Extracts lines from text or HTML files with auto-encoding detection."""
    for enc in ['utf-8', 'cp1256', 'windows-1256', 'latin1']:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                content = f.read()
            # If HTML, strip basic tags
            if file_path.endswith(('.html', '.htm')):
                clean = re.sub(r'<[^>]+>', ' ', content)
                lines = [re.sub(r'\s+', ' ', line).strip() for line in clean.split('\n') if len(line.strip()) > 25]
                return lines
            else:
                lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 20]
                return lines
        except Exception:
            continue
    return []

def resolve_file_path(stored_path, active_directory=None):
    """
    Self-healing file path resolver:
    Handles drive letter changes and reorganized subfolders.
    """
    norm = os.path.normpath(stored_path)
    if os.path.exists(norm):
        return norm

    # Try active directory root
    fname = os.path.basename(stored_path)
    if active_directory and os.path.exists(active_directory):
        # Direct inside active directory
        alt1 = os.path.join(active_directory, fname)
        if os.path.exists(alt1):
            return alt1

    # Try mapping drive letter to existing drives
    drive_part, rest = os.path.splitdrive(norm)
    for d in ['I:', 'H:', 'D:', 'E:', 'G:', 'C:']:
        candidate = d + rest
        if os.path.exists(candidate):
            return candidate

    return None

def find_candidate_books(keywords, library_root=None, project_id=None, limit=12):
    """
    Finds top candidate books matching query keywords from database and disk.
    """
    candidates = []
    seen = set()

    # 1. Search SQLite Database
    if os.path.exists(DB_NAME):
        try:
            con = sqlite3.connect(DB_NAME, timeout=5)
            cur = con.cursor()
            for kw in keywords[:5]:
                cur.execute("""
                    SELECT file_path, file_name, category, extension 
                    FROM files 
                    WHERE (file_name LIKE ? OR category LIKE ?)
                      AND extension IN ('.pdf', '.docx', '.doc', '.txt', '.html')
                    LIMIT ?
                """, (f'%{kw}%', f'%{kw}%', limit))
                for row in cur.fetchall():
                    p, name, cat, ext = row
                    if name not in seen:
                        seen.add(name)
                        resolved = resolve_file_path(p, library_root)
                        if resolved:
                            candidates.append({
                                'path': resolved,
                                'name': name,
                                'category': cat,
                                'ext': ext
                            })
            con.close()
        except Exception as e:
            print(f"RAG DB Search error: {e}")

    # 2. Filesystem search fallback in key theological directories if DB has few results
    if len(candidates) < 4 and library_root and os.path.exists(library_root):
        key_folders = [
            'أبائيات', 'النقد الكتابي-حلمي القمص', 'البابا شنودة الثالث',
            'الانبا بيشوي', 'ابونا متي المسكين', 'تفسير الكتاب المقدس',
            'تعاليم الكنائس الغير ارثوذكسية', 'المادة العلمية -كورس العقيدة 2024'
        ]
        for kf in key_folders:
            folder_path = os.path.join(library_root, kf)
            if os.path.exists(folder_path):
                try:
                    for entry in os.scandir(folder_path):
                        if entry.is_file():
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in ['.pdf', '.docx', '.doc', '.txt', '.html']:
                                norm_name = normalize_arabic(entry.name)
                                if any(normalize_arabic(kw) in norm_name for kw in keywords):
                                    if entry.name not in seen:
                                        seen.add(entry.name)
                                        candidates.append({
                                            'path': entry.path,
                                            'name': entry.name,
                                            'category': kf,
                                            'ext': ext
                                        })
                except Exception:
                    pass

    return candidates

def extract_relevant_snippets(query, library_root=None, project_id=None, max_total_chars=7500):
    """
    Main RAG pipeline:
    Extracts live patristic & theological paragraphs from matching books with exact page numbers.
    Returns:
        (has_sources: bool, context_text: str, source_books: list)
    """
    keywords = extract_keywords(query)
    if not keywords:
        return False, "", []

    candidates = find_candidate_books(keywords, library_root, project_id, limit=12)
    if not candidates:
        return False, "", []

    extracted_snippets = []
    source_books_mentioned = []
    total_chars = 0

    norm_keywords = [normalize_arabic(k) for k in keywords]

    for item in candidates:
        if total_chars >= max_total_chars:
            break

        path = item['path']
        name = item['name']
        ext = item['ext']
        cat = item['category'] or "مكتبة الصليب"

        book_snippets = []

        # --- PDF Extraction ---
        if ext == '.pdf':
            pages = extract_from_pdf(path, max_pages=60)
            for page_no, text in pages:
                norm_text = normalize_arabic(text)
                match_count = sum(1 for kw in norm_keywords if kw in norm_text)
                if match_count >= 1:
                    clean = ' '.join(text.split())
                    # Extract around first match
                    snippet = clean[:500]
                    book_snippets.append({
                        'page': page_no,
                        'text': snippet
                    })
                    if len(book_snippets) >= 2:
                        break

        # --- DOCX Extraction ---
        elif ext == '.docx':
            paragraphs = extract_from_docx(path)
            for idx, p_text in enumerate(paragraphs[:100]):
                norm_p = normalize_arabic(p_text)
                if any(kw in norm_p for kw in norm_keywords):
                    clean = ' '.join(p_text.split())
                    book_snippets.append({
                        'page': f"فقرة {idx + 1}",
                        'text': clean[:500]
                    })
                    if len(book_snippets) >= 2:
                        break

        # --- DOC Binary Extraction ---
        elif ext == '.doc':
            chunks = extract_from_doc_binary(path)
            for idx, c_text in enumerate(chunks[:120]):
                norm_c = normalize_arabic(c_text)
                if any(kw in norm_c for kw in norm_keywords):
                    clean = ' '.join(c_text.split())
                    book_snippets.append({
                        'page': f"موضع {idx + 1}",
                        'text': clean[:500]
                    })
                    if len(book_snippets) >= 2:
                        break

        # --- TXT & HTML Extraction ---
        elif ext in ['.txt', '.html', '.htm']:
            lines = extract_from_txt(path)
            for idx, line in enumerate(lines[:100]):
                norm_line = normalize_arabic(line)
                if any(kw in norm_line for kw in norm_keywords):
                    clean = ' '.join(line.split())
                    book_snippets.append({
                        'page': f"سطر {idx + 1}",
                        'text': clean[:500]
                    })
                    if len(book_snippets) >= 2:
                        break

        if book_snippets:
            source_books_mentioned.append(f"{name} ({cat})")
            for snip in book_snippets:
                entry = f"📖 [كتاب: {name} - تصنيف: {cat} - صفحة/موضع: {snip['page']}]:\n\"{snip['text']}\"\n"
                extracted_snippets.append(entry)
                total_chars += len(entry)
        else:
            # Book matches topic by title, record as owned reference even if text was scanned/image
            source_books_mentioned.append(f"{name} ({cat}) [مرجع متاح بالمكتبة]")

    if extracted_snippets:
        context_str = "=== مقتطفات حية وموثقة من كتب مكتبة الصليب القبطية الأرثوذكسية (استشهد بها وبأرقام صفحاتها بدقة) ===\n\n"
        context_str += "\n".join(extracted_snippets)
        if len(source_books_mentioned) > len(extracted_snippets):
            other_books = [b for b in source_books_mentioned if "[مرجع متاح بالمكتبة]" in b][:5]
            if other_books:
                context_str += "\n\n📚 كتب ومراجع أخرى ذات صلة متوفرة أيضاً في مكتبة المستخدم:\n• " + "\n• ".join(other_books)
        return True, context_str, source_books_mentioned
    elif source_books_mentioned:
        # We found books by title, but could not extract live text (e.g. image scanned)
        context_str = "=== كتب ومراجع ذات صلة متوفرة في مكتبة المستخدم (اذكرها في قسم مراجع مكتبتك) ===\n• "
        context_str += "\n• ".join(source_books_mentioned[:8])
        return True, context_str, source_books_mentioned
    else:
        return False, "", []
