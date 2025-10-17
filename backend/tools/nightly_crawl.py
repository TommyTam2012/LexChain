# ===============================================================
# LexChain Nightly Crawl — Randomized Topics Mode (Phase 1)
# ===============================================================
import os, sys, random, datetime as dt
from pathlib import Path

# --- Playwright dispatcher: call existing CLI script safely ---
def run_playwright_query(topic: str):
    """
    Calls tools/hklii_playwright_extract.py via CLI:
      python tools/hklii_playwright_extract.py --query "<topic>" [--max N] [--headful]
    Env controls:
      MAX_LINKS: int (default 5)
      HEADFUL  : "1" to open browser (default off/headless)
    """
    import subprocess

    TOOLS_DIR = Path(__file__).parent
    script = TOOLS_DIR / "hklii_playwright_extract.py"
    if not script.exists():
        raise FileNotFoundError(f"Cannot find Playwright script: {script}")

    max_links = os.getenv("MAX_LINKS", "5")
    headful   = os.getenv("HEADFUL", "0") == "1"

    cmd = [sys.executable, str(script), "--query", topic, "--max", str(max_links)]
    if headful:
        cmd.append("--headful")

    print(f"[i] Starting Playwright for query: {topic}")
    subprocess.run(cmd, check=True)

# ---------- Topic rotation helpers ----------
def load_all_topics(topics_file: Path) -> list[str]:
    if not topics_file.exists():
        raise FileNotFoundError(f"topics.txt not found: {topics_file}")
    topics = []
    for line in topics_file.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            topics.append(s)
    return topics

def pick_tonight_topics(all_topics: list[str], k: int) -> list[str]:
    k = max(1, min(k, len(all_topics)))
    seed_env = os.getenv("TOPIC_SEED")
    seed = int(seed_env) if seed_env else int(dt.date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    topics = all_topics[:]  # copy
    rng.shuffle(topics)
    return topics[:k]

# ---------- Warm-up ----------
def warmup():
    print("[i] Warming up Playwright browser...")
    run_playwright_query("warmup")
    print("[✓] Warm-up complete. Beginning main crawl...")

# ---------- Main ----------
def main():
    TOOLS_DIR = Path(__file__).parent
    TOPICS_FILE = TOOLS_DIR / "topics.txt"
    all_topics = load_all_topics(TOPICS_FILE)
    k = int(os.getenv("TOPICS_PER_NIGHT", "15"))
    tonight_topics = pick_tonight_topics(all_topics, k)

    print(f"=== Nightly Crawl Started: {dt.datetime.now():%Y-%m-%d %H:%M:%S} ===")
    print(f"[i] Topics available: {len(all_topics)} | Tonight’s quota: {k}")
    for i, t in enumerate(tonight_topics, 1):
        print(f"   {i:2d}. {t}")

    if os.getenv("DRY_RUN", "0") == "1":
        print("[i] DRY_RUN=1 → not crawling, just listing topics.")
        return

    warmup()

    for idx, topic in enumerate(tonight_topics, 1):
        print(f"[{dt.datetime.now():%H:%M:%S}] ({idx}/{len(tonight_topics)}) Starting: {topic}")
        try:
            run_playwright_query(topic)
            print(f"[✓] Finished: {topic} at {dt.datetime.now():%H:%M:%S}")
        except Exception as e:
            print(f"[!] ERROR topic='{topic}': {e}")

    print(f"=== Nightly Crawl Finished at {dt.datetime.now():%Y-%m-%d %H:%M:%S} ===")

if __name__ == "__main__":
    main()
