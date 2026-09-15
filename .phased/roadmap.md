# Roadmap — test15 -> test example triage

The recipe, established by macro 1: build the regression net first, then per area
remove the dead pages, promote the live ones into `test/webpages/` documented,
fold the ones that overlap into the counterpart that already exists there, and
leave the area empty. Every ratchet file is a flat list of ONE page path per line
and fails in both directions, so every macro can only shrink it: a page that
offends while off the list is a regression, a list entry that no longer offends is
stale. The ratchets are `docstring_debt.txt` and `smoke_known_failures.txt` (macro
1), and from macro 3 `framecode_debt.txt`. All three, and the render sweep, read
their page set from the single module-level tuple `pages_ratchet.PACKAGES` — four
readers, one tuple.

`glbl` throughout means `gnr_it:glbl`, a package living outside this repository that
gnrdevelop deliberately does NOT mount: macro 2 established that mounting it
deadlocks the sqlite of the instance the whole app/web suite boots, so pages bound
to it render 200 against empty tables and that is the end of it. test15's own
`model/_packages/glbl/` column injections were deleted by macro 2 and no longer exist.

## Macro 1 (done): the regression net, websocket and components
Documentation ratchet wired into CI, render sweep with port backpressure, plus the
`websocket` and `components` areas; 38 dead pages removed, `testdata/docstore` moved,
`gnrcore:test` mounted in gnrdevelop. Filed #1101-#1105, #1108. Merged as f5d37d1a1.

## Macro 2 (done): the gnrwdg area
25 pages, `test/webpages/components/multibutton.py` among the counterparts it folded
into. The sweep renders every discovered page; only a page whose render fails leaves
the checked set, through `smoke_known_failures.txt`. Mounts `gnrcore:biz`. Merged as
7ef328f0c.

## Macro 3 (current): tools, the server-state half — detailed in active/test15-tools-macro3/plan.md
20 of the area's 44 pages: the page/user/connection stores, the registers, the
messages the server pushes to a client, and the RPC plumbing around them. Plus
`framecode_debt.txt`, guarding the one defect class this migration has produced
three times — macro 1 fixed one instance, macro 2 two more — and that nothing in the
suite sees, because a frameCode collision raises while the client builds the
structure, after the page has already answered 200.
- Delivers: `framecode_debt.txt` and its check, consumed by macros 4, 5 and 6; the
  half-emptied `tools` area, consumed by macro 4.
- Ends at: `test15/webpages/tools/` holds exactly the 24 pages of the widget half;
  `test15/webpages/_resources/` holds `demotpl1.html`, `demotpl2.html`,
  `protovis-sample3.js` and `test.html` and nothing else (`storetester.py` moved
  under `test`, `csstest.css` deleted with its only reader);
  `test15/resources/test_proxy.py` moved under `test`, where a th resource macro 1
  promoted already mixes it in and currently cannot resolve it; `framecode_debt.txt`
  is in place, reads `pages_ratchet.PACKAGES` like its two siblings, runs in CI, and
  lists the one offender left in the tree, `revised/gui/multibutton.py`, which is in
  macro 5's set. `chart/chartjs.py` looks like a second one to a grep and is not one to
  the check: its three `frameCode='pippo'` lines are all commented out, and a call that
  is commented out builds no frame and raises nothing. The unit tests pin that
  distinction, with `chartjs.py` as the negative case.

## Macro 4: tools, second half, and the area emptied
- Objective: triage the remaining 24 pages of `tools` — widgets, editors, media, maps,
  templates — and leave the area empty. It is the half whose pages bind tables of
  packages the instance does not mount (`glbl`, `fatt`, `polimed`, `studio`).
- Starts from: `test15/webpages/tools/` holding exactly those 24 pages;
  `test15/webpages/_resources/` holding the four files above; the three ratchets in
  place; `storetester.py` and `test_proxy.py` already under `test`.
- Ends at: neither `test15/webpages/tools/` nor `test15/webpages/_resources/` exists —
  `demotpl1.html` travels with `gettemplate.py`, the one page that reads it, and
  `demotpl2.html`, `protovis-sample3.js` and `test.html` go, having no reader at all
  (`test` carries its own `resources/test.html`). The `test15/resources/` files these
  24 pages read travel with them: `test_hviewer.css`/`test_hviewer.js`,
  `tplnotable.xml`, and the `tables/_packages/glbl/**` th resources with their `tpl/`
  templates, which `gettemplate.py` addresses by name. `resources/mycomponent.py` and
  `resources/bagfields/alfa.py` go too, nothing references either. `test/webpages/tools/`
  holds the merged set.
