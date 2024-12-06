# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('external_token_use', pkey='id', name_long='!!External token usage',
                        name_plural='!!External token usages')
        tbl.column('id', size='22', name_long='!!id')
        tbl.column('external_token_id', size='22', name_long='!!External token id').relation('external_token.id',relation_name='usages',
                                                                                             mode='foreignkey',
                                                                                             onDelete='cascade')
        tbl.column('datetime', 'DH', name_long='!!Date and Time')
        tbl.column('host', name_long='!!Host')
