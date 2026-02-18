# gnrprinthandler.py — Review

## Summary

This module provides print handling utilities using CUPS for network printing,
including PDF generation, printer connections, and file conversion. It appears
to be partially obsolete with similar functionality in NetworkPrintService.

## Why no split

- Only 186 lines of code (now ~400 with docstrings and type hints)
- Two tightly coupled classes (PrintHandler, PrinterConnection)
- Single cohesive responsibility (print handling)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 400 (including docstrings and type hints)
- **Classes**: 3 (`PrintHandlerError`, `PrinterConnection`, `PrintHandler`)
- **Functions**: 0
- **Constants**: 1 (`HAS_CUPS`)

## Dependencies

### This module imports from:
- `cups` — Python CUPS bindings (optional)
- `gnr.core.logger` — logging
- `gnr.core.gnrlang` — GnrException
- `gnr.core.gnrbag` — Bag
- `gnr.lib.services` — GnrBaseService
- `gnr.core.gnrdecorator` — extract_kwargs

### Other modules that import this:
- `gnr.tests.core.gnrprinthandler_test` — tests (import only)

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 214-229 | SMELL | `paper_size` and `paper_tray` dicts duplicated in NetworkPrintService |
| - | SMELL | Module appears partially obsolete (NetworkPrintService provides similar functionality) |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `HAS_CUPS` | constant | INTERNAL | `PrintHandler.__init__` |
| `PrintHandlerError` | class | USED | `autoConvertFiles` |
| `PrinterConnection` | class | USED | `PrintHandler.getPrinterConnection` |
| `PrinterConnection.initPdf` | method | USED | `__init__` |
| `PrinterConnection.printPdf` | method | USED | via `printAgent` |
| `PrinterConnection.printCups` | method | USED | via `printAgent` |
| `PrinterConnection.initPrinter` | method | USED | `__init__` |
| `PrinterConnection.printFiles` | method | USED | external callers |
| `PrintHandler` | class | USED | (external, tests) |
| `PrintHandler.htmlToPdf` | method | USED | `autoConvertFiles` |
| `PrintHandler.autoConvertFiles` | method | USED | `PrinterConnection.printFiles` |
| `PrintHandler.getPrinters` | method | USED | (external) |
| `PrintHandler.getPrinterAttributes` | method | USED | (external) |
| `PrintHandler.getPrinterConnection` | method | USED | (external) |
| `PrintHandler.joinPdf` | method | USED | `PrinterConnection.printPdf` |
| `PrintHandler.zipPdf` | method | USED | `PrinterConnection.printPdf` |

## Recommendations

1. **Investigate relationship with NetworkPrintService**: The `paper_size` and
   `paper_tray` dictionaries are duplicated. Consider consolidating or
   deprecating one of the implementations.

2. **Remove duplicate in gnrwsgisite.py**: There's a `PrintHandlerError`
   class defined in gnrwsgisite.py that appears unused.

3. **Add proper tests**: Current test only verifies import works.
