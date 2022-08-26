#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('lg_table_id')
        r.fieldcell('name', width='8em')
        r.fieldcell('data_type', name='T', width='3em')
        r.fieldcell('old_type', name='OT', width='3em')
        r.fieldcell('description', width='15em')
        r.fieldcell('notes', width='40em')
        r.fieldcell('group', width='8em')

    def th_order(self):
        return 'name'

    def th_query(self):
        return dict(column='name', op='contains', val='')

    def th_queryBySample(self):
        return dict(fields=[dict(field='@lg_table_id.sqlname', lbl='Table', width='12em'),
                            dict(field='name', lbl='Name', width='12em'),
                            dict(field='description', lbl='Description', width='14em'),
                            dict(field='notes', lbl='Notes', width='14em')],
                    cols=4, 
                    isDefault=True)

    

class ViewFromTable(View):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('lg_table_id')
        r.fieldcell('name', width='8em')
        r.fieldcell('data_type', name='T', width='3em')
        r.fieldcell('old_type', name='OT', width='3em')
        r.fieldcell('description', width='15em')
        r.fieldcell('notes', width='40em')
        r.fieldcell('group', width='8em')


    def th_top_custom(self, top):
        top.bar.replaceSlots('count','count,batchAssign')
        top.slotToolbar('10,sections@types,*,sections@groups,5',
                       childname='superiore',
                       sections_types_remote=self.sectionTypes,
                       sections_groups_remote=self.sectionGroups,
                       _position='<bar')
        
    def th_options(self):
        return dict(addrow=False)

    @public_method
    def sectionTypes(self):
        types = self.db.table('lgdb.lg_column').query('$data_type', distinct=True, 
                                                where= '$data_type IS NOT NULL').fetch()

        result=[]
        result.append(dict(code='all', caption='!![en]All'))
        for t in types:
            result.append(dict(code=t['data_type'], caption=t['data_type'], condition='$data_type= :tp', condition_tp=t['data_type']))
        result.append(dict(code='no_type', caption='!![en]No type', condition='$data_type IS NULL'))
        return result
    
    @public_method(remote_table_id='^#FORM.record.id')
    def sectionGroups(self, table_id, **kwargs):
        if not table_id:
            return []
        groups= self.db.table('lgdb.lg_column').query('$group',
                                                      distinct=True, 
                                                where= '$group IS NOT NULL AND $lg_table_id=:tbl_id',
                                                tbl_id=table_id).fetch()
        
        result=[]
        
        result.append(dict(code='all', caption='!![en]All'))
        result.append(dict(code='no_group', caption='!![en]No group', condition='$group IS NULL'))
        for g in groups:
            gname = g['group'].lower()
            result.append(dict(code=gname.replace(' ','_'), caption=g['group'], condition='LOWER($group)= :gr', condition_gr=gname))
        
        return result
        
    
class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.div(margin_right='10px').formbuilder(cols=2, border_spacing='4px', width='100%', fld_width='100%')
        fb.field('lg_table_id', readOnly=True, background='rgba(128, 128, 128, 0.125)' )
        fb.field('name')
        fb.field('data_type')
        fb.field('old_type')
        fb.field('group')
        fb.field('description', colspan=2)
        fb.field('notes', tag='simpleTextArea', height='90px')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px' )
