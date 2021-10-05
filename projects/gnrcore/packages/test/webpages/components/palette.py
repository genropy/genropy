# -*- coding: utf-8 -*-

"""Palettes"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase,th/th:TableHandler"
    
    def test_1_paletteGrid(self, pane):
        "paletteGrid showing table values, opened with picker"
        frame = pane.framePane(frameCode='test0',height='50px')
        bar = frame.top.slotToolbar('*,palettetest,5')
        bar.palettetest.paletteGrid(paletteCode='paletteprovincia',table='glbl.provincia',viewResource='View',dockButton=True)
        
    def test_2_remoteTableHandler(self, pane):
        "Alternative to former example, showing table values using a remoteTableHandler instead of a palette"
        bc = pane.borderContainer(region='center', height='400px')
        left = bc.borderContainer(width='50%', region='left')
        left.contentPane(region='top').button('Create View',fire='.create_view').dataController("""
             pane._('ContentPane',{remote:'th_remoteTableHandler',remote_thkwargs:{table:'glbl.provincia'}});
            """,_fired='^.create',pane=left.contentPane(region='center'))
        
        right = bc.borderContainer(region='center')
        right.contentPane(region='top').button('Create Form',fire='.create_form').dataController("""
             pane._('ContentPane',{remote:'th_remoteTableHandler',
                                    remote_thkwargs:{table:'glbl.provincia',thwidget:'form'}});
            """,_fired='^.create',pane=right.contentPane(region='center'))
        
    def test_3_palettePane(self, pane):
        "Custom palette with background and no values"
        pane.div(height='30px').dock(id='mydock_1', position='relative')
        pane.palettePane('first', dockTo='mydock_1',maxable=True,background='red')
    
    def test_4_paletteTree(self, pane):
        "paletteTree with custom values built with a Bag and use of paletteGroups"
        pane.div(height='30px').dock(id='mydock_2', position='relative')
        pane.data('.states', self.treedata())
        pg = pane.paletteGroup('second', dockTo='mydock_2')
        pg.paletteTree('states_tree', storepath='test.test_4_paletteTree.states', title='States')
        pg.palettePane('blue', title='Color', background_color='blue').div('blue', color='white')
    
    def treedata(self):
        result = Bag()
        result.setItem('r1', None, code='CA', caption='California')
        result.setItem('r1.a1', None, code='SD', caption='San Diego')
        result.setItem('r1.a2', None, code='SF', caption='San Francisco')
        result.setItem('r1.a3', None, code='SF', caption='Los Angeles')
        result.setItem('r2', None, code='IL', caption='Illinois')
        result.setItem('r4', None, code='TX', caption='Texas')
        result.setItem('r4.a1', None, code='HU', caption='Huston')
        result.setItem('r5', None, code='AL', caption='Alabama')
        return result
        
    def test_5_paletteGrid(self, pane):
        "paletteGrid with custom values built with a Bag and use of paletteGroups"
        pane.div(height='30px', position='relative')
        pane.data('.states', self.treedata())
        pg = pane.paletteGroup('third', dockTo='*', dockButton=True)
        palette = pg.paletteGrid('palette_grid_with_bag', title='States', struct=self.gridstruct)
        palette.bagStore(storepath='test.test_5_paletteGrid.states',storeType='AttributesBagRows')
           
    def gridstruct(self, struct):
        r = struct.view().rows()
        r.cell('code', name='Code', width='5em')
        r.cell('caption', name='Caption', width='auto')