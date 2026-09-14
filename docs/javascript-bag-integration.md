# Opt-in JavaScript Bag integration

The legacy JavaScript Bag remains the default. An instance can select the
standalone implementation independently from the Python Bag implementation:

```xml
<experimental>
    <bag_js implementation="genro-bag-js"/>
</experimental>
```

The supported values are `legacy`, `genro-bag-js`, and `genro-bag-js-mixin`. Missing configuration
selects `legacy`; any other value stops page asset generation with a clear
error. The selected bundle and adapter are loaded before DOM source, stores,
RPC, widgets and application classes in development and compressed modes.

`genro-bag-js` retains the existing reserve adapter (`gnrbag_genro.js`). The
new `genro-bag-js-mixin` path loads only the bundle and `gnrbag_mixin.js`.
It is an isolated, experimental foundation, not yet an application-ready
replacement. See [the lightweight mixin boundary](javascript-bag-mixin.md)
for its verified scope and outstanding integration work. The compatibility
inventory and current scope below describe the reserve adapter.

## Browser bundle

The checked-in `genro_bagjs_bundle.js` artifact contains genro-bag-js and one
genro-tytx registry. TYTX decimal decoding is configured to use JavaScript
`Number`. Rebuild it from the matching genro-bag-js checkout with locked
dependencies:

```sh
npm install
npm run build:browser
cp dist/genro-bag.browser.js /path/to/genropy/gnrjs/gnr_d11/js/genro_bagjs_bundle.js
cp dist/genro-bag.browser.js.map /path/to/genropy/gnrjs/gnr_d11/js/genro-bag.browser.js.map
```

No CDN or sibling checkout is needed at runtime.

## Compatibility inventory

| Behavior | Framework caller | Legacy API | Standalone API | Integration | Regression |
| --- | --- | --- | --- | --- | --- |
| Ordered storage and direct node access | DOM source, forms, grids | Array-like `_nodes` | `BagNodeContainer` | Framework callers use `getNodes()`; the container keeps `_dict` and `_list` as in Python, without numeric properties or an array facade | Standalone container and active mixin tests |
| Nested specialization | DOM source construction and path autocreate | `_nodeFactory` | `nodeClass` and lexical child construction | Adapter maps `_nodeFactory`; standalone uses the runtime child factory | DOM source node identity test |
| Path reads and writes | Data binding, forms, stores | Mode strings and kwargs object | Boolean static mode and positional options | Adapter translates signatures without replacing standalone storage | Form external-change suite under both implementations |
| Change events | Data logger and bindings | `upd`, `ins`, `del` payloads | `update`, `insert`, `delete` subscribers | Adapter restores event names, payload fields, reasons, paths and parent propagation | Form and event-order tests |
| Resolver results | RPC and callback resolvers | Immediate value or Dojo Deferred | Immediate value or Promise | Standalone accepts thenables; adapter preserves Deferred chaining and synchronous returns | Resolver tests under both implementations |
| Server XML scalars | RPC result handler | `_T` typed text and typed attributes | Generic XML plus TYTX codecs | Adapter normalizes legacy scalar and attribute markers with framework conversion | Legacy XML fixture test |
| Decimal values | Existing application arithmetic | JavaScript `Number` | Configurable TYTX decimal class | Browser entry selects `number` | Bundle inheritance/registry test |
| Browser selection | Page bootstrap | `gnrbag.js` | Bundle plus framework adapter | Instance configuration changes the deterministic frontend list | Python selection tests |

## Current scope

The covered vertical slice includes clean namespace startup, inherited Bag and
node construction, specialized DOM source nodes, legacy typed XML scalars,
data-bound changes, form change tracking, array-style grid access, synchronous
resolver results and Deferred completion. Existing XML/RPC transport remains
in place.

Remote resolver reconstruction covers the server `_resolver` JSON envelope,
relation `_resolver_name` metadata and `_resolvedInfo` attribute overlays.
Unknown resolver descriptions are retained as attributes and are never executed
by the adapter. A real browser application trial remains the final acceptance
check.

## Deferred API proposal

Consider fluent `BagNode.setValue()` as a separate future API change, after reviewing callers that consume its return value. For now both the standalone JavaScript Bag and the GenroPy adapter retain the legacy `undefined` return.

## Missing parent contract

`BagNode.getParentBag()` returns `null` for a detached node. Legacy JavaScript returned `undefined` in this case. This difference is intentional. The runtime and application callers in `gnrjs`, `resources`, and `projects` were checked, including JavaScript embedded in Python: no consumer requires an explicit `undefined` result.
