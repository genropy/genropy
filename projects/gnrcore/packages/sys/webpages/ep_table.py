# -*- coding: utf-8 -*-
from gnr.sql.gnrsql import GnrSqlMissingTable
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbag import Bag
AUTH_FORBIDDEN = -1


class NotAllowedError(Exception):
    pass


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

    def ep_get(self,tblobj,pkey,source=None,version=None,force_download=False,**kwargs):
        if not source:
            return
        try:
            documentNode = self._get_documentNode(tblobj,pkey=pkey,source=source,version=version,**kwargs)
        except NotAllowedError:
            return AUTH_FORBIDDEN
        if not documentNode:
            return ''
        if self.is_inline_displayable(documentNode) or force_download:
            self.response.content_type = documentNode.mimetype
            with documentNode.open('rb') as f:
                return f.read()
        else:
            download_url = self.db.application.site.externalUrl(f"/sys/ep_table/{tblobj.fullname.replace('.','/')}/{pkey}/get/{source}",force_download=True,version=version,**kwargs)
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Download file</title>
                <style>
                    body {{ font-family: sans-serif; text-align: center; padding-top: 50px; }}
                    a.download-button {{
                        display: inline-block;
                        padding: 12px 20px;
                        background-color: #4CAF50;
                        color: white;
                        text-decoration: none;
                        border-radius: 6px;
                        font-size: 16px;
                    }}
                    a.download-button:hover {{
                        background-color: #45a049;
                    }}
                </style>
            </head>
            <body>
                <p><a class="download-button" href="{download_url}">
                    ⬇ Download file
                </a></p>
            </body>
            </html>
            """

    def _checkEndpointPermission(self,tags,**kwargs):
        _current_page_id = kwargs.get('_current_page_id') or kwargs.get('_calling_page_id')
        page_item = self.site.register.page(_current_page_id,include_data='lazy')
        if not page_item:
            raise NotAllowedError
        user = page_item['user'] or 'guest_'
        if user.startswith('guest_'):
            raise NotAllowedError
        tags = tags or ''
        user_tags = self.db.application.getAvatar(user,authenticate=False).user_tags
        if tags and not self.db.application.getResourcePermission(tags,user_tags):
            raise NotAllowedError
        return page_item

    def _get_documentNode(self,tblobj,pkey=None,source=None,version=None,**kwargs):
        isCachedInField = tblobj.column(source) is not None
        readTags = None
        handlername = f'_table.{tblobj.fullname}.getDocument_{source}'
        related_page_item = None
        try:
            handler = self.getPublicMethod('rpc',handlername)
        except AttributeError:
            handler = None
        if isCachedInField:
            readTags = tblobj.column(source).attributes.get('readTags')
        elif handler:
            readTags = getattr(handler,'tags')
        if readTags is not False:
            related_page_item = self._checkEndpointPermission(readTags,**kwargs)
        record = tblobj.record(pkey).output('record')
        documentNode = None
        clientRecordUpdater = Bag()
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
            clientRecordUpdater[source] = record[source]
            self.db.commit()
        if related_page_item:
            if isCachedInField and not version:
                clientRecordUpdater.addItem('{source}_versions', self._getVersionBag(documentNode,**kwargs),_sendback=False)
            clientRecordUpdater[tblobj.pkey] = record['id']
            self.setInClientRecord(tblobj,record=clientRecordUpdater,
                                            fields=','.join(clientRecordUpdater.keys()),
                                            page_id=related_page_item['register_item_id'],
                                            silent=True)
        return documentNode



    def _getVersionBag(self,documentNode,**kwargs):
        result = Bag()
        for i,version in enumerate(documentNode.versions):
            result.addItem(f'r_{i:02}',None,caption=self.toText(version['LastModified'],dtype='D'),version_id=version['VersionId'],
                                                date=version['LastModified'],isLatest=version['IsLatest'])
        return result


    def is_inline_displayable(self,storageNode):
        INLINE_MIME_TYPES = {
            'text/html',
            'text/plain',
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/svg+xml'
        }
        return storageNode.mimetype.lower() in INLINE_MIME_TYPES



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

