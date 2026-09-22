#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('image', pkey='id', name_long='!!Image',
                        name_plural='!!Images', caption_field='name')
        self.sysFields(tbl)
        tbl.column('name', name_long='!!Name')
