# Calls to missing GenroJS methods

Scope: gnrjs, resources and projects in this checkout; JS and Python files, including embedded JavaScript. Excludes Bag implementations, tests, minified code and third-party js_libs. Counts are source call occurrences, not runtime execution counts. Computed method names and external applications are outside this static scan.

## Confirmed receiver families

| Missing method | Calls |
| --- | ---: |
| `clearValue` | 46 |
| `addItem` | 46 |
| `getFormattedValue` | 13 |
| `refresh` | 12 |
| `expired` | 9 |
| `parentshipLevel` | 8 |
| `setCallBackItem` | 5 |
| `findNodeById` | 3 |
| `asHtmlTable` | 1 |
| `asObj` | 1 |
| `get_modified` | 1 |
| `moveNode` | 1 |
| `getIndex` | 1 |
| `concat` | 1 |

Total: 14 distinct methods, 148 calls. Receiver classification is based on surrounding source; no claim that every branch executes in test_invoice_pg.

## Occurrences

### addItem

- [gnrjs/gnr_d11/js/genro_wdg.js:1006](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:1006) — `remoteControllerRows.addItem(...)`
- [gnrjs/gnr_d11/js/genro_wdg.js:2068](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:2068) — `filteredStore.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:234](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:234) — `footers.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:412](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:412) — `pane.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:1036](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:1036) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:1038](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:1038) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:1039](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:1039) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:2051](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:2051) — `rowBag.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:4987](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:4987) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:5005](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:5005) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/gnrdomsource.js:1970](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/gnrdomsource.js:1970) — `content.addItem(...)`
- [gnrjs/gnr_d11/js/genro_components.js:4266](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:4266) — `filebag.addItem(...)`
- [gnrjs/gnr_d11/js/genro_components.js:4614](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:4614) — `childItemsPrev.addItem(...)`
- [gnrjs/gnr_d11/js/genro_components.js:4620](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:4620) — `childItemsPost.addItem(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:896](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:896) — `contentBox.addItem(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:5534](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:5534) — `storebag.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dom.js:712](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dom.js:712) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dom.js:735](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dom.js:735) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dom.js:741](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dom.js:741) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dom.js:784](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dom.js:784) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dom.js:802](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dom.js:802) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1119](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1119) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1126](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1126) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1128](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1128) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1133](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1133) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1134](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1134) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1138](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1138) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1142](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1142) — `result.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1155](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1155) — `envelope.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:1175](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:1175) — `local_clipboard.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:3208](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:3208) — `recordLoaded.addItem(...)`
- [gnrjs/gnr_d11/js/genro_frm.js:3367](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_frm.js:3367) — `recordLoaded.addItem(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:438](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:438) — `sources.addItem(...)`
- [gnrjs/gnr_d11/js/genro_google.js:93](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_google.js:93) — `columnsBag.addItem(...)`
- [resources/common/gnrcomponents/framegrid.py:685](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/framegrid.py:685) — `store.addItem(...)`
- [resources/common/gnrcomponents/framegrid.py:699](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/framegrid.py:699) — `store.addItem(...)`
- [resources/common/js_plugins/sheetjs/sheetjs.js:31](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/sheetjs/sheetjs.js:31) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:139](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:139) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:143](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:143) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:148](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:148) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:152](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:152) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:175](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:175) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:176](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:176) — `result.addItem(...)`
- [resources/common/th/th_viewconfigurator.js:329](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:329) — `currColset.addItem(...)`
- [projects/gnrcore/packages/test/resources/grouplets/transforms/payment_data.js:42](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test/resources/grouplets/transforms/payment_data.js:42) — `sourceBag.addItem(...)`
- [projects/gnrcore/packages/test/resources/grouplets/transforms/payment_data.js:44](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test/resources/grouplets/transforms/payment_data.js:44) — `sourceBag.addItem(...)`

### asHtmlTable

- [gnrjs/gnr_d11/js/gnrlang.js:157](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/gnrlang.js:157) — `b.asHtmlTable(...)`

### asObj

- [gnrjs/gnr_d11/js/genro_rpc.js:1053](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_rpc.js:1053) — `).asObj(...)`

### clearValue

- [gnrjs/gnr_d11/js/genro.js:583](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:583) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro.js:1510](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:1510) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_wdg.js:825](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:825) — `rowNode.clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:72](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:72) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:94](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:94) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:110](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:110) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:268](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:268) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:367](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:367) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:777](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:777) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:787](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:787) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:1264](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:1264) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dev.js:1367](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dev.js:1367) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:100](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:100) — `root.clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:293](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:293) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:299](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:299) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:348](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:348) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:382](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:382) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:396](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:396) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:424](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:424) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:529](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:529) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:815](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:815) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:830](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:830) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:845](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:845) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:855](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:855) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:895](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:895) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1015](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1015) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1089](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1089) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1136](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1136) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1252](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1252) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1299](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1299) — `).clearValue(...)`
- [gnrjs/gnr_d11/js/genro_dlg.js:1434](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:1434) — `).clearValue(...)`
- [resources/common/gnrcomponents/timesheet_viewer/timesheet_viewer.js:91](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/timesheet_viewer/timesheet_viewer.js:91) — `).clearValue(...)`
- [resources/common/gnrcomponents/timesheet_viewer/timesheet_viewer.js:424](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/timesheet_viewer/timesheet_viewer.js:424) — `).clearValue(...)`
- [resources/common/gnrcomponents/htablehandler.py:539](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/htablehandler.py:539) — `).clearValue(...)`
- [resources/common/js_plugins/statspane/statspane.js:16](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/statspane/statspane.js:16) — `).clearValue(...)`
- [resources/common/js_plugins/chartjs/chartjs.js:24](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/chartjs/chartjs.js:24) — `).clearValue(...)`
- [resources/common/gnrcomponents/batch_handler/batch_handler.js:48](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/batch_handler/batch_handler.js:48) — `).clearValue(...)`
- [resources/common/gnrcomponents/batch_handler/batch_handler.js:148](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/batch_handler/batch_handler.js:148) — `resultNode.clearValue(...)`
- [resources/common/th/th_viewconfigurator.js:355](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:355) — `).clearValue(...)`
- [resources/common/th/th_querytool.js:226](/private/tmp/genropy-js-bag-integration/resources/common/th/th_querytool.js:226) — `).clearValue(...)`
- [resources/common/th/th_tree.py:393](/private/tmp/genropy-js-bag-integration/resources/common/th/th_tree.py:393) — `).clearValue(...)`
- [projects/gnrcore/packages/test15/webpages/gnrwdg/framepane.py:121](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test15/webpages/gnrwdg/framepane.py:121) — `).clearValue(...)`
- [projects/gnrcore/packages/test15/webpages/gnrwdg/framepane.py:136](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test15/webpages/gnrwdg/framepane.py:136) — `).clearValue(...)`
- [projects/gnrcore/packages/biz/resources/dashboard_component/dashboard_component.js:49](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/biz/resources/dashboard_component/dashboard_component.js:49) — `node.clearValue(...)`
- [projects/gnrcore/packages/test15/webpages/tools/user_store.py:29](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test15/webpages/tools/user_store.py:29) — `rootnode.clearValue(...)`
- [projects/gnrcore/packages/test/webpages/layout/remote.py:33](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test/webpages/layout/remote.py:33) — `pane.clearValue(...)`

### concat

- [gnrjs/gnr_d11/js/genro_components.js:48](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:48) — `content.concat(...)`

### expired

- [gnrjs/gnr_d11/js/genro_wdg.js:1626](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:1626) — `rowDataNode._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_wdg.js:1640](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:1640) — `cellDataNode._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_tree.js:355](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_tree.js:355) — `bagnode._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_tree.js:437](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_tree.js:437) — `).expired(...)`
- [gnrjs/gnr_d11/js/genro_tree.js:582](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_tree.js:582) — `n._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_patch.js:1246](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_patch.js:1246) — `node.item._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_patch.js:1260](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_patch.js:1260) — `node.item._resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:3271](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:3271) — `resolver.expired(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:3362](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:3362) — `resolver.expired(...)`

