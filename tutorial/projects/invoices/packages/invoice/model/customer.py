#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('customer',pkey='id',rowcaption='$code,$name:%s - %s',
                         name_long='!!Customer',name_plural='!!Customers')
        self.sysFields(tbl)
        tbl.column('code',size=':6',name_long='!!Code',unique=True,indexed=True)
        tbl.column('name',size=':24',name_long='!!Name',unique=True,indexed=True)
        tbl.column('address',name_long='!!Address')
        tbl.column('zip',size='5',name_long='!!Zip')
        tbl.column('city',size=':24',name_long='!!City')
        tbl.column('country',size='2',name_long='!!Country').relation('glbl.nazione.code',mode='foreignkey')
        
    def trigger_onUpdating(self, record, old_record):
        if not record.get('code'):
            record['code'] = self.getclientcode()
            
    def trigger_onInserting(self, record):
        record['code'] = self.getclientcode()
        
    def getclientcode(self):
        return self.pkg.getCounter(name='!!Customer Code',codekey='$K',output='$NNNNNN',code='customer')
            