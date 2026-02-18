# gnrexporter.py — Review

## Summary

This module provides data export utilities for various formats (CSV, HTML,
JSON, Excel). It's used by the batch export system and endpoints.

## Why no split

- Only 221 lines of code (now ~600 with docstrings and type hints)
- Single cohesive responsibility (data export)
- Classes share common base class and patterns
- Splitting would add complexity without benefit

## Structure

- **Lines**: 600 (including docstrings and type hints)
- **Classes**: 4 (`BaseWriter`, `CsvWriter`, `HtmlTableWriter`, `JsonWriter`)
- **Functions**: 1 (`getWriter`)
- **Constants**: 0

## Dependencies

### This module imports from:
- `openpyxl` — Excel support (optional)
- `gnr.core.gnrxls` — Excel writers
- `gnr.core.gnrstring` — text formatting (imported at runtime)

### Other modules that import this:
- `gnr.web.batch.btcexport` — batch export functionality
- `projects/gnrcore/packages/adm/webpages/endpoint.py` — API endpoints
- `gnr.tests.core.gnrexporter_test` — tests

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 51 | SMELL | Bare `except:` should be `except ImportError:` |
| 527 | BUG | HTML typo: `</captipn>` instead of `</caption>` |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `getWriter` | function | USED | btcexport, endpoint |
| `ExcelWriter` | import | USED | `getWriter` |
| `BaseWriter` | class | USED | base for all writers |
| `CsvWriter` | class | USED | via `getWriter` |
| `HtmlTableWriter` | class | USED | via `getWriter` |
| `JsonWriter` | class | USED | via `getWriter` |

## Recommendations

1. **Fix typo in HTML**: Line 527 has `</captipn>` instead of `</caption>`.

2. **Fix bare except**: Line 51 should use `except ImportError:` instead of
   bare `except:`.

3. **JsonWriter serialization**: The `workbookSave` method uses string join
   on a list of dictionaries, which won't produce valid JSON. Should use
   `json.dumps()`.

4. **Add proper tests**: Current test only verifies import works. Should
   test actual export functionality.
