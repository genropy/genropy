# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_icons(self, pane):
        """Fontawesome icon"""
        pane.div(height='30px').span(_class='fas fa-user')

    def test_1_button(self, pane):
        """Fontawesome icon"""
        pane.div(height='30px').button(iconClass='fas fa-user')
        pane.div(height='30px').button(iconClass='iconbox plus')