class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    js_requires = 'js_plugin/sheetjs/sheetjs'


    def test_1_xlsx(self,pane):
        pane.button('Load clipboard',fire='.loadclipboard')

        pane.dataController("""
            genro.sheetjs.rowsFromXLSXClipboard()
        """,
                            _fired='^.loadclipboard')