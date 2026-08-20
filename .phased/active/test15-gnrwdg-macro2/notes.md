## Run inspection

Run of 2026-08-20, stopped by stop-work after Phase 1. 1/7 phases landed.

- Phase 1 delivered everything it was asked for and was still marked `[!]`, by a `Done:`
  criterion that cannot go green on this machine: `gnr app dbsetup gnrdevelop` aborts on a
  pre-existing `docu` model drift — the generated statement is
  `ALTER TABLE "docu"."docu_documentation" ALTER TABLE base_language TYPE character varying(2)`,
  which repeats `ALTER TABLE` and asks sqlite for an `ALTER COLUMN TYPE` it does not have. The
  phase reproduced it at HEAD with `instanceconfig.xml` reverted, so it pre-dates this
  workflow. The criterion was the foreman's error, not the phase's failure: it made the phase
  hostage to the whole instance migrating. Corrected to a check on the glbl tables themselves
  and the phase closed `[x]`, keeping its `> Issue:` / `> Attempted:` notes as the record.
- The run was stopped before the fresh-eyes repair session did anything — `log/repair-fable.txt`
  is empty and no `> Repair started:` marker was written. The reason for stopping: the only
  route to that criterion ran through the `docu` model or the sqlite adapter, both outside the
  phase's `Files:` set, so an unattended repair would have been either wasted or an
  unauthorised framework change inside the workflow branch.
- The aborted dbsetup wrote to `projects/gnrcore/instances/gnrdevelop/data/docu.db`, which is a
  **tracked** sqlite binary. Restored with `git checkout` so the branch carries no binary diff.
- `data/glbl.db` (6.1 MB, ~23k rows) was created by the phase and was neither tracked nor
  ignored, so the next phase's commit would have swallowed it. Added to `.gitignore`, next to
  the `test.db` line macro 1 added; the data is rebuildable from the package's own
  `startup_data.gz`.
- Deviation the phase recorded and the foreman accepts: `test/webpages/inputfields/dbselect.py`
  also addresses `adm.user` and `adm.htag`, so its unit test asserts `{'adm', 'glbl'}`, not the
  `{'glbl'}` the plan predicted. The plan's expectation was wrong; the guard is right.
- Two findings for issues of their own, neither in this macro's scope: (1) the migration SQL for
  a column-type change is malformed (`ALTER TABLE` twice) and unexecutable on sqlite, so
  `gnr app dbsetup` cannot complete on a sqlite instance whose model has drifted; (2) instance
  sqlite files are versioned (`docu.db`, `dev.db`, `test15.db`) and drift against their models,
  which is what produced (1) here.

Second launch of 2026-08-20, stopped at 2/7 by a transient API error.

- Phase 2 landed exactly as specified: the four files deleted, three ratchet lines removed, 21
  pages left in the area (from 25) and 17 debt lines (from 20), and nothing else in the commit.
- Phase 3's session never started its work: `API Error: 529 Overloaded`, `claude` exited 1, and
  the launcher stopped on its "claude exited non-zero" condition. It left no `[>]` marker and no
  plan edit, so the relaunch needed no stale-phase reset. Not a finding about the plan.
- `log/phase-2.txt` carries only the one-line result. The launcher writes a phase's log after
  that phase's commit, and a light-mode (`low`) phase leaves no reasoning trace at all: had it
  failed, the diff would have been the only thing left to inspect.

## Phase 3
- `bageditor.py`: the plan asked for `Bag(self.site.storageNode('pkg:adm/localization.xml').internal_path)`
  inline in `test_1_firsttest` and `test_2_component`. It is one `localizationBag()` helper instead
  (path in the module-level `LOCALIZATION_BAG`), because the two cases loaded the identical file and a
  page that reads a sample file twice should name it once. Marked `# wf:phase-3:new`.
- `textboxmenu.py` has `test_1_Menu` and `test_1_Tooltip`, two cases sharing the `test_1_` number.
  Not renumbered: `TestHandlerFull` builds its cards from `dir(self)` and dispatches on the full method
  name, so both render. Renumbering would have been a behavioural edit outside "documentation and dead
  code", which is all this phase authorises.
