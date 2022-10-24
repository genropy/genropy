#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('codekey')
        r.fieldcell('service_identifier')
        r.fieldcell('longurl')
        r.fieldcell('shorturl')
        r.fieldcell('domain')
        r.fieldcell('key')
        r.fieldcell('expiration')
        r.fieldcell('traking')

    def th_order(self):
        return 'codekey'

    def th_query(self):
        return dict(column='codekey', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('codekey')
        fb.field('service_identifier')
        fb.field('longurl')
        fb.field('shorturl')
        fb.field('domain')
        fb.field('key')
        fb.field('expiration')
        fb.field('traking')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
