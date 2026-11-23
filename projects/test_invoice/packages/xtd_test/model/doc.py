#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('doc', pkey='code', name_long='!!Document',
                        name_plural='!!Documents', caption_field='code')
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':10', name_long='!!Code')
        tbl.column('description', name_long='!!Description')
