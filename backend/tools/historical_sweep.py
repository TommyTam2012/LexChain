# ==========================================================
# LexChain — Historical Sweep Wrapper
# ==========================================================
# Purpose:
#   Collect HKLII cases by topic × year × court.
#   Designed for deep precedent gathering (CFI, CA, CFA).
# ==========================================================

import subprocess, time, datetime, os
from pathlib import Path

# ---------- Config ----------
TOPIC_FILE = Path(__file__).parent / "topics.txt"
YEARS_FILE = Path(__file__).parent / "years.txt"
COURTS_FILE = Path(__file__).parent / "courts.txt"
LOG_DIR = Path("../data/hklii_cache/logs").resolve()
PROGRESS_FILE = LOG_DIR / "sweep_progress.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

MAX_PER_QUERY = 50          # results per combination
DELAY_BETWEEN_QUERIES = 90  # seconds delay between queries
PYTHON_CMD = r"C:\Users\user\Desktop\LexChain\.venv\Scripts\python.exe"

# ---------- Timestamp ----------
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log_path = LOG_DIR / f"historical_sweep_log_{datetime.date.today().isoformat()}.txt"

with open(log_path, "a", encoding="utf-8") as log:
    log.write(f"\n=== Historical Sweep Started: {ts} ===\n")

# ---------- Load Inputs ----------
def load_list(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

topics = load_list(TOPIC_FILE)
years = load_list(YEARS_FILE)
courts = load_list(COURTS_FILE)

# ---------- Progress Tracking ----------
completed = set()
if PROGRESS_FILE.exists():
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        completed = {line.strip() for line in f if line.strip()}

# ---------- Sweep Loop ----------
for court in courts:
    for year in years:
        for topic in topics:
            key = f"{court}_{year}_{topic}"
            if key in completed:
                continue

            query = f"{topic} {year} {court}"
            cmd = [
                PYTHON_CMD,
                "tools/hklii_playwright_extract.py",
                "--query", query,
                "--max", str(MAX_PER_QUERY)
            ]

            start = datetime.datetime.now()
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"[{start:%H:%M:%S}] Starting: {query}\n")

            try:
                subprocess.run(cmd, check=True)
                with open(PROGRESS_FILE, "a", encoding="utf-8") as prog:
                    prog.write(key + "\n")
                status = "✓"
            except subprocess.CalledProcessError as e:
                status = f"x ({e})"

            # Delay
            time.sleep(DELAY_BETWEEN_QUERIES)

            end = datetime.datetime.now()
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"[{end:%H:%M:%S}] {status} Finished: {query}\n")

# ---------- Completion ----------
with open(log_path, "a", encoding="utf-8") as log:
    log.write(f"=== Historical Sweep Completed at {datetime.datetime.now():%H:%M:%S} ===\n")

print(f"[✓] Historical sweep finished. Log saved → {log_path}")
