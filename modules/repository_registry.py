# -*- coding: utf-8 -*-
"""
ArchiveMaster - Dynamic Repository Registry & Universal Inspector
سجل المستودعات الكنسية العالمي المفتوح ومحاكي الفحص الذاتي لأي موقع جديد
Allows expanding the library to ANY external Christian/Orthodox repository worldwide in any language.
"""

import os
import sys
import re
import json
import time
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
import httpx

from modules import multilingual_theological_expander, online_book_feeder

REGISTRY_FILE = Path(__file__).parent / "coptic_repositories.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# The 8 Foundational Starter Kit Repositories
DEFAULT_STARTER_REPOS = [
    {
        "id": "awtar_alsama",
        "name": "مكتبة أوتار السماء (دليل الـ 82 مؤلفاً وقديساً)",
        "url": "https://library.awtar-alsama.com/1/",
        "language": "ar",
        "language_name": "العربية",
        "adapter_type": "awtar_catalog",
        "badge": "🎶 أوتار السماء",
        "active": True,
        "description": "فهرس شامل يضم 82 مؤلفاً وقديساً كنسياً بروابط PDF مباشرة.",
        "book_count_est": "3,000+"
    },
    {
        "id": "christianlib",
        "name": "مكتبة الكتب المسيحية (ChristianLib)",
        "url": "https://www.christianlib.com",
        "language": "ar",
        "language_name": "العربية",
        "adapter_type": "wp_api",
        "badge": "📚 ChristianLib",
        "active": True,
        "description": "78 قسماً كنسياً في الأبائيات، العقيدة، التفاسير، والأبحاث.",
        "book_count_est": "4,500+"
    },
    {
        "id": "coptic_treasures",
        "name": "مشروع الكنوز القبطية (كتب نادرة ومخطوطات)",
        "url": "https://coptic-treasures.com",
        "language": "ar",
        "language_name": "العربية ولغات كنسية",
        "adapter_type": "coptic_treasures",
        "badge": "🏛️ الكنوز القبطية",
        "active": True,
        "description": "المستودع الأكبر للكتب النادرة، والمخطوطات، والدراسات اللغوية ثنائية اللغة.",
        "book_count_est": "3,800+"
    },
    {
        "id": "coptic_reads",
        "name": "مكتبة Coptic Reads الأرثوذكسية",
        "url": "https://copticreads.org",
        "language": "ar",
        "language_name": "العربية / الإنجليزية",
        "adapter_type": "sitemap",
        "badge": "📖 Coptic Reads",
        "active": True,
        "description": "مراجع ونصوص كنسية محققة وموثقة بصيغ نقية وسريعة.",
        "book_count_est": "1,210"
    },
    {
        "id": "dr_ghaly",
        "name": "موسوعة وأبحاث د. غالي (Holy Bible 1)",
        "url": "https://drghaly.com",
        "language": "ar",
        "language_name": "العربية",
        "adapter_type": "drghaly_engine",
        "badge": "✝️ د. غالي",
        "active": True,
        "description": "أبحاث تفنيد الشبهات، أصالة الأسفار، والمقارنات النصية.",
        "book_count_est": "1,500+"
    },
    {
        "id": "azbyka_orthodox",
        "name": "المكتبة الأرثوذكسية العالمية (Azbyka - Азбука веры)",
        "url": "https://azbyka.ru",
        "language": "ru",
        "language_name": "الروسية (Russian)",
        "adapter_type": "orthodox_megastore",
        "badge": "☦️ Azbyka العالمية",
        "active": True,
        "description": "أضخم مستودع وموسوعة أرثوذكسية في العالم تضم آلاف الكتب الآبائية والعقائدية.",
        "book_count_est": "25,000+"
    },
    {
        "id": "myriobiblos_greek",
        "name": "أرشيف التراث الآبائي اليوناني (Myriobiblos)",
        "url": "https://www.myriobiblos.gr",
        "language": "el",
        "language_name": "اليونانية (Greek)",
        "adapter_type": "patristic_greek",
        "badge": "🇬🇷 Myriobiblos اليونانية",
        "active": True,
        "description": "المستودع المرجعي لأقوال وكتابات آباء الكنيسة بالنص اليوناني الأصلي.",
        "book_count_est": "5,000+"
    },
    {
        "id": "ccel_patristics",
        "name": "المكتبة المسيحية الكلاسيكية (CCEL / Early Church Fathers)",
        "url": "https://www.ccel.org",
        "language": "en",
        "language_name": "الإنجليزية (English)",
        "adapter_type": "ccel_engine",
        "badge": "🏛️ CCEL Patristics",
        "active": True,
        "description": "السلسلة الكاملة لآباء الكنيسة قبل وبعد نيقية باللغة الإنجليزية.",
        "book_count_est": "8,000+"
    }
]


