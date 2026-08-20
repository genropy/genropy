# Roadmap — test15 -> test example triage

The recipe, established by macro 1: build the regression net first, then per area
remove the dead pages, promote the live ones into `test/webpages/` documented,
fold the ones that overlap into the counterpart that already exists there, and
leave the area empty. The two ratchets (`docstring_debt.txt`,
`smoke_known_failures.txt`) fail in both directions, so every macro can only
shrink them.

- Macro 1 (done, on `refactor/test15-example-migration-macro1`): the regression net — documentation ratchet wired into CI, render sweep with port backpressure — plus the `websocket` and `components` areas, 38 dead pages removed, `testdata/docstore` moved, `gnrcore:test` mounted in gnrdevelop. Filed #1101-#1105, #1108.
- Macro 2 (current): the `gnrwdg` area, 25 pages — detailed in `active/test15-gnrwdg-macro2/plan.md` as Phases 1..7. Mounts `gnr_it:glbl` in gnrdevelop and adds the reusable absent-package guard to the sweep, which every later macro inherits.
- Macro 3: `tools`, first half (~22 of 44 pages). The area's shared resource `webpages/_resources/storetester.py` is used by four of them, so it moves with whichever half takes the last of the four.
- Macro 4: `tools`, second half, and the area emptied.
- Macro 5: `chart` (4 pages) and the leftovers — `dd` 2, `html` 2, and one each of `calendar`, `events`, `mobile`, `revised`, `webservices`. Small enough to close in one pass; `revised/gui/multibutton.py` folds into `test/webpages/components/multibutton.py`, which macro 2 already touched.
- Macro 6: retire test15 — `menu.py`, `requirements.txt`, the `model` leftovers (`nodetbl.py`, `recursive.py`), unmount `gnrcore:test15` from gnrdevelop, and drop `test15` from `pages_ratchet.PACKAGES` so both ratchets cover one package. Ties into #1107 (deprecate the hand-maintained Tests menu).
