#!/usr/bin/env python
# encoding: utf-8
from html.parser import HTMLParser

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('content', pkey='id', name_long='!!Content', 
                        name_plural='!!Contents', caption_field='title')
        self.sysFields(tbl)

        tbl.column('title', name_long='!!Title',indexed=True, validate_notnull=True)
        tbl.column('headline', name_long='!!Headline')
        tbl.column('abstract', name_long='!!Abstract')
        tbl.column('text', name_long='!!Text')
        tbl.column('html', name_long='!!HTML')

        tbl.column('tplbag', dtype='X', name_long='!!Template')

    def trigger_onInserting(self, record):
        if record['html'] and not record['text']:
            record['text'] = self.getTextFromHtml(record['html'])
            
    def trigger_onInserted(self, record):
        self.db.table('docu.content_history').makeNewVersionFromContent(record)

    def trigger_onUpdating(self, record, old_record=None):
        if record['html'] and not record.get('text'):
            record['text'] = self.getTextFromHtml(record['html'])
            
    def trigger_onUpdated(self, record, old_record=None):
        if self.fieldsChanged('text', record, old_record):
            self.db.table('docu.content_history').makeNewVersionFromContent(record)

    def getTextFromHtml(self, html):
        if not html:
          return None

        text_parts = []
        
        class TextExtractor(HTMLParser):
            def handle_data(self, data):
                text_parts.append(data)

        parser = TextExtractor()
        parser.feed(html)

        return ' '.join(text_parts).strip()