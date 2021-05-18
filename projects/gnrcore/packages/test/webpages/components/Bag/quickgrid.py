# -*- coding: utf-8 -*-

"""quickGrid"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
import psutil

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

    def test_3_columns_editable(self,pane):
        "Quick grid with editable columns and default value. Insert province to test it"
        t = pane.table().tbody()
        r = t.tr()
        self.quickGridEditable(r.td(border='1px solid silver',padding='4px'),pos='TL')

    def quickGridEditable(self,pane,pos=None):
        box = pane.div(datapath='.%s' %pos)
        b = Bag()
        pane.data('.griddata',b)
        fb = box.formbuilder()
        fb.textBox('^.def_location',lbl='Default location', placeholder='MI')
        grid = box.quickGrid(value='^.griddata',
                        columns='^.columns',
                        default_location='=.def_location',
                        height='150px',width='400px' ,border='1px solid silver')
        grid.tools('addrow,delrow,duprow,export',position=pos)
        grid.column('location',name='Location',width='15em',edit=dict(tag='dbselect',dbtable='glbl.provincia'))
        grid.column('name',name='Name',width='15em',edit=True)
        grid.column('is_ok',name='Ok',dtype='B',edit=True)


    def test_4_syntax(self,pane):
        "Basic quick grid with two different methods but same result (view code differences)"""
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').formbuilder(cols=2,border_spacing='3px')
        fb.dbselect(value='^.provincia',dbtable='glbl.provincia',lbl='provincia')
        fb.textBox('^.fields',lbl='Fields')
        #1st method: fetch and Bag
        fb.dataRpc('.data',self.bagComuni,provincia='^.provincia',_if='provincia',_else='null')
        #2nd alternative method: output selection
        #fb.dataRpc('.data',self.bagComuniAttr,provincia='^.provincia',_if='provincia',_else='null')

        grid = bc.contentPane(region='center').quickGrid(value='^.data',height='300px',fields='^.fields')
        grid.column('denominazione',color='red',width='40em',name='Den',edit=True)
        grid.tools('export',position='TR')

    @public_method
    def bagComuni(self,provincia=None):
        f = self.db.table('glbl.comune').query(where='$sigla_provincia=:pr',pr=provincia).fetch()
        result = Bag()
        for r in f:
            r = dict(r)
            r['is_ok'] = None
            result[r['id']] = Bag(r)
        return result

    @public_method
    def bagComuniAttr(self,provincia=None):
        return self.db.table('glbl.comune').query(where='$sigla_provincia=:pr',pr=provincia).selection().output('selection')

    def test_5_cpu(self,pane,**kwargs):
        "Basic quick grid with cpu usage values, loaded on start and refreshed every 2 seconds"
        pane=pane.div(margin='15px',datapath='.cpuTimes',height='200px',width='500px')
        pane.quickGrid(value='^.data',
                       border='1px solid silver',
                              font_family='courier',
                              font_weight='bold',
                              height='auto',width='auto'
                              )
        
        pane.dataRpc('.data', self.getCpuTimes,
                     _timing=2,
                     _onStart=True)
    @public_method
    def getCpuTimes(self):
        result=Bag()
        columns=['user','nice','system','idle']
        for j, core in enumerate(psutil.cpu_times(True)):
            row = Bag()
            row['core']=j+1
            for k in columns:
                row.setItem(k, getattr(core,k))
            result.setItem('r_%i'%j, row)
        return result

    def test_video(self, pane):
        "This quickGrid test was explained in this LearnGenropy video"
        pane.iframe(src='https://www.youtube.com/embed/MnqfBy6Q2Ns', width='240px', height='180px')
