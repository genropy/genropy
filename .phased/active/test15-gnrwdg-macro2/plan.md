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
- [ ] **Phase 1**: Mount glbl in gnrdevelop and skip pages whose packages are absent
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
  - Done: `gnr app dbsetup gnrdevelop` exits 0; `pytest projects/gnrcore/packages/test/tests/test_pages_ratchet.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_documented.py -q` passes; `pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs` reports `1 passed` (a skipped sweep does NOT satisfy this: it means the daemon never came up, and a check that skips protects nothing); `flake8` reports zero errors on the Files: set
  - Verify: now — open /test15/gnrwdg/formHandler: the Provincia dbselect drops down with real provinces, which is what proves the mount and the data load rather than the model merely building

- [ ] **Phase 2**: Remove the four dead pages of the area
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

- [ ] **Phase 3**: Promote the seven self-contained pages
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

- [ ] **Phase 4**: Fold the six overlapping pages into their counterparts  `vast`
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
| Phase 7 (review) | xhigh | opus |
