# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('faq_documentation', pkey='id', name_long='!!FAQ Documentation', 
                      name_plural='!!FAQs documentation')
        self.sysFields(tbl)
        
        tbl.column('faq_id',size='22', group='_', name_long='!!FAQ'
                    ).relation('faq.id', relation_name='faq_documentations', mode='foreignkey', onDelete='raise')
        tbl.column('documentation_id',size='22', group='_', name_long='!![en]Documentation'
                    ).relation('documentation.id', relation_name='documentation_faqs', mode='foreignkey', onDelete='raise')