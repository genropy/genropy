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

Generic storage, traversal, update, dictionary conversion and
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

## Duplicate labels in addItem

The active mixin follows Python's compatibility `addItem` collision policy.
An existing label is preserved; the new node receives the first free
`<label>__dup_N` name, starting at 1 and reusing gaps after deletion. Each rename
emits a deprecation warning and stores the original label in `node.xmlTag`.
The fourth-argument options accept `duplicate_policy: 'error'` to reject a
collision instead; the default is `'rename_warn'`.

Both the dictionary and ordered list therefore reference nodes with unique
labels. Code that relied on repeated labels should use the returned node or its
new label. JS keeps its existing node return value, position option and trigger
controls; Python's fluent return convention is not introduced by this change.
This does not change the standalone JS XML reader or the legacy JS Bag selected
without the switch.

## Clearing a Bag

`clear()` / `clear(false)` removes and detaches nodes without events. With a
truthy trigger and backrefs enabled, `clear` emits one deletion per original
node in reverse order, with its original index, origin Bag and a null reason.
Storage is already empty during callbacks; node ancestry remains available until
the callback completes. Each removed node is then detached. Nodes restored or
moved by a callback are retained. A throwing callback propagates its exception;
remaining notifications stop, but the removed nodes are still detached.

Clearing snapshots the nodes once and empties storage without per-node searches,
independently of whether the bundled container detaches nodes itself (0.5.1) or
leaves detachment to the Bag (0.5.2).

## Resolver initialization

The resolver mixin retains the standalone constructor's parameter object,
including class defaults and changes made by `init()`. Internal settings remain
excluded from load parameters. Legacy inherited enumerable input properties are
copied before invoking the standalone constructor.

`GnrRemoteResolver` consumes transport options from its effective parameter
object, so defaults and initialization changes also configure the request without
leaking into its payload. It continues removing those options from the original
caller object for legacy compatibility. Ordinary parameters remain available via
`resolver.kwargs`; this is no longer an alias of the constructor input object in
standalone mode. Subsequent parameter changes should use `resolver.kwargs`.

## Node tags

The node mixin forwards native `nodeTag` and `xmlTag` constructor arguments.
`addItem` accepts both in its options; an explicit XML tag takes precedence over
the original label recorded on collision. `setItem` forwards `options.nodeTag`
through the standalone signature. Imported nodes retain their tag metadata when
rebuilt as framework nodes: TYTX carries `nodeTag`, while XML import supplies
`xmlTag`. These fields are distinct from the DOM source `attr.tag`.

## Legacy sort syntax

The canonical modes are `a`/`d` (case-insensitive) and `A`/`D`
(case-sensitive), with `a` as the default. Both the legacy JS Bag and the mixin
accept these modes. The grid emits canonical modes directly.

The mixin delegates canonical modes unchanged to the standalone algorithm.
Legacy `a*`/`d*` still work but emit a deprecation warning: replace them with
`a`/`d`. Older direction aliases remain accepted. Callable keys pass through
unchanged. Null placement and Bag field extraction belong to the standalone
library, not to this syntax bridge.

## Legacy XML writer

`toXml`, `toXmlBlock` and the node `_toXmlBlock` use GenroJS's existing
`xml_buildTag` conversion helpers to retain the legacy GenRoBag envelope,
encoding header, scalar type markers, typed attributes and cached resolver
values. Nested standalone Bags are supported without mutating their classes.
The original `xmlTag` is used where present. Resolver execution is not triggered
by serialization. No standalone XML algorithm is copied into this bridge.

Regression tests compare wire output to the legacy JS writer and exercise JS
readback. A cross-language test also covers `Bag(xml)` with both Python modes:
legacy passes; native currently loses the empty Bag value (it becomes `::bag`).
The explicit native legacy XML reader preserves it. This constructor-reader
mismatch is recorded by a failing assertion, not worked around in the writer.

## Node path compatibility change

A node without a parent Bag has no path: both `node.fullpath` and
`node.getFullpath()` return `null`, including numeric path modes. This replaces
the legacy method's empty string and the earlier mixin's misleading label.
Connected first-level nodes return their label; nested nodes include ancestor
labels. In a detached subtree, remaining internal parent links define paths
relative to that subtree. This depends on the actual node-to-Bag link, not only
on the Bag's backref flag. Callers must handle `null` before using a path.

## Temporary single-field digest compatibility

The JS mixin retains legacy single-field rows: `digest('#v')` returns
`[[value1], [value2]]` and emits a deprecation warning. The standalone library
continues to return `[value1, value2]`. Multiple fields and column mode remain
unchanged; predicates still filter before wrapping. Values that are arrays are
wrapped as one value, not mistaken for an existing row.

This exception protects known framework/application callers that extract row[0].
Migrate those callers to `query(what, condition)` and consume its flat single-field
result before removing this compatibility override. Do not change callers to
flat digest consumption while this override remains active.

## Attribute lookup order

The mixin defaults `getNodeByAttr(attr, value, caseInsensitive, deep_first)` to
`deep_first=true`, preserving legacy JS traversal. The standalone library defaults
to false (current-level priority). Pass false explicitly as the fourth argument
to select the standalone order. The bridge delegates the complete search and
preserves the standalone presence-only lookup when value is omitted/undefined.
