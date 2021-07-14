# -*- coding: utf-8 -*-

"""Buttons"""

from builtins import object
class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_basic(self, pane):
        """Basic button"""
        pane.timetextbox(value='^.ttb')
        pane.div('^.ttb')


    def test_2_dh(self,pane):
        fb = pane.formbuilder()
        fb.dataFormula('.dhbox','new Date()',_onStart=True)
        fb.datetimeTextBox(value='^.dhbox',lbl='DHBOX',dtype='DHZ')
        fb.dataController('console.log(dhbox,dhbox._gnrdtype)',dhbox='^.dhbox')