# -*- coding: utf-8 -*-

"""bagGrid"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:frameGrid"
    
    def struct_spesa(self, struct):
        r = struct.view().rows()
        r.cell('articolo', width='20em', name='Articolo', edit=True)
        r.cell('quantita', width='10em', dtype='L', name='Quantità', edit=True)

    def test_0_baggrid(self, pane):
        "BagGrid with possibility to add and remove records. Check inspector to see generated Bag"
        frame = pane.bagGrid(struct=self.struct_spesa, datapath='.vista_spesa', storepath='.lista_spesa', 
                                    height='400px', width='400px', export=True, searchOn=True)

    def test_video(self, pane):
        "This bagGrid test was explained in this LearnGenropy video"
        pane.iframe(src='https://www.youtube.com/embed/MnqfBy6Q2Ns', width='480px', height='360px')