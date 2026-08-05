#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('product_type', pkey='id', name_long='!!Product type',
                         name_plural='!!Product types',
                        caption_field='hierarchical_description')
        self.sysFields(tbl,hierarchical='description',counter=True,df=True)
        tbl.column('description' ,size=':50',name_long='!!Description')