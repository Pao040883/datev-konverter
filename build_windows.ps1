$ErrorActionPreference = 'Stop'

Write-Host "[1/4] Pruefe Python..."
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 'py' wurde nicht gefunden. Bitte Python 3 installieren."
}

Write-Host "[2/4] Virtuelle Umgebung anlegen (falls nicht vorhanden)..."
if (-not (Test-Path ".venv/Scripts/python.exe")) {
    py -3 -m venv .venv
}

Write-Host "[3/4] Abhaengigkeiten installieren..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller

Write-Host "[4/4] EXE bauen..."
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --splash splash.png --name DATEV-Konverter datev_konverter.py

Write-Host ""
Write-Host "Fertig. Die EXE liegt in: dist/DATEV-Konverter.exe"
