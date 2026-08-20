# Context: wf/test15-gnrwdg-macro2
Parent: refactor/test15-example-migration-macro1
Mode: autonomous

## Objective
Macro 2 of 6 of the test15 -> test example triage: the `gnrwdg` area, emptied.
Twenty-five pages are triaged with the recipe macro 1 established — dead ones
removed, live ones promoted into `test/webpages/` and documented, overlapping
ones folded into the counterparts that already exist there. The area's own
blocker is that nine of its pages address `glbl`, a core package living in
`projects/gnr_it` that no instance here mounts: the first phase mounts it and
teaches the render sweep to skip a page whose packages are absent, so the
pages need no rewriting and a user instance without `glbl` still runs the suite.

## Work Plan
- [x] **Phase 1**: Mount glbl in gnrdevelop and skip pages whose packages are absent
  > Review: (foreman) the original Done criterion, `gnr app dbsetup gnrdevelop` exits 0, was wrong. It
    made this phase hostage to the whole instance migrating cleanly, and gnrdevelop's sqlite
    carries a pre-existing docu drift that sqlite cannot apply at all (see notes.md, Run
    inspection). Corrected to a check on the glbl tables themselves, which is what the phase
    actually needs and what it delivered in `e5462996c`. The phase closes [x]; its Issue and
    Attempted notes stay as the record of what its checks went through, and the docu drift is
    filed separately, not repaired here.
  > Issue: one Done criterion is unmet — `gnr app dbsetup gnrdevelop` does not exit 0. The
    local sqlite of gnrdevelop carries a pre-existing docu model drift and dbsetup aborts on
    `ALTER TABLE "docu"."docu_documentation" ALTER TABLE base_language TYPE character
    varying(2)` with `sqlite3.OperationalError: near "ALTER": syntax error` — the generated
    SQL repeats ALTER TABLE and sqlite has no ALTER COLUMN TYPE at all. The whole pending
    change list is docu (two ALTER COLUMN TYPE plus the docu_faq/docu_redirect creates);
    nothing in it belongs to this phase, and the same abort happens at HEAD with
    instanceconfig.xml reverted, so it pre-dates this workflow. Everything else the phase
    asked for is in place and green: glbl is mounted, its seven tables were created in
    `data/glbl.db` and loaded from the package's own startup_data.gz (regione 20,
    provincia 110, comune 8092, localita 14751), `page_required_packages` exists with unit
    tests, the smoke sweep skips pages whose packages are absent and prints one line per
    skipped page, the CI step runs the new suite, the six model injections are deleted.
    test_pages_ratchet.py + test_pages_documented.py + test_pages_smoke.py: 5 passed;
    flake8 clean on the Files: set. Repair means deciding what to do about the docu drift
    (an adapter/model matter outside this phase's Files: set, worth its own issue), not
    redoing the phase's work.
  > Attempted: (1) reverted instanceconfig.xml to HEAD and re-ran dbsetup — identical
    failure, so mounting glbl is not the cause; (2) inspected the pending change list with
    `-c -v --loglevel info` — docu only, and the first ALTER aborts the run; (3) fixed the
    mounted-package accessor after the first smoke run failed on `site.application` — the
    site exposes `site.gnrapp.packages`; (4) loaded the glbl startup data through
    `GnrApp('gnrdevelop').db.package('glbl').loadStartupData()`, which succeeded even
    though dbsetup had aborted, because the glbl tables are created in the package's own
    attached sqlite. Not attempted on purpose: deleting and rebuilding the local sqlite
    (destructive well beyond the loadStartupData the plan authorized) and patching the docu
    model or the sqlite adapter's ALTER COLUMN TYPE (outside this phase's Files: set).
  > Review: (deviation) the plan expected `test/webpages/inputfields/dbselect.py` to require
    `{'glbl'}`; it also addresses `adm.user` and `adm.htag`, so the unit test asserts
    `{'adm', 'glbl'}`.
  > Verify: now — open /test15/gnrwdg/formHandler: the Provincia dbselect drops down with
    real provinces, which is what proves the mount and the data load rather than the model
    merely building.
  - Pattern reference: `projects/gnrcore/packages/test/tests/pages_ratchet.py:docstring_defects` (same ast-over-one-page shape, same SyntaxError tolerance); the `pkgcode` lines already in `projects/gnrcore/instances/gnrdevelop/config/instanceconfig.xml`
  - Files:
    - projects/gnrcore/instances/gnrdevelop/config/instanceconfig.xml
    - projects/gnrcore/packages/test/tests/pages_ratchet.py
    - projects/gnrcore/packages/test/tests/test_pages_smoke.py
    - projects/gnrcore/packages/test/tests/test_pages_ratchet.py (new)
    - .github/workflows/tests.yml
    - projects/gnrcore/packages/test/model/_packages/glbl/regione.py (deleted)
    - projects/gnrcore/packages/test/model/_packages/glbl/provincia.py (deleted)
    - projects/gnrcore/packages/test/model/_packages/glbl/comune.py (deleted)
    - projects/gnrcore/packages/test15/model/_packages/glbl/regione.py (deleted)
    - projects/gnrcore/packages/test15/model/_packages/glbl/provincia.py (deleted)
    - projects/gnrcore/packages/test15/model/_packages/glbl/comune.py (deleted)
  - Decisions:
    - `glbl` is mounted as `<gnr_it_glbl pkgcode="gnr_it:glbl"/>`: `GnrApp.addPackage` splits a `project:package` pkgcode (`gnrpy/gnr/app/gnrapp.py:1051`), so the package id stays `glbl` and every `glbl.<table>` reference in the pages resolves unchanged. `glbl` is also added to the instance's `<menu package=.../>` list, so its lookup tables are reachable from the UI.
    - The absent-package guard is ONE reusable helper, `page_required_packages(page_path)` in `pages_ratchet.py`, and the smoke suite is its only consumer. It reads package ids off the source, so it works for `glbl` exactly as for any other package a page might address.
    - `glbl` ships its own `startup_data.gz`, so the local sqlite is populated with `db.package('glbl').loadStartupData()` (`gnrpy/gnr/app/gnrdbo.py:147`) rather than with a fixture of our own. The db file is gitignored: this is developer setup, and it is recorded in the smoke suite's module docstring, not in a test.
    - The `model/_packages/glbl/*` column injections go, from BOTH packages: `mill_si`/`mill_no`/`mill_ast` on provincia, `voto_si`/`voto_no`/`voto_astenuto` on comune, `province_principali_*` on regione are leftovers of an old referendum demo, duplicated in `test` and `test15`, and mounting `glbl` would turn them into real columns.
    - `prov_test`'s commented-out relation to `glbl.regione.sigla` STAYS commented. An instance mounting `gnrcore:test` without `gnr_it:glbl` must keep building clean, which is exactly why macro 1 commented it.
  - Details:
    1. `instanceconfig.xml`: add `<gnr_it_glbl pkgcode="gnr_it:glbl"/>` to `<packages>` after the `gnrcore_test15` line, and add `glbl` to the `<menu package="..."/>` list.
    2. `pages_ratchet.py`: add `page_required_packages(page_path)`. It reads the page like `docstring_defects` does (same `PACKAGES_DIR` join, same `ast.parse` guarded by `SyntaxError` — an unparsable page requires nothing), walks every `ast.Call`, and collects string literals from: the keywords named `table`, `dbtable`, `dbTable`, and the first positional argument of a call whose func is an attribute named `table` (`self.db.table('x.y')`). Of those it keeps the values matching `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` and returns the set of their package parts.
    3. `test_pages_smoke.py`: read the mounted package ids once, from `cls.site.application.packages`. In `page_statuses`, a page whose `page_required_packages` is not a subset of them is not rendered: collect it in a `skipped` mapping (page path -> missing package ids) and leave it out of the statuses the ratchet is asserted over. Print one line per skipped page from the test body, so a sweep that quietly stops covering pages is visible. Extend the module docstring with the guard and with the `loadStartupData` setup step for `glbl`.
    4. `test_pages_ratchet.py` (new): unit tests for `page_required_packages` over three pages of the `test` package that this macro does not touch, so the assertions stay true — `test/webpages/inputfields/dbselect.py` requires `{'glbl'}`, `test/webpages/components/palette_importer.py` requires `{'test'}`, `test/webpages/html/div.py` requires nothing. Source-only, no instance, no db: it belongs in CI. State that choice in the module docstring.
    5. `tests.yml`: extend the existing "Documentation ratchet" step to invoke `test_pages_ratchet.py` alongside `test_pages_documented.py`.
    6. Delete the six `model/_packages/glbl/*.py` files; leave the now-empty `_packages/glbl` folders removed too.
    7. Run `gnr app dbsetup gnrdevelop`, then load the glbl startup data.
  - Done: the glbl tables are in place and populated — `python3 -c "from gnr.app.gnrapp import GnrApp; print(GnrApp('gnrdevelop').db.table('glbl.provincia').countRecords())"` prints a number greater than zero; `pytest projects/gnrcore/packages/test/tests/test_pages_ratchet.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the Files: set
  - Verify: now — open /test15/gnrwdg/formHandler: the Provincia dbselect drops down with real provinces, which is what proves the mount and the data load rather than the model merely building

- [x] **Phase 2**: Remove the four dead pages of the area
  > Done: the four files (recursive_th.py, panegrid.py, gnrlayout.py, embed.py) are deleted via `git rm`; their three docstring_debt.txt lines (embed.py, panegrid.py, recursive_th.py) are removed, gnrlayout.py was not listed as expected; `test_pages_documented.py` 1 passed; `test_pages_smoke.py -rs` reports `1 passed` (no skip). No code files touched, so no flake8 target.
  > Files: projects/gnrcore/packages/test15/webpages/gnrwdg/recursive_th.py (deleted), projects/gnrcore/packages/test15/webpages/gnrwdg/panegrid.py (deleted), projects/gnrcore/packages/test15/webpages/gnrwdg/gnrlayout.py (deleted), projects/gnrcore/packages/test15/webpages/gnrwdg/embed.py (deleted), projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Pattern reference: library-standard (deletions plus their ratchet entries, as in macro 1's `1fbf73ce2`)
  - Files:
    - projects/gnrcore/packages/test15/webpages/gnrwdg/recursive_th.py (deleted)
    - projects/gnrcore/packages/test15/webpages/gnrwdg/panegrid.py (deleted)
    - projects/gnrcore/packages/test15/webpages/gnrwdg/gnrlayout.py (deleted)
    - projects/gnrcore/packages/test15/webpages/gnrwdg/embed.py (deleted)
    - projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Decisions:
    - `recursive_th.py`: `main()` is `pass` and both page hooks return `''` — there is no page.
    - `panegrid.py`: `testOnly='_target_action'` renders one case out of ten, three cases address `polimed.fattura` (a customer package absent from the repo), and the includedView cases it does demonstrate are already covered by `test/webpages/components/includedview.py`.
    - `gnrlayout.py`: one `framePane` with a slotToolbar, covered by `test/webpages/layout/framepane.py` and by the framepane page folded in Phase 4.
    - `embed.py`: macro 1 already promoted its live cases into `test/webpages/components/drop_uploader.py` (`test_3_imgUploaderEdit`, `test_4_embedUploaderReadOnly`). The two left over embed a `/_site/test/testimages/test.pdf` that no one ships, so they demonstrate nothing on any machine.
  - Details: delete the four files. Then remove exactly these three lines from `docstring_debt.txt` — `test15/webpages/gnrwdg/recursive_th.py`, `test15/webpages/gnrwdg/panegrid.py`, `test15/webpages/gnrwdg/embed.py`. `gnrlayout.py` is NOT in that file (it carries a title docstring) so there is no fourth line to remove; removing a line that is not there, or leaving one of the three, fails the ratchet in one direction or the other. Every move in this phase is `git mv` and every removal `git rm`: the rename is recorded (macro 1's commit carries the same `{test15 => test}` renames) and nothing leaves the branch irrecoverably.
  - Done: the four files no longer exist; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing)

- [x] **Phase 3**: Promote the seven self-contained pages
  > Done: the seven pages are under `projects/gnrcore/packages/test/webpages/gnrwdg/` via `git mv` and gone
    from test15. Each got a real title docstring and a one-liner on every `test_*` case (plus on
    `struct_doc`/`doc_form`/`remote_contenuto_test`, the helpers the cases read through).
    `bageditor.py`'s two `/Users/sporcari/...` Bag paths are replaced by one
    `localizationBag()` helper reading `pkg:adm/localization.xml` through
    `self.site.storageNode(...).internal_path`, so both cases work on any machine; its
    commented-out block above `test_3_multiValueEditor` is gone, as is `fieldstree.py`'s
    commented `onDrag=` line. Six `test15/webpages/gnrwdg/` lines removed from
    `docstring_debt.txt` (`textboxmenu.py` was not listed, as the plan said) and no
    `test/webpages/gnrwdg/` line added. `test_pages_documented.py` + `test_pages_smoke.py -rs`:
    2 passed, no skip; `test_pages_ratchet.py`: 3 passed; flake8 zero errors on
    `test/webpages/gnrwdg/`.
  > Files: projects/gnrcore/packages/test/webpages/gnrwdg/bageditor.py, projects/gnrcore/packages/test/webpages/gnrwdg/colormenu.py, projects/gnrcore/packages/test/webpages/gnrwdg/fieldstree.py, projects/gnrcore/packages/test/webpages/gnrwdg/formdocumentstore.py, projects/gnrcore/packages/test/webpages/gnrwdg/gridgallery.py, projects/gnrcore/packages/test/webpages/gnrwdg/textboxmenu.py, projects/gnrcore/packages/test/webpages/gnrwdg/tooltipDialog.py, the same seven under projects/gnrcore/packages/test15/webpages/gnrwdg/ (deleted), projects/gnrcore/packages/test/tests/docstring_debt.txt
  > Review: (deviation) the plan put the storageNode fix inline in the two `bageditor.py` cases; it is
    factored into one `localizationBag()` helper instead, marked `# wf:phase-3:new` for the naming
    review. Same call, written once.
  > Review: `textboxmenu.py` carries two cases with the same `test_1_` prefix (`test_1_Menu`,
    `test_1_Tooltip`). Left as they are: TestHandlerFull dispatches on the full method name
    (`resources/common/gnrcomponents/testhandler.py:38`), so both render and nothing is hidden.
    Phase 4's renumbering rule is about appended cases colliding by full name, not by number.
  > Verify: deferred: needs Phase 6 — the seven pages are in the Phase 6 browser pass; the render
    sweep only proves their bootstrap GET.
  - Pattern reference: the pages macro 1 promoted — `projects/gnrcore/packages/test/webpages/websocket/draw.py` (title docstring plus one line per test case, dead code dropped); `projects/gnrcore/packages/test/webpages/components/drop_uploader.py:99` for the storageNode idiom
  - Files:
    - projects/gnrcore/packages/test/webpages/gnrwdg/bageditor.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/colormenu.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/fieldstree.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/formdocumentstore.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/gridgallery.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/textboxmenu.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/tooltipDialog.py (new, from test15)
    - the same seven files under projects/gnrcore/packages/test15/webpages/gnrwdg/ (deleted)
    - projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Decisions:
    - These seven need no table at all (or, for `formdocumentstore`, only `pkg:test/testdata/docstore`, which macro 1 already moved into `test`), so they move unchanged except for documentation and dead code.
    - `bageditor.py`: `test_1_firsttest` and `test_2_component` open `Bag('/Users/sporcari/sviluppo/genro/projects/gnrcore/packages/adm/localization.xml')`, a path that exists on no machine. Both become `Bag(self.site.storageNode('pkg:adm/localization.xml').internal_path)`. That is two cases going from broken to working, so they are kept, not dropped.
    - `bageditor.py` `test_3_multiValueEditor` keeps its case but loses the commented-out block above it.
    - `colormenu.py` depends on `chroma.min.js`, which is in the repo at `resources/js_libs/chroma.min.js`; its `onMain_chromaImport` loader stays as is.
    - Every promoted page gets a module docstring whose first line is a real title (the ratchet rejects the placeholders `Test page description`, `test`, `-`, `index.py`, `test page`) and a one-line docstring on every `test_*` method — that is exactly what `docstring_defects` checks.
  - Details: move the seven files into `projects/gnrcore/packages/test/webpages/gnrwdg/`, apply the documentation and the two fixes above, and delete the seven `test15` originals. Every move in this phase is `git mv` and every removal `git rm`: the rename is recorded (macro 1's commit carries the same `{test15 => test}` renames) and nothing leaves the branch irrecoverably. Then remove their `test15/webpages/gnrwdg/...` lines from `docstring_debt.txt` — six of the seven are listed there (`textboxmenu.py` is not) — and do NOT add the new `test/webpages/gnrwdg/...` paths: they are documented now, so the ratchet must not list them.
  - Done: the seven files exist under `projects/gnrcore/packages/test/webpages/gnrwdg/` and no longer under test15; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the seven promoted files

- [x] **Phase 4**: Fold the six overlapping pages into their counterparts  `vast`
  > Done: the seven test15 sources are gone. `palette.py` + `panetree.py` -> two cases appended to
    `components/palette.py`; `menuselect.py` -> one case in `dojo/menu.py`; `framepane.py` -> six cases
    plus its `mypage_slotbar_myaction` struct_method in `layout/framepane.py`; `includedview_bagstore.py`
    -> one case in `components/includedview.py` reusing the target's own `common_data`/`common_struct`;
    `baggrid_scroll.py` -> one case in `components/Grid/bag_grid.py` with its two helpers renamed
    (`scrollstruct`, `getScrollDati`) to clear the collision with the target's `gridstruct`/`getDati`;
    `slotbar.py` split into the new `gnrwdg/slotbar.py` (six slotBar/slotToolbar cases plus the `myslot`
    struct_method, `testOnly='_0_'` dropped) and seven multibutton cases appended to
    `components/multibutton.py` with `getmbdata` and `multibuttonRegione`. Every appended case renumbered
    to continue its target's sequence and documented with a one-liner. Dropped as the plan said:
    `framepane.py`'s `test_10/11/12_framepanebug` and `slotbar.py`'s commented-out `multiButtonForm` tail.
    Eight lines removed from `docstring_debt.txt` (the five listed sources plus the three targets that are
    now fully documented). `test_pages_documented.py` + `test_pages_ratchet.py`: 4 passed;
    `test_pages_smoke.py -q -rs`: 1 passed, no skip; flake8 zero errors on the seven touched pages.
  > Files: projects/gnrcore/packages/test/webpages/components/palette.py, projects/gnrcore/packages/test/webpages/dojo/menu.py, projects/gnrcore/packages/test/webpages/layout/framepane.py, projects/gnrcore/packages/test/webpages/components/includedview.py, projects/gnrcore/packages/test/webpages/components/Grid/bag_grid.py, projects/gnrcore/packages/test/webpages/components/multibutton.py, projects/gnrcore/packages/test/webpages/gnrwdg/slotbar.py (new, from test15), projects/gnrcore/packages/test15/webpages/gnrwdg/{palette,panetree,menuselect,framepane,includedview_bagstore,baggrid_scroll,slotbar}.py (deleted), projects/gnrcore/packages/test/tests/docstring_debt.txt
  > Review: (deviation) two source cases were dropped beyond the plan's list because the target already
    carried them verbatim: `framepane.py`'s `test_5_regions` is `layout/framepane.py`'s own `test_1_regions`
    apart from one placeholder string, and `slotbar.py`'s `test_7_slotToolbar_multibutton_base` is a strict
    subset of `components/multibutton.py`'s `test_0_multibutton_base`. Appending them would have shown the
    same case twice on the merged page, which is the opposite of what folding is for.
  > Review: (deviation) the merge forced four global codes apart. `slotbar.py` reused `frameOne` on two
    cases and `frameTwo` on two more, and `slotbar.py`'s `test_12`/`test_14` both used
    `frameMultibuttonStore`: `testOnly='_0_'` hid the clash while only one case rendered, and dropping
    `testOnly` exposes it, since TestHandlerFull renders every case on one page. They are now `frameOneCss`,
    `frameTwoVertical` and `frameMultibuttonStoreMixed`. Likewise `panetree.py`'s `palettePane('pippo')`
    collided with `palette.py`'s `paletteCode='pippo'` in the shared target and became `hiddendock`.
  > Review: (deviation) removing a debt line for a target "now fully documented" meant clearing the
    pre-existing defects of the three listed targets, not only documenting the appended cases: module
    docstrings for `components/includedview.py` and `components/multibutton.py`, one-liners on
    `dojo/menu.py`'s `test_9_menudiv_label`/`test_10_combomenu` and on `components/multibutton.py`'s two
    original cases. `assert_ratchet` fails on stale entries, so a half-documented target could not simply
    keep its line while its appended cases were documented.
  > Review: `dojo_source = True` on `includedview_bagstore.py` and `baggrid_scroll.py` was not carried into
    the targets: it is a dev-only non-minified-dojo switch and `TestHandler` already sets it for every
    test page.
  > Verify: deferred: needs Phase 6 — the seven merged pages are in the Phase 6 browser pass; the render
    sweep only proves their bootstrap GET, and the renumbered cases are exactly what a collision would
    hide silently.
  - Pattern reference: macro 1's three merges in `1fbf73ce2` — `projects/gnrcore/packages/test/webpages/components/TableHandler/inlineedit.py` and `.../selectionname.py` (cases appended to an existing page, renumbered, each documented, nothing lost)
  - Files:
    - projects/gnrcore/packages/test/webpages/components/palette.py  <- test15 palette.py + panetree.py
    - projects/gnrcore/packages/test/webpages/dojo/menu.py  <- test15 menuselect.py
    - projects/gnrcore/packages/test/webpages/layout/framepane.py  <- test15 framepane.py
    - projects/gnrcore/packages/test/webpages/components/includedview.py  <- test15 includedview_bagstore.py
    - projects/gnrcore/packages/test/webpages/components/Grid/bag_grid.py  <- test15 baggrid_scroll.py
    - projects/gnrcore/packages/test/webpages/gnrwdg/slotbar.py (new)  <- test15 slotbar.py, slotbar cases
    - projects/gnrcore/packages/test/webpages/components/multibutton.py  <- test15 slotbar.py, multibutton cases
    - projects/gnrcore/packages/test15/webpages/gnrwdg/{palette,panetree,menuselect,framepane,includedview_bagstore,baggrid_scroll,slotbar}.py (deleted)
    - projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Decisions:
    - The mapping above is fixed; it is not up for rediscovery. `slotbar.py` is the one page that splits: its `test_*_slotbar*` / `test_*_slotToolbar*` cases become a new `gnrwdg/slotbar.py` (no counterpart exists), while `test_6..test_14`, which are all `multibutton` / `multiButtonForm`, are appended to `components/multibutton.py`, which today has two cases.
    - Case numbering: appended cases are renumbered to continue the target page's sequence. The TestHandler dispatches on the `test_<n>_` prefix, so a collision silently hides a case.
    - Dropped, with the reason on the record: `framepane.py`'s `test_10/11/12_framepanebug` — raw `dataController` scripts reproducing 2011 palette/framePane bugs, with no assertion and nothing to look at; `slotbar.py`'s `testOnly='_0_'` and `panegrid`-style commented-out tails.
    - Nothing else is dropped: every other case survives the merge, documented.
  - Details: for each of the six sources, read the target page first, append the cases under the target's own conventions (`py_requires` merged, imports merged, `struct_method` helpers carried over and renamed if they collide), document each appended case, then delete the source. Every move in this phase is `git mv` and every removal `git rm`: the rename is recorded (macro 1's commit carries the same `{test15 => test}` renames) and nothing leaves the branch irrecoverably. `palette.py` takes two sources: `palette.py`'s dockButton palettePane and `panetree.py`'s `hiddenDock` case. Finally remove from `docstring_debt.txt` every `test15/webpages/gnrwdg/` line for the seven deleted sources that appears there (`palette.py`, `menuselect.py`, `framepane.py`, `baggrid_scroll.py`, `slotbar.py` are listed; `panetree.py` and `includedview_bagstore.py` are not), and any line for a target page that is now fully documented.
  - Done: the seven source files no longer exist; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the six target files

