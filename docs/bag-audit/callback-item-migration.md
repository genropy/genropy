# GenroJS callback item migration

`setCallBackItem(path, callback, parameters, kwargs)` is retained only in the
framework mixin and is deprecated. It emits one warning per page, without
blocking execution. The data library already provides
`setCallbackItem(path, callback, options)`.

The compatibility method keeps the legacy undefined return, callback receiver,
parameter precedence (defaults, configured kwargs, per-call overrides), and
node attributes including method/parameters. It uses the framework callback
resolver, preserving its node/cache accessors. Caller dictionaries are not
mutated. Do not migrate by merely changing the capital B: node attributes and
resolver options need explicit review. In particular legacy kwargs.isGetter
was not the positional isGetter constructor argument; do not silently reinterpret
it as readOnly during a spelling migration.

## Known callers

| Location | Purpose / migration concern |
| --- | --- |
| gnrjs/gnr_d11/js/genro.js:940 | Parent iframe Bag; kwargs.isGetter requires explicit semantic review |
| gnrjs/gnr_d11/js/genro.js:948 | Child iframe Bag; callback closes over its data |
| gnrjs/gnr_d11/js/genro_grid.js:815 | Context menu; gridNodeId is callback configuration and node attribute |
| gnrjs/gnr_d11/js/genro_grid.js:1031 | Column menu; callback closes over sourceNode |
| resources/common/th/th_viewconfigurator.js:108 | Structure menu; gridId is callback configuration and node attribute |

These five source occurrences have not been rewritten. They remain functional
through the deprecated method while the legacy/new switch is supported.
External applications may have further callers.

Regression coverage: defaults and per-call overrides, callback receiver, node
attributes, absent optional arguments, caller input preservation, and a single
warning across repeated calls.
