# -*- coding: utf-8 -*-

"""plainTableHandler with the extended query bar over a virtual store

A plainTableHandler configured with extendedQuery=True gets the query builder
that lets the user name and reuse a selection, and virtualStore=True keeps the
rows on the server so a large table is paged instead of loaded whole. The
combination is what a named selection needs: the query is rebuilt server side
every time the selection is reopened.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_a(self, pane):
        """Named selections: extended query and virtual store on glbl.comune"""
        bc = pane.borderContainer(height='1000px')
        bc.contentPane(region='top', height='400px').plainTableHandler(table='glbl.comune', datapath='.topth',
                                                                      viewResource='View', extendedQuery=True,
                                                                      virtualStore=True,
                                                                      nodeId='topth', export=True)
