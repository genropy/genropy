#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('message_id')
        r.fieldcell('address')
        r.fieldcell('reason')

    def th_order(self):
        return 'message_id'

    def th_query(self):
        return dict(column='message_id', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('message_id')
        fb.field('address')
        fb.field('reason')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
