#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('product', pkey='id', name_long='!!Product', name_plural='!!Prodocts',caption_field='description')
        self.sysFields(tbl)
        tbl.column('code' ,size=':10',name_long='!!Code')
        tbl.column('description' ,size=':80',name_long='!!Description')
        tbl.column('presentation_txt',name_long='!!Presentation')
        tbl.column('vat_type_code',size=':5' ,group='_',name_long='!![it]VAT type').relation('vat_type.code',relation_name='products',mode='foreignkey',onDelete='raise')

        tbl.column('product_type_id',size='22' ,group='_',name_long='!!Product type',name_short='Type').relation('product_type.id',relation_name='products',mode='foreignkey',onDelete='raise')
        tbl.column('unit_price',dtype='money',name_long='!!Price',name_short='Price')
        tbl.column('image_url' ,dtype='P',name_long='!!Image url',name_short='Img')
        tbl.column('details',dtype='X',name_long='!!Details',subfields='product_type_id')
        tbl.formulaColumn('picture',"image_url" ,dtype='P',name_long='!!Picture',name_short='Img',cell_format='auto:.5')
        tbl.formulaColumn('total_sold',
                          select=dict(table='invc.invoice_row',
                                      columns='SUM($quantity)',
                                      where='$product_id=#THIS.id'),
                          dtype='N',name_long='Total Sold')
        tbl.formulaColumn('price_range',
                          sql_formula="CASE WHEN $unit_price > 500 THEN 'Premium' WHEN $unit_price > 100 THEN 'Mid' ELSE 'Budget' END",
                          dtype='A', name_long='Price Range')
        tbl.formulaColumn('code_and_desc',
                          sql_formula="$code || ' - ' || $description",
                          dtype='T', name_long='Code and Description')
        tbl.formulaColumn('price_floor',
                          sql_formula='GREATEST($unit_price, 10)',
                          dtype='money', name_long='Price Floor')
        tbl.formulaColumn('price_label',
                          sql_formula="$description || ' (' || CAST($unit_price AS TEXT) || ')'",
                          dtype='T', name_long='Price Label')
        tbl.aliasColumn('product_type_name',
                        relation_path='@product_type_id.description',
                        name_long='Product Type')
