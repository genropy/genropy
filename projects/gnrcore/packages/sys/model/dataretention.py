# encoding: utf-8

class Table(object):

    def config_db(self, pkg):
        tbl =  pkg.table('dataretention', rowcaption='$table_fullname',
                         caption_field='task_fullname', pkey='id',
                         name_long='!!Data Retention Policy',name_plural='!!Data Retention Policies')
        self.sysFields(tbl)
        tbl.column('table_fullname',name_long='!!Table', unique=True)
        tbl.column('filter_column',name_long='!!Filter Column')
        tbl.column('retention_period', dtype='L', name_long='!!Retention (days)')

    
