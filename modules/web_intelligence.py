"""
Cross Coptic Library - Web Intelligence & Online Patristic/Apologetic Reader
Integrates Jina Reader, Dr. Ghaly's Encyclopedia (Holy_Bible_1), and local crawling.
Converts web articles and Christian apologetics into clean Markdown for LLMs and Word (.docx) books.
"""

import re
import os
import datetime
import httpx
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

STOPWORDS = {
    'هل', 'ما', 'هو', 'هي', 'من', 'عن', 'في', 'على', 'إلى', 'الي', 'مع', 'هذا', 
    'هذه', 'كيف', 'لماذا', 'اين', 'أين', 'تم', 'كان', 'تكون', 'ان', 'أن', 'قد',
    'التي', 'الذي', 'الذين', 'ذلك', 'تلك', 'شبهة', 'حول', 'بين'
}

def clean_search_keywords(query: str, max_words: int = 3) -> str:
    """Extracts top significant search keywords from an Arabic question/query."""
    cleaned = re.sub(r'[^\w\s\u0621-\u064A]', ' ', query)
    tokens = [w.strip() for w in cleaned.split() if len(w.strip()) >= 3 and w.strip() not in STOPWORDS]
    if not tokens:
        return query.strip()
    return " ".join(tokens[:max_words])

def read_via_jina(url: str, timeout: float = 12.0) -> str:
    """Fetches clean Markdown of any web page via Jina Reader."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/markdown, text/plain, */*"
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(jina_url, headers=headers)
            if resp.status_code == 200 and len(resp.text.strip()) > 100:
                return resp.text.strip()
    except Exception as e:
        print(f"Jina Reader fetch warning for {url}: {e}")
    return ""

def extract_article_locally(url: str, timeout: float = 10.0) -> str:
    """Fallback: downloads HTML directly and extracts main body text as readable markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove scripts, styles, navigations, headers, footers
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "svg"]):
                tag.decompose()
                
            # Try to find primary container
            target = (
                soup.find("section", id="pdf") or
                soup.find("article") or
                soup.find("main") or
                soup.find("div", class_=re.compile(r"content|article|body", re.I)) or
                soup.find("body")
            )
            if not target:
                return ""
                
            # Extract text preserving linebreaks
            lines = []
            for elem in target.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
                txt = elem.get_text(separator=" ", strip=True)
                if not txt:
                    continue
                if elem.name.startswith("h"):
                    lines.append(f"\n### {txt}\n")
                elif elem.name == "li":
                    lines.append(f"- {txt}")
                else:
                    lines.append(txt)
                    
            return "\n\n".join(lines).strip()
    except Exception as e:
        print(f"Local article extraction warning for {url}: {e}")
        return ""

def read_url_clean(url: str, timeout: float = 12.0) -> str:
    """Unified reader: tries Jina Reader first, then local fallback."""
    text = read_via_jina(url, timeout=timeout)
    if not text or len(text) < 150:
        text = extract_article_locally(url, timeout=timeout)
    return text

