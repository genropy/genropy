#!/usr/bin/env python
# encoding: utf-8
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
import os
import shutil
import textwrap

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('handbook', pkey='id', name_long='!!Handbook', 
                        name_plural='!!Handbooks',caption_field='name',audit='lazy')
        self.sysFields(tbl,hierarchical='name',df=True,
                        counter=True,user_ins=True,user_upd=True)
        tbl.column('name',name_long='!!Name', unique=True)
        tbl.column('title',name_long='!!Title')
        tbl.column('docroot_id', size='22', name_long='!!Doc root').relation('documentation.id',
                                                                                relation_name='handbooks',
                                                                                mode='foreignkey')
        tbl.column('toc_roots', name_long='Toc roots')
        tbl.column('language',size=':2',name_long='Base language').relation('docu.language.code',mode='foreignkey')
        tbl.column('sphinx_path', name_long='Sphinx path')
        tbl.column('is_local_handbook', dtype='B', name_long='Is local handbook')
        tbl.column('local_handbook_zip', name_long='Local handbook zip')
        tbl.column('version', name_long='Version')
        tbl.column('author', name_long='Author')
        tbl.column('theme', name_long='Theme')
        tbl.column('handbook_url', name_long='Handbook url')
        tbl.column('examples_site',name_long='Examples site')
        tbl.column('examples_directory',name_long='Examples dir')
        tbl.column('last_exp_ts', dtype='DH', name_long='Last export ts')
        tbl.column('custom_styles',name_long='Custom styles')
        tbl.column('examples_pars',dtype='X', name_long='Examples parameters')
        tbl.column('ogp_image', dtype='P', name_long='!!Handbook preview image')

    def trigger_onDeleted(self, record):
        for node in ['build','source']:
            handbookNode = self.db.application.site.storageNode(record['sphinx_path']+f'/sphinx/{node}/')
            if not handbookNode.children():
                continue
            for file in handbookNode.children():
                file.delete()
    
    def trigger_onInserting(self, record):
        if not record['is_local_handbook'] and not record['sphinx_path']:
            self.checkSphinxPath(record)
    
    def trigger_onUpdating(self, record, old_record=None):
        if not record['is_local_handbook'] and not record['sphinx_path'] or record['name']!=old_record['name'] :
            self.checkSphinxPath(record)
    
    def checkSphinxPath(self, record):
        "Sets default path to handbooks if not specified"
        current_path = self.db.application.getPreference('.sphinx_path', pkg='docu')
        if not current_path:
            current_path = 'site:handbooks'
        handbook_name=record['name']
        record['sphinx_path'] = current_path + '/' + handbook_name