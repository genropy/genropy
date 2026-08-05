#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('staff_role', pkey='code', name_long='!!Staff Role',
                        name_plural='!!Staff Roles', caption_field='description',
                        lookup=True)
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':5', name_long='!!Code')
        tbl.column('description', name_long='!!Description')
