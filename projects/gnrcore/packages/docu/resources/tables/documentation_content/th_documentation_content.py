#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('content_id')
        r.fieldcell('documentation_id')
        r.fieldcell('language_code')

    def th_order(self):
        return 'content_id'

    def th_query(self):
        return dict(column='content_id', op='contains', val='')



class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('content_id')
        fb.field('documentation_id')
        fb.field('language_code')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')


class ContentForm(BaseComponent):
    py_requires='docu_components:ContentsComponent'

    def th_form(self, form):
        bc = form.center.borderContainer(datapath='.record')
        bc.contentPane(region='top').formbuilder(datapath='.@content_id', 
                                        table='docu.content').field('title', width='30em')

        self.contentText(bc.contentPane(region='center', datapath='.@content_id', 
                                        overflow='hidden', title='!!Content'))
                            
    def th_options(self):
        return dict(showtoolbar=False, defaultPrompt=dict(title='!!New content',
                                    fields=[dict(value='^.language_code',tag='dbSelect',lbl='!!Language',validate_notnull=True,
                                                 table='adm.language', hasDownArrow=True, 
                                                 condition="$code NOT ILIKE ALL(string_to_array(:exs_lang, ','))",
                                                 condition_exs_lang='^#FORM/parent/#FORM.record.available_languages')]))
