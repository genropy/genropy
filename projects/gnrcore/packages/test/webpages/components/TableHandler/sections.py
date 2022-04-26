# -*- coding: utf-8 -*-

"Sections"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase,th/th:TableHandler"

    def test_0_depending_sections(self,pane):
        """Sections filtering data on loading"""
        pane.borderContainer(height='500px').contentPane(region='center').plainTableHandler(table='glbl.provincia',
                                                                                            viewResource='ViewTestSections',
                                                                                            condition_onStart=True)

    def test_1_relations_sections(self,pane):
        """Sections using deep relations"""
        pane.borderContainer(height='500px').contentPane(region='center').plainTableHandler(table='glbl.comune',
                                                                                            viewResource='ViewTestSections',
                                                                                           # view_store_onStart=True
                                                                                           )