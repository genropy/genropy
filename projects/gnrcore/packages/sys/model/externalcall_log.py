# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('externalcall_log', pkey='id', 
                    name_long='External call log',
                     name_plural='External call log',caption_field='methodname')
        self.sysFields(tbl)
        tbl.column('endpoint', name_long='Endpoint')
        tbl.column('methodname', name_long='Method')
        tbl.column('parameters', dtype='X', name_long='Parameters')
        tbl.column('error', name_long='Error')
        tbl.column('result', dtype='X', name_long='Result')