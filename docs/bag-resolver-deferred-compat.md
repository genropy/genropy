# Legacy Dojo resolver queue compatibility

The GenroJS Bag mixins retain the legacy node/resolver protocol for concurrent
reads. The standalone Python and JavaScript Bag libraries are unchanged.

For bridged `GnrBagResolver` instances, a node's first read starts resolution.
Further nonstatic reads while its status is `resolving` receive separate Dojo
Deferreds queued through `meToo`. On success the node enters `loading`, stores
the value, enters `loaded`, schedules queued callbacks, and invokes `onloaded`
with the node as receiver. Queued callbacks read the completed static value.
The primary Dojo Deferred retains its identity. `notrigger` suppresses the
assignment notification, and reads during `loading` return the static value.
Getter resolvers bypass the queue and do not store their result in the node.

`cancelMeToo` cancels queued waiters, not the primary request. Failure preserves
legacy behavior: the node remains resolving and waiters remain pending until
explicitly canceled. This is compatibility, not a new error-recovery design.

All bridged resolver calls retain the legacy contract, with or without a
destination node. Direct calls reload each time; node reads own the cache check.
Without a destination, `_destFullpath` is an empty string. Getter loads receive
one argument and do not update lastUpdate. Other loads receive the destination
as a second argument and update lastUpdate on completion. Dojo Deferreds retain
their identity; ordinary Promise/thenable values are returned untouched, as in
the legacy resolver. The mixin does not interpret `static` as a native option.
Standalone resolver instances attached to bridged nodes keep their native
policy and do not acquire a Dojo queue.

The mixins provide the legacy `lastUpdate`/`isGetter` views and
`meToo`, `runPendingDeferred`, `cancelMeToo`, and node `getValue2` helpers.
No such methods are added to the new core libraries. Future interface needs
must be evaluated separately rather than inferred from Dojo compatibility.

`gnrjs/tests/resolver_deferred_queue_compat.test.js` compares actual legacy and
selected Bag classes for completion order, reentrant reads, cancellation,
getters, notrigger and rejection, and checks native resolver isolation.

## Accepted breaking change: constructor cache setter hook

The legacy JavaScript resolver constructor called `this.setCacheTime(...)`,
which also invoked subclass overrides. The selected resolver initializes
`cacheTime` through the native property setter instead. The mixin intentionally
does not restore the constructor hook. Explicit `setCacheTime(...)` calls
remain supported and still dispatch to subclass overrides.

No application calls or subclass overrides of `setCacheTime` were found in
Sourcerer's indexed repositories or in the current framework/application
checkout (reviewed 2026-09-17). Matches were limited to the legacy definition
and internal constructor call, archived copies, and the mixin definition;
the subclass override in the audit test is synthetic. This search does not
cover unindexed external applications.

Subclasses relying on the constructor hook must move their initialization
into their own constructor after `super(...)`. The differential test records
this accepted difference without restoring the retired resolver attributes API.
