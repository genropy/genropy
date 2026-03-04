# -*- coding: utf-8 -*-

"""Slider"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_basic(self, pane):
        """horizontalSlider, bar with minimum and maximum values and intermediateChanges"""
        fb = pane.formbuilder(cols=2, border_spacing='3px', width='100%', fld_width='30px')
        fb.horizontalSlider(value='^.number', lbl='Number', width='20em', minimum=0, maximum=99,
                               discreteValues=100, intermediateChanges=True)
        fb.div('^.number')
