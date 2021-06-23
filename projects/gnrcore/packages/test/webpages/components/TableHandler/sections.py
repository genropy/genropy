# -*- coding: utf-8 -*-

"Sections"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_depending_sections(self,pane):
        """Sections filtering data on loading"""
        pane.borderContainer(height='500px').contentPane(region='center').plainTableHandler(table='glbl.provincia',
                                                                                            viewResource='ViewTestSections',
                                                                                            condition_onStart=True)