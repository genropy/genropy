# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('queue', pkey='queue_id', name_long='!!Audit queue',
                        name_plural='!!Audit queue')
        tbl.column('queue_id', dtype='serial', name_long='!!Queue id')
        tbl.column('ts', dtype='DHZ', name_long='!!Timestamp')
        tbl.column('txid', dtype='L', name_long='!!Transaction id')
        tbl.column('tbl', name_long='!!Table')
        tbl.column('record_pkey', name_long='!!Record pkey')
        tbl.column('op', size='1', name_long='!!Operation')
        tbl.column('version', dtype='L', name_long='!!Version')
        tbl.column('username', name_long='!!User')
        tbl.column('caller', name_long='!!Caller')
        tbl.column('sqlcommand', name_long='!!Sql command')
        tbl.column('data', dtype='jsonb', name_long='!!Data')
        tbl.column('old_full', dtype='jsonb', name_long='!!Record before the first change')
