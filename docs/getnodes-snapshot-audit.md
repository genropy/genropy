# Node list snapshot contract and caller review

New Python and JavaScript get_nodes/getNodes return independent lists of shared
nodes, including through compatibility mixins. List operations must not be used
to mutate Bag structure. This is an intentional difference from legacy unfiltered
getNodes. Public Bag APIs preserve container indexes, ownership and notifications.

Reviewed local GenroPy framework and bundled applications: gnrjs/gnr_d11/js,
gnrpy, projects and resources, including JavaScript embedded in Python strings.
Searches covered direct list mutations and assignments of getNodes/get_nodes
results; an alias-mutation candidate scan examined the following 100 lines.
This is a static review, not a complete interprocedural alias analysis, and does
not cover external application repositories.

Confirmed structural dependency: grouplet_grid.moveRow spliced the returned
array. It now uses moveNode(fromIndex, finalIndex, false), preserving node identity,
parent ownership and silent movement. Tests execute the actual moveRow body
against legacy and new mixin Bags, moving both directions before/after targets.

statspane reversed the returned list only to traverse it before deleting matching
nodes through popNode. An explicit slice before reverse prevents the legacy mode
from reversing the underlying Bag as a side effect. Deletion remains through the
public API.

Other mutation candidates operate on map-produced lists (Google chart columns,
DOM columns and external-token widget descriptions), not the original node list.
Reviewed Python call sites use traversal, indexing or wrapper iteration; no
structural mutation dependency was identified there.
