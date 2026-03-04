#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('region', pkey='code', name_long='!!Region',
                        name_plural='!!Regions')
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':5', name_long='!!Code')
        tbl.column('name', size=':50', name_long='!!Name')
