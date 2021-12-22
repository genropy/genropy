# -*- coding: UTF-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrexporter import getWriter


class GnrCustomWebPage(object):
    @public_method
    def print_res_data(self,table=None,resource=None,res_type=None,selectionName=None,export_mode=None,export_name=None,**kwargs):
        respath = '{res_type}/{resource}'.format(res_type=res_type,resource=resource)
        export_mode = export_mode or 'html'
        btcprint = self.loadTableScript(table=table,respath=respath)
        export_name = export_name or resource
        export_data = btcprint.get_export_data(selectionName=selectionName,export_mode=export_mode,export_name=export_name,**kwargs)
        exporter = getWriter(export_mode)()
        result = exporter.composeAll(export_data)
        self.response.content_type = exporter.content_type
        
        if export_mode=='xls':
            sn = self.site.storageNode(f'page:{export_name}')
            exporter.save(sn)
            self.download_name = sn.basename
            return sn.open('rb')

        result = exporter.join(result)
        return result
