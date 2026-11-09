# -*- coding: utf-8 -*-

"""Product types shown as a tree

A TableHandler on invc.product_type whose view starts with hierarchical_description
and hierarchical='/': the grid nests the selection rows by that path.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_0_product_type_tree(self, pane):
        """Expand the types; double click a type to open it in the form"""
        bc = pane.borderContainer(height='500px')
        bc.contentPane(region='center').stackTableHandler(table='invc.product_type',
                                                          viewResource='TreeView',
                                                          view_structCb=self.productTypeStruct,
                                                          condition__onBuilt=True)

    def test_1_ancestors_out_of_the_query(self, pane):
        """The query keeps only the hammers: Hand Tools is not among the rows and shows as
        a virtual ancestor"""
        bc = pane.borderContainer(height='300px')
        bc.contentPane(region='center').plainTableHandler(table='invc.product_type', nodeId='hammers',
                                                          viewResource='TreeView',
                                                          view_structCb=self.productTypeStruct,
                                                          condition="$description ILIKE :pattern",
                                                          condition_pattern='%Hammers%',
                                                          condition__onBuilt=True)

    def productTypeStruct(self, struct):
        "Tree"
        r = struct.view().rows()
        r.fieldcell('hierarchical_description', hierarchical='/', width='25em')
        r.fieldcell('description', width='15em')
        r.fieldcell('child_count', width='6em')
