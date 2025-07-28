# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('content_topic', pkey='id', 
                      name_long='!!Content topic', name_plural='!!Content topics')
        self.sysFields(tbl)

        tbl.column('content_id',size='22', group='_', name_long='!!Content'
                    ).relation('content.id', relation_name='topic_contents', 
                               mode='foreignkey', onDelete='cascade')
        tbl.column('topic',size=':50', group='_', name_long='!!Topic'
                    ).relation('topic.topic', relation_name='content_topics', 
                               mode='foreignkey', onDelete='setnull')
        