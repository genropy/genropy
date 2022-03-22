#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('documentation_id')
        r.fieldcell('user_id')

    def th_order(self):
        return 'documentation_id'

    def th_query(self):
        return dict(column='documentation_id', op='contains', val='')

class ViewFromDocumentation(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('__ins_ts', name='!!Date', width='6em', dtype='D')
        r.fieldcell('user_id', name='!!User', width='auto', edit=True)

    def th_order(self):
        return 'user_id'

class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record', height='100px')
        fb = top.formbuilder(cols=2, border_spacing='4px')
        fb.field('documentation_id')
        fb.field('user_id')

    def th_options(self):
        return dict(dialog_height='200px', dialog_width='300px')