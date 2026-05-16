"""groupletGrid demo page — minimum gallery covering every use case.

  test_01_invoice_baseline       — invoice rows, single column, plain
                                   (smoke: add/remove via phantom + kebab)
  test_02_todolist_handler       — handler= callable (not a resource file)
  test_03_invoice_responsive     — same rows, cols=3 + min_width
                                   (responsive: reflow with viewport width)
  test_04_kanban_dnd             — 3 grids sharing dragCode='kanban',
                                   cross-grid drag of editable cards
  test_05_team_tabs              — team roster with a layout picker:
                                   horizontal tabs / vertical tabs / cards
                                   (`layout='tabs'|'vtabs'|'cards'`),
                                   reactive `titleField`, runtime switch
                                   via `setLayout()` on the controller
  test_06_struct_shopping_list   — fakexcel style: `struct=` mode
                                   with checkbox + editable cells, derived
                                   line total (formula) and live footer
                                   total (totalize). No phantom row, no
                                   per-row ×: actions via kebab + toolbar
                                   +/−.
  test_07_myticket_resourcefield — heterogeneous rows where the template
                                   is chosen per-row from the `ticket_type`
                                   discriminator field. Rows are loaded
                                   from `test.myticket` via a `dataRpc`
                                   (`selection().output('baglist')` —
                                   same pattern as `righeDocumento` in
                                   erpy). Each row picks one of the
                                   complete templates under
                                   `myticket/grid_grouplets/` and renders
                                   the matching mini-form.
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

    def test_01_invoice_baseline(self, pane):
        """Invoice rows, single column, plain (smoke test).

        Starts EMPTY. A `Load sample` button swaps the whole rows Bag
        into the grid's storepath in one shot — exercising the
        `newDataStore` path (storepath value replaced wholesale, not
        mutated key by key). The phantom `+` then adds individual rows
        on top of the loaded set, and `×` removes them.
        """
        # Seed lives at a path the grid does NOT watch. The button below
        # copies it into `.invoice_lines` to trigger the swap.
        pane.data('.seed_invoice', self._invoice_seed(3))
        pane.div('Test 01: empty grid + "Load sample" button (exercises '
                 'newDataStore: the whole rows Bag is replaced at once).',
                 color='#666', font_style='italic', margin_bottom='8px')
        toolbar = pane.div(display='flex', gap='0.6em',
                           margin_bottom='8px')
        toolbar.button('!!Load sample').dataController('SET .invoice_lines = seed_invoice.deepCopy()',
                                                    seed_invoice='=.seed_invoice')
        toolbar.button('!!Clear',
                       action="SET .invoice_lines = null;")
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          defaultRow=dict(qty=1, price=0))

    def test_02_todolist_handler(self, pane):
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
        pane.div('Test 02: small todolist driven by handler=callable. '
                 'Kebab is the only affordance (no `×`) and shows the '
                 'three editmenu value shapes: True (preset), string '
                 '(preset with custom label) and dict (full menuline).',
                 color='#666', font_style='italic', margin_bottom='8px')
        # `editmenu` as a dict: keys identify entries, values can be
        #   True   → use the built-in preset (addPrev/addNext/delete)
        #   string → override the preset's label, keep preset action
        #   dict   → full menuline spec (label, action, ...) — must be
        #            a complete genropy menuline kwargs dict, no magic
        #            substitutions
        # The custom `Mark important` entry publishes a page-level topic;
        # subscribers can take action without touching the grid.
        pane.groupletGrid(storepath='.todos',
                          handler=self.todo_row_handler,
                          delitem=False,
                          editmenu={
                              'addPrev': True,
                              'addNext': 'Insert below',
                              'mark': dict(
                                  label='Mark important',
                                  action="alert('Marked as important!');",
                              ),
                              'delete': True,
                          },
                          defaultRow=dict(done=False, text=''))

    @public_method
    def todo_row_handler(self, pane, **kwargs):
        row = pane.div(display='flex', align_items='center', gap='0.6em',
                       padding='2px 0')
        row.checkBox(value='^.done')
        row.textbox(value='^.text', placeholder='!!What needs doing?',
                    width='100%', flex='1')

    def test_03_invoice_responsive(self, pane):
        """Same invoice rows, but in a responsive grid.

        `cols=3 + min_width=300px`: wide viewport → 3 columns, tablet → 2,
        mobile → 1. Demonstrates the auto-fill responsive mode on the
        same data shape as test_1 — only the layout kwargs change.
        """
        pane.data('.invoice_lines', self._invoice_seed(6))
        pane.div('Test 03: same rows as test_01, cols=3 + min_width=300px '
                 '(resize the viewport to see re-flow).',
                 color='#666', font_style='italic', margin_bottom='8px')
        # Prefix capture demo on the phantom add and `×` delete:
        #   additem_tip / additem_class   → on phantom '+'
        #   delitem_tip / delitem_class   → on row '×'
        pane.groupletGrid(storepath='.invoice_lines',
                          resource='invoice_row',
                          cols=3, min_width='300px',
                          additem_tip='!!Add invoice line',
                          additem_class='gg-fancy-add',
                          delitem_tip='!!Remove line',
                          delitem_class='gg-fancy-del',
                          defaultRow=dict(qty=1, price=0))

    def test_04_kanban_dnd(self, pane):
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
        pane.div('Test 04: kanban board — drag cards across columns to '
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
                             dragCode='kanban',
                             defaultRow=dict(title='', assignee='@',
                                             priority='med', due=None))

    def test_05_team_tabs(self, pane):
        """Team roster rendered as horizontal tabs (`layout='tabs'`).

        Same data shape as test_7 (person_with_contacts) but the outer
        grid is now a tab strip: one chip per member, the active chip
        shows the full panel (avatar, name/role/team, nested contacts
        grid). The chip label is bound reactively to the row's `name`
        field via `titleField='name'` — type in the name input and the
        tab updates live.

        The "Toggle layout" toolbar button calls the controller's
        public `setLayout()` API and flips between tabs and cards mode
        at runtime. Row panels survive the switch — pending edits and
        nested grid state stay intact.
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
        c_carla = Bag()
        c_carla.setItem('r_001', Bag(dict(channel='email',
                                          value='carla@acme.io')))
        people.setItem('r_001', Bag(dict(name='Alice Rossi',
                                         role='Producer',
                                         team='Strategy',
                                         contacts=c_alice)))
        people.setItem('r_002', Bag(dict(name='Bob Bianchi',
                                         role='Director',
                                         team='Production',
                                         contacts=c_bob)))
        people.setItem('r_003', Bag(dict(name='Carla Verdi',
                                         role='Designer',
                                         team='Creative',
                                         contacts=c_carla)))
        pane.data('.team_tabs', people)
        pane.div('Test 05: team roster as tabs. Edit a name → tab label '
                 'updates live. Drag a chip to reorder. The layout '
                 'picker on the right flips between cards / horizontal '
                 'tabs / vertical tabs at runtime without losing '
                 'pending edits.',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid_id = 'grpgrid_team_tabs'
        # Seed the layout datapath with the same default the
        # groupletGrid uses, so the picker mirrors the actual state.
        pane.data('.team_tabs_layout', 'tabs')
        toolbar = pane.div(display='flex', gap='0.6em',
                           align_items='center',
                           margin_bottom='8px')
        toolbar.div('!!Layout', color='#666', font_size='0.9em')
        toolbar.filteringSelect(
            value='^.team_tabs_layout',
            values='tabs:!!Tabs (horizontal),vtabs:!!Tabs (vertical),cards:!!Cards',
            width='200px')
        # On layout change, call the controller's public setLayout API.
        # Using a dataController instead of a direct connect_onchange
        # keeps the dispatch off the widget event loop and ensures the
        # call runs in the page datapath context.
        pane.dataController("""
            var n = genro.nodeById(grid_id);
            var c = n && n.gridController;
            if (c && c.layout !== layout) {
                c.setLayout(layout);
            }
        """, layout='^.team_tabs_layout', grid_id=grid_id)
        pane.groupletGrid(storepath='.team_tabs',
                          resource='person_with_contacts',
                          layout='tabs',
                          titleField='name',
                          emptyTitle='!!New member',
                          nodeId=grid_id,
                          defaultRow=dict(name='', role='', team=''))

    def test_06_struct_shopping_list(self, pane):
        """`struct=` mode + reactive controller (Item 12) — fakexcel style.

        Shopping list driven by a `gnr.Grid`-style struct: checkbox to
        mark bought items, editable item name / qty / unit price,
        derived line total via `formula=`, and a totalize footer
        showing total spent. No phantom `+` row, no per-row ×:
        additions and deletions go through the kebab (`editmenu=True`
        → addPrev / addNext / delete) and through the toolbar +/−
        buttons above the grid (publish on the controller's
        actionTopic).

        Live cascade: edit `qty` or `unit_price` → `line_total`
        recomputes; the `Total spent` footer cell updates in real time.
        Driven by the same `gnr.GridChangeManager` Grid uses,
        instantiated directly on the controller — no adapter, no fork.
        """
        seed = Bag()
        for i, (item, qty, price) in enumerate((
                ('Milk',     2, 1.40),
                ('Bread',    1, 2.20),
                ('Apples',   6, 0.55),
                ('Coffee',   1, 8.90),
                ('Pasta',    3, 1.10)), start=1):
            seed.setItem(f'r_{i:03d}',
                         Bag(dict(bought=False, item=item,
                                  qty=qty, unit_price=price)))
        pane.data('.shopping_list', seed)

        def struct(struct):
            r = struct.view().rows()
            r.cell('bought', name=' ', width='3em', dtype='B', edit=True)
            r.cell('item', name='Item', width='100%',
                   edit=True, validate_notnull=True)
            r.cell('qty', name='Qty', width='5em', dtype='L', edit=True)
            r.cell('unit_price', name='Unit price', width='7em',
                   dtype='N', edit=True, format='#,###.00')
            r.cell('line_total', name='Line total', width='8em',
                   dtype='N', formula='qty*unit_price',
                   totalize='.total_spent', format='#,###.00')

        pane.div('Test 06: shopping list (fakexcel style). Edit qty / '
                 'unit price → line total recomputes; the footer shows '
                 'total spent. Use the toolbar +/− to add or remove '
                 'rows, or use the kebab on each row (add before / '
                 'add after / delete).',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid_id = 'grpgrid_shopping_list'
        # Toolbar: title on the left, +/− buttons on the right.
        # The buttons publish on the controller's actionTopic;
        # `_handleAction` routes to `_doAddRow` / `_askAndDeleteRow`.
        action_topic = f'groupletGrid_{grid_id}_action'
        toolbar = pane.div(display='flex', align_items='center',
                           margin_bottom='8px')
        toolbar.div('Shopping list',
                    font_weight='600', font_size='1.05em')
        actions = toolbar.div(margin_left='auto',
                              display='flex', gap='0.4em')
        actions.button(
            '+',
            action=f"genro.publish('{action_topic}', "
                   f"{{action:'add'}});")
        actions.button(
            '−',
            action=f"genro.publish('{action_topic}', "
                   f"{{action:'delete'}});")
        pane.groupletGrid(storepath='.shopping_list',
                          struct=struct,
                          nodeId=grid_id,
                          max_height='320px',
                          additem=False,
                          delitem=False,
                          editmenu=True,
                          defaultRow=dict(bought=False, qty=1,
                                          unit_price=0))

    @public_method
    def getMyTickets(self, **kwargs):
        """Load all `test.myticket` rows as a Bag-of-Bags.

        Mirrors the canonical `righeDocumento` pattern from erpy
        (model/fattura.py:411-415, model/ddt.py:199-203): bagFields=True
        expands every row's columns into a sub-Bag, then
        `selection().output('baglist')` returns a Bag whose children
        are the row Bags keyed by pkey.
        """
        return self.db.table('test.myticket').query(
            order_by='ticket_date desc',
            bagFields=True,
            columns='*',
        ).selection().output('baglist')

    def test_07_myticket_resourcefield(self, pane):
        """Heterogeneous rows: per-row template chosen from the
        `ticket_type` discriminator field.

        Rows arrive from `test.myticket` via the canonical `dataRpc`
        pattern (`selection().output('baglist')`). Each row carries
        `ticket_type='commercial/offer'` (or one of the other 8
        categories) plus an `extra_data` sub-Bag with type-specific
        fields. The groupletGrid in `resourceField='ticket_type'`
        mode preloads ALL templates from `myticket/grid_grouplets/`
        in a single bootstrap RPC, then each row picks its template
        at render time.

        Add-by-type: the toolbar exposes a menu with one item per
        ticket type. Each click publishes
        `{action: 'add', defaults: {ticket_type: '<path>'}}` on the
        action bus; the new row is born with the discriminator
        already set, so the next `_addRow` resolves the correct
        template immediately.

        Setup: run `python projects/gnrcore/packages/test/lib/populate_mytickets.py`
        once to seed test data into `test.myticket`.
        """
        pane.div('Test 07: heterogeneous rows from `test.myticket`. '
                 'Each row picks its template (one of 9) from the '
                 '`ticket_type` field. The toolbar shows an Add menu '
                 'driven by `gr_groupletAddrowMenu` — same Bag pattern '
                 'as `fgr_slotbar_addrow` / `fh_slotbar_form_add`.',
                 color='#666', font_style='italic', margin_bottom='8px')
        grid_id = 'grpgrid_myticket'
        action_topic = f'groupletGrid_{grid_id}_action'
        # Build the add-row menu Bag server-side: one item per grouplet
        # under `myticket/grid_grouplets/`, each carrying default_kw
        # with the discriminator field pre-set. The widget reads this
        # Bag from `.addrow_menu_store` via menupath= and renders a
        # popup; the click emits an action with `default_kw` as $1.
        pane.data('.addrow_menu_store',
                  self.gr_groupletAddrowMenu(
                      table='test.myticket',
                      field='ticket_type',
                      grouplets_root='grid_grouplets'))
        toolbar = pane.div(display='flex', gap='0.8em',
                           align_items='center', margin_bottom='8px')
        # Add menu: `menudiv` is a standalone clickable icon that
        # opens a popup with items from `storepath` (the menu Bag).
        # Each item click runs `action` with `$1` = the clicked
        # node's attrs (including `default_kw` from
        # gr_groupletAddrowMenu). We publish onto the grid's action
        # bus, which the controller picks up as a normal `add`.
        # Pattern from th_picker.py:352 and erpy/th_mese.py:840.
        toolbar.menudiv(
            storepath='.addrow_menu_store',
            iconClass='iconbox add_row',
            tip='!!Add ticket',
            action=(
                f"genro.publish('{action_topic}', "
                "{action: 'add', defaults: $1.default_kw});"
            ),
        )
        # The grid itself: dataRpc fires at boot, then resourceField
        # mode preloads all templates with a single follow-up RPC.
        pane.dataRpc('.tickets', self.getMyTickets, _onBuilt=True)
        pane.groupletGrid(
            storepath='.tickets',
            resourceField='ticket_type',
            table='test.myticket',
            grouplets_root='grid_grouplets',
            nodeId=grid_id,
            delitem=True,
            editmenu=False,
            additem=False,  # add via the menudiv in the toolbar
        )

