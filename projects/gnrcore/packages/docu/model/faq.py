# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('faq', pkey='id', name_long='!!FAQ', name_plural='!!FAQs',caption_field='question')
        self.sysFields(tbl, counter='faq_area_id')
        
        tbl.column('topics',name_long='!!Topics')
        tbl.column('content_id',size='22', group='_', name_long='!![en]Content'
                    ).relation('docu.content.id', one_one='*', mode='foreignkey', onDelete='raise')
        tbl.column('notes', name_long='!!Notes')
        tbl.column('faq_area_id',size='22', group='_', name_long='!!FAQ Area'
                    ).relation('faq_area.id', relation_name='faqs', mode='foreignkey', onDelete='raise')
        
        tbl.aliasColumn('question', '@content_id.title', name_long='!!Question')