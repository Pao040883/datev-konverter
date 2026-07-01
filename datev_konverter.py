"""DATEV-Konverter - grafische Oberflaeche.

Startet ein Fenster, in dem eine Bankexport-Datei geladen und als Tabelle
angezeigt wird. Alle Zahlungseingaenge sind sichtbar; Zeilen ohne gueltige
Rechnungsnummer sind rot markiert und koennen per Doppelklick nachgetragen
werden. Der Export schreibt nur Zeilen mit gueltiger Rechnungsnummer und warnt
vor dem Weglassen offener Eintraege.

Die eigentliche Konvertierungslogik liegt in core.py, der Update-Mechanismus in
updater.py -- diese Datei ist reine Oberflaeche plus Programmstart.
"""

import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"Tkinter konnte nicht geladen werden: {exc}")

import core
import updater
from version import __version__


APP_TITLE = "DATEV-Konverter"

# (interne ID, Ueberschrift, Breite, Ausrichtung)
COLUMNS = [
    ("datum", "Datum", 90, "center"),
    ("zahler", "Zahlungspflichtiger", 260, "w"),
    ("betrag", "Betrag (EUR)", 110, "e"),
    ("referenz", "Rechnungsnummer", 160, "center"),
    ("status", "Status", 180, "w"),
]
COLUMN_IDS = [col[0] for col in COLUMNS]

