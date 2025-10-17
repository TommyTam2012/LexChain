import os, json, re
from typing import Any, Dict, List
import httpx

try:
    from dotenv import load_dotenv  # dev only
    load_dotenv()
except Exception:
    pass

try:
    from bs4 import BeautifulSoup  # HTML fallback
except Exception:  # if not installed, we still run (but HTML parse disabled)
    BeautifulSoup = None  # type: ignore

BASE = (os.getenv("HKLII_BASE_URL") or "").rstrip("/")
TIMEOUT = float(os.getenv("HKLII_REQ_TIMEOUT", "10"))

HEADERS = {
    "Accept": "application/json,text/javascript,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8,zh;q=0.6",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.hklii.hk/",
}

def _ok(data: Dict[str, Any] | List[Dict[str, Any]], url: str, status: int) -> Dict[str, Any]:
    return {"ok": True, "url": url, "status": status, "data": data}

def _err(msg: str, *, url: str = "", status: int | None = None, detail: str | None = None) -> Dict[str, Any]:
    out = {"ok": False, "error": msg}
    if url:
        out["url"] = url
    if status is not None:
        out["status"] = status
    if detail:
        out["detail"] = detail
    return out

def _normalize_html_results(soup: "BeautifulSoup") -> List[Dict[str, Any]]:
    """
    Best-effort extraction:
    - Prefer anchors within obvious result containers.
    - Otherwise, collect anchors that look like case links.
    """
    results: List[Dict[str, Any]] = []

    # heuristic containers
    containers = soup.select(
        ".search-results, .results, .result-list, ul, ol, main, #content"
    )
    if not containers:
        containers = [soup]

    seen = set()
    for c in containers:
        for a in c.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if not href or not text:
                continue
            # normalize absolute URL
            if href.startswith("/"):
                href_abs = f"https://www.hklii.hk{href}"
            elif href.startswith("http"):
                href_abs = href
            else:
                href_abs = f"https://www.hklii.hk/{href.lstrip('./')}"
            # filter to likely case pages
            if not re.search(r"/eng/|/hk/|/jud|/cases|/tpl/", href_abs, re.I):
                continue
            key = (text, href_abs)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "title": text,
                "url": href_abs,
                "source": "HKLII",
                "type": "link"
            })
            # keep it modest
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break

    return results

async def hklii_search(params: Dict[str, Any]) -> Dict[str, Any]:
    if not BASE:
        return _err("HKLII_BASE_URL not set")

    # Try common JSON hints (names vary on legacy endpoints)
    enriched = {
        **params,
        "format": params.get("format", "json"),
        "output": params.get("output", "json"),
        "callback": "",  # avoid JSON-P wrapper
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(BASE, params=enriched)
            url = str(r.request.url)
            text = r.text

            # Attempt JSON first
            try:
                data = r.json()
                if r.status_code >= 400:
                    return _err("HKLII returned error", url=url, status=r.status_code, detail=json.dumps(data)[:700])
                return _ok(data, url, r.status_code)
            except json.JSONDecodeError:
                pass  # fall through to HTML

            # HTML fallback (best-effort)
            if BeautifulSoup is None:
                return _err("Non-JSON response from HKLII (bs4 not installed)", url=url, status=r.status_code, detail=text[:700])

            soup = BeautifulSoup(text, "html.parser")
            items = _normalize_html_results(soup)
            if items:
                return _ok(items, url, r.status_code)

            # No parseable results — return trimmed HTML
            return _err("Non-JSON response from HKLII", url=url, status=r.status_code, detail=text[:700])

    except httpx.ConnectError as e:
        return _err("Connection error to HKLII", url=BASE, detail=str(e))
    except httpx.ReadTimeout as e:
        return _err(f"HKLII timeout after {TIMEOUT}s", url=BASE, detail=str(e))
    except Exception as e:
        return _err("Unexpected error calling HKLII", url=BASE, detail=str(e))
