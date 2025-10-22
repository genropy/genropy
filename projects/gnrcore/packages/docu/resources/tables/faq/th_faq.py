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


class ViewPublic(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('_row_count', width='2em', name=' ', counter=True)
        r.fieldcell('question', width='auto')
        r.fieldcell('topics', width='30em')

    def th_order(self):
        return '_row_count'

    def th_query(self):
        return dict(column='answer',op='contains', val='')
        
    def th_top_custom(self, top):
        top.slotToolbar('5,sections@areas,*',childname='upper',_position='<bar')
            
    def th_sections_areas(self):
        return self.th_distinctSections(table='docu.faq',field='faq_area_name')
        
    def th_options(self):
        return dict(addrow=False, delrow=False, readOnly=True)
    
    


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
        fl = bc.contentPane(region='top').formlet(datapath='.record')
        fl.simpleTextArea('^.@content_id.title', lbl='!!Question', width='100%', height='60px')
        fl.field('topics',width='12em',tag='checkBoxText',table='docu.topic',popup=True)
        
        tc = bc.tabContainer(region='center')
        tc.contentPane(title='!!Answer', datapath='.record.@content_id', overflow='hidden').contentText(mode='html')
        self.referencesPane(tc.contentPane(title='!!References'))
        self.notesPane(tc.contentPane(title='!!Notes', datapath='.record', overflow='hidden'))
    
    def referencesPane(self, pane):
        pane.plainTableHandler(relation='@faq_documentations', picker='documentation_id',
                               viewResource='ViewFromFaqs')
        
    def notesPane(self,pane):
        pane.simpleTextArea(value='^.note',width='100%',height='100%')
                        
    def th_options(self):
        return dict(dialog_windowRatio=.8, duplicate=True)