COLOR_INVALID = "#f8d7da"  # helles Rot (Zahlungseingang ohne gueltige Nummer)
COLOR_VALID = "#ffffff"
COLOR_OUTGOING = "#e2e3e5"  # grau (Auszahlung, wird nicht exportiert)
COLOR_OUTGOING_TEXT = "#6c757d"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_TITLE}  v{__version__}")
        self.geometry("860x560")
        self.minsize(680, 420)

        self.rows: list[core.RowData] = []
        self.rows_by_item: dict[str, core.RowData] = {}
        self.current_file: Path | None = None
        self._skipped_count = 0
        self.summary_var = tk.StringVar(value="Keine Datei geladen.")
        self.file_var = tk.StringVar(value="Keine Datei ausgewaehlt")

        self._build_menu()
        self._build_toolbar()
        self._build_table()
        self._build_footer()

        # Update-Pruefung erst kurz nach dem Anzeigen des Fensters.
        self.after(800, lambda: self.check_updates(manual=False))

    # ---------------------------------------------------------------- Aufbau
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Nach Updates suchen", command=lambda: self.check_updates(manual=True))
        help_menu.add_separator()
        help_menu.add_command(label="Ueber", command=self._show_about)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        self.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")

        ttk.Button(bar, text="Datei oeffnen ...", command=self.open_file).pack(side="left")
        ttk.Label(bar, textvariable=self.file_var, foreground="#555").pack(side="left", padx=12)
        ttk.Label(bar, text=f"v{__version__}", foreground="#999").pack(side="right")

    def _build_table(self) -> None:
        container = ttk.Frame(self, padding=(10, 0))
        container.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            container,
            columns=COLUMN_IDS,
            show="headings",
            selectmode="browse",
        )
        for col_id, heading, width, anchor in COLUMNS:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor, stretch=(col_id == "zahler"))

        self.tree.tag_configure("invalid", background=COLOR_INVALID)
        self.tree.tag_configure("valid", background=COLOR_VALID)
        self.tree.tag_configure("outgoing", background=COLOR_OUTGOING, foreground=COLOR_OUTGOING_TEXT)

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(10, 8))
        footer.pack(fill="x")

        ttk.Label(footer, textvariable=self.summary_var).pack(side="left")
        self.export_button = ttk.Button(
            footer, text="Exportieren ...", command=self.export, state="disabled"
        )
        self.export_button.pack(side="right")

        hint = ttk.Label(
            self,
            text="Rot = Rechnungsnummer prüfen (Doppelklick zum Nachtragen)   ·   "
            "Grau = Auszahlung, wird nicht exportiert",
            foreground="#777",
            padding=(10, 0, 10, 8),
        )
        hint.pack(fill="x")

    # ------------------------------------------------------------- Aktionen
    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="DATEV-Quelldatei auswaehlen",
            filetypes=[("Textdateien", "*.txt *.TXT *.csv *.CSV"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return

        try:
            raw_rows = core.read_source_rows(Path(path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Datei konnte nicht gelesen werden:\n{exc}")
            return

        rows = core.parse_rows(raw_rows)
        # Zeilen ohne Datum/Betrag (z. B. Kopfzeilen) werden uebersprungen -- Anzahl merken.
        self._skipped_count = len(raw_rows) - len(rows)
        self.current_file = Path(path)
        self.rows = rows
        self.file_var.set(self.current_file.name)
        self._populate_table()

        if not rows:
            messagebox.showinfo(
                APP_TITLE,
                "In dieser Datei wurden keine Buchungszeilen gefunden.",
            )

    def _populate_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.rows_by_item.clear()

        for row in self.rows:
            item = self.tree.insert(
                "",
                "end",
                values=(
                    row.buchungsdatum.strftime("%d.%m.%Y"),
                    row.zahlungspflichtiger,
                    row.betrag_text,
                    row.referenz,
                    "",
                ),
            )
            self.rows_by_item[item] = row
            self._apply_status(item, row)

        self._refresh_summary()

    def _apply_status(self, item: str, row: core.RowData) -> None:
        if not row.is_incoming:
            self.tree.item(item, tags=("outgoing",))
            self.tree.set(item, "status", "Auszahlung – wird nicht exportiert")
        elif row.is_valid:
            self.tree.item(item, tags=("valid",))
            self.tree.set(item, "status", "OK")
        else:
            self.tree.item(item, tags=("invalid",))
            self.tree.set(item, "status", "Rechnungsnummer prüfen")

    def _refresh_summary(self) -> None:
        if not self.rows:
            self.summary_var.set("Keine Datei geladen.")
            self.export_button.config(state="disabled")
            return

        incoming = [row for row in self.rows if row.is_incoming]
        missing = [row for row in incoming if not row.is_valid]
        outgoing = len(self.rows) - len(incoming)

        parts = [
            f"{len(incoming)} Zahlungseingänge",
            f"{len(missing)} ohne gültige Rechnungsnummer",
        ]
        if outgoing:
            parts.append(f"{outgoing} Auszahlung(en) – nicht exportiert")
        if self._skipped_count:
            parts.append(f"{self._skipped_count} Zeile(n) ohne Zahlungssatz übersprungen")
        self.summary_var.set("   ·   ".join(parts))

        self.export_button.config(state="normal" if incoming else "disabled")

    # ------------------------------------------------------ Inline-Bearbeitung
    def _on_double_click(self, event: "tk.Event") -> None:
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        column = self.tree.identify_column(event.x)  # z. B. "#4"
        item = self.tree.identify_row(event.y)
        if not item or not column:
            return

        try:
            col_name = COLUMN_IDS[int(column[1:]) - 1]
        except (ValueError, IndexError):
            return
        if col_name != "referenz":
            return

        row = self.rows_by_item.get(item)
        if row is None or not row.is_incoming:
            return  # Auszahlungen sind nicht editierbar

        self._begin_edit(item, column)

    def _begin_edit(self, item: str, column: str) -> None:
        bbox = self.tree.bbox(item, column)
        if not bbox:
            return
        x, y, width, height = bbox

        editor = tk.Entry(self.tree)
        editor.insert(0, self.tree.set(item, "referenz"))
        editor.select_range(0, tk.END)
        editor.focus_set()
        editor.place(x=x, y=y, width=width, height=height)

        editor.bind("<Return>", lambda e: self._commit_edit(item, editor))
        editor.bind("<KP_Enter>", lambda e: self._commit_edit(item, editor))
        editor.bind("<Escape>", lambda e: editor.destroy())
        editor.bind("<FocusOut>", lambda e: self._commit_edit(item, editor))

    def _commit_edit(self, item: str, editor: "tk.Entry") -> None:
        if not editor.winfo_exists():
            return
        new_value = editor.get().strip()
        editor.destroy()

        row = self.rows_by_item.get(item)
        if row is None:
            return
        row.referenz = new_value
        self.tree.set(item, "referenz", new_value)
        self._apply_status(item, row)
        self._refresh_summary()

    # -------------------------------------------------------------- Export
    def export(self) -> None:
        if not self.rows:
            messagebox.showwarning(APP_TITLE, "Es ist keine Datei geladen.")
            return

        valid_rows = [row for row in self.rows if row.is_valid]
        missing_ref = [row for row in self.rows if row.is_incoming and not row.is_valid]

        if not valid_rows:
            messagebox.showerror(
                APP_TITLE,
                "Kein Zahlungseingang hat eine gueltige Rechnungsnummer. Bitte zuerst nachtragen.",
            )
            return

        if missing_ref:
            proceed = messagebox.askyesno(
                APP_TITLE,
                f"{len(missing_ref)} Zahlungseingänge ohne gültige Rechnungsnummer werden "
                f"NICHT exportiert.\n\nMöchten Sie fortfahren?",
            )
            if not proceed:
                return

        output_dir = filedialog.askdirectory(title="Zielordner fuer konvertierte Datei auswaehlen")
        if not output_dir:
            return

        try:
            out_path = core.write_output(valid_rows, Path(output_dir))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Export fehlgeschlagen:\n{exc}")
            return

        messagebox.showinfo(
            APP_TITLE,
            f"Konvertierung abgeschlossen.\n\n{len(valid_rows)} Eintraege exportiert.\n"
            f"Erstellte Datei:\n{out_path}",
        )

    # -------------------------------------------------------------- Updates
    def check_updates(self, manual: bool = False) -> None:
        info = updater.check_for_update()
        if not info:
            if manual:
                messagebox.showinfo(APP_TITLE, "Sie verwenden bereits die neueste Version.")
            return

        proceed = messagebox.askyesno(
            APP_TITLE,
            f"Version {info['version']} ist verfuegbar (installiert: {__version__}).\n\n"
            f"Jetzt aktualisieren?",
        )
        if not proceed:
            return

        if not updater.is_frozen():
            messagebox.showinfo(
                APP_TITLE,
                "Das automatische Update funktioniert nur in der gebauten Windows-EXE.\n"
                "Bitte die neue Version aus GitHub verwenden.",
            )
            return

        try:
            updater.apply_update(info["download_url"])
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Update fehlgeschlagen:\n{exc}")
            return

        messagebox.showinfo(APP_TITLE, "Update wird installiert. Das Programm startet neu.")
        self.destroy()
        sys.exit(0)

    def _show_about(self) -> None:
        messagebox.showinfo(
            APP_TITLE,
            f"{APP_TITLE}\nVersion {__version__}\n\n"
            "Wandelt Bankexport-Dateien in das DATEV-Importformat um.",
        )


def main() -> int:
    try:
        app = App()
        app.mainloop()
        return 0
    except Exception as exc:  # noqa: BLE001
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_TITLE, str(exc))
        except Exception:  # noqa: BLE001
            print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
