#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('product_family', pkey='id', name_long='!!Product family',
                        name_plural='!!Product families',
                        caption_field='hierarchical_description')
        # 'code' is assigned by a counter and is a hierarchical field: it
        # exercises a counter column that the hierarchical paths are built from.
        self.sysFields(tbl, hierarchical='description,code', counter=True)
        tbl.column('code', size=':6', name_long='!!Code', unique=True)
        tbl.column('description', size=':50', name_long='!!Description')

    def counter_code(self, record=None):
        return dict(format='$K$NNNN', code='')
