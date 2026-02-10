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
        tbl.column('customer_type_code', size=':5',name_long='!!Customer type code',name_short='!!Cust type').relation('customer_type.code',relation_name='customers',mode='foreignkey',onDelete='raise')
        tbl.column('payment_type_code',size=':5',name_long='!!Payment type code',name_short='!!Pay type').relation('payment_type.code',relation_name='customers',mode='foreignkey',onDelete='raise')
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
  