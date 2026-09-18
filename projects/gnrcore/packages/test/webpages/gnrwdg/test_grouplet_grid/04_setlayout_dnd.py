"""setLayout() + row DnD reconciliation — regression repro.

A draggable groupletGrid (dragCode set) that starts in `layout='tabs'`
with a runtime tabs/cards switcher. It exposes a known, pre-existing bug:
tile (row) DnD is wired ONCE at mount — in `GroupletGridTile._mountWrapper`
`onCreated`, gated on `!controller._isTabsLayout()` evaluated AT MOUNT TIME
— and is never reconciled by `setLayout()` (neither `setLayout` nor
`_teardownLayoutAffordances` touch `_tileDnDHandlers`).

Consequences:
  - tabs -> cards: tiles mounted under tabs never got their card DnD
    listeners, and setLayout does NOT re-mount them, so drop-on-card
    reordering is DEAD after the swap (a drop on a card no longer inserts
    relative to it; only the "+" append still works).
  - cards -> tabs (mirror): the row listeners wired at mount stay LIVE
    under tabs and can hijack a drop on the visible tile body. The budget
    editor (03_budget_editor) hits this via its chapter tabs/cards switch.

Repro (this page):
  1. The grid starts in "Tabs".
  2. Switch the selector to "Cards".
  3. Drag a card onto another card to reorder it.
  4. BUG: it does not insert before/after the target — at best it appends
     via the "+" path, or nothing happens.

Expected after the fix: `setLayout()` reconciles row DnD with the new
layout (wire each tile on entering cards, unwire on entering tabs), so
drop-on-card works after any number of layout swaps.

Note: cross-grid drag and the "+"-append drop are NOT affected — the "+"
is rewired by every layout build. Only the per-row (tile) DnD is stale.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = ('gnrcomponents/testhandler:TestHandlerFull,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')

    def test_setlayout_dnd(self, pane):
        rows = Bag()
        for i, title in enumerate(('Alpha', 'Bravo', 'Charlie', 'Delta'),
                                   start=1):
            rows.setItem(f'r_{i:03d}', Bag(dict(title=title, note='')))
        pane.data('.sl_rows', rows)
        # Seed the picker with the same default the grid uses.
        pane.data('.sl_layout', 'tabs')
        grid_id = 'grpgrid_setlayout_dnd'

        pane.div('setLayout + DnD repro: the grid starts in Tabs. Switch '
                 'to Cards, then drag a card onto another to reorder. BUG: '
                 'row DnD is never wired after the swap, so reordering does '
                 'not work (only the "+" append does).',
                 color='#666', font_style='italic', margin_bottom='8px')

        toolbar = pane.div(display='flex', gap='0.6em',
                           align_items='center', margin_bottom='8px')
        toolbar.div('!!Layout', color='#666', font_size='0.9em')
        toolbar.filteringSelect(
            value='^.sl_layout',
            values='tabs:!!Tabs,cards:!!Cards',
            width='160px')
        # On layout change, call the controller's public setLayout API
        # (same pattern as test_05_team_tabs).
        pane.dataController("""
            var n = genro.nodeById(grid_id);
            var c = n && n.gridController;
            if (c && c.layout !== layout) {
                c.setLayout(layout);
            }
        """, layout='^.sl_layout', grid_id=grid_id)

        pane.groupletGrid(storepath='.sl_rows',
                          handler=self.sl_row_handler,
                          nodeId=grid_id,
                          layout='tabs',
                          dragCode='setlayout_dnd',
                          titleField='title',
                          defaultRow=dict(title='', note=''))

    @public_method
    def sl_row_handler(self, pane, **kwargs):
        box = pane.div(display='flex', flex_direction='column',
                       gap='0.4em', padding='4px 0')
        box.textbox(value='^.title', lbl='Title', width='100%')
        box.textbox(value='^.note', placeholder='!!Note', width='100%')
