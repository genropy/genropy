# Bag integration decision register

## Historical audit-test removal

Following explicit user instruction, the 12 remaining failing audit tests were
removed, not skipped or converted to passing expectations. The two passing
resolver inventory cases remain. At that checkpoint: 278 tests, 252 passed, zero
failed, 26 pre-existing skips. Runtime code was not changed. R01-R08 remain
recorded findings; test removal does not resolve or accept those differences.
Earlier references below to retained failing tests describe the prior checkpoint.


This is the current decision index for the Python Bag, JavaScript Bag and
Genro compatibility work. It is authoritative for the reconciled audit scope
below, not a claim that every historical API has been audited. Detailed native
contracts remain in each library's BREAKING_CHANGES.md. User instructions take
precedence. Historical audit snapshots are evidence, not current requirements.

## Rules for subsequent work

1. Read this register before presenting a difference or editing a parity test.
2. CLOSED means the decision is settled, not that every implementation is perfect.
   A failing test against a CLOSED contract is a defect or a stale test, not an
   invitation to ask the user to decide again.
3. IMPLEMENTATION means finish an already approved contract. Do not relabel it
   as an open design question merely because the code differs from legacy.
4. REVIEW means evidence or scope is not settled. Check earlier decisions and
   actual callers before requesting a new decision. Missing documentation alone
   does not prove the user has never decided the matter.
5. Reopen a CLOSED decision only on explicit user instruction. Record the old
   ID, new decision and reason; never silently replace it.
6. When closing an item, update this register, the relevant contract document and
   its executable test in the same change. State repository/layer explicitly.
7. Split mixed tests. Preserve valid checks; assert intentional removals. Never
   make a broad exclusion or skip merely to obtain a green suite.
8. Report unique issues by ID, not raw failure counts. Inherited inventory
   failures in Bag/DOM source and node/DOM source node are not separate issues.

9. For remaining differences, verify Sourcerer callers: observed uses are bridged
   in the mixin; no observed uses are documented as breaking changes. This rule
   does not reopen explicitly closed native contracts.

## Closed decisions relevant to the remaining audit

| ID | Decision and scope | Evidence / regression anchor |
| --- | --- | --- |
| D01 | JS mixin does not make inherited methods enumerable. Declaration arity is not a contract test. | javascript-bag-mixin.md; adapter_inheritance.test.js; public operation tests |
| D02 | Shared sum: current level only, strict second, condition third. Invalid types throw in strict mode, otherwise are ignored; selected null/empty gives null in strict mode. | Native BREAKING_CHANGES, Sum; bag_semantics_audit.test.js |
| D03 | JS mixin addItem follows Python collision policy: rename with __dup_N, warn, preserve original XML tag. | javascript-bag-mixin.md, Duplicate labels; addItem tests |
| D04 | Adopt Python attribute update semantics; preserve existing attributes by default, explicit replacement separately. | Native BREAKING_CHANGES, setAttr; bag_semantics_audit.test.js |
| D05 | Formulas and Bag validation removed; do not restore in mixins. | Native BREAKING_CHANGES; bag_accepted_removals.cjs and native validation tests |
| D06 | Resolver-owned getAttr/setAttr removed; BagNode attributes unaffected. | Native BREAKING_CHANGES; accepted-removal test |
| D07 | resolverDescription removed; no implicit resolver execution for display. | Native BREAKING_CHANGES; resolver_compatibility.test.js |
| D08 | GnrBagGetter removed; use explicit callback resolver. | Native BREAKING_CHANGES; accepted-removal test |
| D09 | Bag.doWithItem removed. This does not automatically decide Node.doWithValue. | Native BREAKING_CHANGES; accepted-removal test |
| D10 | backrefOk removed; verify public attach/remove behavior instead. | Native BREAKING_CHANGES; bag_surface_audit.test.js |
| D11 | asObjList removed; asObj compatibility retained. asHtmlTable remains in formatting mixin. | Native BREAKING_CHANGES; bag_surface_audit.test.js |
| D12 | set_modified automatic tracking removed; remaining get_modified is only a reader. | Native BREAKING_CHANGES; bag_surface_audit.test.js |
| D13 | __str__ removed from JS compatibility; native text methods remain. | javascript-bag-breaking-changes.md; bag_surface_audit.test.js |
| D14 | merge/diff future joint evaluation; JS merge absent now. Empty pathsplit placeholder removed. | javascript-bag-breaking-changes.md; bag_surface_audit.test.js |
| D15 | child/rowchild legacy helpers belong only in compatibility mixins, with deprecation; not native Bag API. | Conversation decision; native BREAKING_CHANGES; rowchild tests |
| D16 | htmlRepr included provisionally as optional JS devtools module with separate CSS, not main bundle. No automatic resolver execution. May later be removed by explicit decision. | JS src/devtools; tests/html-repr.test.js. Does not implicitly decide asString/__str2__. |
| D17 | JS resolver mixin must imitate legacy supported behavior. Removed features D05-D09 and approved normalized defaults D20 remain exceptions. | Explicit user instruction: complete imitation in JS mixin; resolver_compatibility.test.js |
| D18 | Legacy pointer grammar belongs in JS mixin. Preserve expressions, selectors, default handling, Deferred, parent and autocreate behavior. | pointer_expression_compat.test.js (8 passing tests) |
| D19 | Public contracts rather than private storage equality. Do not restore _getNode merely for audit tests. | Conversation decision; public insertion/backref tests |

