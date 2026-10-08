"""GroupletGrid empty receivers, nested drag routing and stable drop feedback."""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = ('gnrcomponents/testhandler:TestHandlerFull,'
                   'gnrcomponents/formhandler:FormHandler,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')

    def _rows(self):
        rows = Bag()
        for key, title in [('alpha', 'Alpha'), ('bravo', 'Bravo'), ('charlie', 'Charlie')]:
            value = Bag(dict(title=title, qty=2, extra=Bag(dict(note='Preserve this detail'))))
            value.getNode('qty').setAttr(unit='days')
            rows.setItem(key, value, marker=f'{key}-attributes')
        return rows

    def _pair(self, pane, prefix, target_mode='entry', seed=True, **target_kw):
        pane.attributes['_workspace'] = True
        pane.attributes['style'] = '--entry-bg: #fff4ca;'
        if seed:
            pane.data('.source', self._rows())
            pane.data('.target', Bag())
        columns = pane.div(display='flex', flex_wrap='wrap', gap='12px')
        for side, label in [('source', 'Source'), ('target', 'Receiver')]:
            box = columns.div(flex='1 1 280px', min_width='0')
            box.div(label, font_weight='bold', margin_bottom='6px')
            box.groupletGrid(storepath=f'.{side}', handler=self.detail,
                             nodeId=f'grpgrid_drop_{prefix}_{side}',
                             dragCode=f'drop_{prefix}',
                             additem=target_mode if side == 'target' else 'entry',
                             rowTemplate='$title · $qty',
                             defaultRow=dict(qty=1),
                             **(target_kw if side == 'target' else {}))
        pane.div('Drag by the dotted handle. The receiver must turn green without moving. '
                 'Drop in the white list, on the yellow entry, or after existing rows. '
                 'The empty entry receiver shows a localized hint until its first row. '
                 'Type a draft first: a drop must leave it unchanged. Move out or press Esc '
                 'during a drag: the highlight must disappear.', margin_top='8px')
        pane.dataFormula('#WORKSPACE.counts',
                         "'Source: ' + (source ? source.len() : 0) +"
                         "' / Receiver: ' + (target ? target.len() : 0)",
                         source='^.source', target='^.target', _onStart=True)
        pane.div('^#WORKSPACE.counts', font_weight='bold')
        pane.dataFormula('#WORKSPACE.row_data',
                         "target ? JSON.stringify(target.getNodes().map(n => ({key:n.label, "
                         "attributes:n.attr, data:n.getValue().asDict(true), "
                         "quantityAttributes:n.getValue().getNode('qty').attr})), null, 2) : '[]'",
                         target='^.target', _onStart=True)
        pane.div('^#WORKSPACE.row_data', white_space='pre-wrap', font_family='monospace',
                 max_height='220px', overflow='auto')
        self._drag_probe(pane)

    def test_01_entry(self, pane):
        """Empty entry grids explain how to add a row; the hint disappears after insertion."""
        self._pair(pane, 'entry')

    def test_02_nested(self, pane):
        """Chapter tabs contain item cards and detail grids; each drag stays at its own level."""
        items = Bag()
        items.setItem('lead', Bag(dict(title='Lead', details=self._rows())))
        items.setItem('empty', Bag(dict(title='Empty detail target', details=Bag())))
        chapters = Bag()
        chapters.setItem('cast', Bag(dict(title='Cast', items=items)))
        chapters.setItem('crew', Bag(dict(title='Crew', items=Bag())))
        pane.data('.chapters', chapters)
        pane.groupletGrid(storepath='.chapters', handler=self.chapter,
                         nodeId='grpgrid_drop_chapters', layout='tabs',
                         titleField='title', dragCode='drop_chapters')
        self._drag_probe(pane)
        pane.div('Move Alpha into Empty detail target. Move the item card by its outer handle: '
                 'the detail grid must not catch it. Repeat with a narrow viewport; '
                 'the item cards wrap vertically.', margin_top='8px')

    def test_03_phantom(self, pane):
        """The phantom still accepts append drops without promoting or clearing its values."""
        self._pair(pane, 'phantom', target_mode='phantom')

    def test_04_plus_and_layout(self, pane):
        """The plus accepts append drops in cards and tabs; repeated layout changes stay usable."""
        self._pair(pane, 'plus', target_mode=True, titleField='title')
        pane.data('.layout', 'cards')
        pane.filteringSelect(value='^.layout', values='cards:Cards,tabs:Tabs,vtabs:Vertical tabs')
        pane.dataController("""
            var n = genro.nodeById('grpgrid_drop_plus_target');
            if (n && n.gridController) n.gridController.setLayout(layout);
        """, layout='^.layout')

    def test_05_limits(self, pane):
        """A disabled receiver rejects drops; after two rows maxRows rejects another transfer."""
        pane.data('.disabled', False)
        pane.checkbox(value='^.disabled', label='Disable receiver')
        self._pair(pane, 'limits', maxRows=2, disabled='^.disabled')

    def test_06_isolated(self, pane):
        """Default isolated grids reject each other's rows and plain text dragged from outside."""
        pane.data('.source', self._rows())
        pane.data('.target', Bag())
        for side in ('source', 'target'):
            pane.groupletGrid(storepath=f'.{side}', handler=self.detail,
                             nodeId=f'grpgrid_drop_isolated_{side}', additem='entry',
                             rowTemplate='$title · $qty', margin_bottom='12px')
        self._drag_probe(pane)
        pane.div('Select and drag this plain text: it must not create a row.')

    def test_07_locked_form(self, pane):
        """A memory form's locker prevents row transfers and reordering until unlocked."""
        pane.data('.record', Bag(dict(source=self._rows(), target=Bag())))
        form = pane.frameForm(frameCode='drop_locked_form', height='370px',
                              datapath='.form', border='1px solid silver')
        form.formStore(storeType='Item', handler='memory', locationpath='.#parent.record')
        form.top.slotToolbar('5,*,semaphore,locker,5')
        self._pair(form.center.contentPane(datapath='.record', padding='10px'), 'locked', seed=False)
        form.dataController('this.form.load()', _onStart=True)

    def _drag_probe(self, pane):
        pane.attributes['_workspace'] = True
        pane.button('Check feedback geometry', action="""
            const host = this.getParentNode().getDomNode();
            const results = [...host.querySelectorAll('.grouplet_grid_body,.grouplet_grid_row')]
                .map(el => {
                    const before = el.getBoundingClientRect().toJSON();
                    el.classList.add('canBeDropped');
                    const style = getComputedStyle(el);
                    const result = {surface: el.className, outline: style.outline,
                                    background: style.backgroundColor,
                                    stable: JSON.stringify(before) === JSON.stringify(el.getBoundingClientRect().toJSON())};
                    el.classList.remove('canBeDropped');
                    return result;
                });
            this.setRelativeData('#WORKSPACE.drag_report', JSON.stringify(results, null, 2));
        """)
        pane.div('^#WORKSPACE.drag_report', white_space='pre-wrap', font_family='monospace')
        pane.dataController("""
            const node = this;
            const host = node.getParentNode().getDomNode();
            let report;
            let boxes;
            let receivers = [];
            const measure = el => {
                const r = el.getBoundingClientRect();
                return [r.x, r.y, r.width, r.height, el.scrollWidth, el.scrollHeight];
            };
            const start = e => {
                if (!host.contains(e.target)) return;
                report = {trusted: e.isTrusted, dragover: 0, drop: false,
                          stable: true, feedback: []};
                boxes = new Map([...host.querySelectorAll(
                    '.grouplet_grid_body,.grouplet_grid_row,.grouplet_grid_footer,.grouplet_grid_tab')]
                    .map(el => [el, measure(el)]));
                receivers = [...boxes.keys()];
                receivers.forEach(el => el.addEventListener('dragover', over));
            };
            const over = () => {
                if (!report) return;
                report.dragover++;
                const receiver = host.querySelector('.canBeDropped');
                if (!receiver) return;
                const style = getComputedStyle(receiver);
                const label = receiver.className + ' / ' + style.outline
                    + ' / ' + style.backgroundColor;
                if (!report.feedback.includes(label)) report.feedback.push(label);
                const before = boxes.get(receiver);
                if (before && JSON.stringify(before) !== JSON.stringify(measure(receiver))) {
                    report.stable = false;
                }
            };
            const finish = e => {
                if (!report) return;
                if (e.type === 'drop') report.drop = e.isTrusted;
                receivers.forEach(el => el.removeEventListener('dragover', over));
                setTimeout(() => {
                    report.cleared = !host.querySelector('.canBeDropped,.cannotBeDropped');
                    node.setRelativeData('#WORKSPACE.drag_report', JSON.stringify(report, null, 2));
                }, 0);
            };
            const handlers = {dragstart: start, drop: finish, dragend: finish};
            Object.entries(handlers).forEach(([name, cb]) => document.addEventListener(name, cb, true));
            dojo.connect(node, '_onDeleting', () => {
                receivers.forEach(el => el.removeEventListener('dragover', over));
                Object.entries(handlers).forEach(([name, cb]) => document.removeEventListener(name, cb, true));
            });
        """, _onBuilt=True)

    @public_method
    def chapter(self, pane, **kwargs):
        pane.groupletGrid(storepath='.items', handler=self.item,
                         dragCode='drop_items', titleField='title',
                         cols=2, min_width='240px', gap='8px')

    @public_method
    def item(self, pane, **kwargs):
        pane.div('^.title', font_weight='bold')
        pane.groupletGrid(storepath='.details', handler=self.detail,
                         dragCode='drop_nested_details', additem='entry',
                         rowTemplate='$title · $qty', defaultRow=dict(qty=1))

    @public_method
    def detail(self, pane, **kwargs):
        row = pane.div(display='flex', gap='6px', flex_wrap='wrap', padding='4px')
        row.textbox(value='^.title', placeholder='Title', width='140px')
        row.numberTextBox(value='^.qty', width='60px')
