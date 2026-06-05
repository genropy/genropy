#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('__ins_ts', name='!!Queued at', width='10em')
        r.fieldcell('@message_id.subject', width='auto')
        r.fieldcell('@message_id.to_address', width='15em')
        r.fieldcell('@message_id.from_address', width='15em')
        r.fieldcell('@message_id.account_id', width='12em')
        r.fieldcell('@message_id.send_date', width='10em')
        r.fieldcell('@message_id.error_ts', width='10em')
        r.fieldcell('@message_id.error_msg', width='15em')

    def th_order(self):
        return '__ins_ts'

    def th_query(self):
        return dict(column='message_id', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('message_id')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
