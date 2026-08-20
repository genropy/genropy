# Deferred verification

## Phase 5
- Needs Phase 6 (with the browser pass over the promoted pages): open
  `/test/gnrwdg/formhandler_selection`. All five cases now render on one page, where before
  `testOnly='_2_'` showed only one. Check that no two of them drive the same form — selecting a row
  in one case's grid must load only that case's form. This is what the per-case frameCode renaming
  is there to prevent, and the render sweep cannot see it: the collision happens while the client
  builds the structure, after the bootstrap GET has already answered 200.

## Phase 6
- now — browser pass over the ~20 pages promoted by Phases 3, 4, 5 and 6: each builds its
  structure past the bootstrap GET and shows what its docstring claims. This is what produced six
  issues in macro 1 and the render sweep cannot replace it.
- now — /test/gnrwdg/thpalette: the `open` button raises a dialog holding the th page of
  glbl.provincia (the previous button only logged to the console, so this path has never run).
- now — /test/gnrwdg/gridscale: the Scale X / Scale Y sliders visibly scale the grid.
