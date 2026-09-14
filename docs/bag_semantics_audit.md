# Bag semantic compatibility audit

Compared the complete own callable surface of legacy `GnrBag` against the adapter and inherited standalone implementation. The surface audit separately inventories missing names and browser consumers; the resolver audit owns Node and resolver contracts. This report does not equate a method name match with semantic compatibility.

## Result

`bag_semantics_audit.test.js`: 33 differential scenarios, 30 passing and 3 failing pending the separately blocked Node correction. Each scenario executes the same source in independent legacy and selected VM contexts. No failing assertion was removed or weakened.

Confirmed differences corrected include digest result shape and columns signature; strict sums; sort aliases/case/null ordering; recursive dictionary conversion; duplicate insertion and numeric zero position; empty-path merge; lazy/fired flags; deletion trigger suppression; recursive update flags; copy behavior; traversal callback arguments and early termination; fill behavior; attribute autocreation; identity equality; XML envelopes; search precedence; live node access; and deletion event metadata.

## Remaining failing scenarios

- Pure attribute event: selected `updvalue=false`, legacy omits the key.
- Orphaned node: selected `getParentBag()` returns null, legacy returns undefined.
- Update with unchanged attributes: selected suppresses the attribute event; legacy emits it, so reason delivery differs.

These are owned by the Node audit; no alternate Bag workaround was applied after approval review blocked that patch.

## Complete member classification

“Surface audit” identifies methods newly restored by the parallel full-surface review; those results must be read with its report and tests. A source review is not claimed as exhaustive execution of every branch.

