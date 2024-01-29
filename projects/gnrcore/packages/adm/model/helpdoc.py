# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('helpdoc', pkey='id', 
                      name_long='!![en]Help document', 
                      name_plural='!![en]Help documents',
                      caption_field='title',lookup=True)
        self.sysFields(tbl)
        tbl.column('title', size=':25', name_long='Title')
        tbl.column('url', name_long='Url')
        tbl.column('description', name_long='Description')

