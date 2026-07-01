DATEV-Konverter als EXE bauen (Windows)

Voraussetzung:
- Windows 10/11
- Python 3 installiert (mit Python Launcher 'py')

Schnellstart (einfach):
1. Projektordner auf Windows oeffnen.
2. start_build_windows.vbs doppelklicken.
3. Warten bis "Fertig" erscheint.
4. Ergebnis: dist/DATEV-Konverter.exe

Bei Fehlern:
- Das Fenster bleibt offen und zeigt die Meldung direkt an.
- Wenn nichts passiert: build_windows.bat direkt in einer offenen CMD starten.

Hinweis:
- Der VBS-Starter startet CMD mit /d, dadurch werden problematische AutoRun-Eintraege ignoriert.

Nutzung der EXE:
1. DATEV-Konverter.exe starten.
2. Quelldatei auswaehlen.
3. Zielordner auswaehlen.
4. Konvertierte Datei wird gespeichert.

Hinweise:
- Falls eine Sicherheitswarnung erscheint, "Weitere Informationen" -> "Trotzdem ausfuehren".
- Fuer professionelle Verteilung sollte die EXE digital signiert werden.
