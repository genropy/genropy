#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method,customizable

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('title')
        r.fieldcell('headline')
        r.fieldcell('abstract')
        r.fieldcell('text')

    def th_order(self):
        return 'title'

    def th_query(self):
        return dict(column='title', op='contains', val='')
    
    

class ViewEmbed(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('__ins_ts', width='9em')
        r.fieldcell('title', width='auto')
        
    def th_order(self):
        return 'title'

    def th_query(self):
        return dict(column='title', op='contains', val='')
    
class ViewInline(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('title', edit=True, width='30em', zoom=True, zoom_mode='page')
        r.fieldcell('headline', edit=True, width='100%')

    def th_order(self):
        return 'title'

    def th_query(self):
        return dict(column='title', op='contains', val='')



class Form(BaseComponent):
    py_requires = """gnrcomponents/attachmanager/attachmanager:AttachManager,
                        docu_components:ContentsComponent"""
    
    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top', height='200px')
        self.contentData(top.roundedGroup(title='!!Content Data', region='center', datapath='.record'))
        self.contentAttributes(top.borderContainer(title='!!Content Attributes', region='right', width='500px'))
        self.contentMain(bc.tabContainer(region='center'))
    
    @customizable
    def contentMain(self, tc):
        self.contentText(tc.contentPane(title='!!Text', datapath='.record', overflow='hidden'))
        self.contentTemplate(tc.contentPane(title='!!Template', datapath='.record'))
        self.contentAttachments(tc.contentPane(title='!!Attachments'))
        return tc
    

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
    

class FormEmbed(Form):
    "Minimal Form to embed text content"

    def th_form(self, form):
        bc = form.record
        self.contentEditor(bc.contentPane(region='center',overflow='hidden',datapath='.record'), value='^.text',htmlpath='.html')
        
    def th_options(self):
        return dict(autoSave=True, showtoolbar=False)
    

class FormReview(Form):
    "Form to review text showing text and versions in a tabContainer"
    js_requires='docu_components'
    
    @customizable
    def th_form(self, form):
        tc = form.center.tabContainer(tabPosition='left-h')
        self.contentEditor(tc.contentPane(title='!!Text', region='center',overflow='hidden', 
                                          datapath='.record'), value='^.text',htmlpath='.html')
        self.contentVersions(tc.borderContainer(title='!!Versions', region='center'), value='^.text')
        return tc
        
    def th_options(self):
        return dict(form_add=False,form_delete=False)