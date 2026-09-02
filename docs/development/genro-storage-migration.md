# genro-storage migration — study and action plan

Reference issue: #251 (testing request for the genro-storage integration).
Branch: `feature/251-genro-storage-switch`, cut from `origin/develop` @ `919a3a572a`.
Target package: `genro-storage` 0.8.0 (PyPI, installed), `fsspec` 2025.10.0, `s3fs` 2025.9.0.

Goal: serve the replaceable part of the legacy storage layer through genro-storage,
behind a switch that is **off by default**, with the legacy code left intact and still
the default. Nothing legacy is removed on this branch.

Everything marked *(measured)* below was executed in this session on this machine
(macOS 25.0.0, pyenv 3.13.2, MinIO at `http://127.0.0.1:9000`, bucket `sandbox`).
Everything else is read from source.

---

## 1. The legacy surface

Three layers, all in play:

| Layer | File | Role |
|---|---|---|
| `StorageNode` | `gnrpy/gnr/lib/services/storage.py:248` | the object application code holds |
| `StorageService` / `BaseLocalService` | `gnrpy/gnr/lib/services/storage.py:426` / `:734` | per-implementation behaviour |
| `BaseStorageHandler` / `LegacyStorageHandler` | `gnrpy/gnr/web/gnrwsgisite_proxy/gnrstoragehandler.py:28` / `:420` | registry (`storage_params`), path parsing, node factory |

Wiring: `GnrDomainProxy.storage_handler` (`gnrpy/gnr/web/gnrwsgisite.py:193`) builds one
handler per domain; `site.storage/storageNode/storagePath` (`:737-744`) are thin
delegators; `storageNodeFromPathList` (`:777`) and `storageDispatcher` (`:795`) are the
WSGI serving path and still live on `GnrWsgiSite`, not on the handler.

Caller surface: 166 call sites of `storageNode(` / `.storage(` across `gnrpy/gnr` and
`projects/gnrcore` *(measured)*. Of the node members, the ones that appear most in the
tree are `.internal_path` (73 raw grep hits), `.children` (43), `.listdir` (41),
`.local_path` (10), `.internal_url` (10), `.public_url` (8), `.mkdir` (8), `.serve` (7).

Five places do `isinstance(x, StorageNode)` and must keep working:
`gnr/lib/services/storage.py:429` (`_getNode`), `:699` (`_call`),
`gnr/core/flatfiles.py:752`, `gnr/lib/services/htmltopdf.py:81`,
`projects/gnrcore/packages/docu/tests/test_docu_sphinx_conf.py:46`.

**Consequence for the design:** the genro-storage node adapter must be a *subclass* of
the legacy `StorageNode`, not a duck type. wf/273 made it a plain object; that is the
root of its worst defect (§4.1).

---

## 2. The eight implementations: replaceable or not

