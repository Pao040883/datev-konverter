"""Reine Konvertierungslogik des DATEV-Konverters (ohne Tkinter/GUI).

Liest eine Bankexport-Datei (CSV/TXT, semikolongetrennt) ein und wandelt jede
Zeile mit einem Zahlungseingang in einen DATEV-Datensatz um. Diese Datei enthaelt
bewusst keine GUI-Abhaengigkeiten, damit sie unabhaengig getestet werden kann.

Wichtige Aenderung gegenueber der Erstfassung: Zeilen ohne gueltige Rechnungsnummer
werden NICHT mehr verworfen, sondern mit ``referenz=""`` erhalten, damit die
Oberflaeche sie anzeigen und der Nutzer die Nummer nachtragen kann. Verworfen
werden weiterhin nur Zeilen ohne gueltiges Datum bzw. ohne (positiven) Betrag.
"""

import calendar
import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional


DATE_COLUMN_INDEX = 5  # Spalte 6 (0-basiert)

# Muster fuer die Rechnungsnummer. Zum Finden in Freitext (Verwendungszweck) mit
# Wortgrenzen; zur Validierung einer (auch manuell eingetippten) Nummer exakt.
REFERENCE_SEARCH_PATTERN = re.compile(r"\bR\d+\b")
REFERENCE_VALID_PATTERN = re.compile(r"^R\d+$")

# Feste DATEV-Zielwerte
TARGET_ACCOUNT = "1260"
SENDER_NUMBER = "31458"


def is_valid_reference(text: str) -> bool:
    """True, wenn ``text`` eine gueltige Rechnungsnummer (R + Ziffern) ist."""
    return bool(REFERENCE_VALID_PATTERN.match(text.strip()))


@dataclass
class RowData:
    buchungsdatum: date
    zahlungspflichtiger: str
    referenz: str
    betrag_text: str
    raw: List[str]

    @property
    def is_valid(self) -> bool:
        """Ob diese Zeile exportiert werden kann (gueltige Rechnungsnummer)."""
        return is_valid_reference(self.referenz)

    @property
    def status(self) -> str:
        return "ok" if self.is_valid else "missing_ref"


def read_source_rows(source_path: Path) -> List[List[str]]:
    source_path = Path(source_path)
    encodings = ["cp1252", "utf-8-sig", "utf-8", "latin-1"]
    last_error = None
    for encoding in encodings:
        try:
            with source_path.open("r", encoding=encoding, newline="") as f:
                reader = csv.reader(f, delimiter=";", quotechar='"')
                return [row for row in reader if any(cell.strip() for cell in row)]
        except Exception as exc:  # noqa: BLE001 - Encoding-Fallback
            last_error = exc
    raise ValueError(f"Datei konnte nicht gelesen werden: {last_error}")


def parse_date(value: str) -> Optional[date]:
    value = value.strip().strip('"')
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def extract_reference(row: List[str]) -> str:
    verwendungszweck_parts = []
    for index in (11, 12, 13, 14):
        if index < len(row):
            part = row[index].strip().strip('"')
            if part:
                verwendungszweck_parts.append(part)

    verwendungszweck = " ".join(verwendungszweck_parts)
    match = REFERENCE_SEARCH_PATTERN.search(verwendungszweck)
    if match:
        return match.group(0)

    fallback_text = " ".join(cell.strip().strip('"') for cell in row if cell.strip())
    fallback_match = REFERENCE_SEARCH_PATTERN.search(fallback_text)
    return fallback_match.group(0) if fallback_match else ""


def get_payer_name(row: List[str]) -> str:
    name_parts = []
    for index in (7, 8):
        if index < len(row):
            part = row[index].strip().strip('"')
            if part:
                name_parts.append(part)
    if name_parts:
        return " ".join(name_parts)
    return "UNBEKANNT"


