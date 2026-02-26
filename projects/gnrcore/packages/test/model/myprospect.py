class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('myprospect', pkey='id', name_long='Prospect',
                        name_plural='Prospects', caption_field='company_name',
                        rowcaption='$company_name - $contact_name')
        self.sysFields(tbl)
        tbl.column('company_name', name_long='Company Name')
        tbl.column('contact_name', name_long='Contact Name')
        tbl.column('contact_email', name_long='Email')
        tbl.column('contact_phone', name_long='Phone')
        tbl.column('source', name_long='Source')
        tbl.column('status', name_long='Status')
        tbl.column('extra_data', dtype='X', name_long='Extra Data')
