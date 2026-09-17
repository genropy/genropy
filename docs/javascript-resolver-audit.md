# Resolver compatibility audit

> Historical adapter audit, not the current compatibility contract. Statements
> about restored/enumerable methods describe an earlier implementation. Consult
> [the decision register](bag-decision-register.md) before using this as a requirement.

> Historical audit of the removed reserve adapter. This document does not describe the active mixin or a supported runtime path.

Baseline: neutral legacy `gnrbag.js`, compared with the selected adapter and its full standalone prototype chain. Executable differential evidence: `gnrjs/tests/resolver_compatibility.test.js`. This covers all legacy members, including inherited members of Formula, Getter and callback resolvers; it is not a claim that every external application or remote transport has been exercised.

| Legacy member | Classification and evidence |
| --- | --- |
| constructor(kwargs,isGetter,cacheTime,load) | Restored undefined kwargs preservation; default cache 0, getter flag, attributes and pending list; constructor/cache test |
| declaredClass | Preserved for each of the four classes; exhaustive enumerable prototype comparison |
| onSetResolver(node) | Explicit enumerable no-op override; standalone `setNode` bridges attachment and records both parent references |
| setCacheTime(cacheTime), getCacheTime() | Compatible direct cache state; cache test |
| reset() | Restored legacy timestamp-only reset; cache test |
| expired(kwargs) | Restored exact legacy TTL comparison, including zero TTL within same millisecond; negative cache resolves once |
| resolve(optkwargs,destinationNode) | Restored call-time `_destFullpath` precedence, ordinary `static` keyword, immediate non-Deferred return; kwargs/getter/Deferred tests, including inherited enumerable parameters and Bag-to-dictionary conversion |
| cancelMeToo(r) | Restored missing-list tolerance; cancellation test |
| meToo(cb), runPendingDeferred(pendingDeferred) | Compatible real Dojo Deferred queue; completion/cancellation test |
| load(kwargs,cb) | Restored legacy no-op instead of inherited abstract-load exception |
| setParentNode(parentNode), getParentNode(parentnode) | Restored setter without hook invocation and undefined initial parent; both standalone and legacy parent references kept coherent |
| htraverse(kwargs) | Restored forwarding of `pathlist,autocreate`; forwarding test |
| keys(), items(), values() | Restored forwarding; output compatibility also depends on Bag implementation |
| digest(k), sum(k) | Restored falsy-key-to-null forwarding; forwarding test |
| contains() | Restored exact no-argument forwarding; legacy Bag itself has no `contains` method; test uses a Bag extension implementing it |
| len(), resolverDescription() | Restored forwarding; `resolverDescription` preserves legacy Object formatting for the new default Bag tree formatter, and respects custom formatters |
| getAttr(), setAttr(attributes) | Compatible shared attribute object and legacy objectUpdate merge, including Bag and inherited enumerable sources; attributes test |
| lastUpdate, cacheTime | Public state mapped to standalone private state; cache test |
| kwargs, isGetter, _attributes, _pendingDeferred, _parentNode | Preserved legacy runtime state, constructor/queue/parent tests |
| Formula constructor(root,expr,symbols,kwargs), root, expr, load() | Equivalent template expansion and root/current evaluation; explicit `_parent` needed as legacy expects. Insertion with symbol-based formulas also fails in the baseline (recursive kwargs copy of the root Bag); selected mode now preserves the same baseline recursive conversion. Both legacy and adapter treat fourth constructor argument as base load override, so non-empty kwargs cause resolve to throw. Preserved existing defect, recorded in test |
| Getter constructor(bag,path,what), path, what, load() | Intentional correction already present: legacy references undefined `thisWhat`; adapter supports node/value/attr. Explicit baseline-error and selected-result regression |
| CbResolver constructor(kwargs,isGetter,cacheTime), method, parameters, load(kwargs) | Equivalent merge precedence, method receiver, cache/getter inheritance; callback regression |

Additional inherited standalone methods (`init`, `setNode`, `node`, `readOnly`, `cachedValue`, `_computeEffectiveFingerprint`, `_finalize`, `_convertToBag`, static `registerBagClass` and `classArgs/classKwargs/internalParams` and standalone configuration fields) have no legacy counterparts. Legacy resolution bypasses standalone caching/retry; only `setNode` participates in attachment. They are not claimed to be legacy public API. No Promise or fetch migration is introduced.

## Consumer inspection

Runtime subclasses are `GnrRemoteResolver` and `GnrServerCaller` in `genro_rpc.js`, and `GnrClientCaller` in `genro.js`. They inherit base resolution and state. `GnrRemoteResolver.resultHandler` directly reads `_parentNode.attr`, making the parent bridge essential. `genro_rpc.js` relation resolvers use `getParentNode()` for relation fields and reload. Callback resolvers are created by `genro_dev.js`, `genro_components.js`, and `genro_widgets.js`. Node lazy loading uses `meToo` and pending completion in `gnrbag_genro.js`; formula factory lives on Bag. No direct external construction of Getter was found in the runtime JS tree.

## Limitations

The real Dojo Deferred implementation is loaded, but these tests do not perform network requests, run an entire browser, or inspect unknown third-party applications. They detect missing API members and compare observable contracts for the enumerated scenarios. Inherited additions are classified, not exhaustively fuzzed. Legacy Formula/contains defects are documented rather than silently changed.