| D20 | Keep normalized no-argument JS resolver defaults: kwargs={}, isGetter=false, absent parent=null, base load=null. No compatibility override. Explicit user approval supersedes the earlier blanket R03 implementation classification. | javascript-bag-breaking-changes.md; resolver_compatibility.test.js |

| D21 | One Bag JS variant per HTML page. Server may serve native, adapted and legacy pages. Compose compatibility in Genro page asset selection; isolate compressed cache by source list. | page-bag-javascript-selection.md; gnrbag_javascript_selection_test.py; test_bag_tytx_transport.py |

The native Python/JS BREAKING_CHANGES contain other settled contracts (sort,
traversal, replacement, paths, cache, etc.). This audit cleanup does not reopen
those contracts and does not duplicate their complete specifications here.

## Active queue after reconciliation

Current executed evidence: [verification checkpoint](bag-verification-checkpoint.md).
Default-mode green alone is not selected-mode green. The latest usage audit
closes V01-V03 as documented below; it introduces no native API decisions.

| ID | Status | Exact remaining work |
| --- | --- | --- |
| R01 | IMPLEMENTED — provisional compatibility; future review retained | JS mixin now merges live parameters into a fresh object at load time, then call-time overrides, including inherited enumerable fields. Constructor no longer flattens defaults. Three differential tests in callback_parameter_compat.test.js pass. Revisit whether inherited fields and live mutable defaults should remain in the future shared API; do not promote this bridge to native libraries without explicit review. |
| R02 | CLOSED — fixed under D17 | JS mixin setParentNode assigns the reference without hook or cache reset, matching legacy. Node.setResolver still invokes the hook. Differential coverage: resolver_parent_hook.test.js (2 tests); full suite 254 passed, 0 failed, 26 existing skips. |
| R03 | CLOSED — accepted difference D20 | Keep normalized defaults; legacy undefined values are not restored. User approved after reviewing the four differences and their effects. Documentation and regression test updated; no runtime change. |
| R04 | CLOSED — accepted breaking | No observed active readers of output metadata; documented omission, input positioning retained. |
| R05 | VERIFIED shared-contract alignment | Python legacy and new both preserve the explicit zero default; native JS and mixin agree. Legacy JS alone returns null. No native defect; do not reopen the shared-equivalence decision. No additional legacy exception has been approved. |
| R06 | CLOSED — accepted breaking | No external JS callers found; __str2__/asString remain absent. |
| R07 | CLOSED — accepted breaking | Missing Bag helpers remain absent; paginated generic set search found no external Bag callers. |
| R08 | CLOSED — accepted breaking | Node toJSONString/doWithValue remain absent; no external callers found. |

R04/R06-R08 are now closed under the usage rule. R05 remains verified shared
behavior. V01/V02 were fixed in the JS mixin; V03 is an accepted breaking
difference. See javascript-bag-breaking-changes.md for evidence and migration.
No unresolved design decision remains in this reconciled queue.

## Historical verification checkpoint

For current results use bag-verification-checkpoint.md.

After test cleanup: 290 tests, 252 passed, 12 failed, 26 existing skips.
The callback test was subsequently strengthened to cover own defaults and both
load/resolve; its failure remains one test. Pointer tests unchanged and passing.
R02 was subsequently fixed and R01 implemented provisionally in the JS mixin; the other entries retain their listed status.
See javascript-bag-test-reconciliation.md for the test cleanup record.

## Runtime regression: explicit source rebuild

`GnrDomSourceNode.rebuild()` must request UI reconstruction even when its
content Bag has not changed. Assigning the same value relied on legacy JS
notifications and left frozen quick-dialog content unbuilt with native Bags.
The source node now calls the source handler explicitly; native data-change
semantics and compatibility mixins are unchanged. The handler still respects
freeze/build guards. `source_rebuild.test.js` verifies legacy and selected
modes, content identity, ancestry, `unfreeze(true)` and frozen rebuilds.
