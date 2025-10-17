# nightly_crawl.ps1
# Robust runner for the Playwright nightly crawl, with venv + logging.

$ErrorActionPreference = "Stop"

# --- Paths (resolve from this script's folder) ---
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path              # ...\backend\tools
$RepoRoot   = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path          # ...\LexChain
$BackendDir = (Join-Path $RepoRoot "backend")
$VenvAct    = (Join-Path $RepoRoot ".venv\Scripts\Activate.ps1")
$LogDir     = (Join-Path $BackendDir "logs")
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# --- Log file ---
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "nightly_crawl_$stamp.log"

# --- Context stamp to help future debugging ---
"=== Nightly Crawl Invoked ===" | Tee-Object -FilePath $LogFile -Append
"Local time: $(Get-Date)"      | Tee-Object -FilePath $LogFile -Append
"Time zone : $((Get-TimeZone).Id)" | Tee-Object -FilePath $LogFile -Append
"User      : $env:USERNAME"    | Tee-Object -FilePath $LogFile -Append
"ScriptRoot: $ScriptRoot"      | Tee-Object -FilePath $LogFile -Append
"RepoRoot  : $RepoRoot"        | Tee-Object -FilePath $LogFile -Append
"BackendDir: $BackendDir"      | Tee-Object -FilePath $LogFile -Append
"----------------------------------------------" | Tee-Object -FilePath $LogFile -Append

# --- Activate venv & run ---
Set-Location $BackendDir

if (Test-Path $VenvAct) {
    . $VenvAct
    "Venv: activated." | Tee-Object -FilePath $LogFile -Append
} else {
    "WARNING: venv activate script not found: $VenvAct" | Tee-Object -FilePath $LogFile -Append
}

# Ensure Playwright deps are installed (first run safety) — PowerShell-native
try {
    & python -m playwright install --with-deps *>&1 | Tee-Object -FilePath $LogFile -Append
    "Playwright check: OK" | Tee-Object -FilePath $LogFile -Append
} catch {
    "Playwright install failed (continuing if already installed): $_" | Tee-Object -FilePath $LogFile -Append
}

# Run the actual nightly crawl Python
# (Assumes backend/tools/nightly_crawl.py exists and handles its own warmup + topics)
"Starting nightly_crawl.py ..." | Tee-Object -FilePath $LogFile -Append
$cmd = "python .\tools\nightly_crawl.py"
cmd /c $cmd 2>&1 | Tee-Object -FilePath $LogFile -Append

"=== Nightly Crawl Finished at $(Get-Date) ===" | Tee-Object -FilePath $LogFile -Append
