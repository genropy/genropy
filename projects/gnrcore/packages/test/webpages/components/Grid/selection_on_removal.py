# -*- coding: utf-8 -*-

"""Grid selection when a row is removed"""

from gnr.core.gnrbag import Bag

REMOVE_ROW = """var grid = genro.wdgById('%s_grid');
                var selectedIdx = grid.selection.selectedIndex;
                if(selectedIdx<0){
                    return;
                }
                var storebag = grid.storebag();
                var idx = grid.absIndex(selectedIdx) + %i;
                if(idx>=0 && idx<storebag.len()){
                    storebag.popNode('#'+idx);
                }"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"

    def struct_letters(self, struct):
        r = struct.view().rows()
        r.cell('code', width='6em', name='Code', edit=True)

    def letters(self):
        result = Bag()
        for i, code in enumerate('ABCDEFGH'):
            result.setItem('r_%i' % i, Bag(dict(code=code)), _pkey=code)
        return result

    def removalGrid(self, pane, frameCode, **kwargs):
        pane.data('.%s.store' % frameCode, self.letters())
        frame = pane.bagGrid(frameCode=frameCode, datapath='.%s' % frameCode, storepath='.store',
                             struct=self.struct_letters, height='320px', width='420px', **kwargs)
        bar = frame.bottom.slotBar('5,above,selected,below,*,current,5')
        bar.above.button('Remove row above', action=REMOVE_ROW % (frameCode, -1))
        bar.selected.button('Remove selected', action=REMOVE_ROW % (frameCode, 0))
        bar.below.button('Remove row below', action=REMOVE_ROW % (frameCode, 1))
        bar.current.div('^.selectedId', width='3em')

    def test_0_no_autoselect(self, pane):
        """Remove buttons stand for a change the grid did not ask for (another workstation, a reload):
        removing a row above or below keeps the same row selected, removing the selected row
        leaves no row selected. The Delete button of the toolbar lands on the next row."""
        self.removalGrid(pane, 'no_autoselect')

    def test_1_autoselect(self, pane):
        """With autoSelect=True removing the selected row selects the row that takes its place;
        removing a row above or below still keeps the same row selected."""
        self.removalGrid(pane, 'autoselect', grid_autoSelect=True)
