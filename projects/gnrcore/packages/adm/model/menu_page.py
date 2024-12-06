#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('menu_page', pkey='id', name_long='!!Menu Page',name_plural='!!Menu Pages', rowcaption='$label',caption_field='label')
        self.sysFields(tbl)
        tbl.column('label', name_long='!!Label')
        tbl.column('filepath', name_long='!!Filepath')
        tbl.column('tbl', name_long='!!Table')
        tbl.column('pkg', name_long='!!Package')
        tbl.column('metadata', name_long='!!Metadata')

