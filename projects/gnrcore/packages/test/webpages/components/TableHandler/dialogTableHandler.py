# -*- coding: utf-8 -*-

"dialogTableHandler"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,public:TableHandlerMain"
    maintable='glbl.provincia'

    def windowTitle(self):
        return 'dialogTableHandler'
         
    def test_0_dlg(self,pane):
        "Simple dialogTableHandler on 'provincia' table. Usage of TableHandlerMain and maintable"
        pane = pane.framePane(frameCode='provFrame')
        pane.dialogTableHandler(table='glbl.provincia',
                                    dialog_height='280px',
                                    dialog_width='340px',
                                    dialog_title=u'Provincia')