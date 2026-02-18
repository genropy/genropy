# gnr.core Module Refactoring Log

This file tracks the progress of splitting/reviewing modules in `gnrpy/gnr/core/`.

---

## gnrbaseservice.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrbaseservice`
- **PR**: #510
- **Decision**: review only — 3-line re-export module, already minimal
- **Sub-modules created**: none
- **Lines**: 3 → 11 (added docstring)
- **Public names re-exported**: 1 (GnrBaseService)
- **REVIEW markers added**: 0
- **Dead symbols found**: 0
- **Tests**: N/A (no tests for this module)
- **Commit**: e530b28b6

---

## gnrenv.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrenv`
- **PR**: #511
- **Decision**: review only — 22-line constant definition module, already minimal
- **Sub-modules created**: none
- **Lines**: 22 → 50 (added docstring, type hints)
- **Public names exported**: 4 (GNRHOME, GNRINSTANCES, GNRPACKAGES, GNRSITES)
- **REVIEW markers added**: 1 (COMPAT)
- **Dead symbols found**: 4 (all public constants appear unused)
- **Tests**: pass (empty test file, only import check)
- **Commit**: 1751ff8c0

---

## gnrgit.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrgit`
- **PR**: #512
- **Decision**: review only — 42-line single class module, already minimal
- **Sub-modules created**: none
- **Lines**: 42 → 85 (added docstrings, type hints)
- **Public names exported**: 1 (GnrGit)
- **REVIEW markers added**: 2 (BUG, SMELL)
- **Dead symbols found**: 3 (class and all methods appear unused)
- **Tests**: pass (1 test, import only)
- **Commit**: a659d5f92

---

## gnrredbaron.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrredbaron`
- **PR**: #513
- **Decision**: review only — 64-line single class module with stub methods
- **Sub-modules created**: none
- **Lines**: 64 → 130 (added docstrings, type hints)
- **Public names exported**: 1 (GnrRedBaron)
- **REVIEW markers added**: 5 (SMELL, DEAD)
- **Dead symbols found**: 6 (class entirely unused, 3 stub methods)
- **Tests**: pass (1 test, import only)
- **Commit**: ce68070b0

---

## gnrnumber.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrnumber`
- **PR**: #514
- **Decision**: review only — 68-line utility module, tightly cohesive
- **Sub-modules created**: none
- **Lines**: 68 → 165 (added docstrings, type hints)
- **Public names exported**: 4 (decimalRound, floatToDecimal, calculateMultiPerc, partitionTotals)
- **REVIEW markers added**: 0
- **Dead symbols found**: 0
- **Tests**: pass (4 tests)
- **Commit**: 5e8118199

---

## gnrcaldav.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrcaldav`
- **PR**: #515
- **Decision**: review only — 79-line DEPRECATED module, cannot be imported
- **Sub-modules created**: none
- **Lines**: 79 → 220 (added docstrings, type hints, preserved unreachable code)
- **Public names exported**: 2 (CalDavConnection, dt) — but unreachable
- **REVIEW markers added**: 3 (DEAD, SECURITY x2)
- **Dead symbols found**: 5 (entire module is deprecated)
- **Tests**: N/A (module cannot be imported)
- **Commit**: e471aee27

---

## gnranalyzingbag.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnranalyzingbag`
- **PR**: #516
- **Decision**: review only — 87-line single class module, cohesive
- **Sub-modules created**: none
- **Lines**: 87 → 145 (added docstrings, type hints)
- **Public names exported**: 1 (AnalyzingBag)
- **REVIEW markers added**: 0
- **Dead symbols found**: 0
- **Tests**: pass (1 test, import only)
- **Commit**: e0531f238

---

