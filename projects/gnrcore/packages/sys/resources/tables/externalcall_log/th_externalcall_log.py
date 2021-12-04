#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('endpoint')
        r.fieldcell('methodname')
        r.fieldcell('parameters')
        r.fieldcell('error')
        r.fieldcell('result')

    def th_order(self):
        return 'endpoint'

    def th_query(self):
        return dict(column='endpoint', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('endpoint')
        fb.field('methodname')
        fb.field('parameters')
        fb.field('error')
        fb.field('result')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
