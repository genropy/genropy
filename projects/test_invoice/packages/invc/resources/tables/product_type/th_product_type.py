#!/usr/bin/python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('hierarchical_description')

    def th_order(self):
        return 'hierarchical_description'

    def th_query(self):
        return dict(column='hierarchical_description', op='contains', val='')



class Form(BaseComponent):
    py_requires = 'gnrcomponents/dynamicform/dynamicform:DynamicForm'
    def th_form(self, form):
        bc = form.center.borderContainer()
        fb = bc.contentPane(region='top',datapath='.record').formbuilder(cols=2, border_spacing='4px')
        fb.field('description',validate_notnull=True)
        tc = bc.tabContainer(region='center')
        th = tc.contentPane(title='Products').dialogTableHandler(relation='@products',
                                                                pbl_classes=True,
                                                                #grid_excludeCols='product_type_id',
                                                                margin='2px')
        form.htree.relatedTableHandler(th,dropOnRoot=False,inherited=True)
        tc.contentPane(title='Product fields').fieldsGrid(margin='2px',rounded=6,border='1px solid silver')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px',hierarchical=True)
