# -*- coding: utf-8 -*-

# th_handbook.py
# Created by Saverio Porcari.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('name', name='!!Name', width='20em')
        r.fieldcell('title', name='!!Title', width='20em')
        r.fieldcell('docroot_id', name='!!Doc root', width='20em')
        r.fieldcell('language', name='!!Language', width='5em')
        r.fieldcell('version', name='!!Version', width='8em')
        r.fieldcell('last_exp_ts', width='12em')
        r.fieldcell('handbook_url', width='auto', template="<a href='#' target='_blank'>#</a>")
        
    def th_order(self):
        return 'name'
        
    def th_query(self):
        return dict(column='title',op='contains', val='')

    def th_top_upperslotbar(self,top):
        top.slotToolbar('5,sections@is_local,*,sections@language,5',childname='upper',_position='<bar')

    def th_sections_is_local(self):
        return [dict(code='all',caption='!![en]All'),
                dict(code='online',caption='!![en]Online',condition='$is_local_handbook IS NOT TRUE'),
                dict(code='local',caption='!![en]Local', condition='$is_local_handbook IS TRUE'),
                ]


class Form(BaseComponent):

    def th_form(self, form):
        tc = form.center.tabContainer(datapath='.record')
        self.handbookInfo(tc.contentPane(title='!![en]Info'))
        self.handbookDocRoot(tc.contentPane(title='!![en]Documentation', hidden='^.docroot_id?=!#v'))
        tc.contentPane(title='!![en]Preview', hidden='==(handbook_url || local)', 
                    handbook_url='^.handbook_url?=!#v', local='^.is_local_handbook').remote(
                    self.handbookPreview, _if='handbook_url', handbook_url='^.handbook_url?=!#v')
        self.handbookZip(tc.contentPane(title='!![en]Zip', hidden='^.is_local_handbook?=#v!=true'))

    def handbookInfo(self, main):
        main_bc = main.borderContainer()
        left = main_bc.contentPane(region='left', width='70%')
        fb = left.formbuilder(cols=2,border_spacing='6px',
                                                    fld_width='100%',
                                                    max_width='800px',
                                                    width='100%', colswidth='auto')
        fb.field('name', validate_notnull=True)
        fb.field('is_local_handbook', lbl='', label='!![en]Is local handbook')
        fb.field('title', validate_notnull=True)
        fb.div('^.sphinx_path', lbl='!![en]Sphinx path', hidden='==(handbook_url || local)', 
                                                handbook_url='^.handbook_url?=!#v', local='^.is_local_handbook')
        fb.field('docroot_id', hasDownArrow=True, validate_notnull=True, tag='hdbselect', folderSelectable=True)
        fb.checkBoxText(value='^.toc_roots',
                        table='docu.documentation', popup=True, cols=4,lbl='!![en]TOC roots',
                        condition='$parent_id = :docroot_id', condition_docroot_id='^.docroot_id' )
        fb.field('language', validate_notnull=True)
        fb.field('version')
        fb.field('author')
        themesSn = self.site.storageNode('rsrc:pkg_docu','sphinx_env','themes')
        if themesSn.exists:
            themes = ','.join([s.basename for s in themesSn.children() if s.isdir and not s.basename.startswith('.')])
            fb.field('theme', values=themes, tag='filteringSelect')
        else:
            fb.textBox(value='Sphinx RTD standard theme', lbl='Theme', readOnly=True)
        
        fb.field('examples_site')
        fb.field('examples_directory')
        fb.field('custom_styles',tag='simpleTextArea',colspan=2,height='150px')

        right = main_bc.contentPane(region='center', width='360px', padding='20px')
        right.img(src='^.ogp_image',
                max_width='300px', width='300px',
                max_height='158px', height='158px',
                crop_border='2px dotted silver',
                crop_rounded=6,
                placeholder=True,
                edit=True, 
                upload_folder='documentation:handbooks_images',
                upload_filename='=#FORM.record.name')
        right.span('Recommended file size: 1200x628', font_size='10px', font_style='italic', margin='5px')
        right.button('Remove', hidden='^.ogp_image?=!#v', margin='5px').dataController('SET .ogp_image = null;')
        
        bottom = left.borderContainer(region='center', margin='10px', margin_right='20px')
        example_pars_fb = bottom.formbuilder(cols=2,border_spacing='6px',
                                                    fld_width='100%',
                                                    max_width='500px',
                                                    width='100%',colswidth='auto',
                                                    datapath='.examples_pars',hidden='^#FORM.record.examples_site?=!#v')
    
        example_pars_fb.numberTextBox('^.default_height',width='6em',lbl='Default height')
        example_pars_fb.numberTextBox('^.default_width',width='6em',lbl='Default width')
        example_pars_fb.filteringSelect('^.source_region',width='8em',lbl='Source position',
                    values='stack:Stack Demo/Source,stack_f:Stack Source/Demo,top:Top,left:Left,bottom:Bottom,right:Right')

        examples_themesSn = self.site.storageNode('rsrc:js_libs', 'codemirror', 'theme')
        examples_themes = ','.join([s.cleanbasename for s in examples_themesSn.children() if s.basename.endswith('.css')])
        #DP202108 In this way we build the list of available themes which will be shown in the filteringSelect
        example_pars_fb.filteringSelect(value='^.source_theme',values=examples_themes, width='8em',lbl='Source theme')

    def handbookDocRoot(self, pane):
        th = pane.stackTableHandler(table='docu.documentation', datapath='#FORM.documentation', 
                                        viewResource='ViewFromHandbooks', formResource='FormFromHandbooks')
        pane.dataController("""
                docu_form.goToRecord(docroot_id);
                """, docu_form=th.form.js_form,
                _fired='^#FORM.controller.loaded',
                docroot_id='=#FORM.record.docroot_id',
                _if='docroot_id', _delay=1)

    @public_method
    def handbookPreview(self, frame, **kwargs):
        frame_bc = frame.borderContainer()
        frame_bc.contentPane(region='top', height='30px', overflow='hidden').formbuilder(margin='2px').a(
                            '^.handbook_url', lbl='!![en]Doc url:', href='^.handbook_url', 
                            target='_blank', hidden='^.handbook_url?=!#v')
        frame_bc.contentPane(region='center', overflow='hidden').htmlIframe(src='^.handbook_url', width='100%', height='100%')
    
    def handbookZip(self, frame):
        frame_bc = frame.borderContainer()
        frame_bc.contentPane(region='top', height='30px', overflow='hidden').formbuilder(margin='2px').a(
                            '^.local_handbook_zip', lbl='!![en]Doc url:', href='^.local_handbook_zip', 
                            target='_blank', hidden='^.local_handbook_zip?=!#v')
        frame_bc.contentPane(region='center', overflow='hidden').iframe(src='^.local_handbook_zip', width='100%', height='100%')

    def th_top_exportButton(self, top):
        bar = top.bar.replaceSlots('*','*,export_button')
        bar.export_button.slotButton('Exp.To Sphinx',
                                    action="""this.form.save();
                                                genro.publish("table_script_run",{table:"docu.handbook",
                                                                               res_type:'action',
                                                                               resource:'export_to_sphinx',
                                                                               handbook_id: pkey,
                                                                               publishOnResult:"btc_eseguito"})""",
                                                                               pkey='=#FORM.pkey')
        bar.dataController("this.form.reload();", subscribe_btc_eseguito=True)

    def th_options(self):
        return dict(duplicate=True)