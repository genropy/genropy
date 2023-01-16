#!/usr/bin/env python
# encoding: utf-8
#
#btcexport.py
#
#Created by Francesco Porcari on 2010-10-16.
#Copyright (c) 2011 Softwell. All rights reserved.

#from builtins import object
from gnr.core.gnrdict import dictExtract
from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.core.gnrbag import Bag
from gnr.core.gnrexporter import getWriter
from gnr.core.gnrlang import objectExtract
import re



class BaseResourceExport(BaseResourceBatch):
    batch_immediate = True
    export_zip = False
    export_mode = 'xls'
    localized_data = False
    locale = None
    def __init__(self, *args, **kwargs):
        super(BaseResourceExport, self).__init__(*args, **kwargs)
        self.locale = self.locale or self.page.locale
        self.columns = []
        self.hiddencolumns = []
        self.headers = []
        self.coltypes = {}
        self.groups = []
        self.data = None

    def gridcall(self, data=None, struct=None, export_mode=None, datamode=None,selectedRowidx=None,filename=None,
                    localized_data=None,**kwargs):
        self.batch_parameters = dict(export_mode=export_mode, filename=filename,localized_data=localized_data)
        self.batch_parameters.update(kwargs)
        self.prepareExportCols(data,struct=struct)
        if not isinstance(data,Bag):
            data = data.output('grid')
        self.data = self.rowFromValue(data) if datamode == 'bag' else self.rowFromAttr(data)
        self._pre_process()
        self.do()
        return self.fileurl

    def rowFromAttr(self, data):
        if data: # prevents eror if there is no selection added by JBE 2012-01-23
            for r in data:
                yield r.getAttr()

    def rowFromValue(self, data):
        if data: # prevents eror if there is no selection added by JBE 2012-01-23
            for r in data:
                yield r.getValue()

    def _prepareExportCols_struct(self, struct=None):
        info = struct.pop('info')
        columnsets = {}
        if info:
            columnsets[None]=''
            for columnset in (info['columnsets'] or []):
                columnsets[columnset.getAttr('code')]=columnset.getAttr('name')
        for view in list(struct.values()):
            for row in list(view.values()):
                curr_columnset = dict(start=0, name='')
                curr_column = 0
                for curr_column,cell in enumerate(row):
                    if cell.getAttr('hidden') is True:
                        continue
                    col = self.db.colToAs(cell.getAttr('caption_field') or cell.getAttr('field'))
                    if cell.getAttr('group_aggr'):
                        col = '%s_%s' %(col,re.sub("\\W", "_",cell.getAttr('group_aggr').lower()))
                    self.columns.append(col)
                    self.headers.append(cell.getAttr('name'))
                    self.coltypes[col] = cell.getAttr('dtype')
                    columnset = cell.getAttr('columnset')
                    columnset_name = columnsets.get(columnset)
                    if columnset_name!=curr_columnset.get('name'):
                        curr_columnset['end']=curr_column-1
                        if curr_columnset.get('name'):
                            self.groups.append(curr_columnset)
                        curr_columnset = dict(start=curr_column, name=columnset_name)
                curr_columnset['end']=curr_column
                if curr_columnset.get('name'):
                    self.groups.append(curr_columnset)

    def getFileName(self):
        return 'export'

    def _prepareExportCols_selection(self,selection):
        self.columns = selection.columns
        hiddencolumns = [c.replace('$','').replace('@','_').replace('.','_') for c in self.hiddencolumns]+['pkey', 'rowidx']
        self.columns = [c for c in self.columns if c not in hiddencolumns]
        self.coltypes = dict([(k, v['dataType']) for k, v in selection.colAttrs.items()])
        self.headers = self.columns

    def prepareExportCols(self,selection,struct=None):
        if not struct:
            self._prepareExportCols_selection(selection)
        else:
            self._prepareExportCols_struct(struct)

    def _pre_process(self):
        self.pre_process()
        self.fileurl = None
        self.localized_data = self.batch_parameters.get('localized_data',self.localized_data)
        self.export_mode = self.batch_parameters.get('export_mode',self.export_mode)
        self.prepareFilePath(self.batch_parameters.get('filename',self.getFileName()))
        if not self.data:
            selection = self.get_selection()
            struct = self.batch_parameters.get('struct')
            self.data = self.btc.thermo_wrapper(selection.data, message=self.tblobj.name_plural, tblobj=self.tblobj)
            self.prepareExportCols(selection,struct)
        writerPars = dict(columns=self.columns, coltypes=self.coltypes, headers=self.headers,
                        filepath=self.filepath, groups=self.groups,
                        locale= self.locale if self.localized_data else None)
        extraPars = objectExtract(self,f'{self.export_mode}_')
        modeParameters = dictExtract(self.batch_parameters,f'{self.export_mode}_')
        writerPars.update(extraPars)
        writerPars.update(modeParameters)
        print_prefs = self.db.application.getPreference('.xlsx_print',pkg='sys')
        writerPars['print_prefs'] = print_prefs
        self.writer = getWriter(self.export_mode)(**writerPars)
    

    def do(self):
        self.writer.writeHeaders()
        for row in self.data:
            self.writer.writeRow(row)
        self.post_process()

    def post_process(self):
        self.writer.workbookSave()
        export_mode = self.export_mode
        if self.export_zip:
            export_mode = 'zip'
            zipNode = self.page.site.storageNode('page:output',export_mode,'%s.%s' % (self.filename, export_mode), autocreate=-1)
            self.page.site.zipFiles(file_list=[self.filepath],zipPath=zipNode)
            self.filepath = zipNode.fullpath

        filename = self.filename
        if not self.filename.endswith('.%s' %self.writer.extension):
            filename = '%s.%s' % (self.filename, self.writer.extension)
        self.fileurl = self.page.site.storageNode('page:output', export_mode, filename).url()

    def prepareFilePath(self, filename=None):
        if not filename:
            filename = self.maintable.replace('.', '_') if hasattr(self, 'maintable') else self.page.getUuid()
        filename = filename.replace(' ', '_').replace('.', '_').replace('/', '_')[:64]
        filename = filename.encode('ascii', 'ignore').decode('utf-8')
        self.filename = filename
        self.filepath = self.page.site.storageNode('page:output',self.export_mode,'%s.%s' % (self.filename, self.export_mode), autocreate=-1)

    def result_handler(self):
        if self.batch_immediate:
            self.page.setInClientData(path='gnr.downloadurl',value=self.fileurl,fired=True)

        return 'Execution completed', dict(url=self.fileurl, document_name=self.batch_parameters.get('filename',self.fileurl.split('/')[-1]))

    def get_record_caption(self, item, progress, maximum, **kwargs):
        caption = '%s (%i/%i)' % (self.tblobj.recordCaption(item),
                                  progress, maximum)
        return caption
