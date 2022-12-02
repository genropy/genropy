#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('date')

    def th_order(self):
        return 'date'

    def th_query(self):
        return dict(column='date', op='contains', val='')

class ViewCalendar(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('date',hidden=True)
        r.fieldcell('weekday',hidden=True)
        r.fieldcell('holiday',hidden=True)
        r.fieldcell('day_cal',width='100%')

    def th_top_custom(self,top):
        top.bar.replaceSlots('#','*,spacer,*',background='transparent',_class='')


    def th_order(self):
        return 'date:d'

    def th_view(self,view):
        view.attributes['_class'] = f"{view.attributes['_class']} noheader templateGrid"


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('date')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
