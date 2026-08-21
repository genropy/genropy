# Deferred verification

## Phase 5
- done — `/test/gnrwdg/formhandler_selection`: all five cases render on one page and no two
  drive the same form. Checked in the browser; the per-case frameCode renaming holds.

## Phase 6
- done — browser pass over the ~20 pages promoted by Phases 3, 4, 5 and 6: each builds its
  structure past the bootstrap GET and shows what its docstring claims. The pass produced the
  fixes now in the working tree (bageditor's bagNodeEditor case rebuilt around the tree that
  publishes the current path, `struct='min'` and `struct='regione'` replaced by real column lists,
  the `gridstore1` typo in formhandler_baggrid, the toolbar-after-grid ordering the `addrow` slot
  needs, `dialog_windowRatio` on thpalette) plus the `test_handler_card_warning` the TestHandler
  now shows when a case addresses a table whose package ships startup data this instance never
  loaded.
- done — `/test/gnrwdg/thpalette`: the `open` button raises the dialog holding the th page of
  glbl.provincia.
- done — `/test/gnrwdg/gridscale`: the Scale X / Scale Y sliders scale the grid.

Nothing is left deferred: the macro's verification is closed.
