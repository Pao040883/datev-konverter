Windows-Setup ohne .bat/.vbs (falls Kopieren blockiert wird)

1) Python 3 installieren:
   https://www.python.org/downloads/windows/

2) CMD im Ordner mit datev_konverter.py oeffnen.

3) Befehle ausfuehren:
   py -3 -m venv .venv
   .venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller
   .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name DATEV-Konverter datev_konverter.py

4) Ergebnis:
   dist\DATEV-Konverter.exe

Hinweis:
Wenn die IT Skript-Dateien blockiert, ist dieses Paket meist kopierbar, weil es nur .py und .txt enthaelt.
