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
