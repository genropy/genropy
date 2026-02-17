#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('vat_type', pkey='code', name_long='!!VAT type', 
                        name_plural='!!VAT types',
                        caption_field='description',
                        lookup=True)
        self.sysFields(tbl,id=False)
        tbl.column('code' ,size=':5',name_long='!!Code')
        tbl.column('description',name_long='Description')
        tbl.column('vat_rate',dtype='perc',name_long='!!VAT rate')