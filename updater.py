"""Selbst-Update ueber GitHub Releases (nur Standardbibliothek).

Ablauf beim Programmstart:
1. ``check_for_update()`` fragt das neueste Release im GitHub-Repo ab und
   vergleicht dessen Version mit ``version.__version__``.
2. Ist eine neuere Version vorhanden, fragt die Oberflaeche nach und ruft bei
   Zustimmung ``apply_update()`` auf.
3. ``apply_update()`` laedt die neue ``.exe`` herunter und tauscht sie ueber ein
   kleines Batch-Skript aus, sobald das laufende Programm beendet ist -- unter
   Windows kann eine laufende EXE nicht direkt ueberschrieben werden.

Der eigentliche Selbst-Tausch passiert nur, wenn das Programm als PyInstaller-EXE
laeuft (``sys.frozen``). Im Entwicklungsmodus (reines Python-Skript) wird nur die
Verfuegbarkeit gemeldet.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from typing import Optional

from version import __version__

# Ziel-Repository (oeffentlich -> kein Token noetig).
REPO = "Pao040883/datev-konverter"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
_USER_AGENT = "DATEV-Konverter-Updater"
_TIMEOUT = 10  # Sekunden


def is_frozen() -> bool:
    """True, wenn das Programm als gebaute EXE/App laeuft (nicht als .py)."""
    return bool(getattr(sys, "frozen", False))


def _version_tuple(value: str):
    value = value.strip().lstrip("vV")
    parts = re.split(r"[.\-+]", value)
    nums = []
    for part in parts:
        if part.isdigit():
            nums.append(int(part))
        else:
            break
    return tuple(nums)


def is_newer(remote_version: str, local_version: str = __version__) -> bool:
    """True, wenn ``remote_version`` neuer als ``local_version`` ist."""
    return _version_tuple(remote_version) > _version_tuple(local_version)


def check_for_update() -> Optional[dict]:
    """Prueft GitHub auf ein neueres Release.

    Rueckgabe bei verfuegbarem Update: ``{"version", "download_url", "notes"}``.
    Sonst ``None``. Netzwerk-/API-Fehler werden bewusst als ``None`` behandelt,
    damit das Programm auch offline startet.
    """
    try:
        request = urllib.request.Request(
            LATEST_RELEASE_URL,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - offline/kein Release ist kein Fehler
        return None

    tag = data.get("tag_name") or ""
    if not tag or not is_newer(tag):
        return None

    download_url = None
    for asset in data.get("assets", []):
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe"):
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        return None

    return {
        "version": tag.lstrip("vV"),
        "download_url": download_url,
        "notes": data.get("body") or "",
    }


def _download(url: str, target_path: str) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=_TIMEOUT * 6) as response, open(
        target_path, "wb"
    ) as out_file:
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            out_file.write(chunk)


def _build_update_script(target_exe: str, new_exe: str, log_path: str) -> str:
    """Erzeugt das Batch-Skript fuer den verzoegerten EXE-Austausch.

    Kernidee: NICHT auf eine Prozess-ID warten (bei PyInstaller-onefile haelt ein
    zweiter Bootloader-Prozess die EXE noch kurz gesperrt), sondern den ``move`` in
    einer Schleife wiederholen, bis die alte EXE freigegeben ist und ersetzt werden
    kann. Solange die neue Datei noch existiert, war der move nicht erfolgreich.
    """
    return (
        "@echo off\r\n"
        "setlocal enableextensions\r\n"
        f'set "TARGET={target_exe}"\r\n'
        f'set "NEWEXE={new_exe}"\r\n'
        f'set "LOG={log_path}"\r\n'
        'echo [%date% %time%] Update gestartet>>"%LOG%"\r\n'
        "rem kurze Anfangsverzoegerung, damit sich die alte EXE beenden kann\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"
        "set /a tries=0\r\n"
        ":retry\r\n"
        'move /Y "%NEWEXE%" "%TARGET%" >>"%LOG%" 2>&1\r\n'
        'if not exist "%NEWEXE%" goto done\r\n'
        "set /a tries+=1\r\n"
        "if %tries% geq 90 goto giveup\r\n"
        "ping -n 2 127.0.0.1 >nul\r\n"
        "goto retry\r\n"
        ":giveup\r\n"
        'echo [%date% %time%] Austausch fehlgeschlagen nach %tries% Versuchen>>"%LOG%"\r\n'
        'start "" "%TARGET%"\r\n'
        'del "%~f0"\r\n'
        "exit\r\n"
        ":done\r\n"
        'echo [%date% %time%] Austausch erfolgreich>>"%LOG%"\r\n'
        'start "" "%TARGET%"\r\n'
        'del "%~f0"\r\n'
        "exit\r\n"
    )


def apply_update(download_url: str) -> None:
    """Laedt die neue EXE und startet den verzoegerten Selbst-Tausch.

    Nur im gebauten Zustand (``is_frozen()``) sinnvoll. Nach dem Aufruf muss das
    Programm sofort beendet werden, damit das Batch-Skript die alte EXE
    ueberschreiben kann. Wirft ``RuntimeError``, wenn kein Selbst-Tausch moeglich
    ist (z. B. im Entwicklungsmodus).
    """
    if not is_frozen() or os.name != "nt":
        raise RuntimeError(
            "Automatischer Austausch ist nur in der gebauten Windows-EXE moeglich."
        )

    current_exe = os.path.abspath(sys.executable)
    tmp_dir = tempfile.gettempdir()
    # Neue EXE bewusst im TEMP-Ordner ablegen, nicht neben der laufenden EXE,
    # damit dort auch bei einem Fehler keine ".new.exe" liegen bleibt.
    new_exe = os.path.join(tmp_dir, "DATEV-Konverter.new.exe")
    log_path = os.path.join(tmp_dir, "datev_update_log.txt")
    bat_path = os.path.join(tmp_dir, "datev_konverter_update.bat")

    _download(download_url, new_exe)

    # Als OEM/Konsolen-Codepage schreiben, damit Umlaute in Pfaden von cmd korrekt
    # gelesen werden.
    with open(bat_path, "w", encoding="oem", errors="replace") as bat_file:
        bat_file.write(_build_update_script(current_exe, new_exe, log_path))

    # Losgeloest starten, damit das Skript den Elternprozess (uns) ueberlebt.
    detached = 0x00000008  # DETACHED_PROCESS
    new_group = 0x00000200  # CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=detached | new_group,
        close_fds=True,
    )
