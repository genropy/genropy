# -*- coding: utf-8 -*-

# th_handbook.py
# Created by Saverio Porcari.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('name', name='!!Name', width='20em')
        r.fieldcell('title', name='!!Title', width='20em')
        r.fieldcell('docroot_id', name='!!Doc root', width='20em')
        r.fieldcell('language', name='!!Language', width='5')
        r.fieldcell('version', name='!!Version', width='20em')
        r.fieldcell('last_exp_ts')
        
    def th_order(self):
        return 'name'
        
    def th_query(self):
        return dict(column='title',op='contains', val='')

class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top',datapath='.record')
        fb = top.div(margin_right='20px').formbuilder(cols=2,border_spacing='3px',
                                                    fld_width='100%',
                                                    width='100%',colswidth='auto')
        fb.field('name',colspan=2)
        fb.field('title',colspan=2)
        fb.field('docroot_id', hasDownArrow=True, validate_notnull=True, tag='hdbselect', folderSelectable=True)
        fb.checkBoxText(value='^.toc_roots',#values='MI:Milano,CO:Como,SO:Sondrio')
                        table='docu.documentation', popup=True, cols=4,
                        condition='$parent_id = :docroot_id', condition_docroot_id='^.docroot_id' )


        fb.field('language')
        fb.field('version')
        fb.field('release')
        fb.field('author')
        fb.field('sphinx_path',colspan=2)

    def th_top_exportButton(self, top):
        bar = top.bar.replaceSlots('*','*,export_button')
        bar.export_button.slotButton('Exp.To Sphinx',
                                    action="""genro.publish("table_script_run",{table:"docu.handbook",
                                                                               res_type:'action',
                                                                               resource:'export_to_sphinx',
                                                                               handbook_id: pkey});""",
                                                                               pkey='=#FORM.pkey')

    
        
               