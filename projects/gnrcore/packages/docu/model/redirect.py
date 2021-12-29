# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('redirect', pkey='id', name_long='Redirect', name_plural='Redirects',caption_field='page_name')
        self.sysFields(tbl)
        
        tbl.column('page_id',size='22',name_long='!![en]Moved Page').relation('documentation.id',
                                relation_name='redirects', mode='foreignkey', onDelete='raise')
        tbl.column('old_url', name_long='!![en]Old url')
        tbl.column('new_url', name_long='!![en]New url')
        tbl.column('old_handbook_id',size='22', group='_', name_long='!![en]Old Handbook'
                    ).relation('docu.handbook.id', relation_name='old_redirects', mode='foreignkey', onDelete='raise')
        tbl.column('new_handbook_id',size='22', group='_', name_long='!![en]New Handbook'
                    ).relation('docu.handbook.id', relation_name='new_redirects', mode='foreignkey', onDelete='raise')
        tbl.column('is_active', dtype='B', name_long='Is active', name_short='Act.')

        tbl.aliasColumn('page_name', '@page_id.name', name_long='!![en]Page name')
        tbl.aliasColumn('old_handbook_path', '@old_handbook_id.sphinx_path', name_long='!![en]Handbook path')
        tbl.aliasColumn('old_handbook_url', '@old_handbook_id.handbook_url', name_long='!![en]Handbook url')