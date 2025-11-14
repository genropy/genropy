# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('documentation_content', pkey='id', name_long='!![en]Documentation content', 
                                name_plural='!![en]Documentation content', caption_field='language')
        self.sysFields(tbl)
        
        tbl.column('content_id',size='22', group='_', name_long='!![en]Content'
                   ).relation('content.id', one_one='*', mode='foreignkey', onDelete='cascade')
        tbl.column('documentation_id',size='22', group='_', name_long='!![en]Documentation'
                   ).relation('documentation.id', relation_name='contents', mode='foreignkey', onDelete='cascade')
        tbl.column('language_code',size=':2', group='_', name_long='!![en]Language'
                    ).relation('adm.language.code', mode='foreignkey', onDelete='raise')
        
        tbl.aliasColumn('language', '@language_code.name', name_long='!![en]Language')