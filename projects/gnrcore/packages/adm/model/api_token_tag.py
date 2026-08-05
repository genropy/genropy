# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('api_token_tag', pkey='id',
                        name_long='!!API Token Tag',
                        name_plural='!!API Token Tags')
        self.sysFields(tbl)
        tbl.column('api_token_id', size='22', group='_',
                   name_long='!!API Token').relation('api_token.id',
                   relation_name='tags', mode='foreignkey', onDelete='cascade')
        tbl.column('tag_id', size='22', group='_',
                   name_long='!!Tag').relation('htag.id',
                   relation_name='api_tokens', mode='foreignkey', onDelete='cascade')
        tbl.aliasColumn('tag_code', '@tag_id.authorization_tag')
        tbl.aliasColumn('tag_description', '@tag_id.description')
