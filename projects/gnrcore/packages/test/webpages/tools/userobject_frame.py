# -*- coding: utf-8 -*-

"""User objects: saving a piece of page data as a named object, and the group-by editor

`userObjectBar` saves whatever its `source_*` attributes point at into
`adm.userobject`, under the given table and objtype, and loads it back into the
same paths. `groupByEditor` is the grid with the group-by configurator that the
TableHandler stats are built on.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                    gnrcomponents/userobject/userobject_editor:GroupByEditor"""

    def test_2_userobject_bar(self, pane):
        """Fill the name and the rows, save them from the bar as an object, then load it back"""
        frame = pane.framePane(height='300px', width='400px', border='1px solid silver', rounded=10)
        frame.top.userObjectBar(table='adm.tblinfo', objtype='fakeobject',
                                source_mydata='=.mydata',
                                mainIdentifier='test_2')

        bc = frame.center.borderContainer(datapath='.mydata')
        fb = bc.contentPane(region='top').formbuilder()
        fb.textbox(value='^.nome', lbl='Name')
        grid = bc.contentPane(region='center').quickGrid(value='^.righe')
        grid.tools('delrow,addrow', title='Rows')
        grid.column('code', name='Code', width='5em', edit=True)
        grid.column('description', name='Description', width='20em', edit=True)

    def test_3_userobject_groupbyusage(self, pane):
        """The table info grid with its group-by editor: group it by package"""
        pane.groupByEditor(table='adm.tblinfo', height='600px', width='900px')
