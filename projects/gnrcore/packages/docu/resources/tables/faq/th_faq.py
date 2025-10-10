#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('title')
        r.fieldcell('question')
        r.fieldcell('content_id')
        r.fieldcell('notes')
        r.fieldcell('faq_area_id')

    def th_order(self):
        return 'title'

    def th_query(self):
        return dict(column='title', op='contains', val='')


class ViewFromAreaFaqs(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count', width='2em', name=' ', counter=True)
        r.fieldcell('title', width='15em')
        r.fieldcell('question', width='auto')

    def th_order(self):
        return '_row_count'

    def th_query(self):
        return dict(column='title', op='contains', val='')
    

class Form(BaseComponent):
    py_requires = """docu_components:ContentsComponent"""

    def th_form(self, form):
        bc = form.center.borderContainer()
        fl = bc.contentPane(region='top', datapath='.record').formlet()
        fl.field('title')
        fl.field('question', tag='simpleTextArea', width='100%', height='60px')
        
        tc = bc.tabContainer(region='center')
        self.contentText(tc.contentPane(title='!!Answer', datapath='.record.@content_id', 
                                        overflow='hidden'))
        self.referencesPane(tc.contentPane(title='!!References'))
        self.notesPane(tc.contentPane(title='!!Notes', datapath='.record', overflow='hidden'))
    
    def referencesPane(self, pane):
        pane.plainTableHandler(relation='@faq_documentations', picker='documentation_id',
                               viewResource='ViewFromFaqs')
        
    def notesPane(self,pane):
        pane.simpleTextArea(value='^.note',width='100%',height='100%')
                        
    def th_options(self):
        return dict(dialog_windowRatio=.8, duplicate=True)