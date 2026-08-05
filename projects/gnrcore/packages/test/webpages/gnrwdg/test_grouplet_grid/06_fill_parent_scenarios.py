"""Fill-parent scenarios — vtabs, long cards, and nested --fill.

Three tabs in a tabContainer, each exercising one fillParent case
not covered by 05_fill_parent.py.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):

    py_requires = ('gnrcomponents/grouplet/grouplet:GroupletHandler,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')

    def main(self, root, **kwargs):
        tc = root.tabContainer(_anchor=True)
        self._vtabsScenario(tc.borderContainer(title='A — vtabs'))
        self._cardsScenario(tc.borderContainer(title='B — long cards'))
        self._nestedScenario(tc.borderContainer(title='C — nested --fill'))

    def _wrap(self, parent, datapath, title):
        wrap = parent.borderContainer(region='center', datapath=datapath)
        wrap.contentPane(region='top', padding='8px',
                         background='#f5f7fa',
                         border_bottom='1px solid #ccd6e0').div(
            title, font_weight='600')
        wrap.contentPane(region='bottom', padding='6px 10px',
                         background='#f5f7fa',
                         border_top='1px solid #ccd6e0').div(
            'Sticky footer', color='#666', font_size='.9em')
        return wrap

    def _chaptersSeed(self, sizes):
        b = Bag()
        for k, (label, n) in enumerate(sizes):
            chapter = Bag()
            items = Bag()
            short = label.split(' ', 1)[0]
            for i in range(n):
                items.setItem(f'it_{i}', Bag(),
                              label=f'{short} item {i + 1}',
                              descr=f'Description line for item {i + 1}')
            chapter.setItem('items', items)
            b.setItem(f'ch_{k}', chapter, label=label)
        return b

    def _vtabsScenario(self, parent):
        wrap = self._wrap(parent, '.vtabs',
                          'vtabs: left tabbar sticky, right panel fills')
        wrap.data('.chapters', self._chaptersSeed([
            ('Alpha (5 items)', 5),
            ('Beta (40 items)', 40),
            ('Gamma (80 items)', 80),
        ]))
        wrap.contentPane(region='center').groupletGrid(
            storepath='.chapters',
            handler=self.makeChapter,
            layout='vtabs',
            titleField='label',
            additem=False, delitem=False, editmenu=False, dragCode=False,
            fillParent=True,
        )

    def _cardsScenario(self, parent):
        wrap = self._wrap(parent, '.cards',
                          'cards: body scrolls internally via --framed')
        items = Bag()
        for i in range(40):
            items.setItem(f'it_{i}', Bag(),
                          label=f'Card item {i + 1}',
                          descr=f'Description for card {i + 1}')
        wrap.data('.items', items)
        wrap.contentPane(region='center').groupletGrid(
            storepath='.items',
            handler=self.makeItem,
            layout='cards',
            additem=False, delitem=False, editmenu=False, dragCode=False,
            fillParent=True,
        )

    def _nestedScenario(self, parent):
        wrap = self._wrap(parent, '.nested',
                          'nested --fill > --fill: only innermost scrolls')
        wrap.data('.chapters', self._chaptersSeed([
            ('Alpha (50 items)', 50),
            ('Beta (50 items)', 50),
            ('Gamma (50 items)', 50),
        ]))
        wrap.contentPane(region='center').groupletGrid(
            storepath='.chapters',
            handler=self.makeChapter,
            layout='tabs',
            titleField='label',
            additem=False, delitem=False, editmenu=False, dragCode=False,
            fillParent=True,
        )

    @public_method
    def makeChapter(self, pane, **kwargs):
        pane.div('^.label', font_size='1.1em', font_weight='600',
                 padding='8px 12px',
                 border_bottom='1px solid #e5e7eb')
        pane.groupletGrid(
            storepath='.items',
            handler=self.makeItem,
            layout='cards',
            additem=False, delitem=False, editmenu=False, dragCode=False,
            fillParent=True,
        )

    @public_method
    def makeItem(self, pane, **kwargs):
        pane.div('^.label', font_weight='600')
        pane.div('^.descr', color='#666', font_size='.9em',
                 margin_top='2px')
