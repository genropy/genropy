# -*- coding: utf-8 -*-

# Created by Francesco Porcari on 2010-09-22 and updated by Davide Paci on 2022-01-25.
# Copyright (c) 2010 Softwell. All rights reserved.

"""includedView"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    auto_polling = 0
    user_polling = 0
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,foundation/includedview:IncludedView"

    maintable = 'glbl.localita'

    def test_0_button_view(self, pane):
        "Edit dynamically view columns and perform research"
        bc = pane.borderContainer(height='300px', datapath='test0')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.textbox(value='^.start', lbl='Starts with:')
        fb.button('Add column and search').dataController("""genro._data.setItem('grids.mygrid.struct.view_0.rows_0.cell_3',null,
                                            {width:'12em',name:'Nome Provincia',field:'@provincia.nome',tag:'cell'})""")
        viewpane = bc.contentPane(region='center', datapath='.mygrid')
        viewpane.dataSelection('.selection', self.maintable, where="$nome ILIKE :seed || '%%'", seed='^.#parent.start',
                               columnsFromView='mygrid',
                               selectionName='*currsel', selectionId='mainselection')
        viewpane.includedView(storepath='.selection', struct=self.loc_struct, nodeId='mygrid', table=self.maintable,
                              datamode='bag')

    def loc_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('nome', name='Nome', width='10em')
        r.fieldcell('provincia', name='Provincia', width='10em')
        r.fieldcell('@provincia.@regione.nome', name='Regione', width='10em')
        return struct

    def test_1_includedview_editable_bag(self, pane):
        "Includedview editable datamode bag"
        bc = pane.borderContainer(height='300px')
        bc.data('.mygrid.rows', self.common_data())
        bc.data('nome', 'piero')
        iv = self.includedViewBox(bc, label='!!Products', datapath='.mygrid',
                                  storepath='.rows', struct=self.common_struct,
                                  autoWidth=True, datamode='bag',
                                  add_action=True, del_action=True, editorEnabled=True,
                                  newRowDefaults=dict(name='^nome')
                                  )
        gridEditor = iv.gridEditor()
        gridEditor.textbox(gridcell='name')
        gridEditor.numbertextbox(gridcell='age')
        gridEditor.textbox(gridcell='work')
    
    def common_data(self):
        result = Bag()
        for i in range(5):
            result['r_%i' % i] = Bag(dict(name='Mr. Man %i' % i, age=i + 36, work='Work useless %i' % i))
        return result
        
    def common_struct(self, struct):
        r = struct.view().rows()
        r.cell('name', name='Name', width='10em')
        r.cell('age', name='Age', width='5em', dtype='I')
        r.cell('work', name='Work', width='10em')

    def test_2_includedview_bagstore_addrow(self, pane):
        "includedView on a Bag inside a framePane: the toolbar slot adds rows client side and opens the editor"
        frame = pane.framePane('gridtest',height='400px',_class='no_over',datapath='.test')
        frame.top.slotToolbar('*,addrow',addrow_delay=300)
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
