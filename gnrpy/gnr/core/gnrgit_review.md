# gnrgit.py — Review

## Summary

This module provides a wrapper class (`GnrGit`) for interacting with Git
repositories using the dulwich library. It supports both HTTP and SSH
remote connections.

## Why no split

- Only 42 lines of code (now ~85 with docstrings and type hints)
- Single class with a single responsibility
- Already minimal and cohesive
- Splitting would add complexity without benefit

## Structure

- **Lines**: 85 (including docstrings and type hints)
- **Classes**: 1 (`GnrGit`)
- **Functions**: 0
- **Constants**: 0

## Dependencies

### This module imports from:
- `dulwich.client` — `HttpGitClient`, `SSHGitClient`
- `dulwich.repo` — `Repo`

### Other modules that import this:
- `gnr.tests.core.gnrgit_test` — imports module for existence test only

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 70-72 | BUG | Was `raise NotImplemented` instead of `raise NotImplementedError`. `NotImplemented` is a singleton for rich comparisons, not an exception. **Fixed in this refactoring.** |
| 84 | SMELL | `get_refs()` discards the return value from `remote_client.get_refs()`. Should it return the refs? |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `GnrGit` | class | DEAD | (none found in codebase, only test import) |
| `GnrGit.__init__` | method | DEAD | (none found) |
| `GnrGit.get_refs` | method | DEAD | (none found) |

## Recommendations

1. **Investigate usage**: The `GnrGit` class appears to have zero callers in
   the current codebase. It may be used by external code or may be obsolete.
   Consider deprecating if truly unused.

2. **Fix get_refs**: The `get_refs` method should probably return the refs
   instead of discarding them.

3. **Add error handling**: The class could benefit from better error handling
   when the remote config is missing or malformed.

4. **Consider using GitPython**: The dulwich library is lower-level. For
   simpler use cases, GitPython might be more appropriate.
