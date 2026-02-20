#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('invoice_row', pkey='id', name_long='!!Invoice row', name_plural='!!Invoice rows')
        self.sysFields(tbl,counter='invoice_id')
        tbl.column('invoice_id',size='22' ,group='_',
                    name_long='!!Invoice').relation('invoice.id',relation_name='rows',mode='foreignkey',onDelete='cascade')
        tbl.column('product_id',size='22' ,group='_',name_long='!!Product').relation('product.id',relation_name='invoice_rows',mode='foreignkey',onDelete='raise')
        tbl.column('quantity',dtype='I',name_long=u'!![it]Quantity',name_short='Q.')
        tbl.column('unit_price',dtype='money',name_long='!!Unit price',name_short='U.Pr.')
        tbl.column('tot_price',dtype='money',name_long='!!Total price',name_short='T.Pr.')
        tbl.column('vat', dtype='money', name_long='VAT', name_short='VAT')
        tbl.column('vat_rate',dtype='perc',name_long='!![it]Vat rate')
        tbl.aliasColumn('customer_name', relation_path='@invoice_id.@customer_id.account_name',
                        name_long='Customer name')
        tbl.aliasColumn('customer_id', relation_path='@invoice_id.customer_id',
                        name_long='Customer id'
                        ).relation('customer.id',relation_name='invoice_rows_by_customer',mode='foreignkey')
        tbl.aliasColumn('product_name',
                        relation_path='@product_id.description',
                        name_long='Product Name')
        tbl.aliasColumn('customer_state',
                        relation_path='@invoice_id.@customer_id.@state.name',
                        name_long='Customer State')
        tbl.formulaColumn('line_total',
                          sql_formula='$quantity * $unit_price',
                          dtype='N',name_long='Line Total')
        tbl.formulaColumn('line_vat',
                          sql_formula='$line_total * $vat_rate',
                          dtype='N', name_long='Line VAT')
        tbl.formulaColumn('line_gross',
                          sql_formula='$line_total + $line_vat',
                          dtype='N', name_long='Line Gross')
        tbl.formulaColumn('size_category',
                          sql_formula="CASE WHEN $quantity IN (1,2,3) THEN 'Small' WHEN $quantity < 100 THEN 'Medium' ELSE 'Large' END",
                          dtype='A', name_long='Size Category')
        tbl.formulaColumn('product_note',
                          sql_formula="CASE WHEN @product_id.unit_price > 500 THEN 'Premium' ELSE 'Standard' END",
                          dtype='A', name_long='Product Note')
        tbl.formulaColumn('effective_price',
                          sql_formula='COALESCE($unit_price, @product_id.unit_price)',
                          dtype='money', name_long='Effective Price')
        tbl.formulaColumn('is_expensive',
                          sql_formula='$line_total > 1000',
                          dtype='B', name_long='Is Expensive')
        tbl.formulaColumn('needs_review',
                          sql_formula='$is_expensive OR ($quantity > 50 AND $unit_price < 1)',
                          dtype='B', name_long='Needs Review')
        tbl.formulaColumn('pricing_analysis',
                          sql_formula="""CASE WHEN $effective_price IS NULL THEN 'No price'
                                              WHEN $effective_price > @product_id.unit_price
                                                   THEN 'Above list'
                                              WHEN $effective_price < @product_id.unit_price
                                                   THEN 'Discounted'
                                              ELSE 'At list price' END""",
                          dtype='A', name_long='Pricing Analysis')
        tbl.aliasColumn('customer_region',
                        relation_path='@invoice_id.@customer_id.@state.@region_code.name',
                        name_long='Customer Region')

    def trigger_onInserted(self,record=None):
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])

    def trigger_onUpdated(self,record=None,old_record=None):
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])

    def trigger_onDeleted(self,record=None):
        if self.currentTrigger.parent:
            return
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])
