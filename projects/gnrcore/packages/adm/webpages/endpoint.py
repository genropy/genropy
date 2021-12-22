# -*- coding: UTF-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrexporter import getWriter


class GnrCustomWebPage(object):
    
    @public_method
    def pippo(self,name=None,**kwargs):
        return 'pippo'

    @public_method
    def print_res_data(self,table=None,resource=None,res_type=None,selectionName=None,export_mode=None,export_name=None,**kwargs):
        respath = '{res_type}/{resource}'.format(res_type=res_type,resource=resource)
        export_mode = export_mode or 'html'
        btcprint = self.loadTableScript(table=table,respath=respath)
        export_data = btcprint.get_export_data(selectionName=selectionName,export_mode=export_mode,export_name=export_name,**kwargs)
        exporter = getWriter(export_mode)()
        result = exporter.composeAll(export_data)
        if export_mode=='csv':
            self.response.content_type = 'text/plain'
        #if export_mode=='xls':
            
        result = exporter.join(result)
        return result