- [ ] **Phase 5**: Promote the FormHandler family
  - Pattern reference: Phase 3's promoted pages (same documentation contract); `projects/gnrcore/packages/test/webpages/components/advanced_form.py`, which macro 1 repaired, for how a form page in this package reads
  - Files:
    - projects/gnrcore/packages/test/webpages/gnrwdg/formHandler.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/formhandler_selection.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/formclientstore.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/formhandler_baggrid.py (new, from test15)
    - the same four files under projects/gnrcore/packages/test15/webpages/gnrwdg/ (deleted)
    - projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Decisions:
    - No table is rewritten. Every column these pages use exists in `glbl` — `provincia.ordine`, `ordine_tot`, `cap_valido`, and all of `localita.nome/provincia/codice_istat/codice_comune/prefisso_tel/cap` — and Phase 1 mounted the package.
    - These four are the only pages in the whole repository that document `frameForm`, `formStore`, `linkedForm` and the `recordCluster` handler: `test/webpages` has none. That is why they are promoted rather than dropped, and why their case docstrings should say which part of the component each one shows.
    - `testOnly` goes: `formhandler_selection.py` sets `testOnly='_2_'`, which renders one case out of five. `user_polling=0` / `auto_polling=0` stay — they suppress polling noise, they do not hide cases.
    - Dead matter removed: `formHandler.py`'s commented-out tail in `test_111_frame_formdatapath` and the Italian NISO note in `formContent`, `formclientstore.py`'s commented `default_value` leftovers.
  - Details: Every move in this phase is `git mv` and every removal `git rm`: the rename is recorded (macro 1's commit carries the same `{test15 => test}` renames) and nothing leaves the branch irrecoverably. Move the four pages into `projects/gnrcore/packages/test/webpages/gnrwdg/`, drop `testOnly`, remove the dead matter above, give each page a real title docstring and each case a one-liner, delete the test15 originals, and remove the four `test15/webpages/gnrwdg/` lines from `docstring_debt.txt` (all four are listed).
  - Done: the four files exist under `projects/gnrcore/packages/test/webpages/gnrwdg/` and no longer under test15; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the four promoted files

- [ ] **Phase 6**: Close the area
  - Pattern reference: Phase 3's promoted pages; `projects/gnrcore/packages/test/menu.py` (the target package's menu already carries a `Gnr widgets` directoryBranch, so nothing is added there)
  - Files:
    - projects/gnrcore/packages/test/webpages/gnrwdg/includedview_externalchanges.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/thpalette.py (new, from test15)
    - projects/gnrcore/packages/test/webpages/gnrwdg/gridscale.py (new, from test15)
    - the same three files under projects/gnrcore/packages/test15/webpages/gnrwdg/ (deleted)
    - projects/gnrcore/packages/test15/menu.py
    - projects/gnrcore/packages/test/tests/docstring_debt.txt
  - Decisions:
    - `thpalette.py`: the page's only case builds a `thIframeDialog` and then a button whose action is `console.log(dialog)`, so nothing opens. The button becomes one that actually opens the dialog — otherwise the page demonstrates nothing. Its commented-out `test_0_iframe_autosize` goes.
    - `gridscale.py` keeps its `plainTableHandler` on `glbl.provincia`: the `grid_scaleX`/`grid_scaleY` sliders are the point of the page and they need a real grid.
    - `includedview_externalchanges.py` keeps `glbl.localita` and its `userSets` cases unchanged; it already carries per-case docstrings and a title.
    - The `Gnrwdg` branch leaves `test15/menu.py`; the `Dojo` and `Tools` branches stay, their areas are later macros.
  - Details: Every move in this phase is `git mv` and every removal `git rm`: the rename is recorded (macro 1's commit carries the same `{test15 => test}` renames) and nothing leaves the branch irrecoverably. Promote the three pages as in Phase 3, delete the test15 originals, then remove the `tests.branch(u"Gnrwdg", ...)` line from `projects/gnrcore/packages/test15/menu.py` and delete the now-empty `projects/gnrcore/packages/test15/webpages/gnrwdg/` folder (its `__pycache__` included). Remove the last `test15/webpages/gnrwdg/` lines from `docstring_debt.txt` (`thpalette.py` and `gridscale.py` are listed; `includedview_externalchanges.py` is not).
  - Done: `test projects/gnrcore/packages/test15/webpages/gnrwdg` reports the folder is gone; `grep -c 'test15/webpages/gnrwdg' projects/gnrcore/packages/test/tests/docstring_debt.txt projects/gnrcore/packages/test/tests/smoke_known_failures.txt` returns 0 for both; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the three promoted files
  - Verify: deferred: needs Phase 6 — browser pass over the ~20 promoted pages: each one builds its structure past the bootstrap GET and shows what its docstring claims. This is what produced six issues in macro 1 and the render sweep cannot replace it.

- [ ] **Phase 7**: Coherence review and auto-fix (final, mandatory)
  - Pattern reference: same as Phases 1..6 (cross-check against them)
  - Files: only the files written by Phases 1..6 (collect them from their `Files:` fields). Never touch a pre-existing file they did not modify.
  - Decisions:
    - Auto-fix directly: tool-fixable lint (flake8 findings), unused imports, formatting, trivially mechanical fixes. Re-run the tests after each non-tooling fix; if one breaks a test, roll back that fix and flag it instead.
    - Never auto-fix: logic errors, design divergences from the pattern reference, missing edge cases, anything architectural. Those go to `review.md` only.
    - The documentation contract is part of coherence here: a promoted page whose title docstring is generic, or whose case docstrings restate the method name, passes the ratchet and still fails the point of the macro. Flag those rather than rewriting them.
  - Details: convergence loop (max 3 cycles) of flake8 scoped to the file set -> auto-fix -> flake8 -> the three test suites; stop early if a cycle makes no progress. Then write `.phased/active/test15-gnrwdg-macro2/review.md` with three sections: **Auto-fixed** (file, what, tool), **Flagged for human** (file, description, suggested action), **Final state** (flake8 output, suite results, files reviewed).
  - Done: `review.md` exists in the plan directory with the three sections, flake8 zero errors on the file set, `test_pages_ratchet.py` + `test_pages_documented.py` + `test_pages_smoke.py` all green

## Notes
- Mounting `glbl` is instance-wide, so the 31 pages already in `test/webpages` that address it start building too. That is a wanted side effect, not an widening of scope: none of those pages is touched here, and any defect it surfaces is filed as its own issue, the way macro 1 filed #1101-#1105 and #1108.
- The render sweep only proves the bootstrap GET. A Genropy page answers 200 and can still fail while the client builds its structure, which is why the deferred browser pass on Phase 6 is the real gate and why macro 1 kept it manual.
- `prov_test`'s relation to `glbl.regione.sigla` stays commented on purpose. Restoring it is a one-line change, and it belongs to whichever macro decides that `gnrcore:test` may depend on `gnr_it:glbl` at model level, not just at example level.
- `test15/webpages/_resources/storetester.py` is used only by four `tools` pages, so it stays until that area's macro.
- After this macro test15 holds 58 files: `tools` 44, `chart` 4, `dd` 2, `html` 2, and one each of `calendar`, `events`, `mobile`, `revised`, `webservices`, plus `_resources/storetester.py`.
- Phase 1's `loadStartupData` for `glbl` empties and refills the glbl tables of the local sqlite. Nothing else in gnrdevelop reads them today, but it is a destructive local operation and the phase should say so in its notes.

## Suggested execution config
| Phase | Effort | Model |
|-------|--------|-------|
| Phase 1 | medium | opus |
| Phase 2 | low | sonnet |
| Phase 3 | medium | opus |
| Phase 4 | xhigh | opus |
| Phase 5 | high | opus |
| Phase 6 | medium | opus |
| Phase 7 | xhigh | opus |
