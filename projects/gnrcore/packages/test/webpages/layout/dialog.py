# -*- coding: utf-8 -*-

"""Dialogs"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def windowTitle(self):
        return 'Dialogs'
        
    def test_0_dialog(self, pane):
        "Show dialog with splitted region"
        dlg = pane.dialog(title='Test',closable=True,nodeId='testdialog')
        bc = dlg.borderContainer(height='500px',width='1000px')
        bc.contentPane(region='top',height='50px',splitter=True,background='silver')
        bc.contentPane(region='center',background='red')
        pane.button('Show',action='dlg.show()',dlg=dlg.js_widget)

    def test_1_windowRatio(self, pane):
        "Show dialog with splitted region and inner dialog, use of windowRatio to set dimensions"
        dlg = pane.dialog(title='Test',closable=True,parentRatio=.9)
        bc = dlg.borderContainer()
        top = bc.contentPane(region='top',height='50px',splitter=True,background='silver')
        dlg2 = pane.dialog(title='Inner',closable=True,parentRatio=.8)
        bc2 = dlg2.borderContainer()
        top.button('Show inner dialog',action='dlg.show()',dlg=dlg2.js_widget)
        bc.contentPane(region='center',background='red')
        pane.button('Show',action='dlg.show()',dlg=dlg.js_widget)