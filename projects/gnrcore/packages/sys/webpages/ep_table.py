# -*- coding: utf-8 -*-
from gnr.sql.gnrsql import GnrSqlMissingTable
from gnr.core.gnrstring import templateReplace
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
            if self.response.content_type == 'application/pdf' and documentNode.watermark:
                pdfService = self.site.getService('pdf')
                return pdfService.watermarkedPDF([documentNode],watermark=documentNode.watermark,watermark_align='center')

            with documentNode.open('rb') as f:
                return f.read()
        else:
            if version:
                kwargs['version'] = version
            download_url = self.db.application.site.externalUrl(f"/sys/ep_table/{tblobj.fullname.replace('.','/')}/{pkey}/get/{source}",force_download=True,**kwargs)
            tpl = self.getResourceContent(resource='ep_table/download_file_tpl', ext='html')
            return templateReplace(
                tpl,{'download_url':download_url}
            )


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
        if version=='_latest_':
            version = None
        colobj = tblobj.column(source)
        isCachedInField = colobj is not None
        readTags = None
        handlername = f'_table.{tblobj.fullname}.getDocument_{source}'
        related_page_item = None
        try:
            handler = self.getPublicMethod('rpc',handlername)
        except AttributeError:
            handler = None
        documentPath = None
        record = tblobj.record(pkey).output('record')
        if isCachedInField:
            readTags = colobj.attributes.get('readTags')
            documentPath = record[source]
        elif handler:
            readTags = getattr(handler,'tags',None)
            pathTemplate = getattr(handler,'pathTemplate',None)
            if pathTemplate:
                documentPath = pathTemplate.format(record)
        if not documentPath:
            documentPathHandler = getattr(tblobj,f'{handlername}_path',None)
            if documentPathHandler:
                documentPath = documentPathHandler(record,**kwargs)
        if readTags is not False:
            #do with permissions
            related_page_item = self._checkEndpointPermission(readTags,**kwargs)
        documentNode = None
        clientRecordUpdater = Bag()
        if documentPath:
            documentNode = self.site.storageNode(documentPath,version=version) 
            if documentNode and not documentNode.exists:
                documentNode = None
        if handler and not documentNode:
            documentPath = handler(pkey,documentPath=documentPath,**kwargs)
            documentNode = self.site.storageNode(documentPath)
        if documentNode and isCachedInField and record[source] != documentNode.fullpath:
            with tblobj.recordToUpdate(pkey,raw=True) as rec:
                rec[source] = documentNode.fullpath
            clientRecordUpdater[source] = record[source]
            self.db.commit()
        versions_bag =  self._getVersionBag(documentNode,**kwargs)
        if related_page_item:
            clientRecordUpdater.addItem(f'${source}_versions',versions_bag)
            clientRecordUpdater[tblobj.pkey] = record['id']
            fields = ','.join(clientRecordUpdater.keys())
            self.setInClientRecord(tblobj,record=clientRecordUpdater,
                                            fields=fields,
                                            page_id=related_page_item['register_item_id'],
                                            silent=True)
        documentNode.watermark = None
        if version:
            version_attrs = versions_bag.getAttr(version)
            if version_attrs and not version_attrs['isLatest']:
                outdatedWatermark = colobj.attributes.get('outdatedWatermark') if  isCachedInField else None
                if handler and not outdatedWatermark:
                    outdatedWatermark = getattr(handler,'outdatedWatermark',None)
                documentNode.watermark = outdatedWatermark.format(**version_attrs).format(**record.asDict())
        return documentNode



    def _getVersionBag(self,documentNode,**kwargs):
        result = Bag()
        for version in documentNode.versions:
            localized_date = self.toText(version['LastModified'],dtype='D')
            label = version['VersionId'] if not version['IsLatest'] else '_latest_'
            result.addItem(label,None,caption=self._('!![en]Latest') if version['IsLatest'] else localized_date,version_id=version['VersionId'],
                                                date=version['LastModified'],localized_date=localized_date,isLatest=version['IsLatest'])
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

