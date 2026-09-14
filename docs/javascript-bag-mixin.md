# Lightweight JavaScript Bag mixins

The new path composes subclasses of the standalone classes. It does not load
`gnrbag_genro.js`, copy its methods, or make inherited methods enumerable.
The reserve adapter remains unchanged and independently selectable.

```xml
<experimental>
    <bag_js implementation="genro-bag-js-mixin"/>
</experimental>
```

Use `genro-bag-js` to select the reserve adapter, or `legacy` for the original
Bag. The default remains legacy. No instance configuration is changed by this
implementation.

## Boundaries retained

| Mixin | Framework requirement | Verification |
| --- | --- | --- |
| Node | DOM source identity and parent access, string read modes, positional value assignment, callback lifecycle | Real DOM source construction, parent/path assertions, static and cached callback reads |
| Events | Framework subscriber names and mutation envelopes, original deletion location, reason and path | Nested insert/delete, actual attribute/value changes, silent writes and fired values |
| Bag | Specialized node factory, parent/back-reference aliases, legacy argument objects and tuple result shape | Real DOM source subclass, options and lookup tests |
| Bag removal and firing | Individual reverse-order clear notifications; fire followed by silent reset | Explicit clear and existing/missing fireItem tests |
| Resolver | Callback constructor parameters and parent/cache aliases | Defaults, per-call overrides, receiver, cache and status tests |

Generic storage, digest, sorting, traversal, update, dictionary conversion and
copy algorithms remain inherited. `deepCopy` is only a spelling alias. The
framework namespace and `declaredClass` identify the final subclasses without
changing prototype enumerability. `_parentbag` and `_parentnode` are accessors
for standalone references, not duplicate mutable state.

## Acceptance limits

The focused tests load the real language helpers, standalone bundle, new mixin
and DOM source builder. They do not fall back to the reserve adapter. Python
selection tests verify that each configuration loads the correct asset list.
The reserve regression suite is tested separately and does not establish
compatibility of the new mixin.

This path has not passed a complete browser application trial. Legacy typed
XML, remote resolver reconstruction, Deferred-specific resolver lifecycle,
advanced path semantics and all existing caller return-shape expectations
still require individual review. Truthy `setItem` options `_duplicate`,
`lazySet`, and `fired` currently raise an explicit unsupported-option error.
Do not enable this path for normal instance use yet.

Each further bridge needs a concrete framework consumer and a behavior test.
A defect in a standalone contract belongs in the library; it must not become
an adapter workaround. Remaining differences must be reviewed before adding
compatibility code.
