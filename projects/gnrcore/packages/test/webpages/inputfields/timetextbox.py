# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_basic(self, pane):
        "timeTextBox widget to insert time informations"
        pane.timetextbox(value='^.ttb', width='5em')
        pane.div('^.ttb')

    def test_2_dh(self,pane):
        "dateTimeTextBox inserts both date and time"
        fb = pane.formbuilder()
        fb.datetimeTextBox(value='^.dhbox',lbl='DHBOX',dtype='DHZ', width='8em')

    def test_3_editable_grid(self, pane):
        "timeTextBox in editable grid"
        grid = pane.quickGrid(value='^.schedule', height='300px')
        grid.tools('delrow,addrow')
        grid.column('description', edit=True, name='Description', width='15em')
        grid.column('start_time', edit=dict(tag='timeTextBox'), name='Start', width='4em', dtype='H')
        grid.column('end_time', edit=dict(tag='timeTextBox'), name='End', width='4em', dtype='H')
