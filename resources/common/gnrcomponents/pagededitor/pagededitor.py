# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import public_method,extract_kwargs
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import objectExtract


class PagedEditor(BaseComponent):
    css_requires='gnrcomponents/pagededitor/pagededitor'
    #js_requires='gnrcomponents/pagededitor/pagededitor'

    @extract_kwargs(editor=True,tpl=dict(slice_prefix=False))
    @struct_method
    def pe_pagedEditor(self,pane,value=None,editor_kwargs=None,letterhead_id=None,pagedText=None,printAction=None,bodyStyle=None,
                        datasource=None,extra_bottom=None,tpl_kwargs=True,**kwargs):
        bodyStyle = bodyStyle or self.getPreference('print.bodyStyle',pkg='adm') or self.getService('htmltopdf').printBodyStyle()
        bc = pane.borderContainer(_workspace=True,**kwargs)
        printId = 'pe_print_%s' %id(bc)
        bc.dataRpc(self.pe_printPages,
                    pages=pagedText.replace('^','='),
                    bodyStyle=bodyStyle,nodeId=printId,
                    selfsubscribe_print=True)
        if printAction is True:
            printAction = f"""genro.nodeById('{printId}').publish('print');"""
        center = bc.contentPane(overflow='hidden',region='center')
        editor = center.ExtendedCkeditor(value=value,**editor_kwargs)
        bc.contentPane(region='right',width='30%',closable=True,splitter=True,border_left='1px solid silver',
                            margin_left='2px',margin_right='2px').pagedHtml(sourceText=value,pagedText=pagedText,letterheads='^#WORKSPACE.letterheads',editor=editor,letterhead_id=letterhead_id,
                                printAction=printAction,bodyStyle=bodyStyle,datasource=datasource,extra_bottom=extra_bottom,**tpl_kwargs)
        
        bc.dataRemote('#WORKSPACE.letterheads',self._pe_getLetterhead,letterhead_id=letterhead_id,_if='letterhead_id')#_userChanges=True)
        bc._editor = editor
        return bc


    @public_method
    def _pe_getLetterhead(self,letterhead_id=None,**kwargs):
        letterheadtbl = self.db.table('adm.htmltemplate')
        next_letterhead_id = None
        if ',' in letterhead_id:
            letterhead_id,next_letterhead_id = letterhead_id.split(',')
        else:
            next_letterhead_id = letterheadtbl.readColumns(pkey=letterhead_id,columns='$next_letterhead_id') 
        result = Bag()
        base = letterheadtbl.getHtmlBuilder(letterhead_pkeys=letterhead_id)
        base.finalize(base.body)
        basehtml = base.root.getItem('#0.#1').toXml(omitRoot=True,autocreate=True,forcedTagAttr='tag',docHeader=' ',
                                        addBagTypeAttr=False, typeattrs=False, 
                                        self_closed_tags=['meta', 'br', 'img'])
        result.setItem('page_base',basehtml,**objectExtract(base,'page_',slicePrefix=False))
        if next_letterhead_id:
            nextbuilder = letterheadtbl.getHtmlBuilder(letterhead_pkeys=next_letterhead_id)
            base.finalize(nextbuilder.body)
            nexthtml = nextbuilder.root.getItem('#0.#1').toXml(omitRoot=True,autocreate=True,forcedTagAttr='tag',docHeader=' ',
                                        addBagTypeAttr=False, typeattrs=False, 
                                        self_closed_tags=['meta', 'br', 'img'])
            result.setItem('page_next',nexthtml)
        return result


    @public_method
    def pe_printPages(self,pages=None,bodyStyle=None,**kwargs):
        self.getService('htmltopdf').htmlToPdf(pages,self.site.getStaticPath('page:temp','pe_preview.pdf',autocreate=-1), bodyStyle=bodyStyle)
        self.setInClientData(path='gnr.clientprint',value=self.site.getStaticUrl('page:temp','pe_preview.pdf', nocache=True),fired=True)
