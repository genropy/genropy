# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase,msgarea_component:MsgArea"
    
    def test_0_relative_path(self, pane):     
        "With relative path you can replicate modules infinite times, filling fields with different records"
        prov = self.db.table('glbl.provincia').query(where='$regione=:reg', reg='EMI').fetch()
        for p in prov:
            self.formProvincia(pane,Bag(p))
    
    def formProvincia(self,pane,prov_record,**kwargs):
        prov_sigla = prov_record['sigla']
        prov_box = pane.div(border='1px solid silver', datapath=prov_sigla)
        prov_box.data(prov_sigla,prov_record)
        fb=prov_box.formbuilder(cols=2, fld_width='100%')
        fb.input('^.nome', lbl='Nome', colspan=2)
        fb.input('^.sigla',lbl='Sigla',width='100%')
        fb.input('^.codice_istat', lbl='Cod.ISTAT')   
    
    def test_1_relative_path_annidato(self,pane):
        "Same as before, but in this case the relative path structure is more complex"
        tc = pane.tabContainer(datapath='regioni', height='500px')
        for r in ['EMI','LOM','VEN']:
            pane = tc.contentPane(title=r, datapath=f'.{r}')
            prov = self.db.table('glbl.provincia').query(where='$regione=:reg', reg=r).fetch()
            for p in prov:
                self.formProvinciaModificata(pane,Bag(p))
    
    def formProvinciaModificata(self,pane,prov_record,**kwargs):
        prov_datapath = '.{prov_sigla}'.format(prov_sigla=prov_record['sigla'])
        prov_box = pane.div(border='1px solid silver', datapath=prov_datapath)
        pane.data(prov_datapath,prov_record)
        fb=prov_box.formbuilder(cols=2, fld_width='100%')
        fb.input('^.nome', lbl='Nome', colspan=2)
        fb.input('^.sigla',lbl='Sigla',width='100%')
        fb.input('^.codice_istat', lbl='Cod.ISTAT') 

    def test_video(self, pane):
        "These relative path tests were explained in this Genropy Course video"
        pane.iframe(src='https://player.vimeo.com/video/551396074', width='240px', height='180px',
                        allow="autoplay; fullscreen")