# -*- coding: utf-8 -*-

from gnr.core.gnrbag import Bag
from datetime import datetime,timedelta

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_base(self, pane):
        """You can customize initial view, headerToolbar, add custom buttons..."""
        kw = {'initialView':'dayGridMonth',
              'headerToolbar': {
                    'center': 'addEventButton'
              },
            'customButtons': {
                'addEventButton': {
                'text': 'add event...'}
        }}
        pane.fullCalendar(box_margin='40px',box_max_width='1100px',**kw)

    def test_2_quickgrid_store(self, pane):
        "By specifying a storepath, you can build your own datastore through a quickGrid, a bagGrid"
        bc = pane.borderContainer(height='900px')
        bc.contentPane(region='center').fullCalendar(initialView='dayGridMonth',     
        headerToolbar={
            'left': 'dayGridMonth,timeGridWeek,listWeek,timeGridDay',
            'center': 'title',
            'right': 'prevYear,prev,next,nextYear'
        },box_margin='40px',box_max_width='1100px',storepath='.events')

        bottom = bc.borderContainer(region='bottom',height='300px',splitter=True)
        grid = bottom.contentPane(region='center').quickGrid(value='^.events')
        grid.tools('delrow,addrow')
        grid.column('event_id',edit=True,name='Event',width='15em')
        grid.column('title',edit=True,name='title',width='15em')
        grid.column('start_date',edit=dict(tag='dateTextBox',period_to='.end_date'),dtype='D',name='start date',width='10em')
        grid.column('start_time',edit=dict(tag='timeTextBox'),name='time',width='10em',dtype='H')
        grid.column('end_date',edit=dict(tag='dateTextBox'),name='end date',width='10em',dtype='D')
        grid.column('end_time',edit=dict(tag='timeTextBox'),name='time',width='10em',dtype='H')
        grid.column('start',formula="combineDateAndTime(start_date,start_time)",name='Start',dtype='DHZ')
        grid.column('end',formula="combineDateAndTime(end_date,end_time)",name='End',dtype='DHZ')
  
    def test_3_event_store(self, pane):
        "Either if you build a bag manually or through a query, you can set your values into the store with data"
        events_bag = Bag()
        for i,evt in enumerate(['evt1', 'evt2', 'evt3']):
            start = datetime.now() + timedelta(days=i, hours=i)
            end = start + timedelta(hours=1)
            events_bag.setItem(evt, None)
            events_bag[evt]=Bag(dict(title=f'Event {i}', start=start.isoformat(), end=end.isoformat()))

        bc = pane.borderContainer(height='900px')
        bc.data('.events', events_bag)
        bc.contentPane(region='center').fullCalendar(initialView='dayGridMonth',     
        headerToolbar={
            'left': 'dayGridMonth,timeGridWeek,listWeek,timeGridDay',
            'center': 'title',
            'right': 'prevYear,prev,next,nextYear'
        },box_margin='40px',box_max_width='1100px',storepath='.events')