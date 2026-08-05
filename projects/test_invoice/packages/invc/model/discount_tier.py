#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('discount_tier', pkey='id', name_long='!!Discount Tier',
                        name_plural='!!Discount Tiers')
        self.sysFields(tbl)
        tbl.column('customer_type_code', size=':5', name_long='!!Customer Type').relation(
            'customer_type.code', relation_name='discount_tiers',
            mode='foreignkey', onDelete='cascade')
        tbl.column('min_amount', dtype='N', name_long='!!Min Amount')
        tbl.column('max_amount', dtype='N', name_long='!!Max Amount')
        tbl.column('discount_rate', dtype='perc', name_long='!!Discount Rate')
        tbl.column('description', name_long='!!Description')
