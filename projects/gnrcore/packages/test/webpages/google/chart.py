# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
from datetime import datetime

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_pie(self, pane):
        b = Bag()
        b.addItem('r1',Bag(dict(flavour='Mushrooms',quantity=3,quantity_2=5)))
        b.addItem('r2',Bag(dict(flavour='Onions',quantity=1,quantity_2=2)))
        b.addItem('r3',Bag(dict(flavour='Zucchini',quantity=1,quantity_2=3)))
        b.addItem('r4',Bag(dict(flavour='Pepperoni',quantity=2,quantity_2=1)))
        pane.data('.source',b)
        pane.dataFormula('.store','source',source='=.source',_onStart=True)

        bc = pane.borderContainer(height='600px',width='900px')
        struct = Bag()
        columns = Bag()
        columns.addItem('c1',None, field='flavour', name='Flav')
        columns.addItem('c2',None, field='quantity', name='Qty', dtype='L', color='red')
        columns.addItem('c3',None, field='quantity_2', name='Qty 2', dtype='L', color='lime')
        struct['columns'] = columns
        bc.data('.struct', struct)        
        bc.contentPane(region='center').GoogleChart('ColumnChart',
                                height='500px',
                                width='500px',
                                border='1px solid silver',
                                title='Pizze varie',
                                storepath='.store',
                                structpath='.struct')

    def test_2_pie(self, pane):
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

        gc = bc.contentPane(region='center').GoogleChart('ColumnChart',
                                height='500px',
                                width='500px',
                                border='1px solid silver',
                                title='Pizze varie',
                                grid=qc)
        gc.struct.column('flavour',name='Flv')
        gc.struct.column('quantity', background='lime')
        gc.struct.column('quantity_2', color='green')


    def test_3_organigramma(self, pane):
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


    def test_4_timeline(self, pane):
        b = Bag()
        b.addItem('r1',Bag(dict(code='123', lbl='Maurice', start=datetime(2023, 10, 15), end=datetime(2023, 12, 31))))    
        b.addItem('r2',Bag(dict(code='456', lbl='John', start=datetime(2023, 10, 15), end=datetime(2023, 10, 30))))
        b.addItem('r3',Bag(dict(code='789', lbl='David', start=datetime(2023, 11, 1), end=datetime(2023, 12, 31))))
        b.addItem('r4',Bag(dict(code='012', lbl='Francis', start=datetime(2023, 10, 15), end=datetime(2024, 3, 31))))
        pane.data('.source',b)
        pane.dataFormula('.store','source',source='=.source',_onStart=True)

        bc = pane.borderContainer(height='600px',width='900px')
        struct = Bag()
        columns = Bag()
        columns.addItem('c1',None, field='code', name='Person')
        columns.addItem('c2',None, field='lbl', name='Name')
        columns.addItem('c3',None, field='start', name='Start', dtype='D')
        columns.addItem('c4',None, field='end', name='End', dtype='D')
        struct['columns'] = columns
        bc.data('.struct', struct)        
        bc.contentPane(region='center').GoogleChart('Timeline',
                                height='500px',
                                width='500px',
                                border='1px solid silver',
                                title='Project timeline',
                                storepath='.store',
                                structpath='.struct', 
                                chart_timeline=dict(showRowLabels=True))