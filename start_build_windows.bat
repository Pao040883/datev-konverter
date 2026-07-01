@echo off
cd /d "%~dp0"
set "BUILD_SCRIPT=%~dp0build_windows.bat"

if not exist "%BUILD_SCRIPT%" (
  echo build_windows.bat wurde nicht gefunden.
  echo Bitte ZIP komplett entpacken und erneut versuchen.
  pause
  exit /b 1
)

call "%BUILD_SCRIPT%"
echo.
echo Fenster bleibt offen. Taste druecken zum Schliessen.
pause
