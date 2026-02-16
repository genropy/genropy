#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('state', pkey='code', name_long='!!State', 
                        name_plural='!!States',caption_field='code',lookup=True)
        self.sysFields(tbl,id=False)
        tbl.column('code' ,size=':5',name_long='!!Code')
        tbl.column('name' ,size=':100',name_long='!!Name')

        tbl.formulaColumn('top_customer_id',
                          select=dict(table='invc.invoice_row',
                                      columns='@invoice_id.customer_id',
                                      where='@invoice_id.@customer_id.state=#THIS.code',
                                      order_by='SUM($tot_price) DESC, @invoice_id.customer_id',
                                      group_by='@invoice_id.customer_id',
                                      limit=1),
                          dtype='T', name_long='Top Customer'
                          ).relation('invc.customer.id', relation_name='top_customer', one_name='Top Customer', many_name='Top States')

        tbl.formulaColumn('top_product_id',
                          select=dict(table='invc.invoice_row',
                                      columns='$product_id',
                                      where='@invoice_id.@customer_id.state=#THIS.code',
                                      order_by='SUM($tot_price) DESC, $product_id',
                                      group_by='$product_id',
                                      limit=1),
                          dtype='T', name_long='Top Product'
                          ).relation('invc.product.id', relation_name='top_product_state', one_name='Top Product', many_name='Top States')
