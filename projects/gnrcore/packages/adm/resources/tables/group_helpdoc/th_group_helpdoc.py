#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count')
        r.fieldcell('group_code')
        r.fieldcell('helpdoc_id')

    def th_order(self):
        return '_row_count'

    def th_query(self):
        return dict(column='_row_count', op='contains', val='')

class ViewFromGroup(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count',counter=True)
        r.fieldcell('group_code')
        r.fieldcell('helpdoc_id')

    def th_order(self):
        return '_row_count'

    def th_query(self):
        return dict(column='_row_count', op='contains', val='')




class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('_row_count')
        fb.field('group_code')
        fb.field('helpdoc_id')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