| Implementation | File | Replaceable | Why |
|---|---|---|---|
| `local` | `resources/common/services/storage/local.py` | **Yes** | 1:1 with genro-storage `protocol: local`. Only caveat: `LocalStorage.__init__` raises `FileNotFoundError` if `base_path` does not exist yet *(measured)*, while `BaseLocalService` accepts it and creates on demand. The mount loop must pre-create or skip-and-warn. |
| `aws_s3` | `projects/gnrcore/packages/sys/resources/services/storage/aws_s3.py` | **Yes, with gaps** | genro-storage `protocol: s3` (s3fs) covers read/write/exists/size/mtime/md5hash/children/copy/move/versions/presigned url, verified against MinIO *(measured)*. Gaps to close in the adapter: `mkdir` (legacy writes a `.gnrdir` sentinel so `isdir` becomes True; genro-storage's `mkdir` leaves `is_dir()` False on S3 *(measured)*), `public_url` (no counterpart — legacy `#990` feature), `internal_path` (legacy returns the object key, genro-storage `resolved_path` returns `None` for remote *(measured)*), `readonly`/`write_in_local` (no counterpart), `serve` (legacy redirects to a presigned url, genro-storage streams the bytes). |
| `raw` | `resources/common/services/storage/raw.py` | **Yes, trivially** | It is `local` with `base_path='/'` plus `expandpath`. Mount as `local` with `path: '/'`; keep `expandpath` in the adapter's path handling. |
| `relative` | `resources/common/services/storage/relative.py` | **Yes, but not now** | genro-storage has a relative-mount form (`path: "parent:sub"`, `manager._configure_relative_mount`). The legacy class is a class-swapping hack (`self.__class__ = self.parent_service.__class__`) whose `_resolved_relative` has a `#resolve dbstore...` TODO. Mapping it is a separate, self-contained job; **deferred**, stays legacy. |
| `symbolic` | `resources/common/services/storage/symbolic.py` | **No** | Nine different dynamic resolvers keyed on the mount name (`path_rsrc` → `site.resources`, `path_pkg` → `packageFolder`, `path_gnr`/`path_dojo` → version-keyed, `path_temp` → `tempfile.gettempdir()`, `path_user`/`path_conn`/`path_page` → request-scoped, `path_vol` → `<volumes>`), each with a matching `url_*` producing a site route. It has no `base_path` at all (`self.base_path = 'SYMBOLIC'`). It depends on the site and on the current page, i.e. on things a storage library cannot know. T2 showed genro-storage's callable-path ("switched mount") can carry `rsrc`/`pkg`/`gnr`/`dojo`, but the request-scoped three cannot follow and the `url_*` half stays site-owned regardless. **Stays legacy, permanently, and this is the intended end state.** |
| `http` | `resources/common/services/storage/http.py` | **No** | Genropy's `_http_` is a shortcut where the *path itself is the whole URL* (`internal_path` returns `args[0]`); genro-storage's `http` protocol is a CDN-style mount that needs a `base_path` and appends to it. Different shape, no useful mapping. Stays legacy. |
| `compressed` | `resources/common/services/storage/compressed.py` | **No** | Its identity is the transparent `.gz`/`.bz2` suffix added to every path plus a `Content-Encoding: gzip` serve. genro-storage's `zip`/`tar` backends read *inside* an archive, which is the opposite operation. No counterpart; stays legacy. |
| `sftp` | `projects/gnrcore/packages/sys/resources/services/storage/sftp.py` | **Yes, later** | genro-storage has `protocol: sftp` (fsspec + paramiko). Untestable here without an SFTP host, so it is out of this branch's scope: **deferred**, stays legacy. |

**In this branch: `local`, `raw` and `aws_s3` are routed to genro-storage. Everything
else stays legacy even with the switch on** — and that hybrid is served by the same
handler, per mount.

---

## 3. The API gap, measured

genro-storage 0.8 differs from the legacy node in ways that are silent failures if not
adapted. Verified by running both mounts (local, S3-on-MinIO) *(measured)*:

| Concern | Legacy | genro-storage 0.8 | Adapter must |
|---|---|---|---|
| `exists`, `isfile`, `isdir`, `size`, `mtime`, `md5hash` | properties | **methods** (`exists()`, `is_file()`, `is_dir()`, …) | expose properties — `if node.exists:` on a bound method is always true, and that failure is silent everywhere |
| missing file | `size`/`mtime` → `None` (S3) or `AttributeError` (local); `base64` → `''`; `children` → `None` | **raises `FileNotFoundError`** for `size`/`mtime`/`md5hash`/`to_base64`/`children` | normalise to the legacy return values |
| `base64(mime)` | `mime` falsy → bare b64; `mime is True` → auto-detect data URI; `mime` str → that mime; missing → `''` | `to_base64(mime: str\|None, include_uri=True)` — **defaults to a data URI** | explicit three-case wrapper, not a method rename |
| `url()` | local → `{external_host}/_storage/{mount}/{path}`; S3 → presigned | local → **`None`**; S3 → presigned | route local urls back to the legacy service (the `/_storage/` route is site-owned) |
| `internal_url()` | `{external_host}/_storage/{mount}/{path}` (+`?mtime=` on `nocache`) | **`None` on every backend** | build it in the adapter / delegate to the legacy service |
| `public_url()` | plain non-expiring url (S3 `#990`) | absent | delegate to the legacy service |
| `internal_path` | absolute fs path (local) or object key (S3) | `resolved_path` — path for local, **`None` for remote** | for S3, compose the key from the mount config; 73 grep hits depend on this |
| `listdir()` | list of fullpaths, `None` if not a dir | absent | implement over `children()` |
| `children()` | `None` if not a dir | raises | return `None` |
| `mkdir(*args)` | path segments, idempotent | `mkdir(parents=False, exist_ok=False)` | explicit method — otherwise `node.mkdir('sub')` passes `'sub'` as `parents` and creates nothing |
| `serve(environ, start_response, **kwargs)` | swallows extra kwargs | `serve(environ, start_response, download, download_name, cache_max_age)` — **no `**kwargs`** | explicit method filtering kwargs; `storageDispatcher` passes arbitrary query-string kwargs, and Genropy's own `internal_url(nocache=True)` produces `?mtime=…` |
| `local_path(mode, keep)` | `keep=True` keeps the temp file | `local_path(mode)` — no `keep` | raise on truthy `keep` until upstream has it |
| `move(dest)` | mutates self, returns `None` | `move_to(dest)` returns the new node **and mutates the source** *(measured)* | keep legacy return contract |
| `copy(dest)` | returns destNode; bridges across services | `copy_to(dest)` — dest must be a genro-storage node | route cross-world copy/move through the handler (§4.1) |
| `.parent` | the **site** | the **parent node** | do not delegate; `.parent`, `.service`, `.mode`, `.autocreate`, `.version` stay legacy attributes |
| `mkdir` on S3 | `.gnrdir` sentinel → `isdir` True | no sentinel → `is_dir()` False *(measured)* | write the sentinel, or accept and test the difference |
| `versions` | boto3 CamelCase dicts (`VersionId`, `LastModified`, `IsLatest`) | snake_case (`version_id`, `last_modified`, `is_latest`) *(measured)* | normalise; `projects/gnrcore/packages/sys/webpages/ep_table.py:139` still assumes CamelCase |

Same across both worlds *(measured)*: md5 of the same bytes, `to_base64` payload,
`fullpath` shape (`mount:path`), `child`, `splitext`, `ext`, presigned S3 url.

---

## 4. What is inherited from the three previous attempts

| | strategy | switch | disposition |
|---|---|---|---|
`wf/273-genro-storage-handler` (local, 13 commits) | `GenroStorageHandler(BaseStorageHandler)` by **composition** — holds a `LegacyStorageHandler`, routes per mount on `manager.has_mount()`; `GenroStorageNode` adapter | `storage?use_genro_storage` in siteconfig, default off | **the base of this work** |
`origin/feature/genro-storage-integration` (T1, merged by cgabriel) | side adapter module + an `if` re-inlined into `GnrWsgiSite.storageNode`, bypassing the handler | `<storage_backend>genro-storage</storage_backend>` | **discard the seam, inherit one test file** |
`origin/feature/gs-storage-integration` (T2, 26 commits, 881 behind) | sibling `NewStorageHandler` behind a factory; first ~9 commits *are* today's develop handler | `<storage mode="ns"/>` | **inherit specific pieces** |
`origin/feature/prepare-storage-integration` (T3, 1 commit) | preparatory extraction only, no genro-storage | none (`# TODO`) | **superseded**; as committed it does not even import (`self.storage` shadows the `storage()` method, two `NameError`s left by a rename) |

### 4.1 Inherited

1. **wf/273's switch point** — `GnrDomainProxy.storage_handler`
   (`gnrpy/gnr/web/gnrwsgisite.py:193`). One property, 4 lines, funnels single-domain and
   multidomain, default off. Nothing else in the framework needs to know.
2. **wf/273's `storage_params=None` on `BaseStorageHandler.__init__`** — purely additive,
   lets both handlers share one registry dict (one `sys.service` query, mutations visible
   to both).
3. **wf/273's composition + per-mount routing on `has_mount()`** — makes "flag off =
   byte-identical" trivial to argue and gives the hybrid of §2 a natural home.
4. **wf/273's reuse of `LegacyStorageHandler._adapt_path`** — `vol:`, `_raw_`, `_http_`
   keep being parsed in exactly one place.
5. **wf/273's per-mount `configure([one])` + warn-never-raise** — genro-storage validates
   a batch atomically, so one bad mount would abort site startup
   (upstream `genropy/genro-storage#75`). Keep the loop and the issue reference.
6. **wf/273's property-vs-method adapter** and its introspective test
   `test_every_legacy_property_stays_a_property`, which derives the contract from
   `vars(LegacyStorageNode)` instead of a hand-kept list.
7. **T1's `gnrpy/tests/core/gnrstorage_test.py`** — a 46-test conformance suite for
   today's `StorageNode`: real filesystem, real `BaseLocalService`, a minimal site stub,
   **no daemon and no database**. This is the oracle both modes must satisfy and the shape
   the comparison tests take (§8).
8. **T2's S3 parameter mapping** (`region_name|region → region`,
   `aws_access_key_id → key`, `aws_secret_access_key → secret`, `base_path → prefix`,
   `endpoint_url` passthrough) — wf/273's map only carries `bucket`/`prefix`/`region`, so
   a legacy `aws_s3` service with credentials in its parameters would mount unauthenticated.
