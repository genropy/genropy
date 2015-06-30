#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('widget', pkey='id', name_long='!!Widget', name_plural='!!Widgets',caption_field='name')
        self.sysFields(tbl,hierarchical='name',df=True)
        tbl.column('name',name_long='!!Name')
        tbl.column('summary',name_long='!!Summary')
        tbl.column('server',dtype='B',name_long='!!Server')
        tbl.column('docrows',dtype='X',name_long='!!Parameters doc',_sendback=True)