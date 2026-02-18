#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('customer', pkey='id', name_long='!!Customer', name_plural='!!Customers',caption_field='account_name')
        self.sysFields(tbl) # aggiunge id autogenerato, __ins_ts,__mod_ts,etc.
        tbl.column('account_name', name_long='!!Account name',name_short='Account name', validate_notnull=True, validate_len='2:40')
        tbl.column('street_address',name_long='!!Street Address', name_short='St.Address')
        tbl.column('suburb', name_long='!!Suburb', name_short='!!Suburb')
        tbl.column('state',size=':5',name_long='!!State',name_short='Pr.').relation('invc.state.code',relation_name='clients',mode='foreignkey',onDelete='raise')
        tbl.column('postcode',size=':5',name_long='!!Postcode',name_short='Postcode')
        tbl.column('postcode_id',size='22',name_long='!!Postcode Ref',name_short='PC Ref').relation('postcode.id',relation_name='customers_by_postcode',mode='foreignkey')
        tbl.column('customer_type_code', size=':5',name_long='!!Customer type code',name_short='!!Cust type').relation('customer_type.code',relation_name='customers',mode='foreignkey',onDelete='raise')
        tbl.column('payment_type_code',size=':10',name_long='!!Payment type code',name_short='!!Pay type').relation('payment_type.code',relation_name='customers',mode='foreignkey',onDelete='raise')
        tbl.column('notes',name_long="!!Notes")
        tbl.column('email',name_long='!!Email')
        tbl.column('phone' ,name_long='!!Phone')
        tbl.formulaColumn('n_invoices',select=dict(table='invc.invoice',
                                                  columns='COUNT(*)',
                                                  where='$customer_id=#THIS.id'),
                                      dtype='L',name_long='N.Invoices')

        tbl.formulaColumn('invoiced_total',select=dict(table='invc.invoice',
                                                  columns='SUM($total)',
                                                  where='$customer_id=#THIS.id'),
                                      dtype='N',name_long='Invoiced Total')

        tbl.formulaColumn('last_invoice_date',
                          select=dict(table='invc.invoice',
                                      columns='MAX($date)',
                                      where='$customer_id=#THIS.id'),
                          dtype='D', name_long='Last Invoice Date')

        tbl.formulaColumn('avg_invoice_total',
                          select=dict(table='invc.invoice',
                                      columns='AVG($total)',
                                      where='$customer_id=#THIS.id'),
                          dtype='N', name_long='Avg Invoice Total')

        tbl.formulaColumn('max_invoice',
                          select=dict(table='invc.invoice',
                                      columns='MAX($total)',
                                      where='$customer_id=#THIS.id'),
                          dtype='N', name_long='Max Invoice')

        tbl.formulaColumn('min_invoice',
                          select=dict(table='invc.invoice',
                                      columns='MIN($total)',
                                      where='$customer_id=#THIS.id'),
                          dtype='N', name_long='Min Invoice')

        for year in (2022, 2023, 2024, 2025):
            tbl.formulaColumn(f'invoiced_{year}',
                              select=dict(table='invc.invoice',
                                          columns='SUM($total)',
                                          where=f'$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)={year}'),
                              dtype='N', name_long=f'Invoiced {year}')
            tbl.formulaColumn(f'n_invoices_{year}',
                              select=dict(table='invc.invoice',
                                          columns='COUNT(*)',
                                          where=f'$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)={year}'),
                              dtype='L', name_long=f'N.Invoices {year}')

        tbl.formulaColumn('top_product_id',
                          select=dict(table='invc.invoice_row',
                                      columns='$product_id',
                                      where='@invoice_id.customer_id=#THIS.id',
                                      order_by='SUM($tot_price) DESC, $product_id',
                                      group_by='$product_id',
                                      limit=1),
                          dtype='T', name_long='Top Product'
                          ).relation('invc.product.id', relation_name='top_product', one_name='Top Product', many_name='Top Customers')

        tbl.formulaColumn('top_product_n_sold',
                          select=dict(table='invc.invoice_row',
                                      columns='SUM($quantity)',
                                      where='@invoice_id.customer_id=#THIS.id AND $product_id=#THIS.top_product_id'),
                          dtype='L', name_long='Top Product N.Sold')

        tbl.formulaColumn('last_invoice_id',
                          select=dict(table='invc.invoice',
                                      columns='$id',
                                      where='$customer_id=#THIS.id',
                                      order_by='$date DESC, $id',
                                      limit=1),
                          dtype='T', name_long='Last Invoice')

        # Torture test: deep traversal on BOTH sides of the join
        # remote: invoice_row → product → product_type → production_state (3 hops)
        # local:  customer → postcode → state (2 hops via #THIS)
        tbl.formulaColumn('sales_from_local_state',
                          select=dict(table='invc.invoice_row',
                                      columns='SUM($tot_price)',
                                      where='@invoice_id.customer_id=#THIS.id AND @product_id.@product_type_id.production_state=#THIS.@postcode_id.state'),
                          dtype='N', name_long='Sales From Local State')

        tbl.formulaColumn('sales_from_local_state_v2',
                          select=dict(table='invc.invoice_row',
                                      columns='SUM($tot_price)',
                                      where='@invoice_id.@customer_id.@postcode_id.state=@product_id.@product_type_id.production_state'),
                          dtype='N', name_long='Sales From Local State V2')
