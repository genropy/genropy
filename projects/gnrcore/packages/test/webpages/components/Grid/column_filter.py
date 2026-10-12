# -*- coding: utf-8 -*-

"""Grid column filter: filterField on the cell

A cell with filterField gets a filter icon in its header. The icon opens the
list of the values the column holds, each with its count; checking values
filters the grid. filterField=True filters on the cell's own field, a field
name filters on that related field and shows the cell's text. Clicking the
column title still sorts. The filter runs in the browser, so a grid on a
virtual store ignores filterField and shows no icon.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_static(self, pane):
        """Static store on glbl.provincia: values, counts and filters in the browser"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.provincia', datapath='.provincia',
                                                          viewResource='ViewColumnFilter',
                                                          view_store_onStart=True)

    def test_1_virtual(self, pane):
        """Virtual store on glbl.comune: filterField is ignored, no filter icon"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.comune', datapath='.comune',
                                                          viewResource='ViewColumnFilter',
                                                          virtualStore=True,
                                                          view_store_onStart=True)
