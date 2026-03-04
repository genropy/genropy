#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from io import BytesIO
from gnr.web.gnrbaseclasses import BaseWebtool
from ics import Calendar, Event

class Ics(BaseWebtool):
    content_type = 'text/calendar'
    
    def __call__(self, table=None,pkey=None,record_pointer=None, **kwargs): 
        if not table:
            table,pkey = record_pointer.rsplit('.',1)
        events,download_name = self.site.db.table(table).getIcsEvents(pkey) 
        if not isinstance(events,list):
            events = [events]
        calendar = self.getIcs(events)
        buffer = BytesIO()
        buffer.write(calendar.encode('utf-8'))
        buffer.seek(0)
        self.download_name = f"{download_name}.ics"
        return buffer.read()

    def getIcs(self, events=None):
        calendar = Calendar()
        for event in events:
            calendar.events.add(Event(**event))
        return calendar.serialize()
