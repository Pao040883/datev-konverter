# DATEV-Konverter

Desktop-Programm, das Bankexport-Dateien (CSV/TXT, semikolongetrennt) in das
DATEV-Importformat umwandelt. Alle Zahlungseingänge werden in einer Tabelle
angezeigt; Einträge ohne gültige Rechnungsnummer sind rot markiert und können vor
dem Export von Hand nachgetragen werden.

Entwickelt wird auf dem Mac, eingesetzt wird das Programm überwiegend unter
Windows. Die Windows-EXE wird **in der Cloud** (GitHub Actions) gebaut — ein
Windows-Rechner zum Packen ist nicht nötig.

## Für Anwender (Windows)

1. `DATEV-Konverter.exe` starten (aus dem neuesten [GitHub-Release](https://github.com/Pao040883/datev-konverter/releases)).
2. **Datei öffnen …** → Bankexport auswählen.
3. Rot markierte Zeilen prüfen: **Doppelklick auf die Spalte „Rechnungsnummer"**,
   korrekte Nummer eintragen, Enter.
4. **Exportieren …** → Zielordner wählen. Noch offene Zeilen werden mit Warnung
   ausgelassen.

**Updates** installieren sich selbst: Beim Start prüft das Programm auf eine neuere
Version und fragt nach, bevor es aktualisiert.

## Entwicklung (Mac)

```bash
# Programm lokal starten (Tkinter-Oberfläche)
.venv/bin/python datev_konverter.py

# Tests
.venv/bin/python -m unittest discover -s tests

# Mac-App bauen (optional, für lokale Tests)
./build_mac.command        # -> dist/DATEV-Konverter.app
```

## Release veröffentlichen (Windows-EXE)

Der Cloud-Build wird durch einen Versions-Tag ausgelöst:

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions ([.github/workflows/build-windows.yml](.github/workflows/build-windows.yml))
baut daraufhin die EXE auf einem Windows-Runner, schreibt die Version aus dem Tag in
`version.py` und hängt `DATEV-Konverter.exe` an ein neues Release. Installierte
Programme aktualisieren sich beim nächsten Start automatisch auf diese Version.

## Aufbau

| Datei | Zweck |
|---|---|
| [core.py](core.py) | Reine Konvertierungslogik (kein GUI), unabhängig testbar |
| [datev_konverter.py](datev_konverter.py) | Tkinter-Oberfläche + Programmstart |
| [updater.py](updater.py) | Update-Prüfung + Selbst-Austausch über GitHub Releases |
| [version.py](version.py) | Zentrale Versionskonstante |
| [tests/](tests/) | Unit-Tests der Logik |

## Hinweis zu echten Bankdaten

Die Beispiel-/Echtdateien (`DATEV.TXT`, `Datev_*.txt`) enthalten echte IBANs und
Namen und sind per [.gitignore](.gitignore) vom öffentlichen Repository
ausgeschlossen. Nicht ins Repo aufnehmen.
