# JavaScript Bag audit reconciliation

## Explicit audit-test removal

Following explicit user instruction, the 12 remaining failing audit tests were
removed, not skipped or converted to passing expectations. The two passing
resolver inventory cases remain. Current suite: 278 tests, 252 passed, zero
failed, 26 pre-existing skips. Runtime code was not changed. R01-R08 remain
recorded findings; test removal does not resolve or accept those differences.
Earlier references below to retained failing tests describe the prior checkpoint.


The historical audit compared every legacy detail with the selected mixin.
That is not the current contract: documented removals, native inheritance and
shared Python/JavaScript behavior must be tested explicitly, while undecided
parity gaps must remain visible.

This cleanup changes tests only. No runtime implementation, bundle, native
library, or pointer-expression compatibility test was changed.

## Accepted decisions now asserted

Decision sources are `javascript-bag-mixin.md`,
`javascript-bag-breaking-changes.md`, and the standalone JavaScript package's
`BREAKING_CHANGES.md`.

- Inherited native methods remain callable and non-enumerable. Function
  declaration arity is not used as an argument compatibility test: default and
  rest parameters change `.length` without changing accepted calls.
- `sum` ignores non-numeric values without strict mode and rejects them with
  strict mode. Strict null values produce null; filtering precedes validation.
- `addItem` renames collisions and preserves both values. Insertion-position
  behavior is checked separately rather than hidden behind the old labels.
- `setAttr` creates missing nodes and preserves existing attributes by default.
- Removed formulas, getter class, resolver attribute methods/description,
  object-list and callback helpers, modification tracking and `backrefOk` are
  asserted absent. Previously approved `__str__`, `merge` and `pathsplit`
  removals are included in the same explicit registry.
- `bag_accepted_removals.cjs` lists only approved removals. The public member
  inventory fails on every other missing name, including inherited DOM source
  members. Class removals are likewise enumerated explicitly.
- Private constructor storage layouts and underscore-prefixed implementation
  members are not a public compatibility requirement. Public insertion/event
  and attach/remove operations check the observable behavior instead.
- The still-supported `get_modified` reader is checked without restoring the
  removed automatic tracking mechanism.

Mixed tests were separated so retired features cannot prevent verification of
HTML tables, rowchild, attribute operations, collection forwarding, cache reset,
or inherited parameter handling. No additional skips or expected failures were
introduced.

## Validation

Command: `node --test --test-reporter=spec gnrjs/tests/*.test.js`.

Before cleanup: 232 passed, 25 failed, 26 skipped (283 total).
After cleanup: 252 passed, 12 failed, 26 skipped (290 total).

Counts change because combined scenarios were split. The 12 failures are not
12 independent runtime defects. All eight pointer-expression tests remain in
the suite and pass. Remaining failures are intentionally retained for review.

## Remaining differences, not silently accepted

Use [the decision register](bag-decision-register.md#active-queue-after-reconciliation)
for current status and stable issue IDs. Resolver compatibility gaps are
implementation work under D17, not fresh design decisions. This table records
the cleanup findings; it is not a separate decision queue.

| Area | Difference still exposed |
| --- | --- |
| Insertion options | `_position: 0` inserts correctly in both implementations, but selected does not write legacy `kwargs._new_position = 0`. |
| Bag public inventory | `newNode`, `setParent`, `setParentNode`, `asString`, `set`, `runTrigger`, `onNodeTrigger` are missing. The DOM source inventory repeats the same inherited gaps. No explicit accepted removal was found in the reviewed documents. |
| Node public inventory | `toJSONString` and `doWithValue` are missing. Node and DOM source inventories repeat these gaps. The legacy `toJSONString` is already nonfunctional in its existing serialization test; that does not itself authorize removal. |
| String rendering | `__str2__` and `asString` remain missing. Acceptance of `__str__` removal and introduction of an optional HTML renderer do not decide these two contracts. Each now has its own test. |
| Attribute default | Node `getAttr('missing', 0)` returns 0 in selected and null in legacy. Falsy attribute presence, deletion and replacement pass separately. |
| Resolver defaults | Accepted and closed as D20/R03: selected keeps kwargs `{}`, getter flag false, absent parent and base load result null instead of legacy undefined. Initial timestamp and cache duration agree. Explicit regression coverage replaces the retired parity expectation. |
| Resolver attachment hook | Resolved as R02: the JS mixin parent setter now assigns only the reference; node resolver attachment still invokes the hook. Two differential tests cover hook dispatch and unchanged cache timestamp. |
| Callback direct load | R01 is now implemented provisionally in the JS mixin: load and resolve preserve own/inherited live defaults and call-time overrides. Future shared-API review is retained in the decision register. |

Existing HTML table formatting and public node creation/rowchild tests pass
once obsolete `asObjList`, `_getNode`, and `doWithItem` calls are separated out.
A passing table test is evidence about that fixture, not a new API decision.
