#!/bin/zsh
set -e

cd "$(dirname "$0")"

# Priorisiere bewusst Homebrew-Python, um systemweites Python 3.9/Tk 8.5 zu vermeiden.
if [[ -n "${PYTHON_BIN:-}" ]]; then
  CANDIDATE_PYTHONS=("$PYTHON_BIN")
else
  CANDIDATE_PYTHONS=(
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "$(command -v python3 2>/dev/null || true)"
  )
fi

PYTHON_BIN=""
for candidate in "${CANDIDATE_PYTHONS[@]}"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Kein passendes Python gefunden. Bitte Python 3.11+ installieren (z. B. Homebrew)."
  echo "Beispiel: brew install python@3.12"
  exit 1
fi

PY_INFO="$($PYTHON_BIN -c 'import sys; print(sys.executable); print(sys.version_info.major); print(sys.version_info.minor)')"
PYTHON_REAL="$(echo "$PY_INFO" | sed -n '1p')"
PYTHON_MAJOR="$(echo "$PY_INFO" | sed -n '2p')"
PYTHON_MINOR="$(echo "$PY_INFO" | sed -n '3p')"

if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 11) )); then
  echo "Python zu alt gefunden: $PYTHON_REAL (Version ${PYTHON_MAJOR}.${PYTHON_MINOR})"
  echo "Bitte Python 3.11+ verwenden. Beispiel: /opt/homebrew/bin/python3.12"
  exit 1
fi

if [[ "$PYTHON_REAL" == *"/CommandLineTools/usr/bin/python3"* || "$PYTHON_REAL" == "/usr/bin/python3" ]]; then
  echo "System-Python erkannt: $PYTHON_REAL"
  echo "Bitte Python 3.11+ von Homebrew oder python.org verwenden."
  exit 1
fi

echo "Verwende Python: $PYTHON_REAL"

echo "[1/4] Python-Umgebung anlegen (falls nicht vorhanden)..."
if [[ -x ".venv/bin/python" ]]; then
  VENV_INFO="$(.venv/bin/python -c 'import sys; print(sys.executable); print(sys.version_info.major); print(sys.version_info.minor)')"
  VENV_PYTHON_REAL="$(echo "$VENV_INFO" | sed -n '1p')"
  VENV_PYTHON_MAJOR="$(echo "$VENV_INFO" | sed -n '2p')"
  VENV_PYTHON_MINOR="$(echo "$VENV_INFO" | sed -n '3p')"

  if (( VENV_PYTHON_MAJOR < 3 || (VENV_PYTHON_MAJOR == 3 && VENV_PYTHON_MINOR < 11) )); then
    echo "Bestehende .venv ist zu alt (${VENV_PYTHON_MAJOR}.${VENV_PYTHON_MINOR}) und wird neu erstellt..."
    rm -rf .venv
  fi

  if [[ "$VENV_PYTHON_REAL" == *"/CommandLineTools/usr/bin/python3"* || "$VENV_PYTHON_REAL" == "/usr/bin/python3" ]]; then
    echo "Bestehende .venv nutzt System-Python und wird neu erstellt..."
    rm -rf .venv
  fi
fi

if [[ ! -x ".venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

echo "[2/4] Abhaengigkeiten installieren..."
".venv/bin/python" -m pip install --upgrade pip pyinstaller

echo "[3/4] App bauen..."
".venv/bin/python" -m PyInstaller --noconfirm --clean --windowed --name DATEV-Konverter datev_konverter.py

echo "[4/4] Fertig"
echo "App erstellt unter: dist/DATEV-Konverter.app"
