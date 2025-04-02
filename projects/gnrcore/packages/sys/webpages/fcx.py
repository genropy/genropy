# -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method
from datetime import datetime

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:RecordRpc'
    convert_result = False
    skip_connection = False
    prefix='fcx_'




    def handlerResourceRpc(self,table=None,respath=None,class_name=None,
                                pkey=None,pdf=True,download=False,**kwargs):
        if True:
            pdfpathOrHtml = self.callTableScript(table=table,
                                            respath=respath,
                                            record=pkey,pdf=pdf)
            if not pdf:
                return pdfpathOrHtml
            pdfpath = pdfpathOrHtml
            sn = self.site.storageNode(pdfpath)
            self.response.content_type = 'application/pdf'
            if download:
                self.download_name = sn.basename
            with sn.open('rb') as f:
                return f.read()
        #except Exception as e:
        #    return f'error {str(e)}'

