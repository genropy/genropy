#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  task monitoring
#
#  Copyright (c) 2025 Softwell. 
#

from gnr.core.gnrdecorator import public_method
from gnr.dev.mobilechecks import MobileAppChecks
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    css_requires='public'
    py_requires='gnrcomponents/framegrid:FrameGrid'
    auth_main = 'superadmin,_DEV_,sysadmin'

    def windowTitle(self):
        return '!!Mobile App Configuration check'

    def main(self, root, **kwargs):
        
        bc = root.borderContainer(datapath='main')
        top = bc.borderContainer(region='top', height='500px')
        self.testsFrame(top.contentPane(region='center'))

    def testsStruct(self, struct):
        r = struct.view().rows()
        r.cell('test', width='20%',name='Test name')
        r.cell('result',width='10%',name='Result',dtype='B',semaphore=True)
        r.cell('description',width='70%',name='Description')

    def testsFrame(self, pane):
        frame = pane.frameGrid(frameCode='mobileapptests', datapath='mobileapptests',
                               struct=self.testsStruct, _class='pbl_roundedGroup',
                               grid_autoSelect=True,
                               margin='2px')
        frame.grid.bagStore(storepath='mobileapptests.store',storeType='AttributesBagRows',
                                sortedBy='=.grid.sorted',
                                data='^mobileapptests.loaded_data', selfUpdate=True)
        pane.dataRpc('mobileapptests.loaded_data',self.testsResult, _onStart=True)
        frame.top.slotBar('2,vtitle,*', vtitle="Mobile app checks", _class="pbl_roundedGroupLabel")

    @public_method
    def testsResult(self):
        c = MobileAppChecks(self.site)
        r = c.run()
        result = Bag()
        for i, (k, v) in enumerate(r.items()):
            result.setItem(i, None, **v)
        return result
