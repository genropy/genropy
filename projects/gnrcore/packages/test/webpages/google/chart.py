# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_pie(self, pane):

        b = Bag()
        b.addItem('r1',Bag(dict(flavour='Mushrooms',quantity=3,v=5)))
        b.addItem('r2',Bag(dict(flavour='Onions',quantity=1,v=3)))
        b.addItem('r3',Bag(dict(flavour='Zucchini',quantity=1,v=2)))
        b.addItem('r4',Bag(dict(flavour='Pepperoni',quantity=2,v=1)))
        pane.data('.source',b)
        pane.dataFormula('.data','source',source='=.source',_onStart=True)

        bc = pane.borderContainer(height='600px',width='600px')
        qc = bc.contentPane(region='left',width='50%').quickGrid('^.data',height='100%',width='100%')
        qc.tools('addrow,delrow')
        qc.column('flavour',name='Flav',
                  width='16em',edit=True)
        qc.column('quantity',name='Qt',width='6em',edit=True,dtype='L')
        qc.column('v',name='V2',dtype='L')
        center = bc.contentPane(region='center')
        center.GoogleChart(height='400px',width='400px',grid=qc,chart_type='Histogram')


