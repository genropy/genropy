# -*- coding: utf-8 -*-

# includedview_bagstore.py
# Created by Francesco Porcari on 2011-03-23.
# Copyright (c) 2011 Softwell. All rights reserved.

"includedview: bagstore"


from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    dojo_source = True
    py_requires="gnrcomponents/testhandler:TestHandlerFull,foundation/includedview"
    
    def test_0_firsttest(self,pane):
        """First test description"""
        frame = pane.framePane('gridtest',height='400px',_class='no_over',datapath='.test')
        tbar = frame.top.slotToolbar('*,addrow',addrow_delay=300)
        frame.data('.mybag',self.common_data())
        frame.dataController("console.log(data)",data="=#",fired='tt')
        iv = frame.includedView(storepath='.mybag',datapath=False,struct=self.common_struct,datamode='bag',
                                selectedIndex='.currIndex',
                                selfsubscribe_addrow="""for(var i=0; i<$1._counter;i++){
                                                            this.widget.addBagRow('#id', '*', this.widget.newBagRow());
                                                        }
                                                        this.widget.editBagRow(null);
                                                        """)
        gridEditor = iv.gridEditor()
        gridEditor.textbox(gridcell='name')
        gridEditor.numbertextbox(gridcell='age')
        gridEditor.textbox(gridcell='work')

    def test_1_selected_id_on_store_replacement(self, pane):
        "Legacy selectedId parity on store replacement and NewIncludedView smoke"
        root = pane.borderContainer(height='480px', datapath='.selected_id_test')
        root.data('.seed', self.selected_id_data())
        root.dataFormula('.legacy.rows', 'new gnr.GnrBag()', _onStart=True)
        root.dataFormula('.new.rows', 'new gnr.GnrBag()', _onStart=True)

        toolbar = root.contentPane(region='top', height='32px')
        toolbar.button('Load rows').dataController(
            'SET .legacy.rows = seed.deepCopy(); SET .new.rows = seed.deepCopy();',
            seed='=.seed')
        toolbar.button('Select last').dataController(
            "SET .legacy.selectedId = 'row_039'; SET .new.grid.selectedId = 'row_039';")
        toolbar.button('Select missing').dataController(
            "SET .legacy.selectedId = 'row_999'; SET .new.grid.selectedId = 'row_999';")
        toolbar.button('Clear selection').dataController(
            'SET .legacy.selectedId = null; SET .new.grid.selectedId = null;')
        toolbar.textbox(value='^.legacy.selectedId', lbl='Legacy selected id', readOnly=True)
        toolbar.textbox(value='^.new.grid.selectedId', lbl='New selected id', readOnly=True)

        grids = root.borderContainer(region='center')
        legacy = grids.borderContainer(region='left', width='50%', splitter=True)
        self.includedViewBox(legacy, nodeId='selected_id_legacy',
                             label='Legacy IncludedView', datapath='.legacy',
                             storepath='.rows', struct=self.selected_id_struct,
                             datamode='bag', autoWidth=True)

        grids.bagGrid(region='center', frameCode='selected_id_new_frame',
                      datapath='.new', storepath='.rows',
                      title='NewIncludedView smoke', struct=self.selected_id_struct,
                      grid_nodeId='selected_id_new', grid_selectedId='^.selectedId',
                      store__identifier='_pkey', gridEditor=False,
                      addrow=False, delrow=False, batchAssign=False)

    def selected_id_data(self):
        result = Bag()
        for i in range(40):
            pkey = 'row_%03i' % i
            result.setItem(pkey, Bag(dict(nome='Locality %02i' % i,
                                          cap='%05i' % (20000 + i),
                                          codice_istat='%06i' % i)),
                           _pkey=pkey)
        return result

    def selected_id_struct(self, struct):
        r = struct.view().rows()
        r.cell('nome', name='Name', width='16em')
        r.cell('cap', name='Postal code', width='8em')
        r.cell('codice_istat', name='ISTAT code', width='8em')

    def common_data(self):
        result = Bag()
        for i in range(5):
            result['r_%i' % i] = Bag(dict(name='Mr. Man %i' % i, age=i + 36, work='Work useless %i' % i))
        return result
        
    def common_struct(self, struct):
        r = struct.view().rows()
        r.cell('name',name='Name',width='10em')
        r.cell('age',name='Age',dtype='I',width='5em')
        r.cell('work',name='Work',width='10em')
