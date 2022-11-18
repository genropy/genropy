# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('is_active', semaphore=True, width='4em')
        r.fieldcell('page_id', width='20em')
        r.fieldcell('old_handbook_id', width='10em')
        r.fieldcell('new_handbook_id', width='10em')
        r.fieldcell('old_url', width='auto')
        r.fieldcell('new_url', width='auto')
        
    def th_order(self):
        return 'page_id'
        
    def th_query(self):
        return dict(column='page_id',op='contains', val='')

    def th_top_handbooks(self, top):
        top.slotToolbar('*,sections@handbooks,*', childname='superiore', _position='<bar')

    def th_sections_handbooks(self):
        result = [dict(code='all',caption='!![en]All')]
        handbooks = self.db.table('docu.redirect').query(
                            columns='$old_handbook_id,@old_handbook_id.title AS title,@old_handbook_id.name AS name', 
                            distinct=True).fetch()
        for h in handbooks:
            result.append(dict(code=h['name'], caption=h['title'], 
                                condition='$old_handbook_id=:h_id', condition_h_id=h['old_handbook_id']))
        return result

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
        fb.field('old_handbook_id', hasDownArrow=True, selected_docroot_id='.docroot_id')
        fb.field('new_handbook_id', hasDownArrow=True)
        fb.remoteSelect(value='^.page_id', lbl='!![en]Page',
                                                    condition_docroot_id='=.docroot_id',
                                                    method=self.getHandbookPages,
                                                    auxColumns='$handbook,$descrizione,$versione',
                                                    hasDownArrow=True)
        fb.field('is_active')
        fb.field('old_url', colspan=2, width='100%')
        fb.field('new_url', colspan=2, width='100%')

    @public_method
    def getHandbookPages(self, docroot_id=None, **kwargs):
        if not docroot_id:
            return
        result=Bag()
        pages = self.db.table('docu.documentation').query(
                                    where="string_to_array($hierarchical_pkey, '/') && string_to_array(:d_id,',')", 
                                    d_id=docroot_id, bagFields=True).fetch()
        for p in pages:
            pkey = p['pkey']
            title = list(filter(None, Bag(p['docbag']).digest('#v.title')))
            result.setItem(pkey, None, caption=p['hierarchical_name'], 
                                title=title,
                                _pkey=pkey)
        return result,dict(columns='caption,title', headers='Name,Title')

    def th_top_custom(self, top):
        bar = top.bar.replaceSlots('right_placeholder','right_placeholder,5,make_redirect')
        bar.make_redirect.slotButton('!![en]Make redirect').dataController("""genro.publish('table_script_run',
                                                                            {table:'docu.redirect',
                                                                            res_type:'action',
                                                                            resource:'make_redirect',
                                                                            pkey:pkey});""",
                                                                            pkey='=#FORM.record.id')

    def th_options(self):
        return dict(duplicate=True)