# -*- coding: utf-8 -*-

"""quickGrid"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    @public_method
    def getMyData(self):
        feed = Bag('https://www.ansa.it/sito/ansait_rss.xml')
        result = Bag()
        for i,n in enumerate(feed['rss.channel']):
            if n.label == 'item':
                result.addItem(f'r_{i}',n.value)
        return result
    
    def test_0_quickgrid(self, pane):
        "Quick grid to show ANSA feed. Press 'Load' button to build bag and show grid content"
        bc = pane.borderContainer(height='600px')
        bc.contentPane(region='top',height='100px').button('Load', fire='.load')
        pane.dataRpc('.data', self.getMyData, _fired='^.load')
        grid = bc.contentPane(region='center').quickGrid(value='^.data')
        grid.column('title', width='20em', name='Title')
        grid.column('pubDate', width='10em', name='Publish Date')
        grid.column('link', width='50em', name='Link')

    def test_1_quickgrid(self, pane):
        "Same as before, but with iframe to show selected post on bottom"
        bc = pane.borderContainer(height='900px')
        bc.contentPane(region='top',height='100px').button('Load', fire='.load')
        pane.dataRpc('.data', self.getMyData, _fired='^.load')
        grid = bc.contentPane(region='center').quickGrid(value='^.data', selected_link='.selectedLink')
        grid.column('title', width='20em', name='Title')
        grid.column('pubDate', width='10em', name='Publish Date')
        grid.column('link', width='50em', name='Link')
        bottom = bc.contentPane(region='bottom', height='400px')
        bottom.iframe(src='^.selectedLink', width='100%', height='100%')

    def test_2_quickgrid(self, pane):
        "Quick grid with possibility to add and remove records. Check inspector to see generated Bag"
        bc = pane.borderContainer(height='400px')
        grid = bc.contentPane(region='center').quickGrid(value='^.lista_spesa')
        grid.tools('delrow,addrow,export')
        grid.column('articolo', width='20em', name='Articolo', edit=True)
        grid.column('quantita', width='10em', dtype='L', name='Quantità', edit=True)

    def test_video(self, pane):
        "This quickGrid test was explained in this LearnGenropy video"
        pane.iframe(src='https://www.youtube.com/embed/MnqfBy6Q2Ns', width='240px', height='180px')