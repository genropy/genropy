# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('faq_area', pkey='id', name_long='!!FAQ area', name_plural='!!FAQ areas',
                            caption_field='name')
        self.sysFields(tbl, hierarchical='name', counter=True)
        
        tbl.column('name', name_long='!![en]Name')