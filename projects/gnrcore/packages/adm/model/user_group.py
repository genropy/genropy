# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('user_group', pkey='id', name_long='!![en]User groups', 
                      name_plural='!![en]User groups')
        self.sysFields(tbl)
        tbl.column('user_id',size='22', group='_', name_long='User'
                    ).relation('user.id', relation_name='extra_groups', 
                               mode='foreignkey', onDelete='cascade')
        tbl.column('group_code',size=':15', group='_', name_long='Group'
                    ).relation('group.code', relation_name='user_groups', 
                               mode='foreignkey', onDelete='cascade')