# -*- coding: utf-8 -*-

"Shared Objects. Requires websockets=\"true\" in siteconfig; the dev server (gnr web serve) auto-spawns the gnrasync subprocess."

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
         
    def test_0_sharedObjects(self,pane):
        "Insert values, then visit same page from another browser"
        pane.sharedObject('mydata',shared_id='so_test1')
        fb=pane.formbuilder(cols=1, datapath='mydata')
        fb.textbox('^.name', lbl='Name')
        fb.textbox('^.address', lbl='Address')
        fb.numbertextbox('^.age', lbl='Age')


