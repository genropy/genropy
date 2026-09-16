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

Resolver calls made for a destination node retain the legacy destination path
and getter/load argument conventions. Direct resolver calls retain the current
standalone caching policy; the mixin additionally recognizes Dojo Deferreds so
cache completion waits for their result. Standalone resolver instances attached
to bridged nodes keep their native policy and do not acquire a Dojo queue.

The mixins provide the legacy `lastUpdate`/`isGetter` views and
`meToo`, `runPendingDeferred`, `cancelMeToo`, and node `getValue2` helpers.
No such methods are added to the new core libraries. Future interface needs
must be evaluated separately rather than inferred from Dojo compatibility.

`gnrjs/tests/resolver_deferred_queue_compat.test.js` compares actual legacy and
selected Bag classes for completion order, reentrant reads, cancellation,
getters, notrigger and rejection, and checks native resolver isolation.
