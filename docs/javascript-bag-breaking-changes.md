# JavaScript Bag compatibility: accepted breaking changes

## Text rendering: `Bag.__str__()`

The selected JavaScript Bag does not provide the legacy `__str__()` method.
Use `toString()` or `toStringTree()` for a readable representation of its
contents. The output format changes; these methods are for inspection, not
serialization. Static rendering is the default. The mixin does not restore
`__str__`. Python's `__str__` protocol remains available and is unaffected.

No external calls were found in the framework and application checkout during
review on 2026-09-17; the legacy implementation calls itself recursively.
Unindexed external applications are not covered by this observation.

The later usage audit below also closes `__str2__` and `asString`.

## `merge()` is absent in JavaScript

The legacy JavaScript `merge()` was an empty placeholder returning `undefined`.
Neither the new Bag nor its compatibility mixin provides it. Python's
compatibility implementation is retained unchanged. A future joint review of
`merge` and `diff` will evaluate usefulness and possible complete introduction
with equivalent Python/JavaScript contracts; see the
[issue proposal](bag-merge-diff-issue-proposal.md).

## Removal of the `pathsplit()` placeholder

The legacy JavaScript `Bag.pathsplit()` had an empty body and returned
`undefined`. It is intentionally absent from the new JavaScript Bag and its
compatibility mixin. No replacement is provided for this unimplemented API.

No callers were found in the framework/application checkout or Sourcerer's
indexed repositories during review on 2026-09-17. Python's legacy private
`_pathSplit()` is a different method; this decision does not change Python
path handling or introduce a public Python `pathsplit()` API.

## Normalized resolver defaults (D20 / R03)

A no-argument `new gnr.GnrBagResolver()` retains the new library's defaults.
The compatibility mixin intentionally does not restore legacy `undefined`:

| Read | Legacy | Selected mixin |
| --- | --- | --- |
| `kwargs` | `undefined` | `{}` |
| `isGetter` | `undefined` | `false` |
| `getParentNode()` before attachment | `undefined` | `null` |
| Unimplemented base `load()` result | `undefined` | `null` |

Code checking these values with strict equality must account for this change.
An empty kwargs object is truthy; inspect its keys when testing for parameters.
Ordinary getter-flag truthiness is unchanged. Cache duration and initial update
timestamp are unchanged. This decision does not change callback results or
explicit parent assignments. No runtime adapter is added for these defaults.
The approved contract is covered by resolver_compatibility.test.js.

## Usage-based compatibility audit (2026-09-17)

The approved rule is: restore observed legacy use in the compatibility mixin;
otherwise document the difference. This audit closes R04, R06-R08 and V03.
It does not remove unrelated APIs or change either native library.

| Scope | Accepted difference | Migration |
| --- | --- | --- |
| Bag | `__str2__`, `asString` absent | Use `toString` / `toStringTree`; output is not identical. |
| Bag | `newNode`, `setParent`, `setParentNode`, `set`, `runTrigger`, `onNodeTrigger` absent | Use public insertion/removal/subscription APIs; direct wiring and manual trigger dispatch have no automatic replacement. `setItem` is the insertion entry point. Resolver `setParentNode` is unrelated and retained. |
| BagNode | `toJSONString`, `doWithValue` absent | Choose explicit serialization; read the value and handle any asynchronous result explicitly. |
| setItem options | No `_new_label` / `_new_position` writeback | Read the returned node's label and query its position if needed. Input `_position` remains supported. |
| setItem positional path | Missing `#n` target throws instead of returning null | Check that the indexed node exists before updating. Normal valid positional paths remain supported. |

No active external JS Bag consumers of the removed helpers/writeback were found
in Sourcerer's indexed repositories. Definitions, internal legacy dispatch,
comments, inventory copies and tests are not application uses. This is search
evidence, not a guarantee about unindexed applications or computed method names.
No dependency on a silent out-of-range positional update was identified.

Search evidence: `._new_label` and `._new_position` found assignments and a
commented grid read; `.doWithValue(` and `.setParentNode(` found no calls;
`.toJSONString(`, `.__str2__(`, `.newNode(`, `.runTrigger(` and
`.onNodeTrigger(` found only legacy internals/inventory copies. `.asString(`
external hits were Python. `.setParent(` hits concerned unrelated objects.
The generic `.set(` search was paginated through 165 matching modules (671
matching lines across indexed versions): JS calls belonged to node containers,
Map, Headers, editors, URL parameters, third-party libraries or legacy internal
dispatch, not external Bag consumers. Search counts are not unique call counts.
Positional searches included both quote styles and found grid/configuration
paths into existing rows, with no demonstrated reliance on missing indexes.

### Used contracts restored in the JS mixin

- XML-string construction: `genro_components.js` PaletteImporter uses
  `new gnr.GnrBag(result.currentTarget.responseText)`; `gnrlang.js`
  `convertFromText` delegates BAG/X input to the constructor. Sourcerer also
  found `resources/ecr.js` reading `http.responseText`. The constructor now
  routes XML to the existing typed decoder, including the class dictionary.
  Scalar XML relation resolvers start unloaded; populated resolver branches
  preserve their cached contents.
- `attributeOwnerNode`: FORM lookup in `genro.js` and `gnrdomsource.js` uses
  comma-separated alternatives; `genro_tree.js` uses case-insensitive tag lookup.
  The mixin preserves the legacy method contract.
- `getInheritedAttributes`: used by menu, attachments and source widgets.
  `genro_widgets.js` sets `stopInherite`. The mixin preserves the legacy boundary
  and single-attribute behavior without changing native Bag semantics.

Regression coverage: native_bag_classes.test.js and the accepted-removal
registry consumed by bag_surface_audit.test.js. Existing scenario tests retain
ordering, values, resolver lifecycle and ancestry checks; intentional differences
are asserted explicitly, not skipped.
