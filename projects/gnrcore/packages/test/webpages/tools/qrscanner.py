# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_reader(self, pane):
        "Scans QR code using camera and assigns read value to path. Please enable camera first"
        pane.qrscanner(value='^.value',height='400px')
        pane.div('^.value',font_size='40px')
        pane.iframe(src='^.value',width='100%',height='100%')



