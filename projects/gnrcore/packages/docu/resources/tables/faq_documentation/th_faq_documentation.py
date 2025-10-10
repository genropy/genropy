#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('faq_id')
        r.fieldcell('documentation_id')

    def th_order(self):
        return 'faq_id'

    def th_query(self):
        return dict(column='faq_id', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('faq_id')
        fb.field('documentation_id')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
