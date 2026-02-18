# gnrconfig.py — Review

## Summary

This module provides configuration management utilities for Genro applications.
It handles loading configuration from XML and Python files, environment variable
management, site discovery, and RMS (Remote Management Service) options.

## Why no split

The module is cohesive with 251 lines, well under the 300-line threshold:
1. All classes (`ConfigStruct`, `InstanceConfigStruct`, `IniConfStruct`) are
   closely related, forming a configuration class hierarchy
2. All functions deal with a single concern: Genro configuration management
3. The internal dependencies are tight - functions reference each other
   (`getGnrConfig` uses `gnrConfigPath`, `setEnvironment`, etc.)
4. Splitting would create artificial boundaries without improving clarity

## Structure

- **Lines**: 251 (after formatting: ~500 with docstrings)
- **Classes**:
  - `ConfigStruct` (lines 62-118): Base configuration loader
  - `InstanceConfigStruct` (lines 121-155): Instance config with db() method
  - `IniConfStruct` (lines 158-301): Config with INI export capability
- **Functions**:
  - `getSiteHandler` (lines 307-347): Site path discovery
  - `setEnvironment` (lines 350-362): Set env vars from config
  - `getGnrConfig` (lines 365-384): Load main configuration
  - `gnrConfigPath` (lines 387-450): Find config directory
  - `updateGnrEnvironment` (lines 453-464): Update environment.xml
  - `getEnvironmentPath` (lines 467-472): Get environment.xml path
  - `getEnvironmentItem` (lines 475-495): Get/set environment item
  - `getRmsOptions` (lines 498-507): Get RMS options
  - `setRmsOptions` (lines 510-521): Set RMS options
  - `getGenroRoot` (lines 524-529): Get Genro installation root

## Dependencies

### This module imports from:
- `gnr.core.gnrsys` — `expandpath`
- `gnr.core.gnrbag` — `Bag`
- `gnr.core.gnrlang` — `gnrImport`
- `gnr.core.gnrstring` — `slugify`
- `gnr.core.gnrstructures` — `GnrStructData`
- `gnr` — `__file__` for root detection

### Other modules that import this:
- `gnr.app.gnrconfig` — re-exports all (backward compatibility)
- `gnr.app.gnrapp` — `getGnrConfig`
- `gnr.app.gnrdeploy` — `IniConfStruct`, `getGnrConfig`, `gnrConfigPath`, `setEnvironment`
- `gnr.app.gnrlocalization` — `getGenroRoot`
- `gnr.app.cli.gnrdbsetup` — `getGnrConfig`
- `gnr.app.cli.gnrdbsetupparallel` — `getGnrConfig`
- `gnr.app.cli.gnrheartbeat` — `getGnrConfig`
- `gnr.app.cli.gnrmkapachesite` — `getGnrConfig`
- `gnr.app.cli.gnrrms` — `setRmsOptions`
- `gnr.core.cli.gnrbagedit` — `getEnvironmentPath`
- `gnr.core.gnrlog` — `getGnrConfig`
- `gnr.db.cli.gnrmigrate` — `getGnrConfig`
- `gnr.dev.cli.gnraddprojectrepo` — `getGnrConfig`
- `gnr.dev.cli.gnrstructconvert` — `gnrConfigPath`
- `gnr.lib.services.rms` — `gnrConfigPath`, `getRmsOptions`, `setRmsOptions`
- `gnr.web.gnrdaemonhandler` — `gnrConfigPath`
- `gnr.web.gnrtask` — `getGnrConfig`
- `gnr.web.gnrwsgisite` — `getGnrConfig`, `getEnvironmentItem`
- `gnr.web.gnrwsgisite_proxy.gnrsiteregister` — `gnrConfigPath`
- `gnr.web.serverwsgi` — `getGnrConfig`, `gnrConfigPath`

## Issues found

| Line | Category | Description |
|------|----------|-------------|
| 121-155 | DEAD | `InstanceConfigStruct` class has zero callers in codebase |
| 307-347 | DEAD | `getSiteHandler` function has zero callers in codebase |
| 453-464 | DEAD | `updateGnrEnvironment` function has zero callers in codebase |

## Usage map

| Symbol | Type | Status | Callers |
|--------|------|--------|---------|
| `ConfigStruct` | class | USED | `gnr.app.gnrdeploy`, test files |
| `ConfigStruct.__init__` | method | USED | instantiation |
| `InstanceConfigStruct` | class | DEAD | (none) |
| `InstanceConfigStruct.db` | method | DEAD | (none) |
| `IniConfStruct` | class | USED | `gnr.app.gnrdeploy` |
| `IniConfStruct.section` | method | USED | via `gnr.app.gnrdeploy` |
| `IniConfStruct.parameter` | method | USED | via `gnr.app.gnrdeploy` |
| `IniConfStruct.toIniConf` | method | USED | via `gnr.app.gnrdeploy` |
| `IniConfStruct.toPython` | method | INTERNAL | called by `ConfigStruct.__init__` |
| `getSiteHandler` | function | DEAD | (none) |
| `setEnvironment` | function | USED | `gnr.app.gnrdeploy` |
| `getGnrConfig` | function | USED | 12 modules (see dependencies) |
| `gnrConfigPath` | function | USED | 5 modules (see dependencies) |
| `updateGnrEnvironment` | function | DEAD | (none) |
| `getEnvironmentPath` | function | USED | `gnr.core.cli.gnrbagedit` |
| `getEnvironmentItem` | function | USED | `gnr.web.gnrwsgisite` |
| `getRmsOptions` | function | USED | `gnr.lib.services.rms` |
| `setRmsOptions` | function | USED | `gnr.lib.services.rms`, `gnr.app.cli.gnrrms` |
| `getGenroRoot` | function | USED | `gnr.app.gnrlocalization` |

## Recommendations

1. **Dead code removal**: Consider removing `InstanceConfigStruct`, `getSiteHandler`,
   and `updateGnrEnvironment` in a future cleanup PR, as they have zero callers.

2. **Type safety**: The `gnrConfigPath` function can return `None` but some callers
   (like `getEnvironmentPath`) use it without null checking. Consider adding
   runtime checks or documenting the expectation that config is always available.

3. **Path handling**: Consider using `pathlib.Path` instead of `os.path` for
   cleaner path manipulation in a future modernization effort.
