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
        tbl.column('invoice_time',dtype='H',name_long='!!Invoice Time')
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
                          ).relation('product.id',relation_name='first_in_invoice')
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
        tbl.formulaColumn('days_since_invoice',
                          sql_formula="date_part('day', now() - $date)",
                          dtype='L', name_long='Days Since Invoice')
        tbl.formulaColumn('number_series',
                          sql_formula="""CASE WHEN $inv_number LIKE :pat_a THEN 'Series A'
                                              WHEN $inv_number LIKE :pat_b THEN 'Series B'
                                              ELSE 'Other' END""",
                          var_pat_a='A%%',
                          var_pat_b='B%%',
                          dtype='A', name_long='Number Series')
        tbl.formulaColumn('week_start',
                          sql_formula=("$date - MOD(CAST(EXTRACT(DOW FROM $date) AS integer) + 6, 7)"
                                       " * INTERVAL '1 day'"),
                          dtype='D', name_long='Week Start')
        tbl.formulaColumn('priced_rows_pct',
                          select=dict(table='invc.invoice_row',
                                      columns=("COUNT(*) FILTER (WHERE $unit_price IS NOT NULL)"
                                               " * 100.0 / NULLIF(COUNT(*), 0)"),
                                      where='$invoice_id=#THIS.id'),
                          dtype='N', name_long='Priced Rows Pct')
        tbl.formulaColumn('invoice_datetime',
                          sql_formula='$date + $invoice_time',
                          dtype='DH', name_long='Invoice Datetime')
        tbl.formulaColumn('invoice_month',
                          sql_formula="date_trunc('month', $date)",
                          dtype='D', name_long='Invoice Month')
        tbl.formulaColumn('smart_row_count',
                          sql_formula="CASE WHEN $total > 1000 THEN #high_rows ELSE #all_rows END",
                          select_high_rows=dict(table='invc.invoice_row',
                                                columns='COUNT(*)',
                                                where='$invoice_id=#THIS.id AND $unit_price > 100'),
                          select_all_rows=dict(table='invc.invoice_row',
                                               columns='COUNT(*)',
                                               where='$invoice_id=#THIS.id'),
                          dtype='L', name_long='Smart Row Count')
        # exists=dict() - pattern erpy (has_expensive_rows)
        tbl.formulaColumn('has_expensive_rows',
                          exists=dict(table='invc.invoice_row',
                                      where='$invoice_id=#THIS.id AND $unit_price > 100'),
                          dtype='B', name_long='Has Expensive Rows')
        # select_* con group_by + having - pattern erpy
        tbl.formulaColumn('duplicate_products',
                          sql_formula="COALESCE(#dup_prods, 0)",
                          select_dup_prods=dict(table='invc.invoice_row',
                                                columns='COUNT(*)',
                                                where='$invoice_id=#THIS.id',
                                                group_by='$product_id',
                                                having='COUNT(*) > 1'),
                          dtype='L', name_long='Duplicate Products')
        # INTERVAL aritmetica - pattern erpy
        tbl.formulaColumn('due_date',
                          sql_formula="$date + INTERVAL '30 days'",
                          dtype='D', name_long='Due Date')
        # CAST($__ins_ts AS DATE) = $date - pattern erpy date() cast
        tbl.formulaColumn('created_same_day',
                          sql_formula="CAST($__ins_ts AS DATE) = $date",
                          dtype='B', name_long='Created Same Day')
        # :env_workdate in formula - pattern erpy
        tbl.formulaColumn('is_recent',
                          sql_formula="$date >= :env_workdate - INTERVAL '90 days'",
                          dtype='B', name_long='Is Recent')
        tbl.subQueryColumn('rows_json',
                           query=dict(table='invc.invoice_row',
                                      columns='$product_id,$quantity,$unit_price',
                                      where='$invoice_id=#THIS.id'),
                           mode='json')
        tbl.subQueryColumn('notes_xml',
                           query=dict(table='invc.invoice_note',
                                      columns='$note_type,$note_text',
                                      where='$invoice_id=#THIS.id'),
                           mode='xml')
        tbl.subQueryColumn('max_row_price',
                           query=dict(table='invc.invoice_row',
                                      columns='MAX($unit_price)',
                                      where='$invoice_id=#THIS.id'),
                           dtype='N', name_long='Max Row Price')

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