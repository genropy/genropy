# gnrrlab.py — Review

## Summary

This module provides a base class (`RlabResource`) for generating PDF documents
using ReportLab, integrating with Genro's page system and storage nodes.

## Why no split

- Only 109 lines of code (now ~240 with docstrings and type hints)
- Single class with a single responsibility
- Already minimal and cohesive
- Splitting would add complexity without benefit

## Structure

- **Lines**: 240 (including docstrings and type hints)
- **Classes**: 1 (`RlabResource`)
- **Functions**: 0
- **Constants**: 0

## Dependencies

### This module imports from:
- `io` — `BytesIO` for in-memory PDF
- `reportlab.pdfgen` — `canvas` for PDF generation
- `gnr.core.gnrstring` — `slugify` for filename generation

### Other modules that import this:
- `gnr.tests.core.gnrrlab_test` — imports module for existence test only

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 235 | DEAD | `main()` method is a stub that must be overridden |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `RlabResource` | class | DEAD | (none found in codebase) |
| `RlabResource.__init__` | method | DEAD | (none found) |
| `RlabResource.__call__` | method | DEAD | (none found) |
| `RlabResource.getPdfPath` | method | DEAD | (none found) |
| `RlabResource.getPdfStorageNode` | method | DEAD | (none found) |
| `RlabResource.makePdfIO` | method | DEAD | (none found) |
| `RlabResource.outputDocName` | method | DEAD | (none found) |
| `RlabResource.makePdf` | method | DEAD | (none found) |
| `RlabResource.main` | method | DEAD | stub, must be overridden |

## Recommendations

1. **Investigate usage**: The `RlabResource` class appears to have zero callers
   in the current codebase. It may be used by external code/projects or may
   be obsolete. Consider deprecating if truly unused.

2. **Add tests**: The current test only checks import. Adding tests for basic
   PDF generation would improve coverage and validate the class works correctly.

3. **Consider modernization**: ReportLab is still actively maintained, but
   consider if weasyprint or other libraries might be more suitable for
   modern use cases.