9. **T2's `ep_table._getVersionBag` dual key-format + `None` guard** — the version UI
   still assumes boto3 CamelCase; needed the moment an S3 mount is served by genro-storage.
10. **T2's `GENRO_STORAGE_ISSUE.md`** — six reproducible upstream defect reports; the
    checklist of what genro-storage still owes us.

### 4.2 Discarded

1. **T1's seam** (`if` inside `GnrWsgiSite.storageNode`) — fights the handler
   architecture that landed since, and in re-inlining the legacy body it dropped
   `version=` even on the native path.
2. **T1's `GenroStorageConfigConverter`** — maps `symbolic → local` **with no path key**
   (this is issue #252 by construction: every dynamic resolver of §2 silently disappears),
   never maps `aws_s3` (Genropy's implementation string) so S3 is nominal, and reads
   siteconfig Bag *children* while Genropy stores service config in Bag *attributes*.
   Convert from the `storage_params` registry, never from raw siteconfig.
3. **T1's `GenroStorageServiceAdapter(StorageService)`** — faking a legacy *service* by
   subclassing is the wrong direction.
4. **T1's broad `except Exception` → silent native fallback.** A mount that cannot be
   served must warn; a switch that cannot be honoured must fail loudly.
5. **T1's `test_storage_backend_switch.py`** — mock-only, never touches the seam, and
   `test_convert_symbolic_to_local` asserts the bug.
6. **T2's `_makeSymbolicPathCallable`** — reinvents symbolic's paths and gets them wrong
   (`data/users` vs the real `data/_users`, `data/connections` vs `data/_connections`,
   a made-up temp dir). Symbolic stays legacy; nothing is reimplemented.
7. **T2's hard dependency** (`genro-storage` in `[project] dependencies` + unconditional
   top-level import) — see §6.
8. **T2's duplicate `gnrstoragehandler_test.py`** and its committed `adm.db` binary.
9. **T3's `StorageNode` → `LegacyStorageNode` rename** — develop's import alias
   (`gnrstoragehandler.py:18`) does the same job without breaking in-module callers.
10. **wf/273's duck-typed `GenroStorageNode`** — see §1: five `isinstance` checks and the
    whole `StorageService` copy/move machinery dereference `.service`. With wf/273's
    adapter, `legacyNode.copy('site:foo.txt')` raises `AttributeError: service` and
    `genroNode.copy('rsrc:foo')` asks genro-storage for a mount it does not have. **Any
    cross-world copy or move breaks.** The adapter is redesigned as a `StorageNode`
    subclass whose `service` is a thin service-shaped object, and copy/move go through
    the handler so it can bridge the two worlds by content.

---

## 5. The four review.md findings — decision each

From `.phased/done/273-genro-storage-handler/review.md` (written at commit `6f1e1351c4`;
two were fixed by later commits on that same branch, which the review text predates).

| # | Finding | Decision |
|---|---|---|
| 1 | **`http` backend unreachable** — `IMPLEMENTATION_MAP` mapped `http → ('http', {})` with an empty rename map while the guard required `base_path`, so every `http` mount was skipped with a misleading "missing a required parameter" warning, on every handler construction. | **Resolved, as not applicable.** Already fixed on wf/273 by `9760a260a6` (entry removed, guard clause removed, rationale documented). This plan confirms the choice on the merits: §2 shows Genropy's `_http_` and genro-storage's `http` are different shapes. `http` is absent from the map and `_http_` is legacy by design, with a test asserting it. |
| 2 | **`makeNode` drops `autocreate`/`must_exist`/`mode`/`version`** on the genro-storage path. | **Resolved (all four honoured).** `must_exist` → `exists()` check raising `NotExistingStorageNode`; `version` → `manager.node(..., version=...)`, plus T2's `'_latest_'` sentinel handling; `mode` → stored on the node and used as `local_path`'s default, as legacy does; `autocreate` → accepted and, for the `-1` convention, satisfied by the backends creating parent directories on write *(measured: local and S3 both create intermediate dirs on `open('w')`)* — with a test that pins it instead of a comment. `gnrpy/gnr/web/gnrwsgisite.py:2037` passes `autocreate=-1` on a configurable upload path that can be a concrete mount, so this is a real path, not a hypothetical. |
| 3 | **Stale mount when a service's implementation changes** — `updateStorageParams` only added or replaced mappable mounts, so `local → symbolic` kept being served by genro-storage until restart. | **Resolved, inherited.** Already fixed on wf/273 by `f57b38921b` (drop-then-re-register: `delete_mount` if present, then `_configure_mounts()`), with a test. Inherited as is; the cost (re-walking the registry per `sys.service` update) is acceptable for an admin-triggered event. |
| 4 | **`base64` return-shape mismatch** — routed through a method-rename map, so `node.base64()` returned a `data:` URI instead of a bare string and `node.base64(mime=True)` passed `True` where a `str\|None` was expected. | **Resolved.** Explicit three-case wrapper (§3), plus `''` for a missing file, plus a test asserting each case against both modes. No in-repo caller passes `mime=`, but application code outside this repo is the actual audience of the legacy contract. |

Also inherited from that review, non-blocking: the test that reaches into
`manager._mounts` is rewritten to assert through the public API
(`manager.node('site:x').resolved_path`).

Two further defects found in this study and **not** in review.md, both fixed here:
`serve()` and `mkdir()` delegated blind to incompatible signatures (§3). The first is a
live `TypeError` on the WSGI serving path for any url carrying query kwargs — including
the `?mtime=` that Genropy itself generates — which is very likely why wf/273's one
deferred runtime check ("flag on in a real site, open a page serving a stored file") was
never executed successfully.

---

## 6. The switch

**Spelling** — `storage?use_genro_storage` in siteconfig, i.e. an attribute on a
top-level `<storage>` node, read with `boolean()` (the established pattern for
`wsgi?...` flags). Inherited from wf/273. To avoid the confusion with the
`<services><storage>` section that defines services, the key is documented here and
in `TESTING.md`.

```xml
<storage use_genro_storage="True"/>
```

**Default** — absent → falsy → `LegacyStorageHandler`. An untouched siteconfig behaves
exactly as today. A test asserts the negative branch.

**Granularity** — global to switch *on*, per mount to take *effect*. One flag per site
(per domain, since the handler is per domain) enables the genro-storage handler; that
handler then serves only the mounts it could register (`local`, `raw`, `aws_s3`) and
routes every other mount to the legacy handler it holds. So `symbolic`, `http`,
`compressed`, `relative`, `sftp`, `vol:` and any unknown name keep working unchanged
with the switch on. No per-mount opt-in key is introduced: the mount's own
`implementation` already decides, and a second knob would only add ways to be
misconfigured.

**Environment override for tests** — `GNR_STORAGE_USE_GENRO_STORAGE` is *not* added.
The comparison tests construct both handlers explicitly (§8), which is more direct and
leaves the production flag with exactly one source of truth.

**When genro-storage is not importable** — the import is guarded
(`try: from genro_storage import StorageManager / except ImportError: StorageManager = None`).
With the flag **off**, nothing is imported and nothing changes. With the flag **on** and
the package missing, the handler raises `RuntimeError` at construction with the install
command and the flag name — never a silent fallback to legacy, because a site that asked
for genro-storage and silently got the legacy layer is a site whose behaviour nobody can
reason about.

---

## 7. The dependency

**Form: optional extra `genro_storage`, plus `developer`** — as wf/273 did. There is no
`requirements*.txt` in this repo; `gnrpy/pyproject.toml` is the only place.

```toml
genro_storage = ["genro-storage>=0.8,<0.9", "s3fs>=2023.1.0"]
```

and `"genro-storage>=0.8,<0.9"` added to `developer` so CI can import it unconditionally.
`s3fs` belongs in the extra, not in `developer`: it is what pulls `aiobotocore`.

Why not `[project] dependencies` *(measured)*:

- `genro-storage` 0.8.0 itself is light (`fsspec`, `genro-bag`, `genro-builders`,
  `genro-toolbox`, `pyyaml`); the weight is in the `s3` extra, i.e. `s3fs`.
- `s3fs` pulls `aiobotocore`, and `aiobotocore` 2.24.2 requires
  **`botocore<1.40.19,>=1.40.15`**. genropy declares `boto3` with **no upper bound**
  (`gnrpy/pyproject.toml:28`), and every `boto3` release pins a matching `botocore`.
  The installed pair (`boto3` 1.40.18 / `botocore` 1.40.18) sits inside that window by
  luck; the next `boto3` bump walks out of it. That is exactly **#1079**, and making
  `s3fs` mandatory would put it on the critical path of every genropy install.
  Keeping it in an extra confines it to installs that ask for S3-through-genro-storage.

**`pip check` in this environment** *(measured, before any change on this branch)*:

```
s3fs 2025.9.0 has requirement fsspec==2025.9.0, but you have fsspec 2025.10.0.
gcsfs 2025.9.0 has requirement fsspec==2025.9.0, but you have fsspec 2025.10.0.
pain001 0.0.22 has requirement click==8.1.3, but you have click 8.3.2.
pain001 0.0.22 has requirement rich==13.4.2, but you have rich 15.0.0.
pain001 0.0.22 has requirement xmlschema==2.3.1, but you have xmlschema 4.3.2.
```

So `pip check` is **already not clean, before this branch touches anything**, and the
two relevant lines are the `s3fs`/`gcsfs` exact pin on `fsspec` — a pre-existing state
of this machine, not something the extra introduces. The acceptance criterion "clean
`pip check` after adding the dependency" therefore cannot be met as literally stated;
what §9's Phase 1 verification checks instead is **no new line**: the `pip check` output
after adding the extra is identical to the five lines above. Fixing the pre-existing
mismatch means `pip install 'fsspec==2025.9.0'` (or upgrading `s3fs`/`gcsfs` to a
2025.10.x release), which is an environment decision, not a branch decision — flagged
for a call, not done here.

---

## 8. Implementation phases

Each phase ends with a commit. No push, no PR.

| # | What | Files | Verification |
|---|---|---|---|
| 1 | The optional extra | `gnrpy/pyproject.toml` | `pip check` output identical to §7's five lines; `python -c "import genro_storage"` |
| 2 | `GenroStorageHandler` — registry translation, per-mount `configure`, warn-never-raise, `IMPLEMENTATION_MAP` for `local`/`raw`/`aws_s3` with T2's S3 parameter names; `storage_params=None` on `BaseStorageHandler.__init__`; `updateStorageParams`/`removeStorageFromCache` re-sync | `gnrpy/gnr/web/gnrwsgisite_proxy/gnrstoragehandler.py` | `pytest tests/web/gnrgenrostorage_test.py -q -k handler`; `flake8` on the file |
| 3 | `GenroStorageNode` — **subclass of the legacy `StorageNode`** with a service-shaped `service`; the property wrappers; the explicit `base64`/`serve`/`mkdir`/`listdir`/`children`/`url`/`internal_url`/`public_url`/`internal_path`/`local_path`/`move`/`open`; missing-file normalisation | same file | `pytest tests/core/gnrstorage_compare_test.py -q`; `flake8` |
| 4 | Routing + the flag: `makeNode` honouring the four kwargs, `has_mount` fallback, `GnrDomainProxy.storage_handler` reading `storage?use_genro_storage` | `gnrstoragehandler.py`, `gnrpy/gnr/web/gnrwsgisite.py` | `pytest tests/web/gnrgenrostorage_test.py -q`; full `pytest -q` unchanged vs baseline |
| 5 | Cross-world copy/move bridging through the handler | `gnrstoragehandler.py` | `pytest tests/core/gnrstorage_compare_test.py -q -k "copy or move"` |
| 6 | Comparison tests, local mount (§9) | `gnrpy/tests/core/gnrstorage_compare_test.py` | `pytest tests/core/gnrstorage_compare_test.py -q` — both parametrisations pass, no skips |
| 7 | Comparison tests, S3 mount on MinIO (§9) | same file | with MinIO up: pass; with `GNR_TEST_S3_ENDPOINT` unset: explicit skip |
| 8 | `ep_table._getVersionBag` version-key normalisation | `projects/gnrcore/packages/sys/webpages/ep_table.py` | targeted test on both key shapes |
| 9 | Benchmark (§10) | `gnrpy/tests/core/gnrstorage_benchmark.py` | `pytest tests/core/gnrstorage_benchmark.py -s -q`; table pasted into §11 |
| 10 | Docs: this file's status, `docs/development/envvars.py`, `TESTING.md` | `docs/development/*`, `gnrpy/tests/TESTING.md` | `python docs/development/envvars.py \| grep GNR_TEST_S3` |

Baseline to compare against *(measured, on this branch before any change)*:

```
2339 passed, 69 skipped, 15 warnings in 97.79s
```

The 69 skips are: 47 in `tests/web/gnrstoragehandler_test.py` + 12 in
`tests/web/gnrwsgisite_test.py` ("Daemon not available"), 9 SQLite/PostgreSQL feature
skips, 1 PostgreSQL-only. **Note on the daemon skips:** `BaseGnrDaemonTest` starts its
own `gnr web daemon`, which fails here with `OSError: [Errno 48] Address already in use`
because a daemon is already running on this machine (PID 22374); the site itself
instantiates fine *(measured)*. So on this machine the whole daemon-based storage suite
is skipped, and a skipped run proves nothing — which is why the comparison tests are
built without a daemon (§9).

---

## 9. Comparison tests

**File:** `gnrpy/tests/core/gnrstorage_compare_test.py`.

**Shape** — one test body per operation, run **twice** through a `mode` fixture
parametrised `('legacy', 'genro')`. A `node(path)` helper resolves through the handler
under test, so the body never knows which world it is in. Modelled on T1's
`gnrpy/tests/core/gnrstorage_test.py`: real filesystem, real services, **no daemon and
no database**, so it runs both here and in CI. The only stubbed object is the site
*parent* (`external_host`, `cache_max_age`, `storageNode`, `resources`, `not_found_exception`) —
the storage operations themselves are all real, on a real `tmp_path` and on a real MinIO
bucket. No mock ever stands in for an operation under test.

**Operations covered**, per mount and per mode: `exists`, `isfile`, `isdir`, `size`,
`mtime`, `open` read and write (text and binary), `children`, `listdir`, `child`,
`copy` (file, into a directory, cross-mount), `move`, `delete` (file and directory),
`mkdir` (new and existing), `md5hash`, `base64` (bare / `mime=True` / explicit mime /
missing file), `url`, `internal_url` (plain and `nocache=True`), `local_path` (read and
write-back), plus `internal_path`, `fullpath`, `basename`, `cleanbasename`, `ext`,
`splitext`, `parentStorageNode`, `must_exist`, `version`.

Each is asserted **against the legacy result**, not against a hardcoded expectation, so
the test states the actual contract: "same input, same observable result in both modes".
Where the two legitimately differ, the difference is asserted explicitly and named
(`mkdir` on S3, `versions` key shape), never smoothed over.

**Mounts** — `local` on `tmp_path`; `raw`; S3 pointed at MinIO. The legacy `aws_s3`
service takes `custom_endpoint=True, endpoint_url=...`; the genro-storage mount takes
`endpoint_url` directly.

**MinIO skip** — the S3 class is skipped, with the reason naming the endpoint, when
`GNR_TEST_S3_ENDPOINT` is unset **or** the endpoint does not answer
`GET /minio/health/live` within a short timeout. CI has no MinIO, so this must be a
clean skip there and a real run here.

**Legacy-stays-legacy test** — with the genro-storage handler active, an explicit test
asserts that `rsrc:`, `pkg:` and `page:` nodes are produced by the *legacy* handler
(node class and resolved path both checked), and that a `_http_` url and a `vol:` path
do the same. This is the guard on §2's hybrid.

---

## 10. Benchmark

**File:** `gnrpy/tests/core/gnrstorage_benchmark.py`, modelled on
`gnrpy/tests/sql/test_relations_benchmark.py`: `pytest -s`, `time.perf_counter`,
declared repetition counts, a printed timing table.

Same operations, both modes, both mounts: `write` (small 4 KB / large 4 MB), `read`,
`exists`, `size`, `mtime`, `md5hash`, `children` on a directory of 100 files, `copy`
same-mount, `delete`. Repetitions: 50 for metadata operations, 10 for I/O, 3 for the
large file; the count is printed with the table.

Output columns: operation, mount, `legacy_ms`, `genro_ms`, ratio. The measured table
goes into §11 with date, machine and package versions. **No estimated numbers are
recorded.**

---

## 11. Environment variables

To be added to `docs/development/envvars.py` under `Testing`:

| Variable | Meaning |
|---|---|
| `GNR_TEST_S3_ENDPOINT` | S3-compatible endpoint for the storage comparison tests (e.g. `http://127.0.0.1:9000`); unset ⇒ the S3 tests skip |
| `GNR_TEST_S3_ACCESS_KEY` | Access key for that endpoint |
| `GNR_TEST_S3_SECRET_KEY` | Secret key for that endpoint |
| `GNR_TEST_S3_BUCKET` | Bucket to use (default `sandbox`) |
| `GNR_TEST_S3_PREFIX` | Key prefix the tests may create and delete under (default `gnrtest`) |

Credentials are never committed and never defaulted to real values in code — the
default endpoint is unset, so the tests skip rather than reach for anything.

Local MinIO used for this work:

```bash
MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
  minio server /Users/fporcari/Development/minio_folder \
  --address 127.0.0.1:9000 --console-address 127.0.0.1:9001
```

### Benchmark results

*(To be filled by Phase 9 with measured numbers, date, machine and versions.)*

---

## 12. Status and open points

| Phase | State |
|---|---|
| 1–10 | not started (this document is the plan) |

Open, deliberately:

1. **`relative` and `sftp` deferred** (§2) — both are mappable, neither is testable in
   this environment, and each is a self-contained follow-up.
2. **`public_url`, `readonly`/`write_in_local`, `local_path(keep=True)`, `internal_path`
   for remote mounts** have no genro-storage counterpart. All four are handled in the
   adapter by delegating to the legacy service or raising; each is a candidate upstream
   request, and T2's `GENRO_STORAGE_ISSUE.md` is where they belong.
3. **`pip check` is already dirty on this machine** (§7) — the `s3fs`/`gcsfs` exact pin
   on `fsspec` predates this branch. Needs an environment call.
4. **The daemon-based storage suite is skipped on this machine** (§8) because a daemon is
   already running. Whether the pre-existing 47+12 skips should be made to run (by
   stopping that daemon, or by teaching `BaseGnrDaemonTest` to attach to a running one)
   is a separate question from this migration.
5. **The hybrid is the end state, not a stepping stone** (§2): with the switch on, a
   typical instance keeps every symbolic mount on the legacy layer. The cross-world
   copy/move bridge (§8 Phase 5) exists precisely because of that, and it is the part of
   the design most worth reviewing before implementation.
