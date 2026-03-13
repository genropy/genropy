#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('product', pkey='id', name_long='!!Product', name_plural='!!Prodocts',caption_field='description')
        self.sysFields(tbl)
        tbl.column('code' ,size=':10',name_long='!!Code')
        tbl.column('description' ,size=':80',name_long='!!Description',ext_emb=dict(emb_type='text'))
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
        tbl.bagItemColumn('detail_weight', bagcolumn='$details',
                          itempath='specs.weight', dtype='N',
                          name_long='Detail Weight')
        tbl.bagItemColumn('detail_color', bagcolumn='$details',
                          itempath='specs.color', dtype='T',
                          name_long='Detail Color')
        tbl.formulaColumn('concat_code_desc',
                          sql_formula="CONCAT($code, ' - ', $description)",
                          dtype='T', name_long='Concat Code Desc')
        tbl.formulaColumn('code_normalized',
                          sql_formula="lower(regexp_replace($code, '[^a-zA-Z0-9]', '', 'g'))",
                          dtype='T', name_long='Code Normalized')
        tbl.formulaColumn('code_clean',
                          sql_formula="translate($code, ' /-', '___')",
                          dtype='T', name_long='Code Clean')
        tbl.pyColumn('computed_margin', dtype='N',
                     required_columns='$unit_price',
                     name_long='Computed Margin')
        tbl.formulaColumn('price_rounded',
                          sql_formula='ROUND($unit_price, 0)',
                          dtype='N', name_long='Price Rounded')
        tbl.formulaColumn('description_clean',
                          sql_formula="REPLACE($description, ' ', '-')",
                          dtype='T', name_long='Description Clean')
        tbl.formulaColumn('code_prefix_std',
                          sql_formula="substring($code FROM 1 FOR 3)",
                          dtype='T', name_long='Code Prefix Std')
        tbl.formulaColumn('price_as_int_text',
                          sql_formula="CAST(CAST($unit_price AS integer) AS text)",
                          dtype='T', name_long='Price As Int Text')

    def pyColumn_computed_margin(self, record, field):
        price = record.get('unit_price') or 0
        return price * 0.3
