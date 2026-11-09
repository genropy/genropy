#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('audited_item', pkey='id', name_long='!!Audited item',
                        name_plural='!!Audited items', caption_field='code', audit='external')
        self.sysFields(tbl, draftField=True, user_ins=True, user_upd=True)
        tbl.column('code', size=':10', name_long='!!Code')
        tbl.column('description', name_long='!!Description')
        tbl.column('amount', dtype='N', name_long='!!Amount')
        tbl.column('last_invoice_date', dtype='D', name_long='!!Last invoice date', audit=False)
        tbl.column('details', dtype='X', name_long='!!Details')
