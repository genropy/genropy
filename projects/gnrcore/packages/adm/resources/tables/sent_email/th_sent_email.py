#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('code')
        r.fieldcell('tbl')
        r.fieldcell('mail_address')
        r.fieldcell('sent_ts')
        r.fieldcell('record_id')

    def th_order(self):
        return 'code'

    def th_query(self):
        return dict(column='code', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('code')
        fb.field('tbl')
        fb.field('mail_address')
        fb.field('sent_ts')
        fb.field('record_id')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
