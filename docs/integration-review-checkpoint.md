# Integration review checkpoint — 2026-09-16

This is a review checkpoint, not a release or a declaration that integration
is ready to merge. Package versions have not been bumped.

## Scope

The companion Python and JavaScript Bag changes define the reviewed public
contracts for traversal, sorting, paths, snapshots, attributes, replacement,
XML serialization, resolver cache durations and deprecated legacy surfaces.
The integration keeps required legacy behavior in compatibility mixins and
updates consumers of changed APIs. The checked-in browser bundle is rebuilt
from the companion JavaScript source at this checkpoint.

Python includes the readonly resolver cache fix: caching is independent of
whether the resolved value is written into the node. The JavaScript equivalent
is still open and must not be assumed to be implemented.

## Companion source commits

- Python Bag: `bb9830c` in genropy/genro-bag.
- JavaScript Bag: `aca2a10` in genropy/genro-bag-js.

## Reproducing the integration

Use the companion Python source checkout on PYTHONPATH ahead of gnrpy.
The released genro-bag package does not yet contain this checkpoint's changes.
No private instance configuration or local node_modules link is included.

## Validation

- Standalone Python: 920 passed, 42 warnings.
- Standalone JavaScript: 677 passed.
- Bundled JavaScript integration: 208 passed, 33 failed, 26 skipped (267 tests).
- Previous integration commit 197d6bb69 with its own sources/tests/bundle:
  117 passed, 62 failed, 26 skipped (205 tests).
- All 33 current failing test names also failed at that previous commit.
  This comparison attributes failures by test identity; it does not prove
  identical causes or classify each as harmless.
- Full Python integration suite under default legacy process mode:
  2597 passed, 10 failed, 10 skipped. All 10 failures belong to
  `test_bag_tytx_transport.py`: native facade hooks (`to_genropy_js` and
  resolver serialization bridge) are not installed in legacy mode.
- The entire transport module rerun in a fresh process with native mode
  enabled: 15 passed, 3 warnings. The suite needs separate process/config
  routing for these native-only tests; a default all-tests run is not green.
- Configured Python lint selection on modified integration files: passed.

## Remaining work

1. Implement and review the readonly cache fix in the new JS resolver.
2. Classify each integration failure below against approved contracts. Retired
   formulas, validation and other intentionally removed APIs must not be
   restored just to satisfy blanket legacy parity assertions.
3. Review compatibility mixins for remaining unnecessary duplication and
   complexity, using a finite tracked list rather than reopening settled APIs.
4. Repeat browser acceptance for login, menu, customer/invoice forms, settings
   tree and data transport using the exact checkpoint sources.
5. Decide release versions and dependency pins only after that review.

## Existing JavaScript integration failures

- Getter intentionally repairs legacy undefined thisWhat for node/value/attr modes
- addItem preserves duplicates and numeric zero insertion position
- back-reference consistency check
- callback resolver merges parameters, kwargs and call-time overrides with bound receiver
- collection methods are inherited from the standalone Bag
- direct trigger API bubbles insertion with original location
- every enumerable legacy member remains visible to mixin enumeration
- every legacy Bag and DOM source prototype member remains available
- every legacy resolver subclass member exists and remains enumerable
- fillFrom merges into existing contents and creates array rows
- formula definitions with an explicitly bound evaluation parent
- formula insertion records pre-existing failures without claiming a working formula flow
- formula resolves root and current Bag symbols including resolver references
- getter resolution leaves timestamp unchanged and omits destination argument
- legacy constructor fields and globals remain addressable
- legacy object lists and HTML table formatting
- legacy string representations and empty compatibility hooks
- modified tracking subscription lifecycle
- no-op resolver hooks and cache reset are inherited from standalone
- node creation helpers and callback reads
- resolver Promise is returned untouched as a non-Deferred legacy value
- resolver and callback accept inherited enumerable kwargs and Bag attributes
- resolver constructor invokes subclass cache setter after creating attributes
- resolver constructor, cache, attributes, parent, default load and reset
- resolver description respects a custom value formatter
- resolver forwards the entire legacy Bag interface
- selected GnrBagNode attribute edge cases match legacy truthy defaults
- selected GnrBagNode constructor preserves legacy identity and resolver state
- selected GnrBagNode exposes every legacy method with matching arity
- selected GnrBagNode refresh and reset delegate with legacy conditions
- selected ancestry preserves graph behavior and orphaned parent is null
- setAttr autocreates missing nodes and replaces existing attributes
- sum ignores strings and includes booleans; strict null handling
