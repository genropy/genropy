#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method, customizable

class ContentsComponent(BaseComponent):

    def contentEditor(self, pane, value=None,htmlpath=None, **kwargs):
        pane.MDEditor(value=value,htmlpath=htmlpath, nodeId='contentMd', height='100%', previewStyle='vertical',
                        initialEditType='wysiwyg',viewer=True, **kwargs)
        
    @customizable    
    def contentData(self, pane, **kwargs):
        fb = pane.formbuilder(cols=1, width='600px', border_spacing='4px', **kwargs)
        fb.field('title', width='30em')
        fb.field('headline', width='100%')
        fb.field('abstract', width='100%', height='100px', tag='simpleTextArea')
        return fb
    
    @customizable
    def contentAttributes(self, bc, **kwargs):
        self.contentAuthors(bc.contentPane(region='center'), **kwargs)
        self.contentTopics(bc.contentPane(region='right', width='50%'), **kwargs)
        return bc
        
    def contentAuthors(self, pane, **kwargs):
        pane.plainTableHandler(overflow_y='auto', overflow_x='hidden',
                                                    pbl_classes='*',
                                                    margin='2px', relation='@topic_contents',
                                                    searchOn=False, picker='topic',
                                                    delrow=True,
                                                    configurable=False,
                                                    **kwargs)
    
    def contentTopics(self, pane, **kwargs):
        pane.plainTableHandler(overflow_y='auto', overflow_x='hidden',
                                                    pbl_classes='*',
                                                    margin='2px', relation='@author_contents',
                                                    searchOn=False, picker='author_id',
                                                    delrow=True,
                                                    configurable=False, 
                                                    **kwargs)
    
    def contentText(self, bc):
        self.contentEditor(bc.contentPane(region='center',overflow='hidden',datapath='.record'), value='^.text',htmlpath='.html')

    def contentTemplate(self, pane):
        pane.templateChunk(template='^.tplbag', editable=True, height='100%', margin='5px', overflow='hidden',
                                                table='docu.content', selfsubscribe_onChunkEdit='this.form.save();')

    def contentAttachments(self, pane):
        pane.attachmentMultiButtonFrame()

    def contentVersions(self, bc, **kwargs):
        bc.contentPane(region='center').plainTableHandler(relation='@versions', formResource='FormDiff', configurable=False)
        bc.contentPane(region='bottom', closable='close', closable_label='!![en]Differences', height='50%').simpleTextArea(
                                                    '^.diff', overflow='hidden', height='100%', width='100%', editor=True)