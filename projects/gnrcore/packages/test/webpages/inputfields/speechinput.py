# -*- coding: utf-8 -*-

"Speech input test page"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_simpleTextArea(self, pane):
        """SimpleTextArea with speech=True — mic button should appear on supported browsers"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.simpleTextArea(value='^.note', height='300px', width='400px',
                         lbl='Note', speech=True)
        fb.div('^.note')

    def test_1_textbox(self, pane):
        """Textbox with speech=True — no mic button expected (not yet supported)"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(value='^.prova', speech=True, lbl='Textbox')
        fb.div('^.prova')

    def test_2_dbselect(self, pane):
        """DbSelect with speech=True — no mic button expected (not yet supported)"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.dbSelect(dbtable='glbl.provincia', value='^.provincia',
                   lbl='Provincia', speech=True)
        fb.div('^.provincia')
