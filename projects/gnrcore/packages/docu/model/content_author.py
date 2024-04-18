# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('content_author', pkey='id', 
                      name_long='!!Content author', name_plural='!!Content authors')
        self.sysFields(tbl)

        tbl.column('content_id',size='22', group='_', name_long='!!Content'
                    ).relation('content.id', relation_name='author_contents', 
                               mode='foreignkey', onDelete='cascade')
        tbl.column('author_id',size='22', group='_', name_long='!!Author'
                    ).relation('author.id', relation_name='content_authors', 
                               mode='foreignkey', onDelete='setnull')
        