#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('cap',width='4em')
        r.fieldcell('@provincia.nome',width='100%',name='Provincia')

    def th_order(self):
        return 'cap'

    def th_query(self):
        return dict(column='cap', op='contains', val='')

class ViewPicker(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('cap',width='4em')
        r.fieldcell('provincia',width='100%',name='Provincia')

    def th_order(self):
        return 'cap'

    def th_query(self):
        return dict(column='cap', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('cap')
        fb.field('provincia')
        fb.field('geocoords')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
