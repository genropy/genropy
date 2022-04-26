# -*- coding: utf-8 -*-

"""Grid with drag & drop"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull"""
    def isDeveloper(self):
        #Even if user is not developer, he will be considered as so
        return True
    
    def structtest(self,struct):
        r = struct.view().rows()
        r.cell('city', name='City', width='10em')
        r.cell('zone', name='Zone', width='10em')
        r.cell('country', name='Country', width='10em')

    def storetest(self):
        store = Bag()
        for city,zone,country in (('Milano','Nord','Italia'),('Londra','Sud','Inghilterra'),('Parigi','Centro','Francia')):
            store.setItem(city,None,city=city,zone=zone,country=country)
        return store


    def test_0_dragcolumns(self, pane):
        "Try dragging columns"
        frame = pane.framePane(height='300px',border='1px solid silver')
        grid = frame.includedview(struct=self.structtest,storepath='.store',selfDragColumns=True)
        grid.data('.store',self.storetest())