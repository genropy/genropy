
"""borderTableHander"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_borderTableHander(self, pane):
        bc = pane.borderContainer(height='500px')
        th = bc.contentPane(region='center').borderTableHandler(table='fatt.fattura', datapath='.fattura',
                                                                vpane_height='35%',
                                                                virtualStore=True, view_store_onStart=True, extendedQuery=True,
                                                                grid_multiSelect=True, grid_autoSelect=False, export=True,
                                                                addrow=False, delrow=False, form_locked=False, liveUpdate=False,
                                                                viewResource='View', formResource='Form')
