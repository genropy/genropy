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
        
        tbl.pyColumn('doc_full_external_url', name_long='!![en]Full Url', required_columns='$documentation_id')
    
    
    def pyColumn_doc_full_external_url(self, record, **kwargs):
        """Returns the full url of the documentation page, based on
           the handbook_url of the closest ancestor handbook and on
           the hierarchical_name of the current record

        """
        doc_record = self.db.table('docu.documentation').record(record['documentation_id'],
                                                                mode='bag')
        return doc_record and self.calculateExternalUrl(doc_record) or None
