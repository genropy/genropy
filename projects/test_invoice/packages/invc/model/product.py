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

        tbl.formulaColumn('n_sold',
                          select=dict(table='invc.invoice_row',
                                      columns='COUNT(*)',
                                      where='$product_id=#THIS.id'),
                          dtype='L', name_long='N.Sold')

        tbl.formulaColumn('total_sold',
                          select=dict(table='invc.invoice_row',
                                      columns='SUM($tot_price)',
                                      where='$product_id=#THIS.id'),
                          dtype='N', name_long='Total Sold')

        tbl.formulaColumn('top_customer_id',
                          select=dict(table='invc.invoice_row',
                                      columns='@invoice_id.customer_id',
                                      where='$product_id=#THIS.id',
                                      order_by='SUM($tot_price) DESC, @invoice_id.customer_id',
                                      group_by='@invoice_id.customer_id',
                                      limit=1),
                          dtype='T', name_long='Top Customer')

        tbl.formulaColumn('top_state',
                          select=dict(table='invc.invoice_row',
                                      columns='@invoice_id.@customer_id.state',
                                      where='$product_id=#THIS.id',
                                      order_by='SUM($tot_price) DESC, @invoice_id.@customer_id.state',
                                      group_by='@invoice_id.@customer_id.state',
                                      limit=1),
                          dtype='T', name_long='Top State')

