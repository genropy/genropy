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
    py_requires = 'gnrcomponents/attachmanager/attachmanager:AttachManager'
    
    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top', height='200px')
        self.contentData(top.roundedGroup(title='!!Content Data', region='center', datapath='.record'))
        self.contentAttributes(top.borderContainer(title='!!Content Attributes', region='right', width='500px'))
        
        self.contentMain(bc.tabContainer(region='center'))
        
    @customizable
    def contentData(self, pane):
        fb = pane.formbuilder(cols=1, width='600px', border_spacing='4px')
        fb.field('title', width='30em')
        fb.field('headline', width='100%')
        fb.field('abstract', width='100%', height='100px', tag='simpleTextArea')
        return fb

    @customizable
    def contentAttributes(self, bc):
        bc.contentPane(region='center').plainTableHandler(
                                                    overflow_y='auto', overflow_x='hidden',
                                                    pbl_classes='*',
                                                    margin='2px', relation='@topic_contents',
                                                    searchOn=False, picker='topic',
                                                    delrow=True,
                                                    configurable=False)
        bc.contentPane(region='right', width='50%').plainTableHandler(
                                                    overflow_y='auto', overflow_x='hidden',
                                                    pbl_classes='*',
                                                    margin='2px', relation='@author_contents',
                                                    searchOn=False, picker='author_id',
                                                    delrow=True,
                                                    configurable=False)
        return bc
    
    @customizable
    def contentMain(self, tc):
        self.contentText(tc.contentPane(title='!!Text', datapath='.record', overflow='hidden'))
        self.contentTemplate(tc.contentPane(title='!!Template', datapath='.record'))
        self.contentAttachments(tc.contentPane(title='!!Attachments'))
        return tc
    
    def contentText(self, pane):
        pane.ckEditor('^.text')
    
    def contentTemplate(self, pane):
        pane.templateChunk(template='^.tplbag', editable=True, height='100%',
                                                table='docu.content', selfsubscribe_onChunkEdit='this.form.save();')

    def contentAttachments(self, pane):
        pane.attachmentMultiButtonFrame()


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
    

class FormEmbed(Form):
    "Customizable Form to be embedded"

    def th_options(self):
        return dict(autoSave=True, showtoolbar=False)