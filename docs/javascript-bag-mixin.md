# Lightweight JavaScript Bag mixins

The integration composes subclasses of the standalone classes and loads only
`genro_bagjs_bundle.js` and `gnrbag_mixin.js`. The former reserve adapter has
been removed. Inherited methods are not made enumerable.

```xml
<experimental>
    <bag_js implementation="genro-bag-js-mixin"/>
</experimental>
```

Use `legacy` for the original Bag. Missing configuration selects legacy.
The removed `genro-bag-js` option is rejected explicitly.

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

## Validation scope

Focused tests load the actual language helpers, bundle, mixin and DOM source
builder. Selection tests verify the asset order and reject the retired option.
The test harness selects this same mixin for standalone comparisons.

The active path has been exercised with XML and JSON/TYTX on the invoice test
application, including menus, customer rows and record navigation. This is not
full acceptance of every application workflow. Earlier differential audits
contain legacy parity expectations that require review against the current
standalone contract; removing an adapter must not erase those regressions.

Each further bridge needs a concrete framework consumer and a behavior test.
Standalone contract defects belong in the library.

### Removal verification

After removing the reserve adapter, the active mixin/transport suite passes
40 tests and the frontend selection suite passes 5 tests. The full historical
JS suite reports 117 passed, 62 failed and 26 skipped, both before and after
cleanup, but the failing test identities differ because the comparison target
is now the active mixin. These counts must not be presented as full parity.
The explicitly selected DOM-source/form consumer suites improve from 9 passed
and 62 failed against the retired adapter to 59 passed and 12 failed against
the mixin. Outstanding failures include old enumerability assumptions and
resolver/path/XML expectations; they need contract review, not automatic
restoration of the removed implementation.
