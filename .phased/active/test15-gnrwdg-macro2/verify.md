# Deferred verification

## Phase 5
- Needs Phase 6 (with the browser pass over the promoted pages): open
  `/test/gnrwdg/formhandler_selection`. All five cases now render on one page, where before
  `testOnly='_2_'` showed only one. Check that no two of them drive the same form — selecting a row
  in one case's grid must load only that case's form. This is what the per-case frameCode renaming
  is there to prevent, and the render sweep cannot see it: the collision happens while the client
  builds the structure, after the bootstrap GET has already answered 200.
