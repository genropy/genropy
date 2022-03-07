# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_basic(self, pane):
        "timeTextBox widget to insert time informations"
        pane.timetextbox(value='^.ttb')
        pane.div('^.ttb')

    def test_2_dh(self,pane):
        "dateTimeTextBox inserts both date and time"
        fb = pane.formbuilder()
        fb.datetimeTextBox(value='^.dhbox',lbl='DHBOX',dtype='DHZ')
