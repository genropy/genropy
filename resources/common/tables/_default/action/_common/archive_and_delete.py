# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.batch.btcaction import BaseResourceAction
from gnr.core.gnrbag import Bag
from collections import defaultdict
import os

caption = 'Archive and delete'
tags = '_DEV_,superadmin'
description = 'Archive and delete'

class Main(BaseResourceAction):
    batch_prefix = 'aad'
    batch_title = 'Archive and delete'
    batch_cancellable = True
    batch_delay = 0.5
    batch_steps = 'get_dependencies,archive,delete_archived'

    def step_get_dependencies(self):
        "Get dependencies"
        self.mode = self.batch_parameters.get('mode')
        self.curr_records = self.tblobj.query(where=f'${self.tblobj.pkey} IN :pkeys',pkeys=self.get_selection_pkeys(),addPkeyColumn=False,
                                    excludeLogicalDeleted=False,excludeDraft=False,subtable='*').fetch()
        self.archive_name = self.batch_parameters.get('name') or 'archive_for_%s' %self.tblobj.fullname.replace('.','_')
        #the archive paths are computed by step_archive: in delete only mode none is needed
        self.result_url = None
        self.tableDependencies = self.tblobj.dependenciesTree(self.curr_records)
        self.index_tables = list(self.db.tablesMasterIndex(hard=True)['_index_'].keys())

    def prepareArchiveFolders(self):
        """Compute the archive paths and create the folders that will actually be written.
        Called from step_archive only, so a delete only run leaves no empty folder behind"""
        name = self.archive_name
        site = self.page.site
        self.source_folder = site.getStaticPath('vol:export_archive','source',name)
        #records is the basename of the pickled bag (records.pik), not a folder: autocreate its parent only
        self.archive_path = site.getStaticPath('vol:export_archive','source',name,'records',autocreate=-1)
        #step_archive creates the files subfolders one per table and pkey, only when there is something to copy
        self.files_to_copy = site.getStaticPath('vol:export_archive','source',name,'files')
        self.result_path = site.getStaticPath('vol:export_archive','results','%s.zip' %name,autocreate=-1)
        self.result_url = site.getStaticUrl('vol:export_archive','results','%s.zip' %name)

    def step_archive(self):
        "Prepare Archive file"
        if self.mode == 'D':
            return
        self.prepareArchiveFolders()
        archive = Bag()
        for t in self.index_tables:
            tablename = t.replace('/','.')
            archivingTable = self.db.table(tablename)
            if tablename==self.tblobj.fullname:
                archive[t] = self.curr_records
            else:
                d = self.tableDependencies.get(tablename)
                if d:
                    pkeys = d['one'].union(d['many'])
                    archive[t] = archivingTable.query(where='$%s IN :pkeys' %archivingTable.pkey,
                                                pkeys=list(pkeys),
                                                addPkeyColumn=False,bagFields=True,
                                                excludeDraft=False,excludeLogicalDeleted=False,
                                                subtable='*').fetch()
            if hasattr(archivingTable,'onArchiveExport') and (t in archive):
                files = defaultdict(list)
                archivingTable.onArchiveExport(archive[t],files=files)
                for pkey,pathlist in list(files.items()):
                    destfolder = os.path.join(self.files_to_copy,tablename,pkey)
                    for sn in pathlist:
                        if not sn.exists:
                            continue
                        #created here and not before the loop: a record whose files are all
                        #missing must not leave an empty folder in the archive
                        if not os.path.exists(destfolder):
                            os.makedirs(destfolder)
                        destpath = os.path.join(destfolder,sn.basename)
                        sn.copy(destpath)
        archive.makePicklable()
        archive.pickle('%s.pik' %self.archive_path)
        self.page.site.zipFiles(self.source_folder,self.result_path)

    def step_delete_archived(self):
        "Delete archived"
        if self.mode == 'A':
            return
        self.db.setConstraintsDeferred()
        for t in reversed(self.index_tables):
            t = t.replace('/','.')
            if t in self.tableDependencies:
                s = self.tableDependencies.get(t)['many']
                if s:
                    self.db.table(t).sql_deleteSelection(_pkeys=list(s))
        self.tblobj.sql_deleteSelection(_pkeys=[r[self.tblobj.pkey] for r in self.curr_records])
        self.db.commit()

    def result_handler(self):
        if self.mode == 'D':
            return 'Completed', None
        resultAttr = dict(url=self.result_url)
        return 'Archived %s' %self.tblobj.name_plural, resultAttr
    
    
    def table_script_parameters_pane(self, pane, table=None,**kwargs):
        fb = pane.div(padding='10px').formbuilder(cols=1,border_spacing='3px')
        fb.filteringSelect(value='^.mode', lbl='Mode', values='D:Delete only,A:Archive only,AD:Archive and delete',validate_notnull=True)
        fb.textbox(value='^.name', lbl='Filename', disabled="^.mode?=(#v=='D' || #v==null)")
        # fb.checkbox(value='^.delete_archived',label='Delete archived')

