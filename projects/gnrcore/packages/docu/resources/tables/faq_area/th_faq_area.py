#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('parent_id')
        r.fieldcell('name')
        r.fieldcell('hierarchical_name')
        r.fieldcell('_parent_h_name')
        r.fieldcell('hierarchical_pkey')
        r.fieldcell('_parent_h_pkey')
        r.fieldcell('_h_count')
        r.fieldcell('_parent_h_count')
        r.fieldcell('_row_count')

    def th_order(self):
        return 'parent_id'

    def th_query(self):
        return dict(column='parent_id', op='contains', val='')



class Form(BaseComponent):
    py_requires='gnrcomponents/dynamicform/dynamicform:DynamicForm'

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record', padding='5px')
        fb = top.formbuilder(cols=2, border_spacing='4px')
        fb.field('name', colspan=2, width='30em')

        center = bc.contentPane(region='center', overflow='hidden')
        th = center.dialogTableHandler(relation='@faqs', viewResource='ViewFromAreaFaqs', 
                                                                margin='2px', pbl_classes=True,
                                                                grid_selfDragRows=True)
        form.htree.relatedTableHandler(th, inherited=True) 
                                        
    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px', hierarchical='open')