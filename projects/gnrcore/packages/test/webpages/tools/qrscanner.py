# -*- coding: utf-8 -*-

"FlibPicker test"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_reader(self, pane):
        pane.qrscanner(value='^.value',height='400px')
        pane.div('^.value',font_size='40px')


