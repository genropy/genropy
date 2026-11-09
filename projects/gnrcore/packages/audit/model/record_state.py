# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('record_state', pkey='state_id', name_long='!!Audited record state',
                        name_plural='!!Audited record states')
        tbl.column('state_id', dtype='serial', name_long='!!State id')
        tbl.column('tbl', name_long='!!Table')
        tbl.column('record_pkey', name_long='!!Record pkey')
        tbl.column('version', dtype='L', name_long='!!Version')
        tbl.column('data', dtype='jsonb', name_long='!!Data')
        tbl.index('tbl,record_pkey', unique=True)
