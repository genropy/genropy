# Gramlot pages in the legacy WSGI site

This experimental branch adds Python-authored Gramlot pages to the normal
`webpages/` directory. `GramlotPage` selects a separate loader path before legacy
page mixins are applied. The page receives `.site` and `.db`.

## Try the branch

Use an isolated Python 3.11+ environment and a local test database. From the
repository root:

```sh
git fetch origin
git switch feat/gramlot-pages
python -m venv .venv-gramlot
. .venv-gramlot/bin/activate
python -m pip install -e './gnrpy[pgsql]'
python -m pip install -r projects/test_invoice/requirements-gramlot.txt
```

Configure `test_invoice_pg` with your usual local PostgreSQL settings and seed
data. Start its normal daemon, then launch the WSGI server on a free port:

```sh
python -c 'from gnr.web.serverwsgi import Server; Server().run()' test_invoice_pg --noreload --nodebug -H 127.0.0.1 -p 8101
```

Open `http://127.0.0.1:8101/`, sign in and expand **GramlotPages**:

- **Hello World**: binding and the count of opening-argument notifications.
- **Customer selection**: a `dbSelect` backed by `invc.customer`.
- **States**: a `rpcStore` and grid backed by `invc.state`.

To run alongside other debug instances, use a separate worktree/environment and
copy your instance configuration under a distinct instance name. Give its
`site/siteconfig.xml` a separate daemon port as well as using a free HTTP port.
Keep database configuration local; this branch does not contain credentials or
change your instance settings. The examples only read the selected database.

## Runtime and authoring boundary

The browser runtime is installed separately for each site; it is not shipped in
Genropy's Python wheel. By default place `gramlot.min.js` and its license files
under `<site directory>/gramlot_assets/`. Pages serve that bundle through their
own `/_assets/gramlot.min.js` route, with ETag and Last-Modified validation.
Missing assets return HTTP 503 with an explicit installation message.

An alternate asset directory can be configured in `siteconfig.xml`:

```xml
<gramlot assets_path="gramlot_assets"/>
```

Relative paths are resolved against the site directory, not the working
directory. Absolute paths may point to a shared, administrator-managed runtime.
Only the exact bundle route is served; this does not expose a directory browser.

For this experimental branch, the previously tested snapshot remains available
from the immutable original PR commit. To install it without an npm build:

```sh
# Replace this with the real directory containing this site's siteconfig.xml.
GRAMLOT_SITE_DIR=/path/to/instance/site
mkdir -p "$GRAMLOT_SITE_DIR/gramlot_assets"
git archive ae9d4a3785d6a6888e71c5209aca31295af2e2ae \
  gnrpy/gnr/web/gramlot_assets | \
  tar -x -C "$GRAMLOT_SITE_DIR/gramlot_assets" --strip-components=4
```

Keep `LICENSE`, `NOTICE`, `THIRD-PARTY-NOTICES.txt` and `licenses/` alongside
the runtime. The expected SHA-256 of `gramlot.min.js` is
`c01c83454c7dfee437099db340e709c8c3db977afc72296224e64e2bd04ea7a4`.
This is a transitional snapshot installation, not a new upstream release or a
claim that the full browser build can be reproduced from this repository.
A versioned Gramlot browser release should replace this source when available.

Component styles are supplied by the runtime. The Python dependency uses the
published 0.1.3 wheel, verified with this snapshot.

`window.gramlot` is the actual application. `window.genro` is a separate small
facade providing readiness, publication, resize and unload checks to the legacy
parent. `frameindex.js` is unchanged. Legacy Bags, mixins, widgets, page
registration, dirty-state tracking and notification services are not emulated.

Application code remains Python and uses Gramlot declarations. Decorate
synchronous methods with `gramlot.page.endpoint` or `gramlot.page.source`.
The adapter dispatches only exposed methods, using TYTX JSON over POST; roles,
parameters and request origins are checked. A Source method populates its root
argument and returns `None`. There is no `public_method` dispatch.

## Experimental access boundary

This adapter does not inherit legacy authentication or permissions. Pages are
denied unless they explicitly declare `public = True`; all three demonstrations
opt in and their direct URLs and read-only services are public. Signing into the
parent menu does not protect those URLs. Use a local test database. Authenticated
business pages, write transactions, asynchronous services, inspector/editor
assets and unsaved-change warnings remain outside this initial integration.

## Bundle maintenance

The initial bundle was consolidated from Gramlot browser distribution
`f56e90a19a7ee835` (framework source version 0.1.5), the deployed pre-alpha runtime
used to verify these demonstrations. It is retained in the original PR commit as an experimental snapshot,
not a claim that 0.1.5 is a published package. Its Python authoring contract is
compatible with the pinned public wheel.

`projects/test_invoice/gramlot_tools/minigenro.js` is the readable compatibility source, included in
the bundle. `projects/test_invoice/gramlot_tools/build.mjs` rebundles a prepared Gramlot browser
distribution: install `esbuild@0.28.2` in a working directory, then run
`node projects/test_invoice/gramlot_tools/build.mjs /path/to/browser-distribution /path/to/site/gramlot_assets`.
The distribution must include its manifest and all ESM chunks. Retain the
third-party licenses when replacing the bundle. Runtime changes belong upstream
in Gramlot; do not edit the minified payload manually.

## Asset relocation verification

The asset tests use isolated site directories and cover default, relative and
absolute configuration, conditional requests, a missing installation and the
public-page gate. Build the wheel and verify it contains no `gramlot.min.js` or
vendored Gramlot runtime/licenses before publishing Genropy.

## Original snapshot verification

The results below describe the original PR snapshot, not a new browser run after
asset relocation.

- The legacy web test suite passed: 595 tests using the public Gramlot wheel.
- The configured flake8 7.1.2 check passed on all modified Python files.
- Adapter tests cover single-bundle HTML, explicit public opt-in, endpoint and
  Source dispatch, invalid parameters, roles, methods and origin rejection.
- `node gnrpy/tests/web/gramlot_minigenro_test.mjs` covers readiness, parent
  notification, topic forwarding, foreign-origin rejection, resize and disposal.
- A separate WSGI instance with the published Python wheel returned eight real
  states and customer search/identity results; the bundled grid rendered in the
  browser; customer selection populated the bound caption, locality, postcode
  and state. Undecorated methods and invalid arguments were rejected.
- Full Python suite on the branch: 1,780 passed, 10 skipped, 751 setup errors.
  Every error was PostgreSQL `initdb` failing to allocate a shared-memory segment
  on the verification host. The unchanged base `f5d37d1a1c` reproduced that failure
  in `TestDbModelSrc::test_package`. SQL-suite completion requires a host with
  available PostgreSQL shared-memory resources; this is not a passing SQL run.
