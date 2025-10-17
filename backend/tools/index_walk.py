# ==========================================================
# LexChain Index-Walk Collector (Phase 2 - Step 2)
# ==========================================================
import os, json, random, time
from datetime import date, datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# ---------- Config ----------
BASE_URL = "https://www.hklii.hk"
COURTS = ["hkcfa", "hkca", "hkcfi", "hkdc"]
START_YEAR = 1990
END_YEAR = date.today().year
CACHE_DIR = Path("../data/hklii_cache").resolve()
STATE_FILE = Path("../data/indexwalk_state.json").resolve()
MAX_CASES_PER_RUN = 300
SLEEP_BETWEEN = (1, 3)  # seconds
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------- Helpers ----------
def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def list_case_links(court: str, year: int):
    url = f"{BASE_URL}/en/cases/{court}/{year}/"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = [
            a["href"]
            for a in soup.select("a[href]")
            if a["href"].startswith(f"/en/cases/{court}/{year}/")
        ]
        return sorted(set(links))
    except Exception as e:
        print(f"  [!] Error reading index {court}-{year}: {e}")
        return []

def fetch_case(url_path: str):
    """Download and return full case HTML + metadata dict."""
    full_url = f"{BASE_URL}{url_path}"
    try:
        r = requests.get(full_url, timeout=15)
        if r.status_code != 200:
            print(f"  [!] HTTP {r.status_code} → {full_url}")
            return None
        return {"url": full_url, "html": r.text}
    except Exception as e:
        print(f"  [!] Fetch error {full_url}: {e}")
        return None

def read_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"court": COURTS[0], "year": START_YEAR}

def write_state(court: str, year: int):
    save_json(STATE_FILE, {"court": court, "year": year})

# ---------- Freshness Mode ----------
def crawl_recent_days(days=7, max_cases=50):
    """Quick pass for new cases from the last N days per court."""
    print(f"\n=== Recent {days}-Day Freshness Pass ===")
    cutoff = datetime.now() - timedelta(days=days)
    total = 0
    for court in COURTS:
        url = f"{BASE_URL}/en/cases/{court}/"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            year = datetime.now().year
            links = [
                a["href"]
                for a in soup.select("a[href]")
                if f"/{year}/" in a["href"]
            ]
            for link in sorted(set(links)):
                parts = link.strip("/").split("/")
                file_id = "_".join(parts[-3:]).replace(".html", "")
                out_path = CACHE_DIR / f"case_en_cases_{file_id}.json"
                if out_path.exists():
                    continue
                case = fetch_case(link)
                if case:
                    save_json(out_path, case)
                    total += 1
                    print(f"  [✓] Fresh {court.upper()} {file_id}")
                if total >= max_cases:
                    print("[⚓] Freshness quota reached.")
                    return
                time.sleep(random.uniform(*SLEEP_BETWEEN))
        except Exception as e:
            print(f"  [!] Freshness error {court}: {e}")
    print(f"[✓] Freshness complete, {total} new cases.")

# ---------- Compact Driver ----------
def main():
    mode = os.getenv("MODE", "indexwalk")
    if mode == "fresh":
        crawl_recent_days()
        return

    # default: index-walk backfill
    print("=== Phase 2: Index-Walk Collector ===")
    state = read_state()
    total_saved = 0
    start_found = False

    for court in COURTS:
        for year in range(START_YEAR, END_YEAR + 1):
            if not start_found:
                if court == state.get("court") and year == state.get("year"):
                    start_found = True
                else:
                    continue

            links = list_case_links(court, year)
            print(f"\n[{court.upper()} {year}] Found {len(links)} case links")

            for link in links:
                parts = link.strip("/").split("/")
                file_id = "_".join(parts[-3:]).replace(".html", "")
                out_path = CACHE_DIR / f"case_en_cases_{file_id}.json"
                if out_path.exists():
                    continue

                case_data = fetch_case(link)
                if case_data:
                    save_json(out_path, case_data)
                    total_saved += 1
                    print(f"  [✓] Saved {out_path.name} ({total_saved}/{MAX_CASES_PER_RUN})")

                time.sleep(random.uniform(*SLEEP_BETWEEN))

                if total_saved >= MAX_CASES_PER_RUN:
                    print("\n[⚓] Quota reached — stopping for tonight.")
                    write_state(court, year)
                    print(f"[i] Progress saved → {STATE_FILE}")
                    return

            write_state(court, year)

    print(f"\n=== Crawl complete. Total new cases saved: {total_saved} ===")

if __name__ == "__main__":
    main()