def extract_amount_text(row: List[str]) -> str:
    candidates = []
    for index in (6, 24):
        if index < len(row):
            value = row[index].strip().strip('"')
            if value:
                candidates.append(value)

    amount_pattern = re.compile(r"^-?\d+[\.,]\d{2}$")
    for value in candidates:
        if amount_pattern.match(value):
            return value.replace(".", ",")

    for value in row:
        cleaned = value.strip().strip('"')
        if amount_pattern.match(cleaned):
            return cleaned.replace(".", ",")

    raise ValueError("Kein Betrag in der Zeile gefunden.")


def amount_without_comma(amount_text: str) -> str:
    cleaned = amount_text.strip().replace(".", "").replace(",", "")
    if cleaned.startswith("-"):
        return "-" + cleaned[1:]
    return cleaned


def is_incoming_amount(amount_text: str) -> bool:
    normalized = amount_text.strip().replace(".", "").replace(",", ".")
    try:
        return float(normalized) > 0
    except ValueError:
        return not amount_text.strip().startswith("-")


def extract_booking_date_from_column_6(row: List[str]) -> Optional[date]:
    if len(row) <= DATE_COLUMN_INDEX:
        return None
    return parse_date(row[DATE_COLUMN_INDEX])


def parse_row(row: List[str]) -> Optional[RowData]:
    """Wandelt eine Rohzeile in ``RowData`` um oder gibt ``None`` zurueck.

    ``None`` (Zeile verworfen) nur bei fehlendem Datum oder fehlendem/negativem
    Betrag. Eine fehlende Rechnungsnummer fuehrt NICHT mehr zum Verwerfen -- die
    Zeile bleibt mit ``referenz=""`` erhalten (Status ``missing_ref``).
    """
    datum = extract_booking_date_from_column_6(row)
    if not datum:
        return None

    try:
        betrag_text = extract_amount_text(row)
    except ValueError:
        return None

    if not is_incoming_amount(betrag_text):
        return None

    return RowData(
        buchungsdatum=datum,
        zahlungspflichtiger=get_payer_name(row),
        referenz=extract_reference(row),
        betrag_text=betrag_text,
        raw=row,
    )


def parse_rows(rows: List[List[str]]) -> List[RowData]:
    """Parst alle Rohzeilen und verwirft nur die ohne Datum/Betrag."""
    parsed = [parse_row(row) for row in rows]
    return [row for row in parsed if row is not None]


def load_rows(source_path: Path) -> List[RowData]:
    """Bequemer Einstieg fuer die Oberflaeche: Datei lesen + parsen."""
    return parse_rows(read_source_rows(source_path))


def build_target_line(row_data: RowData) -> str:
    betrag_ohne_komma = amount_without_comma(row_data.betrag_text)
    buchungsdatum_feld = row_data.buchungsdatum.strftime("%d%m")

    fields = [
        betrag_ohne_komma,
        "",
        "",
        row_data.referenz,
        "",
        buchungsdatum_feld,
        TARGET_ACCOUNT,
        "",
        "",
        "",
        "",
        row_data.zahlungspflichtiger,
        "",
        "",
        "EUR",
        "",
        "",
        "1",
        "0",
    ]
    return ";".join(fields)


def build_output_filename(rows: List[RowData]) -> str:
    first_date = rows[0].buchungsdatum
    month = first_date.month
    year = first_date.year
    year_short = f"{year % 100:02d}"
    month_str = f"{month:02d}"
    last_day = calendar.monthrange(year, month)[1]
    return f"Datev_{SENDER_NUMBER}_01{month_str}{year_short}-{last_day:02d}{month_str}{year_short}.txt"


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def write_output(rows: List[RowData], output_dir: Path) -> Path:
    """Schreibt die gueltigen Zeilen als DATEV-Datei und gibt den Pfad zurueck.

    Erwartet, dass ``rows`` bereits nur exportierbare Zeilen enthaelt.
    """
    if not rows:
        raise ValueError("Keine exportierbaren Datensaetze vorhanden.")

    output_dir = Path(output_dir)
    filename = build_output_filename(rows)
    out_path = ensure_unique_path(output_dir / filename)
    lines = [build_target_line(row) for row in rows]
    out_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return out_path
