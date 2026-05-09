"""groupletGrid demo page — gallery of realistic use cases.

  test_1_smoke              — invoice rows, baseline single-column
  test_2_empty              — empty state + defaultRow (phantom add only)
  test_3_todolist           — handler= callable, reactive line-through
                              when a todo is marked done
  test_4_excel_grid         — fakexcel: framed mode + sticky toolbar
  test_5_responsive_invoice — cols=3 + min_width: re-flow on resize
  test_6_framed             — internal scroll with sticky bottom slot
  test_8_kanban_board       — 3 columns sharing dragCode='kanban',
                              drag cards across workflow lanes
  test_9_team_with_contacts — nested groupletGrid: each team member
                              has a sub-grid of contact channels
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_1_smoke(self, pane):
        """Baseline: 3 invoice rows, single column.

        Sanity check: card-like blocks, hover/focus/selected states,
        add/remove via phantom and kebab. Everything else builds on
        this shape.
        """
        rows = Bag()
        rows.setItem('r_001', Bag(dict(product='Apples',
                                       qty=10, price=2.50)))
        rows.setItem('r_002', Bag(dict(product='Bread',
                                       qty=2, price=1.20)))
        rows.setItem('r_003', Bag(dict(product='Coffee',
                                       qty=1, price=12.00)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 1: 3 invoice rows (single column, card blocks).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          addEnabled=True, removeEnabled=True)

    def test_2_empty(self, pane):
        """Empty state with defaultRow.

        Empty Bag → only the phantom add-cell is visible. Clicking it
        inserts the first row pre-filled with `defaultRow`.
        """
        pane.data('.invoice_lines', Bag())
        pane.div('Test 2: empty state — click the phantom + to add the '
                 'first row, prefilled with defaultRow={qty:1, price:0}.',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(
            storepath='.invoice_lines',
            resource='invoice_row',
            addEnabled=True, removeEnabled=True,
            defaultRow=dict(qty=1, price=0))

    def test_3_todolist(self, pane):
        """Use case: classic todolist with checkbox + line-through.

        Each row is a to-do (`done` flag + `text`). Toggling the checkbox
        strikes the text and dims the row. Demonstrates `handler=`
        callable (instead of a resource file on disk) plus reactive
        per-row styling driven by the row data.
        """
        rows = Bag()
        rows.setItem('r_001', Bag(dict(done=False, text='Buy milk')))
        rows.setItem('r_002', Bag(dict(done=True,
                                       text='Send weekly report')))
        rows.setItem('r_003', Bag(dict(done=False,
                                       text='Pick up dry cleaning')))
        rows.setItem('r_004', Bag(dict(done=False,
                                       text='Reply to Marta about Friday')))
        pane.data('.todos', rows)
        pane.div('Test 3: classic todolist — check the box to strike '
                 'and dim the row.',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.todos',
                          handler=self.todo_row_handler,
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(done=False, text=''))

    @public_method
    def todo_row_handler(self, pane, **kwargs):
        row = pane.div(display='flex', align_items='center', gap='0.6em',
                       padding='2px 0')
        row.checkBox(value='^.done')
        # Reactive style: when `done` is true, strike the text and dim
        # the colour. Bind `text_decoration` and `color` directly to the
        # `done` value via `=.done`-style placeholder evaluation in the
        # widget's dynamic attribute system.
        row.textbox(value='^.text', placeholder='!!What needs doing?',
                    width='100%', flex='1',
                    text_decoration='=.done?"line-through":"none"',
                    color='=.done?"#999":"inherit"',
                    transition='color 160ms ease')

    def test_4_excel_grid(self, pane):
        """Fakexcel: dense flat rows with a sticky toolbar.

        `height='320px'` activates the frame mode (internal scroll). The
        toolbar in the `top` slot stays anchored and exposes `+` / `−`
        which publish on the controller's action topic — same path the
        kebab and phantom add-cell use, just from a different UI.
        """
        rows = Bag()
        for i, (prod, qty, price) in enumerate([
            ('Apples', 10, 2.50), ('Bread', 2, 1.20),
            ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
            ('Eggs', 12, 0.30), ('Flour', 3, 2.10),
            ('Grapes', 4, 3.40), ('Honey', 1, 8.00),
        ], start=1):
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        pane.data('.lines', rows)
        pane.div('Test 4: fakexcel — flat rows with a sticky toolbar.',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid_id = 'grpgrid_excel'
        topic = f'groupletGrid_{grid_id}_action'
        grid = pane.groupletGrid(storepath='.lines',
                                 resource='excel_row',
                                 _class='gg-flat-rows',
                                 height='320px',
                                 nodeId=grid_id,
                                 addEnabled=False, removeEnabled=False,
                                 defaultRow=dict(qty=1, price=0))
        toolbar = grid.top.div(_class='gg-excel-toolbar',
                               display='flex', align_items='center',
                               gap='0.4em', padding='0.4em 0.6em',
                               border_bottom='1px solid var(--border-color, #e5e7eb)',
                               background='var(--surface-alt, #f9fafb)')
        toolbar.div('!!Items', font_weight='600', flex='1',
                    color='var(--text-secondary, #6b7280)',
                    font_size='0.9em')
        toolbar.lightButton(
            '+', _class='gg-toolbar-btn', tip='!!Add row',
            action=f"genro.publish('{topic}', {{action:'add'}});")
        toolbar.lightButton(
            '−', _class='gg-toolbar-btn', tip='!!Delete selected row',
            action=f"genro.publish('{topic}', {{action:'delete'}});")

    def test_5_responsive_invoice(self, pane):
        """Responsive multi-column layout.

        `cols=3 + min_width='300px'`: wide monitor → 3 columns, tablet
        → 2, mobile → 1. Demonstrates the auto-fill responsive grid mode.
        """
        rows = Bag()
        for i, (prod, qty, price) in enumerate([
            ('Apples', 10, 2.50), ('Bread', 2, 1.20),
            ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
            ('Eggs', 12, 0.30), ('Flour', 3, 2.10),
        ], start=1):
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 5: invoice rows, cols=3, min_width=300px '
                 '(responsive — re-flow as the viewport narrows).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          cols=3, min_width='300px',
                          addEnabled=True, removeEnabled=True)

    def test_6_framed(self, pane):
        """Frame mode with bottom slot.

        `height='400px'` activates the framed mode: the body scrolls
        internally while the `bottom` slot stays anchored at the foot.
        Use case: a long list with a sticky summary footer.
        """
        rows = Bag()
        for i in range(1, 31):
            rows.setItem(f'r_{i:03d}',
                         Bag(dict(product=f'Item {i}',
                                  qty=i, price=i * 1.5)))
        pane.data('.invoice_lines', rows)
        pane.div('Test 6: framed mode (height=400px) — internal scroll '
                 'with a sticky bottom slot.',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid = pane.groupletGrid(storepath='.invoice_lines',
                                 resource='invoice_row',
                                 height='400px',
                                 addEnabled=True, removeEnabled=True)
        grid.bottom.div('30 rows',
                        padding='6px 12px',
                        border_top='1px solid var(--border-color, #e5e7eb)',
                        background='var(--surface-alt, #f9fafb)',
                        font_size='0.9em',
                        color='var(--text-secondary, #6b7280)')

    def test_8_kanban_board(self, pane):
        """Use case: a 3-column kanban board (To do / In progress / Done).

        Each column is a groupletGrid; all share `dragCode='kanban'` so a
        card can be dragged across columns to advance through the
        workflow. Drop on a card inserts before it; drop on free space
        (or on an empty column) appends.
        """
        todo = Bag()
        todo.setItem('r_001', Bag(dict(title='Draft Q3 plan',
                                       assignee='Alice', priority='high')))
        todo.setItem('r_002', Bag(dict(title='Review PR #412',
                                       assignee='Bob', priority='med')))
        todo.setItem('r_003', Bag(dict(title='Update onboarding doc',
                                       assignee='Marta', priority='low')))
        wip = Bag()
        wip.setItem('r_001', Bag(dict(title='Migrate auth service',
                                      assignee='Bob', priority='high')))
        wip.setItem('r_002', Bag(dict(title='Design new dashboard',
                                      assignee='Alice', priority='med')))
        done = Bag()
        done.setItem('r_001', Bag(dict(title='Ship 1.4.0 release',
                                       assignee='Marta', priority='high')))
        pane.data('.kanban_todo', todo)
        pane.data('.kanban_wip', wip)
        pane.data('.kanban_done', done)
        pane.div('Test 8: kanban board — drag cards across columns to '
                 'advance their state. All columns share dragCode="kanban".',
                 color='#666', font_style='italic', margin_bottom='8px')
        board = pane.div(display='grid',
                         grid_template_columns='1fr 1fr 1fr',
                         gap='12px',
                         align_items='start')
        for label, store in [('To do', '.kanban_todo'),
                             ('In progress', '.kanban_wip'),
                             ('Done', '.kanban_done')]:
            col = board.div(_class='gg-kanban-col',
                            background='var(--surface-alt, #f4f6f9)',
                            border_radius='6px',
                            padding='10px')
            col.div(label,
                    font_weight='600', font_size='12px',
                    text_transform='uppercase',
                    letter_spacing='0.5px',
                    color='#666',
                    margin_bottom='8px')
            col.groupletGrid(storepath=store,
                             resource='kanban_card',
                             addEnabled=True, removeEnabled=True,
                             dragCode='kanban',
                             defaultRow=dict(title='', assignee='',
                                             priority='med'))

    def test_9_team_with_contacts(self, pane):
        """Use case: a team roster where each member has a list of
        contact channels (email, phone, …).

        Outer grid = list of team members. Each member's grouplet renders
        an avatar (initials), name + role + team in the header, and a
        nested `groupletGrid` over `.contacts`. Demonstrates the
        bread-and-butter use case for nested groupletGrids: a "card with
        sub-rows" pattern that you can edit, add to, and remove from at
        either level.
        """
        people = Bag()
        c_alice = Bag()
        c_alice.setItem('r_001', Bag(dict(channel='email',
                                          value='alice@acme.io')))
        c_alice.setItem('r_002', Bag(dict(channel='phone',
                                          value='+39 02 1234 5678')))
        c_bob = Bag()
        c_bob.setItem('r_001', Bag(dict(channel='email',
                                        value='bob@acme.io')))
        c_bob.setItem('r_002', Bag(dict(channel='mobile',
                                        value='+39 333 987 6543')))
        c_bob.setItem('r_003', Bag(dict(channel='web',
                                        value='bobthebuilder.dev')))
        people.setItem('r_001', Bag(dict(name='Alice Rossi',
                                         role='Producer',
                                         team='Strategy',
                                         contacts=c_alice)))
        people.setItem('r_002', Bag(dict(name='Bob Bianchi',
                                         role='Director',
                                         team='Production',
                                         contacts=c_bob)))
        pane.data('.team', people)
        pane.div('Test 9: team roster with per-person contact channels '
                 '(card + nested rows).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.team',
                          resource='person_with_contacts',
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(name='', role='', team=''))
