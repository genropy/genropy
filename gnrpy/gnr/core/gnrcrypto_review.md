# gnrcrypto.py — Review

## Summary

This module provides classes for generating and verifying signed authentication
tokens with optional expiration timestamps. It supports both plain payloads
and URL signing using HMAC-SHA1.

## Why no split

- Only 98 lines of code (now ~220 with docstrings and type hints)
- Single class with two related exception types
- All components are tightly related (signing/verification)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 220 (including docstrings and type hints)
- **Classes**: 3 (`AuthTokenError`, `AuthTokenExpired`, `AuthTokenGenerator`)
- **Functions**: 0
- **Constants**: 0

## Dependencies

### This module imports from:
- `base64` — URL-safe base64 encoding
- `datetime` — timestamp handling
- `hashlib` — SHA1 hashing
- `hmac` — HMAC signing
- `urllib.parse` — URL parsing
- `gnr.core.logger` — logging

### Other modules that import this:
- `gnr.web.gnrwsgisite` — uses `AuthTokenGenerator` for external URLs

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| — | — | No issues found |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `AuthTokenError` | exception | USED | tests, raised internally |
| `AuthTokenExpired` | exception | USED | tests, raised internally |
| `AuthTokenGenerator` | class | USED | `gnrwsgisite.py`, tests |
| `AuthTokenGenerator.generate` | method | USED | tests |
| `AuthTokenGenerator.verify` | method | USED | tests |
| `AuthTokenGenerator.generate_url` | method | USED | `gnrwsgisite.py` |
| `AuthTokenGenerator.verify_url` | method | USED | `gnrwsgisite.py` |

## Recommendations

1. **Good module**: Well-designed, cohesive module for authentication token
   handling. No changes needed beyond documentation and type hints.

2. **Consider SHA-256**: The module uses SHA-1 for HMAC. While HMAC-SHA1 is
   still considered secure for this use case, SHA-256 would be more modern.
   This could be made configurable in a future enhancement.

3. **Consider using `secrets` module**: For any random token generation,
   the `secrets` module should be preferred over other random sources.
