"""Zentrale Versionskonstante.

Diese Zahl ist die einzige Wahrheit fuer die Anzeige im Programm und fuer den
Update-Vergleich (siehe updater.py). Beim Cloud-Build (GitHub Actions) wird der
Wert automatisch aus dem Git-Tag ueberschrieben, sodass die eingebettete Version
immer dem veroeffentlichten Release entspricht.
"""

__version__ = "1.0.7"
