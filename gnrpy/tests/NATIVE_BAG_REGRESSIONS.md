<!-- Current configuration spelling supersedes historical notes below. -->

The public implementation name and installation extra are `genro-bag`:

```xml
<experimental><bag implementation="genro-bag"/></experimental>
```

Use `implementation="legacy"` or omit the switch for the historical classes.
The old `native` boolean is rejected with a migration message. Runtime
`gnr.BAG_MODE` is either `genro-bag` or `legacy`. Install with
`pip install "genropy[genro-bag]"`. The optional dependency currently has no
minimum constraint: before PR publication/merge it must be pinned to the
compatible release containing the paired changes. No compatible release
number is inferred from the development checkout version.

# Native Bag integration regressions

These tests belong to GenroPy because they exercise its consumers and bootstrap,
not only the standalone Bag API. Run them from the repository root. The tests
create temporary configurations and databases; they do not use the developer's
invoice database, daemon, browser session or checkout-specific paths.

## Prerequisites and execution

Install GenroPy's developer dependencies and the matching native Bag source
revision in the same Python environment. The integration currently depends on
changes in both repositories; an older published native package is not a
substitute for the paired source revision. The dependency/release revision must
be settled before enabling this suite in a clean CI job or merging the PR.
Native cases intentionally fail rather than silently skip when the dependency
is missing or incompatible.

```sh
python -m pip install -e './gnrpy[developer]'
python -m pip install -e "$GENRO_BAG_SOURCE"
PYTHONPATH=gnrpy python -m pytest -q \
  gnrpy/tests/core/test_instance_bag_mode.py \
  gnrpy/tests/core/test_native_bag_ui_regressions.py \
  gnrpy/tests/core/test_native_bag_data_regressions.py \
  gnrpy/tests/web/test_native_bag_runtime_regressions.py
```

`GENRO_BAG_SOURCE` is a checkout selected by the caller, not a baked-in local
path. Bag implementation selection is tested in fresh subprocesses so a cached
import cannot make native tests accidentally exercise the historical classes.

## Failure coverage

| Observed failure or required contract | Regression location |
| --- | --- |
| Login/query failure from unnamed static virtual/composite SQL columns | `test_instance_bag_mode.py`: real temporary SQLite schema, insert and query |
| Historical classes imported despite native opt-in; stale mixin bindings | `test_instance_bag_mode.py`: flags, child process, alternate-name import, mixin overrides and hooks |
| Chat grid lookup returned `None`, then `.attr` failed | `test_native_bag_ui_regressions.py`: actual Dojo `nodeById` |
| Invoice/customer menu HTTP 500 because `rowchild` was missing | UI regressions: actual table-handler menu builder, both tables and privilege branches |
| Product-type form recursion from expanding hierarchical data during frame lookup | UI regressions: actual `includedview_inframe` with a hierarchical resolver that must stay unloaded |
| Resolver callback and XML response protocol | UI regressions: actual page public-method lookup, `resolverRecall`, RPC envelope round trip |
| Selection row and filesystem metadata shape | `test_native_bag_data_regressions.py`: actual SQL selection and file-selection consumers |
| Synchronous configuration lookup inside an active event loop | Data regressions: cold resource configuration loading |
| Explicit textual Dojo version required by URL construction | Runtime regressions: temporary typed XML configuration |
| Unix socket listener and long-path socket discovery | `test_native_bag_runtime_regressions.py` |

The UI fixtures provide page permissions and output sinks but execute the real
GenroPy methods. SQL tests execute actual queries against temporary SQLite
files. These checks do not constitute a complete authenticated browser test,
PostgreSQL-specific coverage or a full GenroPy regression run.

## Verified regression sensitivity

In isolated test subprocesses, without modifying running services:

- Removing `rowchild` fails both native invoice/customer menu cases.
- Restoring the eager `getNodeByAttr` delegation fails with the explicit
  hierarchical-load assertion before exhausting Python's recursion depth.
- Returning `None` from `findNodeByAttr` fails the chat node lookup.
- Restoring `Bag(row)` in `SqlSelection.buildAsGrid` fails the named SQL row test.

These are failure checks, not expected failures in the committed suite. The
ordinary suite must stay green. No production source mutation is required to
run the suite.

## Validation for this change

The four regression files plus the existing `gnrasync_test.py` and
`serverwsgi_test.py` passed together: **49 tests**, with one existing import
deprecation warning. The new regression group accounts for 42 cases.
Flake8 checks matching the repository CI selection, Ruff and diff whitespace
checks passed. No full GenroPy suite or PR publication is claimed by this run.

The secondary recursion while persisting resolver-bearing traceback locals to
`sys.error` has not been fixed or certified by these tests. The product-type
regression covers the original UI lookup failure that triggered that error
handler. Full authenticated browser navigation remains an acceptance step.

## Named tuple constructor follow-up

The paired native Bag now accepts a single `(label, value[, attributes])`
tuple and sequences of node tuples. GenroPy's original SQL virtual-column,
package metadata and filesystem triple constructors have been restored.
Their existing regressions now protect compatibility without requiring those
caller rewrites. A direct package-metadata regression runs in both modes.
The SQL grid row mapping adaptation remains a separate concern.

Verification after this change: the previous switch/data/UI group passed 39
cases; the data group with the two new package-metadata cases passed 8.
The paired native library full suite passed 772 tests.

The SQL grid caller has also been restored to `Bag(row)`: its sequence of named pairs is now accepted by the native constructor. Both native and legacy real SQLite grid regressions pass (2 cases), and selection.py has no remaining diff.

## Directory constructor follow-up

Native Bag now mounts existing directory paths lazily under their basename,
including Path inputs. The historical getGnrConfig implementation is restored;
gnrconfig.py no longer needs a mode-specific branch. The misspelled
_template_kargs option remains ignored with a source, as before.
Real getGnrConfig tests cover .gnr/custom directory names, XML access and an
active event loop in both modes. Data regressions: 12 passed; paired native
full suite: 776 passed. This does not add environment substitution for that
misspelled option.
