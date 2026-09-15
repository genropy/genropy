# Standalone Bag integration regressions

The instance setting is `<experimental><bag implementation="genro-bag"/></experimental>`.
Omitting it or using `implementation="legacy"` retains the historical classes.
The previous experimental `native` boolean is rejected explicitly.

## Running the tests

Install the GenroPy developer dependencies and the corresponding standalone Bag
source revision into the same environment. From the repository root:

```sh
python -m pip install -e './gnrpy[developer]'
python -m pip install -e "$GENRO_BAG_SOURCE"
PYTHONPATH=gnrpy python -m pytest -q \
  gnrpy/tests/core/test_instance_bag_mode.py \
  gnrpy/tests/core/test_native_bag_ui_regressions.py \
  gnrpy/tests/core/test_native_bag_data_regressions.py
```

`GENRO_BAG_SOURCE` is useful only when developing the library itself. For
release validation install `genro-bag==0.23.0` from PyPI instead of the editable
source. The optional extra requires `genro-bag>=0.23.0,<0.24`. The published
release contains the constructor, synchronous resolver and legacy adapter
changes exercised here. Tests fail rather than skip if it is unavailable.

## Coverage

- Fresh-process implementation selection, configuration errors, child-process
  inheritance and historical file import blocking.
- Real class identity across mixins, preserved application overrides, rejection
  of stale references, canonical export recovery and unsupported reload.
- Real SQLite schema creation, insert/query, virtual/composite column names,
  default grid row labels and record resolvers.
- Actual Dojo chat node lookup, invoice/customer menu construction, and frame
  lookup that must not expand hierarchical data.
- Actual page resolverRecall dispatch and RPC XML response round-trip.
- Actual file-selection handler and resolver with temporary storage fixtures.
- Actual cold configuration lookup inside an event loop, directory constructor
  compatibility and package metadata tuples.

Subprocesses isolate the implementation choice. Fixtures do not depend on a
private instance, live daemon, development PostgreSQL database, browser session,
or absolute checkout paths. Page permission fixtures and output sinks isolate
UI infrastructure; SQL operations execute against actual temporary databases.

The suite is bounded consumer coverage, not a full authenticated browser run
or proof of every historical export. Socket fixes and their regression tests
belong to a separate change. Arbitrary dynamic imports, transactional rollback
of mixin hook side effects, and all resolver-bearing traceback persistence paths
are outside the guarantee.

## Review validation

On the clean develop-based delivery branch, the final focused group passed 49
tests. The full suite reported 1,817 passed, 10 skipped and 751 setup errors;
all setup errors came from PostgreSQL initdb being unable to allocate shared
memory on the host. The unchanged base fixture reproduced the same failure.
The final focused run includes three bootstrap checks added after the full run
started. Rerun the full suite in a functioning PostgreSQL test environment.

Published-package validation: all 49 focused integration tests passed against
`genro-bag==0.23.0` installed from PyPI in an isolated package directory, with
no standalone source checkout on PYTHONPATH.
