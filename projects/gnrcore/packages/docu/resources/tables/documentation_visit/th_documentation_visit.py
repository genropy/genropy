#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('visitor_identifier')
        r.fieldcell('documentation_id')
        r.fieldcell('visit_level')
        r.fieldcell('notes')

    def th_order(self):
        return 'visitor_identifier'

    def th_query(self):
        return dict(column='visitor_identifier', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('visitor_identifier')
        fb.field('documentation_id')
        fb.field('visit_level')
        fb.field('notes')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