| Legacy member | Evidence and disposition |
| --- | --- |
| `constructor` | Reviewed adapter initialization and XML entry point; existing bootstrap/XML tests. XML extension kwargs are not exhaustively exercised. |
| `_nodeFactory` | Specialized node constructor retained; existing DomSource subclass test. |
| `newNode` | Same constructor argument order; source subclass tests. |
| `fillFrom` | Differential: merge, object rows, nested Bags, autolist. Standalone parsed Bags are converted into adapter children. |
| `getParent` | Differential: root absence retained. |
| `setParent` | Reviewed direct parent assignment; linked-tree tests. |
| `setParentNode` | Reviewed alias synchronization; topology also depends on blocked Node changes. |
| `getParentNode` | Reviewed alias getter; linked-tree tests. |
| `attributes` | Differential: root absence retained. |
| `resolver` | Differential: root absence retained. |
| `asHtmlTable` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `asNestedTable` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `getFormattedValue` | Restored full formatting dispatch, including HTML/nested/table flags; helpers covered by surface audit. Formatting combinations remain broader than runtime cases. |
| `getItem` | Reviewed defaults, mode and optkwargs propagation; existing Deferred and attribute-path tests. |
| `sort` | Differential: all eight legacy order/case aliases, nulls and nested fields. |
| `sum` | Differential: numeric/boolean inclusion, string exclusion, strict-null mode. |
| `get` | Restored legacy index lookup and suffix handling; differential #=id lookup; existing attribute/query tests. |
| `htraverse` | Reviewed traversal, escaping, parent paths and Deferred chaining; existing async relation test. Invalid paths beyond root remain a legacy edge case. |
| `len` | Reviewed direct length alias; clear and construction tests. |
| `__str2__` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `__str__` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `asString` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `keys` | Reviewed inherited container ordered-label mapping; duplicates/order tests. |
| `values` | Reviewed inherited container dynamic getValue mapping; duplicate and resolver tests. |
| `items` | Differential: named key/value entries rather than tuples. |
| `digest` | Differential: row shape, columns flag, nested fields and static token semantics via restored algorithm. |
| `columns` | Differential: attribute prefix and transpose signature. |
| `asObj` | Reviewed resolver marker and formatting mapping; existing tests. |
| `asObjList` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `getResolver` | Restored legacy node lookup and absent-node behavior; resolver suite. |
| `getNodes` | Differential: live container identity and filtered list. Raw container method coverage belongs to surface audit. |
| `pop` | Differential suppression and missing return; orphan parent absence test remains blocked on Node. |
| `delItem` | Differential no-value return and suppression. |
| `moveNode` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `popNode` | Differential suppression/orphan semantics; root parent absence remains blocked on Node. |
| `_pop` | Reviewed copy-on-removal and notification path; existing consecutive-removal source test. |
| `clear` | Differential reverse removal, event indices, absence of invented reason; existing source clear test. |
| `merge` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `update` | Differential null replacement, mode, attribute merge, replace marker and reasons; unchanged-attribute notification count remains blocked on Node. |
| `concat` | Reviewed node transfer/reparent and absence of notification; existing source tests. |
| `deepCopy` | Differential duplicate retention and nested independence; static/dynamic switch restored from legacy algorithm. Resolver behavior also covered by resolver audit. |
| `getNodeByAttr` | Differential depth-first precedence and existence-only matching; restored legacy traversal. |
| `getNodeByValue` | Differential nested field traversal. |
| `getNode` | Differential query suffix, attribute index lookup, missing tuple shape; existing caption regression. |
| `_getNode` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `setAttr` | Differential autocreation and replacement semantics. |
| `getAttr` | Differential absence/default and attribute retrieval. |
| `pathsplit` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `asDict` | Differential recursive/flat, null exclusion, automatic lists and JS-tagged text omission. |
| `addItem` | Differential duplicate labels and insertion flags. |
| `fireItem` | Differential fired flag/value reset; exact attr-event envelope remains blocked on Node. |
| `rowchild` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `setItem` | Differential empty-path merge, query attributes, lazySet/fired, duplicate and numeric zero position. Existing Deferred and source tests. |
| `set` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `_insertNode` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `index` | Reviewed ordinal, label and typed attribute-index parsing; differential lookup/order tests. |
| `findNodeById` | Restored legacy early-exit static walk. |
| `forEach` | Differential kwargs/index order and early return. |
| `walk` | Differential callback args, static mode, continue sentinel and early exit; existing recursive source tests. |
| `getBackRef` | Reviewed direct backref getter; differential clear tests. |
| `hasBackRef` | Reviewed boolean backref getter. |
| `setBackRef` | Reviewed adapter alias and child propagation; final topology evidence also depends on blocked Node patch. |
| `clearBackRef` | Differential retained node ownership and recursive child flags; both internal parent-node aliases cleared. |
| `backrefOk` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `runTrigger` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `onNodeTrigger` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `subscribe` | Reviewed callback aliases and automatic backref enablement; differential event tests. |
| `unsubscribe` | Reviewed whole-subscriber deletion mapping; surface notification test. |
| `fromXmlDoc` | Reviewed Document/element/string handling, declared child classes, typed attrs and resolver metadata. Existing XML fixtures cover populated branch metadata; all XML resolver-description variants are not exhaustively executed. |
| `toXml` | Differential GenRoBag envelope and legacy dtype encoding; restored legacy Node serialization dispatch. |
| `toXmlBlock` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `formula` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `defineSymbol` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `defineFormula` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `setCallBackItem` | Reviewed legacy callback/parameters kwargs construction; resolver audit owns execution. |
| `get_modified` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `set_modified` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `_setModified` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `getRoot` | Reviewed recursive parent root selection; linked-tree tests. |
| `getFullpath` | Reviewed label/#/## paths and explicit/true root handling; existing duplicate-label path tests. |
| `getIndex` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `isEqual` | Differential identity semantics and null input. |
| `_deepIndex` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `getIndexList` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |
| `delParentRef` | Reviewed inherited parent/backref reset matching legacy. |
| `doWithItem` | Restored/reviewed by surface audit; see its method-level inventory and differential tests. |

## Explicit limits

- All 86 own callable members are classified above; this is an API inventory and targeted semantic audit, not proof for every possible application input.
- Inherited `Object.prototype` behavior also needs attention: the new superclass introduces a tree-rendering `toString()`, whereas legacy Bags stringify as `[object Object]`. This addition is documented for explicit disposition rather than silently called compatible.
- Raw `_nodes`/`getNodes()` container methods are reviewed by the surface audit. The live container is a facade, not an actual Array; `Array.isArray()` and direct numeric assignment cannot be treated as equivalent without separate decisions.
- XML resolver metadata, browser-specific formatting and unknown external applications require integration coverage beyond finite unit scenarios.
- Compatibility methods retain legacy algorithms where changing a call signature alone cannot reproduce behavior. This deliberately increases adapter code; the standalone package still supplies storage and reusable primitives.
