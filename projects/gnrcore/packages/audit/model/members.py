# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('members', pkey='sqltable', name_long='!!Audited table',
                        name_plural='!!Audited tables')
        tbl.column('sqltable', name_long='!!Sql table')
        tbl.column('tbl', name_long='!!Table')
        tbl.column('pkey_column', name_long='!!Pkey column')
        tbl.column('excluded_cols', name_long='!!Excluded columns')
        tbl.column('activated_ts', dtype='DHZ', name_long='!!Activated')