### findNodeById

- [gnrjs/gnr_d11/js/genro_tree.js:715](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_tree.js:715) — `).findNodeById(...)`
- [gnrjs/gnr_d11/js/genro_src.js:463](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_src.js:463) — `this._main.findNodeById(...)`
- [gnrjs/gnr_d11/js/genro_src.js:514](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_src.js:514) — `genro.src._main.findNodeById(...)`

### getFormattedValue

- [gnrjs/gnr_d11/js/genro.js:1305](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:1305) — `v.getFormattedValue(...)`
- [gnrjs/gnr_d11/js/genro.js:1316](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:1316) — `b.getFormattedValue(...)`
- [gnrjs/gnr_d11/js/gnrlang.js:388](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/gnrlang.js:388) — `value.getFormattedValue(...)`
- [gnrjs/gnr_d11/js/gnrlang.js:1340](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/gnrlang.js:1340) — `value.getFormattedValue(...)`
- [resources/common/gnrcomponents/dynamicform/dynamicform.py:298](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/dynamicform/dynamicform.py:298) — `currdata.getFormattedValue(...)`
- [resources/common/js_plugins/chartjs/chartjs.js:819](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/chartjs/chartjs.js:819) — `row.parameters.getFormattedValue(...)`
- [resources/common/js_plugins/chartjs/chartjs.js:847](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/chartjs/chartjs.js:847) — `b.getFormattedValue(...)`
- [resources/common/th/th_querytool.js:277](/private/tmp/genropy-js-bag-integration/resources/common/th/th_querytool.js:277) — `row.condition.getFormattedValue(...)`
- [resources/common/th/th.js:17](/private/tmp/genropy-js-bag-integration/resources/common/th/th.js:17) — `).getFormattedValue(...)`
- [projects/gnrcore/packages/sys/webpages/test/test_storageTree.py:32](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/sys/webpages/test/test_storageTree.py:32) — `v.getFormattedValue(...)`
- [projects/gnrcore/packages/biz/lib/dashboard.py:253](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/biz/lib/dashboard.py:253) — `wherePars.getFormattedValue(...)`
- [projects/gnrcore/packages/biz/resources/dashboard_items/standard/dash_tableviewer.py:43](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/biz/resources/dashboard_items/standard/dash_tableviewer.py:43) — `wherePars.getFormattedValue(...)`
- [projects/gnrcore/packages/test/webpages/gnrwdg/dynamicform.py:74](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/test/webpages/gnrwdg/dynamicform.py:74) — `rec.getFormattedValue(...)`