## gnrdatetime.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrdatetime`
- **PR**: #517
- **Decision**: review only — 91-line well-designed module
- **Sub-modules created**: none
- **Lines**: 91 → 165 (added type hints, enhanced docstrings)
- **Public names exported**: 12 (TZDateTime, datetime, date, time, timedelta, timezone, tzinfo, MINYEAR, MAXYEAR, now, utcnow)
- **REVIEW markers added**: 0
- **Dead symbols found**: 0
- **Tests**: pass (3 tests)
- **Commit**: df935e289

---

## gnrcrypto.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrcrypto`
- **PR**: #518
- **Decision**: review only — 98-line authentication token module, cohesive
- **Sub-modules created**: none
- **Lines**: 98 → 220 (added docstrings, type hints)
- **Public names exported**: 3 (AuthTokenError, AuthTokenExpired, AuthTokenGenerator)
- **REVIEW markers added**: 0
- **Dead symbols found**: 0
- **Tests**: pass (4 tests)
- **Commit**: 289dbcb35

---

## gnrrlab.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrrlab`
- **PR**: #519
- **Decision**: review only — 109-line ReportLab PDF generation base class
- **Sub-modules created**: none
- **Lines**: 109 → 240 (added docstrings, type hints)
- **Public names exported**: 1 (RlabResource)
- **REVIEW markers added**: 1 (DEAD)
- **Dead symbols found**: 9 (class and all methods appear unused in codebase)
- **Tests**: pass (1 test, import only)
- **Commit**: 1d73675b9

---

## gnrsys.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrsys`
- **PR**: #520
- **Decision**: review only — 113-line OS/filesystem utility module
- **Sub-modules created**: none
- **Lines**: 113 → 180 (added docstrings, type hints)
- **Public names exported**: 5 (progress, mkdir, expandpath, listdirs, resolvegenropypath)
- **REVIEW markers added**: 1 (BUG)
- **Dead symbols found**: 1 (listdirs is broken and not used except in tests)
- **Tests**: pass (5 tests)
- **Commit**: ca843a921

---

## loggingimport.py — REVIEW ONLY

- **Branch**: `pkg_refactor/loggingimport`
- **PR**: #521
- **Decision**: review only — 123-line DEPRECATED module (uses `imp`)
- **Sub-modules created**: none
- **Lines**: 123 → 245 (added docstrings, type hints)
- **Public names exported**: 9 (functions and saved hooks)
- **REVIEW markers added**: 3 (DEAD, COMPAT, SMELL)
- **Dead symbols found**: 9 (entire module is unused)
- **Tests**: N/A (no tests, module has side effects)
- **Commit**: edf32cad9

---

## gnrvobject.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrvobject`
- **PR**: #522
- **Decision**: review only — 134-line vCard handling module
- **Sub-modules created**: none
- **Lines**: 134 → 220 (added docstrings, type hints)
- **Public names exported**: 2 (VCard, VALID_VCARD_TAGS)
- **REVIEW markers added**: 1 (SMELL)
- **Dead symbols found**: 1 (doprettyprint unused)
- **Tests**: pass (1 test)
- **Commit**: 9ab115467

---

## gnrssh.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrssh`
- **PR**: #523
- **Decision**: review only — 143-line SSH tunneling module
- **Sub-modules created**: none
- **Lines**: 143 → 360 (added docstrings, type hints)
- **Public names exported**: 5 (ForwardServer, Handler, IncompleteConfigurationException, SshTunnel, normalized_sshtunnel_parameters)
- **REVIEW markers added**: 2 (SMELL)
- **Dead symbols found**: 0
- **Tests**: pass (1 test)
- **Commit**: 7e9fb506a

---

## gnrprinthandler.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrprinthandler`
- **PR**: #524
- **Decision**: review only — 186-line print handling module
- **Sub-modules created**: none
- **Lines**: 186 → 400 (added docstrings, type hints)
- **Public names exported**: 3 (PrintHandlerError, PrinterConnection, PrintHandler)
- **REVIEW markers added**: 1 (SMELL - duplicated dicts with NetworkPrintService)
- **Dead symbols found**: 0
- **Tests**: pass (1 test)
- **Commit**: adb428e4b
