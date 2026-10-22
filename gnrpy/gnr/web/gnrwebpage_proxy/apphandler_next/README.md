# apphandler_next

`GnrWebAppHandlerNext` is the application handler of a web page built on
table and database proxies. It is a full copy of the package
`gnr.web.gnrwebpage_proxy.apphandler`, not a subclass: it imports nothing
from it, and the legacy package is frozen.

## Switch

An experimental flag of the instance configuration selects the handler;
nothing else changes.

```xml
<experimental>
    <db next_app_handler="True"/>
</experimental>
```

`GnrWebPage.app` (`gnrwebpage.py`) builds `GnrWebAppHandlerNext` when
`experimentalFlag('db', 'next_app_handler')` is true and `GnrWebAppHandler`
otherwise.

## How to read the copy

`diff -u apphandler/<module>.py apphandler_next/<module>.py` shows, method by
method, only these kinds of hunk:

1. **a block replaced by one call to a proxy** — a block that needed only the
   table and the database now lives on a proxy of the table, reached through
   `tblobj.selectionProxy()`, `tblobj.recordProxy()`, `tblobj.dbSelectProxy()`,
   `tblobj.writeProxy()` (`gnr.app.gnrdbo.TableBase`), or on the proxy of the
   database, `db.structureProxy()` (`gnr.app.gnrapp.GnrSqlAppDb`);
2. **a recorded defect fix** — listed below, each with a test that asserts
   the divergence from the legacy handler;
3. **dead code not ported** — methods with no caller in `gnrpy`, `projects`,
   `resources` and `gnrjs`, listed below;
4. **package identity** — module docstrings and class names.

Everything else is byte for byte the legacy: same order, same names, same
comments. The page enters a proxy only as a parameter or a callable; a proxy
never imports a web page.

## Proxies (`gnr/app/gnrsqltable_proxy/`)

| proxy | module | flows | methods |
|---|---|---|---|
| `SelectionProxy` | `selection.py` | getSelection | 14 |
| `RecordProxy` | `record.py` | getRecord, getRelatedRecord, getRelatedSelection | 13 |
| `DbSelectProxy` | `db_select.py` | dbSelect, tableAnalyzeStore, getValuesString, getMultiFetch | 15 |
| `WriteProxy` | `write.py` | insert, update, save, duplicate, unify, delete, archive, grid changesets | 14 |
| `DbStructureProxy` | `db_structure.py` | getTablesTree, dbStructure | 2 |

Method names are verb + object, with a one line docstring that says what the
method does and what it returns.

`batch.py` and `export.py` have no block that needs only table and database:
they stay copies of the legacy minus the dead methods.

## Defects fixed in the copy

| id | where | legacy | copy |
|---|---|---|---|
| C1 | getSelection | a saved record without `where` hands the whole userobject record to the where decoder | an empty saved where means no filter |
| D2 | getRelatedSelection | the SQL context join condition is destroyed right after it is read, so its applymethod never runs | called once, result merged |

Two defects this copy had fixed on its own, #1359 a and #1359 b on
`getSelection`, were fixed in the legacy handler too by #1375 (`cfdc5bdb8a`).
Ten more followed the same route: #1388 took D4, D7, DS6, DS7 and E10, #1391
took A9, D9, F4, DS5 and D8. All twelve are gone from the table above, and
their cases assert the equivalence rather than the divergence.

What this leaves is the point of the exercise: with the frozen handler
repaired, the copy is a refactoring and nothing else on every flow but the two
in the table above, so turning the switch on changes no behaviour a user can
see.

The two that remain need a decision rather than a patch. D2 restarts an
applymethod that has not run in a long time, so the risk is in the fix. C1 is
latent, because the where decoder finds no condition in the userobject record
and returns an empty WHERE. Issues open on the reproduced ones: #1363, #1364,
#1365.

## Dead code not ported

`getDb` and `__getitem__`, `_getAppId` and `appId`, `dbSelect_selection`,
`rpc_getRecordForm`, `formAuto`, `rpc_batchDo`, `runSelectionBatch`,
`setThermo`, `rpc_getThermo`, `rpc_onSelectionDo`, `export_standard`,
`print_standard`, `rpc_pdfmaker`, `rpc_printStaticGridDownload`,
`getPackages` and `rpc_getPackages`, `getTables` and `rpc_getTables`,
`getTableFields` and `rpc_getTableFields`, `_columnsFromStruct`,
`_externalQueries`. Two of them, `rpc_batchDo` and `dbSelect_selection`, have
callers in application repositories; #1369 decides their fate and that of the
other seventeen.

## Tests (`gnrpy/tests/web/`)

`apphandler_next_common.py` builds one handler of each class on the real
`test_invoice` database (sqlite, and Postgres where a case needs it) with a
stand-in page that offers only the page services the flows use. Every case
sends the same input to both handlers and compares the results; a fixed
defect has a case that asserts the divergence instead.

| module | flows |
|---|---|
| `test_apphandler_next.py` | getSelection |
| `test_apphandler_next_record.py` | getRecord, related |
| `test_apphandler_next_dbselect.py` | dbSelect and siblings |
| `test_apphandler_next_misc.py` | writes, frozen selections, grid, file system |
| `test_apphandler_next_structure.py` | getTablesTree, dbStructure |

```
cd gnrpy && PYTHONPATH=$PWD pytest tests/web/test_apphandler_next*.py -q
```
