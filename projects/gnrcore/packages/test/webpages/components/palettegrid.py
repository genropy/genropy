# -*- coding: utf-8 -*-

"""palette_manager"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_paletteGridRemote(self, pane):
        frame = pane.framePane(frameCode='test2',height='50px')
        bar = frame.top.slotToolbar('*,palettetest,5')
        bar.palettetest.paletteGrid(paletteCode='paletteprovincia',table='glbl.provincia',viewResource='View',dockButton=True)
        