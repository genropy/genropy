# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('is_active', semaphore=True, width='3em')
        r.fieldcell('page_id', width='18em')
        r.fieldcell('old_handbook_id', width='15em')
        r.fieldcell('new_handbook_id', width='15em')
        r.fieldcell('old_url', width='auto')
        r.fieldcell('new_url', width='auto')
        
    def th_order(self):
        return 'page_id'
        
    def th_query(self):
        return dict(column='page_id',op='contains', val='')

    def th_view(self,view):
        bar = view.top.bar.replaceSlots('delrow','make_redirect,5,delrow')
        bar.make_redirect.slotButton('!![en]Make redirect').dataController("""genro.publish('table_script_run',
                                                                            {table:'docu.redirect',
                                                                            res_type:'action',
                                                                            resource:'make_redirect',
                                                                            selectionName:grid.collectionStore().selectionName,
                                                                            selectedPkeys:selectedPkeys});""",
                                                                            grid=view.grid.js_widget,
                                                                            selectedPkeys='=.grid.currentSelectedPkeys')

class Form(BaseComponent):

    def th_form(self, form):
        fb = form.record.formbuilder(cols=2, fld_width='20em')
        fb.field('page_id')
        fb.field('is_active')
        fb.field('old_handbook_id', hasDownArrow=True)
        fb.field('new_handbook_id', hasDownArrow=True)
        fb.field('old_url')
        fb.field('new_url')

    def th_top_custom(self, top):
        bar = top.bar.replaceSlots('form_archive','make_redirect,5,form_archive')
        bar.make_redirect.slotButton('!![en]Make redirect').dataController("""genro.publish('table_script_run',
                                                                            {table:'docu.redirect',
                                                                            res_type:'action',
                                                                            resource:'make_redirect',
                                                                            pkey:pkey});""",
                                                                            pkey='=#FORM.record.id')
