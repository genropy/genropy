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