- `textboxmenu.py` `test_3_tooltipTextArea` assigned `multilineTextbox(...)` to an unused local
  `tooltip`; the assignment is dropped (dead matter), the widget stays.
- Case docstrings say which part of the widget each case shows rather than restating the method name,
  because Phase 7 flags generic ones and the point of the macro is a reader learning the widget.

## Phase 4

- The plan's "nothing else is dropped" met two cases that the target already held verbatim.
  `framepane.py`'s `test_5_regions` is `layout/framepane.py`'s `test_1_regions` (macro 1 clearly
  promoted it from there, changing only the `placeholder='puzza'` string), and slotbar's
  `test_7_slotToolbar_multibutton_base` is `components/multibutton.py`'s `test_0_multibutton_base`
  minus its `dataController`. Both were dropped rather than appended: folding a page into its
  counterpart cannot mean showing the same case twice on the merged page. Nothing else went.
- `testOnly` is what had been hiding duplicate global codes. `slotbar.py` shipped `testOnly='_0_'`,
  so only `test_0` ever rendered and nobody noticed that `frameOne` and `frameTwo` were each used by
  two cases, or that `test_12` and `test_14` shared `frameMultibuttonStore`. TestHandlerFull renders
  every case on a single page and gives each one its own datapath but not its own frameCode, so
  dropping `testOnly` (as Phase 5's decisions do for its own pages) requires renaming them. The same
  applies across a merge: panetree's `palettePane('pippo')` and palette's `paletteCode='pippo'` were
  independent while the pages were separate and collide in `components/palette.py`.
- `multiButtonForm` resolves through `py_requires="th/th:TableHandler"` even though it is defined in
  `resources/common/th/th.py`'s `MultiButtonForm` class: `@struct_method` registers at module import,
  so requiring any component of `th/th` registers all of them. The target's existing `py_requires`
  needed no change.
- The multibutton cases folded here also exist, nearly identical, in
  `projects/gnrcore/packages/test15/webpages/revised/gui/multibutton.py`. That page belongs to the
  `revised` area and to a later macro: when its turn comes it is a fold into
  `components/multibutton.py` (now carrying nine documented cases), not a promotion.
- The `test15` sources' `dojo_source = True` was not carried over. `TestHandler` sets it for every
  test page already, and as a page attribute it only selects the non-minified dojo build.

## Phase 5

- Dropping `testOnly='_2_'` from `formhandler_selection.py` exposed the same defect Phase 4 met on
  slotbar: with only `test_2` ever rendering, nobody noticed that all five cases used the frameCode
  `provincia` for their form and three of them `province` for their grid. TestHandlerFull renders
  every case on one page, so the codes were suffixed per case (`provincia_0..4`,
  `province_0/2/3`, `province_regione_4`, `regione_4`) together with everything that derives from
  them: `genro.formById("provincia_N_form")`, `subscribe_form_provincia_N_onLoaded`, the
  `parentStore` attribute, and `default_regione='=#province_2_frame.regione'`. `province_1` kept
  its name, so its `parentStore` line is unchanged.
- `formhandler_selection.testToolbar` computed `left = 'selectrecord,|,' if not startKey else ''`
  and never interpolated it — the slotToolbar string has no `%s`. Removed as dead matter: it is the
  same category as the leftovers the plan lists, and Phase 7 would flag it otherwise. The
  `mytoolbar_selectrecord` struct_method in `formHandler.py` that would have filled that slot is
  left alone; it is a registered struct_method, not dead code inside a case.
- Unused local assignment *targets* were dropped while keeping their calls (`t1`,
  `slot_viewer`, `center`, `saver`, and the `form` of `remote_testPalette`): in Genropy the call is
  what adds the widget to the structure, so only the name was dead. flake8 here selects
  F401,E9,F63,F7,F82, so none of these was failing the linter.
- `formclientstore.py` had no module docstring at all: its `"Store memory"` literal sat *after* the
  imports, which makes it a plain expression. The debt list was right to carry the page.
- `formhandler_baggrid.py`'s header comment claimed the file was `includedview_bagstore.py`, the
  page Phase 4 folded into `components/includedview.py`. Stale copy-paste, not a duplicate: the two
  share no case (diffed against `HEAD~1`). Replaced by a real title docstring.
- `#default_value='MI',` was removed from `formHandler.testToolbar` as well as from
  `formclientstore.testToolbar`; the plan named only the latter, and it is the same leftover.
- `dojo_source = True` was kept where the source had it (`formHandler.py`,
  `formhandler_baggrid.py`), unlike Phase 4's folds: a promotion has no target page whose own
  attributes should win, and the two pages already promoted into this folder (`tooltipDialog.py`,
  `textboxmenu.py`) carry it too.

## Phase 6
- `thpalette.py`'s button: the plan asked for a button that really opens the dialog but not for a
  mechanism. `dlg.js_widget` — the idiom of `test/webpages/layout/dialog.py` — is not usable here:
  `thIframeDialog` returns the gnrwdg node (`resources/common/th/th.py:995`) while the dialog is
  built client-side by `ThIframeDialog.createContent`, and `js_widget` resolves a pyref on the
  node's parent. `createContent` forwards every `dialog_*` keyword to that dialog, so the page
  passes `dialog_nodeId` and the button calls `genro.wdgById(<that nodeId>).show()` — the same
  shape `formHandler.py:test_4_formPane_dialog` already uses in this area.
- `includedview_externalchanges.py` is promoted byte-for-byte, as the plan decided: it already
  carries a title and a docstring on both cases, and its old author header is left alone rather
  than reformatted, keeping the diff a pure rename.
- The `test15/webpages/gnrwdg/` folder is removed with `rm -rf` rather than `git rm`: after the
  three `git mv`, the only thing left in it was `__pycache__`, which is untracked.

## Phase 7

Where the auto-fix / flag line was drawn. The plan authorized auto-fixing "tool-fixable lint,
unused imports, formatting, trivially mechanical fixes" and forbade touching logic, design or
architecture. flake8 was already clean on the whole set at the baseline, so the lint budget bought
nothing and the real question was what else counts as mechanical.

Three things qualified. The two `wf:phase-1:new` markers sat inside docstrings instead of on the
definition line: the fix is a two-line move, it changes no behaviour, and leaving it would have
shipped the marker as part of a helper's documentation — in a macro whose entire point is the
documentation contract. The Italian `print("Dati salvati:")` in the promoted formHandler.py is a
debug string no caller reads; translating it is inert and the English-only rule is contractual, not
stylistic.

Everything else was flagged, and three of those refusals are worth recording because they look
mechanical and are not:

- `rpc_salvaDati` in formHandler.py is provably unreferenced in its own page, which makes deleting
  it look like removing an unused import. It is not: the same name is live in
  `components/advanced_form.py`, so the method is a shared convention across test pages, and
  deciding that this page should not have the hook decides what the page demonstrates. Flagged with
  a suggested action, and its Italian string translated so nothing waits on the ruling.
- The `xxx` slot name and `.abx` datapath in slotbar.py's promoted case are two lines that must
  change together, and they name a client-side slot. The rename is safe in all likelihood and
  nothing here can prove it: the smoke sweep only sees the bootstrap GET, so only the browser pass
  could catch a mistake. The cost of being wrong is a broken promoted example; the cost of flagging
  is one line in review.md.
- `includedview_externalchanges.py` needs three docstrings rewritten to match what Phase 6's other
  two pages did. That is authorship — writing what an example demonstrates — and the phase text says
  so explicitly ("Flag those rather than rewriting them").

The one finding outside the macro's own work is `test15/menu.py`'s surviving `Dojo` branch, pointing
at a directory absent from HEAD since well before this workflow. Phase 6 removed the `Gnrwdg` branch
one line above it. Removing it too would have been a one-line change to a file already in the set,
and it belongs to whichever macro triages the `dojo` area: flagged, not taken.
