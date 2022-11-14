# encoding: utf-8

from builtins import object
from gnr.core.gnrdecorator import metadata

class Table(object):
    def config_db(self,pkg):
        tbl =  pkg.table('language',pkey='code',name_long='!![en]Language',name_plural='!![en]Languages',
                                    caption_field='code', lookup=True)
        self.sysFields(tbl,id=False,counter=True)
        tbl.column('code',size=':2',name_long='!![en]Code',unique=True,indexed=True)
        tbl.column('name',size=':50',name_long='!![en]Name',unique=True,indexed=True)
        
        tbl.column('params_lbl', name_long='!![en]Parameters lbl')
        tbl.column('params_name_lbl', name_long='!![en]Parameters name lbl')
        tbl.column('params_type_lbl', name_long='!![en]Parameters type lbl')
        tbl.column('params_desc_lbl', name_long='!![en]Parameters description lbl')
        tbl.column('attachments_lbl', name_long='!![en]Attachments lbl')

    @metadata(mandatory=True)
    def sysRecord_it(self):
        return self.newrecord(code='it',name='Italiano',params_lbl='Parametri',
                                params_name_lbl='Nome parametro',params_type_lbl='Tipo',
                                params_desc_lbl='Descrizione', attachments_lbl='Allegati')

    @metadata(mandatory=True)
    def sysRecord_en(self):
        return self.newrecord(code='en',name='English',params_lbl='Parameters',
                                params_name_lbl='Parameter name',params_type_lbl='Type',
                                params_desc_lbl='Description', attachments_lbl='Attachments')