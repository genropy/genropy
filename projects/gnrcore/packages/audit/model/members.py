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
        tbl.column('touched_ts', dtype='DHZ', name_long='!!Touched')

    def touch(self, sqltable=None, block_size=1000):
        """Give version 0 to every record of the audited tables that has none.

        Each block is committed on its own; a table is marked touched when
        no record without version is left.

        :param sqltable: only this audited table (``<sqlschema>.<sqlname>``)
        :param block_size: records updated per block
        """
        adaptSqlName = self.db.adapter.adaptSqlName
        where = '$sqltable = :sqltable' if sqltable else None
        members = self.query(columns='$sqltable,$pkey_column', where=where,
                             sqltable=sqltable).fetch()
        for member in members:
            target = '.'.join(adaptSqlName(name) for name in member['sqltable'].split('.'))
            pkey = adaptSqlName(member['pkey_column'])
            sql = (f'UPDATE {target} SET __version = 0 WHERE {pkey} IN '
                   f'(SELECT {pkey} FROM {target} WHERE __version IS NULL LIMIT :block_size)')
            while self.db.execute(sql, dict(block_size=block_size)).rowcount:
                self.db.commit()
            self.db.execute(f'UPDATE {self.model.sqlfullname} SET touched_ts = now() '
                            'WHERE sqltable = :sqltable', dict(sqltable=member['sqltable']))
            self.db.commit()
