#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('price_year_note', pkey='id',
                        name_long='!!Price Year Note',
                        name_plural='!!Price Year Notes')
        self.sysFields(tbl)
        tbl.column('product_id', size='22', group='_',
                    name_long='!!Product').relation(
            'product.id', relation_name='price_year_notes',
            mode='foreignkey', onDelete='cascade')
        tbl.column('year', dtype='L', name_long='!!Year')
        tbl.compositeColumn('product_year_ref',
                            columns='product_id,year').relation(
            'price_year.product_year_key',
            relation_name='notes')
        tbl.column('note_text', name_long='!!Note Text')
        tbl.column('importance', dtype='I', name_long='!!Importance')
        tbl.aliasColumn('price_year_price',
                        relation_path='@product_year_ref.unit_price',
                        name_long='Price Year Price')
        tbl.aliasColumn('price_year_label',
                        relation_path='@product_year_ref.price_label',
                        name_long='Price Year Label')
        tbl.aliasColumn('product_description',
                        relation_path='@product_year_ref.@product_id.description',
                        name_long='Product Description')
