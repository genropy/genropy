#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('postcode')
        r.fieldcell('suburb')
        r.fieldcell('state')
        r.fieldcell('lat')
        r.fieldcell('lon')

    def th_order(self):
        return 'postcode'

    def th_query(self):
        return dict(column='postcode', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('postcode')
        fb.field('suburb')
        fb.field('state')
        fb.field('lat')
        fb.field('lon')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
