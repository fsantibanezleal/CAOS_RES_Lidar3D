# One-shot environment setup (Python 3.12 .venv + torch cu126 + vendored lingbot-map).
$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot\.."
py -3.12 -m venv .venv
$py = '.venv\Scripts\python.exe'
& $py -m pip install -U pip
& $py -m pip install -r requirements.txt
# Heavy engine: torch matching the local driver (560.x -> CUDA 12.6), then vendored lingbot-map.
& $py -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu126
& $py -m pip install -e third_party/lingbot-map --no-deps
Write-Host "Setup done. Run:  $py run_app.py   (then http://127.0.0.1:8120)"