### getIndex

- [gnrjs/gnr_d11/js/genro_google.js:44](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_google.js:44) — `data.getIndex(...)`

### get_modified

- [gnrjs/gnr_d11/js/genro_dlg.js:40](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_dlg.js:40) — `).get_modified(...)`

### moveNode

- [gnrjs/gnr_d11/js/genro_grid.js:2146](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:2146) — `storebag.moveNode(...)`

### parentshipLevel

- [gnrjs/gnr_d11/js/genro_wdg.js:2262](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:2262) — `kw.node.parentshipLevel(...)`
- [gnrjs/gnr_d11/js/genro_wdg.js:2335](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_wdg.js:2335) — `kw.node.parentshipLevel(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:2957](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:2957) — `kw.node.parentshipLevel(...)`
- [gnrjs/gnr_d11/js/genro_components.js:2644](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:2644) — `item.parentshipLevel(...)`
- [gnrjs/gnr_d11/js/genro_components.js:3456](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_components.js:3456) — `kw.node.parentshipLevel(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:782](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:782) — `kw.node.parentshipLevel(...)`
- [resources/common/js_plugins/statspane/statspane.py:493](/private/tmp/genropy-js-bag-integration/resources/common/js_plugins/statspane/statspane.py:493) — `_node.parentshipLevel(...)`
- [resources/common/gnrcomponents/grouplet/grouplet_grid.js:1205](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/grouplet/grouplet_grid.js:1205) — `kw.node.parentshipLevel(...)`

### refresh

