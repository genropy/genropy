#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('ts')
        r.fieldcell('data')

    def th_order(self):
        return 'ts'

    def th_query(self):
        return dict(column='ts', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('ts')
        fb.field('data')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