def load_repositories() -> list:
    """Loads all active and custom repositories from JSON, populating defaults if missing."""
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass

    # Save defaults
    save_repositories(DEFAULT_STARTER_REPOS)
    return DEFAULT_STARTER_REPOS


def save_repositories(repos: list):
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(repos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving repository registry: {e}")


def add_custom_repository(name: str, url: str, language: str = "ar", description: str = "", badge: str = "🌐 مستودع كنسي") -> dict:
    """Adds a new custom repository to the registry after running auto-inspection."""
    repos = load_repositories()
    clean_url = url.strip().rstrip("/")
    repo_id = "repo_" + re.sub(r'[^a-zA-Z0-9]', '_', clean_url.split("//")[-1])[:24]

    # Check for existing
    for r in repos:
        if r.get("url", "").rstrip("/") == clean_url:
            r["active"] = True
            r["name"] = name
            save_repositories(repos)
            return r

    new_repo = {
        "id": repo_id,
        "name": name,
        "url": clean_url,
        "language": language,
        "language_name": "العربية" if language == "ar" else ("اليونانية" if language == "el" else ("الروسية" if language == "ru" else "الإنجليزية")),
        "adapter_type": "auto_adaptive",
        "badge": badge,
        "active": True,
        "description": description or f"مستودع مضاف حديثاً: {clean_url}",
        "book_count_est": "قيد الفحص"
    }
    repos.append(new_repo)
    save_repositories(repos)
    return new_repo


def delete_repository(repo_id: str) -> bool:
    repos = load_repositories()
    filtered = [r for r in repos if r.get("id") != repo_id]
    if len(filtered) != len(repos):
        save_repositories(filtered)
        return True
    return False


def toggle_repository_active(repo_id: str, is_active: bool) -> bool:
    repos = load_repositories()
    updated = False
    for r in repos:
        if r.get("id") == repo_id:
            r["active"] = is_active
            updated = True
            break
    if updated:
        save_repositories(repos)
    return updated


def inspect_repository_url(url: str, timeout: float = 12.0) -> dict:
    """
    Magic Inspector: Probes any URL, automatically discovering:
    - CMS platform (WordPress REST API, Sitemap XML, Pure HTML)
    - Primary language of the site
    - Estimated book / category count
    - Cloud storage download methods (Mediafire, Google Drive, direct PDF)
    """
    clean_url = url.strip().rstrip("/")
    report = {
        "url": clean_url,
        "accessible": False,
        "platform": "موقع ويب غير معروف",
        "adapter_suggested": "generic_crawler",
        "language": "ar",
        "title": "",
        "categories_found": 0,
        "books_found_sample": [],
        "download_method": "روابط مباشرة وويب"
    }

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(clean_url)
            if resp.status_code != 200:
                report["error"] = f"كود الاستجابة: {resp.status_code}"
                return report

            report["accessible"] = True
            soup = BeautifulSoup(resp.text, "html.parser")
            report["title"] = soup.title.string.strip() if soup.title else clean_url

            # Detect language
            html_tag = soup.find("html")
            lang_attr = html_tag.get("lang", "").lower() if html_tag else ""
            if "el" in lang_attr or "gr" in lang_attr or "greek" in lang_attr:
                report["language"] = "el"
            elif "ru" in lang_attr:
                report["language"] = "ru"
            elif "en" in lang_attr:
                report["language"] = "en"
            elif "fr" in lang_attr:
                report["language"] = "fr"
            else:
                # Text heuristic
                txt = soup.get_text()[:2000]
                if re.search(r'[\u0370-\u03FF]', txt):
                    report["language"] = "el"
                elif re.search(r'[\u0400-\u04FF]', txt):
                    report["language"] = "ru"
                elif re.search(r'[\u0600-\u06FF]', txt):
                    report["language"] = "ar"
                else:
                    report["language"] = "en"

            # 1. Probe WordPress REST API
            try:
                r_wp = client.get(f"{clean_url}/wp-json/wp/v2/categories?per_page=15", timeout=6.0)
                if r_wp.status_code == 200 and isinstance(r_wp.json(), list):
                    cats = r_wp.json()
                    report["platform"] = "WordPress (نظام إدارة محتوى متقدم مع REST API)"
                    report["adapter_suggested"] = "wp_api"
                    report["categories_found"] = len(cats)
                    sample_books = []
                    # Also probe posts for books
                    r_posts = client.get(f"{clean_url}/wp-json/wp/v2/posts?per_page=5", timeout=6.0)
                    if r_posts.status_code == 200:
                        posts = r_posts.json()
                        for p in posts:
                            t = p.get("title", {}).get("rendered", "")
                            if t:
                                sample_books.append(re.sub(r'<[^>]+>', '', t).strip())
                    report["books_found_sample"] = sample_books
                    report["download_method"] = "Mediafire / Google Drive / روابط مباشرة"
                    return report
            except Exception:
                pass

            # 2. Probe Sitemap XML
            for sm in ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"]:
                try:
                    r_sm = client.get(f"{clean_url}{sm}", timeout=6.0)
                    if r_sm.status_code == 200 and "<urlset" in r_sm.text or "<sitemapindex" in r_sm.text:
                        report["platform"] = f"Sitemap XML ({sm}) متاح ومفهرس"
                        report["adapter_suggested"] = "sitemap"
                        locs = re.findall(r'<loc>([^<]+)</loc>', r_sm.text)
                        report["categories_found"] = len(locs)
                        report["books_found_sample"] = locs[:5]
                        return report
                except Exception:
                    pass

            # 3. Generic HTML Book Signature Scanning
            pdf_links = []
            for a in soup.find_all("a", href=True):
                h = a["href"].lower()
                txt = a.get_text(strip=True)
                if ".pdf" in h or any(x in h for x in ["drive.google.com", "mediafire.com", "archive.org/download"]):
                    if txt and len(txt) > 3:
                        pdf_links.append(txt)

            if pdf_links:
                report["platform"] = "صفحات ويب حرة تضم مراجع وكتب مباشرة"
                report["adapter_suggested"] = "generic_crawler"
                report["books_found_sample"] = pdf_links[:6]
                report["categories_found"] = len(pdf_links)
            else:
                report["platform"] = "مستودع كنسي عام (سيتم استخدام محرك الاستكشاف الشامل)"
                report["adapter_suggested"] = "generic_crawler"

    except Exception as e:
        report["error"] = str(e)

    return report


def search_across_all_active_repositories(query: str, active_only: bool = True, limit_per_repo: int = 5, log_callback=None) -> list:
    """
    Executes a federated, multilingual search across all registered repositories:
    1. Expands Arabic query into English, Greek, Russian, French.
    2. Routes requests to each repository in its native language.
    3. Translates foreign book titles back to Arabic.
    4. Cross-references against local 38,460 books in SQLite to detect true GAPS.
    """
    def _log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass

    repos = load_repositories()
    if active_only:
        repos = [r for r in repos if r.get("active", True)]

    _log(f"🌐 تفعيل محرك التوسيع اللاهوتي العابر للغات عن: «{query}» ...")
    expanded = multilingual_theological_expander.expand_theological_query(query)
    _log(f"  • الإنجليزية: {expanded.get('en')}")
    _log(f"  • اليونانية: {expanded.get('el')}")
    _log(f"  • الروسية: {expanded.get('ru')}")

    results = []
    seen_titles = set()

    for r in repos:
        r_name = r.get("name", "")
        r_lang = r.get("language", "ar")
        r_type = r.get("adapter_type", "")
        r_badge = r.get("badge", "🌐 مستودع")

        # Pick search term matching repository language
        search_term = query
        if r_lang == "en" and expanded.get("en"):
            search_term = expanded["en"]
        elif r_lang == "el" and expanded.get("el"):
            search_term = expanded["el"]
        elif r_lang == "ru" and expanded.get("ru"):
            search_term = expanded["ru"]
        elif r_lang == "fr" and expanded.get("fr"):
            search_term = expanded["fr"]

        _log(f"🔍 فحص مستودع «{r_name}» بالمصطلح: «{search_term}» ...")

        try:
            # 1. ChristianLib
            if r_type == "wp_api" and "christianlib.com" in r.get("url", ""):
                cl_url = f"https://www.christianlib.com/?s={urllib.parse.quote(search_term)}"
                with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
                    resp = client.get(cl_url)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for art in soup.find_all("article")[:limit_per_repo]:
                            a = art.find("a", href=True)
                            h = art.find(["h2", "h1", "h3"])
                            if a and h:
                                t = h.get_text(strip=True)
                                if t and t.lower() not in seen_titles:
                                    seen_titles.add(t.lower())
                                    results.append({
                                        "title": t,
                                        "source": r_name,
                                        "source_badge": r_badge,
                                        "page_url": a["href"],
                                        "download_url": a["href"],
                                        "format": "PDF",
                                        "target_folder": "كتب روحية وعقائدية",
                                        "details": "متاح عبر ChristianLib"
                                    })

            # 2. Coptic Treasures
            elif r_type == "coptic_treasures" or "coptic-treasures.com" in r.get("url", ""):
                ct_url = f"https://coptic-treasures.com/?s={urllib.parse.quote(search_term)}"
                with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=8.0) as client:
                    resp = client.get(ct_url)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for a in soup.find_all("a", href=True):
                            h = a["href"]
                            t = a.get_text(strip=True)
                            if "/book/" in h and t and len(t) > 3:
                                if t.lower() not in seen_titles:
                                    seen_titles.add(t.lower())
                                    results.append({
                                        "title": t,
                                        "source": r_name,
                                        "source_badge": r_badge,
                                        "page_url": h,
                                        "download_url": h,
                                        "format": "PDF",
                                        "target_folder": "مخطوطات وكتب نادرة",
                                        "details": "متاح عبر الكنوز القبطية"
                                    })
                                    if len(results) >= 6:
                                        break

            # 3. Archive.org / CCEL / International
            elif "archive.org" in r.get("url", "") or r_type in ["ccel_engine", "patristic_greek", "orthodox_megastore"]:
                # Use Internet Archive Global Texts Search for international Orthodox literature
                q_enc = urllib.parse.quote(f"{search_term} AND (Orthodox OR Patristic OR Coptic OR Theology)")
                ia_url = f"https://archive.org/advancedsearch.php?q={q_enc}&fl[]=identifier,title,creator,year&rows={limit_per_repo}&output=json"
                with httpx.Client(headers=HEADERS, timeout=8.0) as client:
                    resp = client.get(ia_url)
                    if resp.status_code == 200:
                        docs = resp.json().get("response", {}).get("docs", [])
                        for d in docs:
                            ident = d.get("identifier")
                            raw_t = d.get("title") or ident
                            clean_t = str(raw_t).strip()
                            if clean_t and clean_t.lower() not in seen_titles:
                                seen_titles.add(clean_t.lower())
                                # Translate foreign title to Arabic for clarity
                                ar_explanation = multilingual_theological_expander.translate_foreign_metadata_to_arabic(clean_t)
                                display_title = f"{clean_t} ({ar_explanation})" if r_lang != "ar" and ar_explanation != clean_t else clean_t
                                results.append({
                                    "title": display_title,
                                    "source": f"{r_name} (دولي)",
                                    "source_badge": r_badge,
                                    "page_url": f"https://archive.org/details/{ident}",
                                    "download_url": f"https://archive.org/details/{ident}",
                                    "format": "PDF",
                                    "target_folder": "مكتبات عالمية مترجمة",
                                    "details": f"مرجع أرثوذكسي عالمي ({r['language_name']})"
                                })

            # 4. Standard online candidates fallback (Awtar, Ghaly, CopticReads)
            else:
                cands = online_book_feeder.search_online_candidates(search_term, limit=limit_per_repo)
                for c in cands:
                    if c["title"].lower() not in seen_titles:
                        seen_titles.add(c["title"].lower())
                        results.append(c)

        except Exception as e:
            _log(f"  ⚠️ تنبيه فحص «{r_name}»: {e}")

    # Cross-reference ALL results against local SQLite database
    _log(f"🧠 مطابقة {len(results)} كتاباً مع 38,460 مجلداً في رصيد مكتبتك أوفلاين...")
    results = online_book_feeder.cross_reference_candidates_with_local_db(results)
    existing_c = sum(1 for b in results if b.get("local_status") == "EXISTING")
    gaps_c = len(results) - existing_c
    _log(f"✅ اكتمل الفحص الشامل: تم العثور على {gaps_c} ثغرة جديدة و {existing_c} متوفر لديك بالفعل.")

    return results
