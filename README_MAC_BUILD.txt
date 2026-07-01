DATEV-Konverter als startbare Mac-App bauen

Voraussetzung:
- macOS
- Python 3.11+ von Homebrew oder python.org

Wichtig:
- Nicht mit /usr/bin/python3 bauen. Das ist auf macOS oft System-Python 3.9 mit altem Tk 8.5.
- Diese Kombination kann in der fertigen App beim Start abstuerzen.

Bauen:
1. build_mac.command einmal ausfuehrbar machen:
   chmod +x build_mac.command
2. build_mac.command starten (Doppelklick oder Terminal)
3. Ergebnis liegt hier:
   dist/DATEV-Konverter.app

Nutzung:
1. DATEV-Konverter.app starten
2. Quelldatei auswaehlen
3. Zielordner auswaehlen
4. Ausgabedatei wird erzeugt

Wenn schon einmal mit System-Python gebaut wurde:
1. Alte Artefakte loeschen:
   rm -rf .venv build dist DATEV-Konverter.spec
2. Modernes Python installieren (Beispiel):
   brew install python@3.12
3. Neu bauen:
   ./build_mac.command

Falls macOS die App blockiert:
- Rechtsklick auf die App -> Oeffnen
- Danach erneut normal startbar
