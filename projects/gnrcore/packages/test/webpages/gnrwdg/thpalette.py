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
