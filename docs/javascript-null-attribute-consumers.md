# Null attribute consumer audit

Scope: runtime files under `gnrjs/gnr_d11/js`, excluding the legacy/adapter Bag implementations and generated browser bundle. The scan covered explicit attribute-presence checks, attribute enumeration, generated function arguments, and literal null producers. Presence-sensitive checks are not automatically bugs: with the new contract, setting null deletes an attribute, so absent-attribute defaults intentionally apply.

## Corrected consumers

- `SlotButton.createContent`: the generated button action reads `_kwargs.command` and normalizes absence to null, instead of referencing a local `command` argument whose declaration depended on a retained null attribute. Dynamic command values continue to arrive through evaluated kwargs.
- `Selection.checkExternalChange`: both changed and unchanged field branches explicitly call `setAttr({_loadedValue: ...}, false, true, false)`. Here null is required data: it records the server baseline of an edited field. Deleting this marker loses the distinction between a clean field and an edit from a null baseline.

`slotbutton_null_attributes.test.js` executes the real component methods with raw standalone `BagNode` instances using the new null-removal default. It compiles and executes generated actions through the actual `funcApply`, covers absent/null/literal/dynamic commands, and exercises both external-change branches while checking that local edits and unrelated field metadata survive.

## Additional routed consumers

The two grid edit-row producers in `genro_wdg.js` construct field nodes with `_loadedValue` metadata. These also require explicit retention of null baselines. The marker is subsequently tested by presence in `genro.js`, `genro_frm.js`, and `genro_wdg.js`; direct writes to `node.attr._loadedValue` already retain null.

## Generated functions

`funcApply` and `GnrDomSourceNode.currentFromDatasource` derive function parameter names from existing attribute keys. Generic downstream code cannot recover a deleted parameter name. Runtime-generated SlotButton code now uses the stable `_kwargs` object for its optional parameter. Application-provided expressions that intentionally rely on null-valued attributes must either retain those attributes explicitly or use a kwargs lookup/default; this audit does not assert compatibility for unknown application scripts.

## Intentional absence defaults

The runtime contains presence checks where null deletion changes behavior by design: `visible`, `checked`, `canSort`, `editorEnabled`, `inherithLock`, `inheritProtect`, `child_count`, `pivotYear`, `sync`, placeholder/display metadata and optional widget bindings. A caller intending false or zero must pass false or zero, rather than null. No literal runtime null producers were found for those disabling flags. Direct options objects, local variables and API result objects containing null do not pass through Bag attribute storage and need no change.

The reviewed static inventory included 104 matches for attribute-presence/enumeration patterns and 67 literal-null pattern matches (including ternary expressions and ordinary local objects). These counts describe scan coverage, not 171 independently verified runtime flows. Browser-wide and unknown application coverage cannot be inferred from them.
