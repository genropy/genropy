# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('message_index', pkey='id', name_long='Message index')
        self.sysFields(tbl)
        tbl.column('dbstore')        