# -*- coding: utf-8 -*-

"""Dialogs"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
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

    def test_2_autoSize(self, pane):
        "Form dialog with dialog_autoSize: it fits the loaded record, short or long"
        pane.thFormHandler(table='test.myticket', formId='autosize_form',
                           formResource='FormAutoSize', datapath='main.autosize',
                           dialog_autoSize=True)
        short = dict(subject='Short', description='One line only.')
        long_text = '\n'.join('Line %i of a long description.' % i for i in range(1, 41))
        pane.button('Short', action="genro.formById('autosize_form').newrecord(defaults);",
                    defaults=short)
        pane.button('Long', action="genro.formById('autosize_form').newrecord(defaults);",
                    defaults=dict(subject='Long', description=long_text))
        pane.button('Wide', action="genro.formById('autosize_form').newrecord(defaults);",
                    defaults=dict(subject='Wide', description='W' * 150))

    def test_3_autoSizeLayout(self, pane):
        "dialog_autoSize on a form whose center is a borderContainer: it takes the windowRatio cap"
        pane.thFormHandler(table='test.myticket', formId='autosize_layout_form',
                           datapath='main.autosize_layout', dialog_autoSize=True)
        pane.button('Open', action="genro.formById('autosize_layout_form').newrecord();")
