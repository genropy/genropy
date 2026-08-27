# Client-side build and trigger performance

This document explains why very large Genropy pages were slow on the client,
how the real causes were measured (as opposed to guessed), what was changed in
the js engine and what margins remain.

## How the numbers were measured

Everything below was measured on a purpose-built oversized page,
`test/perf/test_heavy_build` (package `test`): 8 tabs with 120 bound form
fields each, 8 bag grids of 200 rows x 20 columns, 3000 divs with a dynamic
`_class` binding, two tablehandlers. About 8.200 source nodes and 1.400 dojo
widgets on one page.

The page loads `heavy_profiler.js` (a `test` package resource) which offers
three instruments:

- `?_profile=1` wraps the hot engine methods with call counters and
  self/total timing (`gnrProfiler.report()`).
- `?_sample=1` runs the native JS Self-Profiling API across the build; the
  page sends the `Document-Policy: js-profiling` header to enable it
  (`gnrProfiler.sampleReport()` / `totalReport()`).
- `?_bt_sample=N` reloads N times collecting the `startUp` build time in
  localStorage (`gnrProfiler.samples()`), because single measurements vary
  with GC/JIT state.

Reference numbers (median of 6 runs, same machine, same browser tab):

| metric                              | before  | after  |
|-------------------------------------|---------|--------|
| `startUp` build of the heavy page   | 1609 ms | 514 ms |
| 600 `setData` on bound fields       | 384 ms  | 30 ms  |

## Problem 1: every data change reached every subscriber

**What happened.** Every dynamic attribute (`value='^.foo'`, `_class='^...'`,
etc.) subscribed to the single dojo topic `_trigger_data`. `genro.setData`
published on that topic, so every one of the thousands of subscriptions on a
big page ran `trigger_data` -> `attrDatapath` -> `absDatapath` ->
`getTriggerReason`, rebuilding path strings each time, just to discover the
event was not for them. Profiling showed 2.5 million `trigger_data` calls for
600 `setData` (~4.200 subscribers scanned per event). This cost grows with
page size and is paid on **every** data change, forever: it is the main
reason big pages feel sluggish after they are built.

**The fix.** `gnr.GnrTriggerIndex` (in `genro_src.js`) indexes subscriptions
in a trie keyed by the segments of their absolute datapath. An event walks
the trie along its own path and notifies only the nodes registered on that
path, on one of its ancestors, or inside its subtree - the exact superset of
the nodes whose `getTriggerReason` can match. `trigger_data` still performs
its full semantic check, so false positives are harmless and behavior is
unchanged.

Subscriptions whose resolution can change over time are **not** indexed: they
go to a floating set checked on every event, exactly as before. A
subscription is considered stable only when its path and every `datapath` in
its ancestor chain are plain strings (no `^pointer`, no function, no
`#parent`); `#FORM`/`#ANCHOR`/`#DATA` heads are accepted because they resolve
on an ancestor - when that ancestor rebuilds, the whole subtree re-registers
anyway. Everything else (`#ROW`, `#WORKSPACE`, aliases, generic `#nodeId`)
floats. On the heavy page 99 subscriptions float out of ~7.900.

The dojo topic is still published for the few components that subscribe to it
directly (grid cellpars, tree), so external code keeps working.

## Problem 2: full source-tree scans during the build

Three distinct causes, found with the sampling profiler:

- `refreshSourceIndexAndSubscribers` walked the **entire** source tree on
  every `del`/`upd` trigger to rebuild the nodeId index and drop dead
  subscriptions (~450.000 walk calls per build of the heavy page). The
  triggers now clean up only the removed subtree; the full refresh remains as
  a manual utility.
- `genro.nodeById` misses during the build fell back to `getNodeByAttr`,
  a full-tree scan per probe. The `FramePane` "existing frame" assert - one
  probe per frame, always a miss - now checks the nodeId index directly,
  which is correct because frames always register on creation. Other probes
  (grid searchbox lookup, `pyref`) still scan; see "remaining margins".
- `getFormHandler` walked to the root for every node outside a form. The
  negative result is now cached on the node too, so descendants stop at their
  parent.

## Problem 3: per-widget work that never changes

- `createDojoWidget` resolved the widget factory on every creation:
  `dojo.require` calls plus a class-path walk, ~1.400 times per page. The
  factory is now cached by the resolved dojo tag. The cache key must be the
  **resolved** tag, not the genro tag: handlers like `menuline` switch
  `_dojotag` per instance (MenuItem/MenuSeparator/PopupMenuItem).
- `doMixin` scanned every property of the handler for every widget instance,
  doing string work per property. The set of applicable
  `mixin_/patch_/versionpatch_/nodemixin_/validatemixin_` properties never
  changes, so the scan now happens once per handler (`_mixinPlan`) and the
  per-widget work is a short loop. This was the single biggest build win and
  also removed most of the build-time GC noise (measured build variance went
  from +-20% to +-3%).

## Problem 4: bag hot paths

- `htraverse` regex-matched and split every path, even plain single labels
  (the most common case by far: every `setItem`/`getNode` of a direct child).
  Single plain labels now return immediately.
- `walk(cb, 'static')` called `getValue` per node; it now reads `_value`
  directly in static mode.
- `fromXmlDoc` converted every attribute twice; plain strings (no `::T`
  suffix) are now stored as they are.

## What was tried and reverted (worth remembering)

- **Pre-indexing nodeIds of a build batch**: components (bagGrid,
  tablehandler) pop and re-create nodes with the same nodeId during the
  build, so pre-indexed entries went stale and broke every tablehandler page
  ("duplicate nodeId"). Reverted.
- **`_pop` via `splice`**: half the framework iterates `bag._nodes` while
  popping (slot resolution in slotbars, `mergeRemoteContent`...), relying on
  `_pop` replacing the array instead of mutating it. The replacement behavior
  is kept and now documented in the code.

## Where the time goes now (and the remaining margins)

After these changes the build of the heavy page breaks down roughly as:

- ~45% dijit widget instantiation (`dojo.declare` machinery, templates,
  DOM) - not addressable without touching dojo 1.1 or creating fewer
  widgets;
- ~15% XML parsing of the main page bag (`fromXmlDoc`) - a JSON wire format
  for the main source would cut most of it;
- ~10% residual full-tree scans (`genro.nodeById` misses for absent ids:
  grid searchbox probe, `pyref`) - would need a source-level nodeId
  registry maintained on insertion;
- the rest is spread over attribute extraction (`objectExtract` chains,
  ~21 passes per node) and form/validation bookkeeping.

The runtime trigger dispatch is no longer proportional to page size; what is
left of a `setData` burst is the real work (widget `setValue`, validation,
DOM class changes).
