# Bag verification checkpoint

Executed on 2026-09-17 after the usage-based compatibility audit. This records
executed checks, not complete application coverage. Decisions remain in
bag-decision-register.md; old reports do not reopen them.

## Executed JavaScript modes

```
node --test gnrjs/tests/*.test.js
GNR_JS_BAG=genro-bag-js-mixin node --test gnrjs/tests/*.test.js
```

| Mode | Total | Passed | Failed | Skipped |
| --- | --- | --- | --- | --- |
| Default | 284 | 258 | 0 | 26 |
| Explicit mixin | 284 | 284 | 0 | 0 |

The second command is mandatory. The 26 default skips are the existing
selected-mode scenarios, all executed successfully in explicit mixin mode.
No test was deleted or newly skipped by this audit. git diff --check passed.
Local logs: /private/tmp/usage-audit-default.log and
/private/tmp/usage-audit-mixin.log.

## Reconciled findings

| ID | Resolution |
| --- | --- |
| V01 | XML constructor restored in JS mixin using its existing typed decoder and class dictionary. Scalar imported resolvers remain unloaded until read; populated branches retain cached values. Three XML scenarios pass. The test harness now supplies the framework expression evaluator required by the existing decoder. |
| V02 | Legacy ancestor lookup and inheritance boundary implemented in node mixin. FORM alternatives, case-insensitive tag lookup and stopInherite consumers confirmed. Existing ancestry test passes. |
| V03 | No demonstrated reliance on silent missing positional targets. Throwing on absent #n is documented and asserted as an accepted breaking change; valid positional updates remain supported. |
| R01 | Callback parameter bridge implemented provisionally; future shared-API review remains a follow-up, not a release implementation gap. |
| R02 | Parent reference assignment hook compatibility fixed and covered. |
| R03 | Normalized resolver defaults explicitly accepted under D20. |
| R04 | No active metadata consumers found. _new_label/_new_position omission documented; label/order behavior remains tested. |
| R05 | Explicit zero attribute default agrees with both Python implementations and native JS. No new defect. |
| R06-R08 | No external JS Bag uses found for the listed missing helpers. Accepted breaking changes and executable removal registry updated. Generic set search was paginated and attributed to unrelated receivers or legacy internals. |

Detailed caller evidence, exclusions and migration notes are in
javascript-bag-breaking-changes.md. Searches cover indexed source, not unindexed
applications or computed/dynamic method references. No native-library files
were changed during this audit. The reconciled queue contains no open design
decision.

## Other validation and remaining release work

Previously executed page asset selection/bootstrap tests: 11 passed.
Previously executed TYTX transport tests: 16 passed.
Native browser bundle loads without gnr namespace or rowchild compatibility.
Same-server page selection has unit coverage; real-server browser acceptance of
legacy, adapted and custom native pages remains outstanding. Clean package
installation and final three-repository release checks remain outstanding.
No commit, push or release was performed during this audit.

## Release preparation follow-up

Full native library suites executed against the working checkouts:

- Python: **921 passed**, 42 warnings, zero errors. The source directory must be
  on PYTHONPATH; the installed package is older. HTTP fixture binding requires
  permission outside the restricted sandbox. The restricted run had 23 fixture
  errors, all resolved by rerunning with local socket permission.
- JavaScript: **692 passed**, zero skipped/failed.
- Page asset selection: **11 passed**; TYTX transport: **16 passed**.
- New page-selection/frontend modules: flake8 passed.

Local Python wheel and npm tarball built successfully. Archive inspection
confirmed Python compatibility modules and JS main/devtools/CSS entry files;
node_modules and tests are not shipped in the npm package. These are local
builds of the current versions, not published releases or clean-install proof.
Artifacts: /private/tmp/bag-release-artifacts.

Runtime inspection: ports 8094/8095 have no listener. Current PathResolver finds
the test_invoice_pg instance but cannot resolve its site: the instance-local
root.py required by the current resolver is absent. No private configuration
was changed. Real-server acceptance must first restore an isolated site startup
pointing at this worktree and then exercise legacy/adapted/native pages.
Clean dependency installation, full release lint and commit/version/publication
steps remain outstanding. No version bump or publication was performed here.

## Pre-push verification

The complete Genropy Python suite was run both on this checkout and on an
unmodified archive of its parent commit c646a2e30, with the same interpreter and
restricted environment:

| Checkout | Passed | Failed | Errors | Skipped |
| --- | --- | --- | --- | --- |
| Integration changes | 1724 | 56 | 831 | 10 |
| Parent baseline | 1719 | 57 | 831 | 10 |

Comparing failed/error test IDs found **no new failures or errors**. Baseline
app-insights failed only in the baseline run; this is not claimed as a fix.
These runs expose existing environment/package issues, including blocked local
sockets and the older installed Bag package. They are not a green full-suite
claim. Logs: /private/tmp/push-genropy-full.log and
/private/tmp/push-genropy-baseline.log.

With the current Python Bag source on PYTHONPATH, all **58** targeted Python
integration tests passed (instance selection, import guards, SQL/UI regressions,
legacy XML, child/walk compatibility and retired features). All modified Python
integration files and tests passed flake8; Python Bag changes passed ruff;
JavaScript syntax checks passed. The previously recorded JS and transport
suite results remain applicable.

Library checkpoints pushed before the integration commit:
- genro-bag: bef0a96, codex/direct-xml-indentation; pre-push 921 tests passed.
- genro-bag-js: af047cd, codex/direct-xml-indentation; pre-push 692 tests passed.

Version numbers and release tags have not changed. Browser acceptance and
clean dependency-install verification remain release follow-ups.

## Versioned distribution checkpoint

Released library versions: genro-bag 0.24.0 (5702141) and genro-bag-js 0.6.0
(00696e0). Genropy now requires genro-bag>=0.24.0,<0.25 in its optional extra
and embeds the 0.6.0 JS bundle with its regenerated source map.

The versioned distributions were rebuilt and validated: Python 921 tests,
JavaScript 692 tests, integration JS 284 selected-mode tests and 16 TYTX
transport tests passed. Clean wheel installation with declared dependencies
and clean npm tarball installation both passed import/value smoke checks;
the optional JS devtools import and htmlRepr were verified as well.

Genropy remains on genro_integration: no Genropy package release tag was
created. Real-server application/browser acceptance remains outstanding.
