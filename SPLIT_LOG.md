# SPLIT_LOG — gnr.core Package Refactoring Progress

This file tracks progress of the gnr.core module refactoring task.

## Completed modules (1-21)

Based on existing PR branches on origin, the following modules have been processed:

| # | Module | Branch | PR | Decision |
|:-:|--------|--------|:--:|----------|
| 1 | gnrbaseservice.py | `pkg_refactor/gnrbaseservice` | #510 | REVIEW ONLY |
| 2 | gnrenv.py | `pkg_refactor/gnrenv` | #511 | REVIEW ONLY |
| 3 | gnrgit.py | `pkg_refactor/gnrgit` | #512 | REVIEW ONLY |
| 4 | gnrredbaron.py | `pkg_refactor/gnrredbaron` | #513 | REVIEW ONLY |
| 5 | gnrnumber.py | `pkg_refactor/gnrnumber` | #514 | REVIEW ONLY |
| 6 | gnrcaldav.py | `pkg_refactor/gnrcaldav` | #515 | REVIEW ONLY |
| 7 | gnranalyzingbag.py | `pkg_refactor/gnranalyzingbag` | #516 | REVIEW ONLY |
| 8 | gnrdatetime.py | `pkg_refactor/gnrdatetime` | #517 | REVIEW ONLY |
| 9 | gnrcrypto.py | `pkg_refactor/gnrcrypto` | #518 | REVIEW ONLY |
| 10 | gnrrlab.py | `pkg_refactor/gnrrlab` | #519 | REVIEW ONLY |
| 11 | gnrsys.py | `pkg_refactor/gnrsys` | #520 | REVIEW ONLY |
| 12 | loggingimport.py | `pkg_refactor/loggingimport` | #521 | REVIEW ONLY |
| 13 | gnrvobject.py | `pkg_refactor/gnrvobject` | #522 | REVIEW ONLY |
| 14 | gnrssh.py | `pkg_refactor/gnrssh` | #523 | REVIEW ONLY |
| 15 | gnrprinthandler.py | `pkg_refactor/gnrprinthandler` | #524 | REVIEW ONLY |
| 16 | gnrexporter.py | `pkg_refactor/gnrexporter` | #525 | REVIEW ONLY |
| 17 | gnrdecorator.py | `pkg_refactor/gnrdecorator` | #526 | REVIEW ONLY |
| 18 | gnrbageditor.py | `pkg_refactor/gnrbageditor` | #527 | REVIEW ONLY |
| 19 | gnrdict.py | `pkg_refactor/gnrdict` | #530 | REVIEW ONLY |
| 20 | gnrconfig.py | `pkg_refactor/gnrconfig` | #531 | REVIEW ONLY |
| 21 | gnrlog.py | `pkg_refactor/gnrlog` | #532 | REVIEW ONLY |

## gnrlog.py — REVIEW ONLY

- **Branch**: `pkg_refactor/gnrlog`
- **PR**: #532
- **Decision**: review only (module <300 lines, cohesive logging infrastructure)
- **Lines**: 254 (original) → ~380 (with docstrings/type hints)
- **Public names**: 7 (LOGGING_LEVELS, init_logging_system, get_all_handlers, apply_dynamic_conf, get_gnr_log_configuration, set_gnr_log_global_level, AuditLogger)
- **REVIEW markers added**: 4 (BUG: 1, SMELL: 2, DEAD: 1)
- **Dead symbols found**: 1 (get_all_handlers)
- **Tests**: pass (2/2)
- **Commit**: 432ac7fb3

## Next module to process

Module 22: gnrremotebag.py (309 lines)
