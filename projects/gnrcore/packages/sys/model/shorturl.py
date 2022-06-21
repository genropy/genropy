# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('shorturl', pkey='codekey',pkey_values='$domain,$key', name_long='Shorturl', name_plural='Shorturl',caption_field='shorturl')
        self.sysFields(tbl)
        tbl.column('codekey', size=':100', name_long='Codekey')
        tbl.column('service_identifier',size=':60', group='_', name_long='Service'
                    ).relation('service.service_identifier', relation_name='urls', 
                                    mode='foreignkey', onDelete='raise')
        tbl.column('longurl', name_long='Long url')
        tbl.column('shorturl', name_long='Short url', name_short='Short')
        tbl.column('domain', name_long='Domain')
        tbl.column('key', name_long='Key')
        tbl.column('expiration','D', name_long='Expiration')
        tbl.column('traking', dtype='X', name_long='Traking')