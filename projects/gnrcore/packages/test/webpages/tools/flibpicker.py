# -*- coding: utf-8 -*-

"FlibPicker test"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,flib:FlibPicker"

    def test_1_flibpicker(self, pane):
        "Add flib pkg in instance to manage media files with Flib picker"
        pane.flibPicker(dockButton=True)