class DrGhalyEngine:
    """Client for Dr. Ghaly's Apologetics Encyclopedia (drghaly.com / Holy_Bible_1)."""
    BASE_URL = "https://drghaly.com"

    @classmethod
    def search_articles(cls, query: str, limit: int = 5) -> list:
        """
        Searches drghaly.com for articles matching query.
        Returns list of dicts: {'title': str, 'url': str, 'id': str}
        """
        results = []
        queries_to_try = [query]
        cleaned_kw = clean_search_keywords(query, max_words=2)
        if cleaned_kw and cleaned_kw != query:
            queries_to_try.append(cleaned_kw)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        seen_urls = set()
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            for q_term in queries_to_try:
                try:
                    search_url = f"{cls.BASE_URL}/articles?q={q_term}"
                    resp = client.get(search_url, headers=headers)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/articles/") and href.count("/") == 2:
                            # Extract clean title
                            h_tag = a.find(["h2", "h3", "h4", "span"])
                            title = h_tag.get_text(separator=" ", strip=True) if h_tag else a.get_text(separator=" ", strip=True)
                            
                            if title and title not in ["للطباعة", "PDF", "عرض PDF"] and href not in seen_urls:
                                seen_urls.add(href)
                                full_url = f"{cls.BASE_URL}{href}"
                                art_id = href.split("/")[-1]
                                results.append({
                                    "title": title,
                                    "url": full_url,
                                    "id": art_id
                                })
                                if len(results) >= limit:
                                    return results
                except Exception as ex:
                    print(f"DrGhaly search error for term '{q_term}': {ex}")

                if len(results) >= limit:
                    break

        return results

    @classmethod
    def get_article_content(cls, article_url_or_id: str) -> dict:
        """
        Fetches full article content from drghaly.com.
        """
        if article_url_or_id.isdigit():
            full_url = f"{cls.BASE_URL}/articles/{article_url_or_id}"
        elif article_url_or_id.startswith("http"):
            full_url = article_url_or_id
        else:
            full_url = f"{cls.BASE_URL}/articles/{article_url_or_id.lstrip('/')}"

        content = read_url_clean(full_url)
        return {
            "url": full_url,
            "content": content
        }

    @classmethod
    def search_and_get_top_context(cls, query: str, max_articles: int = 2, max_chars_per_article: int = 2500) -> tuple:
        """
        Performs search and compiles a ready-to-inject RAG context string.
        Returns: (has_context: bool, formatted_context: str, sources_list: list)
        """
        articles = cls.search_articles(query, limit=max_articles)
        if not articles:
            return False, "", []

        sources = []
        context_blocks = []
        for art in articles[:max_articles]:
            art_data = cls.get_article_content(art["url"])
            raw_text = art_data.get("content", "")
            if not raw_text:
                continue
            # Trim header noise if present
            trimmed = raw_text[:max_chars_per_article].strip()
            block = (
                f"📖 [موسوعة د. غالي - Holy_Bible_1]\n"
                f"العنوان: {art['title']}\n"
                f"الرابط المرجعي: {art['url']}\n"
                f"المحتوى المستخلص:\n{trimmed}\n"
            )
            context_blocks.append(block)
            sources.append({
                "title": art["title"],
                "url": art["url"],
                "id": art["id"]
            })

        if not context_blocks:
            return False, "", []

        combined_text = "\n" + "="*50 + "\n" + "\n\n".join(context_blocks) + "\n" + "="*50
        return True, combined_text, sources

def save_article_as_docx(title: str, content: str, source_url: str, output_path: str) -> str:
    """
    Saves a web or Dr. Ghaly article as a formatted Word (.docx) book with Coptic branding.
    """
    doc = Document()
    
    # Page setup (A4, 1 inch margins)
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    def set_rtl(p):
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pPr = p._element.get_or_add_pPr()
        if pPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}bidi') is None:
            pPr.append(OxmlElement('w:bidi'))

    # Header Cross
    p_cross = doc.add_paragraph()
    set_rtl(p_cross)
    p_cross.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cross = p_cross.add_run("✠ مكتبة الصليب القبطية الأرثوذكسية ✠\nموسوعة الدفاعيات والرد على الشبهات (د. غالي - Holy_Bible_1)")
    r_cross.font.size = Pt(13)
    r_cross.font.bold = True
    r_cross.font.color.rgb = RGBColor(197, 160, 89)

    # Document Title
    p_title = doc.add_paragraph()
    set_rtl(p_title)
    r_title = p_title.add_run(f"\n{title}\n")
    r_title.font.size = Pt(18)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(24, 43, 73)

    # Meta Info
    p_meta = doc.add_paragraph()
    set_rtl(p_meta)
    r_meta = p_meta.add_run(
        f"المصدر: {source_url}\n"
        f"تاريخ التوثيق والأرشفة: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"{'─'*50}\n"
    )
    r_meta.font.size = Pt(9.5)
    r_meta.font.italic = True
    r_meta.font.color.rgb = RGBColor(100, 116, 139)

    # Content paragraphs
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        p = doc.add_paragraph()
        set_rtl(p)
        if stripped.startswith('###') or stripped.startswith('##') or stripped.startswith('#'):
            clean_head = re.sub(r'^#+\s*', '', stripped)
            r = p.add_run(clean_head)
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 58, 138)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            clean_bullet = stripped[2:].strip()
            r = p.add_run(f"• {clean_bullet}")
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(30, 41, 59)
        else:
            r = p.add_run(stripped)
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(30, 41, 59)

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    return output_path

def create_coptic_formatted_docx(*args, **kwargs):
    """Flexible wrapper supporting both argument orders for Word docx generation."""
    if len(args) == 4:
        if isinstance(args[0], str) and args[0].lower().endswith(".docx"):
            return save_article_as_docx(title=args[1], content=args[2], source_url=args[3], output_path=args[0])
        else:
            return save_article_as_docx(title=args[0], content=args[1], source_url=args[2], output_path=args[3])
    return save_article_as_docx(*args, **kwargs)

