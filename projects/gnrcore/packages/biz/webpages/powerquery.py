#  -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    def saved_query(self,*args,**kwargs):
        self.getCallArgs('method','pkg','table','queryName')
        print(x)