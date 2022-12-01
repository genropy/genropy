# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
import datetime

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_event_store(self, pane):
        "Full Calendar view with possibility to add events through a quickGrid"
        #kw = {'initialView':'dayGridMonth',
        #      'headerToolbar': {
        #            'center': 'addEventButton'
        #      },
        #    'customButtons': {
        #        'addEventButton': {
        #        'text': 'add event...'}
        #}} 
        #Alternative syntax. It is possible to customize addEventButton to add an event instead of quickGrid used below        
        bc = pane.borderContainer(height='900px')
        bc.contentPane(region='center').fullCalendar(initialView='dayGridMonth',     
        headerToolbar={
            'left': 'dayGridMonth,timeGridWeek,listWeek,timeGridDay',
            'center': 'title',
            'right': 'prevYear,prev,next,nextYear'
        }, box_margin='40px',box_max_width='1100px', storepath='.events', ) #**kw

        top = bc.borderContainer(region='top',height='100px',splitter=True)
        grid = top.contentPane(region='center').quickGrid(value='^.events')
        grid.tools('delrow,addrow')
        grid.column('event_id', edit=True,name='Event',width='10em')
        grid.column('title', edit=True,name='title',width='auto')
        grid.column('start', edit=dict(tag='dateTimeTextBox'), name='Start date', width='12em', dtype='DH')
        grid.column('end', edit=dict(tag='dateTimeTextBox'), name='End', width='12em', dtype='DH')

        event_bag = Bag()
        event_bag_row = Bag(event_id='Test', title='Demo event', start=datetime.datetime.now(), 
                                        end=datetime.datetime.now()+datetime.timedelta(hours=1))
        event_bag.setItem('demo', event_bag_row)                    
        top.data('.events', event_bag)