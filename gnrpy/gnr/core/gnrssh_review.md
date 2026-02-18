# gnrssh.py — Review

## Summary

This module provides SSH tunneling utilities using paramiko for secure
port forwarding. It's used by the daemon handler for database connections
through SSH tunnels.

## Why no split

- Only 143 lines of code (now ~360 with docstrings and type hints)
- Single cohesive responsibility (SSH tunneling)
- Classes are tightly coupled (Handler uses SshTunnel attributes)
- Splitting would add complexity without benefit

## Structure

- **Lines**: 360 (including docstrings and type hints)
- **Classes**: 4 (`ForwardServer`, `Handler`, `IncompleteConfigurationException`, `SshTunnel`)
- **Functions**: 3 (`normalized_sshtunnel_parameters`, `stop_tunnel`, `main`)
- **Constants**: 2 (`CONN_STRING_RE`, `CONN_STRING`)

## Dependencies

### This module imports from:
- `paramiko` — SSH client library (optional)
- `gnr.core.logger` — logging
- `gnr.core.gnrlang` — GnrException

### Other modules that import this:
- `gnr.web.gnrdaemonhandler` — uses SshTunnel and normalized_sshtunnel_parameters
- `gnr.tests.core.gnrssh_test` — tests

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 142-144 | SMELL | Bare except that just re-raises (try/except serves no purpose) |
| 340-344 | SMELL | `password = None` immediately followed by `password = getpass.getpass(...)` |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `CONN_STRING_RE` | constant | USED | `CONN_STRING` |
| `CONN_STRING` | constant | USED | `normalized_sshtunnel_parameters` |
| `normalized_sshtunnel_parameters` | function | USED | `gnrdaemonhandler.sshtunnel_get` |
| `ForwardServer` | class | USED | `SshTunnel.prepare_tunnel` |
| `Handler` | class | USED | `SshTunnel.prepare_tunnel` (subclassed) |
| `IncompleteConfigurationException` | class | USED | `SshTunnel.prepare_tunnel` |
| `SshTunnel` | class | USED | `gnrdaemonhandler.sshtunnel_create` |
| `stop_tunnel` | function | USED | `main` (atexit) |
| `main` | function | INTERNAL | only `if __name__ == '__main__'` |

## Recommendations

1. **Remove useless try/except**: In `Handler.handle()`, the try/except
   block that just re-raises serves no purpose:
   ```python
   # Current (useless)
   try:
       chan = self.ssh_transport.open_channel(...)
   except Exception:
       raise

   # Better
   chan = self.ssh_transport.open_channel(...)
   ```

2. **Clean up main()**: Remove redundant `password = None` assignment.

3. **Consider adding SSH key authentication**: Currently only password
   auth is supported (`look_for_keys=False`).
