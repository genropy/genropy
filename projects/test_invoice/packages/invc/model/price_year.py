#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('price_year', pkey='id', name_long='!!Price Year',
                        name_plural='!!Price Years')
        self.sysFields(tbl)
        tbl.column('product_id', size='22', group='_',
                    name_long='!!Product').relation(
            'product.id', relation_name='price_years',
            mode='foreignkey', onDelete='cascade')
        tbl.column('year', dtype='L', name_long='!!Year')
        tbl.column('unit_price', dtype='money', name_long='!!Unit Price')
        tbl.column('note', name_long='!!Note')
        tbl.compositeColumn('product_year_key',
                            columns='product_id,year', unique=True)
        tbl.formulaColumn('price_label',
                          sql_formula="CAST($year AS TEXT) || ': ' || CAST($unit_price AS TEXT)",
                          dtype='T', name_long='Price Label')
        tbl.aliasColumn('product_description',
                        relation_path='@product_id.description',
                        name_long='Product Description')
