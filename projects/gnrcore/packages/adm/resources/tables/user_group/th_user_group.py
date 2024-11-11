#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('user_id')
        r.fieldcell('group_code')

    def th_order(self):
        return 'user_id'

    def th_query(self):
        return dict(column='user_id', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('user_id')
        fb.field('group_code')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
