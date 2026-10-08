# -*- coding: utf-8 -*-

"""TableHandler on a hierarchical table, its view shown as a tree

The first column of the view is hierarchical_description with hierarchical='/':
the grid nests the rows of the selection by that path, client side. Export,
print, delete and the form keep working on the same selection; the tree only
decides which rows are visible and in which order. An ancestor that is not in
the selection shows as a virtual row.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_htag_tree(self, pane):
        """adm.htag nested by its hierarchical_description. A query whose result leaves out the
        parent of a tag brings that parent in as a virtual row"""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='center').stackTableHandler(table='adm.htag', viewResource='HierarchicalView',
                                                          view_structCb=self.htagTreeStruct,
                                                          condition__onBuilt=True)

    def htagTreeStruct(self, struct):
        "Tree"
        r = struct.view().rows()
        r.fieldcell('hierarchical_description', hierarchical='/', width='25em')
        r.fieldcell('code', width='12em')
        r.fieldcell('hierarchical_code', width='20em')
        r.fieldcell('child_count', width='6em')
