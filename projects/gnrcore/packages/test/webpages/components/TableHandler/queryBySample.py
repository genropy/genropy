# -*- coding: utf-8 -*-

"queryBySample"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase,th/th:TableHandler"

    def test_0_queryBySample(self,pane):
        """queryBySample for most used research fields, with use of special characters in labels"""
        pane.borderContainer(height='500px').contentPane(region='center').plainTableHandler(table='glbl.comune',
                                                                                            viewResource='ViewTestQuery',
                                                                                            extendedQuery=True)

    def test_1_condition(self,pane):
        """queryBySample with widgets and conditions"""
        pane.borderContainer(height='500px').contentPane(region='center').plainTableHandler(table='glbl.comune',
                                                                                            viewResource='ViewTestQueryCondition',
                                                                                            extendedQuery=True)