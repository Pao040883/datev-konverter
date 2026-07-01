@echo off
setlocal

cd /d "%~dp0"

echo ==================================================
echo DATEV-Konverter Windows Build
echo Arbeitsordner: %cd%
echo ==================================================
echo.
echo Hinweis: Wenn dieses Fenster sofort schliesst, nutze start_build_windows.vbs
echo.

echo [1/4] Pruefe Python...
where py >nul 2>nul
if %errorlevel% neq 0 (
  echo Python Launcher (py) nicht gefunden. Bitte Python 3 installieren.
  echo Download: https://www.python.org/downloads/windows/
  echo.
  pause
  exit /b 1
)
py -3 --version
echo.

echo [2/4] Virtuelle Umgebung anlegen (falls nicht vorhanden)...
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if %errorlevel% neq 0 (
    echo Fehler beim Erstellen der virtuellen Umgebung.
    echo.
    pause
    exit /b 1
  )
)
echo OK
echo.

echo [3/4] Abhaengigkeiten installieren...
".venv\Scripts\python.exe" -m pip install --upgrade pip pyinstaller
if %errorlevel% neq 0 (
  echo Fehler bei der Installation von PyInstaller.
  echo.
  pause
  exit /b 1
)
echo.

echo [4/4] EXE bauen...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --splash splash.png --name DATEV-Konverter datev_konverter.py
if %errorlevel% neq 0 (
  echo Fehler beim Build.
  echo.
  pause
  exit /b 1
)

echo.
echo Fertig. Die EXE liegt in: dist\DATEV-Konverter.exe
echo.
pause
exit /b 0
