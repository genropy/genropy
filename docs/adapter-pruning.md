# Adapter pruning

The adapter has been reduced from 1,993 to 1,839 lines in this pass. Passing integration tests is not proof that the remaining overrides are minimal.

## Removed implementations

`items`, `keys`, `values`, `columns`, `update`, `delParentRef`, and `getResolver` are inherited directly from the standalone Bag. Tests assert both prototype identity and visibility to the framework's enumerable-method mixins.

The copied `digest` algorithm is replaced by a small row-shape conversion around the standalone implementation. A one-field standalone digest is flat; existing Genro consumers expect one-element rows. Filtering and the three-argument columns form now reach the standalone implementation.

`deepCopy` is a name/argument bridge to `deepcopy`. `BagNode.delAttr` only expands the legacy array argument before delegating. Duplicate `attributes` and `resolver` definitions are consolidated into class methods, which are required to shadow the standalone getters safely.

`GnrBagResolver.onSetResolver` and `reset` are inherited directly. The hook is the
same no-op supplied by the standalone resolver. The adapter's reset only cleared
the last-update timestamp; the standalone reset does that and also clears its
unused parameter fingerprint, which the adapter's custom `resolve` never reads.
Tests assert prototype identity and enumerable visibility for both methods.

## Standalone fixes uncovered by removal

- Digest resolves requested value fields, while key, attribute and explicit static-value queries avoid resolver execution. Excluded nodes are filtered before value resolution.
- Deep copy preserves repeated labels and nullable attributes, uses the specialized node/Bag classes and supports explicitly requested resolution.

## Remaining contract differences

These overrides have not been declared redundant or removed merely because a subset of tests passes:

| Area | Reason the current method cannot simply be deleted |
| --- | --- |
| `sort` | Case sensitivity, mode aliases and placement of nulls differ; nested Bag fields also need correct extraction. |
| `asDict` | Genro uses recursive/flat conversion, `_autolist`, null exclusion and typed-script filtering; standalone parameters instead select ASCII/lowercase keys. |
| `walk` / `forEach` | Callback index, traversal mode, no-recursion flag and `__continue__` behavior differ. |
| `sum` | Genro excludes strings, includes booleans and has a strict missing-value mode; standalone accepts a predicate and recursion option. |
| `getNodes` | Genro exposes its mutable container; standalone returns a snapshot. |
| `getNodeByAttr` | Genro's depth-first traversal differs from standalone level-priority search. |
| `isEqual` | Genro compares identity/parent-node identity; standalone compares contents. |
| Paths and mutation | `get`, `getNode`, `getItem`, `set`, `setItem`, `fillFrom`, pop/clear and insertion preserve Genro path forms, kwargs, duplicate-node insertion and event/iteration contracts. |
| Node attributes/ancestry | Legacy signatures and fallback rules still coexist with DOM-source inheritance and framework node identity. |
| Framework facilities | XML typed envelopes, formatting, formula helpers, RPC/getter resolvers, Deferred coordination and event payload translation depend on Genro services. |

## Retained candidates needing contract review

The following superficially similar methods remain because deleting them would
change observable behavior under the current standalone implementation:

- `BagNode.resetResolver` leaves the cached value in place, while standalone also
  clears it and emits the corresponding value change.
- `BagNode.getAttr`, `hasAttr`, `attributeOwnerNode`, and
  `getInheritedAttributes` retain legacy fallback, loose comparison,
  case-insensitive/comma-list lookup, named-attribute, and inheritance-stop rules.
- `Bag.getNodeByValue`, `getNodeByAttr`, `getNodes`, `setAttr`, and `getAttr`
  differ in path traversal, search order, mutable-container exposure, or argument
  handling.
- `GnrBagResolver.setNode`, `resolve`, `load`, and `expired` retain parent-node,
  default return, call signature, Deferred, and legacy cache semantics.

Further reduction should resolve these contracts in the standalone library or migrate their callers, then remove each corresponding override. They are not all inherently framework-specific.

## Validation

All 178 integration tests pass with `GNR_JS_BAG=genro-bag-js`. The generated
browser bundle was left unchanged. No package release or server restart was
performed in this pass.
