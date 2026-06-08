"""Fill-parent demo — groupletGrid sized by a dijit ancestor.

Side-by-side: same groupletGrid with `fillParent=False` (legacy) vs
`fillParent=True`. Each side sits inside a borderContainer with a
sticky header and footer, so the available area for the grid is
clearly bounded.

  - Left  (fillParent=False): the grid wraps its content. The tabbar
    sits at the top of the content; the active panel takes its
    natural height. Long content pushes past the footer line.
  - Right (fillParent=True):  the grid claims 100% of the center
    region. The tabbar stays anchored, the active panel fills the
    remaining height and scrolls internally when content overflows.
    The sticky footer never moves.

The widget below has no real data behaviour: only static rows with
text, enough to make the layout difference visible.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):

    py_requires = ('gnrcomponents/grouplet/grouplet:GroupletHandler,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')

    def main(self, root, **kwargs):
        bc = root.borderContainer(_anchor=True)
        self._sidePane(bc, region='left', width='50%',
                       title='fillParent=False (legacy)',
                       fill=False)
        self._sidePane(bc, region='center',
                       title='fillParent=True',
                       fill=True)

    def _sidePane(self, parent, fill=False, title=None, **regionKwargs):
        wrap = parent.borderContainer(
            datapath=f'.demo_{"fill" if fill else "nofill"}',
            **regionKwargs)
        wrap.contentPane(region='top', padding='8px',
                         background='#f5f7fa',
                         border_bottom='1px solid #ccd6e0').div(
            title, font_weight='600')
        wrap.contentPane(region='bottom', padding='6px 10px',
                         background='#f5f7fa',
                         border_top='1px solid #ccd6e0').div(
            'Sticky footer (always at the bottom of the pane)',
            color='#666', font_size='.9em')

        wrap.data('.chapters', self._chaptersSeed())

        center = wrap.contentPane(region='center')
        center.groupletGrid(
            storepath='.chapters',
            handler=self.makeChapter,
            layout='tabs',
            titleField='label',
            additem=False, delitem=False, editmenu=False, dragCode=False,
            fillParent=fill,
        )

    def _chaptersSeed(self):
        b = Bag()
        for k, (label, n) in enumerate([('Alpha (5 items)', 5),
                                        ('Beta (40 items)', 40),
                                        ('Gamma (80 items)', 80)]):
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
        )

    @public_method
    def makeItem(self, pane, **kwargs):
        pane.div('^.label', font_weight='600')
        pane.div('^.descr', color='#666', font_size='.9em',
                 margin_top='2px')
