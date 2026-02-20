#!/usr/bin/env python
# encoding: utf-8
from decimal import Decimal

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('invoice', pkey='id', name_long='!!Invoice', name_plural='!!Invoice', caption_field='inv_number')
        self.sysFields(tbl)
        tbl.column('inv_number' ,size='10',name_long='!!Invoice number', name_short='Inv N',unique=True)
        tbl.column('customer_id',size='22' ,group='_',name_long='!!Customer'
                                        ).relation('customer.id',
                                                    relation_name='invoices',
                                                    mode='foreignkey',
                                                    onDelete='raise')
        tbl.column('date',dtype='D',name_long='!!Date',validate_notnull=True)
        tbl.column('total',dtype='money',name_long='!!Total')
        tbl.column('vat_total',dtype='money',name_long='!!VAT total')
        tbl.column('gross_total',dtype='money',name_long='!!Gross total')
        tbl.formulaColumn('row_count',
                          select=dict(table='invc.invoice_row',
                                      columns='COUNT(*)',
                                      where='$invoice_id=#THIS.id'),
                          dtype='L',name_long='Row Count')
        tbl.formulaColumn('first_product_id',
                          select=dict(table='invc.invoice_row',
                                      columns='$product_id',
                                      where='$invoice_id=#THIS.id',
                                      order_by='$_row_count',
                                      limit=1),
                          dtype='T',name_long='First Product'
                          ).relation('product.id',relation_name='first_in_invoice',mode='foreignkey')
        tbl.aliasColumn('customer_name',
                        relation_path='@customer_id.account_name',
                        name_long='Customer Name')
        tbl.formulaColumn('anno',
                          sql_formula="EXTRACT(YEAR FROM $date)",
                          dtype='T', name_long='Anno')
        tbl.formulaColumn('periodo',
                          sql_formula="TO_CHAR($date,'YYYY-MM')",
                          dtype='A', name_long='Periodo')
        tbl.formulaColumn('value_category',
                          sql_formula="CASE WHEN $total > 1000 THEN 'High' WHEN $total > 100 THEN 'Medium' ELSE 'Low' END",
                          dtype='A', name_long='Value Category')
        tbl.formulaColumn('display_total',
                          sql_formula="COALESCE($gross_total, $total, 0)",
                          dtype='N', name_long='Display Total')
        tbl.joinColumn('discount_tier_id', name_long='Discount Tier').relation(
            'discount_tier.id',
            cnd="""@discount_tier_id.customer_type_code=@customer_id.customer_type_code
                   AND @discount_tier_id.min_amount <= $total
                   AND @discount_tier_id.max_amount > $total""",
            relation_name='invoices_in_tier', one_one=True)
        tbl.formulaColumn('all_notes',
                          select=dict(table='invc.invoice_note',
                                      columns="STRING_AGG($note_text, ' | ' ORDER BY $priority)",
                                      where='$invoice_id=#THIS.id'),
                          dtype='T', name_long='All Notes')
        tbl.formulaColumn('priority_note',
                          sql_formula="COALESCE(#top_note, 'No notes')",
                          select_top_note=dict(table='invc.invoice_note',
                                               columns='$note_text',
                                               where='$invoice_id=#THIS.id',
                                               order_by='$priority',
                                               limit=1),
                          dtype='T', name_long='Priority Note')
        tbl.formulaColumn('invoice_status',
                          sql_formula="""CASE WHEN $total IS NULL THEN 'Draft'
                                              WHEN $total = 0 THEN 'Empty'
                                              ELSE CASE WHEN $gross_total > 5000 THEN 'Large'
                                                        WHEN $gross_total > 1000 THEN 'Medium'
                                                        ELSE 'Small' END
                                         END""",
                          dtype='A', name_long='Invoice Status')
        tbl.formulaColumn('status_label',
                          sql_formula="""CASE WHEN $total > 1000 THEN :high_label
                                              WHEN $total > 100 THEN :mid_label
                                              ELSE :low_label END""",
                          var_high_label='Premium Invoice',
                          var_mid_label='Standard Invoice',
                          var_low_label='Basic Invoice',
                          dtype='A', name_long='Status Label')

    def calculateTotals(self,invoice_id):
        with self.recordToUpdate(invoice_id) as record:
            total,vat_total = self.db.table('invc.invoice_row').readColumns(columns="""SUM($tot_price) AS total,
                                                                                        SUM($vat) AS vat_total""",
                                                                                 where='$invoice_id=:invoice_id',
                                                                                 invoice_id=invoice_id)
            
            total=Decimal(total)
            record['total'] = total
            record['vat_total'] = vat_total
            record['gross_total'] = record['total'] + record['vat_total']

    def defaultValues(self):
        return dict(date = self.db.workdate)

    def counter_inv_number(self,record=None):
        return dict(format='$K$YY/$NNNNNN',code='A',period='YY',date_field='date',showOnLoad=True,recycle=True)