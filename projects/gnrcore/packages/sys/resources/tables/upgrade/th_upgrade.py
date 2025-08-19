#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('__mod_ts', name='!!Last Modified', width='8em')
        r.fieldcell('codekey')
        r.fieldcell('pkg')
        r.fieldcell('filename')
        r.fieldcell('error', width='auto')

    def th_order(self):
        return 'codekey'

    def th_query(self):
        return dict(column='codekey', op='contains', val='')
    
    def th_top_custom(self,top):
        top.slotToolbar('2,sections@packages,*',childname='upper',_position='<bar')
        
    def th_sections_packages(self):
        return self.th_distinctSections(table='sys.upgrade',field='pkg')

    def th_options(self):
        return dict(addrow=False)
    

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('codekey')
        fb.field('pkg')
        fb.field('filename')
        fb.field('error')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px', addrow=False)
