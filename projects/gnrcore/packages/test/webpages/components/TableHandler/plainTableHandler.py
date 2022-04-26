# -*- coding: utf-8 -*-

"plainTableHandler"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    maintable='glbl.provincia'

    def windowTitle(self):
        return 'plainTableHandler'
    
    def test_0_base(self, pane):
        "plainTableHandler. With view_store_onStart=True records are shown on page loading"
        bc = pane.borderContainer(height='400px')
        th = bc.contentPane(region='center').plainTableHandler(table='glbl.provincia',view_store_onStart=True)
 
    def test_1_base(self, pane):
        "With autoSelect=True, in every TableHandler the first record is automatically selected on loading"
        bc = pane.borderContainer(height='400px')
        th = bc.contentPane(region='center').plainTableHandler(table='glbl.provincia', 
                grid_autoSelect=True, view_store_onStart=True)
