# -*- coding: utf-8 -*-

"""Zooming a grid: the grid_scaleX and grid_scaleY attributes of a TableHandler

The two sliders drive `grid_scaleX` and `grid_scaleY` of a `plainTableHandler`
on `glbl.provincia`: the scale is applied to the grid's own rendering, so rows
and columns shrink or grow while the store, the selection and the toolbars keep
working untouched.
"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def windowTitle(self):
        return 'Grid scale'

    def test_1_gridscale(self, pane):
        """A plainTableHandler whose grid is scaled on both axes by two sliders"""
        bc = pane.borderContainer(height='600px', width='800px')
        th = bc.plainTableHandler(table='glbl.provincia', view_store__onStart=True,
                                  grid_scaleX='^.scaleX',
                                  grid_scaleY='^.scaleY',
                                  region='center')
        fb = th.view.bottom.slotToolbar('10,fbscale,*').fbscale.formbuilder(cols=2)
        fb.horizontalSlider(value='^.grid.scaleX', lbl='Scale X', minimum=0.3, maximum=1,
                            intermediateChanges=True, width='10em')
        fb.horizontalSlider(value='^.grid.scaleY', lbl='Scale Y', minimum=0.3, maximum=1,
                            intermediateChanges=True, width='10em')