- [gnrjs/gnr_d11/js/genro_grid.js:3324](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:3324) — `storeParent.refresh(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:5697](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:5697) — `sourceNode.refresh(...)`
- [gnrjs/gnr_d11/js/genro_widgets.js:5706](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_widgets.js:5706) — `sourceNode.refresh(...)`
- [resources/common/gnrcomponents/htablehandler.py:486](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/htablehandler.py:486) — `).refresh(...)`
- [resources/common/gnrcomponents/htablehandler.py:841](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/htablehandler.py:841) — `n.refresh(...)`
- [resources/common/gnrcomponents/htablehandler.py:849](/private/tmp/genropy-js-bag-integration/resources/common/gnrcomponents/htablehandler.py:849) — `n.refresh(...)`
- [projects/gnrcore/packages/sys/lib/services/ftp.py:139](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/sys/lib/services/ftp.py:139) — `kwargs._dropnode.refresh(...)`
- [projects/gnrcore/packages/sys/lib/services/ftp.py:148](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/sys/lib/services/ftp.py:148) — `kwargs._dropnode.refresh(...)`
- [resources/common/th/th_tree.js:31](/private/tmp/genropy-js-bag-integration/resources/common/th/th_tree.js:31) — `n.refresh(...)`
- [resources/common/th/th_tree.js:39](/private/tmp/genropy-js-bag-integration/resources/common/th/th_tree.js:39) — `n.refresh(...)`
- [projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:97](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:97) — `).refresh(...)`
- [projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:153](/private/tmp/genropy-js-bag-integration/projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:153) — `n.refresh(...)`

### setCallBackItem

- [gnrjs/gnr_d11/js/genro.js:940](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:940) — `genro._data.setCallBackItem(...)`
- [gnrjs/gnr_d11/js/genro.js:948](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro.js:948) — `parentGenroData.setCallBackItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:815](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:815) — `controllerData.setCallBackItem(...)`
- [gnrjs/gnr_d11/js/genro_grid.js:1031](/private/tmp/genropy-js-bag-integration/gnrjs/gnr_d11/js/genro_grid.js:1031) — `gridData.setCallBackItem(...)`
- [resources/common/th/th_viewconfigurator.js:108](/private/tmp/genropy-js-bag-integration/resources/common/th/th_viewconfigurator.js:108) — `gridData.setCallBackItem(...)`

## Remaining names

| Name | Textual calls | Assessment |
| --- | ---: | --- |
| `__str2__` | 0 | No direct calls found |
| `__str__` | 0 | No direct calls found |
| `_deepIndex` | 0 | No direct calls found |
| `_getNode` | 0 | No direct calls found |
| `_insertNode` | 0 | No direct calls found |
| `_nodeFactory` | 0 | No direct calls found |
| `_setModified` | 0 | No direct calls found |
| `_toXmlBlock` | 0 | No direct calls found |
| `asNestedTable` | 0 | No direct calls found |
| `asObjList` | 0 | No direct calls found |
| `asString` | 0 | No direct calls found |
| `backrefOk` | 0 | No direct calls found |
| `cancelMeToo` | 0 | No direct calls found |
| `contains` | 9 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `defineFormula` | 0 | No direct calls found |
| `defineSymbol` | 0 | No direct calls found |
| `digest` | 45 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `doWithItem` | 0 | No direct calls found |
| `doWithValue` | 0 | No direct calls found |
| `formula` | 0 | No direct calls found |
| `getAttr` | 76 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `getIndexList` | 2 | Python calls only |
| `getValue2` | 0 | No direct calls found |
| `htraverse` | 0 | No direct calls found |
| `items` | 179 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `keys` | 130 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `len` | 202 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `meToo` | 0 | No direct calls found |
| `merge` | 0 | No direct calls found |
| `newNode` | 0 | No direct calls found |
| `onNodeTrigger` | 0 | No direct calls found |
| `orphaned` | 0 | No direct calls found |
| `pathsplit` | 0 | No direct calls found |
| `resolverDescription` | 0 | No direct calls found |
| `rowchild` | 25 | Python calls only |
| `runPendingDeferred` | 0 | No direct calls found |
| `runTrigger` | 0 | No direct calls found |
| `set` | 4 | Other receivers: Map/editor/shared_data |
| `setAttr` | 57 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `setParent` | 1 | Python calls only |
| `setParentNode` | 0 | No direct calls found |
| `set_modified` | 0 | No direct calls found |
| `sum` | 9 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |
| `toJSONString` | 0 | No direct calls found |
| `toXmlBlock` | 0 | No direct calls found |
| `values` | 68 | Found on Bag/BagNode or other objects, not established on a resolver (where the method is missing) |

The full candidate list, including excluded receiver matches, is in mixin-missing-callsites.json. `expired` exists as a property in the new resolver, but the nine calls use method syntax; these remain incompatible. The two absent classes GnrBagFormula and GnrBagGetter are separate from the method counts.
