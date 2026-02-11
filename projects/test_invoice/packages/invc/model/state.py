#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('state', pkey='code', name_long='!!State', 
                        name_plural='!!States',caption_field='code',lookup=True)
        self.sysFields(tbl,id=False)
        tbl.column('code' ,size=':5',name_long='!!Code')
        tbl.column('name' ,size=':100',name_long='!!Name')