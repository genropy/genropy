"""groupletGrid demo page — minimum gallery covering every use case.

  test_1_invoice_baseline      — invoice rows, single column, plain
                                 (smoke: add/remove via phantom + kebab)
  test_2_todolist_handler      — handler= callable (not a resource file)
  test_3_invoice_responsive    — same rows, cols=3 + min_width
                                 (responsive: reflow with viewport width)
  test_4_excel_framed_top_slot — flat-row layout, framed scroll,
                                 toolbar in `top` slot wired to action-bus
  test_5_long_list_bottom_slot — framed long list with sticky `bottom` slot
  test_6_kanban_dnd            — 3 grids sharing dragCode='kanban',
                                 cross-grid drag of editable cards
  test_7_nested_team           — outer grid of team members, each with a
                                 nested groupletGrid of contact channels
"""
import datetime

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def _invoice_seed(self, n):
        catalogue = [('Apples', 10, 2.50), ('Bread', 2, 1.20),
                     ('Coffee', 1, 12.00), ('Donuts', 6, 1.50),
                     ('Eggs', 12, 0.30), ('Flour', 3, 2.10),
                     ('Grapes', 4, 3.40), ('Honey', 1, 8.00)]
        rows = Bag()
        for i in range(1, n + 1):
            prod, qty, price = catalogue[(i - 1) % len(catalogue)]
            if i > len(catalogue):
                prod = f'{prod} #{i // len(catalogue) + 1}'
            rows.setItem(f'r_{i:03d}', Bag(dict(product=prod,
                                                qty=qty, price=price)))
        return rows

    def test_1_invoice_baseline(self, pane):
        """Invoice rows, single column, plain (smoke test).

        The simplest shape: a card per row, full width, add/remove via
        phantom `+` and per-row kebab. Empty state emerges naturally if
        all rows are deleted — clicking the phantom `+` then inserts a
        row prefilled from `defaultRow`.
        """
        pane.data('.invoice_lines', self._invoice_seed(3))
        pane.div('Test 1: 3 invoice rows, single column (baseline).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(qty=1, price=0))

    def test_2_todolist_handler(self, pane):
        """Todolist via inline `handler=` callable (not a resource file).

        Demonstrates that the row template can be a Python callable on
        the page itself, instead of a resource in `resources/grouplets/`.
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
        pane.div('Test 2: small todolist driven by handler=callable.',
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
        row.textbox(value='^.text', placeholder='!!What needs doing?',
                    width='100%', flex='1')

    def test_3_invoice_responsive(self, pane):
        """Same invoice rows, but in a responsive grid.

        `cols=3 + min_width=300px`: wide viewport → 3 columns, tablet → 2,
        mobile → 1. Demonstrates the auto-fill responsive mode on the
        same data shape as test_1 — only the layout kwargs change.
        """
        pane.data('.invoice_lines', self._invoice_seed(6))
        pane.div('Test 3: same rows as test_1, cols=3 + min_width=300px '
                 '(resize the viewport to see re-flow).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          cols=3, min_width='300px',
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(qty=1, price=0))

    def test_4_excel_framed_top_slot(self, pane):
        """Fakexcel: flat rows + framed scroll + toolbar in `top` slot.

        `height=320px` activates frame mode (body scrolls, slots stay
        anchored). Toolbar buttons publish on the controller's action
        topic — same path the kebab and phantom add-cell use, just
        invoked from a custom UI affordance.
        """
        pane.data('.lines', self._invoice_seed(8))
        pane.div('Test 4: fakexcel — flat rows, framed scroll, toolbar '
                 'in top slot wired to the action bus.',
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

    def test_5_long_list_bottom_slot(self, pane):
        """Framed long list with a sticky summary in the `bottom` slot.

        30 rows; body scrolls internally; the `bottom` slot stays
        anchored at the foot. Use case: a long editable list with a
        running total / footer note.
        """
        pane.data('.invoice_lines', self._invoice_seed(30))
        pane.div('Test 5: framed long list (height=400px) — internal '
                 'scroll + sticky bottom slot.',
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

    def test_6_kanban_dnd(self, pane):
        """3-column kanban board with cross-grid drag-and-drop.

        Each column is its own groupletGrid; all share `dragCode='kanban'`
        so a card can be dragged across columns to advance through the
        workflow. Drop on a card inserts before it; drop on free space
        (or on an empty column) appends. Each card is fully editable
        inline — title, priority (filteringSelect with coloured dots),
        assignee, and due date.
        """
        d = datetime.date
        todo = Bag()
        todo.setItem('r_001', Bag(dict(title='Draft Q3 plan',
                                       assignee='@alice',
                                       priority='high',
                                       due=d(2026, 6, 15))))
        todo.setItem('r_002', Bag(dict(title='Review PR #412',
                                       assignee='@bob',
                                       priority='med',
                                       due=d(2026, 5, 20))))
        todo.setItem('r_003', Bag(dict(title='Update onboarding doc',
                                       assignee='@marta',
                                       priority='low',
                                       due=d(2026, 7, 1))))
        wip = Bag()
        wip.setItem('r_001', Bag(dict(title='Migrate auth service',
                                      assignee='@bob',
                                      priority='high',
                                      due=d(2026, 5, 15))))
        wip.setItem('r_002', Bag(dict(title='Design new dashboard',
                                      assignee='@alice',
                                      priority='med',
                                      due=d(2026, 6, 1))))
        done = Bag()
        done.setItem('r_001', Bag(dict(title='Ship 1.4.0 release',
                                       assignee='@marta',
                                       priority='high',
                                       due=d(2026, 5, 9))))
        pane.data('.kanban_todo', todo)
        pane.data('.kanban_wip', wip)
        pane.data('.kanban_done', done)
        pane.div('Test 6: kanban board — drag cards across columns to '
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
                             defaultRow=dict(title='', assignee='@',
                                             priority='med', due=None))

    def test_7_nested_team(self, pane):
        """Outer grid with a nested groupletGrid inside each row.

        Outer = team members; each member's grouplet renders an avatar
        (initials), name + role + team in the header, and a nested
        `groupletGrid` over `.contacts`. The bread-and-butter "card with
        sub-rows" pattern: add/remove/edit works independently at either
        level.
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
        pane.div('Test 7: team roster with per-person contact channels '
                 '(card + nested rows).',
                 color='#666', font_style='italic', margin_bottom='8px')
        pane.groupletGrid(storepath='.team',
                          resource='person_with_contacts',
                          addEnabled=True, removeEnabled=True,
                          defaultRow=dict(name='', role='', team=''))
