# -*- coding: utf-8 -*-

"plainTableHandler"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,tg:TableHandlerMain"
    maintable='glbl.provincia'

    def windowTitle(self):
        return 'plainTableHandler'
    
    def test_0_base(self, pane):
        "plainTableHandler. With view_store_onStart=True records are shown on page loading"
        bc = pane.borderContainer(height='400px')
        th = bc.contentPane(region='center').plainTableHandler(table='glbl.provincia',view_store_onStart=True)
 
