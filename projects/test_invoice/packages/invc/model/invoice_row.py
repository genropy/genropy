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


    def trigger_onInserted(self,record=None):
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])

    def trigger_onUpdated(self,record=None,old_record=None):
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])

    def trigger_onDeleted(self,record=None):
        if self.currentTrigger.parent:
            return
        self.db.table('invc.invoice').calculateTotals(record['invoice_id'])
