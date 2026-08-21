# Coherence review — macro 2, the `gnrwdg` area

Phase 7 of `test15-gnrwdg-macro2`. Scope: only the files written by Phases 1..6,
cross-checked against each other and against the pattern each phase named. No
pre-existing file outside that set was read for defects or touched.

The convergence loop closed in **one cycle**: flake8 was already clean on the
whole set at the phase's baseline, the three mechanical fixes below did not
disturb it, and all three suites stayed green. A second cycle would have made no
progress, so it was not run.

## Auto-fixed

| File | What | How |
|------|------|-----|
| `projects/gnrcore/packages/test/tests/pages_ratchet.py:74` | The `wf:phase-1:new` marker sat **inside** the docstring of `page_required_packages`, so the marker leaked into the shipped documentation of the helper. The convention (`refs/common.md` → *New-method markers*) is an end-of-line comment on the definition line, which is also what Phases 3 and 4 used on their own new callables. | Marker moved to the `def` line; the docstring now reads as documentation only. Mechanical, no behaviour change. |
| `projects/gnrcore/packages/test/tests/test_pages_smoke.py:80` | Same divergence on `mounted_packages`. | Same fix. |
| `projects/gnrcore/packages/test/webpages/gnrwdg/formHandler.py:157` | `print("Dati salvati:")` — Italian in a page this macro promoted, against the project's English-only rule. Phase 5 swept the page's Italian (the NISO note) and missed this one. | String translated to `"Data saved:"`. The method it lives in is separately flagged below as dead. |

No lint fix was needed: flake8 reports zero errors on the file set both before
and after.

## Flagged for human

Ordered by how much they cost a reader of the promoted examples.

1. **`test/webpages/gnrwdg/includedview_externalchanges.py` — promoted without
   the documentation contract its two siblings met.** The title docstring is
   `includedview: externalchanges`, which restates the file name and carries no
   body paragraph; the two case docstrings (`standard checkboxcolumn`,
   `virtual checkboxcolumn`) name the widget instead of saying what the case
   shows; the helpers `isDeveloper` and `mystruct` are undocumented. It passes
   `test_pages_documented.py` — the ratchet only asks for *a* non-placeholder
   title and *a* docstring per `test_` method — so nothing catches it.
   Phase 6's other two pages (`thpalette.py`, `gridscale.py`) are exactly the
   model. *Suggested action:* rewrite its three docstrings on the shape of
   `thpalette.py`. Not auto-fixed: writing what an example demonstrates is
   authorship, not a mechanical fix, and the phase's own rule says flag it.

2. **`test/webpages/gnrwdg/tooltipDialog.py` — two case docstrings restate the
   widget name.** `test_1_tooltipPane` says `tooltipPane` and `test_2_div` says
   `div tooltipPane`, while the other seven cases of the same page say what they
   open and how (`test_3_forcedOpen`, `test_8_placing_id`, …). *Suggested
   action:* say what the first two cases show, matching their siblings.

