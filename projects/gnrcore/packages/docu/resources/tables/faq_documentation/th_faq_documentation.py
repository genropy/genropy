#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('faq_id')
        r.fieldcell('documentation_id')

    def th_order(self):
        return 'faq_id'

    def th_query(self):
        return dict(column='faq_id', op='contains', val='')

class ViewFromFaqs(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('@documentation_id.name',width='20em')
        r.fieldcell('@documentation_id.topics',width='30em')
        r.cell('copyurl',calculated=True,name='!!Copy',cellClasses='cellbutton',
                    format_buttonclass='copy iconbox', width='3em',
                    format_isbutton=True,
                    format_onclick="""
                var row = this.widget.rowByIndex($1.rowIndex);
                var doc_full_external_url = row.doc_full_external_url;
                genro.textToClipboard(doc_full_external_url,_T('!!Copied to clipboard'));
                """)
        r.fieldcell('doc_full_external_url', name='!![en]Url', width='2.5em',
               template='<a href="$doc_full_external_url" target="_blank"><img src="/_rsrc/common/css_icons/svg/16/link_connected.svg" height="13px" /></a>')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('faq_id')
        fb.field('documentation_id')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
