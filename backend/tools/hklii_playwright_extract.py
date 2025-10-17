import asyncio, json, os, re, time, argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

# ==========================================================
# CONFIG — robust, project-root-based paths
# ==========================================================
START_URL = "https://www.hklii.hk/"
BASE_DIR = Path(__file__).resolve().parent              # .../backend/tools
PROJECT_ROOT = BASE_DIR.parent                          # .../backend
CACHE_DIR = (PROJECT_ROOT / "data" / "hklii_cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_PER_RUN_DEFAULT = 3
NAV_TIMEOUT_MS = 30000  # 30s
HUMAN_DELAY_SEC = (1.2, 2.2)

# ==========================================================
# HELPERS
# ==========================================================
def save_json(p: Path, obj: Any):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def guess_year(text: str) -> Optional[int]:
    m = re.search(r"(19|20)\d{2}", text)
    return int(m.group(0)) if m else None

def normalize_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"https://www.hklii.hk{href}"
    return f"https://www.hklii.hk/{href.lstrip('./')}"

def canonicalize_url(url: str) -> str:
    s = urlsplit(url)
    path = s.path.rstrip("/")
    return urlunsplit((s.scheme, s.netloc, path, "", ""))

def case_key_from_url(url: str) -> str:
    s = urlsplit(canonicalize_url(url))
    return s.path.lower().lstrip("/")

def extract_case_body(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title = clean_text(soup.title.get_text()) if soup.title else ""
    selectors = [
        "article", "#content", "main", ".judgment", ".content",
        "#main", ".casebody", ".judgment-content"
    ]
    body_text = ""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            body_text = clean_text(el.get_text(" "))
            if len(body_text) > 800:
                break
    if len(body_text) < 800:
        body_text = clean_text(soup.get_text(" "))

    header_candidates = []
    for sel in ["h1", "h2", ".header", ".title", ".heading"]:
        for el in soup.select(sel):
            txt = clean_text(el.get_text(" "))
            if txt:
                header_candidates.append(txt)

    header_blob = " | ".join(header_candidates[:5])
    year = guess_year(header_blob) or guess_year(title) or guess_year(body_text)
    court = None
    for key in [
        "Court of Final Appeal", "Court of Appeal",
        "Court of First Instance", "District Court",
        "Magistrates’ Court",
    ]:
        if re.search(re.escape(key), header_blob, re.IGNORECASE) or re.search(
            re.escape(key), title, re.IGNORECASE
        ):
            court = key
            break

    date_iso = None
    try:
        dt = dtparser.parse(header_blob, fuzzy=True)
        if dt:
            date_iso = dt.date().isoformat()
    except Exception:
        pass

    return {
        "title": title,
        "court": court,
        "year": year,
        "date": date_iso,
        "content": body_text,
        "length": len(body_text),
        "headers_seen": header_candidates[:8],
    }

async def human_pause(page):
    import random, asyncio
    await asyncio.sleep(random.uniform(*HUMAN_DELAY_SEC))
    try:
        await page.mouse.wheel(0, random.randint(200, 800))
    except Exception:
        pass

# ==========================================================
# PAGE HELPERS
# ==========================================================
async def extract_search_results_html(page) -> str:
    await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
    html = await page.content()
    (CACHE_DIR / "rendered_search.html").write_text(html, encoding="utf-8")
    try:
        await page.screenshot(path=str(CACHE_DIR / "rendered_search.png"), full_page=True)
    except Exception:
        pass
    return html

async def click_next_page(page) -> bool:
    try:
        selectors = [
            "a[aria-label='Next']", "button[aria-label='Next']",
            "text=Next", "a:has-text('›')", "a:has-text('»')"
        ]
        for sel in selectors:
            el = page.locator(sel)
            if await el.count() > 0 and await el.first.is_enabled():
                await el.first.click()
                await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
                return True
    except Exception:
        pass
    return False

async def click_case_filter(page):
    try:
        await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
        for sel in [
            "text=Case(EN)", "text=Case (EN)",
            "text=Cases (EN)", "text=Cases(EN)",
        ]:
            chip = page.locator(sel)
            if await chip.count() > 0:
                await chip.first.click()
                await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
                return True
        try:
            btn = page.get_by_role("button", name=re.compile(r"Case\s*\(EN\)", re.I))
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
                return True
        except Exception:
            pass
        any_el = page.get_by_text(re.compile(r"Case\s*\(EN\)", re.I))
        if await any_el.count() > 0:
            await any_el.first.click()
            await page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
            return True
    except Exception:
        pass
    return False

def parse_result_links(html: str, max_items: int) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    results: List[Dict[str, str]] = []
    seen_keys = set()
    ALLOW = re.compile(r"/(eng/hk|en)/cases/.+(\.html?)?($|\?)", re.I)
    DENY  = re.compile(r"/en/legis/|/en/reg/|/databases|/about|/news|/donors|hklii2023|/feedback|/operators", re.I)
    anchors = soup.select(".v-data-table__wrapper a[href], a.routing[href], a[href]")
    for a in anchors:
        href = (a.get("href") or "").strip()
        text = clean_text(a.get_text(" "))
        if not href or not text:
            continue
        url = normalize_url(href)
        if not url or DENY.search(url) or not ALLOW.search(url):
            continue
        key = case_key_from_url(url)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        results.append({"title": text, "url": canonicalize_url(url)})
        if len(results) >= max_items:
            break
    return results

# ==========================================================
# MAIN EXECUTION
# ==========================================================
async def run(query: str, max_results: int = RESULTS_PER_RUN_DEFAULT, headful: bool = False):
    out_search = CACHE_DIR / f"search_{re.sub(r'[^a-z0-9]+','_',query.lower()).strip('_')}.json"
    print(f"[i] Starting Playwright for query: {query}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headful, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        await page.goto(START_URL, wait_until="domcontentloaded")
        await human_pause(page)

        search_locators = [
            "input[name='q']", "input[type='search']",
            "input[placeholder*='Search']", "input[placeholder*='search']",
            "form input[type='text']", "input"
        ]
        found = False
        for sel in search_locators:
            loc = page.locator(sel)
            if await loc.count() > 0:
                try:
                    await loc.first.fill(query)
                    await human_pause(page)
                    await loc.first.press("Enter")
                    found = True
                    break
                except Exception:
                    continue
        if not found:
            print("[!] Could not find search box; using fallback URL…")
            await page.goto(f"{START_URL}en/search/?q={query}", wait_until="domcontentloaded")

        await human_pause(page)
        await click_case_filter(page)
        try:
            await page.wait_for_selector(".v-data-table__wrapper a[href], a.routing[href]", timeout=NAV_TIMEOUT_MS)
        except Exception:
            pass

        await human_pause(page)
        html = await extract_search_results_html(page)
        results = parse_result_links(html, max_results)

        while len(results) < max_results:
            moved = await click_next_page(page)
            if not moved:
                break
            await human_pause(page)
            html = await extract_search_results_html(page)
            more = parse_result_links(html, max_results - len(results))
            results.extend(more)

        save_json(out_search, {"query": query, "ts": now_iso(), "count": len(results), "results": results})
        print(f"[i] Saved search JSON → {out_search} (found {len(results)} unique links)")

        extracted: List[Dict[str, Any]] = []
        for i, item in enumerate(results, 1):
            url = item["url"]
            print(f"[i] [{i}/{len(results)}] Opening case: {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await human_pause(page)
                case_html = await page.content()
                case_data = extract_case_body(case_html)
                case_data.update({
                    "source": "HKLII",
                    "url": url,
                    "query": query,
                    "ts": now_iso(),
                    "ok": case_data.get("length", 0) > 800
                })
                case_key = case_key_from_url(url)
                safe_key = re.sub(r"[^a-z0-9]+", "_", case_key).strip("_")[:120]
                out_case = CACHE_DIR / f"case_{safe_key}.json"
                save_json(out_case, case_data)
                print(f"    ↳ saved → {out_case} (len={case_data.get('length')})")
                extracted.append(case_data)
            except Exception as e:
                print(f"    [x] Failed to open/parse: {url} | {e}")

        await context.close()
        await browser.close()

    summary = {
        "query": query,
        "ts": now_iso(),
        "total_found": len(results),
        "total_extracted": sum(1 for c in extracted if c.get('ok')),
        "cases": [
            {
                "title": c.get("title"),
                "court": c.get("court"),
                "year": c.get("year"),
                "date": c.get("date"),
                "length": c.get("length"),
                "url": c.get("url"),
                "ok": c.get("ok")
            }
            for c in extracted
        ],
    }
    save_json(CACHE_DIR / f"summary_{re.sub(r'[^a-z0-9]+','_',query.lower()).strip('_')}.json", summary)
    print(f"[✓] Done. Extracted {summary['total_extracted']} full case(s) out of {summary['total_found']} unique links.")
    print(f"[✓] All data saved to → {CACHE_DIR}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HKLII Playwright extractor")
    parser.add_argument("--query", "-q", required=True, help="Search term (e.g. arbitration)")
    parser.add_argument("--max", "-k", type=int, default=RESULTS_PER_RUN_DEFAULT, help="Max result links to open")
    parser.add_argument("--headful", action="store_true", help="Run with a visible browser window")
    args = parser.parse_args()
    asyncio.run(run(args.query, max_results=args.max, headful=args.headful))