- Delivers: `test15/webpages/` reduced to macro 5's eight folders, consumed by macro 5.
- Consumes: the promotion recipe and the two original ratchets from macro 1, the
  frameCode ratchet from macro 3.
- Requires of earlier work: the frameCode check must cover `test15` as well as `test` —
  these 24 pages carry frames and grids where macro 3's pages carry forms, so they are
  the ones most likely to introduce a collision while being folded; and BOTH macro 1
  ratchets must keep one line per page path, because macro 4 removes its lines by path
  and a line left behind for a deleted page goes stale and reds CI.
- Policy on defects found while promoting: a frameCode collision, or a page that stops
  rendering, is FIXED in that page, never recorded — every ratchet only shrinks, so a
  new `test/...` line is not an option in either file. The ratchets exist for pages
  still sitting in `test15`, not for pages this programme moves.
- Open decisions: what to do with the pages bound to unmounted packages — promote them
  against empty tables as the sweep already tolerates (mounting `gnr_it:glbl` is
  foreclosed, see the header), rewrite them onto a mounted table, or drop them; whether
  test15's `ckeditor.py` (7 cases) folds into the existing `test/webpages/tools/ckeditor.py`
  or replaces it.

## Macro 5: chart and the leftovers
- Objective: the last 13 pages — `chart` 4, `dd` 2, `html` 2, and one each of
  `calendar`, `events`, `mobile`, `revised`, `webservices`. Small enough for one pass.
- Starts from: `test15/webpages/` holding exactly those eight folders and nothing else —
  no `tools/`, no `_resources/`.
- Ends at: `test15/webpages/` holds no page and no folder; `resources/canvas.js` has
  travelled with `chart/canvas.py` and `html/webRTC.py`, its last readers; none of the
  three ratchets carries a `test15/...` line, `framecode_debt.txt` included — its one
  entry, `revised/gui/multibutton.py`, is the only offender in the tree and it is
  cleared here, so the file ends empty.
- Delivers: an empty `test15/webpages/`, consumed by macro 6.
- Consumes: `test15/webpages/` reduced to its eight folders (macro 4); the frameCode
  ratchet (macro 3); the promotion recipe and the two original ratchets (macro 1).
- Requires of earlier work: the frameCode check must be a RATCHET against a committed
  list, not a hard failure — its one offender lives here, and a hard failure would have
  made macro 3 fix a page outside its own scope.
- Open decisions: whether `revised/gui/multibutton.py` folds case-by-case into
  `test/webpages/components/multibutton.py`, which macro 2 already touched.

## Macro 6: retire test15
- Objective: delete the package and collapse the suites onto one package.
- Starts from: `test15/webpages/` empty of pages and folders, and no `test15/...` line
  left in any of the three ratchets.
- Ends at: the `test15` package does not exist; `pages_ratchet.PACKAGES` is `('test',)`;
  `gnrcore:test15` unmounted from gnrdevelop and dropped from its `<menu package=.../>`
  list.
- Delivers: the final deliverable of the programme.
- Consumes: the empty `test15/webpages/` and the cleared ratchets, from macro 5.
- Requires of earlier work: `pages_ratchet.PACKAGES` must stay the ONE module-level
  tuple that the documentation ratchet, the frameCode ratchet, the render sweep and
  `smoke_known_failures.txt`'s own suite all read, so dropping `test15` is a one-line
  edit rather than four; and nothing a `test` page reads may still live under `test15/` —
  macro 3 takes `test_proxy.py` out, macro 4 takes `_resources/` and the tools-half
  resources out, macro 5 takes `canvas.js`, and what remains is this macro's own to
  dispose of.
- Open decisions: what becomes of `model/nodetbl.py`, `model/recursive.py` and the th
  resources under `resources/tables/nodetbl/` and `resources/tables/recursive/` — move to
  `test` or drop; whether `localization.xml` has anything worth carrying over; how this
  ties into #1107 (deprecate the hand-maintained Tests menu).
