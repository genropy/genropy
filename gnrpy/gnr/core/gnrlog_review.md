# gnrlog.py — Review

## Summary

This module provides the logging infrastructure for Genro applications. It handles:
- Configuration loading from siteconfig XML
- Dynamic runtime log level adjustment
- Audit logging with specialized loggers
- Integration with various logging handlers (stdout, file, postgres, etc.)

## Why no split

- Module has 254 lines (under 300-line threshold)
- All components are tightly coupled around a single responsibility: logging
- Functions and classes work together as a cohesive unit
- Splitting would not improve clarity or maintainability

## Structure

- **Lines**: 254 (after refactoring with docstrings/type hints: ~380)
- **Constants**:
  - `LOGGING_LEVELS` (line 45): Dict mapping level names to logging constants
  - `DEFAULT_LOG_HANDLER_CLS` (line 56): Default handler class path
- **Functions**:
  - `_load_handler` (line 60): Load handler class from fully qualified name
  - `init_logging_system` (line 78): Initialize the logging infrastructure
  - `get_all_handlers` (line 162): Get available stdlib handlers
  - `apply_dynamic_conf` (line 177): Apply configuration at runtime
  - `_load_logging_configuration` (line 193): Parse and apply Bag configuration
  - `get_gnr_log_configuration` (line 244): Get current logging state
  - `set_gnr_log_global_level` (line 278): Set level for all gnr loggers
- **Classes**:
  - `AuditLoggerFilter` (line 302): Filter that adds user info to records
  - `AuditLogger` (line 322): Specialized logger for audit trails

## Dependencies

### This module imports from:
- `gnr.core.gnrconfig` — `getGnrConfig()`

### Other modules that import this:
- `gnr/__init__.py` — imports module and calls `init_logging_system()`
- `gnr/app/gnrapp.py` — imports module, calls `apply_dynamic_conf()`
- `gnr/sql/__init__.py` — imports `AuditLogger` (creates `SqlAuditLogger`, `OrmAuditLogger`)
- `gnr/core/cli/__init__.py` — imports module, uses `LOGGING_LEVELS` and `set_gnr_log_global_level()`
- `projects/gnrcore/packages/sys/webpages/logging.py` — imports `get_gnr_log_configuration()`

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 127 | SMELL | Bare `except Exception` catches too much; should be more specific |
| 210-212 | BUG | `handler.attr.pop("impl")` mutates the caller's attr dict, which could cause issues if the config is reused |
| 229-232 | SMELL | Original code assigned to variable `l` but then used `clogger`; now fixed but indicates code was copy-pasted |
| 162-164 | DEAD | `get_all_handlers()` has zero callers in codebase (commented out in logging.py) |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `LOGGING_LEVELS` | constant | USED | `gnr/core/cli/__init__.py`, same module |
| `DEFAULT_LOG_HANDLER_CLS` | constant | INTERNAL | same module only |
| `_load_handler` | function | INTERNAL | same module only |
| `init_logging_system` | function | USED | `gnr/__init__.py`, `gnrpy/tests/core/gnrlog_test.py` |
| `get_all_handlers` | function | DEAD | (commented out in `projects/.../logging.py`) |
| `apply_dynamic_conf` | function | USED | `gnr/app/gnrapp.py` |
| `_load_logging_configuration` | function | INTERNAL | same module only |
| `get_gnr_log_configuration` | function | USED | `projects/gnrcore/packages/sys/webpages/logging.py` |
| `set_gnr_log_global_level` | function | USED | `gnr/core/cli/__init__.py`, test |
| `AuditLoggerFilter` | class | INTERNAL | used only by `AuditLogger` |
| `AuditLogger` | class | USED | `gnr/sql/__init__.py` (subclassed) |
| `AuditLogger.log` | method | USED | called via dynamic `__getattr__` |
| `AuditLogger._get_logger` | method | INTERNAL | same class only |
| `AuditLogger._get_logger_name` | method | INTERNAL | same class only |

## Recommendations

1. **Fix the mutation bug**: The `handler.attr.pop("impl")` call mutates the original
   Bag node's attributes. Consider copying the dict first:
   ```python
   handler_kwargs = dict(handler.attr)
   handler_impl = handler_kwargs.pop("impl")
   ```

2. **Consider removing `get_all_handlers`**: Function has no callers and is commented
   out where it was intended to be used. Mark for deprecation or removal.

3. **Improve exception handling**: The bare `except Exception` in `init_logging_system`
   should catch a more specific exception type, or at least log the error.

4. **Consider thread safety**: The werkzeug logger configuration at module level
   happens at import time, which is generally fine but could be made more explicit.
