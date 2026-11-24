#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('event_id', width='6em')
        r.fieldcell('ts', width='10em')
        r.fieldcell('tbl', width='12em')
        r.fieldcell('record_pkey', width='12em')
        r.fieldcell('op', width='3em')
        r.fieldcell('version', width='4em')
        r.fieldcell('username', width='8em')

    def th_order(self):
        return 'event_id:d'

    def th_query(self):
        return dict(column='tbl', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('tbl')
        fb.field('record_pkey')
        fb.field('op')
        fb.field('version')
        fb.field('expected_version')
        fb.field('ts')
        fb.field('username')
        fb.field('txid')
        fb.field('queue_id')
        fb.field('caller', colspan=2, width='100%')
        fb.field('sqlcommand', colspan=2, width='100%')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px', readOnly=True)


class ViewTableHistory(BaseComponent):
    """The events of one table, in the table history palette."""

    def th_hiddencolumns(self):
        return '$tbl,$record_pkey,$data'

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('version', name='V', width='3em')
        r.fieldcell('ts', name='!![en]Date', width='9em', filterField=True)
        r.fieldcell('op', name='!![en]Event', width='4em', values='I:INS,U:UPD,D:DEL,A:---', filterField=True)
        r.cell('caption', name='!![en]Record', width='12em', calculated=True, filterField=True)
        r.fieldcell('username', name='!![en]User', width='8em', filterField=True)
        r.cell('changes', name='!![en]Changes', width='12em', calculated=True,
               filterField=True, filterField_aggr=', ')

    def th_order(self):
        return 'event_id:d'

    def th_top_custom(self, top):
        top.slotToolbar('5,sections@event,10,sections@period,*', childname='upper', _position='<bar')

    def th_sections_event(self):
        return [dict(code='all', caption='!![en]All'),
                dict(code='ins', caption='INS', condition="$op='I'"),
                dict(code='upd', caption='UPD', condition="$op='U'"),
                dict(code='del', caption='DEL', condition="$op='D'"),
                dict(code='ini', caption='---', condition="$op='A'")]

    def th_sections_period(self):
        today = datetime.date.today()
        return [dict(code='d30', caption='!![en]30 days', condition='$ts >= :since',
                     condition_since=today - datetime.timedelta(days=30)),
                dict(code='d90', caption='!![en]90 days', condition='$ts >= :since',
                     condition_since=today - datetime.timedelta(days=90)),
                dict(code='year', caption='!![en]Year', condition='$ts >= :since',
                     condition_since=today - datetime.timedelta(days=365)),
                dict(code='all', caption='!![en]All')]

    def th_queryBySample(self):
        return dict(fields=[dict(field='username', lbl='!![en]User', width='10em'),
                            dict(field='record_pkey', lbl='!![en]Record pkey', width='12em')],
                    cols=2, isDefault=True)

    @public_method
    def th_applymethod(self, selection, **kwargs):
        if not selection.data:
            return
        tbl = selection.data[0]['tbl']
        eventtbl = self.db.table('audit.event')
        captions = eventtbl.recordCaptions(tbl, set(row['record_pkey'] for row in selection.data))
        hidden = eventtbl.displayHiddenColumns(tbl)

        def cb(row):
            changes = eventtbl.changedPaths(tbl, row['data'], hidden=hidden) if row['op'] == 'U' else []
            return dict(caption=captions.get(row['record_pkey']) or row['record_pkey'],
                        changes=', '.join(changes))
        selection.apply(cb)
