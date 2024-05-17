#!/usr/bin/env python
# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('content', pkey='id', name_long='!!Content', 
                        name_plural='!!Contents', caption_field='title')
        self.sysFields(tbl)

        tbl.column('title', name_long='!!Title',indexed=True, validate_notnull=True)
        tbl.column('headline', name_long='!!Headline')
        tbl.column('abstract', name_long='!!Abstract')
        tbl.column('text', name_long='!!Text')
        tbl.column('tplbag', dtype='X', name_long='!!Template')

    def trigger_onInserted(self, record):
        self.db.table('docu.content_history').makeNewVersionFromContent(record)

    def trigger_onUpdated(self, record, old_record=None):
        if self.fieldsChanged('text', record, old_record):
            self.db.table('docu.content_history').makeNewVersionFromContent(record)

    