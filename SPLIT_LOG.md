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
- **Commit**: 103bdc646
