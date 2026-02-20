#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('customer', pkey='id', name_long='!!Customer', name_plural='!!Customers',caption_field='account_name')
        self.sysFields(tbl, draftField=True)
        tbl.column('account_name', name_long='!!Account name',name_short='Account name', validate_notnull=True, validate_len='2:40')
        tbl.column('street_address',name_long='!!Street Address', name_short='St.Address')
        tbl.column('suburb', name_long='!!Suburb', name_short='!!Suburb')
        tbl.column('state',size=':5',name_long='!!State',name_short='Pr.').relation('invc.state.code',relation_name='clients',mode='foreignkey',onDelete='raise')
        tbl.column('postcode',size=':5',name_long='!!Postcode',name_short='Postcode')
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

        tbl.formulaColumn('last_invoice_id',select=dict(table='invc.invoice',
                                                  columns='$id',
                                                  where='$customer_id=#THIS.id',
                                                  order_by='$date DESC',
                                                  limit=1),
                                      dtype='T',name_long='Last Invoice'
                                      ).relation('invoice.id',relation_name='last_invoice')
        tbl.formulaColumn('full_address',
                          sql_formula="$street_address || ', ' || $suburb",
                          dtype='T',name_long='Full Address')
        tbl.formulaColumn('has_invoices',
                          exists=dict(table='invc.invoice',
                                      where='$customer_id=#THIS.id'),
                          dtype='B',name_long='Has Invoices')
        tbl.formulaColumn('customer_rank',
                          sql_formula="CASE WHEN $n_invoices = 0 THEN 'Inactive' WHEN $n_invoices < 5 THEN 'Occasional' ELSE 'Regular' END",
                          dtype='A', name_long='Customer Rank')
        tbl.formulaColumn('display_name',
                          sql_formula="COALESCE($account_name, 'Unknown')",
                          dtype='T', name_long='Display Name')
        tbl.formulaColumn('postcode_padded',
                          sql_formula="LPAD($postcode, 5, '0')",
                          dtype='T', name_long='Postcode Padded')
        tbl.aliasColumn('state_name', relation_path='@state.name',
                        name_long='State Name')
        tbl.aliasColumn('payment_description',
                        relation_path='@payment_type_code.description',
                        name_long='Payment Description')
        tbl.aliasColumn('region_name',
                        relation_path='@state.@region_code.name',
                        name_long='Region Name')
        tbl.formulaColumn('account_code',
                          sql_formula="LPAD(CAST($id AS TEXT), 8, '0')",
                          dtype='T', name_long='Account Code')
        tbl.formulaColumn('is_active_valuable',
                          sql_formula='$has_invoices AND $n_invoices >= 3',
                          dtype='B', name_long='Active Valuable Customer')
        tbl.formulaColumn('contact_info',
                          sql_formula="CONCAT(COALESCE($email, 'no-email'), ' | ', COALESCE($phone, 'no-phone'))",
                          dtype='T', name_long='Contact Info')
        tbl.pyColumn('customer_score', dtype='N',
                     required_columns='$account_name,$email',
                     name_long='Customer Score')
        tbl.formulaColumn('invoice_numbers',
                          sql_formula="array_to_string(ARRAY(#inv_nums), ', ')",
                          select_inv_nums=dict(table='invc.invoice',
                                               columns='$inv_number',
                                               where='$customer_id=#THIS.id',
                                               order_by='$date DESC',
                                               limit=5),
                          dtype='T', name_long='Invoice Numbers')
        tbl.formulaColumn('avg_invoice_value',
                          sql_formula='$invoiced_total / NULLIF($n_invoices, 0)',
                          dtype='N', name_long='Avg Invoice Value')
        tbl.formulaColumn('has_activity',
                          sql_formula=("$has_invoices OR EXISTS(SELECT 1 FROM invc.invc_invoice_note AS n"
                                       " INNER JOIN invc.invc_invoice AS i ON n.invoice_id = i.id"
                                       " WHERE i.customer_id = #THIS.id)"),
                          dtype='B', name_long='Has Activity')

        tbl.subtable('residential', condition="$customer_type_code = 'RES'")
        tbl.subtable('commercial', condition="$customer_type_code = 'COM'")
        tbl.subtable('government', condition="$customer_type_code = 'GOV'")
        tbl.subtable('trade', condition="$customer_type_code = 'TRD'")

        # $__is_draft in formula - pattern erpy
        tbl.formulaColumn('is_confirmed',
                          sql_formula="$__is_draft IS NOT TRUE",
                          dtype='B', name_long='Is Confirmed')

    def pyColumn_customer_score(self, record, field):
        score = 10
        if record.get('email'):
            score += 5
        return score
