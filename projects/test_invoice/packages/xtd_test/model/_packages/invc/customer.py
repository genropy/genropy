#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('customer')
        tbl.column('xtd_reference', name_long='XTD reference')
