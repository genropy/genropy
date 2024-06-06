#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):
    js_requires='docu_components'

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('content_id')
        r.fieldcell('version', width='3em')
        r.fieldcell('__ins_user', width='auto')
        r.fieldcell('__ins_ts', width='9em')
        r.fieldcell('text', hidden=True)

    def th_order(self):
        return 'content_id'

    def th_query(self):
        return dict(column='content_id', op='contains', val='')

    def th_view(self, view):
        view.dataController("""var diff = diffUtil.calculateDifference(new_version, old_version, 'html');
                                SET #FORM.diff=diff;
                            """, 
                            old_version='^.grid.selectedId?text', 
                            new_version='=#FORM.record.text', _if='old_version')

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('content_id')
        fb.field('version')
        fb.field('text')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')


class FormDiff(BaseComponent):

    def th_form(self, form):
        pane = form.record
        pane.div(width='100%', height='100%', overflow='hidden').simpleTextArea(
                        value='^.text', width='100%', height='100%')
        
    def th_options(self):
        return dict(showtoolbar=False, readOnly=True)