3. **`test/webpages/gnrwdg/formHandler.py:155` — `rpc_salvaDati` is dead in this
   page.** No `dataRpc`, no javascript string and no case in the file references
   it; the same method is genuinely wired in
   `test/webpages/components/advanced_form.py:44`, which is where the name comes
   from. Its docstring ("Server-side receiver printing whatever a case sends
   it") makes it look intentional. *Suggested action:* delete it from
   `formHandler.py`, or wire a case to it. Not auto-fixed: removing a hook from
   an example page decides what the page demonstrates, and the identical name is
   live elsewhere in the package.

4. **`test/webpages/gnrwdg/formHandler.py:83` — placeholder debug output on a
   case that does not document it.** `test_10_frameform_iv` passes
   `_onCalling='console.log("xxxx")'` to its load handler, while its own
   docstring is about the tabContainer and the localita grid. The sibling
   `test_0_frameform` demonstrates the same feature deliberately and says so
   ("with a callback on the load handler", via
   `rpc.addCallback('console.log(result)')`). *Suggested action:* drop the kwarg
   from `test_10`, or document it and give it real output.

5. **`test/webpages/gnrwdg/slotbar.py:79,83` — placeholder identifiers in the
   case Phase 4 promoted.** `test_5_slotToolbar_multiline` declares
   `slots='*,xxx,*'` and binds `value='^.abx'`, where every other slot in the
   file is named for what it holds (`myslot`, the named regions).
   *Suggested action:* rename the slot and the datapath after the multibutton
   they carry. Not auto-fixed: the rename touches a client-side slot name and a
   datapath together, and only the browser pass can prove it.

6. **`test/webpages/gnrwdg/slotbar.py:1` — the one promoted title that names
   widgets instead of describing the page.** `slotBar and slotToolbar` passes the
   ratchet and has no body paragraph, where the other thirteen promoted pages
   open with a sentence plus a paragraph explaining what the widget is for. The
   lightest of the documentation findings: every case docstring below it is
   substantive.

7. **`test15/menu.py:4` — the menu points at a directory that no longer
   exists.** `tests.branch(u"Dojo", tags="", pkg="test15", dir="dojo")` survives,
   but `test15/webpages/dojo` is absent at HEAD (last touched by `c251af165`,
   before this workflow). Phase 6 removed the `Gnrwdg` branch immediately next to
   it and left this one. *Suggested action:* remove the branch, once whoever owns
   the `dojo` area confirms its migration is complete — that area is another
   macro's scope, which is why this is flagged and not fixed.

8. **Pre-existing debt in the six fold targets, deliberately untouched.** The
   pages Phase 4 folded cases *into* keep their original generic titles —
   `palette.py` "Palettes", `dojo/menu.py` "Menu", `layout/framepane.py`
   "framePane", `components/includedview.py` "includedView",
   `components/Grid/bag_grid.py` "bagGrid", `components/multibutton.py`
   "multibutton" — and their original thin case docstrings (e.g.
   `includedview.test_1_includedview_editable_bag`, and `menu.test_5_text_div`
   and `menu.test_11_singleLineAsButton` sharing the same "Popup with options
   from text div"). Same category: `bag_grid.py:14`'s Italian column label
   `name='Quantità'` and the `xxx` datastore paths in its pre-existing
   `test_1_load` / `test_2_remotestruct`, and `dojo/menu.py:150`'s undocumented
   `menulineRpc` printing to stdout on every call. Every case *this macro* added
   to those six files is documented. Listed for completeness because the files
   are in the reviewed set; not this macro's authorship, and rewriting them is
   the widening of scope Phase 7 is told not to do.

Nothing in the reviewed set showed a logic error, a divergence from the
pattern each phase named at the code level, or a missing edge case. The three
suites and the ratchet files agree with the tree: `docstring_debt.txt` holds 91
entries, 46 of them still under `test15/`, none under `test15/webpages/gnrwdg/`,
and none of the 21 reviewed pages appears in it.

## Final state

**flake8** — zero errors on the 25-file set:

```
$ flake8 $(cat fileset.txt)
$ echo $?
0
```

**Suites** — all three green, after the fixes:

```
$ pytest projects/gnrcore/packages/test/tests/test_pages_ratchet.py \
         projects/gnrcore/packages/test/tests/test_pages_documented.py -q
4 passed in 0.61s

$ pytest projects/gnrcore/packages/test/tests/test_pages_smoke.py -q -rs
1 passed, 2 warnings in 43.75s
```

The smoke sweep reports `1 passed` with **no skip**: it rendered, it did not
opt out. The `glbl`-addressing pages render because Phase 1 mounted the package.

**The area is empty.** `test15/webpages/gnrwdg/` no longer exists, and `test15`
holds the 58 files the plan predicted: `tools` 44, `chart` 4, `dd` 2, `html` 2,
one each of `calendar`, `events`, `mobile`, `revised`, `webservices`, plus
`_resources/storetester.py`.

**Files reviewed (25).** Test infrastructure and config: `pages_ratchet.py`,
`test_pages_smoke.py`, `test_pages_ratchet.py` (Phase 1). Pages promoted from
`test15`: `gnrwdg/{bageditor,colormenu,fieldstree,formdocumentstore,gridgallery,`
`textboxmenu,tooltipDialog}.py` (Phase 3), `gnrwdg/slotbar.py` (Phase 4),
`gnrwdg/{formHandler,formhandler_selection,formclientstore,formhandler_baggrid}.py`
(Phase 5), `gnrwdg/{includedview_externalchanges,thpalette,gridscale}.py`
(Phase 6). Fold targets: `components/palette.py`, `dojo/menu.py`,
`layout/framepane.py`, `components/includedview.py`,
`components/Grid/bag_grid.py`, `components/multibutton.py` (Phase 4).
`test15/menu.py` (Phase 6). Not re-reviewed as files, checked as state:
`docstring_debt.txt`, `.github/workflows/tests.yml`,
`instances/gnrdevelop/config/instanceconfig.xml`.

## Ruling on the flagged findings (after the browser pass)

Decided by the owner once the browser pass had confirmed the pages, and applied
in the same working tree:

1. **`includedview_externalchanges.py` docstrings** — rewritten: a title plus a
   body paragraph saying what `externalChanges=True` and the two `userSets`
   columns are for, one line on each case naming what distinguishes it (whole
   selection vs chunked store driving `currentfilter`), and one line each on
   `isDeveloper` and `mystruct`.
2. **`tooltipDialog.py`** — `test_1_tooltipPane` and `test_2_div` now say what
   they show instead of restating the widget name.
3. **`rpc_salvaDati`** — deleted from `formHandler.py`. The live copy stays in
   `components/advanced_form.py`, which is where the convention lives.
4. **`formHandler.py` `test_10_frameform_iv`** — the `_onCalling='console.log("xxxx")'`
   kwarg is gone; `test_0_frameform` remains the case that demonstrates a load
   callback deliberately.
5. **`slotbar.py` placeholders** — the slot is `tagpicker` and its datapath
   `.picked_tags` (both occurrences, the multibutton and the echoing textbox).
   `multibutton` itself cannot be a slot name: `__getattr__` resolves the widget
   namespace before the slot children (`gnrpy/gnr/web/gnrwebstruct/base.py:174`
   vs `:185`), so a slot named after a tag would return a builder, not the slot.
6. **`slotbar.py` title** — replaced by a sentence plus a paragraph on the
   `slots` string, the `*` / `|` / number forms, the toolbar flavour and
   `replaceSlots`.
7. **`test15/menu.py`** — the stale `Dojo` branch is removed; only `Tools`
   survives, which is the one area still holding pages.
8. **Pre-existing debt in the six fold targets** — left as it is, confirmed:
   it belongs to whichever macro owns those areas.

Not filed as issues, by the owner's ruling: the malformed `ALTER TABLE` in the
sqlite migration path is a known limitation and stays as it is, and the missing
duplicate-frameCode check does not become a suite check — it is a developer rule,
written up as the Sourcerer skill *frameCode must be unique on the page*
(`GenroPy/User Interface/Layout`, linked to `GenroPy/Conventions/Naming Rules`).

After these edits: flake8 zero errors on the touched files,
`test_pages_documented.py` + `test_pages_ratchet.py` 10 passed,
`test_pages_smoke.py -q -rs` 1 passed with no skip.
