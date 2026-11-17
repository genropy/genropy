#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('doc_line', pkey='id', name_long='!!Document line',
                        name_plural='!!Document lines')
        self.sysFields(tbl, relidx='doc_code')
        tbl.column('doc_code', size=':10', name_long='!!Document').relation(
            'doc.code', relation_name='lines', mode='foreignkey', onDelete='cascade')
        tbl.column('description', name_long='!!Description')
