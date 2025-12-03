# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('task')
        tbl.column('user_id').relation('adm.user.id', mode='foreignkey', onDelete='raise')
