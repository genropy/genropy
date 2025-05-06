# -*- coding: utf-8 -*-
from gnr.sql.gnrsql import GnrSqlMissingTable
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:RecordRpc'
    convert_result = False
    skip_connection = False

    def rootPage(self,switch,pkg,tbl,pkey,ep,*args,**kwargs):
        ephandler = getattr(self,f'ep_{switch}_{ep}',self.ep_missing)
        table = f'{pkg}.{tbl}'
        try:
            tblobj = self.db.table(table)
        except GnrSqlMissingTable:
            self.ep_error = 'Missing table {table}'
            return 
        return ephandler(tblobj,pkey,*args,**kwargs)

    def ep_missing(self,*args,**kwargs):
        return 'Missing'

    def ep_record_print(self,tblobj,pkey,document=None,resource=None,version=None,**kwargs):
        if document:
            documentColumn = tblobj.column(document)
            handlername = document
            record = tblobj.record(pkey).output('record')
            documentNode = None
            if documentColumn is not None:
                documentNode = self.getDocumentNode(tblobj,record=record,field=document,version=version)
            if not documentNode:
                handlername = f'_table.{tblobj.fullname}.printRecord_{document}'
                handler = self.getPublicMethod('rpc',handlername)
                documentpath = handler(pkey,**kwargs)
                documentNode = self.site.storageNode(documentpath)
            self.response.content_type = 'application/pdf'
            with documentNode.open('rb') as f:
                return f.read()

    def getDocumentNode(self,tblobj,record=None,field=None,version=None,at_date=None):
        documentpath = record[field]
        history_field = tblobj.column(f'{field}_history')
        version = version or 0
        if documentpath:
            if version>0 or at_date:
                if history_field is None:
                    raise GnrException(f'Missing field {history_field}')
                version_bag = Bag(record[history_field]) or Bag()
                if version_bag and at_date:
                    version = 1
                    for n in version_bag:
                        if n.attr['date']>=at_date:
                            break
                        version+=1
                documentpath = f'{documentpath.split(".")[0]}_versions',f'v_{version:04}.pdf'
            return self.site.storageNode(documentpath)
