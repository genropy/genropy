#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('message_identifier')
        r.fieldcell('sender')
        r.fieldcell('subscription_id')
        r.fieldcell('send_ts')
        r.fieldcell('click_ts')
        r.fieldcell('title')
        r.fieldcell('message')
        r.fieldcell('url')
        r.fieldcell('sending_error')

    def th_order(self):
        return 'message_identifier'

    def th_query(self):
        return dict(column='message_identifier', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('message_identifier')
        fb.field('sender')
        fb.field('subscription_id')
        fb.field('send_ts')
        fb.field('click_ts')
        fb.field('title')
        fb.field('message')
        fb.field('url')
        fb.field('sending_error')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
