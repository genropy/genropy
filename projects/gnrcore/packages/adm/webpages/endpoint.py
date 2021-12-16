# -*- coding: UTF-8 -*-

from gnr.core.gnrdecorator import public_method
class GnrCustomWebPage(object):
    
    @public_method
    def pippo(self,name=None,**kwargs):
        return 'pippo'

    @public_method
    def print_res_data(self,**kwargs):
        self.loadTableScript()
        return str(kwargs)
