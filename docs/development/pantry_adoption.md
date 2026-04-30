# Proposal: adopt mypantry for optional dependency management

**Issue**: #756
**Branch**: `feature/pantry-optional-deps`
**Date**: 2026-03-31

## Problem

GenroPy has ~20 conditional imports scattered across the codebase, each using
ad-hoc patterns to handle optional dependencies. At least 7 different patterns
coexist, with no consistency in error reporting or discoverability.

Several of these guard packages that are **already mandatory** in pyproject.toml
(simpleeval, paramiko, docutils, openpyxl, psutil, weasyprint, PyPDF2, pymupdf)
— their try/except blocks are historical residues that serve no purpose today.

## Current patterns in genropy (from Sourcerer cross-repo search)

### Truly optional dependencies (not in pyproject.toml dependencies)

| # | File | Package | Pattern | Purpose |
|---|------|---------|---------|---------|
| 1 | `common/gnrcomponents/maintenance.py:20` | `sh` | `SH_ENABLED = True/pass` | Shell commands |
| 2 | `common/gnrcomponents/source_viewer/source_viewer.py:11` | `pygments` | `print('Missing...')` | Syntax highlighting |
| 3 | `common/services/networkprint/pycups.py:6` | `cups` | `HAS_CUPS = True/False` | Network printing |
| 4 | `gnr/core/gnrprinthandler.py:4` | `cups` | `HAS_CUPS = True/False` | Duplicate of #3 |
| 5 | `gnr/core/gnrlist.py:615` | `cchardet`/`chardet` | cascading try/except | Encoding detection |
| 6 | `gnr/sql/adapters/gnrpostgres.py:27` | `psycopg2`/cffi/ct | 3-level cascade | PostgreSQL adapter |
| 7 | `gnr/web/cli/gnrsyncstorage.py:11` | `progressbar` | `PROGRESS = None` | CLI progress bar |
| 8 | `gnr/web/gnrwsgisite_proxy/gnrapidispatcher.py:13` | `genro_routes` | `HAS_GENRO_ROUTES = True/False` | API routing |
| 9 | `gnr/web/serverwsgi.py:300` | `debugpy` | `self.debugpy = False` | Remote debugging |
| 10 | `resources/preference.py:22` | `pyotp` | `pyotp = None` | 2FA/TOTP |

### Already mandatory but still guarded (dead try/except)

| # | File | Package | In pyproject.toml |
|---|------|---------|-------------------|
| 11 | `gnr/core/gnrbaghtml.py:22` | `simpleeval` | yes |
| 12 | `gnr/core/gnrlist.py:910` | `openpyxl` | yes |
| 13 | `gnr/core/gnrssh.py:9` | `paramiko` | yes |
| 14 | `gnr/lib/services/htmltopdf.py:24` | `weasyprint` | yes |
| 15 | `gnr/sql/gnrsqldata/selection.py:1510` | `openpyxl` | yes |
| 16 | `resources/services/rst2html/.../service.py:12` | `docutils` | yes |
| 17 | `resources/services/storage/sftp.py:14` | `paramiko` | yes |
| 18 | `resources/services/sysinfo/psutil/psutil.py:15` | `psutil` | yes |
| 19 | `common/services/pdf/pypdf.py:12` | `PyPDF2` | yes |
| 20 | `common/services/pdf/pypdf.py:19` | `fitz` (PyMuPDF) | yes |

### Version/module compat (not candidates for pantry)

| File | What | Note |
|------|------|------|
| `gnr/web/gnrwsgisite.py:48` | werkzeug `EnvironBuilder` location | Version compat |
| `gnr/web/serverwsgi.py:15` | werkzeug debug tbtools | Version compat |
| `gnr/web/daemon/siteregister.py:46` | `pickle` | Py2/Py3 compat (obsolete) |
| `gnr/dev/cli/gnrtests.py:9` | `pytest` | Re-raise with message |

## Observed pattern inconsistencies

| Pattern | Count | Problem |
|---------|-------|---------|
| `HAS_X = True/False` | 5 | No error message, silent degradation |
| `module = False/None` | 5 | Breaks type hints, silent failure at call site |
| `print('Missing...')` | 2 | No structured logging, lost in output |
| Cascading try/except | 2 | Hard to read, error swallowing |
| Fallback function | 2 | Hidden behavior change |
| `pass` (silent) | 2 | No way to diagnose missing feature |
| Re-raise with message | 1 | Good but ad-hoc |

## What pantry provides

mypantry reads `[project.optional-dependencies]` from pyproject.toml and probes
which packages are installed at import time. Single API for all cases:

```python
import pantry

# Boolean check (replaces HAS_X pattern)
if pantry.has('cups'):
    import cups

# Import-or-raise with clear message (replaces try/except/print)
orjson = pantry['orjson']

# Decorator guard (replaces manual checks in methods)
@pantry('debugpy')
def start_debugger():
    import debugpy
    debugpy.listen(5678)

# Diagnostic report (replaces guesswork)
pantry.report()
# ┌─────────────┬───────────┬─────────┐
# │ Package     │ Installed │ Version │
# ├─────────────┼───────────┼─────────┤
# │ cups        │ no        │ —       │
# │ debugpy     │ yes       │ 1.8.7   │
# │ psycopg2    │ yes       │ 2.9.9   │
# └─────────────┴───────────┴─────────┘
```

## Current approach vs pantry — side by side

### Check if available

Current (7 different patterns):