class StTaklaEngine:
    """Client for St-Takla.org - The largest Arabic Coptic Orthodox Theological Encyclopedia."""
    BASE_URL = "https://st-takla.org"

    @classmethod
    def search_articles(cls, query: str, limit: int = 5) -> list:
        """
        Searches st-takla.org for patristic, biblical, or apologetic articles.
        Returns list of dicts: {'title': str, 'url': str, 'id': str, 'snippet': str}
        """
        results = []
        cleaned_kw = clean_search_keywords(query, max_words=3)
        search_term = f"site:st-takla.org {cleaned_kw}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
        }

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.post("https://html.duckduckgo.com/html/", data={"q": search_term}, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    seen_urls = set()
                    import urllib.parse
                    
                    for res in soup.find_all("div", class_="result"):
                        a_title = res.find("a", class_="result__title") or res.find("a", class_="result__snippet")
                        a_url = res.find("a", class_="result__url")
                        snippet_tag = res.find("a", class_="result__snippet")
                        snippet_text = snippet_tag.get_text(strip=True) if snippet_tag else ""
                        
                        if a_url:
                            raw_href = a_url.get("href", "").strip()
                            if "/l/?uddg=" in raw_href:
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                                target_url = parsed.get("uddg", [raw_href])[0]
                            else:
                                target_url = raw_href
                                
                            if "st-takla.org" in target_url and target_url not in seen_urls:
                                seen_urls.add(target_url)
                                title = a_title.get_text(separator=" ", strip=True) if a_title else "مرجع كنسي من موقع الأنبا تكلا"
                                # Clean title noise
                                title = title.replace("- موقع الأنبا تكلا هيمانوت", "").replace("موقع الأنبا تكلا هيمانوت", "").strip()
                                art_id = target_url.split("/")[-1].replace(".html", "").replace(".htm", "")
                                
                                results.append({
                                    "title": title or "دراسة قبطية من موقع تكلا",
                                    "url": target_url,
                                    "id": f"takla_{art_id}",
                                    "snippet": snippet_text
                                })
                                if len(results) >= limit:
                                    break
        except Exception as ex:
            print(f"StTakla search warning: {ex}")

        return results

    @classmethod
    def get_article_content(cls, url: str) -> dict:
        content = read_url_clean(url)
        return {
            "url": url,
            "content": content
        }

    @classmethod
    def search_and_get_top_context(cls, query: str, max_articles: int = 2, max_chars_per_article: int = 2500) -> tuple:
        """
        Performs search on St-Takla and compiles ready RAG context.
        Returns: (has_context: bool, formatted_context: str, sources_list: list)
        """
        articles = cls.search_articles(query, limit=max_articles)
        if not articles:
            return False, "", []

        sources = []
        context_blocks = []
        for art in articles[:max_articles]:
            art_data = cls.get_article_content(art["url"])
            raw_text = art_data.get("content", "")
            if not raw_text:
                continue
            trimmed = raw_text[:max_chars_per_article].strip()
            block = (
                f"📖 [موقع القديس تكلاهيمانوت - St-Takla.org]\n"
                f"العنوان: {art['title']}\n"
                f"الرابط المرجعي: {art['url']}\n"
                f"المحتوى المستخلص:\n{trimmed}\n"
            )
            context_blocks.append(block)
            sources.append({
                "title": art["title"],
                "url": art["url"],
                "id": art["id"]
            })

        if not context_blocks:
            return False, "", []

        combined_text = "\n" + "="*50 + "\n" + "\n\n".join(context_blocks) + "\n" + "="*50
        return True, combined_text, sources

class ForeignPatristicsEngine:
    """
    Curated foreign academic patristic & manuscript references
    (CCEL, New Advent Fathers, CSNTM, Biblical Archaeology Society).
    """
    SCHOLARLY_RESOURCES = [
        {
            "name": "Christian Classics Ethereal Library (CCEL)",
            "url": "https://www.ccel.org/fathers",
            "scope": "Ante-Nicene, Nicene & Post-Nicene Fathers (38 volumes complete early church consensus)."
        },
        {
            "name": "New Advent Church Fathers & Catholic Encyclopedia",
            "url": "https://www.newadvent.org/fathers/",
            "scope": "Searchable English patristic writings (Athanasius, Cyril, Chrysostom, Basil, Augustine)."
        },
        {
            "name": "Center for the Study of New Testament Manuscripts (CSNTM)",
            "url": "https://www.csntm.org/",
            "scope": "High-resolution digital Greek NT manuscripts (Codex Sinaiticus, Vaticanus, Alexandrinus)."
        },
        {
            "name": "Biblical Archaeology Review & Society",
            "url": "https://www.biblicalarchaeology.org/",
            "scope": "Neutral scientific archaeological discoveries confirming biblical history."
        }
    ]

    @classmethod
    def get_patristic_resources_info(cls) -> list:
        return cls.SCHOLARLY_RESOURCES

class OfflineLibrarySettler:
    """
    محرك التسكين الأوفلاين الشامل داخل مكتبة المستخدم (I:\...):
    تحميل أبحاث د. غالي ومقالات الدفاعيات، توليدها ككتب Word منسقة بالصليب،
    وفهرستها في قاعدة بيانات المكتبة file_archive.db لتعمل أوفلاين مدى الحياة.
    """
    @classmethod
    def get_default_ghaly_settle_dir(cls, library_root: str = None) -> str:
        if library_root and os.path.exists(library_root):
            base = os.path.join(library_root, "الكتاب المقدس والعلم", "موسوعة دكتور غالي الشاملة")
        elif os.path.exists(r"I:\2021\2020\✠ Cross Coptic Library ✠"):
            base = r"I:\2021\2020\✠ Cross Coptic Library ✠\الكتاب المقدس والعلم\موسوعة دكتور غالي الشاملة"
        else:
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "موسوعة_دكتور_غالي")
        os.makedirs(base, exist_ok=True)
        return base

    @classmethod
    def settle_ghaly_research(cls, query: str, output_dir: str = None, max_articles: int = 15, progress_callback=None, project_id: int = 1) -> list:
        """
        Searches drghaly.com, downloads articles, compiles each as a .docx book,
        saves to local library, and indexes into database_handler.
        """
        from modules import database_handler

        target_base = output_dir or cls.get_default_ghaly_settle_dir()
        clean_cat = re.sub(r'[^\w\s\u0621-\u064A]', '', query).strip().replace(" ", "_")[:25] or "أبحاث_دفاعية"
        target_dir = os.path.join(target_base, clean_cat)
        os.makedirs(target_dir, exist_ok=True)

        articles = DrGhalyEngine.search_articles(query, limit=max_articles)
        if not articles:
            return []

        saved_files = []
        total = len(articles)

        for idx, art in enumerate(articles):
            title = art.get("title", f"بحث_رقم_{idx+1}")
            clean_title = re.sub(r'[^\w\s\u0621-\u064A]', '', title).strip().replace(" ", "_")[:40]
            file_name = f"د_غالي_{clean_title}.docx"
            file_path = os.path.join(target_dir, file_name)

            if progress_callback:
                progress_callback(idx + 1, total, title, file_path)

            # Skip download if already exists locally
            if not os.path.exists(file_path) or os.path.getsize(file_path) < 1000:
                art_data = DrGhalyEngine.get_article_content(art["url"])
                content = art_data.get("content", "")
                if not content or len(content) < 100:
                    continue
                save_article_as_docx(title, content, art["url"], file_path)

            # Index into file_archive.db
            try:
                stat = os.stat(file_path)
                con = database_handler.get_connection()
                cur = con.cursor()
                cur.execute("SELECT id FROM root_folders WHERE id = ?", (project_id,))
                rf_row = cur.fetchone()
                if rf_row:
                    rf_id = rf_row[0]
                else:
                    cur.execute("SELECT id FROM root_folders LIMIT 1")
                    first_rf = cur.fetchone()
                    if first_rf:
                        rf_id = first_rf[0]
                    else:
                        cur.execute("INSERT OR IGNORE INTO root_folders (folder_path) VALUES (?)", (target_base,))
                        con.commit()
                        cur.execute("SELECT id FROM root_folders WHERE folder_path = ?", (target_base,))
                        rf_id = cur.fetchone()[0]
                con.close()

                file_record = [(
                    rf_id,
                    os.path.abspath(file_path),
                    os.path.basename(file_path),
                    ".docx",
                    stat.st_size,
                    stat.st_mtime,
                    "الكتاب المقدس والعلم",
                    f"موسوعة د. غالي أوفلاين: {title}"
                )]
                database_handler.process_file_batch(file_record, is_update=False)
            except Exception as ex_db:
                print(f"Indexing error for {file_path}: {ex_db}")

            saved_files.append(file_path)

        return saved_files
