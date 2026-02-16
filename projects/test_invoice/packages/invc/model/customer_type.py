#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('customer_type', pkey='code', name_long='!!Customer type', 
                        name_plural='!!Customer types',
                        caption_field='description',
                        lookup=True)
        self.sysFields(tbl,id=False)
        tbl.column('code' ,size=':5',name_long='!!Code')
        tbl.column('description',name_long='Description')