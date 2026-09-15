# GnrBagNode legacy compatibility audit

> Historical audit of the removed reserve adapter. This document does not describe the active mixin or a supported runtime path.

Baseline: `gnrjs/gnr_d11/js/gnrbag.js` on the integration branch. Selected
implementation: `GenroBagJS.BagNode` plus `gnrbag_genro.js`. Evidence is in
`gnrjs/tests/bagnode_legacy_audit.test.js`, the existing selected-mode tests,
and repository call-site searches excluding vendored libraries.

## Construction and fields

| Contract | Classification | Evidence |
| --- | --- | --- |
| Five constructor arguments and `#id` label generation | matched | differential constructor test |
| Resolver constructor ignores the supplied value | matched | differential constructor test |
| `_id`, `locked`, `_onChangedValue`, `_resolver`, `_value`, `label` | matched | constructor test and runtime surface inspection |
| `_parentbag` direct legacy field | matched | adapter `parentBag` setter keeps `_parentBag` and `_parentbag` synchronized; direct callers exist in `genro_wdg.js` and `gnrdomsource.js` |
| `attr` writable reference | matched | adapter getter/setter and component `_beforeCreation` regression |
| Direct resolver node starts with `_status == 'loaded'` | blocked mismatch | legacy says `loaded`; selected says `unloaded`; differential test fails |
| Orphan parent getters | blocked mismatch | legacy returns `undefined`; selected returns `null`; differential test fails |
| Extra standalone fields (`_attr`, `_compiled`, `_invalidReasons`, `_nodeSubscribers`, `nodeTag`, `xmlTag`) | compatible extension | no legacy caller collision found |

## Methods

Every legacy method is present, enumerable, and has matching declared arity.
The surface test checks this list directly.

| Members | Classification | Evidence |
| --- | --- | --- |
| `getStringId`, `getStaticValue`, `setStaticValue` | matched | direct implementation review; identity tests |
| `isExpired`, `isLoaded`, `isLoading`, `refresh`, `resetResolver` | matched except constructor status above | differential lifecycle test; resolver suite |
| `getParentNode`, `getParentBag`, `setParentBag`, `getFullpath`, `backrefOk` | matched except orphan nullability above | path, menu round-trip, nested backref tests |
| `orphaned` | graph behavior matched; return nullability blocked | differential ancestry/orphan test |
| `isChildOf`, `isAncestor`, `isDescendant`, `parentshipLevel` | matched | differential graph test and real `GnrFrmHandler.isNodeInFormData` test |
| `getValue`, `getValue2` | matched for static, getter, cached, expired, reload, concurrent Deferred and loaded-node cases | selected resolver tests; `getValue2` arity restored |
| `setValue`, `clearValue` | blocked mismatches | selected clears value when `fired`, returns the node, omits `_onChangedValue`, retains old Bag backrefs, and suppresses unchanged attribute events; fail-before evidence recorded below |
| `setResolver`, `getResolver` | matched for parent hook and reset surface | resolver construction/inheritance tests |
| `getAttr`, `hasAttr`, `getInheritedAttributes`, `attributeOwnerNode` | matched | differential truthy-default test; FORM alternative and inheritance-boundary tests |
| `replaceAttr`, `setAttribute`, `updAttributes`, `setAttr`, `delAttr` | matched for mutation/default/remove-null behavior | differential attribute test and event-envelope tests |
| Pure-attribute event `updvalue` field | blocked mismatch outside node block | legacy omits it; selected emits `false`; `bag_semantics_audit.test.js` |
| `getFormattedValue` | matched including `_autoTable`, joiner, and omit-empty defaults | differential formatting test |
| `_toXmlBlock` | matched | differential XML test; required by `GnrBag.toXmlBlock` |
| `toJSONString` | surface matched | both require the application-provided `Object.prototype.toJSONString`; isolated harness verifies the same failure without that application extension |
| `doWithValue` | matched for synchronous and Dojo Deferred values | existing resolver Deferred tests and implementation review |

No external call sites were found for `getValue2`, `backrefOk`, `replaceAttr`,
or node `toJSONString`; they remain part of the public legacy surface. Active
callers were found for ancestry, resolver fields, `_parentbag`, formatting,
refresh, XML serialization, attribute mutation, and value mutation.

## Blocked core correction

Fail-before differential output demonstrates:

```text
legacy:   value=2, return=undefined, callback before event, fired=true
selected: value=null, return=GnrBagNode, no callback, fired=true
legacy replaced child Bag hasBackRef=false
selected replaced child Bag hasBackRef=true
```

The proposed correction must preserve legacy ordering: normalize resolver or
node input; assign the value and attributes; call `_onChangedValue`; detach the
old Bag and attach the new Bag; then emit one parent update containing `fired`.
It must return `undefined` and must not clear the stored value for `fired`.
Automatic approval review rejected applying this core rewrite pending explicit
approval because of its runtime reach.

## GnrDomSourceNode inherited compatibility (read-only)

Runtime prototype inventory confirms that every `GnrBagNode` member above is
visible on `GnrDomSourceNode`. Its own constructor still delegates all five node
arguments. Active inherited calls include `getParentNode`, `_parentbag`,
`getValue`, `setValue`, resolver access, attributes, ancestry, formatting,
refresh, and `_toXmlBlock`. Therefore the blocked `setValue` event/backref
differences also affect DomSource nodes. No missing inherited method remains;
this audit did not edit `gnrdomsource.js`.
