# -*- coding: utf-8 -*-

"""gridGallery showing the rows of whichever grid is selected

Two quickGrids write to two datastore nodes and the filteringSelect at the top
chooses which of the two the gallery reads. Editing a label or adding a row in
the selected grid updates the gallery live: the point of the case is that
gridGallery follows a store path, so it needs no store of its own.
"""

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    def test_1_gridgallery(self,pane):
        """The gallery at the bottom renders the store named by the filteringSelect at the top"""
        bc = pane.borderContainer(height='800px',width='700px')
        bc.contentPane(region='top').filteringSelect(value='^.current_store',values='gg_store_1,gg_store_2')

        top = bc.borderContainer(region='center')
        g1 = top.contentPane(region='left',width='50%').quickGrid(value='^gg_store_1')
        g1.column('label',edit=True,name='Label')
        g1.column('content',edit=True,name='Content')
        g1.tools('addrow,delrow')


        g1 = top.contentPane(region='center').quickGrid(value='^gg_store_2')
        g1.column('label',edit=True,name='Label')
        g1.column('content',edit=True,name='Content')
        g1.tools('addrow,delrow')



        bc.gridGallery(region='bottom',items='^.current_store',height='500px')
