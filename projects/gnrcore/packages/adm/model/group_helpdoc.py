# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('group_helpdoc', pkey='id', 
                      name_long='!![en]Help document for group', name_plural='!![en]Help documents for group',caption_field='')
        self.sysFields(tbl,counter='group_code')
        tbl.column('group_code',size=':15', 
                   group='_', name_long='Group'
                    ).relation('group.code', 
                               relation_name='helpdocs', 
                               mode='foreignkey', onDelete='raise')
        tbl.column('helpdoc_id',size='22', group='_', name_long='Help document'
                    ).relation('helpdoc.id', relation_name='connected_groups', 
                               mode='foreignkey', onDelete='cascade')
        tbl.aliasColumn('url','@helpdoc_id.url',name_long='Url',static=True)
        