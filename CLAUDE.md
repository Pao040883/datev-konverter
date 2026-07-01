# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python desktop tool that converts German bank-export CSV/TXT files into a
DATEV import format. The UI is Tkinter, all user-facing strings are German, and
there are no third-party runtime dependencies (stdlib + Tkinter only). PyInstaller
is used only to build binaries.

Development happens on **macOS**, but the program runs mostly on **Windows**. The
Windows `.exe` is built in the cloud via GitHub Actions — no Windows machine is
needed to package it. Installed copies self-update from GitHub Releases.

## Architecture

The code is split so the conversion logic can be tested without a GUI:

- [core.py](core.py) — **pure conversion logic, no Tkinter.** Reading, parsing,
  the `RowData` model, target-line building, filename derivation. This is the
  domain layer and the main thing tests exercise.
- [datev_konverter.py](datev_konverter.py) — Tkinter main window (review table +
  inline editing + export) and `main()`. This is the **PyInstaller entry point**;
  imported siblings (`core`, `updater`, `version`) are bundled automatically.
- [updater.py](updater.py) — checks the latest GitHub Release, compares versions,
  and on Windows performs a self-swap of the running `.exe` via a detached `.bat`
  (you cannot overwrite a running exe on Windows, so a helper waits for the process
  to exit, replaces the file, and relaunches). Self-swap only runs when frozen
  (`sys.frozen`); in dev it just reports availability.
- [version.py](version.py) — single source of truth for the version. The CI build
  overwrites `__version__` from the git tag so the embedded version == the release.

## Commands

```bash
.venv/bin/python datev_konverter.py                  # run the GUI locally (macOS)
.venv/bin/python -m unittest discover -s tests       # run the unit tests
.venv/bin/python -m unittest tests.test_core.ParseRowTests   # a single test class
./build_mac.command                                  # -> dist/DATEV-Konverter.app
```

Release a Windows build (this is the whole distribution flow now):

```bash
git tag v1.1.0 && git push origin v1.1.0
```

That triggers [.github/workflows/build-windows.yml](.github/workflows/build-windows.yml):
a `windows-latest` runner writes the tag into `version.py`, runs PyInstaller
(`--onefile --windowed`), and attaches `DATEV-Konverter.exe` to a new GitHub Release.
`build_windows.bat` / `build_windows.ps1` still exist as a local fallback but are no
longer the primary path.

The macOS build gotcha still applies (see [README_MAC_BUILD.txt](README_MAC_BUILD.txt)):
`build_mac.command` deliberately refuses system Python 3.9 / Tk 8.5 (it crashes the
packaged app) and prefers Homebrew `python3.12`/`3.11`. Override with `PYTHON_BIN`.

## Conversion logic (the core domain knowledge)

Input is a semicolon-delimited bank export with hard-coded column positions — check
the sample files before changing any index. All of this lives in [core.py](core.py):

- **Encoding**: input tried as `cp1252` → `utf-8-sig` → `utf-8` → `latin-1`.
  Output is UTF-8 with `\r\n` line endings.
- **Date** from column index 5 (`DATE_COLUMN_INDEX`); rows without a parseable date
  are dropped.
- **Amount** from index 6 or 24, matched `^-?\d+[.,]\d{2}$`; **only positive
  (incoming) amounts are kept.**
- **Reference** = invoice number matching `\bR\d+\b`, searched in the
  Verwendungszweck fields (indices 11–14) then the whole row.
- **Payer** joins indices 7 and 8, default `"UNBEKANNT"`.

**Key behavior change vs. the original single-file version:** rows *without* a valid
invoice number are **no longer dropped**. `parse_row` keeps them with `referenz=""`
so the UI can show them (red) and the user can type the correct number. A row is
exportable when `RowData.is_valid` (reference matches `^R\d+$`, see
`is_valid_reference`). Export writes only valid rows and warns about the rest. Rows
are still dropped only for a missing date or a missing/negative amount.

Each exported row becomes a fixed 19-field DATEV line (`build_target_line`): amount
without punctuation, reference, `DDMM` date, constant account `1260`, payer, `EUR`,
`1`, `0`. Output filename is derived from the first row's month/year as
`Datev_31458_01MMYY-<lastday>MMYY.txt` (`SENDER_NUMBER = "31458"`), de-duplicated
with `_2`, `_3`, … The mapping constants worth knowing: `DATE_COLUMN_INDEX`,
`TARGET_ACCOUNT`, `SENDER_NUMBER`, `REFERENCE_SEARCH_PATTERN`,
`REFERENCE_VALID_PATTERN`.

> Note: the stale sample `Datev_*.txt` files predate the current logic (they include
> a negative row and a 20-field layout). Trust `build_target_line` / the tests, not
> those files, for the current output format.

## Data safety

`DATEV.TXT` and `Datev_*.txt` contain **real IBANs, names, and amounts** and are
excluded via [.gitignore](.gitignore). The repo is public — never commit real bank
data. Keep the samples locally only.
