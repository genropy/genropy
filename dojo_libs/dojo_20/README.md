# Dojo 2.0 — Softwell Fork

## Overview

This directory contains **Dojo 2.0**, the Softwell fork of the Dojo Toolkit.
It starts as an **exact copy of Dojo 1.1** (`dojo_libs/dojo_11/`) and will
diverge over time as Softwell-specific modifications are applied.

The source repository for the fork is
[genropy/giojo](https://github.com/nicola-porcari/giojo) (Giojo.js).

## Directory Structure

```
dojo_20/
├── dojo/           # Dojo core
├── dijit/          # Dijit widget library  (inside dojo/)
├── dojox/          # DojoX extensions      (inside dojo/)
├── dojo_release/   # Compressed/minified build for production
└── dojo_src/       # Uncompressed source for development
```

## How Dojo Versioning Works in GenroPy

GenroPy has two **independent** version parameters:

| Parameter        | Controls                   | Values      | Default |
|------------------|----------------------------|-------------|---------|
| `dojo_version`   | Dojo toolkit (this dir)    | `'11'`, `'20'` | `'11'`  |
| `gnrjsversion`   | GenroPy JS (`gnrjs/`)      | `'11'`, `'20'` | `'11'`  |

Both can be set independently per-page or per-site.

### Version Selection Chain

1. **Page class attribute** — `dojo_version = '20'` on `GnrCustomWebPage`
2. **Site configuration** — `<dojo_version>20</dojo_version>` in `siteconfig.xml`
3. **Fallback default** — `'11'` (hardcoded in `gnrresourceloader.py`)

The same chain applies to `gnrjsversion`.

### Filesystem Mapping (environment.xml)

The `environment.xml` file maps version keys to filesystem paths:

```xml
<static>
    <js>
        <dojo_11 path="$GNRHOME/dojo_libs/dojo_11" cdn=""/>
        <dojo_20 path="$GNRHOME/dojo_libs/dojo_20" cdn=""/>
        <gnr_11  path="$GNRHOME/gnrjs/gnr_d11"/>
        <gnr_20  path="$GNRHOME/gnrjs/gnr_d20"/>
    </js>
</static>
```

### Runtime Loading

1. **`gnrwsgisite.py:find_gnrjs_and_dojo()`** — reads `environment.xml`,
   builds a dict of available versions and their paths.

2. **Static handlers** — `DojoStaticHandler` and `GnrStaticHandler`
   (in `gnrstatichandler.py`) map URL prefixes to filesystem paths:
   - `/_dojo/11/...` → `dojo_libs/dojo_11/dojo/...`
   - `/_dojo/20/...` → `dojo_libs/dojo_20/dojo/...`
   - `/_gnr/11/...` → `gnrjs/gnr_d11/...`
   - `/_gnr/20/...` → `gnrjs/gnr_d20/...`

3. **Frontend modules** — `gnrpy/gnr/web/gnrwebpage_proxy/frontend/dojo_XX.py`
   declare CSS/JS file lists for each version. Loaded dynamically by
   `gnrwebpage.py` based on `dojo_version`.

4. **DomSrc factories** — `GnrDomSrc_dojo_XX` classes in `gnrwebstruct.py`
   provide version-specific DOM source generation (currently identical).

5. **Template rendering** — `gnr_header.tpl` (Mako) generates `<script>` and
   `<link>` tags using the version-specific file lists.

6. **JS compression** — `jstools.py` concatenates and minifies JS files for
   production (`dojo_release/`), serves individual files in development.

### JS-Side Version Detection

In `genro.js`, the variable:

```javascript
var dojo_version = dojo.version.major + '.' + dojo.version.minor;
```

is used to branch behavior where Dojo 1.1 and 2.0 differ. All existing
`if (dojo_version == '1.1')` checks are preserved for future differentiation.

## Relationship with Giojo

[Giojo](https://github.com/nicola-porcari/giojo) is Softwell's Dojo fork.
It contains the modified Dojo source (dojo + dijit + dojox) plus the GenroPy
JavaScript libraries (gnr_d11). Changes made in Giojo will eventually be
pulled into this directory (`dojo_20/`) and into `gnrjs/gnr_d20/`.

## Adding a New Version (Checklist)

To add a new Dojo version (e.g., `30`):

1. Create `dojo_libs/dojo_30/` with the toolkit files
2. Create `gnrjs/gnr_d30/` with GenroPy JS files
3. Add `GnrDomSrc_dojo_30` in `gnrwebstruct.py`
4. Create `frontend/dojo_30.py` with CSS/JS declarations
5. Add `dojo_30` / `gnr_30` entries in `environment.xml`
6. Add paths in `gnrdeploy.py`

No changes needed to `gnrwsgisite.py`, `gnrstatichandler.py`, or the
template — they all work dynamically with any version found in
`environment.xml`.

## History

- **Versions 1.4, 1.5, 1.7, 1.8** were planned but never used. All related
  code (frontend modules, DomSrc classes, `dojo_libs/dojo_18/`) has been
  removed.
- **Version 1.1** remains the active production version.
- **Version 2.0** was created as an identical copy of 1.1, ready to diverge
  as the Softwell fork (Giojo) evolves.
