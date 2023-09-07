# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_pie(self, pane):
        b = Bag()
        b.addItem('r1',Bag(dict(flavour='Mushrooms',quantity=3,quantity_2=5)))
        b.addItem('r2',Bag(dict(flavour='Onions',quantity=1,quantity_2=2)))
        b.addItem('r3',Bag(dict(flavour='Zucchini',quantity=1,quantity_2=3)))
        b.addItem('r4',Bag(dict(flavour='Pepperoni',quantity=2,quantity_2=1)))
        pane.data('.source',b)
        pane.dataFormula('.data','source',source='=.source',_onStart=True)

        bc = pane.borderContainer(height='600px',width='900px')
        qc = bc.contentPane(region='left',width='300px').quickGrid('^.data',height='100%',width='100%')
        qc.tools('addrow,delrow')
        qc.column('flavour',name='Flav',
                  width='16em',edit=True)
        qc.column('quantity',name='Qt',width='6em',edit=True,dtype='L')
        qc.column('quantity_2',name='Qt2',width='6em',edit=True,dtype='L')

        center = bc.contentPane(region='center')
        gc = center.GoogleChart('ColumnChart',
                                height='500px',
                                width='500px',
                                border='1px solid silver',
                                title='Pizze varie',grid=qc)
        gc.column('flavour',name='Flv')
        gc.column('quantity')
        #gc.column('quantity_2')



    def test_2_organigramma(self, pane):

        """
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Name');
        data.addColumn('string', 'Manager');
        data.addColumn('string', 'ToolTip');

        // For each orgchart box, provide the name, manager, and tooltip to show.
        data.addRows([
          [{'v':'Mike', 'f':'Mike<div style="color:red; font-style:italic">President</div>'},
           '', 'The President'],
          [{'v':'Jim', 'f':'Jim<div style="color:red; font-style:italic">Vice President</div>'},
           'Mike', 'VP'],
          ['Alice', 'Mike', ''],
          ['Bob', 'Jim', 'Bob Sponge'],
          ['Carol', 'Bob', '']
        ]);
        
        
        
        """
        b = Bag()
        b.addItem('l1',Bag(),label='Mario Rossi')
        b.addItem('l1.v1',Bag(),label='Luigi Bianchi')
        b.addItem('l1.v2',Bag(),label='Lucia Sbarazzini')
        b.addItem('l1.v2.sm',Bag(),label='Davide Paci')
        b.addItem('l1.v2.pr',Bag(),label='Daniela Ale')



        pane.data('.source',b)
        pane.dataFormula('.data','source',source='=.source',_onStart=True)

        bc = pane.borderContainer(height='600px',width='900px')
        bc.contentPane(region='left',width='50%').tree(storepath='.data',
                                                       labelAttribute='label',
                                                       draggable=True,
                                                       hideValues=True)
        center = bc.contentPane(region='center')
        center.GoogleChart('OrgChart',storepath='.data')


