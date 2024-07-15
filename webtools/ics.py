#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseWebtool
from ics import Calendar, Event
from gnr.core.gnrdict import dictExtract
from io import BytesIO

class Ics(BaseWebtool):
    content_type = 'text/calendar'
    
    def __call__(self, download_name='calendar', events=None, **kwargs):   
        if not events:
            events = [dictExtract(kwargs, 'event_')]
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