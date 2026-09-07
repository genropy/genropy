#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('product_group', pkey='id', name_long='!!Product group',
                        name_plural='!!Product groups',
                        caption_field='hierarchical_code')
        # '_row_count' is part of the hierarchical list on purpose: it exercises
        # the hierarchical counter being used as a hierarchical field itself.
        self.sysFields(tbl, hierarchical='code,_row_count', counter=True)
        tbl.column('code', size=':10', name_long='!!Code')
        tbl.column('description', size=':50', name_long='!!Description')
