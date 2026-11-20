# -*- coding: utf-8 -*-

"""A whole TableHandler page opened inside a dialog: thIframeDialog

`thIframeDialog` wraps `/sys/thpage/<pkg>/<table>` in an iframe inside a lazily
built dialog, so a full TableHandler — view, form, toolbars — becomes a modal of
the page that hosts it, without that page requiring the table's th resource.
"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th"

    def windowTitle(self):
        return 'thIframeDialog'

    def test_0_thpalette(self, pane):
        """The dialog holds the th page of glbl.provincia and the button shows it"""
        pane.thIframeDialog(table='glbl.provincia', title='Province',
                            dialog_nodeId='thpalette_provincia_dlg',
                            dialog_windowRatio='.5')
        pane.button('open', action='genro.wdgById("thpalette_provincia_dlg").show()')

    def test_1_record_form_close(self, pane):
        """The X of a record form opened in a modal page asks before dropping its pending changes:
        edit a field, then close with the X"""
        pane.button('Open MI', action="""genro.dlg.thIframeDialog({table:'glbl.provincia', title:'Provincia',
                                                                 main_call:'main_form', windowRatio:.6,
                                                                 nodeId:'thpalette_provincia_form'},
                                                                {pkey:'MI'});""")

    def test_2_list_form_close(self, pane):
        """In a list/form page the X asks about the open record, and going back to the list
        after a cancelled X leaves the dialog open"""
        pane.button('Open list', action="""genro.dlg.thIframeDialog({table:'glbl.provincia', title:'Province',
                                                                   windowRatio:.7,
                                                                   nodeId:'thpalette_provincia_list'},{});""")
