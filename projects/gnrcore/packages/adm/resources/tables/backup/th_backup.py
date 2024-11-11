#!/usr/bin/python
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('completed', semaphore=True, width='2.5em', name='OK')
        r.fieldcell('start_ts', width='10em')
        r.fieldcell('file_url', name='DL', width='2.5em',
               template='<a href="$file_url"><img src="/_rsrc/common/css_icons/svg/16/link_connected.svg" height="13px" /></a>')
        r.fieldcell('file_url', name='Filepath', width='auto')

    def th_order(self):
        return 'start_ts:d'

    def th_query(self):
        return dict(column='start_ts', op='equal', val='!![en]This month')
    
    def th_top_custom(self, top):
        bar = top.bar.replaceSlots('addrow', 'addrow_custom')
        bar.addrow_custom.slotButton('!!New backup', iconClass='iconbox add_row').dataController(
                                        "FIRE .th_batch_run = {resource:'dumpall',res_type:'action'};")


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.field('start_ts', readOnly=True)
        fb.a('^.file_url', lbl='!!Download', href='^.file_url', hidden='^.file_url?=!#v')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px', addrow=False)
