# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    
    def main(self,root,**kwargs):
        "With relative path you can replicate modules infinite times, filling fields with different records"
        prov = self.db.table('glbl.provincia').query(where='$regione=:reg', reg='EMI').fetch()
        for p in prov:
            self.formProvincia(root,Bag(p))
    
    def formProvincia(self,pane,prov_record,**kwargs):
        prov_sigla = prov_record['sigla']
        prov_box = pane.div(border='1px solid silver', datapath=prov_sigla)
        prov_box.data(prov_sigla,prov_record)
        fb=prov_box.formbuilder(cols=2, fld_width='100%')
        fb.input('^.nome', lbl='Nome', colspan=2)
        fb.input('^.sigla',lbl='Sigla',width='100%')
        fb.input('^.codice_istat', lbl='Cod.ISTAT')   