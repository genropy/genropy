# -*- coding: utf-8 -*-
from gnr.sql.gnrsql import GnrSqlMissingTable
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:RecordRpc'
    convert_result = False
    skip_connection = False

    def rootPage(self,pkg,tbl,pkey,ep,source,*args,**kwargs):
        ephandler = getattr(self,f'ep_{ep}',self.ep_missing)
        table = f'{pkg}.{tbl}'
        try:
            tblobj = self.db.table(table)
        except GnrSqlMissingTable:
            self.ep_error = 'Missing table {table}'
            return 
        return ephandler(tblobj,pkey,source,*args,**kwargs)

    def ep_missing(self,*args,**kwargs):
        return 'Missing'

    def ep_get(self,tblobj,pkey,source=None,version=None,**kwargs):
        if not source:
            return
        documentNode = self._get_documentNode(tblobj,pkey=pkey,source=source,version=version,**kwargs)
        if not documentNode:
            return ''
        self.response.content_type = documentNode.mimetype
        with documentNode.open('rb') as f:
            return f.read()

    
    def _get_documentNode(self,tblobj,pkey=None,source=None,version=None,**kwargs):
        isCachedInField = tblobj.column(source) is not None
        handlername = f'_table.{tblobj.fullname}.getDocument_{source}'
        try:
            handler = self.getPublicMethod('rpc',handlername)
        except AttributeError:
            handler = None
        record = tblobj.record(pkey).output('record')
        documentNode = None
        if isCachedInField:
            documentNode = self.getStoredDocumentFromField(tblobj,record=record,field=source,version=version)
            if documentNode and not documentNode.exists:
                documentNode = None
        if handler and not documentNode:
            documentpath = handler(pkey,**kwargs)
            documentNode = self.site.storageNode(documentpath)
        if isCachedInField and record[source] != documentNode.fullpath:
            with tblobj.recordToUpdate(pkey,raw=True) as rec:
                rec[source] = documentNode.fullpath
            self.db.commit()
        return documentNode



    def getStoredDocumentFromField(self,tblobj,record=None,field=None,version=None,at_date=None):
        documentpath = record[field]
        history_field = tblobj.column(f'{field}_history')
        version = version or 0
        if not (version or at_date):
            return self.site.storageNode(documentpath) if documentpath else None
        if history_field is None:
            raise GnrException(f'Missing field {history_field}')
        version_bag = Bag(record[history_field]) or Bag()
        if version_bag and at_date:
            version = 1
            for n in version_bag:
                if n.attr['date']>=at_date:
                    break
                version+=1
        versionpath = f'{documentpath.split(".")[0]}_versions',f'v_{version:04}.pdf'
        return self.site.storageNode(versionpath)

