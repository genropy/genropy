#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('content_history', pkey='id', name_long='!!Content history', 
                        name_plural='!!Contents history', caption_field='version',
                        order_by='$__ins_ts DESC')
        self.sysFields(tbl)

        tbl.column('content_id',size='22', group='_', name_long='!!Content'
                    ).relation('content.id', relation_name='versions', mode='foreignkey', onDelete='cascade')
        tbl.column('version', dtype='I', name_long='!!Version', name_short='!!Vers.',
                    indexed=True, validate_notnull=True)
        tbl.column('text', name_long='!!Text')
        tbl.column('html', name_long='!!Html')

    
    def makeNewVersionFromContent(self, content_record):
        last_content_version = self.readColumns(where='$content_id=:c_id', 
                        c_id=content_record['id'], columns='$version', order_by='$__ins_ts DESC', limit=1) or 0
        new_version = self.newrecord(text=content_record['text'],html=content_record['html'], version=last_content_version+1, 
                                     content_id=content_record['id'])
        self.insert(new_version)