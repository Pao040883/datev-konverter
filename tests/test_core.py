"""Unit-Tests fuer die reine Konvertierungslogik (core.py).

Laufen ohne GUI/Netzwerk. Aufruf:
    python -m unittest discover -s tests
"""

import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core  # noqa: E402
import updater  # noqa: E402


def build_row(
    *,
    datum="09.03.26",
    betrag="172,00",
    payer="KATHRIN STEINMEYER",
    payer2="",
    verwendungszweck="SVWZ+Rechnung Nr.",
    referenz="R2620800128",
):
    """Erzeugt eine Rohzeile (bereits ohne Anfuehrungszeichen) mit 25 Spalten."""
    row = [""] * 25
    row[3] = datum
    row[5] = datum  # Datumsspalte (Index 5)
    row[6] = betrag
    row[7] = payer
    row[8] = payer2
    row[11] = verwendungszweck
    row[12] = referenz
    return row


class ReferenceValidationTests(unittest.TestCase):
    def test_valid_references(self):
        self.assertTrue(core.is_valid_reference("R123"))
        self.assertTrue(core.is_valid_reference("R2620800128"))
        self.assertTrue(core.is_valid_reference("  R42  "))

    def test_invalid_references(self):
        self.assertFalse(core.is_valid_reference(""))
        self.assertFalse(core.is_valid_reference("12345"))
        self.assertFalse(core.is_valid_reference("r123"))
        self.assertFalse(core.is_valid_reference("R12-3"))


class ParsingHelperTests(unittest.TestCase):
    def test_parse_date_variants(self):
        self.assertEqual(core.parse_date("09.03.26"), date(2026, 3, 9))
        self.assertEqual(core.parse_date("09.03.2026"), date(2026, 3, 9))
        self.assertIsNone(core.parse_date("keine-datum"))

    def test_extract_amount_normalises_dot(self):
        row = build_row(betrag="172.00")
        self.assertEqual(core.extract_amount_text(row), "172,00")

    def test_amount_without_comma(self):
        self.assertEqual(core.amount_without_comma("172,00"), "17200")
        self.assertEqual(core.amount_without_comma("-301,00"), "-30100")
        self.assertEqual(core.amount_without_comma("1.234,56"), "123456")

    def test_is_incoming_amount(self):
        self.assertTrue(core.is_incoming_amount("172,00"))
        self.assertFalse(core.is_incoming_amount("-301,00"))


class ParseRowTests(unittest.TestCase):
    def test_valid_row_keeps_reference(self):
        row = core.parse_row(build_row())
        self.assertIsNotNone(row)
        self.assertEqual(row.referenz, "R2620800128")
        self.assertTrue(row.is_valid)
        self.assertEqual(row.status, "ok")

    def test_missing_reference_row_is_kept_not_dropped(self):
        # Kernanforderung: Zeile ohne Rechnungsnummer bleibt erhalten.
        row = core.parse_row(
            build_row(verwendungszweck="SVWZ+Zahlung ohne Nummer", referenz="")
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.referenz, "")
        self.assertFalse(row.is_valid)
        self.assertEqual(row.status, "missing_ref")

    def test_negative_amount_is_dropped(self):
        self.assertIsNone(core.parse_row(build_row(betrag="-301,00")))

    def test_row_without_date_is_dropped(self):
        self.assertIsNone(core.parse_row(build_row(datum="")))


class TargetLineTests(unittest.TestCase):
    def test_build_target_line(self):
        row = core.RowData(
            buchungsdatum=date(2026, 3, 9),
            zahlungspflichtiger="KATHRIN STEINMEYER",
            referenz="R2620800128",
            betrag_text="172,00",
            raw=[],
        )
        # 19 Felder, exakt wie die bisherige (unveraenderte) Logik sie erzeugt.
        expected = "17200;;;R2620800128;;0903;1260;;;;;KATHRIN STEINMEYER;;;EUR;;;1;0"
        self.assertEqual(core.build_target_line(row), expected)

    def test_build_output_filename(self):
        row = core.RowData(
            buchungsdatum=date(2026, 3, 9),
            zahlungspflichtiger="X",
            referenz="R1",
            betrag_text="1,00",
            raw=[],
        )
        self.assertEqual(core.build_output_filename([row]), "Datev_31458_010326-310326.txt")


class IntegrationTests(unittest.TestCase):
    def test_load_and_write_roundtrip(self):
        content = (
            '"37020500";20228271;10;09.03.26;09.03.26;09.03.26;"172,00";'
            '"KATHRIN STEINMEYER";"";"HASPDEHHXXX";DE58;"SVWZ+Rechnung Nr.";'
            '"R2620800128";"";"";"166";"EUR"\r\n'
            '"37020500";20228271;10;10.03.26;10.03.26;10.03.26;"50,00";'
            '"MAX MUSTERMANN";"";"HASPDEHHXXX";DE58;"SVWZ+ohne Nummer";'
            '"";"";"";"166";"EUR"\r\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "quelle.txt")
            with open(src, "w", encoding="cp1252", newline="") as f:
                f.write(content)

            rows = core.load_rows(src)
            self.assertEqual(len(rows), 2)  # beide bleiben erhalten
            valid = [r for r in rows if r.is_valid]
            self.assertEqual(len(valid), 1)  # nur eine hat gueltige Nummer

            out_path = core.write_output(valid, tmp)
            self.assertTrue(os.path.exists(out_path))
            # Binaer lesen, damit die CRLF-Zeilenenden nicht uebersetzt werden.
            written = open(out_path, "rb").read()
            self.assertIn(b"R2620800128", written)
            self.assertTrue(written.endswith(b"\r\n"))


class UpdaterVersionTests(unittest.TestCase):
    def test_version_comparison(self):
        self.assertTrue(updater.is_newer("v1.1.0", "1.0.0"))
        self.assertTrue(updater.is_newer("1.0.1", "1.0.0"))
        self.assertFalse(updater.is_newer("1.0.0", "1.0.0"))
        self.assertFalse(updater.is_newer("v0.9.0", "1.0.0"))


if __name__ == "__main__":
    unittest.main()