```python
# gnrprinthandler.py
try:
    import cups
    HAS_CUPS = True
except ImportError:
    HAS_CUPS = False

# gnrssh.py
try:
    import paramiko
except ImportError:
    paramiko = False      # breaks type hints, bool instead of module

# source_viewer.py
try:
    from pygments import highlight
except ImportError:
    print('Missing pygments. Please do pip install pygments')  # lost in stdout

# gnrsyncstorage.py
try:
    import progressbar
    PROGRESS = progressbar.ProgressBar()
except ImportError:
    PROGRESS = None       # caller must check None every time

# psutil.py
try:
    import psutil as ps
except ImportError:
    pass                  # NameError at call site, no hint
```

With pantry (one pattern):

```python
import pantry

if pantry.has('cups'):
    import cups           # type-safe, static analyzers see the import

if pantry.has('pygments'):
    from pygments import highlight
```

### Guard a function

Current:

```python
# serverwsgi.py — inside a method, runtime import
try:
    import debugpy
    self.debugpy = True
    self.debugpy_port = self.options.debugpy_port or 5678
except ImportError:
    logger.error(f"Failed to import debugpy: {sys.exc_info()[1]}.")
    self.debugpy = False
    self.debugpy_port = None
```

With pantry:

```python
@pantry('debugpy')
def configure_debugpy(self):
    import debugpy
    self.debugpy_port = self.options.debugpy_port or 5678
```

### Cascading alternatives

Current (gnrpostgres.py — 13 lines):

```python
try:
    import psycopg2
except ImportError:
    try:
        from psycopg2cffi import compat
        compat.register()
    except ImportError:
        try:
            from psycopg2ct import compat
            compat.register()
        except ImportError:
            pass
    import psycopg2
```

With pantry:

```python
for driver in ('psycopg2', 'psycopg2cffi', 'psycopg2ct'):
    if pantry.has(driver):
        psycopg2 = pantry[driver]
        break
```

### Diagnostics

Current: no way to see at a glance which optional features are available
in a running installation. Each module defines its own flag, there is no
central registry.

With pantry:

```python
pantry.report()
```

Prints a table of all optional dependencies declared in pyproject.toml,
whether each is installed, and its version. Useful for support, debugging,
and deployment verification.

### Summary

| Aspect | Current (try/except) | pantry |
|--------|---------------------|--------|
| Consistency | 7 different patterns | 1 API |
| Discoverability | grep for `HAS_`, `= False`, `= None`... | `pantry.report()` |
| Error messages | varies: print, log, pass, NameError | uniform, configurable |
| Type safety | `module = False` breaks type hints | `if pantry.has(): import` preserves types |
| Centralized registry | no | pyproject.toml `[optional-dependencies]` |
| Dead guards | 10 try/except for mandatory packages | not needed — mandatory = direct import |
| Lines of code | ~80 lines of boilerplate across 20 files | ~20 lines total |

## Proposed approach

### Phase 1 (this branch)
- Add `mypantry` to genropy dependencies
- No code changes — just make it available

### Phase 2 (separate PRs)
- Remove dead try/except for already-mandatory packages (#11–#20)
- Migrate truly optional imports (#1–#10) to pantry API
- Register optional dependency groups in pyproject.toml

### Phase 3 (downstream)
- Evaluate adoption in genro-asgi, genro-office, genro-print, genro-storage
  (where the same patterns were found by Sourcerer cross-repo search)

## Open questions (from PR #748 review)

During the encrypted columns review, concerns were raised about pantry adoption.
Here they are with context against the current state of the codebase.

### 1. "Standard library can handle this, lazy imports incoming in mainstream Python"

PEP 690 (global lazy imports with `-L` flag) was **rejected** by the Steering
Council in December 2022 — it would have created two incompatible Pythons.

PEP 810 (explicit `lazy import` keyword) was proposed in October 2025 and
targets **Python 3.15** (October 2026). It is opt-in and explicit.

However: GenroPy supports Python 3.11+. Even if PEP 810 ships in 3.15, it
will be years before 3.15 is the minimum supported version. And `lazy import`
solves **deferred loading**, not the problem of **knowing whether a package is
available** — it provides no equivalent to `has()`, `report()`, or uniform
error messages.

Today the "standard library approach" in GenroPy is 20 ad-hoc try/except
blocks with 7 inconsistent patterns. Pantry replaces them with one.

### 2. "With pantry all imports become runtime"

The current try/except blocks have the same problem: a missing package is
not detected at import time — it's caught and silenced. Some patterns even
use `pass`, hiding the error entirely.

With pantry, the recommended pattern for truly optional imports is
`if pantry.has('pkg'): import pkg` — which is module-level and visible.
Mandatory dependencies keep direct `import` statements, no pantry involved.

### 3. "Static code analyzers will be limited"

The `@pantry('pkg')` decorator is opaque to type checkers. But the
`if pantry.has('pkg'): import pkg` pattern preserves full static analysis —
the type checker sees a regular import under a branch condition.

The current patterns (`paramiko = False`, `pyotp = None`, `HAS_CUPS`) are
equally or more opaque to static analyzers.

### 4. "Expanded surface for SCA (Software Composition Analysis) / APTs (supply chain attacks)"

mypantry is ~200 lines of code with zero external dependencies. It is published
under the genropy GitHub org, maintained by the same team, with the same review
process and access controls as all other genro-* libraries (genro-bag,
genro-storage, genro-office, genro-routes, etc.). It carries no more risk than
any other internal library already in the dependency tree.

## Decision requested

Discuss at technical committee (2026-04-01):

- Adopt pantry for genropy optional dependency management?
- If yes, proceed with Phase 1 (add dependency) then Phase 2 (migrate)?
- If no, at minimum clean up the dead try/except blocks (#11–#20)?
