# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from gnr.core.gnrdecorator import public_method, extract_kwargs
from gnr.core.gnrdict import dictExtract
import urllib
from ics import Calendar, Event
from datetime import datetime

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_makecalendar(self, pane):
        "Click button build ics object and read result"
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.name',lbl='Name', default='Genropy test')
        fb.simpleTextArea(value='^.description', lbl='Description', 
                          width='100%', height='40px', default="""This is a test event.\nPlease join us to test the new Genropy feature.""")
        fb.dateTimeTextBox(value='^.start_ts',lbl='Start', default=datetime.now())
        fb.dateTimeTextBox(value='^.end_ts',lbl='End', default=datetime.now()+timedelta(hours=1))
        fb.textbox(value='^.url',lbl='Url', default='http://www.genropy.org')
        fb.button('!!Make calendar').dataRpc('.ics_result', self.getIcs, event_name='=.name', event_description='=.description', 
                                                    event_begin='=.start_ts', event_end='=.end_ts', event_url='=.url')
        fb.div('^.ics_result', lbl='Ics result')

    def test_2_dlcalendar(self, pane):
        "Click button build ics object and click on a button to get result"
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.name',lbl='Name', default='Genropy test')
        fb.simpleTextArea(value='^.description', lbl='Description', 
                          width='100%', height='40px', default="""This is a test event.\nPlease join us to test the new Genropy feature.""")
        fb.dateTimeTextBox(value='^.start_ts',lbl='Start', default=datetime.now())
        fb.dateTimeTextBox(value='^.end_ts',lbl='End', default=datetime.now()+timedelta(hours=1))
        fb.textbox(value='^.url',lbl='Url', default='http://www.genropy.org')
        fb.a("!!Download ICS", href='^.webtool_url', _class='iconbox download')
        fb.dataFormula('.webtool_url', """genro.callWebTool('ics', 
                       {event_name:event_name,event_description:event_description,event_begin:event_begin,event_end:event_end,event_url:event_url});""", 
                            event_name='^.name', event_description='^.description', 
                            event_begin='^.start_ts', event_end='^.end_ts', event_url='^.url', _onStart=True)

        #fb.icsButton(event_name='^.name', event_description='^.description', 
        #                    event_begin='^.start_ts', event_end='^.end_ts', event_url='^.url') #webstruct component?

    @public_method
    def getIcs(self, mode='serialize', events=None, **kwargs):
        if not events:
            events = [dictExtract(kwargs, 'event_')]
        calendar = Calendar()
        for event in events:
            calendar.events.add(Event(**event))
        if mode=='serialize':
            return calendar.serialize()
        print(calendar)
