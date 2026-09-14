# Application attribute-call migration

Scope: first-party JavaScript in `resources/` and `projects/`, including JavaScript embedded in Python strings. The target Node API is `setAttr(attributes, trigger=true, updattr=true, removeNullAttributes=true)`. Python calls, vendor libraries and generated/minified assets are excluded. The `updAttributes` compatibility helper retains its existing merge-and-preserve-null contract.

## Inventory

The source scan found **24 direct JavaScript call sites**, **10 actual Python call sites** and **one dynamic instrumentation reference**. There are no third-argument `'*'` calls or fourth-argument `changedAttr` expressions among these application callers. The core runtime audit owns such calls outside this directory scope.

**16 call sites in 12 files were updated.** Two callers explicitly replace attributes; fourteen callers merge potentially nullable data. The remaining eight calls use `updAttributes` for non-null literals, counts or a generated string, and remain valid under that helper's retained contract.

| Caller | Decision and source evidence |
| --- | --- |
| `resources/common/gnrcomponents/framegrid.py:813` | Explicit `setAttr(updattr,false,true,false)`. Checkbox/radio data uses `getItem()` and deliberately carries missing values as null; retain silent merge. |
| `resources/common/gnrcomponents/htablehandler.py:456` | Explicit replacement with null retention. The payload is the existing complete attribute dictionary with its caption edited. |
| `resources/common/gnrcomponents/htablehandler.py:845` | Unchanged helper: computed `child_count` is a number, including zero. |
| `resources/common/gnrcomponents/doc_handler/doc_handler.py:86` | Explicit merge/null retention for an editable document title. |
| `resources/common/gnrcomponents/chat_component/chat_component.js:128` | Unchanged helper: `key_from_users` returns a joined string. |
| `resources/common/th/th_tree.js:35` | Unchanged helper: computed `child_count` is numeric. |
| `resources/common/th/th_groupth.js:287` | Explicit merge/null retention for dynamically named aggregate fields copied from incoming rows. |
| `resources/common/th/th_groupth.js:299` | Explicit merge/null retention for the aggregate row and computed totals. |
| `resources/common/th/th_viewconfigurator.js:449` | Explicit merge/null retention for edited column-set properties; preserve `_columnsetsEditor` reason. |
| `resources/common/th/th_viewconfigurator.js:604` | Explicit merge/null retention for edited column properties and nullable group/style values; preserve the supplied reason. |
| `resources/common/th/th.js:446` | Unchanged helper: literal `hiddenPage=false`. |
| `projects/gnrcore/packages/adm/resources/frameindex.js:79` | Explicit merge/null retention for optional iframe metadata (`fullpath`, `subtab`, etc.). |
| `projects/gnrcore/packages/adm/resources/frameindex.js:501` | Explicit merge/null retention for supplied frame title. |
| `projects/gnrcore/packages/adm/resources/frameindex.js:513` | Unchanged helper: literal `hiddenPage=true`. |
| `projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:160` | Explicit merge/null retention: `badgeContent = child_count || null` intentionally clears an empty badge. |
| `projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py:180` | Explicit merge/null retention for the server-provided badge result. |
| `projects/gnrcore/packages/adm/resources/tables/group/th_group.py:137` | Explicit merge/null retention for edited row metadata, including cleared tags. |
| `projects/gnrcore/packages/adm/resources/tables/tblinfo_item/th_tblinfo_item.py:128` | Explicit merge/null retention for edited captions. |
| `projects/gnrcore/packages/adm/resources/tables/tblinfo/th_tblinfo.py:44` | Unchanged helper: record count is numeric. |
| `projects/gnrcore/packages/sys/resources/logging.js:25` | Explicit merge/null retention for editable logging options from a result Bag. |
| `projects/gnrcore/packages/test15/webpages/gnrwdg/bageditor.py:84` | Explicit merge/null retention: the editor passes arbitrary attribute values, including null. |
| `projects/gnrcore/packages/test15/webpages/gnrwdg/menuselect.py:32` | Preserve replacement and autocreation by obtaining the destination Node and explicitly replacing its attributes; retain null values from the selected option. |
| `projects/gnrcore/packages/test/webpages/html/javascript.py:19` | Unchanged helper: literal font size string. |
| `projects/gnrcore/packages/test/webpages/html/javascript.py:61` | Unchanged helper: literal background color string. |

For open-ended metadata dictionaries, explicit null retention preserves the caller's prior result rather than assuming that null and an absent key are interchangeable. This does not claim every individual field has a presence-sensitive consumer.

## Exclusions and dynamic reference

The ten Python calls remain untouched: `resources/common/services/git/gitpython.py:67`, `resources/common/gnrcomponents/htablehandler.py:1054`, `projects/gnrcore/packages/multidb/main.py:552`, `projects/gnrcore/packages/hosting/model/instance.py:46,47`, `projects/gnrcore/packages/docu/resources/docu_components.py:58`, `projects/gnrcore/packages/adm/model/counter.py:298`, `projects/gnrcore/packages/adm/model/preference.py:87`, `projects/gnrcore/packages/adm/resources/prefhandler/prefhandler.py:150`, and `projects/gnrcore/packages/sys/webpages/package_editor.py:107`.

`projects/gnrcore/packages/test/resources/heavy_profiler.js:61` wraps the method by name for instrumentation. Its wrapper forwards the original arguments; it does not introduce a positional contract or require a migration.

Vendor Kinetic code has unrelated `setAttr(name, value)` calls and is excluded. Browser DOM `setAttribute` calls are different APIs. A scan of HTML/template/XML/JSON sources found no additional literal `setAttr`/`updAttributes` references. Runtime-generated method names and application code outside this checkout cannot be proven absent by a static search.

## Verification

`resources/common/tests/setattr_callers.test.js` contains **16 tests**, one for each changed call expression. Each executes the argument expression read from the actual caller against both the real legacy Node and the real standalone Node. The tests verify that explicit null attributes survive and that replacement removes unrelated attributes while merge retains them. All 16 pass.

The test deliberately does not claim complete browser execution of the surrounding components or full notification-envelope equivalence; those belong to the runtime integration and metadata audits. Changed Python files parse successfully, changed JavaScript files pass `node --check`, and the scoped diff passes `git diff --check`.
