# genro-storage migration — study and action plan

Reference issue: #251 (testing request for the genro-storage integration).
Branch: `feature/251-genro-storage-switch`, cut from `origin/develop` @ `919a3a572a`.
Target package: `genro-storage` 0.8.0 (PyPI, installed), `fsspec` 2025.10.0, `s3fs` 2025.9.0.

Goal: serve the replaceable part of the legacy storage layer through genro-storage,
behind a switch that is **off by default**, with the legacy code left intact and still
the default. Nothing legacy is removed on this branch.

> **Implementation note (§4.1 point 10, resolved further than planned).** The plan
> called for a node adapter subclassing `StorageNode` over a service-shaped shim.
> Implementing it showed the stronger form of the same idea: a **`StorageService` whose
> backends are genro-storage**, with the legacy `StorageNode` unchanged on top. The
> legacy node then keeps its own `isinstance` identity, `.service`, `serve()`, `mkdir()`,
> `base64` shape, `internal_url`, `listdir`, `autocreate`, and the `StorageService`
> copy/move machinery bridges the two worlds by content on its own. So there is no node
> adapter and no bridging code: `gnr/lib/services/storage_genro.py` is the whole
> variation, and `GenroStorageHandler` overrides exactly one method, `storage()`.
> Consequences: planned Phase 3 collapsed into Phase 2, planned Phase 5 (cross-world
> copy/move) needed no code — only tests — and planned Phase 8 (`ep_table` version keys)
> became unnecessary, because the service reports `versions()` with the legacy boto3 key
> names instead.

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
| `children()` | `None` if not a dir, **sorted by basename** | raises; **order not guaranteed** | return `None`, and sort — the order is what every tree on top of this displays |
| `size`/`md5hash` on a **directory** | `st_size` of the directory (a meaningless number) / `IsADirectoryError` | raises `ValueError` | answer `None`, which is what the legacy aws_s3 service already does for a directory |
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
| 2 | **`makeNode` drops `autocreate`/`must_exist`/`mode`/`version`** on the genro-storage path. | **Resolved: the question stopped existing.** `makeNode` is not overridden at all — the inherited `LegacyStorageHandler.makeNode` builds a legacy `StorageNode`, which consumes all four itself. `must_exist` raises `NotExistingStorageNode` from `StorageNode.__init__`, `mode` is kept on the node and used as `local_path`'s default, `version` reaches the service's `open()` (which also handles T2's `'_latest_'` sentinel), and `autocreate` goes through `StorageService.autocreate` onto the service's `makedirs`. Pinned by `test_node_kwargs_reach_the_node`, `test_must_exist_raises_on_missing` and `test_open_write_creates_intermediate_directories` in both modes. |
| 3 | **Stale mount when a service's implementation changes** — `updateStorageParams` only added or replaced mappable mounts, so `local → symbolic` kept being served by genro-storage until restart. | **Resolved, inherited.** Already fixed on wf/273 by `f57b38921b` (drop-then-re-register: `delete_mount` if present, then `_configure_mounts()`), with a test. Inherited as is; the cost (re-walking the registry per `sys.service` update) is acceptable for an admin-triggered event. |
| 4 | **`base64` return-shape mismatch** — routed through a method-rename map, so `node.base64()` returned a `data:` URI instead of a bare string and `node.base64(mime=True)` passed `True` where a `str\|None` was expected. | **Resolved: `to_base64` is never called.** The service inherits `StorageService.base64`, which builds the string from `open()` — so the bare/`mime=True`/explicit-mime shapes and the `''` for a missing file are the legacy code itself, not a reimplementation of it. Four tests assert the four cases in both modes. |

Also inherited from that review, non-blocking: the test that reaches into
`manager._mounts` is rewritten to assert through the public API
(`manager.node('site:x').resolved_path`).

Two further defects found in this study and **not** in review.md: `serve()` and `mkdir()`
delegated blind to incompatible signatures (§3). The first is a live `TypeError` on the
WSGI serving path for any url carrying query kwargs — including the `?mtime=` that
Genropy itself generates — which is very likely why wf/273's one deferred runtime check
("flag on in a real site, open a page serving a stored file") was never executed
successfully. Both are closed by the service-level design: `mkdir` keeps the legacy
signature (and writes the `.gnrdir` sentinel on a remote mount, so `isdir` behaves as it
does today), and `serve` is implemented on the service with the legacy `**kwargs`
signature — streaming the file for a local mount, redirecting to a presigned url for a
remote one, exactly as `BaseLocalService` and `aws_s3` do.

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

| # | What | Files | Verification | State |
|---|---|---|---|---|
| 1 | The optional extra `genro_storage`, and genro-storage in `developer` | `gnrpy/pyproject.toml` | `pip check` output identical to §7's five lines — **verified, no new line** | done |
| 2 | `GenroStorageService`, `GenroStorageHandler` (registry translation, per-mount `configure`, warn-never-raise, `IMPLEMENTATION_MAP` for `local`/`raw`/`aws_s3` with T2's S3 parameter names), `storage_params=None` on `BaseStorageHandler.__init__`, `updateStorageParams`/`removeStorageFromCache` re-sync | `gnrpy/gnr/lib/services/storage_genro.py` (new), `gnrpy/gnr/web/gnrwsgisite_proxy/gnrstoragehandler.py` | `flake8` clean; smoke on the live `gnrdevelop` site | done |
| 3 | *(collapsed into Phase 2 — see the implementation note above: no node adapter)* | — | — | n/a |
| 4 | The flag: `GnrDomainProxy.storage_handler` reading `storage?use_genro_storage` | `gnrpy/gnr/web/gnrwsgisite.py` | `pytest tests/web/gnrgenrostoragehandler_test.py -q`; full suite unchanged vs baseline | done |
| 5 | *(cross-world copy/move needed no code — `StorageService` bridges it; covered by tests instead)* | — | `pytest tests/core/gnrstorage_compare_test.py -q -k "copy or move"` | n/a |
| 6 | Comparison tests, local mount (§9) | `gnrpy/tests/core/gnrstorage_compare_test.py`, `gnrpy/tests/core/storage_fixtures.py` | 94 passed, 0 skipped | done |
| 7 | Comparison tests, S3 mount on MinIO (§9) | same files | 188 passed with MinIO up; 94 passed + 94 skipped with `GNR_TEST_S3_ENDPOINT` unset | done |
| 8 | *(`ep_table` version keys — unnecessary: the service reports `versions()` with the legacy boto3 key names)* | — | — | n/a |
| 9 | Benchmark (§10) | `gnrpy/tests/core/gnrstorage_benchmark.py` | table in §11 | done |
| 10 | Docs: this file, `docs/development/envvars.py` | `docs/development/*` | `python docs/development/envvars.py \| grep GNR_TEST_S3` | done |

Verification commands:

```bash
cd gnrpy && python -m pytest -q                                   # whole suite, switch off
cd gnrpy && python -m pytest tests/core/gnrstorage_compare_test.py tests/web/gnrgenrostoragehandler_test.py -q
cd gnrpy && python -m pytest tests/core/gnrstorage_benchmark.py -s -q
```

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

Measured 2026-09-02 on the committed code, macOS 25.0.0 (Darwin, Apple silicon), pyenv Python 3.13.2,
genro-storage 0.8.0, fsspec 2025.10.0, s3fs 2025.9.0, boto3/botocore 1.40.18,
smart_open 7.1.0, MinIO (homebrew binary) at `http://127.0.0.1:9000`, bucket `sandbox`.
Reproduce with `cd gnrpy && python -m pytest tests/core/gnrstorage_benchmark.py -s -q`.
Totals in ms for the stated repetition count; `ratio = genro_ms / legacy_ms`, so above 1
genro-storage is slower.

**Local mount**

| operation | reps | legacy_ms | genro_ms | ratio | per call: legacy → genro |
|---|---|---|---|---|---|
| write small (4KB) | 10 | 0.47 | 1.36 | 2.88 | 0.047 → 0.136 ms |
| write large (4MB) | 3 | 2.32 | 2.42 | 1.04 | 0.77 → 0.81 ms |
| read small (4KB) | 10 | 0.18 | 1.14 | 6.21 | 0.018 → 0.114 ms |
| read large (4MB) | 3 | 0.74 | 0.99 | 1.33 | 0.25 → 0.33 ms |
| exists | 50 | 0.10 | 2.33 | 22.49 | 0.002 → 0.047 ms |
| size | 50 | 0.11 | 2.48 | 22.77 | 0.002 → 0.050 ms |
| mtime | 50 | 0.10 | 2.49 | 24.03 | 0.002 → 0.050 ms |
| md5hash | 50 | 0.95 | 7.91 | 8.36 | 0.019 → 0.158 ms |
| children (100 files) | 10 | 0.93 | 8.27 | 8.88 | 0.093 → 0.827 ms |
| copy same mount | 10 | 1.25 | 3.93 | 3.14 | 0.125 → 0.393 ms |
| internal_url | 50 | 0.04 | 0.05 | 1.17 | 0.001 → 0.001 ms |

**S3 mount (MinIO on localhost, so almost no network latency: on a real remote
endpoint the round trip dominates every row)**

| operation | reps | legacy_ms | genro_ms | ratio | per call: legacy → genro |
|---|---|---|---|---|---|
| write small (4KB) | 10 | 49.76 | 29.30 | 0.59 | 4.98 → 2.93 ms |
| write large (4MB) | 3 | 48.41 | 42.24 | 0.87 | 16.1 → 14.1 ms |
| read small (4KB) | 10 | 21.95 | 36.59 | 1.67 | 2.20 → 3.66 ms |
| read large (4MB) | 3 | 10.56 | 15.81 | 1.50 | 3.52 → 5.27 ms |
| exists | 50 | 33.51 | 30.43 | 0.91 | 0.67 → 0.61 ms |
| size | 50 | 30.61 | 31.21 | 1.02 | 0.61 → 0.62 ms |
| mtime | 50 | 32.12 | 29.80 | 0.93 | 0.64 → 0.60 ms |
| md5hash | 50 | 31.99 | 90.65 | 2.83 | 0.64 → 1.81 ms |
| children (100 files) | 10 | 72.35 | 64.61 | 0.89 | 7.24 → 6.46 ms |
| copy same mount | 10 | 35.10 | 76.58 | 2.18 | 3.51 → 7.66 ms |
| internal_url | 50 | 0.07 | 0.07 | 0.99 | 0.001 → 0.001 ms |

Reading the numbers:

- **The overhead is per call, not per byte.** On a local mount a metadata call
  costs 0.002 ms through the legacy service and 0.047 ms through genro-storage,
  which is the 22x: genro-storage builds a node object per call. On the 4 MB
  file the ratio collapses to 1.04-1.33, because the fixed cost stops mattering.
  So the ratio to watch is not the worst one, it is the one on the operation you
  actually repeat thousands of times.
- **The one local row that can reach a user** is `children` on 100 files: 0.09 ms
  against 0.83 ms per listing. A `StorageResolver` walking a large directory pays
  that per level. Still sub-millisecond, but it is the first place to look if a
  tree ever feels slow, and the fix is a per-path node cache in the service.
- **On S3 genro-storage is not slower overall**: writes are almost twice as fast
  (s3fs against smart_open + boto3), metadata is a wash, `children` slightly
  better. The real regression is the small read, 2.20 → 3.66 ms.
- **The S3 copy stays server-side in both worlds** *(measured separately)*: the
  cost does not grow with the file - 4 KB copies in 19.9 ms, 4 MB in 15.6 ms - so
  no bytes travel through the client. genro-storage's 2.18x is extra round trips
  for its own checks, a fixed cost, not a transfer.
- **`md5hash` on S3 is not a like-for-like comparison.** The legacy service reads
  the ETag and gives up when a multipart upload made it something other than an
  md5, so its 0.64 ms buy a `None`; genro-storage's 1.81 ms return the real hash.
  This is the divergence pinned in `TestNamedDivergences`.
- **Run-to-run noise on S3 is material** at these repetition counts: across three
  runs `children` moved between 0.36x and 1.15x and `read small` between 1.60x
  and 2.96x. The local ratios were stable to within a few percent. Treat the S3
  column as an order of magnitude and raise the repetitions before drawing a
  conclusion from one cell.

## 12. Status and open points

| Phase | State |
|---|---|
| 1, 2, 4, 6, 7, 9, 10 | done (see §8) |
| 3, 5, 8 | not needed — see the implementation note at the top |

Measured results against the acceptance criteria:

| Criterion | Result |
|---|---|
| Switch off ⇒ same outcome as develop | **2339 passed, 69 skipped** — identical to the baseline measured on this branch before any change; no test went passed→failed, no new skip |
| Switch on ⇒ comparison tests pass on local | **94 passed, 0 skipped** (both modes) |
| Switch on ⇒ MinIO tests pass when configured, skip otherwise | **188 passed** with `GNR_TEST_S3_ENDPOINT` set; **94 passed + 94 skipped**, reason naming the variable, when unset |
| Non-replaced implementations stay legacy with the switch on | `tests/web/gnrgenrostoragehandler_test.py` — 29 passed, including the nine symbolic mounts and `_http_`, and `internal_path` parity with the legacy handler for `rsrc:`, `pkg:`, `temp:`, `gnr:` |
| `pip check` clean | **Not achievable as stated, and not caused by this branch** — see §7. Verified instead: the output is identical to the five pre-existing lines |
| Benchmark table present and reproducible | §11, with the command |

Open, deliberately:

1. **`relative` and `sftp` deferred** (§2) — both are mappable, neither is testable in
   this environment, and each is a self-contained follow-up.
2. **Four things genro-storage does not provide**, each handled and each an upstream
   candidate (T2's `GENRO_STORAGE_ISSUE.md` is where they belong):
   `public_url` — built in the service from the mount's endpoint and bucket;
   `internal_path` for remote mounts — composed from the mount's `base_path`, since
   `resolved_path` is `None` off the local filesystem;
   `readonly`/`write_in_local` — no counterpart at all, so a readonly mount is **left on
   the legacy service**, because serving it through a writable backend would silently
   drop the restriction;
   `local_path(keep=True)` — refused with `NotImplementedError` on a remote mount rather
   than silently not keeping the file.
3. **Two upstream round-trip costs on S3, reported as `genropy/genro-storage#78`**
   *(measured)*: `copy_to()` issues 6 API calls where one `CopyObject` would do — two of
   them `ListObjectVersions`, which a copy does not need — and `open('rb')` adds a
   `HeadObject` before the `GetObject`. On a real endpoint that is ~180 ms instead of
   ~30 for a copy, plus a billed request per `ListObjectVersions`. The copy nonetheless
   stays server-side, so the cost is round trips and not a transfer through the client.
   Our own `duplicateNode` could sidestep it by going through the backend's `copy()`
   instead of the node's `copy_to()`; not done here, because it is an optimisation
   beyond this branch's scope and the upstream fix would make it unnecessary.
4. **One round-trip cost of our own, on the legacy side**: `StorageNode.open()`
   (`gnr/lib/services/storage.py:357`) calls `service.autocreate(path, autocreate=-1)`
   even when opening for reading, which on S3 costs a `HeadObject` plus a
   `ListObjectsV2` per open — 3 round trips where 1 would do, on both the legacy and the
   genro-storage path. Pre-existing, unrelated to this branch, worth its own issue.
5. **`pip check` is already dirty on this machine** (§7) — the `s3fs`/`gcsfs` exact pin
   on `fsspec` predates this branch. Needs an environment call.
6. **The daemon-based storage suite is skipped on this machine** (§8) because a daemon is
   already running. Whether the pre-existing 47+12 skips should be made to run (by
   stopping that daemon, or by teaching `BaseGnrDaemonTest` to attach to a running one)
   is a separate question from this migration.
7. **The hybrid is the end state, not a stepping stone** (§2): with the switch on, a
   typical instance keeps every symbolic mount on the legacy layer. This is why the
   service-level design matters — `StorageService` bridges a copy or move between the
   two worlds by content on its own, with no code of ours in the path.
8. **A local mount whose `base_path` does not exist yet stays legacy** (§8 Phase 2):
   genro-storage's local backend requires the directory to exist, the legacy service
   creates it on first write. On `gnrdevelop` this is the `mail` mount, and it logs one
   warning at handler construction. Pre-creating the directory at startup would be the
   alternative; not done, because a storage switch should not create directories.
9. **Run with the flag on in a serving site: done, and it found two defects.**
   `projects/gnrcore/packages/test15/webpages/tools/storage_genro.py` is a testhandler
   page that exercises the switch through real requests — storage trees on the mounts
   genro-storage takes over and on the ones that stay legacy, an inspector over the whole
   node surface, a side-by-side of the two handlers on the same path, an uploader, a
   cross-world copy/move, and a tree on an S3 mount. Driven against `gnrdevelop` with
   the flag on it showed, on top of what the unit tests already covered:
   `children()` was not sorted (the legacy local service sorts, so every tree changed
   order), and `size`/`md5hash` raised on a directory instead of answering. Both are
   fixed, both now have a test. What is still untested in a live site: the upload path
   itself (it needs a file picked by hand) and multidomain.
10. **The per-call node construction on local mounts** (§11) is the one measured
   inefficiency: worth a cache in the service if a profile ever points here.
