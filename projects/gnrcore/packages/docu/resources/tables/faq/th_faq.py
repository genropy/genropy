#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('question')
        r.fieldcell('topics')
        r.fieldcell('content_id')
        r.fieldcell('notes')
        r.fieldcell('faq_area_id')

    def th_order(self):
        return 'question'

    def th_query(self):
        return dict(column='question', op='contains', val='')


class ViewFromAreaFaqs(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count', width='2em', name=' ', counter=True)
        r.fieldcell('question', width='auto')
        r.fieldcell('topics', width='30em')

    def th_order(self):
        return '_row_count'

    def th_query(self):
        return dict(column='question', op='contains', val='')
    

class Form(BaseComponent):
    py_requires = """docu_components:ContentsComponent"""

    def th_form(self, form):
        bc = form.center.borderContainer()
        fl = bc.contentPane(region='top', datapath='.record').formlet()
        fl.simpleTextArea('^.@content_id.title', lbl='!!Question', width='100%', height='60px')
        fl.field('topics',width='12em',tag='checkBoxText',table='docu.topic',popup=True)
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