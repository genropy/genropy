# Runtime attribute caller migration

Target: explicit Python-style `setAttr(attributes, trigger, merge, removeNull)`
arguments at first-party JavaScript callers. The legacy Bag implementation and
its internal compatibility hooks are not changed by this caller-only pass.

## Decisions

- Widget `_original_attributes` snapshots and whole grid-row attributes replace
  the previous dictionary and retain null fields explicitly.
- Tree checkbox updates, row metadata, datasource widget modifiers, formatting
  metadata and editor changes merge while retaining unrelated null metadata.
  Existing `updAttributes` calls in runtime consumers were converted to explicit
  `setAttr(..., trigger, true, false)` without changing their merge contract.
- Grid remote-edit and programmatic-update initialization preserve null
  `_loadedValue` baselines explicitly after node creation.
- Attribute-mode grid cell editing and HTML checkbox callbacks now pass an
  attribute dictionary, instead of the invalid `(attributeName, value)` form.
- `setSelectedVal` is an explicit partial update. Under the new Node API, null
  removes the selection attribute; tests cover this behavior.
- SlotButton reads its optional command from `_kwargs`, so absence is valid.
- Existing application `updAttributes` helpers handling only non-null values
  remain valid; see `setattr-application-callers.md` for each location.

No first-party consumer uses `'*'` as the third argument or a named
`changedAttr` as the fourth argument. These signatures remain inside the legacy
Bag/compatibility implementation only. This pass does not remove or redefine
those internal hooks, nor apply the separately blocked core node rewrite.

## Verification

- `setattr_runtime_consumers.test.js`: 9 actual runtime consumer regressions,
  including standalone nodes, grid edits, row updates, checkbox callbacks,
  selection attributes and nullable metadata.
- `slotbutton_null_attributes.test.js`: 6 generated-action and external-change
  regressions using raw standalone BagNode and real `funcApply`.
- `original_attributes.test.js`: 3 snapshot restoration regressions across
  legacy, selected and standalone nodes.
- `resources/common/tests/setattr_callers.test.js`: 16 application expressions
  executed against legacy and standalone nodes.

The broader suite has eight previously recorded node/state/event failures;
these are not suppressed or fixed by changing consumers. No server restart,
commit or publication is part of this pass. Repository coverage does not imply
that external applications or arbitrary user-provided scripts were inspected.

## Runtime call-site inventory

- `gnrjs/gnr_d11/js/genro.js:2248:        dataNode.setAttr({'selectedValue':value},true,true);`
- `gnrjs/gnr_d11/js/genro_tree.js:580:                    n.setAttr({'checked':checkedStatus}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_tree.js:583:                    n.setAttr({'checked':false}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_tree.js:585:                    n.setAttr({'checked':checked}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_tree.js:595:        bagnode.setAttr({'checked':checked}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_tree.js:600:                parentNode.setAttr({'checked':this.checkBoxCalcStatus(parentNode)}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_tree.js:831:            n.setAttr({'checked':false}, true, true, false);`
- `gnrjs/gnr_d11/js/genro_wdg.js:1379:            rowData.setItem(colname,n.attr[colname]).setAttr(`
- `gnrjs/gnr_d11/js/genro_wdg.js:1421:                rowEditor.data.getParentNode().setAttr(row_attributes,false,true,false);`
- `gnrjs/gnr_d11/js/genro_wdg.js:1527:                    rowData.setItem(k,row[k]).setAttr({_loadedValue:row[k]},false,true,false);`
- `gnrjs/gnr_d11/js/genro_dom.js:435:                this.setAttr(attributes,true,true);`
- `gnrjs/gnr_d11/js/gnrdomsource.js:1422:                genro.getDataNode(this.absDatapath(valuepath)).setAttr(updattr,true,true,false);`
- `gnrjs/gnr_d11/js/gnrdomsource.js:1426:            this.setAttr(this._original_attributes,true,false,false);`
- `gnrjs/gnr_d11/js/gnrdomsource.js:1444:                        this.setAttr(wdg_modifiers,true,true,false);`
- `gnrjs/gnr_d11/js/gnrdomsource.js:1603:                            valueNode.setAttr({_formattedValue:genro.formatter.asText(valueToFormat, nattr)},this,true,false);`
- `gnrjs/gnr_d11/js/gnrdomsource.js:1660:                this.setAttr(attrdict, this, true, false);`
- `gnrjs/gnr_d11/js/genro_grid.js:290:            container.setAttr({width:(totalWidth+2+'px')},true,true,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:295:                n.setAttr({width:width},true,true,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:1002:            this.structBag.getItem('view_0.rows_0').getNode('#'+inIndex).setAttr({width:inUnitWidth},true,true,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:1603:        bagnode.setAttr(attributes,true,false,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:3155:            editnode.setAttr(attributes,true,true,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:3571:            chNode.setAttr(currAttr,true,true,false);`
- `gnrjs/gnr_d11/js/genro_grid.js:4266:                n.setAttr(newattr,true,true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:3591:                b.getNode(nl).setAttr(updkw,true,true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:4980:                        innernode.setAttr({innerHTML:kw.title},true,true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:7268:        rowNode.setAttr(updDict,{editedRowIndex:idx},true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:7706:                                            editedNode.setAttr({'_loadedValue':objectPop(newattr,attrname)},false,true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:7715:                                        editedNode.setAttr({'_loadedValue':objectPop(newattr,attrname)},false,true,false);`
- `gnrjs/gnr_d11/js/genro_components.js:7720:                        rowNode.setAttr(newattr,true,true,false);`
- `gnrjs/gnr_d11/js/genro_src.js:605:                            valueNode.setAttr(node.evaluateOnNode(specialattr),true,true,false);`
- `gnrjs/gnr_d11/js/genro_widgets.js:6272:            valueNode.setAttr({_formattedValue:formattedValue},sourceNode,true,false);  `
