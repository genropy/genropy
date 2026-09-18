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

## D22 — Empty-path assignment (supersedes the native merge decision)

Native Python `set_item('', value)` and JS `setItem('', value)` reject empty
paths with ValueError / RangeError, without mutation. Successful native writes
return the written BagNode. Empty-label creation is not restored. Builders must
validate empty identifiers before insertion. Python camelCase `setItem` and the
GenroJS mixin retain legacy empty-path merge and scalar no-op behavior; JS keeps
copied resolvers unresolved. Native and compatibility tests cover these separate
contracts. This corrects the contract introduced in Python 0.24.0 / JS 0.6.0.

## D23 — Sandbox resolver and application compatibility

The sandbox handoff exposed legacy resolver defaults and extra-keyword access.
Native Python now honors `read_only` class defaults, including inherited
declarations. Its names mixin only translates `classKwargs`/`readOnly`.
Explicit constructor overrides win; automatic policy applies only when no
class or constructor policy is set. Both True and False defaults are honored. Its `kwargs` view exposes
extra parameters only, excluding declared defaults and consumed positional
arguments; aliasing it to the entire native `kw` would change menu behavior.
No menu-specific bridge or duplicated SQL constructor defaults are needed.

Application corrections stay with their consumers: PWA configuration reads
XML text explicitly; related-tree SQL retains its original root predicate.
Missing SQL bindings resolve to NULL in the shared execute path (separate
Genropy issue #1341 / PR #1342); the tree workaround is withdrawn.
SQL relation resolvers use `output_mode` for their result format (separate
Genropy issue #1343 / PR #1344); O/M relation metadata retains `mode`.
The two temporary `internal_params` exceptions are removed. Native null-attribute
policy is unchanged. `test_sandbox_bag_regressions.py` covers these consumers
in separate legacy/native processes, and the library tests cover inherited
resolver defaults, explicit overrides and live extra-keyword access.


## D24 — Readonly cache storage is a native contract

Readonly resolution never writes its result to the BagNode. Zero cache reloads
on every read; negative cache retains results in the resolver until invalidation;
positive cache retains results there until TTL expiry. Constructor settings
precede class defaults; class defaults precede automatic policy. Python had
ignored class defaults when choosing storage; the fix belongs in the native
property, not in SQL constructors or the compatibility mixin. JS already respects
class defaults. Tests in both libraries cover inherited defaults, constructor
overrides, the three durations, TTL expiry, reset and unchanged static node values.

## D25 — Resolver parameter preparation belongs to the engine

Native Python removes the `kw` property. Resolver authors keep `load(self)` and
read declared arguments as attributes, with `kwargs` for extras only. The engine
prepares a shallow copy through `on_loading` once per actual load attempt, never
on parameter reads or cache hits. Both pull resolution and explicit refresh use
the same private wrapper. Nested contexts and exceptions restore prior prepared
state; original persistent parameters remain available outside load. Existing
call-time updates remain persistent. No public preparation helper is added.
This supersedes the D23 description of extras as only a compatibility API.
The library migration and tests cover callbacks, concrete resolvers, retry,
refresh, invalid hook returns and nested calls; see its resolver documentation.

## D26 — JS sort direction uses its first character

Both GenroJS legacy Bag and compatibility mixin interpret only the first
trimmed direction character: a/d are case-insensitive, A/D are case-sensitive.
All suffixes, including *, are ignored silently. No Aa/Dd modes are introduced.
The changed meaning of lowercase a/d compared with historical legacy is an
explicitly accepted switch-off difference. This supersedes the star deprecation
warning and any rule letting star force case-insensitive sorting. The native
algorithm still receives canonical modes from the mixin. Regression anchor:
sort_direction_contract.test.js and the sort delegation tests in bag_mixin.test.js.

## D27 — Implicit discovery must not block legacy imports

Automatic instance discovery may select native Bags only from a readable,
unambiguous configuration. Duplicate instance names across project roots do not
block import when all candidates are legacy; normal application startup remains
responsible for instance resolution. If any candidate opts into native Bags,
ambiguity still requires an explicit GNR_INSTANCE_CONFIG. Implicit XML/read errors
are deferred to normal configuration loading. An explicit GNR_INSTANCE_CONFIG
continues to validate its path, XML and implementation switch strictly. Native
selection still propagates the resolved configuration to child processes; legacy
auto-discovery no longer writes that environment variable. Invalid switch values
remain errors. Regression coverage: test_instance_bag_mode.py.

## D28 — RPC parameter interception is transport-gated

GnrWsgiSite.parse_kwargs handles opaque ::RPC names and ::BAGTYTX payloads
specially only when TYTX transport is enabled and its prerequisite switches
validate. With transport absent or xml, every textual parameter follows the
original catalog.fromTypedText path, including custom parsers and standard
catalog exceptions. Tests: test_rpc_legacy_parameter_catalog.py and native
bag_tytx_transport_cases.py (opaque references and incoming Bag round-trip).

## D29 — Legacy compressed JavaScript cache remains site-wide

Pages selecting legacy JS continue to read and populate site.compressedJsPath,
including application overrides and recompression in debug mode. Opt-in mixin
and standalone native pages use a separate cache keyed by ordered asset paths;
they never read or overwrite the legacy URL. Both cache paths can coexist on the
same site regardless of which page loads first. Regression coverage:
gnrbag_javascript_selection_test.py, including both initial request orders,
custom legacy URLs, and debug refreshes.

## D30 — Switch-off audit disposition

The switch-off review explicitly accepts these observed differences; do not reopen
these decisions from the historical audit alone:

- ES class conversion: no external Dojo Bag subclasses found in the indexed
  application code; framework subclasses are already migrated.
- expired is a property: all 11 framework callsites migrated; no application
  method callers found in local projects or Sourcerer symbols/references.
- Sort case modes: accepted under D26.
- RPC parse errors use bag_parse rather than xml_parse: accepted.
- SlotBar copies nodes before removal to avoid skipped consecutive items: accepted.
- StatsPane reverses a copy rather than mutating the Bag order: accepted.
- setSelectedVal preserves unrelated node attributes: accepted.
- changedAttr false versus undefined: leave unchanged for now.

Source-node rebuild is different: legacy nodes must retain setValue(this._value)
and its normal Bag subscriber notifications. Only native nodes keep the current
direct UI trigger. A possible forceTrigger API is deferred; no native Bag contract
change is introduced here. source_rebuild.test.js covers UI behavior in both
modes and legacy subscriber delivery. D27-D29 cover bootstrap, RPC parameter
parsing and compressed asset caches. These accepted exceptions mean this is not
a claim of strict identity with every historical legacy behavior.
