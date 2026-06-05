class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('myticket', pkey='id', name_long='Ticket',
                        name_plural='Tickets', caption_field='subject',
                        rowcaption='subject')
        self.sysFields(tbl)
        tbl.column('subject', name_long='Subject')
        tbl.column('description', name_long='Description')
        tbl.column('ticket_type', name_long='Ticket Type')
        tbl.column('ticket_date', dtype='D', name_long='Date')
        tbl.column('status', name_long='Status')
        tbl.column('extra_data', dtype='X', name_long='Extra Data')
