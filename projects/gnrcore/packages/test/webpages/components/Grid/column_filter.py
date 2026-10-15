# -*- coding: utf-8 -*-

"""Grid column filter: filterField on the cell

A cell with filterField gets a filter icon in its header. The icon opens the
list of the values the column holds, each with its count; checking values
filters the grid. filterField=True filters on the cell's own field, a field
name filters on that related field and shows the cell's text. Clicking the
column title still sorts. The filter runs in the browser, so a grid on a
virtual store ignores filterField and shows no icon.

filterFieldDefault on the grid (grid_filterFieldDefault in the th options)
turns filterField on for every cell that shows a plain field, columns added
from the configurator included; template, calculated, values and button cells
are left out, and filterField=False opts a cell out.
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

    def test_2_default(self, pane):
        """Static store with grid_filterFieldDefault: every plain column gets the filter"""
        bc = pane.borderContainer(height='450px')
        bc.contentPane(region='center').plainTableHandler(table='glbl.provincia', datapath='.provincia_default',
                                                          grid_filterFieldDefault=True,
                                                          view_store_onStart=True)
