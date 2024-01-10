# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_icons(self, pane):   
        fb = pane.formbuilder(cols=1)
        fb.textbox('^.background', lbl='Background')
        fb.textbox('^.icon', lbl='Icon', placeholder='check')
        fb.div(_class='google_icon', background='^.background', nodeId='googleIcon', hidden='^.icon?=!#v')
        pane.dataController("""genro.dom.addClass(genro.dom.getDomNode('googleIcon'), which_icon);""",
                            which_icon='^.icon')